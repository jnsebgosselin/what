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
from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QPushButton, QProgressBar, QLabel, QScrollArea,
    QApplication, QMessageBox, QFrame, QCheckBox, QGroupBox)

# ---- Local imports
from gwhat.widgets.buttons import ExportDataButton
from gwhat.common.widgets import QDoubleSpinBox
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

        self.modelsdistplot = ModelsDistplotWidget()
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

        class QLabelCentered(QLabel):
            def __init__(self, text):
                super(QLabelCentered, self).__init__(text)
                self.setAlignment(Qt.AlignCenter)

        # Setup the maximum readily available water range (RASmax).
        rasmax_tooltip = (
            """
            <b>Maximum Readily Available Storage (RASmax)</b>
            <p>The <i>maximum readily available storage</i> corresponds
            to the maximum capacity of a soil to retain water which can then be
            evaporated or extracted by the roots of plants.
            The value of this parameter is mainly related to the type of
            vegetation on the surface and the capillary properties of
            the soil.</p>
            <p>Groudwater recharge will be evaluated for a set of evenly
            spaced RASmax values within the specified range using an
            increment of 1 mm.</p>
            """
            )

        rasmax_label = QLabel('RASmax:')
        rasmax_label.setToolTip(rasmax_tooltip)

        self.QRAS_min = QDoubleSpinBox(5)
        self.QRAS_min.setRange(0, 999)
        self.QRAS_min.setToolTip(rasmax_tooltip)

        rasmax_label2 = QLabelCentered('to')
        rasmax_label2.setToolTip(rasmax_tooltip)

        self.QRAS_max = QDoubleSpinBox(40)
        self.QRAS_max.setRange(0, 999)
        self.QRAS_max.setToolTip(rasmax_tooltip)

        rasmax_label3 = QLabel('mm')
        rasmax_label3.setToolTip(rasmax_tooltip)

        # Setup the Specific yield cutoff range.
        syrange_tooltip = (
            """
            <b>Specific Yield (Sy)</b>
            <p>According to Meinzer (1923), the <i>specific yield</i> is the
            ratio of the volume of water a rock or soil yield by gravity
            after being saturated to its own volume.</p>
            <p>Only models with an estimated specific yield  that falls inside
            this range of values are retained as behavioural.</p>
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
            <b>Runoff Coefficient (Cro)</b>
            <p>The <i>runoff coefficient</i> is a dimensionless coefficient
            relating the amount of runoff to the amount of precipitation
            received. It is a larger value for areas with low infiltration
            and high runoff (pavement, steep gradient), and lower for
            permeable, well vegetated areas (forest, flat land).</p>
            <p>Groudwater recharge will be evaluated for a set of evenly
            spaced Cro values within the specified range using an
            increment of 0.01.</p>
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
        params_space_group = QGroupBox('Models Parameters Space')
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
        tmelt_tooltip = (
            """
            <b>Base Air Temperature of Melting (Tmelt)</b>

            <p>In the degree-day method, the daily snowmelt potential
            in mm/°C is assumed to be directly proportional to the
            difference, in °C, between the mean daily temperature and
            the <i>base air temperature of melting.
            The daily melt potential is assumed to be zero
            if the air temperature is lower than the base temperature.</p>
            <p>Typically, the base temperature should be 0°C.
            Adjusting the value of this parameter can be used to
            indirectly reflect the different energy dynamics and snowpack
            conditions which are too complex to be represented directly
            by the simple degree-day approach used in GWHAT.</p>
            """)
        tmelt_label = QLabel('Tmelt:')
        tmelt_label.setToolTip(tmelt_tooltip)
        tmelt_label2 = QLabel('°C')
        tmelt_label2.setToolTip(tmelt_tooltip)
        self._Tmelt = QDoubleSpinBox(0, 1)
        self._Tmelt.setRange(-25, 25)
        self._Tmelt.setToolTip(tmelt_tooltip)

        cm_tooltip = (
            """
            <b>Degree-day Melt Coefficient (CM)</b>
            <p>The <i>degree-day melt coefficient</i> is a coefficient
            relating the amount of total daily melt potential in mm to the
            difference, in °C, between the main daily temperature and the base
            air temperature of melting (Tmelt).</p>
            <p>The degree-day melt coefficient varies geographically and
            seasonally, with typical values ranging between 1.6&nbsp;mm/°C to
            6.0&nbsp;mm/°C. When information is lacking, a constant value of
            2.7&nbsp;mm/°C can be used as suggested by USDA NRCS (2004).
            <p>In GWHAT, CM is assumed to be constant.</p>
            """
            )
        cm_label = QLabel('CM:')
        cm_label.setToolTip(cm_tooltip)
        cm_label2 = QLabel('mm/°C')
        cm_label2.setToolTip(cm_tooltip)
        self._CM = QDoubleSpinBox(4, 1, 0.1)
        self._CM.setToolTip(cm_tooltip)
        self._CM.setRange(0.1, 100)
        self._CM.setToolTip(cm_tooltip)

        # Setup the recharge delay widgets.
        deltat_tooltip = (
            """
            <b>Recharge delay (deltaT)</b>
            <p>The <i>recharge delay</i> relates to time required, on average,
            for the infiltrated water to percolate downward through
            the unsaturated zone and reach the water table.</p>
            <p>The value of this parameter is strongly related to the hydraulic
            properties and average water content of the unstaturated zone.
            </p>
            """
            )
        deltat_label = QLabel('deltaT:')
        deltat_label.setToolTip(deltat_tooltip)
        deltat_label2 = QLabel('days')
        deltat_label2.setToolTip(deltat_tooltip)
        self._deltaT = QDoubleSpinBox(0, 0)
        self._deltaT.setRange(0, 999)
        self._deltaT.setToolTip(deltat_tooltip)

        # Setup the secondary models parameters groupbox.
        secondary_group = QGroupBox('Secondary Models Parameters')
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

        # Setup the RMSE cutoff.
        rmsecutoff_tooltip = (
            "<b>RMSE Cutoff Value</b>"
            "<p>All models whose RMSE falls above this RMSE cutoff value "
            "are discarded as non-behavioural.</p>")

        self.rmsecutoff_sbox = QDoubleSpinBox(0, 1)
        self.rmsecutoff_sbox.setRange(0, 99999)
        self.rmsecutoff_sbox.setEnabled(False)
        self.rmsecutoff_sbox.setToolTip(rmsecutoff_tooltip)

        self.rmsecutoff_cbox = QCheckBox('RMSE:')
        self.rmsecutoff_cbox.setToolTip(rmsecutoff_tooltip)
        self.rmsecutoff_cbox.toggled.connect(self.rmsecutoff_sbox.setEnabled)

        rmsecutoff_label = QLabel('mm')
        rmsecutoff_label.setToolTip(rmsecutoff_tooltip)

        # Setup the cutoff criteria group widget.
        cutoff_group = QGroupBox('Models Cutoff Criteria')
        cutoff_layout = QGridLayout(cutoff_group)

        row += 0
        cutoff_layout.addWidget(self.rmsecutoff_cbox, row, 0)
        cutoff_layout.addWidget(self.rmsecutoff_sbox, row, 1)
        cutoff_layout.addWidget(rmsecutoff_label, row, 2, 1, 2)

        cutoff_layout.setColumnStretch(cutoff_layout.columnCount() + 1, 1)

        # Setup the scroll area.
        scroll_area_widget = QFrame()
        scroll_area_widget.setObjectName("viewport")
        scroll_area_widget.setStyleSheet(
            "#viewport {background-color:transparent;}")

        scroll_area_layout = QGridLayout(scroll_area_widget)
        scroll_area_layout.setContentsMargins(10, 5, 10, 0)

        scroll_area_layout.addWidget(params_space_group, 0, 0)
        scroll_area_layout.addWidget(secondary_group, 1, 0)
        scroll_area_layout.addWidget(cutoff_group, 2, 0)
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

        self.btn_modelsdistplot = create_toolbutton(
            parent=self,
            icon='models_dist',
            tip='Display the model distribution plot.',
            triggered=self.modelsdistplot.show,
            iconsize=get_iconsize('normal')
            )

        layout = QGridLayout(toolbar)
        layout.addWidget(btn_calib, 0, 0)
        layout.addWidget(self.btn_show_result, 0, 1)
        layout.addWidget(self.btn_modelsdistplot, 0, 2)
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
        self.modelsdistplot.set_gluedf(gluedf)
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

        self.rechg_worker.rmse_cutoff = self.rmsecutoff_sbox.value()
        self.rechg_worker.rmse_cutoff_enabled = int(
            self.rmsecutoff_cbox.isChecked())

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
            self.modelsdistplot.set_gluedf(glue_dataframe)
        self.progressbar.hide()
        self.setEnabled(True)

    def close(self):
        """Extend Qt method to close child windows."""
        self.figstack.close()
        self.modelsdistplot.close()
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
