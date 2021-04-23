# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import io
import os
import os.path as osp

# ---- Third party imports
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.widgets import AxesWidget
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import ScaledTranslation

from qtpy.QtGui import QImage
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QGridLayout, QAbstractSpinBox, QApplication, QDoubleSpinBox,
    QFileDialog, QLabel, QMessageBox, QScrollArea, QScrollBar,
    QSpinBox, QTabWidget, QWidget, QStyle, QFrame, QMainWindow,
    QGroupBox, QToolBar, QDoubleSpinBox)


# ---- Local imports
from gwhat.utils.icons import get_icon
from gwhat.utils.qthelpers import create_toolbutton


mpl.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Arial']})
LOCS = ['left', 'top', 'right', 'bottom']


COLORS = {'precip': [0/255, 25/255, 51/255],
          'recharge': [0/255, 76/255, 153/255],
          'runoff': [0/255, 128/255, 255/255],
          'evapo': [102/255, 178/255, 255/255]}


class ModelsDistplotWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(850, 450)
        self.setWindowTitle('Models Distribution')
        self.setWindowIcon(get_icon('models_dist'))

        self.setup()
        self.set_gluedf(None)

    def setup(self):
        """Setup the FigureStackManager withthe provided options."""
        self.figcanvas = ModelsDistplotCanvas()
        self.figcanvas.sig_rmse_treshold_selected.connect(
            self.set_rmse_treshold)

        ft = QApplication.instance().font()
        ft.setPointSize(ft.pointSize() - 1)

        # Models Info Group.
        self.models_label = QLabel()
        self.models_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.models_label.setTextFormat(Qt.RichText)
        self.models_label.setFont(ft)

        self.models_grpbox = QGroupBox("Models info")
        self.models_layout = QGridLayout(self.models_grpbox)
        self.models_layout.addWidget(self.models_label, 0, 0)
        self.models_layout.setRowStretch(1, 1)

        # Selected Models Info Group.
        rmse_cutoff_tooltip = (
            "RMSE cutoff value"
            "<br><br>"
            "The RMSE cutoff value is reprensented by a plain red vertical "
            "line on the graph. Cutoff models info are calculated from the "
            "family of models whose RMSE falls below that cutoff value."
            "<br><br>"
            "You can also select a new RMSE cutoff value by clicking "
            "with the left button of the mouse on the graph and you "
            "can clear the treshold by clicking with the right button."
            )
        self.rmse_cutoff_sbox = QDoubleSpinBox()
        self.rmse_cutoff_sbox.setDecimals(1)
        self.rmse_cutoff_sbox.setSingleStep(0.1)
        self.rmse_cutoff_sbox.setRange(0, 9999)
        self.rmse_cutoff_sbox.setValue(0)
        self.rmse_cutoff_sbox.setSpecialValueText('None')
        self.rmse_cutoff_sbox.setKeyboardTracking(False)
        self.rmse_cutoff_sbox.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.rmse_cutoff_sbox.valueChanged.connect(
            self._handle_rmse_treshold_changed)

        rmse_cutoff_widget = QWidget()
        rmse_cutoff_widget.setToolTip(rmse_cutoff_tooltip)

        ft = rmse_cutoff_widget.font()
        ft.setPointSize(ft.pointSize() - 1)
        rmse_cutoff_widget.setFont(ft)

        rmse_cutoff_layout = QGridLayout(rmse_cutoff_widget)
        rmse_cutoff_layout.setContentsMargins(2, 0, 0, 0)
        rmse_cutoff_layout.addWidget(QLabel('RMSE cutoff:'), 0, 0)
        rmse_cutoff_layout.addWidget(self.rmse_cutoff_sbox, 0, 1)
        rmse_cutoff_layout.addWidget(QLabel('mm'), 0, 2)

        self.selectmodels_label = QLabel()
        self.selectmodels_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse)
        self.selectmodels_label.setTextFormat(Qt.RichText)
        self.selectmodels_label.setFont(ft)

        self.selectmodels_grpbox = QGroupBox("Cutoff models info")
        self.selectmodels_layout = QGridLayout(self.selectmodels_grpbox)
        self.selectmodels_layout.addWidget(rmse_cutoff_widget, 0, 0)
        self.selectmodels_layout.addWidget(self.selectmodels_label, 1, 0)
        self.selectmodels_layout.setRowStretch(2, 1)
        self.selectmodels_layout.setSpacing(2)

        # Setup the central widget.
        self.central_widget = QWidget()
        self.central_layout = QGridLayout(self.central_widget)
        self.central_layout.addWidget(self.figcanvas, 0, 0, 3, 1)
        self.central_layout.addWidget(self.models_grpbox, 0, 1)
        self.central_layout.addWidget(self.selectmodels_grpbox, 1, 1)
        self.central_layout.setColumnStretch(0, 1)
        self.central_layout.setRowStretch(2, 1)
        self.setCentralWidget(self.central_widget)

        self.setup_toolbar()

    def setup_toolbar(self):
        """
        Setup the toolbar of this mainwindow.
        """
        self.setContextMenuPolicy(Qt.NoContextMenu)
        toolbar = QToolBar()
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar {spacing:1px; padding: 5px;}")
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.btn_copy_to_clipboard = create_toolbutton(
            self, icon='copy_clipboard',
            text="Copy",
            tip="Put a copy of the figure on the Clipboard.",
            triggered=self.figcanvas.copy_to_clipboard,
            shortcut='Ctrl+C')
        toolbar.addWidget(self.btn_copy_to_clipboard)

        # Setup the bins widget.
        self.bins_sbox = QDoubleSpinBox()
        self.bins_sbox.setDecimals(0)
        self.bins_sbox.setMaximum(999)
        self.bins_sbox.setMinimum(1)
        self.bins_sbox.setValue(30)
        self.bins_sbox.valueChanged.connect(self.figcanvas.figure.set_bins_nbr)

        bins_widget = QWidget()
        bins_widget.setToolTip("Number of equal-width bins in the range.")

        bins_layout = QGridLayout(bins_widget)
        bins_layout.setContentsMargins(5, 0, 0, 0)
        bins_layout.addWidget(QLabel('Bins nbr:'), 0, 0)
        bins_layout.addWidget(self.bins_sbox, 0, 1)

        toolbar.addWidget(bins_widget)

    def update_models_info(self):
        if self.glue_data is None:
            self.models_label.setText('')
            return

        rmse = self.glue_data['RMSE']
        cru = self.glue_data['params']['Cru']
        rasmax = self.glue_data['params']['RASmax']
        sy = self.glue_data['params']['Sy']
        text = (
            """
            Nbr of Models = {}<br><br>
            Ranges<br>---
            <table>
              <tr>
                <td>RMSE</td>
                <td>: </td>
                <td>{:0.1f} - {:0.1f} mm</td>
              </tr>
              <tr>
                <td>CRu</td>
                <td>: </td>
                <td>{:0.2f} - {:0.2f}</td>
              </tr>
              <tr>
                <td>RASmax</td>
                <td>: </td>
                <td>{:0.0f} - {:0.0f} mm</td>
              </tr>
              <tr>
                <td>Sy</td>
                <td>: </td>
                <td>{:0.3f} - {:0.3f}</td>
              </tr>
            </table>
            """).format(len(rmse),
                        np.min(rmse), np.max(rmse),
                        np.min(cru), np.max(cru),
                        np.min(rasmax), np.max(rasmax),
                        np.min(sy), np.max(sy))
        self.models_label.setText(text)

    def _handle_rmse_treshold_changed(self, value):
        value = None if value == 0 else value
        self.figcanvas.set_rmse_treshold(value)
        self.set_rmse_treshold(value)

    def set_rmse_treshold(self, rmse_treshold=None):
        if self.glue_data is None:
            self.selectmodels_label.setText('')
            self.rmse_cutoff_sbox.blockSignals(True)
            self.rmse_cutoff_sbox.setValue(0)
            self.rmse_cutoff_sbox.blockSignals(False)
            return
        else:
            self.rmse_cutoff_sbox.blockSignals(True)
            self.rmse_cutoff_sbox.setValue(
                0 if rmse_treshold is None else rmse_treshold)
            self.rmse_cutoff_sbox.blockSignals(False)

        # Update the left panel info.
        rmse_data = self.glue_data['RMSE']
        if rmse_treshold is None:
            rmse_treshold = np.max(rmse_data)

        where = np.where(rmse_data <= rmse_treshold)[0]
        selectmodels_text = (
            """
            <table style="width:100%">
              <tr>
                <td>Nbr of Models</td>
                <td>: </td>
                <td>{}</td>
              </tr>
              <tr>
                <td>Models %</td>
                <td>: </td>
                <td>{:0.1f}</td>
              </tr>
            </table>
            """
            ).format(len(where), len(where) / len(rmse_data) * 100)

        if len(where) > 0:
            rmse = self.glue_data['RMSE'][where]
            cru = self.glue_data['params']['Cru'][where]
            rasmax = self.glue_data['params']['RASmax'][where]
            sy = self.glue_data['params']['Sy'][where]
            selectmodels_text += (
                """
                <br><br>
                Ranges<br>---
                <table style="width:100%">
                  <tr>
                    <td>RMSE</td>
                    <td>: </td>
                    <td>{:0.1f} - {:0.1f} mm</td>
                  </tr>
                  <tr>
                    <td>CRu</td>
                    <td>: </td>
                    <td>{:0.2f} - {:0.2f}</td>
                  </tr>
                  <tr>
                    <td>RASmax</td>
                    <td>: </td>
                    <td>{:0.0f} - {:0.0f} mm</td>
                  </tr>
                  <tr>
                    <td>Sy</td>
                    <td>: </td>
                    <td>{:0.3f} - {:0.3f}</td>
                  </tr>
                </table>
                """
                ).format(np.min(rmse), np.max(rmse),
                         np.min(cru), np.max(cru),
                         np.min(rasmax), np.max(rasmax),
                         np.min(sy), np.max(sy))
        self.selectmodels_label.setText(selectmodels_text)

    def set_gluedf(self, glue_data):
        """Set the namespace for the GLUE results dataset."""
        self.glue_data = glue_data
        self.update_models_info()
        self.set_rmse_treshold(None)
        if glue_data is None:
            self.figcanvas.clear_figure()
        else:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.figcanvas.plot_results(glue_data)
            QApplication.restoreOverrideCursor()

    def show(self):
        """Qt method override."""
        if self.windowState() == Qt.WindowMinimized:
            self.setWindowState(Qt.WindowNoState)
        super().show()
        self.activateWindow()
        self.raise_()


