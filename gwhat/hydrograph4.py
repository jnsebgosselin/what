# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.
#
# The function filt_data is based on the codes provided by
# StackOverflow user Alleo.
# https://stackoverflow.com/a/27681394/4481445
# -----------------------------------------------------------------------------

# ---- Standard library imports
from calendar import monthrange

# ---- Third party imports
import numpy as np
import matplotlib as mpl
from matplotlib.patches import Rectangle
from matplotlib.figure import Figure
from matplotlib.transforms import ScaledTranslation
# import matplotlib.patches
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import pandas as pd

from xlrd.xldate import xldate_from_date_tuple
from xlrd import xldate_as_tuple

# ---- Local imports
from gwhat.utils.dates import datetimeindex_to_xldates
from gwhat.common.utils import calc_dist_from_coord
from gwhat.config.colors import ColorsManager

mpl.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Arial']})


class LabelDatabase():

    def __init__(self, language):  # ------------------------------- English --

        self.temperature = 'Temperature (°C)'
        self.mbgs = 'Water Level (mbgs)'
        self.masl = 'Water Level (masl)'
        self.precip = 'Precipitation (%s)'
        self.precip_units = ['mm/day', 'mm/week', 'mm/month', 'mm/year']
        self.title = 'Well %s'
        self.station_meteo = ('Weather Station %s\n' +
                              '(located %0.1f km from the well)')
        self.month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

        self.legend = ['Snow', 'Rain', 'Air temperature', 'Missing data',
                       'Water level (trend)', 'Water level',
                       'Water level (data)', 'Manual measures',
                       'Estimated recession']

        if language.lower() == 'french':  # ------------------------- French --

            self.mbgs = "Niveau d'eau (m sous la surface)"
            self.masl = "Niveau d'eau (masl)"
            self.precip = 'Précipitations (%s)'
            self.precip_units = ['mm/jour', 'mm/sem.', 'mm/mois', 'mm/an']
            self.temperature = 'Température (°C)'
            self.title = 'Puits %s'
            self.station_meteo = ('Station météo %s\n' +
                                  '(située à %0.1f km du puits)')
            self.month_names = ["JAN", "FÉV", "MAR", "AVR", "MAI", "JUN",
                                "JUL", "AOÛ", "SEP", "OCT", "NOV", "DÉC"]

            self.legend = ['Neige', 'Pluie', "Température de l'air",
                           'Données manquantes',
                           "Niveau d'eau (tendance)", "Niveaux d'eau observés",
                           "Niveau d'eau (données)", 'Mesures manuelles',
                           'Récession simulée']


