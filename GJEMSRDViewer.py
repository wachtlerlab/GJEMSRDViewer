import sys
from PyQt4 import QtGui, QtCore
import os
from mplwidget import MatplotlibWidget
from rawDataImport import RawDataImporter
import quantities as qu
import numpy as np

class TitledText(QtGui.QGroupBox):

    def __init__(self, title, parent=None):

        QtGui.QGroupBox.__init__(self, title, parent)
        self.dirPathW = QtGui.QLineEdit()
        self.dirPathW.setReadOnly(True)
        self.dirPathW.setMaxLength(120)
        self.dirPathW.setMaximumHeight(30)
        self.dirPathW.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)

        hbox = QtGui.QHBoxLayout(self)
        hbox.addWidget(self.dirPathW)

        self.setLayout(hbox)

    def setText(self, str):
        self.dirPathW.setText(str)



class PathSelect(QtGui.QGroupBox):

    def getDir(self):

        pass

    def __init__(self, title, parent=None):

        QtGui.QGroupBox.__init__(self, title, parent)

        self.dirPathW = QtGui.QLineEdit()
        self.dirPathW.setMaxLength(100)
        self.dirPathW.setMaximumHeight(30)
        self.dirPathW.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        chooseDirPathB = QtGui.QPushButton('Select')
        chooseDirPathB.setMaximumHeight(30)
        chooseDirPathB.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.connect(chooseDirPathB, QtCore.SIGNAL('clicked()'), self.getDir)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.dirPathW)
        hbox.addWidget(chooseDirPathB)

        self.pathSet = False

        self.dirPathW.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        self.setMaximumHeight(60)

        self.setLayout(hbox)

    def raiseInfo(self, str):

        QtGui.QMessageBox.information(self.dirPathW, 'Warning!', str)

    def setText(self, str):

        if os.path.isdir(str) or os.path.isfile(str):
            self.dirPathW.setText(str)
        else:
            # self.raiseInfo('No such file or directory: ' + str)
            pass

class FileSelect(PathSelect):


    def getDir(self):

        filePath = QtGui.QFileDialog.getOpenFileName(self, 'Select ' + self.title(), os.getcwd(),
                                                         self.fileType)
        if filePath is None:
            self.raiseInfo('Invalid Selection! Please try again.')
        else:
            self.setText(filePath)


    def __init__(self, title, fileType, parent=None,):

        PathSelect.__init__(self, title, parent)
        self.fileType = fileType


class CentralWidget(QtGui.QWidget):

    def __init__(self, parent):

        QtGui.QWidget.__init__(self, parent)

        iconsFolder = parent.iconsFolder

        self.smrFileSelect = FileSelect('SMR File', 'SMR File( *.smr)')
        self.metaDataSelect = FileSelect('Metadata File', 'MS Excel File( *.xls *.xlsx)')

        fileSelectGrid = QtGui.QGridLayout()
        fileSelectGrid.addWidget(self.metaDataSelect, 0, 0)
        fileSelectGrid.addWidget(self.smrFileSelect, 0, 1)

        self.mplPlot = MatplotlibWidget(parent=self)
        prevButton = QtGui.QPushButton(QtGui.QIcon(os.path.join(iconsFolder, 'go-previous.png')), 'Previous', self)
        nextButton = QtGui.QPushButton(QtGui.QIcon(os.path.join(iconsFolder, 'go-next.png')), 'Next', self)
        self.connect(nextButton, QtCore.SIGNAL('clicked()'), self.plotNextInterval)
        self.connect(prevButton, QtCore.SIGNAL('clicked()'), self.plotPrevInterval)

        plotGrid = QtGui.QGridLayout()
        plotGrid.addWidget(prevButton, 0, 0)
        plotGrid.addWidget(self.mplPlot, 0, 1)
        plotGrid.addWidget(nextButton, 0, 2)



        calibGrid = QtGui.QGridLayout()

        self.voltCalib = TitledText('Voltage Calibrations')
        self.vibCalib = TitledText('Vibration Calibrations')


        calibGrid.addWidget(self.voltCalib, 0, 0)
        calibGrid.addWidget(self.vibCalib, 0, 1)


        vbox = QtGui.QVBoxLayout()
        vbox.stretch(1)
        vbox.addLayout(fileSelectGrid)
        vbox.addLayout(plotGrid)
        vbox.addLayout(calibGrid)

        self.setLayout(vbox)

    def showData(self):



        self.rdi = RawDataImporter(str(self.smrFileSelect.dirPathW.text()),
                                   str(self.metaDataSelect.dirPathW.text()),
                                   'Sheet1')

        vibCalib = self.rdi.dataBlock.segments[0].eventarrays[1].annotations['extra_labels']
        self.vibCalib.setText(str(vibCalib.tolist()))
        voltCalib = self.rdi.dataBlock.segments[0].eventarrays[0].annotations['extra_labels']
        self.voltCalib.setText(str(voltCalib.tolist()))


        self.rdi.parseSpike2Data()
        tStart = self.rdi.vibrationSignal.t_start
        tStart.units = qu.s
        tStop = self.rdi.vibrationSignal.t_stop
        tStop.units = qu.s

        self.epochStarts = np.linspace(tStart.magnitude, tStop.magnitude, 20) * qu.s
        self.intInd = 0

        self.draw()


    def draw(self):
        self.rdi.plotVibEpoch(self.mplPlot.axes, [self.epochStarts[self.intInd], self.epochStarts[self.intInd + 1]])
        self.mplPlot.draw()

    def plotNextInterval(self):

        if self.intInd < len(self.epochStarts) - 1:
            self.intInd += 1

            self.draw()

    def plotPrevInterval(self):

        if self.intInd > 0:
            self.intInd -= 1

            self.draw()



class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.iconsFolder = os.path.join(os.path.dirname(sys.executable), 'icons')

        self.initUI()

    def initUI(self):

        self.statusBar().showMessage('Ready')

        self.resizeAndCenter()



        self.setWindowTitle('GinJang Data Viewer')
        self.setWindowIcon(QtGui.QIcon(os.path.join(self.iconsFolder, 'LogoGJ.png')))

        exit = QtGui.QAction(QtGui.QIcon(os.path.join(self.iconsFolder, 'cancel.png')), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        toolbar = self.addToolBar('ToolBar')
        toolbar.addAction(exit)

        self.centralW = CentralWidget(self)
        self.setCentralWidget(self.centralW)

        showData = QtGui.QAction(QtGui.QIcon(os.path.join(self.iconsFolder, 'dialog-apply.png')), 'Show Data', self)
        showData.setShortcut('F5')
        showData.setStatusTip('Show data from the selected files')
        self.connect(showData, QtCore.SIGNAL('triggered()'), self.centralW.showData)

        toolbar.addAction(showData)


        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(showData)

        file.addAction(exit)



    def resizeAndCenter(self):

        screen = QtGui.QDesktopWidget().screenGeometry()
        self.resize(screen.width() / 2.0, screen.height() / 2.0)
        size = self.geometry()
        self.move((screen.width() - size.width())/2, (screen.height() - size.height())/2)





    def closeEvent(self, event):

        reply = QtGui.QMessageBox.question(self, 'Message',
                                            "Are you sure to quit?", QtGui.QMessageBox.Yes |
                                            QtGui.QMessageBox.No, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():

    app = QtGui.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()