from rawDataImport import RawDataViewer
from matplotlib import pyplot as plt
import quantities as qu


def test_load_basic():
    """
    Testing the load function
    """

    testFile = "tests/testFiles/140813-3Al.smr"

    rdi = RawDataViewer(testFile,
                             forceUnits=True,
                             voltageCalibStr='20',
                             ints2Exclude=None
                             )
    tStart = max(rdi.vibrationSignal.t_start, rdi.voltageSignal.t_start)
    if rdi.currentSignal is not None:
        tStart = max(tStart, rdi.currentSignal.t_start)
    tStart.units = qu.s
    epochWidth = 20 * qu.s

    fig, ax = plt.subplots(figsize=(14, 11.2))
    rdi.plotVibEpoch(ax=ax, epochTimes=[tStart, tStart + epochWidth])
    assert True