class Hydrograph(Figure):
    def __init__(self):
        super().__init__(facecolor='white', frameon=True, edgecolor='black')

        # set canvas and renderer :

        self.set_canvas(FigureCanvas(self))
        self.canvas.get_renderer()

        self.__isHydrographExists = False

        # Fig Init :

        self.fwidth = 11
        self.fheight = 7
        self.NZGrid = 8  # Number of interval in the grid of the bottom part

        # Vertical height ratio between the top part  and the bottom part
        self.va_ratio = 0.2

        # Graph labels language :
        self.language = 'english'

        # Database :
        self.colorsDB = ColorsManager()

        # Scales :

        self.WLmin = 0
        self.WLscale = 0

        self.RAINscale = 20

        self.TIMEmin = 36526
        self.TIMEmax = 36526

        # Legend  and Title :

        self.isLegend = 1
        self.isGraphTitle = 1

        # Layout Options :

        self.WLdatum = 0  # 0: mbgs;  1: masl
        self.trend_line = 0
        self.trend_MAW = 30
        # trend_MAW = width of the Moving Average Window used to
        #             smooth the water level data
        self.meteo_on = True
        self.glue_wl_on = False
        self.mrc_wl_on = False
        self.gridLines = 2  # 0 -> None, 1 -> "-" 2 -> ":"
        self.datemode = 'Month'  # 'month' or 'year'
        self.label_font_size = 14
        self.date_labels_pattern = 2
        self._figframe_lw = 0

        # Waterlvl & Meteo Obj :

        self.wldset = None
        self.wxdset = None
        self.gluedf = None

        # Daily Weather :

        self.dist = 0
        self.name_meteo = ''
        self.TIMEmeteo = np.array([])  # Time in Excel numeric format (days)
        self.TMAX = np.array([])  # Daily maximum temperature (deg C)
        self.PTOT = np.array([])
        self.RAIN = np.array([])

        # Bin Redistributed Weather :

        self.bTIME = np.array([])
        self.bTMAX = np.array([])
        self.bPTOT = np.array([])
        self.bRAIN = np.array([])

        self.bwidth_indx = 1
        #   0: 1 day;
        #   1: 1 week;
        #   2: 1 month;
        #   3: 1 year;

        self.NMissPtot = []

    @property
    def meteo_on(self):
        """Controls whether meteo data are plotted or not."""
        return (self.__meteo_on and self.wxdset is not None)

    @meteo_on.setter
    def meteo_on(self, x):
        self.__meteo_on = bool(x)

    def set_meteo_on(self, x):
        """Set whether the meteo data are plotted or not."""
        self.meteo_on = x
        if self.__isHydrographExists:
            self.ax3.set_visible(self.meteo_on)
            self.ax4.set_visible(self.meteo_on)
            self.setup_waterlvl_scale()
            self.draw_weather()

    @property
    def glue_wl_on(self):
        """Controls whether glue water levels are plotted or not."""
        return (self.__glue_wl_on and self.gluedf is not None)

    @glue_wl_on.setter
    def glue_wl_on(self, x):
        self.__glue_wl_on = bool(x)

    def set_glue_wl_on(self, x):
        """Set whether the glue water levels data are plotted or not."""
        self.glue_wl_on = x
        if self.__isHydrographExists:
            self.draw_glue_wl()
            self.setup_legend()

    @property
    def mrc_wl_on(self):
        """Return whether the mrc water levels must be plotted or not."""
        return (self.__mrc_wl_on and self.wldset is not None and
                self.wldset.mrc_exists())

    @mrc_wl_on.setter
    def mrc_wl_on(self, x):
        """Set whether the mrc water levels data must plotted or not."""
        self.__mrc_wl_on = bool(x)

    def set_mrc_wl_on(self, x):
        """Set whether the mrc water levels data must plotted or not."""
        self.mrc_wl_on = x
        if self.__isHydrographExists:
            self.draw_mrc_wl()
            self.setup_legend()

    def set_figframe_lw(self, x):
        """
        Set the line thickness of the frame that encloses the entire figure.
        """
        self._figframe_lw = x
        self.patch.set_linewidth(self._figframe_lw)

    @property
    def language(self):
        return self.__language

    @language.setter
    def language(self, x):
        if x.lower() in ['english', 'french']:
            self.__language = x
        else:
            print('WARNING: Language not supported. '
                  'Setting language to "english".')
            self.__language = 'english'

    @property
    def isHydrographExists(self):
        return self.__isHydrographExists

    def set_wldset(self, wldset):
        self.wldset = wldset

    def set_wxdset(self, wxdset):
        self.wxdset = wxdset

    def set_gluedf(self, gluedf):
        """Set the namespace for the GLUE dataframe."""
        self.gluedf = gluedf
        self.draw_glue_wl()
        self.setup_legend()

    def clf(self, *args, **kargs):
        """Matplotlib override to set internal flag."""
        self.__isHydrographExists = False
        super(Hydrograph, self).clf(*args, **kargs)

    def savefig(self, fname, dpi=300):
        """Matplotlib override to set frameon when saving."""
        super().savefig(fname, facecolor='white', edgecolor='black', dpi=dpi)

    def generate_hydrograph(self, wxdset=None, wldset=None):
        wxdset = self.wxdset if wxdset is None else wxdset
        wldset = self.wldset if wldset is None else wldset

        # Reinit the figure.
        self.clf()
        self.set_size_inches(self.fwidth, self.fheight, forward=True)
        self.patch.set_linewidth(self._figframe_lw)

        # Assign Weather Data.
        if self.wxdset is None:
            self.name_meteo = ''
            self.TIMEmeteo = np.array([])
            self.TMAX = np.array([])
            self.PTOT = np.array([])
            self.RAIN = np.array([])
        else:
            self.name_meteo = wxdset.metadata['Station Name']
            self.TIMEmeteo = datetimeindex_to_xldates(wxdset.data.index)
            self.TMAX = wxdset.data['Tmax'].values
            self.PTOT = wxdset.data['Ptot'].values
            self.RAIN = wxdset.data['Rain'].values

        # Resample Data in Bins :

        self.resample_bin()

        # -------------------------------------------------- AXES CREATION ----

        # ---- Time (host) ----

        # Also holds the gridlines.

        self.ax1 = self.add_axes([0, 0, 1, 1], frameon=False)
        self.ax1.set_zorder(100)

        # ---- Frame ----

        # Only used to display the frame so it is always on top.

        self.ax0 = self.add_axes(self.ax1.get_position(), frameon=True)
        self.ax0.patch.set_visible(False)
        self.ax0.set_zorder(self.ax1.get_zorder() + 200)
        self.ax0.tick_params(bottom=False, top=False, left=False, right=False,
                             labelbottom=False, labelleft=False)

        # ---- Water Levels ----

        self.ax2 = self.add_axes(self.ax1.get_position(), frameon=False,
                                 label='axes2', sharex=self.ax1)
        self.ax2.set_zorder(self.ax1.get_zorder() + 100)
        self.ax2.yaxis.set_ticks_position('left')
        self.ax2.yaxis.set_label_position('left')
        self.ax2.tick_params(axis='y', direction='out', labelsize=10)

        # ---- Precipitation ----

        self.ax3 = self.add_axes(self.ax1.get_position(), frameon=False,
                                 label='axes3', sharex=self.ax1)
        self.ax3.set_zorder(self.ax1.get_zorder() + 150)
        self.ax3.set_navigate(False)

        # ---- Air Temperature ----

        self.ax4 = self.add_axes(self.ax1.get_position(), frameon=False,
                                 label='axes4', sharex=self.ax1)
        self.ax4.set_zorder(self.ax1.get_zorder() + 150)
        self.ax4.set_navigate(False)
        self.ax4.set_axisbelow(True)
        self.ax4.tick_params(bottom=False, top=False, left=False,
                             right=False, labelbottom=False, labelleft=False)

        if self.meteo_on is False:
            self.ax3.set_visible(False)
            self.ax4.set_visible(False)

        # ---- Bottom Graph Grid ----

        self.axLow = self.add_axes(self.ax1.get_position(), frameon=False,
                                   label='axLow', sharex=self.ax1)
        self.axLow.patch.set_visible(False)
        self.axLow.set_zorder(self.ax2.get_zorder() - 50)
        self.axLow.tick_params(bottom=False, top=False, left=False,
                               right=False, labelbottom=False, labelleft=False)

        self.setup_waterlvl_scale()

        # -------------------------------------------------- Remove Spines ----

        for axe in self.axes[2:]:
            for loc in axe.spines:
                axe.spines[loc].set_visible(False)

        # ------------------------------------------------- Update margins ----

        self.bottom_margin = 0.75
        self.set_margins()  # set margins for all the axes

        # --------------------------------------------------- FIGURE TITLE ----

        # Calculate horizontal distance between weather station and
        # observation well.
        if self.wxdset is not None:
            self.dist = calc_dist_from_coord(
                wldset['Latitude'], wldset['Longitude'],
                wxdset.metadata['Latitude'], wxdset.metadata['Longitude'])
        else:
            self.dist = 0

        # Weather Station name and distance to the well
        self.text1 = self.ax0.text(0, 1, '', va='bottom', ha='left',
                                   rotation=0, fontsize=10)

        # Well Name
        self.figTitle = self.ax0.text(0, 1, '', fontsize=18,
                                      ha='left', va='bottom')

        self.draw_figure_title()

        # ----------------------------------------------------------- TIME ----

        self.xlabels = []
        self.set_time_scale()

        self.ax1.xaxis.set_ticklabels([])
        self.ax1.xaxis.set_ticks_position('bottom')
        self.ax1.tick_params(axis='x', direction='out')
        self.ax1.tick_params(top=False, left=False, right=False,
                             labeltop=False, labelleft=False, labelright=False)

        self.set_gridLines()

        # ---- Init water level artists

        # Continuous Line Datalogger
        self.l1_ax2, = self.ax2.plot(
            [], [], '-', zorder=10, lw=1, color=self.colorsDB.rgb['WL solid'])

        # Data Point Datalogger
        self.l2_ax2, = self.ax2.plot(
            [], [], '.', color=self.colorsDB.rgb['WL data'], markersize=5)

        # Manual Mesures
        self.h_WLmes, = self.ax2.plot(
            [], [], 'o', zorder=15, label='Manual measures',
            markerfacecolor='none', markersize=5, markeredgewidth=1.5,
            mec=self.colorsDB.rgb['WL obs'])

        # Predicted Recession Curves
        self._mrc_plt, = self.ax2.plot(
            [], [], color='red', lw=1.5, dashes=[5, 3], zorder=100,
            alpha=0.85)

        # Predicted GLUE water levels
        self.glue_plt, = self.ax2.plot([], [])

        self.draw_waterlvl()
        self.draw_glue_wl()
        self.draw_mrc_wl()

        # ---- Init weather artists

        # ---- PRECIPITATION -----

        self.ax3.yaxis.set_ticks_position('right')
        self.ax3.yaxis.set_label_position('right')
        self.ax3.tick_params(axis='y', direction='out', labelsize=10)

        self.PTOT_bar, = self.ax3.plot([], [])
        self.RAIN_bar, = self.ax3.plot([], [])
        self.baseline, = self.ax3.plot(
            [self.TIMEmin, self.TIMEmax], [0, 0], 'k')

        # ---- AIR TEMPERATURE -----

        TEMPmin = -40
        TEMPscale = 20
        TEMPmax = 40

        self.ax4.axis(ymin=TEMPmin, ymax=TEMPmax)

        yticks_position = np.array([TEMPmin, 0, TEMPmax])
        yticks_position = np.arange(
            TEMPmin, TEMPmax + TEMPscale / 2, TEMPscale)
        self.ax4.set_yticks(yticks_position)
        self.ax4.yaxis.set_ticks_position('left')
        self.ax4.tick_params(axis='y', direction='out', labelsize=10)
        self.ax4.yaxis.set_label_position('left')

        self.ax4.set_yticks([-20, 20], minor=True)
        self.ax4.tick_params(axis='y', which='minor', length=0)
        self.ax4.xaxis.set_ticklabels([], minor=True)

        self.l1_ax4, = self.ax4.plot([], [])  # fill shape
        self.l2_ax4, = self.ax4.plot(
            [], [], color='black', lw=1)  # contour line

        # ---- MISSING VALUES MARKERS

        # Precipitation.
        vshift = 5 / 72
        offset = ScaledTranslation(0, vshift, self.dpi_scale_trans)
        if self.wxdset is not None:
            t1 = pd.DataFrame(self.wxdset.missing_value_indexes['Ptot'],
                              index=self.wxdset.missing_value_indexes['Ptot'],
                              columns=['datetime'])
            t2 = pd.DataFrame(self.wxdset.missing_value_indexes['Ptot'] +
                              pd.Timedelta('1 days'),
                              self.wxdset.missing_value_indexes['Ptot'] +
                              pd.Timedelta('1 days'),
                              columns=['datetime'])
            time = datetimeindex_to_xldates(pd.DatetimeIndex(
                pd.concat([t1, t2], axis=0)
                .drop_duplicates()
                .resample('1D')
                .asfreq()
                ['datetime']
                ))
            y = np.ones(len(time)) * self.ax4.get_ylim()[0]
        else:
            time, y = [], []
        self.lmiss_ax4, = self.ax4.plot(
            time, y, ls='-', solid_capstyle='projecting', lw=1, c='red',
            transform=self.ax4.transData + offset)

        # Air Temperature.
        offset = ScaledTranslation(0, -vshift, self.dpi_scale_trans)
        if self.wxdset is not None:
            t1 = pd.DataFrame(self.wxdset.missing_value_indexes['Tmax'],
                              index=self.wxdset.missing_value_indexes['Tmax'],
                              columns=['datetime'])
            t2 = pd.DataFrame(self.wxdset.missing_value_indexes['Tmax'] +
                              pd.Timedelta('1 days'),
                              self.wxdset.missing_value_indexes['Tmax'] +
                              pd.Timedelta('1 days'),
                              columns=['datetime'])
            time = datetimeindex_to_xldates(pd.DatetimeIndex(
                pd.concat([t1, t2], axis=0)
                .drop_duplicates()
                .resample('1D')
                .asfreq()
                ['datetime']
                ))
            y = np.ones(len(time)) * self.ax4.get_ylim()[1]
        else:
            time, y = [], []
        self.ax4.plot(time, y, ls='-', solid_capstyle='projecting',
                      lw=1., c='red', transform=self.ax4.transData + offset)

        self.draw_weather()
        self.draw_ylabels()
        self.setup_legend()

        self.__isHydrographExists = True

    def setup_legend(self):
        """Setup the legend of the graph."""
        if self.isLegend == 1:
            labelDB = LabelDatabase(self.language).legend
            lg_handles = []
            lg_labels = []
            if self.meteo_on:
                colors = self.colorsDB.rgb
                # Snow
                lg_handles.append(Rectangle(
                    (0, 0), 1, 1, fc=colors['Snow'], ec=colors['Snow']))
                lg_labels.append(labelDB[0])

                # Rain
                lg_handles.append(Rectangle(
                    (0, 0), 1, 1, fc=colors['Rain'], ec=colors['Rain']))
                lg_labels.append(labelDB[1])

                # Air Temperature
                lg_handles.append(Rectangle(
                    (0, 0), 1, 1, fc=colors['Tair'], ec='black'))
                lg_labels.append(labelDB[2])

                # Missing Data Markers
                if len(self.lmiss_ax4.get_xdata()):
                    lg_handles.append(self.lmiss_ax4)
                    lg_labels.append(labelDB[3])

            # Continuous Line Datalogger
            lg_handles.append(self.l1_ax2)
            if self.trend_line == 1:
                lg_labels.append(labelDB[4])
            else:
                lg_labels.append(labelDB[5])

            # Water Levels (data points)
            if self.trend_line == 1:
                lg_handles.append(self.l2_ax2)
                lg_labels.append(labelDB[6])

            # Manual Measures
            TIMEmes, WLmes = self.wldset.get_wlmeas()
            if len(TIMEmes) > 0:
                lg_handles.append(self.h_WLmes)
                lg_labels.append(labelDB[7])

            if self.mrc_wl_on:
                lg_labels.append(labelDB[8])
                lg_handles.append(self._mrc_plt)

            if self.glue_wl_on:
                lg_labels.append('GLUE 5/95')
                lg_handles.append(Rectangle(
                    (0, 0), 1, 1, fc='0.65', ec='0.65'))

            # Draw the legend
            # LOCS = ['right', 'center left', 'upper right', 'lower right',
            #         'center', 'lower left', 'center right', 'upper left',
            #         'upper center', 'lower center']
            # ncol = int(np.ceil(len(lg_handles)/2.))
            self.ax0.legend(lg_handles, lg_labels, bbox_to_anchor=[1, 1],
                            loc='lower right', ncol=3,
                            numpoints=1, fontsize=10, frameon=False)
            self.ax0.get_legend().set_zorder(100)
        else:
            if self.ax0.get_legend():
                self.ax0.get_legend().set_visible(False)

    def update_colors(self):
        """Update the color scheme of the figure."""
        if not self.__isHydrographExists:
            return

        self.colorsDB.load_colors()
        self.l1_ax2.set_color(self.colorsDB.rgb['WL solid'])
        self.l2_ax2.set_color(self.colorsDB.rgb['WL data'])
        self.h_WLmes.set_color(self.colorsDB.rgb['WL obs'])
        self.draw_weather()
        self.setup_legend()

    def update_fig_size(self):
        """Update the size of the figure."""
        self.set_size_inches(self.fwidth, self.fheight)
        self.set_margins()
        self.draw_ylabels()
        self.set_time_scale()

        self.canvas.draw()

    def set_margins(self):
        """Set the margins of the axes in inches."""
        fheight = self.fheight

        # --- MARGINS (Inches / Fig. Dimension) --- #

        left_margin = 0.85 / self.fwidth

        if self.meteo_on is False:
            right_margin = 0.15 / self.fwidth
        else:
            right_margin = 0.85 / self.fwidth

        bottom_margin = 0.6 / self.fheight

        top_margin = 0.25 / self.fheight
        if self.isGraphTitle == 1 or self.isLegend == 1:
            if self.meteo_on is False:
                top_margin += 0.2 / fheight
            else:
                top_margin += 0.45 / fheight

        # --- MARGINS (% of figure) --- #

        if self.meteo_on:
            va_ratio = self.va_ratio
        else:
            va_ratio = 0

        htot = 1 - (bottom_margin + top_margin)
        htop = htot * va_ratio
        hlow = htot * (1-va_ratio)
        wtot = 1 - (left_margin + right_margin)

        # Host, Frame, Water Levels, Precipitation, Air Temperature

        for i, axe in enumerate(self.axes):
            if i == 4:  # Air Temperature
                axe.set_position([left_margin, bottom_margin + hlow,
                                  wtot, htop])
            elif i in [0, 1]:  # Time, Frame
                axe.set_position([left_margin, bottom_margin, wtot, htot])

            else:
                axe.set_position([left_margin, bottom_margin, wtot, hlow])

    def draw_ylabels(self):

        labelDB = LabelDatabase(self.language)

        # ------------------------------------- Calculate LabelPadding ----

        left_margin = 0.85
        right_margin = 0.85
        if self.meteo_on is False:
            right_margin = 0.35

        axwidth = (self.fwidth - left_margin - right_margin)

        labPad = 0.3 / 2.54  # in Inches
        labPad /= axwidth   # relative coord.

        # --------------------------- YLABELS LEFT (Temp. & Waterlvl) ----

        if self.WLdatum == 0:
            lab_ax2 = labelDB.mbgs
        elif self.WLdatum == 1:
            lab_ax2 = labelDB.masl

        # ---- Water Level ---- #

        self.ax2.set_ylabel(lab_ax2, rotation=90,
                            fontsize=self.label_font_size,
                            va='bottom', ha='center')

        # Get bounding box dimensions of yaxis ticklabels for ax2
        renderer = self.canvas.get_renderer()
        self.canvas.draw()

        bbox2_left, _ = self.ax2.yaxis.get_ticklabel_extents(renderer)

        # bbox are structured in the the following way:   [[ Left , Bottom ],
        #                                                  [ Right, Top    ]]

        # Transform coordinates in ax2 coordinate system.
        bbox2_left = self.ax2.transAxes.inverted().transform(bbox2_left)

        # Calculate the labels positions in x and y.
        ylabel2_xpos = bbox2_left[0, 0] - labPad
        ylabel2_ypos = (bbox2_left[1, 1] + bbox2_left[0, 1]) / 2.

        if self.meteo_on is False:
            self.ax2.yaxis.set_label_coords(ylabel2_xpos, ylabel2_ypos)
            self.draw_figure_title()
            return

        # ------------------------------------------------ Temperature ----

        self.ax4.set_ylabel(labelDB.temperature, rotation=90, va='bottom',
                            ha='center', fontsize=self.label_font_size)

        # Get bounding box dimensions of yaxis ticklabels for ax4
        bbox4_left, _ = self.ax4.yaxis.get_ticklabel_extents(renderer)

        # Transform coordinates in ax4 coordinate system.
        bbox4_left = self.ax4.transAxes.inverted().transform(bbox4_left)

        # Calculate the labels positions in x and y.
        ylabel4_xpos = bbox4_left[0, 0] - labPad
        ylabel4_ypos = (bbox4_left[1, 1] + bbox4_left[0, 1]) / 2.

        # Take the position which is farthest from the left y axis in order
        # to have both labels on the left aligned.
        ylabel_xpos = min(ylabel2_xpos, ylabel4_xpos)

        self.ax2.yaxis.set_label_coords(ylabel_xpos, ylabel2_ypos)
        self.ax4.yaxis.set_label_coords(ylabel_xpos, ylabel4_ypos)

        # ---------------------------------------------- Precipitation ----

        label = labelDB.precip % labelDB.precip_units[self.bwidth_indx]
        self.ax3.set_ylabel(label, rotation=270, va='bottom',
                            ha='center', fontsize=self.label_font_size)

        # Get bounding box dimensions of yaxis ticklabels for ax3
        _, bbox = self.ax3.yaxis.get_ticklabel_extents(renderer)

        # Transform coordinates in ax3 coordinate system and
        # calculate the labels positions in x and y.
        bbox = self.ax3.transAxes.inverted().transform(bbox)

        ylabel3_xpos = bbox[1, 0] + labPad
        ylabel3_ypos = (bbox[1, 1] + bbox[0, 1]) / 2.

        self.ax3.yaxis.set_label_coords(ylabel3_xpos, ylabel3_ypos)

        self.draw_figure_title()

    def best_fit_waterlvl(self):
        WL = self.wldset['WL']
        if self.WLdatum == 1:  # masl
            WL = self.wldset['Elevation'] - WL

        WL = WL[~np.isnan(WL)]
        dWL = np.max(WL) - np.min(WL)
        ygrid = self.NZGrid - 5

        # --- WL Scale --- #

        SCALE = np.hstack((np.arange(0.05, 0.30, 0.05),
                           np.arange(0.3, 5.1, 0.1)))
        dSCALE = np.abs(SCALE - dWL / ygrid)
        indx = np.where(dSCALE == np.min(dSCALE))[0][0]

        self.WLscale = SCALE[indx]

        # ---- WL Min Value --- #

        if self.WLdatum == 0:  # mbgs
            N = np.ceil(np.max(WL)/self.WLscale)
        elif self.WLdatum == 1:  # masl
            # WL = self.WaterLvlObj.ALT - WL
            N = np.floor(np.min(WL) / self.WLscale)

        self.WLmin = self.WLscale * N

        return self.WLscale, self.WLmin

    def best_fit_time(self, TIME):  # =========================================

        # ----- Data Start -----

        date0 = xldate_as_tuple(TIME[0], 0)
        date0 = (date0[0], date0[1], 1)

        self.TIMEmin = xldate_from_date_tuple(date0, 0)

        # ----- Date End -----

        date1 = xldate_as_tuple(TIME[-1], 0)

        year = date1[0]
        month = date1[1] + 1
        if month > 12:
            month = 1
            year += 1

        date1 = (year, month, 1)

        self.TIMEmax = xldate_from_date_tuple(date1, 0)

        return date0, date1

    def resample_bin(self):  # ================================================

        # day; week; month; year
        self.bwidth = [1, 7, 30, 365][self.bwidth_indx]
        bwidth = self.bwidth

        if self.bwidth_indx == 0:  # daily

            self.bTIME = np.copy(self.TIMEmeteo)
            self.bTMAX = np.copy(self.TMAX)
            self.bPTOT = np.copy(self.PTOT)
            self.bRAIN = np.copy(self.RAIN)
        else:
            self.bTIME = self.bin_sum(self.TIMEmeteo, bwidth) / bwidth
            self.bTMAX = self.bin_sum(self.TMAX, bwidth) / bwidth
            self.bPTOT = self.bin_sum(self.PTOT, bwidth)
            self.bRAIN = self.bin_sum(self.RAIN, bwidth)

