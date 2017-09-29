from neo import Spike2IO, AnalogSignal
import os
from GJEMS.ephys.neoNIXIO import addQuantity2section, addAnalogSignal2Block
from GJEMS.ephys.NEOFuncs import downSampleAnalogSignal, sliceAnalogSignal
import nixio as nix
import numpy as np
import json
import quantities as qu
import pandas as pd


# **********************************************************************************************************************


def parseStartStopStr(startStopStr):

    startTimeStr, endTimeStr = startStopStr.split("-")
    try:
        if endTimeStr in ['maxtime', 'max time', 'Max Time']:
            endTime = None
        else:
            endTime = float(endTimeStr)


        startTime = float(startTimeStr)
        return startTime, endTime
    except Exception as e:
        raise ValueError('Improper Recording period string {}'.format(startStopStr))

# **********************************************************************************************************************


def parseCalibString(calibString, unitStr):

    if calibString.find(',') < 0:
        calibValQ = qu.Quantity(float(calibString), units=unitStr)
        return calibValQ, None, None
    else:
        timeIntervalStr, calibVal = calibString.split(", ")
        calibValQ = qu.Quantity(float(calibVal), units=unitStr)

        startTimeStr, endTimeStr = timeIntervalStr.split("-")

        if endTimeStr.endswith('s'):
            endTimeStr = endTimeStr.rstrip('s')
        elif endTimeStr.endswith('sec'):
            endTimeStr = endTimeStr.rstrip('sec')

        try:
            if endTimeStr in ['maxtime', 'max time', 'Max Time']:
                endTime = None
            else:
                endTime = float(endTimeStr) * qu.s

            if startTimeStr.endswith('sec'):
                startTimeStr = startTimeStr.rstrip('sec')
            startTime = float(startTimeStr) * qu.s

            return calibValQ, startTime, endTime
        except Exception as e:
            raise ValueError('Improper calibration string {}'.format(calibString))

# **********************************************************************************************************************

def calibrateSignal(inputSignal, calibString, calibUnitStr, forceUnits=None):

    if calibString.find(';') > 0:
        calibStrings = calibString.split(';')
    elif calibString.find(':') > 0:
        calibStrings = calibString.split(':')
    elif all([x.isdigit() or x == '.' for x in calibString]):
        calibStrings = [calibString]
    else:
        raise(ValueError("Improper Calibration string {}".format(calibString)))

    ipSignalMag = inputSignal.magnitude
    ipSigUnits = inputSignal.units

    for calibString in calibStrings:

        calib, startTime, endTime = parseCalibString(calibString, calibUnitStr)

        if endTime is None:
            endTime = inputSignal.t_stop

        if startTime is None:
            startTime = inputSignal.t_start

        startIndex = int((startTime - inputSignal.t_start) * inputSignal.sampling_rate)

        endIndex = int((endTime - inputSignal.t_start) * inputSignal.sampling_rate)

        ipSignalMag[startIndex: endIndex + 1] *= calib.magnitude

        if forceUnits is not None:
            ipSigUnits = forceUnits
        else:
            if ipSigUnits == qu.Quantity(1):
                ipSigUnits = calib.units

            elif ipSigUnits != calib.units:
                raise(Exception('CalibStrings given don\'t have the same units'))


        outputSignal = AnalogSignal(
                                    signal=ipSignalMag,
                                    units=ipSigUnits,
                                    sampling_rate=inputSignal.sampling_rate
                                    )
        outputSignal = outputSignal.reshape((outputSignal.shape[0],))

    return outputSignal

# **********************************************************************************************************************

def readSignal(rawSignal, calibStrings, calibUnitStr, timeWindow, forceUnits=None):

    calibSignal = calibrateSignal(rawSignal, calibStrings, calibUnitStr, forceUnits)

    startInd = int((timeWindow[0] - calibSignal.t_start) * calibSignal.sampling_rate.magnitude)
    endInd = int((timeWindow[1] - calibSignal.t_start) * calibSignal.sampling_rate.magnitude)

    return calibSignal[startInd: endInd + 1]

# **********************************************************************************************************************

