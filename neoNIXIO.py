import nix
import neo
import quantities as qu
import numpy as np

qu2Val = lambda x: nix.Value(float(x))
quUnitStr = lambda x: x.dimensionality.string

#***********************************************************************************************************************

def addAnalogSignal2Block(blk, analogSignal):

    assert hasattr(analogSignal, 'name'), 'Analog signal has no name'

    data = blk.create_data_array(analogSignal.name, 'nix.regular_sampled', data=analogSignal.magnitude)



    data.unit = quUnitStr(analogSignal)
    data.label = analogSignal.name

    qu.set_default_units = 'SI'
    samplingPeriod = analogSignal.sampling_period.simplified
    t = data.append_sampled_dimension(float(samplingPeriod))
    t.label = 'time'
    t.unit = quUnitStr(samplingPeriod)
    t.offset = float(analogSignal.t_start.simplified)

    return data

#***********************************************************************************************************************

def dataArray2AnalogSignal(dataArray):

    for dim in dataArray.dimensions:

        if isinstance(dim, nix.SampledDimension):

            t_start = qu.Quantity(dim.offset, units=dim.unit)
            samplingPeriod = qu.Quantity(dim.sampling_interval, units=dim.unit)

            break


    analogSignal = neo.AnalogSignal(signal=dataArray[:],
                                    units=dataArray.unit,
                                    sampling_period=samplingPeriod,
                                    t_start=t_start)

    analogSignal.name = dataArray.name

    return analogSignal

#***********************************************************************************************************************

def property2qu(property):

    return qu.Quantity([v.value for v in property.values], units=property.unit)

#***********************************************************************************************************************

def addQuantity2section(sec, quant, name):

    if quant.shape == ():

        p = sec.create_property(name, [qu2Val(quant)])

    #only 1D arrays
    elif len(quant.shape) == 1:

        #not an empty 1D array
        if quant.shape[0]:

            p = sec.create_property(name, [qu2Val(x) for x in quant])

        else:
            raise(ValueError('Quantity passed must be either scalar or 1 dimensional'))

    else:
            raise(ValueError('Quantity passed must be either scalar or 1 dimensional'))

    p.unit = quUnitStr(quant)

    return p

#***********************************************************************************************************************

def createPosDA(name, pos, blk):

    positions = blk.create_data_array(name, 'nix.positions', data=pos)
    positions.append_set_dimension()
    positions.append_set_dimension()

    return positions

#***********************************************************************************************************************

def createExtDA(name, ext, blk):

    extents = blk.create_data_array(name, 'nix.extents', data=ext)
    extents.append_set_dimension()
    extents.append_set_dimension()

    return extents

#***********************************************************************************************************************

def tag2AnalogSignal(tag, refInd):

    ref = tag.references[refInd]
    dim = ref.dimensions[0]
    offset = dim.offset
    ts = dim.sampling_interval
    nSamples = ref[:].shape[0]

    startInd = max(0, int(np.floor((tag.position[0] - offset) / ts)))
    endInd = min(startInd + int(np.floor(tag.extent[0] / ts)) + 1, nSamples)
    trace = ref[startInd:endInd]

    analogSignal = neo.AnalogSignal(signal=trace,
                                    units=ref.unit,
                                    sampling_period=qu.Quantity(ts, units=dim.unit),
                                    t_start=qu.Quantity(offset + startInd * ts, units=dim.unit))

    # trace = tag.retrieve_data(refInd)[:]
    # tVec = tag.position[0] + np.linspace(0, tag.extent[0], trace.shape[0])

    return analogSignal

#***********************************************************************************************************************

def multiTag2SpikeTrain(tag, tStart, tStop):

    sp = neo.SpikeTrain(times=tag.positions[:], t_start=tStart, t_stop=tStop, units=tag.units[0])

    return sp

