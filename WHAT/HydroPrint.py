# -*- coding: utf-8 -*-
"""
Copyright 2014-2017 Jean-Sebastien Gosselin
email: jean-sebastien.gosselin@ete.inrs.ca

This file is part of WHAT (Well Hydrograph Analysis Toolbox).

WHAT is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>
"""

from __future__ import division, unicode_literals

# Standard library imports :

import csv
import sys
import os
import copy

# Third party imports :

from PySide import QtGui, QtCore
from PySide.QtCore import QDate

import numpy as np
from xlrd.xldate import xldate_from_date_tuple
from xlrd import xldate_as_tuple

# Local imports :

import HydroCalc
import hydrograph3 as hydrograph
import mplFigViewer3 as mplFigViewer
from meteo.meteo_utils import MeteoObj, WeatherAvgGraph
import custom_widgets as MyQWidget
from waterlvldata import WaterlvlData

from common import IconDB, StyleDB, QToolButtonNormal
import common.widgets as myqt
import common.database as db


# =============================================================================


class HydroprintGUI(QtGui.QWidget):

    ConsoleSignal = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(HydroprintGUI, self).__init__(parent)

        self.workdir = os.getcwd()
        self.__updateUI = True
        self.fwaterlvl = []
        self.waterlvl_data = WaterlvlData()
        self.meteo_data = MeteoObj()

        # memory path variable :

        self.meteo_dir = os.path.join(self.workdir, 'Meteo', 'Output')
        self.waterlvl_dir = os.path.join(self.workdir, 'Water Levels')
        self.save_fig_dir = self.workdir

        self.__initUI__()

    def __initUI__(self):

        # Main Window :

        self.setWindowIcon(IconDB().master)

        # Weather Normals Widget :

        self.weather_avg_graph = WeatherAvgGraph(self)

        # HydroCalc Widget :

        self.hydrocalc = HydroCalc.WLCalc()
        self.hydrocalc.hide()

        # Page Setup Widget :

        self.page_setup_win = PageSetupWin(self)
        self.page_setup_win.newPageSetupSent.connect(self.layout_changed)

        # Color Palette Widget :

        self.color_palette_win = ColorsSetupWin(self)
        self.color_palette_win.newColorSetupSent.connect(self.update_colors)

        # ---------------------------------------------------------- Toolbar --

        # BUTTONS :

        btn_loadConfig = QToolButtonNormal(IconDB().load_graph_config)
        btn_loadConfig.setToolTip('<p>Load graph layout for the current'
                                  ' Water Level Data File if it exists</p>')

        btn_saveConfig = QToolButtonNormal(IconDB().save_graph_config)
        btn_saveConfig.setToolTip('Save current graph layout')

        btn_bestfit_waterlvl = QToolButtonNormal(IconDB().fit_y)
        btn_bestfit_waterlvl.setToolTip('Best fit the water level scale')

        btn_bestfit_time = QToolButtonNormal(IconDB().fit_x)
        btn_bestfit_time.setToolTip('Best fit the time scale')

        btn_closest_meteo = QToolButtonNormal(IconDB().closest_meteo)
        btn_closest_meteo.setToolTip('<p>Search and Load the Weather Data File'
                                     ' of the station located the closest from'
                                     ' the well</p>')

        btn_draw = QToolButtonNormal(IconDB().refresh)
        btn_draw.setToolTip('Force a refresh of the well hydrograph')

        btn_weather_normals = QToolButtonNormal(IconDB().meteo)
        btn_weather_normals.setToolTip('<p>Plot the yearly and monthly'
                                       ' averages for the Weather Data File'
                                       ' currently selected.</p>')

        self.btn_work_waterlvl = QToolButtonNormal(IconDB().toggleMode)
        self.btn_work_waterlvl.setToolTip('Toggle between layout and '
                                          ' computation mode')

        btn_save = QToolButtonNormal(IconDB().save)
        btn_save.setToolTip('Save the well hydrograph')

        btn_page_setup = QToolButtonNormal(IconDB().page_setup)
        btn_page_setup.setToolTip('Show the page setup window')
        btn_page_setup.clicked.connect(self.page_setup_win.show)

        btn_color_pick = QToolButtonNormal(IconDB().color_picker)
        btn_color_pick.setToolTip('<p>Show a window to setup the color palette'
                                  ' used to draw the hydrograph</p.')
        btn_color_pick.clicked.connect(self.color_palette_win.show)

        # LAYOUT :

        btn_list = [self.btn_work_waterlvl, myqt.VSep(), btn_save, btn_draw,
                    btn_loadConfig, btn_saveConfig, myqt.VSep(),
                    btn_bestfit_waterlvl, btn_bestfit_time, btn_closest_meteo,
                    myqt.VSep(), btn_weather_normals, btn_page_setup,
                    btn_color_pick]

        subgrid_toolbar = QtGui.QGridLayout()
        toolbar_widget = QtGui.QWidget()

        row = 0
        for col, btn in enumerate(btn_list):
            subgrid_toolbar.addWidget(btn, row, col)

        subgrid_toolbar.setSpacing(5)
        subgrid_toolbar.setContentsMargins(0, 0, 0, 0)
        subgrid_toolbar.setColumnStretch(col + 1, 100)

        toolbar_widget.setLayout(subgrid_toolbar)

        # ------------------------------------------------------- LEFT PANEL --

        # SubGrid Hydrograph Frame :

        self.hydrograph = hydrograph.Hydrograph()
        self.hydrograph_scrollarea = mplFigViewer.ImageViewer()

        grid_hydrograph_widget = QtGui.QFrame()
        grid_hydrograph = QtGui.QGridLayout()

        grid_hydrograph.addWidget(self.hydrograph_scrollarea, 0, 0)

        grid_hydrograph.setRowStretch(0, 500)
        grid_hydrograph.setColumnStretch(0, 500)
        grid_hydrograph.setContentsMargins(0, 0, 0, 0)  # (L, T, R, B)

        grid_hydrograph_widget.setLayout(grid_hydrograph)

        # ASSEMBLING SubGrids :

        grid_layout = QtGui.QGridLayout()
        self.grid_layout_widget = QtGui.QFrame()

        row = 0
        grid_layout.addWidget(toolbar_widget, row, 0)
        row += 1
        grid_layout.addWidget(grid_hydrograph_widget, row, 0)

        grid_layout.setContentsMargins(0, 0, 0, 0)  # (L, T, R, B)
        grid_layout.setSpacing(5)
        grid_layout.setColumnStretch(0, 500)
        grid_layout.setRowStretch(1, 500)

        self.grid_layout_widget.setLayout(grid_layout)

        # ---------------------------------------------------- Right Panel ----

        data_files_panel = self.__init_dataFilesPanel__()
        self.tabscales = self.__init_scalesTabWidget__()
        self.qAxeLabelsLanguage = self.__init_labelLangWidget__()
        self.hydrocalc.widget_MRCparam.hide()

        RightPanel = QtGui.QFrame()
        layout = QtGui.QGridLayout()
        # ----
        row = 0
        layout.addLayout(data_files_panel, row, 0)
        row += 1
        layout.addWidget(self.tabscales, row, 0)
        layout.addWidget(self.hydrocalc.widget_MRCparam, row, 0)
        row += 1
        layout.addWidget(self.qAxeLabelsLanguage, 2, 0)
        row += 1
        layout.setRowStretch(row, 100)
        # ----
        layout.setContentsMargins(0, 0, 0, 0)  # (L, T, R, B)
        layout.setSpacing(15)

        RightPanel.setLayout(layout)

        # ------------------------------------------------------ MAIN GRID ----

        mainGrid = QtGui.QGridLayout()

        mainGrid.addWidget(self.grid_layout_widget, 0, 0)
        mainGrid.addWidget(self.hydrocalc, 0, 0)
        mainGrid.addWidget(myqt.VSep(), 0, 1)
        mainGrid.addWidget(RightPanel, 0, 2)

        mainGrid.setContentsMargins(10, 10, 10, 10)  # (L, T, R, B)
        mainGrid.setSpacing(15)
        mainGrid.setColumnStretch(0, 500)
        mainGrid.setColumnMinimumWidth(2, 250)

        self.setLayout(mainGrid)

        # -------------------------------------------------- MESSAGE BOXES ----

        self.msgBox = QtGui.QMessageBox()
        self.msgBox.setIcon(QtGui.QMessageBox.Question)
        self.msgBox.setStandardButtons(QtGui.QMessageBox.Yes |
                                       QtGui.QMessageBox.No)
        self.msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
        self.msgBox.setWindowTitle('Save Graph Layout')
        self.msgBox.setWindowIcon(IconDB().master)

        # --------------------------------------------------------- EVENTS ----

        # ---- Toolbox Layout ----

        btn_loadConfig.clicked.connect(self.load_graph_layout)
        btn_saveConfig.clicked.connect(self.save_config_isClicked)
        btn_bestfit_waterlvl.clicked.connect(self.best_fit_waterlvl)
        btn_bestfit_time.clicked.connect(self.best_fit_time)
        btn_closest_meteo.clicked.connect(self.select_closest_meteo_file)
        btn_draw.clicked.connect(self.draw_hydrograph)
        btn_save.clicked.connect(self.select_save_path)
        btn_weather_normals.clicked.connect(self.show_weather_averages)

        # Toggle Mode :

        self.btn_work_waterlvl.clicked.connect(self.toggle_computeMode)
        self.hydrocalc.btn_layout_mode.clicked.connect(self.toggle_layoutMode)

        # Hydrograph Layout :

        self.language_box.currentIndexChanged.connect(self.layout_changed)
        self.Ptot_scale.valueChanged.connect(self.layout_changed)
        self.qweather_bin.currentIndexChanged.connect(self.layout_changed)

        # ----------------------------------------------------- Init Image ----

        self.hydrograph_scrollarea.load_mpl_figure(self.hydrograph)

    def __init_dataFilesPanel__(self):  # =====================================

        # Widgets :

        btn_waterlvl_dir = QtGui.QPushButton(' Water Level Data File')
        btn_waterlvl_dir.setIcon(IconDB().openFile)
        btn_waterlvl_dir.setIconSize(StyleDB().iconSize2)
        btn_waterlvl_dir.clicked.connect(self.select_waterlvl_file)

        self.well_info_widget = QtGui.QTextEdit()
        self.well_info_widget.setReadOnly(True)
        self.well_info_widget.setFixedHeight(150)

        btn_weather_dir = QtGui.QPushButton(' Weather Data File')
        btn_weather_dir.setIcon(IconDB().openFile)
        btn_weather_dir.setIconSize(StyleDB().iconSize2)
        btn_weather_dir.clicked.connect(self.select_meteo_file)

        self.meteo_info_widget = QtGui.QTextEdit()
        self.meteo_info_widget.setReadOnly(True)
        self.meteo_info_widget.setFixedHeight(150)

        # Layout :

        layout = QtGui.QGridLayout()

        layout.addWidget(btn_waterlvl_dir, 0, 0)
        layout.addWidget(self.well_info_widget, 1, 0)
        layout.addWidget(btn_weather_dir, 2, 0)
        layout.addWidget(self.meteo_info_widget, 3, 0)

        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        return layout

    def __init_scalesTabWidget__(self):  # ====================================

        class QRowLayout(QtGui.QGridLayout):
            def __init__(self, items, parent=None):
                super(QRowLayout, self).__init__(parent)

                for col, item in enumerate(items):
                    self.addWidget(item, 0, col)

                self.setContentsMargins(0, 0, 0, 0)
                self.setColumnStretch(0, 100)

        # ----------------------------------------------------------  TIME ----

        # Widget :

        self.date_start_widget = QtGui.QDateEdit()
        self.date_start_widget.setDisplayFormat('01 / MM / yyyy')
        self.date_start_widget.setAlignment(QtCore.Qt.AlignCenter)
        self.date_start_widget.dateChanged.connect(self.layout_changed)

        self.date_end_widget = QtGui.QDateEdit()
        self.date_end_widget.setDisplayFormat('01 / MM / yyyy')
        self.date_end_widget.setAlignment(QtCore.Qt.AlignCenter)
        self.date_end_widget.dateChanged.connect(self.layout_changed)

        self.time_scale_label = QtGui.QComboBox()
        self.time_scale_label.setEditable(False)
        self.time_scale_label.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.time_scale_label.addItems(['Month', 'Year'])
        self.time_scale_label.setCurrentIndex(0)
        self.time_scale_label.currentIndexChanged.connect(self.layout_changed)

        self.dateDispFreq_spinBox = QtGui.QSpinBox()
        self.dateDispFreq_spinBox.setSingleStep(1)
        self.dateDispFreq_spinBox.setMinimum(1)
        self.dateDispFreq_spinBox.setMaximum(100)
        self.dateDispFreq_spinBox.setValue(
            self.hydrograph.date_labels_display_pattern)
        self.dateDispFreq_spinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.dateDispFreq_spinBox.setKeyboardTracking(False)
        self.dateDispFreq_spinBox.valueChanged.connect(self.layout_changed)

        # Layout :

        widget_time_scale = QtGui.QFrame()
        widget_time_scale.setFrameStyle(0)
        grid_time_scale = QtGui.QGridLayout()

        GRID = [[QtGui.QLabel('From :'), self.date_start_widget],
                [QtGui.QLabel('To :'), self.date_end_widget],
                [QtGui.QLabel('Scale :'), self.time_scale_label],
                [QtGui.QLabel('Date Disp. Pattern:'),
                 self.dateDispFreq_spinBox]]

        for i, ROW in enumerate(GRID):
            grid_time_scale.addLayout(QRowLayout(ROW), i, 1)

        grid_time_scale.setVerticalSpacing(5)
        grid_time_scale.setContentsMargins(10, 10, 10, 10)

        widget_time_scale.setLayout(grid_time_scale)

        # ---------------------------------------------------- WATER LEVEL ----

        # Widget :

        self.waterlvl_scale = QtGui.QDoubleSpinBox()
        self.waterlvl_scale.setSingleStep(0.05)
        self.waterlvl_scale.setMinimum(0.05)
        self.waterlvl_scale.setSuffix('  m')
        self.waterlvl_scale.setAlignment(QtCore.Qt.AlignCenter)
        self.waterlvl_scale.setKeyboardTracking(False)
        self.waterlvl_scale.valueChanged.connect(self.layout_changed)
        self.waterlvl_scale.setFixedWidth(100)

        self.waterlvl_max = QtGui.QDoubleSpinBox()
        self.waterlvl_max.setSingleStep(0.1)
        self.waterlvl_max.setSuffix('  m')
        self.waterlvl_max.setAlignment(QtCore.Qt.AlignCenter)
        self.waterlvl_max.setMinimum(-1000)
        self.waterlvl_max.setMaximum(1000)
        self.waterlvl_max.setKeyboardTracking(False)
        self.waterlvl_max.valueChanged.connect(self.layout_changed)
        self.waterlvl_max.setFixedWidth(100)

        self.NZGridWL_spinBox = QtGui.QSpinBox()
        self.NZGridWL_spinBox.setSingleStep(1)
        self.NZGridWL_spinBox.setMinimum(1)
        self.NZGridWL_spinBox.setMaximum(50)
        self.NZGridWL_spinBox.setValue(self.hydrograph.NZGrid)
        self.NZGridWL_spinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.NZGridWL_spinBox.setKeyboardTracking(False)
        self.NZGridWL_spinBox.valueChanged.connect(self.layout_changed)
        self.NZGridWL_spinBox.setFixedWidth(100)

        self.datum_widget = QtGui.QComboBox()
        self.datum_widget.addItems(['Ground Surface', 'See Level'])
        self.datum_widget.currentIndexChanged.connect(self.layout_changed)

        # Layout :

        subgrid_WLScale = QtGui.QGridLayout()

        GRID = [[QtGui.QLabel('Minimum :'), self.waterlvl_max],
                [QtGui.QLabel('Scale :'), self.waterlvl_scale],
                [QtGui.QLabel('Grid Divisions :'), self.NZGridWL_spinBox],
                [QtGui.QLabel('Datum :'), self.datum_widget]]

        for i, ROW in enumerate(GRID):
            subgrid_WLScale.addLayout(QRowLayout(ROW), i, 1)

        subgrid_WLScale.setVerticalSpacing(5)
        subgrid_WLScale.setContentsMargins(10, 10, 10, 10)  # (L, T, R, B)

        WLScale_widget = QtGui.QFrame()
        WLScale_widget.setFrameStyle(0)
        WLScale_widget.setLayout(subgrid_WLScale)

        # -------------------------------------------------------- WEATHER ----

        # Widgets :

        self.Ptot_scale = QtGui.QSpinBox()
        self.Ptot_scale.setSingleStep(5)
        self.Ptot_scale.setMinimum(5)
        self.Ptot_scale.setMaximum(500)
        self.Ptot_scale.setValue(20)
        self.Ptot_scale.setSuffix('  mm')
        self.Ptot_scale.setAlignment(QtCore.Qt.AlignCenter)

        self.qweather_bin = QtGui.QComboBox()
        self.qweather_bin.setEditable(False)
        self.qweather_bin.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.qweather_bin.addItems(['day', 'week', 'month'])
        self.qweather_bin.setCurrentIndex(1)

        # Layout :

        layout = QtGui.QGridLayout()

        GRID = [[QtGui.QLabel('Precip. Scale :'), self.Ptot_scale],
                [QtGui.QLabel('Resampling :'), self.qweather_bin]]

        for i, row in enumerate(GRID):
            layout.addLayout(QRowLayout(row), i, 1)

        layout.setVerticalSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)  # (L,T,R,B)
        layout.setRowStretch(i+1, 100)

        widget_weather_scale = QtGui.QFrame()
        widget_weather_scale.setFrameStyle(0)
        widget_weather_scale.setLayout(layout)

        # ------------------------------------------------ ASSEMBLING TABS ----

        tabscales = QtGui.QTabWidget()
        tabscales.addTab(widget_time_scale, 'Time')
        tabscales.addTab(WLScale_widget, 'Water Level')
        tabscales.addTab(widget_weather_scale, 'Weather')

        return tabscales

    def __init_labelLangWidget__(self):  # ------------------------------------

        # Widgets :

        self.language_box = QtGui.QComboBox()
        self.language_box.setEditable(False)
        self.language_box.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.language_box.addItems(['French', 'English'])
        self.language_box.setCurrentIndex(1)

        # Layout :

        layout = QtGui.QGridLayout()
        # ----
        layout.addWidget(QtGui.QLabel('Label Language:'), 0, 0)
        layout.addWidget(self.language_box, 0, 1)
        # ----
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)  # (L, T, R, B)

        qAxeLabelsLanguage = QtGui.QFrame()
        qAxeLabelsLanguage.setLayout(layout)

        return qAxeLabelsLanguage

    # =========================================================================

    def set_workdir(self, directory):
        self.workdir = directory
        self.meteo_dir = os.path.join(directory, 'Meteo', 'Output')
        self.waterlvl_dir = os.path.join(directory, 'Water Levels')
        self.save_fig_dir = directory

    def check_files(self):

        # System project folder organization :

        dirname = os.path.join(self.workdir, 'Water Levels')
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # water lvl manual measurements :

        fname = os.path.join(self.workdir, 'waterlvl_manual_measurements.csv')
        if not os.path.exists(fname):

            msg = ('No "waterlvl_manual_measurements.xls" file found. '
                   'A new one has been created.')
            print(msg)

            fcontent = [['Well_ID', 'Time (days)', 'Obs. (mbgs)']]
            with open(fname, 'w') as f:
                writer = csv.writer(f, delimiter='\t', lineterminator='\n')
                writer.writerows(fcontent)

        # graph_layout.lst :

        filename = self.workdir + '/graph_layout.lst'
        if not os.path.exists(filename):
            fcontent = db.FileHeaders().graph_layout

            msg = ('No "graph_layout.lst" file found. ' +
                   'A new one has been created.')
            print(msg)

            with open(filename, 'w') as f:
                writer = csv.writer(f, delimiter='\t', lineterminator='\n')
                writer.writerows(fcontent)

    # =========================================================================

    def toggle_layoutMode(self):
        self.hydrocalc.hide()
        self.grid_layout_widget.show()

        # Update Right Panel :

        self.hydrocalc.widget_MRCparam.hide()

        self.tabscales.show()
        self.qAxeLabelsLanguage.show()

    def toggle_computeMode(self):
        self.grid_layout_widget.hide()
        self.hydrocalc.show()

        # Update Right Panel Update :

        self.hydrocalc.widget_MRCparam.show()

        self.tabscales.hide()
        self.qAxeLabelsLanguage.hide()

    # =========================================================================

    def update_colors(self):
        self.hydrograph.update_colors()
        self.hydrograph_scrollarea.load_mpl_figure(self.hydrograph)

    # =========================================================================

    def show_weather_averages(self):
        filemeteo = copy.copy(self.hydrograph.fmeteo)
        if not filemeteo:
            msg = 'No valid Weather Data File currently selected.'
            print(msg)
            self.ConsoleSignal.emit('font color=red>%s</font>' % msg)

            msg = 'Please select a valid Weather Data File first.'
            print(msg)
            self.emit_error_message('<b>%s</b>' % msg)

            return

        self.weather_avg_graph.save_fig_dir = self.workdir
        self.weather_avg_graph.generate_graph(filemeteo)
        self.weather_avg_graph.show()

    def emit_error_message(self, msg):
        btn = QtGui.QMessageBox.Ok
        QtGui.QMessageBox.warning(self, 'Warning', msg, btn)

    # =========================================================================

    def select_waterlvl_file(self):
        # This method is called by <btn_waterlvl_dir> is clicked. It prompts
        # the user to select a valid Water Level Data file.

        filename, _ = QtGui.QFileDialog.getOpenFileName(
            self, 'Select a valid water level data file',
            self.waterlvl_dir, '(*.xls *.xlsx)')

        for i in range(5):
            QtCore.QCoreApplication.processEvents()

        if filename:
            self.load_waterlvl(filename)

    def load_waterlvl(self, filename):
        # If "filename" exists:
        # The (1) water level time series, (2) observation well info and the
        # (3) manual measures are loaded and saved in the class instance
        # "waterlvl_data".

        # Then the code check if there is a layout already saved for this well
        # and if yes, will prompt the user if he wants to load it.

        # Depending if there is a layout or not, a Weather Data File will be
        # loaded and the hydrograph will be automatically plotted.

        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        if not os.path.exists(filename):
            print('Path does not exist. Cannot load water level file.')
            return

        self.check_files()

        # Update UI Memory Variables :

        self.waterlvl_dir = os.path.dirname(filename)
        self.fwaterlvl = filename

        # Load Data :
        msg = 'Loading water level data...'
        self.ConsoleSignal.emit('<font color=black>%s</font>' % msg)
        for i in range(5):
            QtCore.QCoreApplication.processEvents()

        state = self.waterlvl_data.load(filename)
        if state is False:
            msg = ('WARNING: Waterlvl data file "%s" is not formatted '
                   ' correctly.') % os.path.basename(filename)
            print(msg)
            self.ConsoleSignal.emit('<font color=red>%s</font>' % msg)
            QtGui.QApplication.restoreOverrideCursor()
            return False

        name_well = self.waterlvl_data.name_well

        # Load Manual Measures :

        filename = os.path.join(self.workdir,
                                'waterlvl_manual_measurements.xls')
        self.waterlvl_data.load_waterlvl_measures(filename, name_well)

        # Update Waterlvl Obj :

        self.hydrograph.set_waterLvlObj(self.waterlvl_data)

        # Display Well Info in UI :

        print(self.waterlvl_data.well_info)
        self.well_info_widget.setText(self.waterlvl_data.well_info)

        msg = ('Water level data set loaded successfully ' +
               'for well %s.' % name_well)
        print(msg)
        self.ConsoleSignal.emit('<font color=black>%s</font>' % msg)

        # Update Graph of "Compute" Mode :
        self.hydrocalc.load_waterLvl_data(self.fwaterlvl)

        # Well Layout :

        filename = os.path.join(self.workdir, 'graph_layout.lst')
        isLayoutExist = self.hydrograph.checkLayout(name_well, filename)

        if isLayoutExist is True:
            msg = 'Loading existing graph layout for well %s.' % name_well
            print(msg)
            self.ConsoleSignal.emit('<font color=black>%s</font>' % msg)
            self.load_graph_layout()
            QtGui.QApplication.restoreOverrideCursor()
            return

        # Fit Water Level in Layout :

        self.__updateUI = False

        self.best_fit_waterlvl()
        self.best_fit_time()

        self.__updateUI = True

        self.select_closest_meteo_file()

        QtGui.QApplication.restoreOverrideCursor()

    # =========================================================================

    def select_closest_meteo_file(self):

        meteo_folder = os.path.join(self.workdir, 'Meteo', 'Output')

        if os.path.exists(meteo_folder) and self.fwaterlvl:

            LAT1 = self.waterlvl_data.LAT
            LON1 = self.waterlvl_data.LON

            # Generate a list of data file paths :
            fmeteo_paths = []
            for root, directories, filenames in os.walk(meteo_folder):
                for filename in filenames:
                    if os.path.splitext(filename)[1] == '.out':
                        fmeteo_paths.append(os.path.join(root, filename))

            if len(fmeteo_paths) > 0:

                LAT2 = np.zeros(len(fmeteo_paths))
                LON2 = np.zeros(len(fmeteo_paths))
                DIST = np.zeros(len(fmeteo_paths))
                i = 0
                for fmeteo in fmeteo_paths:

                    with open(fmeteo, 'r') as f:
                        reader = list(csv.reader(f, delimiter='\t'))

                    LAT2[i] = float(reader[2][1])
                    LON2[i] = float(reader[3][1])
                    DIST[i] = hydrograph.LatLong2Dist(LAT1, LON1, LAT2[i],
                                                      LON2[i])

                    i += 1

                index = np.where(DIST == np.min(DIST))[0][0]

                self.load_meteo_file(fmeteo_paths[index])
                for i in range(5):
                    QtCore.QCoreApplication.processEvents()

    # =========================================================================

    def select_meteo_file(self):
        '''
        This method is called by <btn_weather_dir.clicked.connect>. It prompts
        the user to select a valid Weather Data file.
        '''

        filename, _ = QtGui.QFileDialog.getOpenFileName(
            self, 'Select a valid weather data file', self.meteo_dir, '*.out')

        for i in range(5):
            QtCore.QCoreApplication.processEvents()

        self.load_meteo_file(filename)

    def load_meteo_file(self, filename):

        if not filename:
            print('Path is empty. Cannot load weather data file.')
            return

        self.meteo_dir = os.path.dirname(filename)
        self.hydrograph.fmeteo = filename
        self.hydrograph.finfo = filename[:-3] + 'log'

        self.meteo_data.load_and_format(filename)
        self.meteo_info_widget.setText(self.meteo_data.INFO)

        msg = ('<font color=black>Weather data set loaded successfully for '
               'station %s.</font>') % self.meteo_data.STA
        self.ConsoleSignal.emit(msg)

        # Update Graph of "Compute" Mode :
        self.hydrocalc.load_weather_data(filename)

        if self.fwaterlvl:
            QtCore.QCoreApplication.processEvents()
            self.draw_hydrograph()

    # =========================================================================

    def update_graph_layout_parameter(self):
        '''
        This method is called either by the methods <save_graph_layout>
        or by <draw_hydrograph>. It fetches the values that are currently
        displayed in the UI and save them in the class instance
        <hydrograph> of the class <Hydrograph>.
        '''

        if self.__updateUI is False:
            return

        # Dates :

        year = self.date_start_widget.date().year()
        month = self.date_start_widget.date().month()
        day = 1
        date = xldate_from_date_tuple((year, month, day), 0)
        self.hydrograph.TIMEmin = date

        year = self.date_end_widget.date().year()
        month = self.date_end_widget.date().month()
        day = 1
        date = xldate_from_date_tuple((year, month, day), 0)
        self.hydrograph.TIMEmax = date

        # Scales :

        self.hydrograph.WLscale = self.waterlvl_scale.value()
        self.hydrograph.WLmin = self.waterlvl_max.value()
        self.hydrograph.RAINscale = self.Ptot_scale.value()

        # Label language :

        self.hydrograph.language = self.language_box.currentText()

        # ----------------------------------------------------- Page Setup ----

        # Water Level Trend :

        self.hydrograph.trend_line = int(self.page_setup_win.isTrendLine)

        # Legend :

        self.hydrograph.isLegend = int(self.page_setup_win.isLegend)

        # Graph title :

        self.hydrograph.isGraphTitle = int(self.page_setup_win.isGraphTitle)

        # Figure size :

        self.hydrograph.fwidth = self.page_setup_win.pageSize[0]

    # ======================================================= Graph layout ====

    def load_graph_layout(self):

        self.check_files()

        # ----------------------------------- Check if Waterlvl Data Exist ----

        if not self.fwaterlvl:
            msg = ('No valid water level data file currently selected '
                   'Cannot load graph layout.')
            print(msg)
            self.ConsoleSignal.emit('<font color=red>%s</font>' % msg)

            self.emit_error_message(
                '<b>Please select a valid water level data file.</b>')

            return

        # ----------------------------------------- Check if Layout Exists ----

        filename = os.path.join(self.workdir, 'graph_layout.lst')
        name_well = self.waterlvl_data.name_well
        isLayoutExist = self.hydrograph.checkLayout(name_well, filename)

        if isLayoutExist is False:
            msg = 'No graph layout exists for well %s.' % name_well
            print(msg)
            self.ConsoleSignal.emit('<font color=red>%s</font>' % msg)
            self.emit_error_message('<b>%s</b>' % msg)
            return

        # ---------------------------------------------------- Load Layout ----

        self.hydrograph.load_layout(name_well, filename)

        # ----------------------------------------------------- Update UI -----

        self.__updateUI = False

        # Scales :

        date = self.hydrograph.TIMEmin
        date = xldate_as_tuple(date, 0)
        self.date_start_widget.setDate(QDate(date[0], date[1], date[2]))

        date = self.hydrograph.TIMEmax
        date = xldate_as_tuple(date, 0)
        self.date_end_widget.setDate(QDate(date[0], date[1], date[2]))

        self.dateDispFreq_spinBox.setValue(
            self.hydrograph.date_labels_display_pattern)

        self.waterlvl_scale.setValue(self.hydrograph.WLscale)
        self.waterlvl_max.setValue(self.hydrograph.WLmin)
        self.datum_widget.setCurrentIndex(self.hydrograph.WLdatum)
        self.NZGridWL_spinBox.setValue(self.hydrograph.NZGrid)

        self.Ptot_scale.setValue(self.hydrograph.RAINscale)

        # Color Palette :

        self.color_palette_win.load_colors()

        # Page Setup :

        self.page_setup_win.pageSize = (self.hydrograph.fwidth,
                                        self.hydrograph.fheight)
        self.page_setup_win.va_ratio = self.hydrograph.va_ratio
        self.page_setup_win.isLegend = self.hydrograph.isLegend
        self.page_setup_win.isGraphTitle = self.hydrograph.isGraphTitle
        self.page_setup_win.isTrendLine = self.hydrograph.trend_line

        if self.hydrograph.isGraphTitle == 1:
            self.page_setup_win.title_on.toggle()
        else:
            self.page_setup_win.title_off.toggle()

        if self.hydrograph.isLegend == 1:
            self.page_setup_win.legend_on.toggle()
        else:
            self.page_setup_win.legend_off.toggle()

        if self.hydrograph.trend_line == 1:
            self.page_setup_win.trend_on.toggle()
        else:
            self.page_setup_win.trend_off.toggle()

        self.page_setup_win.fwidth.setValue(self.hydrograph.fwidth)
        self.page_setup_win.fheight.setValue(self.hydrograph.fheight)
        self.page_setup_win.va_ratio_spinBox.setValue(self.hydrograph.va_ratio)

        # Check if Weather Data File exists :

        if os.path.exists(self.hydrograph.fmeteo):
            msg = 'Graph layout loaded successfully for well %s.' % name_well
            print(msg)
            self.ConsoleSignal.emit('<font color=black>%s.</font>' % msg)
            QtCore.QCoreApplication.processEvents()

            self.load_meteo_file(self.hydrograph.fmeteo)

        else:
            self.meteo_info_widget.setText('')
            self.ConsoleSignal.emit(
            '''<font color=red>Unable to read the weather data file. %s
               does not exist.</font>''' % self.hydrograph.fmeteo)
            self.emit_error_message(
            '''<b>Unable to read the weather data file.<br><br>
               %s does not exist.<br><br> Please select another weather
               data file.<b>''' % self.hydrograph.fmeteo)
            self.hydrograph.fmeteo = []
            self.hydrograph.finfo = []

        self.__updateUI = True

    def save_config_isClicked(self):

        if not self.fwaterlvl:

            self.ConsoleSignal.emit(
            '''<font color=red>No valid water level file currently selected.
                 Cannot save graph layout.
               </font>''')

            self.msgError.setText(
            '''<b>Please select valid water level data file.</b>''')

            self.msgError.exec_()

            return

        if not self.hydrograph.fmeteo:

            self.ConsoleSignal.emit(
            '''<font color=red>No valid weather data file currently selected.
                 Cannot save graph layout.
               </font>''')

            self.msgError.setText(
                '<b>Please select valid weather data file.</b>')

            self.msgError.exec_()

            return

        # ----------------------------------------- Check if Layout Exists ----

        filename = self.workdir + '/graph_layout.lst'
        if not os.path.exists(filename):
            # Force the creation of a new "graph_layout.lst" file
            self.check_files()

        name_well = self.waterlvl_data.name_well
        isLayoutExist = self.hydrograph.checkLayout(name_well, filename)

        # ---------------------------------------------------- Save Layout ----

        if isLayoutExist is True:
            self.msgBox.setText(
            '''<b>A graph layout already exists for well %s.<br><br> Do
                 you want to replace it?</b>''' % name_well)
            override = self.msgBox.exec_()

            if override == self.msgBox.Yes:
                self.save_graph_layout(name_well)

            elif override == self.msgBox.No:
                self.ConsoleSignal.emit('''<font color=black>Graph layout
                               not saved for well %s.</font>''' % name_well)

        else:
            self.save_graph_layout(name_well)

    def save_graph_layout(self, name_well):
        self.update_graph_layout_parameter()
        filename = os.path.join(self.workdir, 'graph_layout.lst')
        self.hydrograph.save_layout(name_well, filename)
        msg = 'Graph layout saved successfully for well %s.' % name_well
        self.ConsoleSignal.emit('<font color=black>%s</font>' % msg)

    # =========================================================================

    def best_fit_waterlvl(self):
        if len(self.waterlvl_data.lvl) != 0:
            WLscale, WLmin = self.hydrograph.best_fit_waterlvl()
            self.waterlvl_scale.setValue(WLscale)
            self.waterlvl_max.setValue(WLmin)

    def best_fit_time(self):
        if len(self.waterlvl_data.time) != 0:
            TIME = self.waterlvl_data.time
            date0, date1 = self.hydrograph.best_fit_time(TIME)
            self.date_start_widget.setDate(QDate(date0[0], date0[1], date0[2]))
            self.date_end_widget.setDate(QDate(date1[0], date1[1], date1[2]))

    # =========================================================================

    def select_save_path(self):

        name_well = self.waterlvl_data.name_well
        dialog_dir = self.save_fig_dir + '/hydrograph_' + name_well

        dialog = QtGui.QFileDialog()
        dialog.setConfirmOverwrite(True)
        fname, ftype = dialog.getSaveFileName(
                                    caption="Save Figure", dir=dialog_dir,
                                    filter=('*.pdf;;*.svg'))

        if fname:

            if fname[-4:] != ftype[1:]:
                # Add a file extension if there is none
                fname = fname + ftype[1:]

            self.save_fig_dir = os.path.dirname(fname)
            self.save_figure(fname)

    def save_figure(self, fname):  # ==========================================

        self.hydrograph.generate_hydrograph(self.meteo_data)
        self.hydrograph.savefig(fname)

    def draw_hydrograph(self):  # =============================================

        if not self.fwaterlvl:
            console_text = ('<font color=red>Please select a valid water ' +
                            'level data file</font>')
            self.ConsoleSignal.emit(console_text)
            self.emit_error_message(
                '<b>Please select a valid Water Level Data File first.</b>')

            return

        if not self.hydrograph.fmeteo:
            console_text = ('<font color=red>Please select a valid ' +
                            'weather data file</font>')
            self.ConsoleSignal.emit(console_text)
            self.emit_error_message(
                '<b>Please select a valid Weather Data File first.</b>')

            return

        self.update_graph_layout_parameter()

        # Generate and Display Graph :

        for i in range(5):
            QtCore.QCoreApplication.processEvents()

        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.hydrograph.generate_hydrograph(self.meteo_data)
        self.hydrograph_scrollarea.load_mpl_figure(self.hydrograph)
        QtGui.QApplication.restoreOverrideCursor()

    def layout_changed(self):  # ==============================================
        """
        When an element of the graph layout is changed in the UI,
        """

        sender = self.sender()
        if self.__updateUI is False:
            return

        if sender == self.language_box:
            self.hydrograph.language = self.language_box.currentText()
            if self.hydrograph.isHydrographExists:
                self.hydrograph.draw_ylabels()
                self.hydrograph.draw_xlabels()
                self.hydrograph.set_legend()

            self.weather_avg_graph.set_lang(self.language_box.currentText())

        elif sender in [self.waterlvl_max, self.waterlvl_scale]:
            self.hydrograph.WLmin = self.waterlvl_max.value()
            self.hydrograph.WLscale = self.waterlvl_scale.value()
            if self.hydrograph.isHydrographExists:
                self.hydrograph.update_waterlvl_scale()
                self.hydrograph.draw_ylabels()

        elif sender == self.NZGridWL_spinBox:
            self.hydrograph.NZGrid = self.NZGridWL_spinBox.value()
            if self.hydrograph.isHydrographExists:
                self.hydrograph.update_waterlvl_scale()
                self.hydrograph.update_precip_scale()
                self.hydrograph.draw_ylabels()

        elif sender == self.Ptot_scale:
            self.hydrograph.RAINscale = self.Ptot_scale.value()
            if self.hydrograph.isHydrographExists:
                self.hydrograph.update_precip_scale()
                self.hydrograph.draw_ylabels()

        elif sender == self.datum_widget:

            self.hydrograph.WLdatum = self.datum_widget.currentIndex()

            # ---- compute new WLmin ----

            # This is calculated so that trailing zeros in the altitude of the
            # well is not carried to the y axis labels, so that they remain a
            # int multiple of *WLscale*.

            yoffset = int(self.waterlvl_data.ALT/self.hydrograph.WLscale)
            yoffset *= self.hydrograph.WLscale

            self.hydrograph.WLmin = (yoffset - self.hydrograph.WLmin)
            self.waterlvl_max.setValue(self.hydrograph.WLmin)

            # ---- Update graph and draw ----

            if self.hydrograph.isHydrographExists:
                self.hydrograph.update_waterlvl_scale()
                self.hydrograph.draw_waterlvl()
                self.hydrograph.draw_ylabels()

        elif sender in [self.date_start_widget, self.date_end_widget]:
            year = self.date_start_widget.date().year()
            month = self.date_start_widget.date().month()
            day = 1
            date = xldate_from_date_tuple((year, month, day), 0)
            self.hydrograph.TIMEmin = date

            year = self.date_end_widget.date().year()
            month = self.date_end_widget.date().month()
            day = 1
            date = xldate_from_date_tuple((year, month, day), 0)
            self.hydrograph.TIMEmax = date

            if self.hydrograph.isHydrographExists:
                self.hydrograph.set_time_scale()
                self.hydrograph.draw_weather()
                self.hydrograph.draw_figure_title()

        elif sender == self.dateDispFreq_spinBox:
            self.hydrograph.date_labels_display_pattern = \
                self.dateDispFreq_spinBox.value()

            if self.hydrograph.isHydrographExists:
                self.hydrograph.set_time_scale()
                self.hydrograph.draw_xlabels()

        elif sender == self.page_setup_win:
            self.hydrograph.fwidth = self.page_setup_win.pageSize[0]
            self.hydrograph.fheight = self.page_setup_win.pageSize[1]
            self.hydrograph.va_ratio = self.page_setup_win.va_ratio

            self.hydrograph.trend_line = int(self.page_setup_win.isTrendLine)
            self.hydrograph.isLegend = int(self.page_setup_win.isLegend)
            self.hydrograph.isGraphTitle = \
                int(self.page_setup_win.isGraphTitle)
            if self.hydrograph.isHydrographExists:
                self.hydrograph.update_fig_size()
                # Implicitly call : set_margins()
                #                   draw_ylabels()
                #                   set_time_scale()
                #                   draw_figure_title

                self.hydrograph.draw_waterlvl()
                self.hydrograph.set_legend()

        # ---------------------------------------- Weather Data resampling ----

        elif sender == self.qweather_bin:
            self.hydrograph.bwidth_indx = self.qweather_bin.currentIndex()
            if self.hydrograph.isHydrographExists:
                self.hydrograph.resample_bin()
                self.hydrograph.draw_weather()
                self.hydrograph.draw_ylabels()

        # ---------------------------------------------- Scale Data Labels ----

        elif sender == self.time_scale_label:
            self.hydrograph.datemode = self.time_scale_label.currentText()

            year = self.date_start_widget.date().year()
            month = self.date_start_widget.date().month()
            date = xldate_from_date_tuple((year, month, 1), 0)
            self.hydrograph.TIMEmin = date

            year = self.date_end_widget.date().year()
            month = self.date_end_widget.date().month()
            date = xldate_from_date_tuple((year, month, 1), 0)
            self.hydrograph.TIMEmax = date

            if self.hydrograph.isHydrographExists:
                self.hydrograph.set_time_scale()
                self.hydrograph.draw_weather()

        else:
            print('No action for this widget yet.')

        # !!!! temporary fix until I can find a better solution !!!!

