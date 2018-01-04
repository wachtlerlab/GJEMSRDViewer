import numpy as np
from neo import AnalogSignal
import quantities as pq

#***********************************************************************************************************************

def downSampleAnalogSignal(analogSignal, downSampleFactor):
    '''
    Downsamples the input analogsignal, with the downsampled signal having the same t_start as analogsignal
    :param analogSignal: neo.analogsignal
    :param downSampleFactor: int, must be at least 1
    :return: analogSignalDown, neo.analogsignal with sampling rate = analogsignal.sampling_rate/factor
    and analogSignalDown.t_start = analogSignal.t_start
    '''

    assert type(downSampleFactor) == int, 'downsample factor must be an int'
    assert downSampleFactor >= 1, 'downsample factor must be atleast 1'

    if downSampleFactor == 1:
        return analogSignal.copy()

    else:
        newSamplingRate = analogSignal.sampling_rate / downSampleFactor
        downSamplingIndices = range(0, analogSignal.shape[0], downSampleFactor)
        analogSignalMagnitude = analogSignal.magnitude[downSamplingIndices]

        analogSignalDown = AnalogSignal(signal=analogSignalMagnitude,
                                                units=analogSignal.units,
                                                sampling_rate=newSamplingRate,
                                                t_start=analogSignal.t_start)
        analogSignalDown = analogSignalDown.reshape((analogSignalDown.shape[0],))
        return analogSignalDown


#***********************************************************************************************************************

def sliceAnalogSignal(analogSignal, sliceStartTime=None, sliceEndTime=None):
    '''
    Slice a neo.analogsignal using times instead of indices
    :param analogSignal: neo.analogsignal
    :param sliceStartTime: quantities.Quantity, start time of the slice, must be at least analogSignal.t_start.
    If it is None, slice starts at the beginning of analogSignal
    :param sliceEndTime: quantities.Quantity, stop time of the slice, must be at most analogSignal.t_start
    If it is None, slice ends at the end of analogSignal
    :return: neo.analogsignal, the slice of analogSignal between sliceStartTime and sliceEndTime.
    '''

    assert type(analogSignal) is AnalogSignal, 'analogSignal must be a neo.AnalogSignal'

    if sliceStartTime is None:
        sliceStartTime = analogSignal.t_start

    if sliceEndTime is None:
        sliceEndTime = analogSignal.t_stop

    assert type(sliceStartTime) is pq.Quantity, 'sliceStartTime must be a quantities.Quanitity'
    assert type(sliceEndTime) is pq.Quantity, 'sliceEndTime must be a quantities.Quanitity'

    assert sliceStartTime >= analogSignal.t_start, 'sliceStartTime must be >= analogSignal.t_start'
    assert sliceEndTime <= analogSignal.t_stop, 'sliceEndTime must be <= analogSignal.t_stop'

    sliceStartInd = int(((sliceStartTime - analogSignal.t_start) / analogSignal.sampling_period).simplified)
    sliceEndInd = int(((sliceEndTime - analogSignal.t_start) / analogSignal.sampling_period).simplified)

    toReturn = analogSignal[sliceStartInd: sliceEndInd + 1]

    return toReturn

#***********************************************************************************************************************

def getSpikesIn(spikeTimes, intervalStart, intervalEnd):
    '''
    Return spike times in the specified time interval
    :param spikeTimes: quantities.Quantity, representing the spike times
    :param intervalStart: quantities.Quantity, start time of interval of interest
    :param intervalEnd: qunatiies.Quantity, end time of interval of interest
    :return: quantities.Quantity, spikes times in the specified interval
    '''

    return spikeTimes[(spikeTimes >= intervalStart) & (spikeTimes < intervalEnd)]

#***********************************************************************************************************************

def getSpikeRateIn(spikeTrain, intervalStart=None, intervalEnd=None):
    '''
    Calculate the spike rate of the spike train in the specified time iterval. It is calculated as the number of spikes
    in the interval of interest divided by the duration of the interval.
    :param spikeTrain: neo.spiketrain
    :param intervalStart: quantities.Quantity, start time of the interval of interest
    :param intervalEnd: quantities.Quantity, end time of the interval of interest
    :return: float, spike rate of the spike train in the interval of interest in Hz
    '''

    if intervalStart is None:
        intervalStart = spikeTrain.t_start

    if intervalEnd is None:
        intervalEnd = spikeTrain.t_stop

    intervalSpikes = getSpikesIn(spikeTrain.times, intervalStart, intervalEnd)
    intervalDuration = intervalEnd - intervalStart
    intervalDuration.units = pq.s

    return len(intervalSpikes) / float(intervalDuration.magnitude)

#***********************************************************************************************************************

def simpleFloat(quant):
    '''
    Float(s) of simplified version(s) of a quantity.Quantity or an iterable of quantity.Quantity objects
    :param quant: a quantity.Quantity or an iterable of quantity.Quantity objects
    :return: float or iterable of floats
    '''

    if quant.shape == ():

        return float(quant.simplified)

    elif len(quant.shape) == 1:

        if quant.shape[0]:

            return [float(q.simplified) for q in quant]

    else:

        raise(ValueError('simpleFloat only supports scalar and 1D quantities'))

#***********************************************************************************************************************

def getSpikeAmps(resp, spikeTimes):

    spikeInds = map(int, (spikeTimes - resp.t_start) * resp.sampling_rate)
    return resp[spikeInds]

#***********************************************************************************************************************