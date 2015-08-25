from rawDataImport import RawDataImporter
import matplotlib.pyplot as plt
import ipdb
import quantities as qu
import numpy as np
import sys



assert len(sys.argv) == 4, 'Improper Usage! Please use as follows:\npython checkCalib.py <smr file> <metadata excel file>'
smrFile = sys.argv[1]
excelFile = sys.argv[2]
excelSheet = 'Sheet1'
see = RawDataImporter(smrFile, excelFile,excelSheet)
see.parseSpike2Data()
tStart = see.vibrationSignal.t_start
tStart.units = qu.s
tStop = see.vibrationSignal.t_stop
tStop.units = qu.s

ts = np.linspace(tStart, tStop, 20)

for ind in range(len(ts) - 1):

    see.plotVibEpoch([ts[ind].magnitude, ts[ind + 1].magnitude])
    ipdb.set_trace()
    plt.close()


