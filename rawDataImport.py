from neo import Spike2IO, AnalogSignal
import os
import pyexcel_xlsx
import pyexcel as pe
import pyexcel.ext.xlsx
import time
from matplotlib import pyplot as plt
import quantities as qu
from neo import AnalogSignal
import numpy as np


#***********************************************************************************************************************

def extractMetaData(excelFile, excelSheet, expName):

    metaDataSheet = pe.get_sheet(file_name=excelFile, sheet_name=excelSheet)
    lne1 = metaDataSheet.row_at(0)
    lne2 = metaDataSheet.row_at(1)

    freqCol = lne2.index('Frequency')
    pulseCol = lne2.index('Pulse (Duration/Interval)')
    spontCol = lne2.index('Spontaneous')
    respCol = lne2.index('Response')

    metaData = {}
    metaData['pulse'] = [[], []]

    expRow = metaDataSheet.column_at(0).index(unicode(expName))

    expData = metaDataSheet.row_at(expRow)

    if isinstance(expData[freqCol], int):
        metaData['freqs'] = expData[freqCol] * qu.Hz
    else:
        metaData['freqs'] = qu.Quantity([float(x) for x in expData[freqCol].split(',') if not x == ''], qu.Hz)

    if expData[pulseCol]:
        unresolved = []
        try:
            for word in expData[pulseCol].split(','):
                if word.count('/'):
                    (duration, interval) = word.split('/')
                    unresolved.append(float(duration))
                    metaData['pulse'][1].extend([float(interval)] * len(unresolved))
                    metaData['pulse'][0].extend(unresolved)
                    unresolved = []
                else:
                    unresolved.append(float(word))

            metaData['pulse'][1].extend(unresolved)
            lastNum = metaData['pulse'][0][-1]
            metaData['pulse'][0].extend([lastNum] * len(unresolved))
        except:
            raise(Exception('Improper entry in pulse column for the given smr file.'))

    metaData['pulse'][0] = qu.Quantity(metaData['pulse'][0], qu.ms)
    metaData['pulse'][1] = qu.Quantity(metaData['pulse'][1], qu.ms)
    spontStr = expData[spontCol]
    metaData['spont'] = bool(spontStr.count('yes') + spontStr.count('Yes') + spontStr.count('YES'))
    metaData['resp'] = str(expData[respCol])

    return metaData

# **********************************************************************************************************************

def parseCalibString(calibString):

    f = lambda x: x.isdigit() or (x is '.')

    backslahAt = calibString.find('/')

    assert backslahAt >= 0, 'Improper calibration string: ' + calibString

    val = float(filter(f, calibString[:backslahAt]))
    unitStr = filter(str.isalpha, calibString[:backslahAt])
    calib = qu.Quantity(val, units=unitStr)

    openingBracketAt = calibString.find('(')
    closingBracketAt = calibString.find(')')
    dashAt = calibString.find('-')

    if openingBracketAt >= 0 and closingBracketAt >= 0 and dashAt >= 0:

        startTimeStr = calibString[openingBracketAt + 1: dashAt]
        endTimeStr = calibString[dashAt + 1: closingBracketAt]

        if endTimeStr == 'maxtime':
            endTime = None

        else:

            endTime = float(endTimeStr[:-3]) * qu.s

        startTime = float(startTimeStr) * qu.s

    elif openingBracketAt == -1 and closingBracketAt == -1 and dashAt == -1:
        startTime = None
        endTime = None
    else:
        raise Exception('Improper calibration string: ' + calibString)

    return calib, startTime, endTime

# **********************************************************************************************************************

def calibrateSignal(inputSignal, calibStrings):

    ipSignalMag = inputSignal.magnitude
    ipSigUnits = inputSignal.units

    for calibString in calibStrings:

        calib, startTime, endTime = parseCalibString(calibString)

        if endTime is None:
            endTime = inputSignal.t_stop

        if startTime is None:
            startTime = inputSignal.t_start

        startIndex = int((startTime - inputSignal.t_start) * inputSignal.sampling_rate)

        endIndex = int((endTime - inputSignal.t_start) * inputSignal.sampling_rate)

        ipSignalMag[startIndex: endIndex + 1] *= calib.magnitude

        if ipSigUnits == qu.Quantity(1):
            ipSigUnits = calib.units

        elif ipSigUnits != calib.units:
            raise(Exception('CalibStrings given don\'t have the same units'))

        outputSignal = AnalogSignal(
                                    signal=ipSignalMag,
                                    units=ipSigUnits,
                                    sampling_rate=inputSignal.sampling_rate
                                    )

    return outputSignal

