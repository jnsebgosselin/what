# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import os

# ---- Third party imports
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QStyle, QApplication, QToolButton
import qtawesome as qta

# ---- Local imports
from gwhat import __rootdir__

DIRNAME = os.path.join(__rootdir__, 'ressources', 'icons_png')
GWHAT_ICONS = {
    'master': 'WHAT',
    'expand_range_vert': 'expand_range_vert',
    'calc_brf': 'start',
    'setup': 'page_setup',
    'openFolder': 'folder',
    'clear': 'clear-search',
    'importFile': 'open_project',
    'download': 'download',
    'tridown': 'triangle_down',
    'triright': 'triangle_right',
    'go_previous': 'go-previous',
    'go_next': 'go-next',
    'go_last': 'go-last',
    'go_first': 'go-first',
    'go_up': 'go-up',
    'play': 'start',
    'forward': 'start_all',
    'refresh': 'refresh',
    'stop': 'process-stop',
    'settings': 'settings',
    'staList': 'note',
    'add2list': 'add2list',
    'todate': 'calendar_todate',
    'fromdate': 'calendar_fromdate',
    'select_range': 'select_range',
    'toggleMode': 'toggleMode2',
    'undo': 'undo',
    'clear_search': 'clear-search',
    'mrc_calc': 'MRCalc',
    'edit': 'edit',
    'add_point': 'add_point',
    'erase': 'erase',
    'erase2': 'erase2',
    'showDataDots': 'show_datadots',
    'stratigraphy': 'stratigraphy',
    'recharge': 'recharge',
    'page_setup': 'page_setup',
    'fit_y': 'fit_y',
    'fit_x': 'fit_x',
    'save_graph_config': 'save_config',
    'load_graph_config': 'load_config',
    'closest_meteo': 'closest_meteo',
    'draw_hydrograph': 'stock_image',
    'meteo': 'meteo',
    'work': 'work',
    'color_picker': 'color_picker',
    'merge_data': 'merge_data',
    'fill_data': 'fill_data',
    'fill_all_data': 'fill_all_data',
    'showGrid': 'grid',
    'export_data': 'export-data',
    'show_glue_wl': 'show_glue_wl',
    'show_meteo': 'show_meteo',
    'manual_measures': 'manual_measures',
    'rect_select': 'rect_select',
    'rect_select_clear': 'rect_select_clear'
    }

COLOR = '#4d4d4d'
GREEN = '#00aa00'
RED = '#aa0000'