#        elif self.bwidth_indx == 4 : # monthly
#            print('option not yet available, kept default of 1 day')
#
#        elif self.bwidth_indx == 5 : # yearly
#            print('option not yet available, kept default of 1 day')

    def bin_sum(self, x, bwidth):  # ==========================================
        """
        Sum data x over bins of width "bwidth" starting at indice 0 of x.
        If there is residual data at the end because of the last bin being not
        complete, data are rejected and removed from the reshaped series.
        """

        bwidth = int(bwidth)
        nbin = int(np.floor(len(x) / bwidth))

        bheight = x[:nbin*bwidth].reshape(nbin, bwidth)
        bheight = np.sum(bheight, axis=1)

        return bheight

    # ---- Drawing data methods

    def draw_glue_wl(self):
        """Draw the GLUE estimated water levels envelope."""
        if self.glue_wl_on is False:
            self.glue_plt.set_visible(False)
            return
        else:
            self.glue_plt.set_visible(True)

        xlstime = self.gluedf['water levels']['time']
        wl05 = self.gluedf['water levels']['predicted'][:, 0]/1000
        wl95 = self.gluedf['water levels']['predicted'][:, 2]/1000

        self.glue_plt.remove()
        self.glue_plt = self.ax2.fill_between(
            xlstime, wl95, wl05, facecolor='0.85', lw=1, edgecolor='0.65',
            zorder=0)

    def draw_mrc_wl(self):
        """Draw the water levels predicted with the MRC."""
        if self.mrc_wl_on is False:
            self._mrc_plt.set_visible(False)
        else:
            self._mrc_plt.set_visible(True)
            mrc_data = self.wldset.get_mrc()
            self._mrc_plt.set_data(mrc_data['time'], mrc_data['recess'])

    def draw_waterlvl(self):
        """
        This method is called the first time the graph is plotted and each
        time water level datum is changed.
        """

        # ---- Logger Measures

        time = self.wldset.xldates
        if self.WLdatum == 1:  # masl
            water_lvl = self.wldset['Elevation']-self.wldset['WL']
        else:  # mbgs -> yaxis is inverted
            water_lvl = self.wldset['WL']

        if self.trend_line == 1:
            tfilt, wlfilt = filt_data(time, water_lvl, self.trend_MAW)
            self.l1_ax2.set_data(tfilt, wlfilt)
            self.l2_ax2.set_data(time, water_lvl)

        else:
            self.l1_ax2.set_data(time, water_lvl)
            self.l2_ax2.set_data([], [])

        # ---- Manual Measures

        time_wl_meas, wl_meas = self.wldset.get_wlmeas()
        if len(wl_meas) > 0:
            if self.WLdatum == 1:
                # The datum is meter above see level.
                wl_meas = self.wldset['Elevation'] - wl_meas
            self.h_WLmes.set_data(time_wl_meas, wl_meas)

    def draw_weather(self):
        """
        This method is called the first time the graph is plotted and each
        time the time scale is changed.
        """
        if self.meteo_on is False:
            return

        # --------------------------------------------------- SUBSAMPLE DATA --

        # For performance purposes, only the data that fit within the limits
        # of the x axis limits are plotted.

        istart = np.where(self.bTIME > self.TIMEmin)[0]
        if len(istart) == 0:
            istart = 0
        else:
            istart = istart[0]
            if istart > 0:
                istart += -1

        iend = np.where(self.bTIME < self.TIMEmax)[0]
        if len(iend) == 0:
            iend = 0
        else:
            iend = iend[-1]
            if iend < len(self.bTIME):
                iend += 1

        time = self.bTIME[istart:iend]
        Tmax = self.bTMAX[istart:iend]
        Ptot = self.bPTOT[istart:iend]
        Rain = self.bRAIN[istart:iend]

        # ------------------------------------------------------ PLOT PRECIP --

        TIME2X = np.zeros(len(time) * 4)
        Ptot2X = np.zeros(len(time) * 4)
        Rain2X = np.zeros(len(time) * 4)

        n = self.bwidth / 2.
        f = 0.85  # Space between individual bar.

        TIME2X[0::4] = time - n * f
        TIME2X[1::4] = time - n * f
        TIME2X[2::4] = time + n * f
        TIME2X[3::4] = time + n * f

        Ptot2X[0::4] = 0
        Ptot2X[1::4] = Ptot
        Ptot2X[2::4] = Ptot
        Ptot2X[3::4] = 0

        Rain2X[0::4] = 0
        Rain2X[1::4] = Rain
        Rain2X[2::4] = Rain
        Rain2X[3::4] = 0

        self.PTOT_bar.remove()
        self.RAIN_bar.remove()

        self.PTOT_bar = self.ax3.fill_between(TIME2X, 0., Ptot2X,
                                              color=self.colorsDB.rgb['Snow'],
                                              linewidth=0.0)

        self.RAIN_bar = self.ax3.fill_between(TIME2X, 0., Rain2X,
                                              color=self.colorsDB.rgb['Rain'],
                                              linewidth=0.0)

        self.baseline.set_data([self.TIMEmin, self.TIMEmax], [0, 0])

        # ---------------------------------------------------- PLOT AIR TEMP --

        TIME2X = np.zeros(len(time)*2)
        Tmax2X = np.zeros(len(time)*2)

        n = self.bwidth / 2.
        TIME2X[0:2*len(time)-1:2] = time - n
        TIME2X[1:2*len(time):2] = time + n
        Tmax2X[0:2*len(time)-1:2] = Tmax
        Tmax2X[1:2*len(time):2] = Tmax

        self.l1_ax4.remove()
        self.l1_ax4 = self.ax4.fill_between(TIME2X, 0., Tmax2X,
                                            color=self.colorsDB.rgb['Tair'],
                                            edgecolor='None')

        self.l2_ax4.set_xdata(TIME2X)
        self.l2_ax4.set_ydata(Tmax2X)

        self.update_precip_scale()

    def set_time_scale(self):
        """Setup the time scale of the x-axis."""
        if self.datemode.lower() == 'year':
            year = xldate_as_tuple(self.TIMEmin, 0)[0]
            self.TIMEmin = xldate_from_date_tuple((year, 1, 1), 0)

            last_month = xldate_as_tuple(self.TIMEmax, 0)[1] == 1
            last_day = xldate_as_tuple(self.TIMEmax, 0)[2] == 1

            if last_month and last_day:
                pass
            else:
                year = xldate_as_tuple(self.TIMEmax, 0)[0] + 1
                self.TIMEmax = xldate_from_date_tuple((year, 1, 1), 0)

        self.setup_xticklabels()
        self.ax1.axis([self.TIMEmin, self.TIMEmax, 0, self.NZGrid])

    def setup_xticklabels(self):
        """
        Setup the xtick labels.

        Note that labels are placed manually because this is around 25% faster
        than using the minor ticks.
        """
        xticks_info = self.make_xticks_info()
        self.ax1.set_xticks(xticks_info[0])
        self.ax1.set_xticks(xticks_info[3], minor=True)

        for i in range(len(self.xlabels)):
            self.xlabels[i].remove()

        padding = ScaledTranslation(0, -6/72, self.dpi_scale_trans)

        self.xlabels = []
        for i in range(len(xticks_info[1])):
            new_label = self.ax1.text(
                xticks_info[1][i], 0, xticks_info[2][i], rotation=45,
                va='top', ha='right', fontsize=10,
                transform=self.ax1.transData + padding)
            self.xlabels.append(new_label)

    def draw_figure_title(self):
        """Draw the title of the figure."""
        labelDB = LabelDatabase(self.language)
        if self.isGraphTitle:
            # Set the text and position of the title.
            if self.meteo_on:
                offset = ScaledTranslation(0, 7/72, self.dpi_scale_trans)
                self.text1.set_text(
                    labelDB.station_meteo % (self.name_meteo, self.dist))
                self.text1.set_transform(self.ax0.transAxes + offset)

            dy = 30 if self.meteo_on else 7
            offset = ScaledTranslation(0, dy/72, self.dpi_scale_trans)
            self.figTitle.set_text(labelDB.title % self.wldset['Well'])
            self.figTitle.set_transform(self.ax0.transAxes + offset)

        # Set whether the title is visible or not.
        self.text1.set_visible(self.meteo_on and self.isGraphTitle)
        self.figTitle.set_visible(self.isGraphTitle)

    def setup_waterlvl_scale(self):
        """Update the y scale of the water levels."""
        NZGrid = self.NZGrid if self.meteo_on else self.NZGrid - 2

        self.axLow.set_yticks(np.arange(1, self.NZGrid))
        self.axLow.axis(ymin=0, ymax=NZGrid)
        self.axLow.yaxis.set_ticklabels([])

        if self.WLdatum == 1:   # masl
            WLmin = self.WLmin
            WLscale = self.WLscale
            WLmax = WLmin + (NZGrid * WLscale)

            if self.meteo_on:
                self.ax2.set_yticks(np.arange(WLmin, WLmax - 1.9*WLscale,
                                              WLscale))
            else:
                self.ax2.set_yticks(np.arange(WLmin, WLmax + 0.1*WLscale,
                                              WLscale))

            self.ax2.axis(ymin=WLmin, ymax=WLmax)

        else:  # mbgs: Y axis is inverted
            WLmax = self.WLmin
            WLscale = self.WLscale
            WLmin = WLmax - (NZGrid * WLscale)

            if self.meteo_on:
                self.ax2.set_yticks(np.arange(WLmax, WLmin + 1.9*WLscale,
                                              -WLscale))
            else:
                self.ax2.set_yticks(np.arange(WLmax, WLmin - 0.1*WLscale,
                                              -WLscale))

            self.ax2.axis(ymin=WLmin, ymax=WLmax)
            self.ax2.invert_yaxis()

    def update_precip_scale(self):
        """Update the scale of the axe where precipitation are plotter."""
        if self.meteo_on is False:
            return

        ymax = self.NZGrid * self.RAINscale
        try:
            p = self.PTOT_bar.get_paths()[0]
            v = p.vertices
            y = v[:, 1]

            yticksmax = 0
            while True:
                if yticksmax > max(y):
                    break
                yticksmax += self.RAINscale
            yticksmax = min(ymax, yticksmax) + self.RAINscale/2
        except Exception:
            yticksmax = 3.9 * self.RAINscale

        self.ax3.axis(ymin=0, ymax=ymax)
        self.ax3.set_yticks(np.arange(0, yticksmax, self.RAINscale))
        self.ax3.invert_yaxis()

    def set_gridLines(self):
        """Setup the grid lines."""

        # 0 -> None, 1 -> "-" 2 -> ":"
        grid_color = [0.35, 0.35, 0.35]
        if self.gridLines == 0:
            for ax in self.axes:
                ax._gridOn = False
        elif self.gridLines == 1:
            self.ax4.grid(axis='y', color=grid_color, linestyle='-',
                          linewidth=0.25, which='minor')
            self.axLow.grid(axis='y', color=grid_color, linestyle='-',
                            linewidth=0.25)
            self.ax1.grid(axis='x', color=grid_color, linestyle='-',
                          linewidth=0.25)
        else:
            self.ax4.grid(
                axis='y', color=grid_color, linewidth=0.5, dashes=[1, 5],
                dash_capstyle='butt', which='minor')
            self.axLow.grid(
                axis='y', color=grid_color, linewidth=0.5, dashes=[1, 5],
                dash_capstyle='butt')
            self.ax1.grid(
                axis='x', color=grid_color, linewidth=0.5, dashes=[1, 5],
                dash_capstyle='butt')

    def make_xticks_info(self):

        # The strategy here is to:
        # 1. render some random text ;
        # 2. get the height of its bounding box ;
        # 3. get the horizontal translation of the top-right corner after a
        #    rotation of the bbox of 45 degrees ;
        # 4. sclale the length calculated in step 3 to the height to width
        #    ratio of the axe ;
        # 5. convert the lenght calculated in axes coord. to the data coord.
        #    system ;
        # 6. remove the random text from the figure.

        # Random text bbox height :

        dummytxt = self.ax1.text(0.5, 0.5, 'some_dummy_text', fontsize=10,
                                 ha='right', va='top',
                                 transform=self.ax1.transAxes)

        renderer = self.canvas.get_renderer()

        bbox = dummytxt.get_window_extent(renderer)
        bbox = bbox.transformed(self.ax1.transAxes.inverted())

        # Horiz. trans. of bbox top-right corner :

        dx = bbox.height * np.sin(np.radians(45))

        # Scale dx to axe dimension.
        bbox = self.ax1.get_window_extent(renderer)  # in pixels
        bbox = bbox.transformed(self.dpi_scale_trans.inverted())  # in inches

        sdx = dx * bbox.height / bbox.width
        sdx *= (self.TIMEmax - self.TIMEmin + 1)

        dummytxt.remove()

        # Transform to data coord :

        month_names = LabelDatabase(self.language).month_names

        xticks_labels_offset = sdx

        xticks_labels = []
        xticks_position = []
        xticks_labels_position = []
        xticks_minor_position = []

        i = 0
        next_xtick_pos = self.TIMEmin
        while True:
            datetuple = xldate_as_tuple(next_xtick_pos, 0)
            year = datetuple[0]
            month = datetuple[1]
            month_range = monthrange(year, month)[1]

            xticks_minor_position.append(next_xtick_pos)
            if i % self.date_labels_pattern == 0:
                xticks_position.append(next_xtick_pos)
                xticks_labels_position.append(
                    next_xtick_pos + xticks_labels_offset)
                if self.datemode.lower() == 'month':
                    xticks_labels.append("{} '{}".format(
                        month_names[month - 1], str(year)[-2:]))
                elif self.datemode.lower() == 'year':
                    xticks_labels.append("%d" % year)

            if self.datemode.lower() == 'month':
                next_xtick_pos = next_xtick_pos + month_range
            elif self.datemode.lower() == 'year':
                next_xtick_pos = xldate_from_date_tuple((year + 1, 1, 1), 0)

            if next_xtick_pos > self.TIMEmax:
                break
            i += 1

        return (xticks_position, xticks_labels_position, xticks_labels,
                xticks_minor_position)