# **********************************************************************************************************************

def readSignal(rawSignal, calibStrings, timeWindow):

    calibSignal = calibrateSignal(rawSignal, calibStrings)

    startInd = int((timeWindow[0] - calibSignal.t_start) * calibSignal.sampling_rate.magnitude)
    endInd = int((timeWindow[1] - calibSignal.t_start) * calibSignal.sampling_rate.magnitude)

    return calibSignal[startInd: endInd + 1]

# **********************************************************************************************************************


class RawDataImporter(object):

    def __init__(self, smrFile, excelFile, excelSheet):

        assert os.path.isfile(smrFile), 'SMR file not found:' + smrFile
        assert os.path.isfile(excelFile), 'Excel file not found:' + excelFile

        self.expName = os.path.split(smrFile)[1].strip('.smr')

        spike2Reader = Spike2IO(smrFile)
        self.dataBlock = spike2Reader.read()[0]

        self.metaData = extractMetaData(excelFile, excelSheet, self.expName)

        self.currentSignal = None

        self.maximumFreq = 700 * qu.Hz

    #*******************************************************************************************************************

    def parseSpike2Data(self):

        voltageCalibs = self.dataBlock.segments[0].eventarrays[0].annotations['extra_labels']
        entireVoltageSignal = self.dataBlock.segments[0].analogsignals[0]
        entireVoltageSignal.sampling_rate = (1 / 4.8e-5) * qu.Hz

        vibrationCalibs = self.dataBlock.segments[0].eventarrays[1].annotations['extra_labels']
        entireVibrationSignal = self.dataBlock.segments[0].analogsignals[1]

        if len(self.dataBlock.segments[0].analogsignals) > 2:
            currentCalibs = self.dataBlock.segments[0].eventarrays[3].annotations['extra_labels']
            entireCurrentSignal = self.dataBlock.segments[0].analogsignals[2]

        recordingStartTime = self.dataBlock.segments[0].eventarrays[2].times[0]
        recordingEndTime = self.dataBlock.segments[0].eventarrays[2].times[1]

        self.voltageSignal = readSignal(entireVoltageSignal, voltageCalibs, [recordingStartTime, recordingEndTime])
        self.voltageSignal.name = 'MembranePotential'

        self.vibrationSignal = readSignal(entireVibrationSignal, vibrationCalibs, [recordingStartTime, recordingEndTime])
        self.vibrationSignal.name = 'VibrationStimulus'

        if len(self.dataBlock.segments[0].analogsignals) > 2:
            self.currentSignal = readSignal(entireCurrentSignal, currentCalibs, [recordingStartTime, recordingEndTime])
            self.currentSignal.name = 'CurrentInput'

    #*******************************************************************************************************************

    def downSampleVibSignal(self):

        self.downSamplingFactor = int(round(self.vibrationSignal.sampling_rate / (4 * self.maximumFreq)))
        newSamplingRate = self.vibrationSignal.sampling_rate / self.downSamplingFactor
        downSamplingIndices = range(0, self.vibrationSignal.shape[0], self.downSamplingFactor)

        self.vibrationSignalDown = AnalogSignal(signal=self.vibrationSignal.magnitude[downSamplingIndices],
                                                units=self.vibrationSignal.units,
                                                sampling_rate=newSamplingRate,
                                                t_start=self.vibrationSignal.t_start)

        self.vibrationSignalDown -= np.median(self.vibrationSignalDown)

        self.vibrationSignalDownStdDev = np.std(self.vibrationSignalDown)


    #*******************************************************************************************************************

    def downSampleVoltageSignal(self, downSamplingFactor=None):

        if downSamplingFactor is None:

            downSamplingFactor = self.downSamplingFactor

        newSamplingRate = self.voltageSignal.sampling_rate / downSamplingFactor
        downSamplingIndices = range(0, self.voltageSignal.shape[0], downSamplingFactor)

        voltageSignalDown = AnalogSignal(signal=self.voltageSignal.magnitude[downSamplingIndices],
                                                units=self.voltageSignal.units,
                                                sampling_rate=newSamplingRate,
                                                t_start=self.voltageSignal.t_start)

        return voltageSignalDown


    #*******************************************************************************************************************

    def downSampleCurrentSignal(self, downSamplingFactor=None):

        if downSamplingFactor is None:

            downSamplingFactor = self.downSamplingFactor

        newSamplingRate = self.currentSignal.sampling_rate / downSamplingFactor
        downSamplingIndices = range(0, self.currentSignal.shape[0], downSamplingFactor)

        currentSignalDown = AnalogSignal(signal=self.currentSignal.magnitude[downSamplingIndices],
                                                units=self.currentSignal.units,
                                                sampling_rate=newSamplingRate,
                                                t_start=self.currentSignal.t_start)

        return currentSignalDown

    #*******************************************************************************************************************

    def plotVibEpoch(self, ax, epochTimes, signal=None, points=False):

        # indStart = int(epochTimes[0] * qu.s * self.entireVibrationSignal.sampling_rate + self.recordingStartIndex)
        # indEnd = int(epochTimes[1] * qu.s * self.entireVibrationSignal.sampling_rate + self.recordingStartIndex)

        # epochTVec = self.entireVibrationSignal.t_start + np.arange(indStart, indEnd) * self.entireVibrationSignal.sampling_period

        # plt.plot(epochTVec, self.entireVibrationSignal[indStart:indEnd], 'g' + extra)

        self.downSampleVibSignal()

        voltageSignalDown = self.downSampleVoltageSignal()

        indStart = int(np.floor((epochTimes[0] - self.vibrationSignalDown.t_start) * self.vibrationSignalDown.sampling_rate))
        indEnd = int(np.floor((epochTimes[1] - self.vibrationSignalDown.t_start) * self.vibrationSignalDown.sampling_rate))

        epochTVec = self.vibrationSignalDown.t_start + np.arange(indStart, indEnd) * self.vibrationSignalDown.sampling_period



        extra = ''
        if points:
            extra = '*-'

        ax.cla()

        ax.plot(epochTVec.magnitude, self.vibrationSignalDown[indStart:indEnd].magnitude, 'g' + extra,
                label='vibration signal')
        plt.xlabel('time (' + str(epochTVec.units) + ')')
        ax.plot(epochTVec.magnitude, voltageSignalDown[indStart:indEnd].magnitude, 'b' + extra,
                label='voltage signal')



        if len(self.dataBlock.segments[0].analogsignals) > 2:
            currentSignalDown = self.downSampleCurrentSignal()
            ax.plot(epochTVec.magnitude,currentSignalDown[indStart:indEnd].magnitude, 'r' + extra,
                              label='current input')



        if signal is not None:


            newSamplingRate = signal.sampling_rate / self.downSamplingFactor
            downSamplingIndices = range(0, signal.shape[0], self.downSamplingFactor)

            signalDown = AnalogSignal(signal=signal.magnitude[downSamplingIndices],
                                                    units=signal.units,
                                                    sampling_rate=newSamplingRate,
                                                    t_start=signal.t_start)

            signalIndStart = int(np.floor((epochTimes[0] * qu.s - signal.t_start) * newSamplingRate))
            signalIndEnd = int(np.floor((epochTimes[1] * qu.s - signal.t_start) * newSamplingRate))

            if (signalIndEnd - signalIndStart) > epochTVec.shape[0]:
                signalIndStart += 1
            elif (signalIndEnd - signalIndStart) < epochTVec.shape[0]:
                signalIndEnd += 1


            ax.plot(epochTVec, signalDown[signalIndStart:signalIndEnd], 'm' + extra, label='external signal')

        ax.set_xlabel('time (s)')
        ax.set_ylabel('Voltage signal(mV), vibration signal(um), current signal(nA)')
        ax.legend()


    #*******************************************************************************************************************





