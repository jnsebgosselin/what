# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Stantard imports
import time
import os.path as osp

# ---- Third party imports
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtCore import pyqtSlot as QSlot
from PyQt5.QtCore import pyqtSignal as QSignal
from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton, QProgressBar,
                             QLabel, QSizePolicy, QScrollArea, QApplication,
                             QMessageBox, QFrame, QCheckBox, QGroupBox)

# ---- Local imports
from gwhat.widgets.buttons import ExportDataButton
from gwhat.common.widgets import QDoubleSpinBox
from gwhat.widgets.layout import HSep
from gwhat.gwrecharge.gwrecharge_calc2 import RechgEvalWorker
from gwhat.gwrecharge.gwrecharge_plot_results import FigureStackManager
from gwhat.gwrecharge.glue import GLUEDataFrameBase
from gwhat.gwrecharge.models_distplot import ModelsDistplotWidget
from gwhat.utils.icons import QToolButtonSmall, get_iconsize, get_icon
from gwhat.utils.qthelpers import create_toolbutton


class RechgEvalWidget(QFrame):

    sig_new_gluedf = QSignal(GLUEDataFrameBase)

    def __init__(self, parent=None):
        super(RechgEvalWidget, self).__init__(parent)
        self.setWindowTitle('Recharge Calibration Setup')
        self.setWindowFlags(Qt.Window)

        self.wxdset = None
        self.wldset = None
        self.figstack = FigureStackManager()

        self.progressbar = QProgressBar()
        self.progressbar.setValue(0)
        self.progressbar.hide()
        self.__initUI__()

        # Set the worker and thread mechanics
        self.rechg_worker = RechgEvalWorker()
        self.rechg_worker.sig_glue_finished.connect(self.receive_glue_calcul)
        self.rechg_worker.sig_glue_progress.connect(self.progressbar.setValue)

        self.rechg_thread = QThread()
        self.rechg_worker.moveToThread(self.rechg_thread)
        self.rechg_thread.started.connect(self.rechg_worker.eval_recharge)

    def __initUI__(self):

        class QRowLayout(QWidget):
            def __init__(self, items, parent=None):
                super(QRowLayout, self).__init__(parent)

                layout = QGridLayout()
                for col, item in enumerate(items):
                    layout.addWidget(item, 0, col)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setColumnStretch(0, 100)
                self.setLayout(layout)

        class QLabelCentered(QLabel):
            def __init__(self, text):
                super(QLabelCentered, self).__init__(text)
                self.setAlignment(Qt.AlignCenter)

        # Setup the maximum readily available water range (RASmax).
        rasmax_label = QLabel('RASmax:')

        self.QRAS_min = QDoubleSpinBox(5)
        self.QRAS_min.setRange(0, 999)

        rasmax_label2 = QLabelCentered('to')

        self.QRAS_max = QDoubleSpinBox(40)
        self.QRAS_max.setRange(0, 999)

        rasmax_label3 = QLabel('mm')

        # Setup the Specific yield cutoff range.
        syrange_tooltip = (
            """
            <b>Specific yield (Sy) range</b>
            <br><br>
            Only models with an estimated specific yield  that falls inside
            this range of values are retained as behavioural.
            <br><br>
            According to Meinzer (1923), the <b>specific yield</b> is the
            ratio of the volume of water a rock or soil yield by gravity
            after being saturated to its own volume.
            """
            )

        self.sy_label = QLabel('Sy:')
        self.sy_label.setToolTip(syrange_tooltip)

        self.QSy_min = QDoubleSpinBox(0.05, 3)
        self.QSy_min.setRange(0.001, 1)
        self.QSy_min.setToolTip(syrange_tooltip)

        sy_range_label2 = QLabelCentered('to')
        sy_range_label2.setToolTip(syrange_tooltip)

        self.QSy_max = QDoubleSpinBox(0.2, 3)
        self.QSy_max.setRange(0.001, 1)
        self.QSy_max.setToolTip(syrange_tooltip)

        # Setup the runoff coefficient (Cro) range.
        cro_tooltip = (
            """
            The runoff coefficient (Cro) is a dimensionless coefficient
            relating the amount of runoff to the amount of precipitation
            received. It is a larger value for areas with low infiltration
            and high runoff (pavement, steep gradient), and lower for
            permeable, well vegetated areas (forest, flat land).
            """
            )
        cro_label = QLabel('Cro:')
        cro_label.setToolTip(cro_tooltip)

        self.CRO_min = QDoubleSpinBox(0.1, 2)
        self.CRO_min.setRange(0, 1)
        self.CRO_min.setToolTip(cro_tooltip)

        cro_label2 = QLabelCentered('to')
        cro_label2.setToolTip(cro_tooltip)

        self.CRO_max = QDoubleSpinBox(0.3, 2)
        self.CRO_max.setRange(0, 1)
        self.CRO_max.setToolTip(cro_tooltip)

        # Setup the models parameters space groupbox.
        params_space_group = QGroupBox('Models parameters space')
        params_space_layout = QGridLayout(params_space_group)

        row = 0
        params_space_layout.addWidget(rasmax_label, row, 0)
        params_space_layout.addWidget(self.QRAS_min, row, 1)
        params_space_layout.addWidget(rasmax_label2, row, 2)
        params_space_layout.addWidget(self.QRAS_max, row, 3)
        params_space_layout.addWidget(rasmax_label3, row, 4)
        row += 1
        params_space_layout.addWidget(cro_label, row, 0)
        params_space_layout.addWidget(self.CRO_min, row, 1)
        params_space_layout.addWidget(cro_label2, row, 2)
        params_space_layout.addWidget(self.CRO_max, row, 3)
        row += 1
        params_space_layout.addWidget(self.sy_label, row, 0)
        params_space_layout.addWidget(self.QSy_min, row, 1)
        params_space_layout.addWidget(sy_range_label2, row, 2)
        params_space_layout.addWidget(self.QSy_max, row, 3)

        params_space_layout.setColumnStretch(
            params_space_layout.columnCount() + 1, 1)

        # Setup the snowmelt parameters (°C).
        tmelt_label = QLabel('Tmelt:')
        tmelt_label2 = QLabel('°C')
        self._Tmelt = QDoubleSpinBox(0, 1)
        self._Tmelt.setRange(-25, 25)

        cm_label = QLabel('CM:')
        cm_label2 = QLabel('mm/°C')
        self._CM = QDoubleSpinBox(4, 1, 0.1)
        self._CM.setRange(0.1, 100)

        # units=' days'
        deltat_label = QLabel('deltaT :')
        deltat_label2 = QLabel('days')
        self._deltaT = QDoubleSpinBox(0, 0)
        self._deltaT.setRange(0, 999)

        # Setup the secondary models parameters groupbox.
        secondary_group = QGroupBox('Secondary models parameters')
        secondary_layout = QGridLayout(secondary_group)

        row = 0
        secondary_layout.addWidget(tmelt_label, row, 0)
        secondary_layout.addWidget(self._Tmelt, row, 1)
        secondary_layout.addWidget(tmelt_label2, row, 3)
        row += 1
        secondary_layout.addWidget(cm_label, row, 0)
        secondary_layout.addWidget(self._CM, row, 1)
        secondary_layout.addWidget(cm_label2, row, 3)
        row += 1
        secondary_layout.addWidget(deltat_label, row, 0)
        secondary_layout.addWidget(self._deltaT, row, 1)
        secondary_layout.addWidget(deltat_label2, row, 3)

        secondary_layout.setColumnStretch(
            secondary_layout.columnCount() + 1, 1)


        # Setup the scroll area.
        scroll_area_widget = QFrame()
        scroll_area_widget.setObjectName("viewport")
        scroll_area_widget.setStyleSheet(
            "#viewport {background-color:transparent;}")

        scroll_area_layout = QGridLayout(scroll_area_widget)
        scroll_area_layout.setContentsMargins(10, 5, 10, 0)

        scroll_area_layout.addWidget(params_space_group, 0, 0)
        scroll_area_layout.addWidget(secondary_group, 1, 0)
        scroll_area_layout.setRowStretch(3, 100)

        qtitle = QLabel('Parameter Range')
        qtitle.setAlignment(Qt.AlignCenter)

        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_area_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(0)
        scroll_area.setStyleSheet(
            "QScrollArea {background-color:transparent;}")

        # Setup the main layout.
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.addWidget(scroll_area, 0, 0)
        main_layout.addWidget(self.setup_toolbar(), 1, 0)
        main_layout.setRowStretch(0, 1)
        main_layout.setVerticalSpacing(10)

    def setup_toolbar(self):
        """Setup the toolbar of the widget. """
        toolbar = QWidget()

        btn_calib = QPushButton('Compute Recharge')
        btn_calib.clicked.connect(self.btn_calibrate_isClicked)

        self.btn_show_result = QToolButtonSmall(get_icon('search'))
        self.btn_show_result.clicked.connect(self.figstack.show)
        self.btn_show_result.setToolTip("Show GLUE results.")

        self.btn_save_glue = ExportGLUEButton(self.wxdset)

        layout = QGridLayout(toolbar)
        layout.addWidget(btn_calib, 0, 0)
        layout.addWidget(self.btn_show_result, 0, 1)
        layout.addWidget(self.btn_save_glue, 0, 3)
        layout.setContentsMargins(10, 0, 10, 0)

        return toolbar

    def set_wldset(self, wldset):
        """Set the namespace for the water level dataset."""
        self.wldset = wldset
        self.setEnabled(self.wldset is not None and self.wxdset is not None)
        gluedf = None if wldset is None else wldset.get_glue_at(-1)
        self._setup_ranges_from_wldset(gluedf)
        self.figstack.set_gluedf(gluedf)
        self.btn_save_glue.set_model(gluedf)

    def set_wxdset(self, wxdset):
        """Set the namespace for the weather dataset."""
        self.wxdset = wxdset
        self.setEnabled(self.wldset is not None and self.wxdset is not None)

    def _setup_ranges_from_wldset(self, gluedf):
        """
        Set the parameter range values from the last values that were used
        to produce the last GLUE results saved into the project.
        """
        if gluedf is not None:
            try:
                # This was introduced in gwhat 0.5.1.
                self.rmsecutoff_sbox.setValue(gluedf['cutoff']['rmse_cutoff'])
                self.rmsecutoff_cbox.setChecked(
                    gluedf['cutoff']['rmse_cutoff_enabled'])
            except KeyError:
                pass
            try:
                self.QSy_min.setValue(min(gluedf['ranges']['Sy']))
                self.QSy_max.setValue(max(gluedf['ranges']['Sy']))
            except KeyError:
                pass
            try:
                self.CRO_min.setValue(min(gluedf['ranges']['Cro']))
                self.CRO_max.setValue(max(gluedf['ranges']['Cro']))
            except KeyError:
                pass
            try:
                self.QRAS_min.setValue(min(gluedf['ranges']['RASmax']))
                self.QRAS_max.setValue(max(gluedf['ranges']['RASmax']))
            except KeyError:
                pass
            try:
                self._Tmelt.setValue(gluedf['params']['tmelt'])
                self._CM.setValue(gluedf['params']['CM'])
                self._deltaT.setValue(gluedf['params']['deltat'])
            except KeyError:
                pass

    def get_params_range(self, name):
        if name == 'Sy':
            return (min(self.QSy_min.value(), self.QSy_max.value()),
                    max(self.QSy_min.value(), self.QSy_max.value()))
        elif name == 'RASmax':
            return (min(self.QRAS_min.value(), self.QRAS_max.value()),
                    max(self.QRAS_min.value(), self.QRAS_max.value()))
        elif name == 'Cro':
            return (min(self.CRO_min.value(), self.CRO_max.value()),
                    max(self.CRO_min.value(), self.CRO_max.value()))
        else:
            raise ValueError('Name must be either Sy, Rasmax or Cro.')

    # ---- Properties.
    @property
    def Tmelt(self):
        return self._Tmelt.value()

    @property
    def CM(self):
        return self._CM.value()

    @property
    def deltaT(self):
        return self._deltaT.value()

    def btn_calibrate_isClicked(self):
        """
        Handles when the button to compute recharge and its uncertainty is
        clicked.
        """
        self.start_glue_calcul()

    def start_glue_calcul(self):
        """
        Start the method to evaluate ground-water recharge and its
        uncertainty.
        """
        # Set the model parameter ranges.
        self.rechg_worker.Sy = self.get_params_range('Sy')
        self.rechg_worker.Cro = self.get_params_range('Cro')
        self.rechg_worker.RASmax = self.get_params_range('RASmax')

        # Set the value of the secondary model parameters.
        self.rechg_worker.TMELT = self.Tmelt
        self.rechg_worker.CM = self.CM
        self.rechg_worker.deltat = self.deltaT


        # Set the data and check for errors.
        error = self.rechg_worker.load_data(self.wxdset, self.wldset)
        if error is not None:
            QMessageBox.warning(self, 'Warning', error, QMessageBox.Ok)
            return

        # Start the computation of groundwater recharge.
        self.setEnabled(False)
        self.progressbar.show()

        waittime = 0
        while self.rechg_thread.isRunning():
            time.sleep(0.1)
            waittime += 0.1
            if waittime > 15:
                print('Impossible to quit the thread.')
                return
        self.rechg_thread.start()

    def receive_glue_calcul(self, glue_dataframe):
        """
        Handle the plotting of the results once ground-water recharge has
        been evaluated.
        """
        self.rechg_thread.quit()
        if glue_dataframe is None:
            msg = ("Recharge evaluation was not possible because all"
                   " the models produced were deemed non-behavioural."
                   "\n\n"
                   "This usually happens when the range of values for"
                   " Sy, RASmax, and Cro are too restrictive or when the"
                   " Master Recession Curve (MRC) does not represent well the"
                   " behaviour of the observed hydrograph.")
            QMessageBox.warning(self, 'Warning', msg, QMessageBox.Ok)
        else:
            self.wldset.clear_glue()
            self.wldset.save_glue(glue_dataframe)
            self.sig_new_gluedf.emit(glue_dataframe)

            self.btn_save_glue.set_model(glue_dataframe)
            self.figstack.set_gluedf(glue_dataframe)
        self.progressbar.hide()
        self.setEnabled(True)

    def close(self):
        """Extend Qt method to close child windows."""
        self.figstack.close()
        super().close()