FA_ICONS = {
    'calendar': [
        ('mdi.calendar-question',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'clear_changes': [
        ('mdi.close-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    'close_all': [
        ('fa.close', 'fa.close', 'fa.close'),
        {'options': [{'scale_factor': 0.6,
                      'offset': (0.3, -0.3),
                      'color': COLOR},
                     {'scale_factor': 0.6,
                      'offset': (-0.3, -0.3),
                      'color': COLOR},
                     {'scale_factor': 0.6,
                      'offset': (0.3, 0.3),
                      'color': COLOR}]}],
    'content_duplicate': [
        ('mdi.content-duplicate',),
        {'color': COLOR, 'scale_factor': 1.2}],
    'commit_changes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'copy_clipboard': [
        ('mdi.content-copy',),
        {'color': COLOR, 'scale_factor': 1.2}],
    'delete_data': [
        ('mdi.delete-forever',),
        {'color': COLOR, 'scale_factor': 1.4}],
    'erase_data': [
        ('mdi.eraser',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'expand_all': [
        ('mdi.arrow-expand-all',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'folder_open': [
        ('mdi.folder-open',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'home': [
        ('mdi.home',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'info': [
        ('mdi.information-outline',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'language': [
        ('mdi.web',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'link': [
        ('mdi.link',),
        {'color': COLOR, 'scale_factor': 1, 'rotated': 90}],
    'link_off': [
        ('mdi.link-off',),
        {'color': COLOR, 'scale_factor': 1, 'rotated': 90}],
    'models_dist': [
        ('mdi.chart-bell-curve',),
        {'color': COLOR, 'scale_factor': 1.2}],
    'pan': [
        ('mdi.pan',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'play_start': [
        ('mdi.play',),
        {'color': GREEN, 'scale_factor': 1.5}],
    'report_bug': [
        ('mdi.bug',),
        {'color': COLOR, 'scale_factor': 1.4}],
    'save': [
        ('fa.save',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'search': [
        ('fa5s.search',),
        {'color': COLOR, 'scale_factor': 1.0}],
    'undo_changes': [
        ('mdi.undo-variant',),
        {'color': COLOR, 'scale_factor': 1.3}],
    'zoom_in': [
        ('mdi.plus-circle-outline',),
        {'color': COLOR, 'scale_factor': 1.2}],
    'zoom_out': [
        ('mdi.minus-circle-outline',),
        {'color': COLOR, 'scale_factor': 1.2}],
    'zoom_to_rect': [
        ('mdi.selection-search',),
        {'color': COLOR, 'scale_factor': 1.2}],
    }

ICON_SIZES = {'large': (32, 32),
              'normal': (24, 24),
              'small': (20, 20)}


def get_icon(name):
    """Return a QIcon from a specified icon name."""
    if name in FA_ICONS:
        args, kwargs = FA_ICONS[name]
        return qta.icon(*args, **kwargs)
    elif name in GWHAT_ICONS:
        return QIcon(os.path.join(DIRNAME, GWHAT_ICONS[name]))
    else:
        return QIcon()


def get_iconsize(size):
    return QSize(*ICON_SIZES[size])


def get_standard_icon(constant):
    """
    Return a QIcon of a standard pixmap.

    See the link below for a list of valid constants:
    https://srinikom.github.io/pyside-docs/PySide/QtGui/QStyle.html
    """
    constant = getattr(QStyle, constant)
    style = QApplication.instance().style()
    return style.standardIcon(constant)


def get_standard_iconsize(constant):
    """
    Return the standard size of various component of the gui.

    https://srinikom.github.io/pyside-docs/PySide/QtGui/QStyle
    """
    style = QApplication.instance().style()
    if constant == 'messagebox':
        return style.pixelMetric(QStyle.PM_MessageBoxIconSize)
    elif constant == 'small':
        return style.pixelMetric(QStyle.PM_SmallIconSize)


class QToolButtonBase(QToolButton):
    """A basic tool button."""

    def __init__(self, icon, *args, **kargs):
        super(QToolButtonBase, self).__init__(*args, **kargs)
        icon = get_icon(icon) if isinstance(icon, str) else icon
        self.setIcon(icon)
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.NoFocus)

    def setToolTip(self, ttip):
        """
        Qt method override to ensure tooltips are enclosed in <p></p> so
        that they wraps correctly.
        """
        ttip = ttip if ttip.startswith('<p>') else '<p>' + ttip
        ttip = ttip if ttip.endswith('</p>') else ttip + '</p>'
        super().setToolTip(ttip)


class QToolButtonNormal(QToolButtonBase):
    def __init__(self, Qicon, *args, **kargs):
        super(QToolButtonNormal, self).__init__(Qicon, *args, **kargs)
        self.setIconSize(get_iconsize('normal'))


class QToolButtonSmall(QToolButtonBase):
    def __init__(self, Qicon, *args, **kargs):
        super(QToolButtonSmall, self).__init__(Qicon, *args, **kargs)
        self.setIconSize(get_iconsize('small'))


class QToolButtonVRectSmall(QToolButtonBase):
    def __init__(self, Qicon, *args, **kargs):
        super(QToolButtonVRectSmall, self).__init__(Qicon, *args, **kargs)
        self.setIconSize(QSize(8, 20))


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout

    app = QApplication(sys.argv)

    window = QWidget()
    layout = QGridLayout(window)
    layout.addWidget(QToolButtonNormal(get_icon('download')), 0, 0)
    layout.addWidget(QToolButtonNormal(get_icon('close_all')), 0, 1)
    window.show()

    sys.exit(app.exec_())