#        sender.blockSignals(True)
        if type(sender) in [QtGui.QDoubleSpinBox, QtGui.QSpinBox]:
            sender.setReadOnly(True)

        for i in range(10):
            QtCore.QCoreApplication.processEvents()
        self.hydrograph_scrollarea.load_mpl_figure(self.hydrograph)
        for i in range(10):
            QtCore.QCoreApplication.processEvents()

        if type(sender) in [QtGui.QDoubleSpinBox, QtGui.QSpinBox]:
            sender.setReadOnly(False)
#        sender.blockSignals(False)


###############################################################################


class ColorsSetupWin(QtGui.QWidget):                         # ColorsSetupWin #

    newColorSetupSent = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(ColorsSetupWin, self).__init__(parent)

        self.setWindowTitle('Colors Palette Setup')
        self.setWindowFlags(QtCore.Qt.Window)

        self.__initUI__()

    def __initUI__(self):  # ==================================================

        # Toolbar :

        toolbar_widget = QtGui.QWidget()

        btn_apply = QtGui.QPushButton('Apply')
        btn_apply.clicked.connect(self.btn_apply_isClicked)
        btn_cancel = QtGui.QPushButton('Cancel')
        btn_cancel.clicked.connect(self.close)
        btn_OK = QtGui.QPushButton('OK')
        btn_OK.clicked.connect(self.btn_OK_isClicked)
        btn_reset = QtGui.QPushButton('Reset Defaults')
        btn_reset.clicked.connect(self.reset_defaults)

        toolbar_layout = QtGui.QGridLayout()
        toolbar_layout.addWidget(btn_reset, 1, 0, 1, 3)
        toolbar_layout.addWidget(btn_OK, 2, 0)
        toolbar_layout.addWidget(btn_cancel, 2, 1)
        toolbar_layout.addWidget(btn_apply, 2, 2)

        toolbar_layout.setColumnStretch(3, 100)
        toolbar_layout.setRowStretch(0, 100)

        toolbar_widget.setLayout(toolbar_layout)

        # Color Grid :

        colorsDB = hydrograph.Colors()
        colorsDB.load_colors_db()

        colorGrid_widget = QtGui.QWidget()

        self.colorGrid_layout = QtGui.QGridLayout()
        for i in range(len(colorsDB.rgb)):
            self.colorGrid_layout.addWidget(
                QtGui.QLabel('%s :' % colorsDB.labels[i]), i, 0)

            btn = QtGui.QToolButton()
            btn.setAutoRaise(True)
            btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(self.pick_color)

            self.colorGrid_layout.addWidget(btn, i, 3)
        self.load_colors()
        self.colorGrid_layout.setColumnStretch(2, 100)

        colorGrid_widget.setLayout(self.colorGrid_layout)

        # Main Layout :

        main_layout = QtGui.QGridLayout()
        main_layout.addWidget(colorGrid_widget, 0, 0)
        main_layout.addWidget(toolbar_widget, 1, 0)
        self.setLayout(main_layout)

    def load_colors(self):   # ================================================

        colorsDB = hydrograph.Colors()
        colorsDB.load_colors_db()

        nrow = self.colorGrid_layout.rowCount()
        for row in range(nrow):
            item = self.colorGrid_layout.itemAtPosition(row, 3).widget()
            item.setStyleSheet("background-color: rgb(%i,%i,%i)" %
                                   (colorsDB.RGB[row][0],
                                    colorsDB.RGB[row][1],
                                    colorsDB.RGB[row][2])
                               )

    def reset_defaults(self): #============================= Reset Deafaults ==

        colorsDB = hydrograph.Colors()

        nrow = self.colorGrid_layout.rowCount()
        for row in range(nrow):
            btn = self.colorGrid_layout.itemAtPosition(row, 3).widget()
            btn.setStyleSheet("background-color: rgb(%i,%i,%i)" %
                                  (colorsDB.RGB[row][0],
                                   colorsDB.RGB[row][1],
                                   colorsDB.RGB[row][2])
                              )

    def pick_color(self):  # =============================== Pick New Colors ==

        sender = self.sender()
        color = QtGui.QColorDialog.getColor(sender.palette().base().color())
        if color.isValid():
            rgb = color.getRgb()[:-1]
            sender.setStyleSheet("background-color: rgb(%i,%i,%i)" % rgb)

    def btn_OK_isClicked(self): #======================================== OK ==
        self.btn_apply_isClicked()
        self.close()

    def btn_apply_isClicked(self): #================================== Apply ==

        colorsDB = hydrograph.Colors()
        colorsDB.load_colors_db()

        nrow = self.colorGrid_layout.rowCount()
        for row in range(nrow):
            item = self.colorGrid_layout.itemAtPosition(row, 3).widget()
            rgb = item.palette().base().color().getRgb()[:-1]

            colorsDB.RGB[row] = [rgb[0], rgb[1], rgb[2]]
            colorsDB.rgb[row] = [rgb[0]/255., rgb[1]/255., rgb[2]/255.]

        colorsDB.save_colors_db()
        self.newColorSetupSent.emit(True)

    def closeEvent(self, event): #==================================== Close ==
        super(ColorsSetupWin, self).closeEvent(event)

        #---- Refresh UI ----

        # If cancel or X is clicked, the parameters will be reset to
        # the values they had the last time "Accept" button was
        # clicked.

        self.load_colors()

    def show(self): #================================================== Show ==
        super(ColorsSetupWin, self).show()
        self.activateWindow()
        self.raise_()

        qr = self.frameGeometry()
        if self.parentWidget():
            parent = self.parentWidget()

            wp = parent.frameGeometry().width()
            hp = parent.frameGeometry().height()
            cp = parent.mapToGlobal(QtCore.QPoint(wp/2., hp/2.))
        else:
            cp = QtGui.QDesktopWidget().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.setFixedSize(self.size())


