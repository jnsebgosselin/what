# -*- coding: utf-8 -*-

# Copyright © 2014-2018 GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.

# ---- Standard library imports


# ---- Imports: third parties

import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure as MPLFigure


from PyQt5.QtCore import Qt, QSize
from PyQt5.QtCore import pyqtSignal as QSignal
from PyQt5.QtWidgets import (
    QGridLayout, QApplication, QComboBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QLabel, QTabWidget, QToolBar, QWidget)


# ---- Imports: local

from gwhat.gwrecharge.gwrecharge_calc2 import calcul_glue
from gwhat.gwrecharge.gwrecharge_calc2 import calcul_glue_yearly_rechg
from gwhat.common import icons, QToolButtonNormal
from gwhat.mplFigViewer3 import ImageViewer

mpl.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Arial']})
LOCS = ['left', 'top', 'right', 'bottom']
LANGUAGES = ['French', 'English']


class FigureStackManager(QWidget):
    def __init__(self, parent=None):
        super(FigureStackManager, self).__init__(parent)
        self.setMinimumSize(1250, 650)
        self.setWindowTitle('Recharge Results')
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowIcon(icons.get_icon('master'))

        self.setup()

    def setup(self):
        """Setup the FigureStackManager withthe provided options."""
        self.setup_stack()
        layout = QGridLayout(self)
        layout.addWidget(self.stack, 0, 0)

    def setup_stack(self):
        self.fig_wl_glue = FigManagerWaterLevelGLUE(self)
        self.fig_rechg_glue = FigManagerRechgGLUE(self)

        self.stack = QTabWidget()
        self.stack.addTab(self.fig_wl_glue, 'Hydrograph')
        self.stack.addTab(self.fig_rechg_glue, 'Recharge')

    def plot_results(self, glue_data):
        self.fig_wl_glue.plot_prediction(glue_data)
        self.fig_rechg_glue.plot_recharge(glue_data)


# ---- Figure Managers

class NavigationToolbar(NavigationToolbar2QT):
    # Only display the buttons that we want.
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom', 'Save')]

    def __init__(self, *args, **kwargs):
        self.icon_names = {'home.png': 'home',
                           'move.png': 'pan',
                           'zoom_to_rect.png': 'search',
                           'filesave.png': 'save'}
        super(NavigationToolbar, self).__init__(*args, **kwargs)
        self.setIconSize(QSize(28, 28))

    def _icon(self, name):
        """Matplotlib method override."""
        if name in list(self.icon_names.keys()):
            icon = icons.get_icon(self.icon_names[name])
            return icon
        else:
            return super(NavigationToolbar, self)._icon(name)

    def sizeHint(self):
        """
        Matplotlib method override because the toolbar height is too big
        otherwise.
        """
        return super(NavigationToolbar2QT, self).sizeHint()


class FigManagerBase(QDialog):
    """
    Abstract manager to show the results from GLUE.
    """
    def __init__(self, figure_class, parent=None):
        super(FigManagerBase, self).__init__(parent)
        self.setFixedSize(1000, 550)
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowMinimizeButtonHint |
                            Qt.WindowCloseButtonHint)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowIcon(icons.get_icon('master'))

        self.figure = figure_class()
        self.toolbar = NavigationToolbar(self.figure, parent=self)

        layout = QGridLayout(self)
        layout.addWidget(self.toolbar, 0, 0)
        layout.addWidget(self.figure, 1, 0)


class FigManagerWaterLevelGLUE(FigManagerBase):
    """
    Figure manager with toolbar to show the results for the predicted
    water level versus the observations.
    """
    def __init__(self, parent=None):
        super(FigManagerWaterLevelGLUE, self).__init__(FigWaterLevelGLUE,
                                                       parent)

    def plot_prediction(self, glue_data):
        self.figure.plot_prediction(glue_data)