class ExportGLUEButton(ExportDataButton):
    """
    A toolbutton with a popup menu that handles the export of GLUE data
    to file.
    """
    MODEL_TYPE = GLUEDataFrameBase
    TOOLTIP = "Export GLUE data."

    def __init__(self, model=None, parent=None):
        super(ExportGLUEButton, self).__init__(model, parent)
        self.setIconSize(get_iconsize('small'))

    def setup_menu(self):
        """Setup the menu of the button tailored to the model."""
        super(ExportGLUEButton, self).setup_menu()
        self.menu().addAction('Export GLUE water budget as...',
                              self.save_water_budget_tofile)
        self.menu().addAction('Export GLUE water levels as...',
                              self.save_water_levels_tofile)
        self.menu().addAction('Export GLUE likelyhood measures...',
                              self.save_likelyhood_measures)

    # ---- Save data
    @QSlot()
    def save_likelyhood_measures(self, savefilename=None):
        """
        Prompt a dialog to select a file and save the models likelyhood
        measures that are used to compute groundwater levels and recharge
        rates with GLUE.
        """
        if savefilename is None:
            savefilename = osp.join(
                self.dialog_dir, "glue_likelyhood_measures.xlsx")
        savefilename = self.select_savefilename(
            "Save GLUE likelyhood measures",
            savefilename, "*.xlsx;;*.xls;;*.csv")
        if savefilename:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                self.model.save_glue_likelyhood_measures(savefilename)
            except PermissionError:
                self.show_permission_error()
                self.save_likelyhood_measures(savefilename)
            QApplication.restoreOverrideCursor()

    @QSlot()
    def save_water_budget_tofile(self, savefilename=None):
        """
        Prompt a dialog to select a file and save the GLUE water budget.
        """
        if savefilename is None:
            savefilename = osp.join(self.dialog_dir, "glue_water_budget.xlsx")

        savefilename = self.select_savefilename(
            "Save GLUE water budget", savefilename, "*.xlsx;;*.xls;;*.csv")

        if savefilename:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                self.model.save_mly_glue_budget_to_file(savefilename)
            except PermissionError:
                self.show_permission_error()
                self.save_water_budget_tofile(savefilename)
            QApplication.restoreOverrideCursor()

    @QSlot()
    def save_water_levels_tofile(self, savefilename=None):
        """
        Prompt a dialog to select a file and save the GLUE water levels.
        """
        if savefilename is None:
            savefilename = osp.join(self.dialog_dir, "glue_water_levels.xlsx")

        savefilename = self.select_savefilename(
            "Save GLUE water levels", savefilename, "*.xlsx;;*.xls;;*.csv")

        if savefilename:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                self.model.save_glue_waterlvl_to_file(savefilename)
            except PermissionError:
                self.show_permission_error()
                self.save_water_levels_tofile(savefilename)
            QApplication.restoreOverrideCursor()


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    widget = RechgEvalWidget()
    widget.show()

    sys.exit(app.exec_())