# =============================================================================


class PageSetupWin(QtGui.QWidget):

    newPageSetupSent = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(PageSetupWin, self).__init__(parent)

        self.setWindowTitle('Page Setup')
        self.setWindowFlags(QtCore.Qt.Window)

        # ---- Default Values ----

        self.pageSize = (11., 8.5)
        self.isLegend = True
        self.isGraphTitle = True
        self.isTrendLine = False
        self.va_ratio = 0.18
        self.NZGrid = 8

        self.initUI()

    def initUI(self): #============================================= Init UI ==

        #---- Toolbar ----

        toolbar_widget = QtGui.QWidget()

        btn_apply = QtGui.QPushButton('Apply')
        btn_apply.clicked.connect(self.btn_apply_isClicked)
        btn_cancel = QtGui.QPushButton('Cancel')
        btn_cancel.clicked.connect(self.close)
        btn_OK = QtGui.QPushButton('OK')
        btn_OK.clicked.connect(self.btn_OK_isClicked)

        toolbar_layout = QtGui.QGridLayout()
        toolbar_layout.addWidget(btn_OK, 0, 1)
        toolbar_layout.addWidget(btn_cancel, 0, 2)
        toolbar_layout.addWidget(btn_apply, 0, 3)
        toolbar_layout.setColumnStretch(0, 100)

        toolbar_widget.setLayout(toolbar_layout)

        #---- Figure Size ----

        figSize_widget =  QtGui.QWidget()

        self.fwidth = QtGui.QDoubleSpinBox()
        self.fwidth.setSingleStep(0.05)
        self.fwidth.setMinimum(5.)
        self.fwidth.setValue(self.pageSize[0])
        self.fwidth.setSuffix('  in')
        self.fwidth.setAlignment(QtCore.Qt.AlignCenter)

        self.fheight = QtGui.QDoubleSpinBox()
        self.fheight.setSingleStep(0.05)
        self.fheight.setMinimum(5.)
        self.fheight.setValue(self.pageSize[1])
        self.fheight.setSuffix('  in')
        self.fheight.setAlignment(QtCore.Qt.AlignCenter)

        self.va_ratio_spinBox = QtGui.QDoubleSpinBox()
        self.va_ratio_spinBox.setSingleStep(0.01)
        self.va_ratio_spinBox.setMinimum(0.1)
        self.va_ratio_spinBox.setMaximum(0.95)
        self.va_ratio_spinBox.setValue(self.va_ratio)
        self.va_ratio_spinBox.setAlignment(QtCore.Qt.AlignCenter)

        class QTitle(QtGui.QLabel):
            def __init__(self, label, parent=None):
                super(QTitle, self).__init__(label, parent)
                self.setAlignment(QtCore.Qt.AlignCenter)

        figSize_layout = QtGui.QGridLayout()
        row = 0
        figSize_layout.addWidget(QTitle('FIGURE SIZE\n'), row, 0, 1, 3)
        row += 1
        figSize_layout.addWidget(QtGui.QLabel('Figure Width :'), row, 0)
        figSize_layout.addWidget(self.fwidth, row, 2)
        row += 1
        figSize_layout.addWidget(QtGui.QLabel('Figure Height :'), row, 0)
        figSize_layout.addWidget(self.fheight, row, 2)
        row += 1
        figSize_layout.addWidget(
            QtGui.QLabel('Top/Bottom Axes Ratio :'), row, 0)
        figSize_layout.addWidget(self.va_ratio_spinBox, row, 2)
        row += 1
        figSize_layout.addWidget(myqt.HSep(), row, 0, 1, 3)
        row += 1
        figSize_layout.addWidget(
            QTitle('GRAPH ELEMENTS VISIBILITY\n'), row, 0, 1, 3)

        figSize_layout.setColumnStretch(1, 100)
        figSize_layout.setContentsMargins(0, 0, 0, 0) # (L, T, R, B)

        figSize_widget.setLayout(figSize_layout)

        #---- Legend ----

        legend_widget =  QtGui.QWidget()

        self.legend_on = QtGui.QRadioButton('On')
        self.legend_on.toggle()
        self.legend_off = QtGui.QRadioButton('Off')

        legend_layout = QtGui.QGridLayout()
        legend_layout.addWidget(QtGui.QLabel('Legend :'), 0, 0)
        legend_layout.addWidget(self.legend_on, 0, 2)
        legend_layout.addWidget(self.legend_off, 0, 3)
        legend_layout.setColumnStretch(1, 100)
        legend_layout.setContentsMargins(0, 0, 0, 0)  # (L, T, R, B)

        legend_widget.setLayout(legend_layout)

        #----- Graph title -----

        title_widget = QtGui.QWidget()

        self.title_on = QtGui.QRadioButton('On')
        self.title_on.toggle()
        self.title_off = QtGui.QRadioButton('Off')

        title_layout = QtGui.QGridLayout()
        title_layout.addWidget(QtGui.QLabel('Graph Title :'), 0, 0)
        title_layout.addWidget(self.title_on, 0, 2)
        title_layout.addWidget(self.title_off, 0, 3)
        title_layout.setColumnStretch(1, 100)
        title_layout.setContentsMargins(0, 0, 0, 0)  # (L, T, R, B)

        title_widget.setLayout(title_layout)

        #---- Trend Line ----

        trend_widget = QtGui.QWidget()

        self.trend_on = QtGui.QRadioButton('On')
        self.trend_off = QtGui.QRadioButton('Off')
        self.trend_off.toggle()

        trend_layout = QtGui.QGridLayout()
        trend_layout.addWidget(QtGui.QLabel('Water Level Trend :'), 0, 0)
        trend_layout.addWidget(self.trend_on, 0, 2)
        trend_layout.addWidget(self.trend_off, 0, 3)
        trend_layout.setColumnStretch(1, 100)
        trend_layout.setContentsMargins(0, 0, 0, 0)  # (L, T, R, B)

        trend_widget.setLayout(trend_layout)

        #---- Main Layout ----

        main_layout = QtGui.QGridLayout()
        main_layout.addWidget(figSize_widget, 0, 0)
        main_layout.addWidget(legend_widget, 2, 0)
        main_layout.addWidget(title_widget, 3, 0)
        main_layout.addWidget(trend_widget, 4, 0)
        main_layout.addWidget(toolbar_widget, 5, 0)

        self.setLayout(main_layout)

    def btn_OK_isClicked(self):  # ============================================
        self.btn_apply_isClicked()
        self.close()

    def btn_apply_isClicked(self):  # =========================================

        self.pageSize = (self.fwidth.value(), self.fheight.value())
        self.isLegend = self.legend_on.isChecked()
        self.isGraphTitle = self.title_on.isChecked()
        self.isTrendLine = self.trend_on.isChecked()
        self.va_ratio = self.va_ratio_spinBox.value()

        self.newPageSetupSent.emit(True)

    def closeEvent(self, event):  # ===========================================
        super(PageSetupWin, self).closeEvent(event)

        #---- Refresh UI ----

        # If cancel or X is clicked, the parameters will be reset to
        # the values they had the last time "Accept" button was
        # clicked.

        self.fwidth.setValue(self.pageSize[0])
        self.fheight.setValue(self.pageSize[1])
        self.va_ratio_spinBox.setValue(self.va_ratio)

        if self.isLegend is True:
            self.legend_on.toggle()
        else:
            self.legend_off.toggle()

        if self.isGraphTitle is True:
            self.title_on.toggle()
        else:
            self.title_off.toggle()

        if self.isTrendLine is True:
            self.trend_on.toggle()
        else:
            self.trend_off.toggle()

    def show(self):  # ========================================================
        super(PageSetupWin, self).show()
        self.activateWindow()
        self.raise_()

        qr = self.frameGeometry()
        if self.parentWidget():
            parent = self.parentWidget()

            wp = parent.frameGeometry().width()
            hp = parent.frameGeometry().height()
            cp = parent.mapToGlobal(QtCore.QPoint(wp/2., hp/2.))
        else:
            cp = QtGui.QDesktopWidget().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.setFixedSize(self.size())

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)

    Hydroprint = HydroprintGUI()
    Hydroprint.set_workdir("../Projects/Project4Testing")
    Hydroprint.show()

    sys.exit(app.exec_())