class FigManagerRechgGLUE(FigManagerBase):
    """
    Figure manager with a toolbar to show the results for the yearly
    ground-water recharge and its uncertainty evaluated with GLUE.
    """
    def __init__(self, parent=None):
        super(FigManagerRechgGLUE, self).__init__(FigYearlyRechgGLUE, parent)

    def plot_recharge(self, data, Ymin0=None, Ymax0=None, yrs_range=None):
        self.figure.plot_recharge(data, Ymin0, Ymax0, yrs_range)


# ---- Figure Canvas

class FigCanvasBase(FigureCanvasQTAgg):
    """
    This is the base figure format to plot GLUE results.
    """
    sig_fig_changed = QSignal(MPLFigure)

    colors = {'dark grey': '0.65',
              'light grey': '0.85'}

    FWIDTH, FHEIGHT = 8.5, 5
    MARGINS = [1, 0.15, 0.15, 0.65]  # left, top, right, bottom

    def __init__(self, language='English'):
        super(FigCanvasBase, self).__init__(mpl.figure.Figure())

        self.language = language

        self.figure.set_size_inches(self.FWIDTH, self.FHEIGHT)
        self.figure.patch.set_facecolor('white')

        self.ax0 = ax0 = self.figure.add_axes([0, 0, 1, 1])
        self.set_axes_margins_inches(self.MARGINS)
        ax0.patch.set_visible(False)
        for axis in ['top', 'bottom', 'left', 'right']:
            ax0.spines[axis].set_linewidth(0.5)

    def set_axes_margins_inches(self, margins):
        """Set the margins of the figure axes in inches."""
        fheight = self.figure.get_figheight()
        fwidth = self.figure.get_figwidth()

        left = margins[0]/fwidth
        top = margins[1]/fheight
        right = margins[2]/fwidth
        bottom = margins[3]/fheight

        self.ax0.set_position([left, bottom, 1-left-right, 1-top-bottom])

        self.sig_fig_changed.emit(self.figure)

    def set_fig_size(self, fw, fh, units='IP'):
        """
        Set the figure width and height in inches if units is IP
        or in cm if units is SI.
        """
        if units == 'SI':
            # Convert values from cm to in.
            fw = fw / 2.54
            fh = fh / 2.54
        self.figure.set_size_inches(fw, fh)
        self.sig_fig_changed.emit(self.figure)

    def set_fig_language(self, language):
        """
        Set the language of the text shown in the figure. This needs to be
        impemented in the derived class.
        """
        pass


class FigWaterLevelGLUE(FigCanvasBase):
    """
    This is a graph that shows observed ground-water levels and GLUE 5/95
    predicted water levels.
    """

    def __init__(self, *args, **kargs):
        super(FigWaterLevelGLUE, self).__init__(*args, **kargs)
        fig = self.figure

        ax = self.ax0

        # ---- Axes labels

        self.set_axes_labels()

        # ---- Grids

        ax.grid(axis='x', color='0.35', ls=':', lw=1, zorder=200)
        ax.grid(axis='y', color='0.35', ls=':', lw=1, zorder=200)
        ax.invert_yaxis()

        # ----- Plot Observation

        self.plot_wlobs, = ax.plot([], [], color='b', ls='None',
                                   marker='.', ms=3, zorder=100)
        fig.canvas.draw()

        # ---- Yticks format

        ax.yaxis.set_ticks_position('left')
        ax.tick_params(axis='y', direction='out', labelsize=12)

        # ---- Xticks format

        ax.xaxis.set_ticks_position('bottom')
        ax.tick_params(axis='x', direction='out')
        fig.autofmt_xdate()

        # ---- Legend

        dum1 = mpl.patches.Rectangle((0, 0), 1, 1, fc='0.85', ec='0.65')
        dum2, = ax.plot([], [], color='b', ls='None', marker='.', ms=10)

        lg_handles = [dum2, dum1]
        lg_labels = ['Observations', 'GLUE 5/95']

        ax.legend(lg_handles, lg_labels, ncol=2, fontsize=12, frameon=False,
                  numpoints=1)

    def plot_prediction(self, glue_data):
        glue_dly = calcul_glue(glue_data, [0.05, 0.95], varname='hydrograph')

        dates, wlobs = glue_data['wl_date'], glue_data['wl_obs']
        ax = self.figure.axes[0]
        self.plot_wlobs.set_xdata(dates)
        self.plot_wlobs.set_ydata(wlobs)
        ax.fill_between(dates, glue_dly[:, -1]/1000, glue_dly[:, 0]/1000,
                        facecolor='0.85', lw=1, edgecolor='0.65', zorder=0)

    def set_fig_language(self, language):
        """
        Set the language of the text shown in the figure.
        """
        self.language = language
        self.set_axes_labels()
        self.sig_fig_changed.emit(self.figure)

    def set_axes_labels(self):
        """
        Set the text and position of the axes labels.
        """
        if self.language == 'French':
            xlabel = "Niveau d'eau (m sous la surface)"
        else:
            xlabel = 'Water Level (mbgs)'
        self.ax0.set_ylabel(xlabel, fontsize=16, labelpad=20)


