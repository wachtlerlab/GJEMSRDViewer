from neo import Spike2IO, AnalogSignal
import os
import pandas as pd
import time
from GJEMS.ephys.neoNIXIO import addQuantity2section, addAnalogSignal2Block
from GJEMS.ephys.NEOFuncs import downSampleAnalogSignal, sliceAnalogSignal
import nixio as nix
from matplotlib import pyplot as plt
import numpy as np
import json
import quantities as qu
import operator

#***********************************************************************************************************************

def smrFilesPresent(expNames, smrDir):
    temp1 = []
    for expName in expNames:

        expDir = os.path.join(smrDir, expName[:8])
        if os.path.isdir(expDir):
            dirList = os.listdir(expDir)
            matches = [x.endswith('.smr') and x[:10] == expName for x in dirList]
            smrFilePresent = any(matches)

        else:
            smrFilePresent = False

        temp1.append(smrFilePresent)
    temp1 = np.array(temp1).reshape((len(temp1), 1))
    return temp1

#***********************************************************************************************************************

def addDyeNamesIfNess(expNames, smrDir):
    newIndices = {}
    for expName in expNames:

        expDir = os.path.join(smrDir, expName[:8])
        if os.path.isdir(expDir):
            dirList = os.listdir(expDir)
            matches = [x.endswith('.smr') and x[:8] == expName[:8] for x in dirList]
            newIndex = dirList[matches.index(True)][:-4]
            if len(newIndex) > len(expName):
                newIndices[expName] = newIndex
            else:
                newIndices[expName] = expName

        else:
            newIndices[expName] = expName

    return newIndices


#***********************************************************************************************************************
def parseMetaDataFile(excelFile, excelSheet, smrDir):

    tempDf = pd.read_excel(excelFile, sheetname=excelSheet, header=None, parse_cols=None)

    currentVal = tempDf.loc[0, 0]
    for ind, val in enumerate(tempDf.loc[0, 1:]):
        if pd.isnull(val):
            tempDf.loc[0, ind + 1] = currentVal
        else:
            currentVal = val

    for ind, val in enumerate(tempDf.loc[1, :]):

        if pd.isnull(val):
            tempDf.loc[1, ind] = tempDf.loc[0, ind]

    metaDF = tempDf.loc[3:, 1:]
    metaDF.index = tempDf.loc[3:, 0]
    metaDF.columns = pd.MultiIndex.from_arrays((tempDf.loc[0, 1:], tempDf.loc[1, 1:]))
    metaDF.sort_index()

    newIndices = addDyeNamesIfNess(metaDF.index, smrDir)
    metaDF = metaDF.rename(index=newIndices)

    markedUploaded = (metaDF.loc[:, ('Powerfolder', 'LSM')] == '*').values
    smrsPresent = smrFilesPresent(metaDF.index, smrDir)

    problem = np.logical_and(markedUploaded, np.logical_not(smrsPresent))

    if any(problem):
        print('These experiments were marked uploaded but were not found in {}:\n{}\nIGNORING THESE'
              .format(smrDir, [x for x, y in zip(metaDF.index, problem) if y]))

    metaDFFiltered = metaDF[smrsPresent]

    return metaDFFiltered

#***********************************************************************************************************************