class ModelsDistplotCanvas(FigureCanvasQTAgg):
    """
    """
    sig_rmse_treshold_selected = Signal(object)

    colors = {'dark grey': '0.65',
              'light grey': '0.85'}

    FWIDTH, FHEIGHT = 8.5, 5
    xlabel_size = 12

    def __init__(self, setp={}):
        super().__init__(ModelsDistplotFigure())

    def clear_figure(self):
        """Clear the whole figure."""
        pass

    def plot_results(self, glue_data):
        self.figure.plot(glue_data)

    def draw(self):
        """
        Override matplotlib method to handle the blitting of the cursors.
        """
        if self.figure.cursor is not None:
            self.figure.cursor.clear()

        super().draw()
        self.background = self.copy_from_bbox(self.figure.bbox)

        if self.figure.cursor is not None:
            self.figure.cursor.restore()

    def set_rmse_treshold(self, rmse_treshold):
        """Set the value of the RMSE treshold in the figure cursor."""
        if self.figure.cursor:
            self.figure.cursor.set_rmse_treshold(rmse_treshold)

    def copy_to_clipboard(self):
        """Put a copy of the figure on the clipboard."""
        buf = io.BytesIO()
        self.figure.savefig(buf, dpi=300)
        QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
        buf.close()


class ModelsDistplotCursor(AxesWidget):

    def __init__(self, ax, useblit=True):
        super().__init__(ax)
        self.infotextpad = 3
        self.infotextheight = 11

        self._selected_rmse_treshold = None
        self._cleared_rmse_treshold = False
        self.connect_event('motion_notify_event', self.onmove)
        self.connect_event('button_press_event', self.onpress)
        self.connect_event('button_release_event', self.onrelease)

        self.visible = True
        self.useblit = useblit and self.canvas.supports_blit

        self.linev = ax.axvline(
            ax.get_xbound()[1], visible=False, color='red', linewidth=1,
            ls='--', animated=self.useblit)

        self.treshold_vline = ax.axvline(
            ax.get_xbound()[1], visible=False, color='red', linewidth=1,
            animated=False)

        scaled_translation = ScaledTranslation(
            self.infotextpad/72, self.infotextpad/72,
            self.ax.figure.dpi_scale_trans)
        self.infotext = ax.text(
            0, 1, '', va='bottom', ha='left', rotation=0,
            fontsize=self.infotextheight,
            transform=ax.transAxes + scaled_translation
            )

    def update_infotext(self, xdata):
        glue_data = self.ax.figure.glue_data
        if glue_data is not None and xdata is not None:
            where = np.where(glue_data['RMSE'] <= xdata)[0]
            percent = len(where) / len(glue_data['RMSE']) * 100
            text = ("{} models ({:0.1f}%) have a RMSE less "
                    "than or equal to {:0.1f} mm.").format(
                        len(where), percent, xdata)
        else:
            text = ''
        self.infotext.set_text(text)

    def clear_rmse_treshold(self):
        """Clear the RMSE treshold vertical line."""
        self._selected_rmse_treshold = None
        self.draw_rmse_treshold()

    def set_rmse_treshold(self, value):
        """Set änd plot a new value for the RMSE treshold vertical line."""
        self._selected_rmse_treshold = value
        self.draw_rmse_treshold()

    def draw_rmse_treshold(self):
        """Draw the RMSE treshold vertical line."""
        if self._selected_rmse_treshold is not None:
            self.treshold_vline.set_xdata(
                (self._selected_rmse_treshold, self._selected_rmse_treshold))
            self.treshold_vline.set_visible(True)
        else:
            self.treshold_vline.set_visible(False)
        self.canvas.draw_idle()

    def clear(self):
        """
        Clear the cursor.

        This method must be called by the canvas BEFORE making a copy of
        the canvas background.
        """
        self.__linev_visible = self.linev.get_visible()
        self.__infotext_visible = self.infotext.get_visible()
        self.linev.set_visible(False)
        self.infotext.set_visible(False)

    def restore(self):
        """
        Restore the cursor.

        This method must be called by the canvas AFTER a copy has been made
        of the canvas background.
        """
        self.linev.set_visible(self.__linev_visible)
        self.infotext.set_visible(self.__infotext_visible)
        self.ax.draw_artist(self.linev)
        self.ax.draw_artist(self.infotext)

    def onpress(self, event):
        if event.button == 1:
            self._selected_rmse_treshold = event.xdata
        elif event.button == 3:
            self._cleared_rmse_treshold = True

    def onrelease(self, event):
        if event.button == 1:
            self.set_rmse_treshold(event.xdata)
            self.canvas.sig_rmse_treshold_selected.emit(
                self._selected_rmse_treshold)
        elif event.button == 3 and self._cleared_rmse_treshold is True:
            self._cleared_rmse_treshold = False
            self.clear_rmse_treshold()
            self.canvas.sig_rmse_treshold_selected.emit(None)

    def onmove(self, event):
        """Internal event handler to draw the cursor when the mouse moves."""
        if self.ignore(event):
            return
        if not self.canvas.widgetlock.available(self):
            return
        if not self.visible:
            return

        self.linev.set_xdata((event.xdata, event.xdata))
        self.update_infotext(event.xdata)

        self.linev.set_visible(self.visible)
        self.infotext.set_visible(self.visible and event.xdata)

        self._update()

    def _update(self):
        if self.useblit:
            if self.canvas.background is not None:
                self.canvas.restore_region(self.canvas.background)
            self.ax.draw_artist(self.linev)
            self.ax.draw_artist(self.infotext)
            self.canvas.blit()
        else:
            self.canvas.draw_idle()
        return False