def filt_data(time, waterlvl, N):
    """
    Resamples the water level measurements on a daily basis and run a
    moving average window of N days on the resampled data.
    """
    # Resample the data on a daily basis.
    days = np.arange(np.floor(time[0]), np.floor(time[-1])+1)
    index_nonan = np.where(~np.isnan(waterlvl))[0]
    waterlvl = np.interp(days, time[index_nonan], waterlvl[index_nonan])

    # Compute a centered moving average window on the daily resampled data.
    # Based on the codes provided by StackOverflow user Alleo.
    # https://stackoverflow.com/a/27681394/4481445
    N = int(N)
    cumsum = np.cumsum(np.insert(waterlvl, 0, 0))
    wlf = (cumsum[N:] - cumsum[:-N])/float(N)
    tf = days[N//2:-N//2+1]

    return tf, wlf


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    from gwhat.widgets.mplfigureviewer import ImageViewer
    from gwhat.meteo.weather_reader import WXDataFrame
    from gwhat.projet.reader_projet import ProjetReader

    app = QApplication(sys.argv)

    # ---- Load the data
    path_projet = "C:\\Users\\User\\gwhat\\Projects\\Example\\Example.gwt"
    projet = ProjetReader(path_projet)

    wldset = projet.get_wldset('3040002_15min')
    wxdset = projet.get_wxdset('Marieville')

    # ---- Setup the hydrograph

    hydrograph = Hydrograph()
    hydrograph.set_wldset(wldset)
    hydrograph.set_wxdset(wxdset)
    hydrograph.language = 'english'

    hydrograph.fwidth = 11.  # Width of the figure in inches
    hydrograph.fheight = 8.5

    hydrograph.WLdatum = 0  # 0 -> mbgs ; 1 -> masl
    hydrograph.trend_line = False
    hydrograph.gridLines = 2  # Gridlines Style
    hydrograph.isGraphTitle = 1  # 1 -> title ; 0 -> no title
    hydrograph.isLegend = 1

    hydrograph.meteo_on = True  # True or False
    hydrograph.datemode = 'year'  # 'month' or 'year'
    hydrograph.date_labels_pattern = 1
    hydrograph.bwidth_indx = 2  # Meteo Bin Width
    # 0: daily | 1: weekly | 2: monthly | 3: yearly
    hydrograph.RAINscale = 100

    hydrograph.best_fit_time(wldset.xldates)
    hydrograph.best_fit_waterlvl()
    hydrograph.generate_hydrograph()

    # ---- Show figure on-screen
    imgview = ImageViewer()
    imgview.sfmax = 10
    imgview.load_mpl_figure(hydrograph)
    imgview.show()

    projet.close()
    sys.exit(app.exec_())
