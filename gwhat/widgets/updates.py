# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.
#
# Copyright (c) 2017 Spyder Project Contributors
# https://github.com/spyder-ide/spyder
#
# Some parts of this file is a derivative work of the Spyder project.
# Licensed under the terms of the MIT License.
# https://github.com/spyder-ide/spyder/master/spyder/workers/updates.py
# https://github.com/spyder-ide/spyder/blob/master/spyder/utils/programs.py
#
# Copyright (C) 2013 The IPython Development Team
# https://github.com/ipython/ipython
#
# See gwhat/__init__.py for more details.
# -----------------------------------------------------------------------------

# ---- Standard imports
import re
from distutils.version import LooseVersion


# ---- Third party imports
from PyQt5.QtCore import QObject, Qt, QThread
from PyQt5.QtCore import pyqtSlot as QSlot
from PyQt5.QtCore import pyqtSignal as QSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QMessageBox
import requests

# ---- Local imports
from gwhat import __version__, __releases_url__, __releases_api__, __namever__
from gwhat.utils import icons


class ManagerUpdates(QMessageBox):
    """
    Self contained manager that checks if updates are available on GitHub
    and displays the ressults in a message box.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('GWHAT updates')
        self.setWindowIcon(icons.get_icon('master'))
        self.setMinimumSize(800, 700)
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setStandardButtons(QMessageBox.Ok)
        self.setDefaultButton(QMessageBox.Ok)

        self.thread_updates = QThread()
        self.worker_updates = WorkerUpdates()
        self.worker_updates.moveToThread(self.thread_updates)
        self.thread_updates.started.connect(self.worker_updates.start)
        self.worker_updates.sig_ready.connect(self._receive_updates_check)

    def start_updates_check(self):
        """Check if updates are available."""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.thread_updates.start()

    @QSlot()
    def _receive_updates_check(self):
        self.thread_updates.quit()
        latest_release = self.worker_updates.latest_release
        if self.worker_updates.error is not None:
            icn = QMessageBox.Warning
            msg = self.worker_updates.error
        else:
            icn = QMessageBox.Information
            if self.worker_updates.update_available:
                url_i = ("https://gwhat.readthedocs.io/en/latest/"
                         "getting_started.html")
                msg = ("<b>GWHAT %s is available!</b><br><br>"
                       "This new version can be downloaded from our "
                       "<a href=\"%s\">Releases</a> page.<br><br>"
                       "Instructions to update GWHAT are provided on our "
                       "<a href=\"%s\">Installation</a> instructions."
                       ) % (latest_release, __releases_url__, url_i)
            else:
                url_m = "https://github.com/jnsebgosselin/gwhat/milestones"
                url_t = "https://github.com/jnsebgosselin/gwhat/issues"
                msg = ("<b>%s is up to date.</b><br><br>"
                       "Further information about GWHAT releases are available"
                       " on our <a href=\"%s\">Releases</a> page.<br><br>"
                       "The roadmap of the GWHAT project can be consulted"
                       " on our <a href=\"%s\">Milestones</a> page.<br><br>"
                       "Please help GWHAT by reporting bugs or proposing new"
                       " features on our"
                       " <a href=\"%s\">Issues Tracker</a>."
                       ) % (__namever__, __releases_url__, url_m, url_t)
        self.setText(msg)
        self.setIcon(icn)
        QApplication.restoreOverrideCursor()
        self.exec_()


class WorkerUpdates(QObject):
    """
    Worker that checks for releases using the Github API.
    """
    sig_ready = QSignal()

    def __init__(self):
        super(WorkerUpdates, self).__init__()
        self.error = None
        self.latest_release = None
        self.update_available = False

    def start(self):
        """Main method of the WorkerUpdates worker."""
        self.update_available = False
        self.latest_release = __version__
        self.error = None
        try:
            page = requests.get(__releases_api__)
            data = page.json()
            releases = [item['tag_name'].replace('gwhat-', '')
                        for item in data
                        if item['tag_name'].startswith("gwhat")]
            result = check_update_available(__version__, releases)
            self.update_available, self.latest_release = result
        except requests.exceptions.HTTPError:
            self.error = ('Unable to retrieve information because of.'
                          ' an http error.')
        except requests.exceptions.ConnectionError:
            self.error = ('Unable to connect to the internet.<br><br>Make '
                          'sure the connection is working properly.')
        except requests.exceptions.Timeout:
            self.error = ('Unable to retrieve information because the'
                          ' connection timed out.')
        except Exception:
            self.error = ('Unable to check for updates because of'
                          ' an unexpected error.')
        self.sig_ready.emit()


def check_update_available(version, releases):
    """
    Checks if there is an update available.

    It takes as parameters the current version of GWHAT and a list of
    valid cleaned releases in chronological order (what github api returns
    by default). Example: ['2.3.4', '2.3.3' ...]

    Copyright (c) Spyder Project Contributors
    Licensed under the terms of the MIT License
    """
    if is_stable_version(version):
        # Remove non stable versions from the list
        releases = [r for r in releases if is_stable_version(r)]

    latest_release = releases[0]
    if version.endswith('dev'):
        return (False, latest_release)
    else:
        return (check_version(version, latest_release, '<'),
                latest_release)


def check_version(actver, version, cmp_op):
    """
    Check version string of an active module against a required version.

    If dev/prerelease tags result in TypeError for string-number comparison,
    it is assumed that the dependency is satisfied. Users on dev branches are
    responsible for keeping their own packages up to date.

    Copyright (C) 2013 The IPython Development Team
    Licensed under the terms of the BSD License
    """
    if isinstance(version, tuple):
        version = '.'.join([str(i) for i in version])

    # Hacks needed so that LooseVersion understands that (for example)
    # version = '3.0.0' is in fact bigger than actver = '3.0.0rc1'
    if (is_stable_version(version) and not is_stable_version(actver) and
            actver.startswith(version) and version != actver):
        version = version + 'zz'
    elif (is_stable_version(actver) and not is_stable_version(version) and
            version.startswith(actver) and version != actver):
        actver = actver + 'zz'

    try:
        if cmp_op == '>':
            return LooseVersion(actver) > LooseVersion(version)
        elif cmp_op == '>=':
            return LooseVersion(actver) >= LooseVersion(version)
        elif cmp_op == '=':
            return LooseVersion(actver) == LooseVersion(version)
        elif cmp_op == '<':
            return LooseVersion(actver) < LooseVersion(version)
        elif cmp_op == '<=':
            return LooseVersion(actver) <= LooseVersion(version)
        else:
            return False
    except TypeError:
        return True


def is_stable_version(version):
    """
    Returns wheter this is a stable version or not. A stable version has no
    letters in the final component, but only numbers.

    Stable version example: 1.2, 1.3.4, 1.0.5
    Not stable version: 1.2alpha, 1.3.4beta, 0.1.0rc1, 3.0.0dev

    Copyright (c) 2017 Spyder Project Contributors
    Licensed under the terms of the MIT License
    """
    if not isinstance(version, tuple):
        version = version.split('.')
    last_part = version[-1]

    if not re.search('[a-zA-Z]', last_part):
        return True
    else:
        return False


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    updates_worker = ManagerUpdates()
    updates_worker.show()
    sys.exit(app.exec_())