def extractMetaData(mdDF, expName):

    expData = mdDF.loc[expName]

    freqEntry = str(expData[('Stimulus', 'Frequency')])
    pulseEntry = expData[('Stimulus', 'Pulse (Duration/Interval)')]
    spontEntry = expData[('Activity', 'Spontaneous')]
    respEntry = expData[('Activity', 'Response')]


    metaData = {}
    metaData['pulse'] = [[], []]
    metaData['freqs'] = []
    metaData['spont'] = ''
    metaData['resp'] = ''

    if not pd.isnull(freqEntry):
        if freqEntry.find(',') < 0:

            # sometimes the commas are not read in, leading to concatenated entries like 100265. Splitting them.
            tempN = len(freqEntry)
            for x in xrange(int(np.ceil(tempN / 3.0))):

                metaData['freqs'].append(int(freqEntry[max(0, tempN - (x + 1) * 3): tempN - 3 * x]))

        else:
            metaData['freqs'] = map(lambda x: int(x), freqEntry.split(','))

    metaData['freqs'] *= qu.Hz

    if not pd.isnull(pulseEntry):
        unresolved = []
        # pulseEntry is expected to be made of two types of entries:
        # (i) a/b (ii) a, c / b which is the same as a/b , c/b
        try:
            for word in pulseEntry.split(','):
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

    metaData['pulse'][0] *= qu.ms
    metaData['pulse'][1] *= qu.ms

    if not pd.isnull(spontEntry):
        metaData['spont'] = bool(spontEntry.count('yes') + spontEntry.count('Yes') + spontEntry.count('YES'))


    if not pd.isnull(respEntry):
        metaData['resp'] = str(respEntry)

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

        if endTimeStr in ['maxtime', 'max time', 'Max Time']:
            endTime = None
        else:
            endTime = float(endTimeStr[:-3]) * qu.s

        if startTimeStr.endswith('sec'):
            startTimeStr = startTimeStr[:-3]

        startTime = float(startTimeStr) * qu.s

    elif openingBracketAt == -1 and closingBracketAt == -1 and dashAt == -1:
        startTime = None
        endTime = None
    else:
        raise Exception('Improper calibration string: ' + calibString)

    return calib, startTime, endTime

# **********************************************************************************************************************

def calibrateSignal(inputSignal, calibStrings, forceUnits=None):

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

    return outputSignal

# **********************************************************************************************************************

def readSignal(rawSignal, calibStrings, timeWindow, forceUnits=None):

    calibSignal = calibrateSignal(rawSignal, calibStrings, forceUnits)

    startInd = int((timeWindow[0] - calibSignal.t_start) * calibSignal.sampling_rate.magnitude)
    endInd = int((timeWindow[1] - calibSignal.t_start) * calibSignal.sampling_rate.magnitude)

    return calibSignal[startInd: endInd + 1]

# **********************************************************************************************************************

def parseSpike2Data(smrFile, startStop=None, forceUnits=False):
    spike2Reader = Spike2IO(smrFile)
    dataBlock = spike2Reader.read()[0]
    voltageCalibs = dataBlock.segments[0].eventarrays[0].annotations['extra_labels']
    entireVoltageSignal = dataBlock.segments[0].analogsignals[0]

    vibrationCalibs = dataBlock.segments[0].eventarrays[1].annotations['extra_labels']
    entireVibrationSignal = dataBlock.segments[0].analogsignals[1]

    entireCurrentSignal = None
    if len(dataBlock.segments[0].analogsignals) > 2:
        if 'extra_labels' in dataBlock.segments[0].eventarrays[3].annotations:
            currentCalibs = dataBlock.segments[0].eventarrays[3].annotations['extra_labels']
            entireCurrentSignal = dataBlock.segments[0].analogsignals[2]

    if startStop is None:
        recordingStartTime = dataBlock.segments[0].eventarrays[2].times[0]

        recordingEndTime = dataBlock.segments[0].eventarrays[2].times[1]
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

    voltageSignal = readSignal(entireVoltageSignal, voltageCalibs, [recordingStartTime, recordingEndTime],
                               voltForceUnits)
    voltageSignal.name = 'MembranePotential'

    vibrationSignal = readSignal(entireVibrationSignal, vibrationCalibs, [recordingStartTime, recordingEndTime],
                                 vibForceUnits)
    vibrationSignal.name = 'VibrationStimulus'

    currentSignal = None
    if len(dataBlock.segments[0].analogsignals) > 2:
        if 'extra_labels' in dataBlock.segments[0].eventarrays[3].annotations:
            currentSignal = readSignal(entireCurrentSignal, currentCalibs, [recordingStartTime, recordingEndTime],
                                       currForceUnits)
            currentSignal.name = 'CurrentInput'

    return voltageSignal, vibrationSignal, currentSignal

# **********************************************************************************************************************