class ModelsDistplotFigure(Figure):
    def __init__(self, bins_nbr=30):
        super().__init__()
        self.set_facecolor('white')
        self.set_tight_layout(True)
        self.setp = {
            'xlabel_size': 16,
            'ylabel_size': 16,
            'xtickslabel_size': 12,
            'ytickslabel_size': 12,
            'left_margin': None,
            'right_margin': None,
            'top_margin': None,
            'bottom_margin': None,
            'figure_border': 15
            }
        self.xlabelpad = 10
        self.ylabelpad = 10

        self.hist_obj = None
        self.glue_data = None
        self.cursor = None
        self.bins_nbr = bins_nbr

        self.setup_axes()

    def setup_axes(self):
        """Setup the axes of the figure."""
        self.ax0 = self.add_axes([0, 0, 1, 1])
        self.ax0.patch.set_visible(False)
        for axis in ['top', 'bottom', 'left', 'right']:
            self.ax0.spines[axis].set_linewidth(0.75)

        # Setup axe tick parameters.
        self.ax0.tick_params(
            axis='x', which='major', labelsize=self.setp['xtickslabel_size'])
        self.ax0.tick_params(
            axis='y', which='major', labelsize=self.setp['ytickslabel_size'])
        self.ax0.yaxis.set_major_locator(MaxNLocator(integer=True))

        # Setup axes labels.
        self.ax0.set_xlabel(
            'RMSE', fontsize=self.setp['xlabel_size'],
            labelpad=self.xlabelpad)
        self.ax0.set_ylabel(
            'Models', fontsize=self.setp['ylabel_size'],
            labelpad=self.ylabelpad)

    def setup_margins(self):
        """Setup the margins of the figure."""
        if self.ax0 is None:
            return
        figborderpad = self.setp['figure_border'] / 72 * self.dpi

        try:
            # This is required when saving the figure in some format like
            # pdf and svg.
            renderer = self.canvas.get_renderer()
        except AttributeError:
            self.canvas.draw()
            return

        figbbox = self.bbox
        ax = self.ax0
        axbbox = self.ax0.bbox

        bbox_xaxis_bottom, bbox_xaxis_top = (
            ax.xaxis.get_ticklabel_extents(renderer))
        bbox_yaxis_left, bbox_yaxis_right = (
            ax.yaxis.get_ticklabel_extents(renderer))

        bbox_yaxis_label = ax.yaxis.label.get_window_extent(renderer)
        bbox_xaxis_label = ax.xaxis.label.get_window_extent(renderer)

        # Calculate left margin width.
        left_margin = self.setp['left_margin']
        if left_margin is None:
            yaxis_width = axbbox.x0 - bbox_yaxis_left.x0
            ylabel_width = bbox_yaxis_label.width + self.ylabelpad
            left_margin = (
                yaxis_width + ylabel_width + (figborderpad)
                ) / figbbox.width

        # Calculate right margin width.
        right_margin = self.setp['right_margin']
        if right_margin is None:
            xaxis_width = max(
                bbox_xaxis_bottom.x1 - axbbox.x1,
                bbox_xaxis_top.x1 - axbbox.x1,
                0)
            right_margin = (xaxis_width + figborderpad) / figbbox.width

        # Calculate top margin height.
        top_margin = self.setp['top_margin']
        if top_margin is None:
            cursorinfotext_height = (
                self.cursor.infotextheight + self.cursor.infotextpad if
                self.cursor else 0
                )
            top_margin = (
                figborderpad + cursorinfotext_height
                ) / figbbox.height

        # Calculate bottom margin height.
        bottom_margin = self.setp['bottom_margin']
        if bottom_margin is None:
            xaxis_height = axbbox.y0 - bbox_xaxis_bottom.y0
            xlabel_height = bbox_xaxis_label.height + self.xlabelpad
            bottom_margin = (
                xaxis_height + xlabel_height + figborderpad
                ) / figbbox.height

        # Setup axe position.
        for ax in self.axes:
            ax.set_position([
                left_margin, bottom_margin,
                1 - left_margin - right_margin,
                1 - top_margin - bottom_margin])

    def plot(self, glue_data):
        """
        Generate the histogram plot using the RMSE values of the models stored
        in glue_data.
        """
        self.glue_data = glue_data
        self._draw_hist()
        if self.cursor is None:
            self.cursor = ModelsDistplotCursor(self.ax0)
        else:
            self.cursor.clear()
            self.canvas.sig_rmse_treshold_selected.emit(
                self.cursor._selected_rmse_treshold)
            self.canvas.draw_idle()

    def _draw_hist(self):
        """
        Draw the histogram of the models RMSE.
        """
        glue_rmse = self.glue_data['RMSE']

        self.ax0.set_visible(True)
        if self.hist_obj is not None:
            for patch in self.hist_obj:
                patch.remove()
        n, bins, self.hist_obj = self.ax0.hist(
            glue_rmse, color='blue', edgecolor='black', bins=self.bins_nbr)

        renderer = self.canvas.get_renderer()
        ax_bbox = self.ax0.yaxis.label.get_window_extent(renderer)

        bins_width = bins[1] - bins[0]
        self.ax0.axis(
            ymin=0,
            ymax=(ax_bbox.height * np.max(n)) / (ax_bbox.height - 3),
            xmin=bins[0] - bins_width / 2, xmax=bins[-1] + bins_width / 2,
            )

        self.canvas.draw()

    def tight_layout(self, force_update=False):
        """
        Override matplotlib method to setup the margins of the axes.
        """
        self.setup_margins()

    def set_size_inches(self, *args, **kargs):
        """
        Override matplotlib method to force a call to tight_layout when
        set_size_inches is called. This allow to keep the size of the margins
        fixed when the canvas of this figure is resized.
        """
        super().set_size_inches(*args, **kargs)
        self.tight_layout()

    def set_bins_nbr(self, bins_nbr):
        """
        Set the number of equal-width bins to plot in the histogram.
        """
        self.bins_nbr = int(bins_nbr)
        self._draw_hist()


if __name__ == '__main__':
    from gwhat.projet.reader_projet import ProjetReader
    from gwhat.utils.qthelpers import create_qapplication
    import sys
    fname = ("D:/OneDrive/INRS/2017 - Projet INRS PACC/"
             "Éval recharge (GWHAT)/evaluate_recharge/evaluate_recharge.gwt")

    project = ProjetReader(fname)
    wldset = project.get_wldset('Mercier_v2 (03090001)')
    glue_data = wldset.get_glue_at(-1)
    project.db.close()

    app = create_qapplication()

    distplotwidget = ModelsDistplotWidget()
    distplotwidget.show()
    distplotwidget.set_gluedf(glue_data)
    distplotwidget.set_gluedf(glue_data)

    sys.exit(app.exec_())