def parseSpike2Data(smrFile, calibStrings, startStop=None, forceUnits=False):

    spike2Reader = Spike2IO(smrFile)
    dataBlock = spike2Reader.read()[0]
    entireVoltageSignal = dataBlock.segments[0].analogsignals[0]

    entireVibrationSignal = dataBlock.segments[0].analogsignals[1]

    entireCurrentSignal = None
    if len(dataBlock.segments[0].analogsignals) > 2 and calibStrings['currentCalibStr'] is not None:
        entireCurrentSignal = dataBlock.segments[0].analogsignals[2]
        currentCalibs = calibStrings['currentCalibStr']
        currentCalibUnitStr = 'nA'

    voltageCalibs = calibStrings['voltageCalibStr']
    voltageCalibUnitStr = 'mV'
    vibrationCalibs = calibStrings['vibrationCalibStr']
    vibrationCalibUnitStr = 'um'

    if startStop is None:
        recordingStartTime = -np.inf

        recordingEndTime = np.inf

    else:
        recordingStartTime = startStop[0] * qu.s
        recordingEndTime = startStop[1] * qu.s

    recordingStartTime = max(recordingStartTime,
                             entireVibrationSignal.t_start,
                             entireVoltageSignal.t_start)
    recordingEndTime = min(recordingEndTime,
                           entireVibrationSignal.t_stop,
                           entireVoltageSignal.t_stop)

    if forceUnits:
        voltForceUnits = qu.mV
        vibForceUnits = qu.um
        currForceUnits = qu.nA
    else:
        voltForceUnits = vibForceUnits = currForceUnits = None

    voltageSignal = readSignal(entireVoltageSignal, voltageCalibs, voltageCalibUnitStr,
                               [recordingStartTime, recordingEndTime], voltForceUnits)
    voltageSignal.name = 'MembranePotential'

    vibrationSignal = readSignal(entireVibrationSignal, vibrationCalibs, vibrationCalibUnitStr,
                                 [recordingStartTime, recordingEndTime], vibForceUnits)
    vibrationSignal.name = 'VibrationStimulus'

    currentSignal = None

    if len(dataBlock.segments[0].analogsignals) > 2 and calibStrings['currentCalibStr'] is not None:
        currentSignal = readSignal(entireCurrentSignal, currentCalibs, currentCalibUnitStr,
                                   [recordingStartTime, recordingEndTime],
                                   currForceUnits)
        currentSignal.name = 'CurrentInput'

    return voltageSignal, vibrationSignal, currentSignal

# **********************************************************************************************************************

class RawDataViewer(object):

    def __init__(self, smrFile, maxFreq=700*qu.Hz, forceUnits=False):

        calibStrings = {}
        calibStrings['voltageCalibStr'] = '20'
        calibStrings['vibrationCalibStr'] = '27.1'
        calibStrings['currentCalibStr'] = '10'

        signals = parseSpike2Data(smrFile, calibStrings, [-np.inf, np.inf], forceUnits)

        signalSamplingRates = [x.sampling_rate for x in signals if x is not None]
        assert (np.diff(signalSamplingRates) < 1 * qu.Hz).all(), \
            'Signals do not have same sampling rate\n{}'.format(reduce(lambda x, y: x + '\n' + y, map(repr, signals)))

        self.voltageSignal = downSampleAnalogSignal(signals[0], int(signals[0].sampling_rate / maxFreq))
        self.vibrationSignal = downSampleAnalogSignal(signals[1], int(signals[1].sampling_rate / maxFreq))


        if signals[2] is not None:
            self.currentSignal = downSampleAnalogSignal(signals[2], int(signals[2].sampling_rate / maxFreq))
        else:
            self.currentSignal = None




    def plotVibEpoch(self, ax, epochTimes, signal=None, points=False):

        marker = '*' if points else 'None'

        epochVoltSignal = sliceAnalogSignal(self.voltageSignal, epochTimes[0], epochTimes[1])
        ax.plot(epochVoltSignal.times, epochVoltSignal, ls='-', color='b', marker=marker,
                label='Membrane potential (mV)')
        epochVibSignal = sliceAnalogSignal(self.vibrationSignal, epochTimes[0], epochTimes[1])
        ax.plot(epochVibSignal.times, epochVibSignal, ls='-', color='r', marker=marker,
                label='Vibration Input to Antenna (um)')

        if self.currentSignal is not None:
            epochCurSignal = sliceAnalogSignal(self.currentSignal, epochTimes[0], epochTimes[1])
            ax.plot(epochCurSignal.times, epochCurSignal, ls='-', color='r', marker=marker,
                    label='Current input through electrode (nA)')

        if signal is not None:

            epochSignal = sliceAnalogSignal(signal, epochTimes[0], epochTimes[1])
            ax.plot(epochSignal.times, epochSignal, ls='-', color='m', marker=marker,
                    label='External Signal')


        ax.legend(ncol=2, loc='best')
        ax.set_xlabel('Time ({})'.format(epochVoltSignal.times.units.dimensionality.string))

    # ******************************************************************************************************************
# **********************************************************************************************************************



