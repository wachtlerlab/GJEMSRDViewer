import sys
from PyQt4 import QtGui, QtCore
import os
from mplwidget import MatplotlibWidget
from rawDataImport import RawDataViewer
import quantities as qu

mplPars = {
           'axes.labelsize': 'large',
           'axes.titlesize': 16,
           # 'font.family': 'sans-serif', 
           # 'font.sans-serif': 'computer modern roman',
           'font.size': 16,
           'font.weight': 'black',
           'xtick.labelsize': 14,
           'ytick.labelsize': 14,
           'legend.fontsize': 12,
           }



class TitledText(QtGui.QGroupBox):

    def __init__(self, title, parent=None):

        QtGui.QGroupBox.__init__(self, title, parent)
        self.line = QtGui.QLineEdit()
        self.line.setMaxLength(120)
        self.line.setMaximumHeight(30)
        self.line.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)

        hbox = QtGui.QHBoxLayout(self)
        hbox.addWidget(self.line)

        self.setLayout(hbox)

    def setText(self, str):
        self.line.setText(str)

    def raiseInfo(self, str):

        QtGui.QMessageBox.information(self.line, 'Warning!', str)



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

        fileSelectGrid = QtGui.QGridLayout()

        fileSelectGrid.addWidget(self.smrFileSelect, 0, 0)

        self.startW = TitledText('Start time in s')
        self.endW = TitledText('End time in s')

        startstopGrid = QtGui.QGridLayout()
        startstopGrid.addWidget(self.startW, 0, 0)
        startstopGrid.addWidget(self.endW, 0, 1)

        self.vCalib = TitledText("Voltage Calibration Entry")
        self.ints2Exclude = TitledText("Intervals to Exclude Entry")
        calibrationExclGrid = QtGui.QGridLayout()
        calibrationExclGrid.addWidget(self.vCalib, 0, 0)
        calibrationExclGrid.addWidget(self.ints2Exclude, 0, 1)

        self.mplPlot = MatplotlibWidget(parent=self, mplPars=mplPars)
        prevButton = QtGui.QPushButton(QtGui.QIcon(os.path.join(iconsFolder, 'go-previous.png')), 'Previous', self)
        nextButton = QtGui.QPushButton(QtGui.QIcon(os.path.join(iconsFolder, 'go-next.png')), 'Next', self)
        self.connect(nextButton, QtCore.SIGNAL('clicked()'), self.plotNextInterval)
        self.connect(prevButton, QtCore.SIGNAL('clicked()'), self.plotPrevInterval)

        plotGrid = QtGui.QGridLayout()
        plotGrid.addWidget(prevButton, 0, 0)
        plotGrid.addWidget(self.mplPlot, 0, 1)
        plotGrid.addWidget(nextButton, 0, 2)

        vbox = QtGui.QVBoxLayout()
        vbox.stretch(1)
        vbox.addLayout(fileSelectGrid)
        vbox.addLayout(startstopGrid)
        vbox.addLayout(calibrationExclGrid)
        vbox.addLayout(plotGrid)

        self.setLayout(vbox)

    def load(self):

        vCalibStr = str(self.vCalib.line.text())
        if vCalibStr == '':
            vCalibStr = "20"

        ints2Excl = str(self.ints2Exclude.line.text())
        if ints2Excl == '':
            ints2Excl = None
        self.rdi = RawDataViewer(str(self.smrFileSelect.dirPathW.text()),
                                 forceUnits=True,
                                 voltageCalibStr=vCalibStr,
                                 ints2Exclude=ints2Excl
                                 )
        tStart = min(self.rdi.vibrationSignal.t_start, self.rdi.voltageSignal.t_start)
        if self.rdi.currentSignal is not None:
            tStart = min(tStart, self.rdi.currentSignal.t_start)
        tStart.units = qu.s

        self.presentPlotStart = tStart
        self.epochWidth = 20 * qu.s

        self.draw(self.presentPlotStart, self.presentPlotStart + self.epochWidth)

    def refresh(self):

        if not hasattr(self, 'rdi'):
            self.startW.raiseInfo('Please load the data first')

        else:

            startText = self.startW.line.text()
            endText = self.endW.line.text()

            if not startText:
                self.startW.raiseInfo('Please enter a valid starting time.')
            elif not endText:
                self.endW.raiseInfo('Please enter a valid ending time')
            else:
                startTime = float(startText) * qu.s
                endTime = float(endText) * qu.s
                if startTime < self.rdi.vibrationSignal.t_start:
                    self.startW.raiseInfo('Signal Starts at ' + str(self.rdi.vibrationSignal.t_start)
                                          +'. Please enter valid start value.' )
                elif endTime > self.rdi.vibrationSignal.t_stop:
                    self.startW.raiseInfo('Signal End at ' + str(self.rdi.vibrationSignal.t_stop)
                                          +'. Please enter valid end value.')
                elif endTime == startTime:
                    self.startW.raiseInfo('Error: Start and End times are same')
                else:
                    self.draw(startTime, endTime)

                    self.epochWidth = endTime - startTime
                    self.presentPlotStart = startTime

    def draw(self, start=None, end=None):

        if start:
            self.presentPlotStart = start
        self.mplPlot.axes.clear()
        self.rdi.plotVibEpoch(self.mplPlot.axes, [start, end])
        self.mplPlot.draw()

    def plotNextInterval(self):

        if self.presentPlotStart + 2 * self.epochWidth <= self.rdi.voltageSignal.t_stop:

            self.draw(self.presentPlotStart + self.epochWidth, self.presentPlotStart + 2 * self.epochWidth)

    def plotPrevInterval(self):

        if self.presentPlotStart - self.epochWidth >= self.rdi.voltageSignal.t_start:

            self.draw(self.presentPlotStart - self.epochWidth, self.presentPlotStart)



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

        loadData = QtGui.QAction(QtGui.QIcon(os.path.join(self.iconsFolder, 'document-save.png')), 'Load Data', self)
        loadData.setShortcut('F4')
        loadData.setStatusTip('Load data from the selected files')
        self.connect(loadData, QtCore.SIGNAL('triggered()'), self.centralW.load)

        toolbar.addAction(loadData)

        refresh = QtGui.QAction(QtGui.QIcon(os.path.join(self.iconsFolder, 'dialog-apply.png')), 'Refresh plot', self)
        refresh.setShortcut('F5')
        refresh.setStatusTip('Refresh plot according to start stop times entered')
        self.connect(refresh, QtCore.SIGNAL('triggered()'), self.centralW.refresh)

        toolbar.addAction(refresh)


        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(loadData)
        file.addAction(refresh)

        file.addAction(exit)



    def resizeAndCenter(self):

        screen = QtGui.QDesktopWidget().screenGeometry()
        self.resize(screen.width() / 2.0, screen.height() / 2.0)
        size = self.geometry()
        self.move((screen.width() - size.width())/2, (screen.height() - size.height())/2)





    def closeEvent(self, event):

        reply = QtGui.QMessageBox.question(self, 'Message',
                                            "Really quit?", QtGui.QMessageBox.Yes |
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