class FigYearlyRechgGLUE(FigCanvasBase):
    """
    This is a graph that shows annual ground-water recharge and its
    uncertainty.
    """

    MARGINS = [1, 0.15, 0.15, 1.1]  # left, top, right, bottom

    def __init__(self, *args, **kargs):
        super(FigYearlyRechgGLUE, self).__init__(*args, **kargs)

        # ---- Customize Ax0

        self.ax0.set_axisbelow(True)

    def plot_recharge(self, data, Ymin0=None, Ymax0=None, year_limits=None):
        fig = self.figure
        ax0 = self.ax0

        p = [0.05, 0.25, 0.5, 0.75, 0.95]
        year_labels, year_range, glue_rechg_yr = calcul_glue_yearly_rechg(
                data, p, year_limits)

        max_rechg_yrly = glue_rechg_yr[:, -1]
        min_rechg_yrly = glue_rechg_yr[:, 0]
        prob_rechg_yrly = glue_rechg_yr[:, 2]
        glue25_yr = glue_rechg_yr[:, 1]
        glue75_yr = glue_rechg_yr[:, -2]

        # ---- Axis range

        Xmin0 = min(year_range)-1
        Xmax0 = max(year_range)+1

        if Ymax0 is None:
            Ymax0 = np.max(max_rechg_yrly) + 50
        if Ymin0 is None:
            Ymin0 = 0

        # ---- Xticks format

        ax0.xaxis.set_ticks_position('bottom')
        ax0.tick_params(axis='x', direction='out', pad=1)
        ax0.set_xticks(year_range)
        ax0.xaxis.set_ticklabels(year_labels, rotation=45, ha='right')

        # ----- ticks format

        scale_yticks = 25 if np.max(max_rechg_yrly) < 250 else 100
        scale_yticks_minor = 5 if np.max(max_rechg_yrly) < 250 else 25
        yticks = np.arange(0, 2*Ymax0+1, scale_yticks)

        ax0.yaxis.set_ticks_position('left')
        ax0.set_yticks(yticks)
        ax0.tick_params(axis='y', direction='out', gridOn=True, labelsize=12)
        ax0.grid(axis='y', color=[0.35, 0.35, 0.35], linestyle=':',
                 linewidth=0.5, dashes=[0.5, 5])

        ax0.set_yticks(np.arange(0, 2*Ymax0, scale_yticks_minor), minor=True)
        ax0.tick_params(axis='y', direction='out', which='minor', gridOn=False)

        # ---- Axis range

        ax0.axis([Xmin0, Xmax0, Ymin0, Ymax0])

        # ---- Plot results

        ax0.plot(year_range, prob_rechg_yrly, ls='--', color='0.35',
                 zorder=100)

        yerr = [prob_rechg_yrly-min_rechg_yrly, max_rechg_yrly-prob_rechg_yrly]
        herr = ax0.errorbar(year_range, prob_rechg_yrly, yerr=yerr,
                            fmt='o', capthick=1, capsize=4, ecolor='0',
                            elinewidth=1, mfc='White', mec='0', ms=5,
                            markeredgewidth=1, zorder=200)

        h25 = ax0.plot(year_range, glue25_yr, color='red',
                       dashes=[3, 5], alpha=0.65)
        ax0.plot(year_range, glue75_yr, color='red', dashes=[3, 5], alpha=0.65)

        # ---- Axes labels

        self.set_axes_labels()

        # ----- Legend

        lg_handles = [herr[0], herr[1], h25[0]]
        lg_labels = ['Recharge (GLUE 50)', 'Recharge (GLUE 5/95)',
                     'Recharge (GLUE 25/75)']

        ax0.legend(lg_handles, lg_labels, ncol=3, fontsize=12, frameon=False,
                   numpoints=1, loc='upper left')

        # ---- Averages Text

        if self.language.lower() == 'french':
            text = 'Recharge annuelle moyenne :\n'
            text += '(GLUE 5) %d mm/a ; ' % np.mean(min_rechg_yrly)
            text += '(GLUE 25) %d mm/a ; ' % np.mean(glue25_yr)
            text += '(GLUE 50) %d mm/a ; ' % np.mean(prob_rechg_yrly)
            text += '(GLUE 75) %d mm/a ; ' % np.mean(glue75_yr)
            text += '(GLUE 95) %d mm/a' % np.mean(max_rechg_yrly)
        else:
            text = 'Mean annual recharge :\n'
            text += '(GLUE 5) %d mm/y ; ' % np.mean(min_rechg_yrly)
            text += '(GLUE 25) %d mm/y ; ' % np.mean(glue25_yr)
            text += '(GLUE 50) %d mm/y ; ' % np.mean(prob_rechg_yrly)
            text += '(GLUE 75) %d mm/y ; ' % np.mean(glue75_yr)
            text += '(GLUE 95) %d mm/y' % np.mean(max_rechg_yrly)

        dx, dy = 5/72, 5/72
        padding = mpl.transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
        transform = ax0.transAxes + padding
        ax0.text(0, 0, text, va='bottom', ha='left', fontsize=10,
                 transform=transform)

    def set_fig_language(self, language):
        """
        Set the language of the text shown in the figure.
        """
        self.language = language
        self.set_axes_labels()
        self.sig_fig_changed.emit(self.figure)

    def set_axes_labels(self):
        """
        Set the text and position of the axes labels.
        """
        if self.language.lower() == 'french':
            ylabl = "Recharge annuelle (mm/a)"
            xlabl = ("Années Hydrologiques (1er octobre d'une année "
                     "au 30 septembre de la suivante)")
        else:
            ylabl = "Annual Recharge (mm/y)"
            xlabl = ("Hydrological Years (October 1st of one "
                     "year to September 30th of the next)")
        self.ax0.set_ylabel(ylabl, fontsize=16, labelpad=15)
        self.ax0.set_xlabel(xlabl, fontsize=16, labelpad=20)


# %% ---- if __name__ == '__main__'

if __name__ == '__main__':
    from gwhat.gwrecharge.gwrecharge_calc2 import RechgEvalWorker
    import sys

    app = QApplication(sys.argv)

    rechg_worker = RechgEvalWorker()
    data = rechg_worker.load_glue_from_npy("..\GLUE.npy")

    glue_wl_viewer = FigManagerWaterLevelGLUE()
    glue_wl_viewer.plot_prediction(data)
    glue_wl_viewer.show()

    fig_rechg_glue = FigManagerRechgGLUE()
    fig_rechg_glue.plot_recharge(data)
    fig_rechg_glue.show()

    sys.exit(app.exec_())