def saveNixFile(smrFile, nixFile, metaData, startStop=None, askShouldReplace=True, forceUnits=False):
    voltageSignal, vibrationSignal, currentSignal = parseSpike2Data(smrFile, startStop, forceUnits)


    if os.path.isfile(nixFile):

        if askShouldReplace:
            ch = raw_input('File Already Exists. Overwrite?(y/n):')

            if ch != 'y':
                exit('Aborted.')

        os.remove(nixFile)

    nixFileO = nix.File.open(nixFile, nix.FileMode.Overwrite)

    vibStimSec = nixFileO.create_section('VibrationStimulii-Raw', 'Recording')

    vibStimSec.create_property('NatureOfResponse', [nix.Value(metaData['resp'])])
    vibStimSec.create_property('SpontaneousActivity', [nix.Value(metaData['spont'])])

    contStimSec = vibStimSec.create_section('ContinuousStimulii', 'Stimulii/Sine')

    if any(metaData["freqs"]):
        addQuantity2section(contStimSec, metaData['freqs'], 'FrequenciesUsed')

    if all(map(len, metaData['pulse'])):
        pulseStimSec = vibStimSec.create_section('PulseStimulii', 'Stimulii/Pulse')
        addQuantity2section(pulseStimSec, 265 * qu.Hz, 'FrequenciesUsed')

        addQuantity2section(pulseStimSec, metaData['pulse'][0], 'PulseDurations')
        addQuantity2section(pulseStimSec, metaData['pulse'][1], 'PulseIntervals')

    rawDataBlk = nixFileO.create_block('RawDataTraces', 'RecordingData')

    vibSig = addAnalogSignal2Block(rawDataBlk, vibrationSignal)

    voltSig = addAnalogSignal2Block(rawDataBlk, voltageSignal)

    if currentSignal is not None:
        curSig = addAnalogSignal2Block(rawDataBlk, currentSignal)

    nixFileO.close()

# **********************************************************************************************************************

def importAll(smrPath, excelFile, excelSheet, nixPath, expNames=None,
              startStopFile=None, askShouldReplace=True, forceUnits=False):

    metaDataDF = parseMetaDataFile(excelFile, excelSheet, smrPath)

    if expNames is None:
        expNames = map(str, metaDataDF.index)

    adjustedStartStop = {}
    if startStopFile:
        with open(startStopFile, 'r') as fle:
            adjustedStartStop = json.load(fle)

    for expName in expNames:

        if expName not in metaDataDF.index:

            raise(ValueError('Experiment with ID {} not found in {}'.format(expName, excelFile)))

        print('Doing {}'.format(expName))
        metaData = extractMetaData(metaDataDF, expName)

        smrFile = os.path.join(smrPath, expName[:8], expName + '.smr')
        nixFile = os.path.join(nixPath, expName + '.h5')

        startStop = None
        if expName in adjustedStartStop:
            startStop = adjustedStartStop[expName]
        saveNixFile(smrFile, nixFile, metaData, startStop, askShouldReplace, forceUnits)

# **********************************************************************************************************************

class RawDataViewer(object):

    def __init__(self, smrFile, maxFreq=700*qu.Hz, forceUnits=False):

        expName = os.path.split(smrFile)[1][:-4]

        signals = parseSpike2Data(smrFile, [-np.inf, np.inf], forceUnits)

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

        if self.currentSignal:
            epochCurSignal = sliceAnalogSignal(self.currentSignal, epochTimes[0], epochTimes[1])
            ax.plot(epochCurSignal.times, epochCurSignal, ls='-', color='r', marker=marker,
                    label='Current input through electrode (nA)')

        if signal:

            epochSignal = sliceAnalogSignal(signal, epochTimes[0], epochTimes[1])
            ax.plot(epochSignal.times, epochSignal, ls='-', color='m', marker=marker,
                    label='External Signal')


        ax.legend(ncol=2, loc='best')
        ax.set_xlabel('Time ({})'.format(epochVoltSignal.times.units.dimensionality.string))

    # ******************************************************************************************************************
# **********************************************************************************************************************




