# Modified version of the file 'mplwidget.py' on http://wiki.scipy.org/Cookbook/Matplotlib/Qt_with_IPython_and_Designer
# Ajayrama Kumaraswamy, 25. 09. 2015

from PyQt4 import QtGui, QtCore

import matplotlib
matplotlib.use('Agg')
import numpy as np

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MatplotlibWidget(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, name=None, width=5, height=4, dpi=100, bgcolor=None):

        self.parent = parent
        if self.parent:
            bgc = parent.palette().color(QtGui.QPalette.Background)
            bgcolor = float(bgc.red())/255.0, float(bgc.green())/255.0, float(bgc.blue())/255.0
            #bgcolor = "#%02X%02X%02X" % (bgc.red(), bgc.green(), bgc.blue())

            self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=bgcolor, edgecolor=bgcolor)
            self.axes = self.fig.add_subplot(111)

            self.compute_initial_figure()

            FigureCanvas.__init__(self, self.fig)
            self.setParent(parent)

            FigureCanvas.setSizePolicy(self,
                                       QtGui.QSizePolicy.Expanding,
                                       QtGui.QSizePolicy.Expanding)
            FigureCanvas.updateGeometry(self)

    def sizeHint(self):
        w = self.fig.get_figwidth()
        h = self.fig.get_figheight()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        return QtCore.QSize(10, 10)

    def compute_initial_figure(self):
        t = np.arange(0.0, 3.0, 0.01)
        s = np.sin(2*np.pi*t)
        self.axes.plot(t, s)







