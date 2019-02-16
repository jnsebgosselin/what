# -*- coding: utf-8 -*-

# Copyright © 2014-2018 GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.

from __future__ import division, unicode_literals

# ---- Standard library imports
import os
import csv
import os.path as osp
from shutil import copyfile
import subprocess

# ---- Third party imports
import h5py
import numpy as np

# ---- Local library imports
from gwhat.meteo.weather_reader import WXDataFrameBase
from gwhat.projet.reader_waterlvl import WLDataFrameBase
from gwhat.gwrecharge.glue import GLUEDataFrameBase
from gwhat.common.utils import save_content_to_file
from gwhat.utils.math import nan_as_text_tolist, calcul_rmse

INVALID_CHARS = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']


class ProjetReader(object):
    def __init__(self, filename):
        self.__db = None
        self.load_projet(filename)

    def __del__(self):
        self.close()

    @property
    def db(self):  # project data base
        return self.__db

    @property
    def filename(self):
        return self.db.filename

    @property
    def dirname(self):
        return os.path.dirname(self.filename)

    def load_projet(self, filename):
        """Open the hdf5 project file."""
        self.close()
        print("Loading project from '{}'... ".format(osp.basename(filename)),
              end='')
        try:
            if not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))
            self.__db = h5py.File(filename, mode='a')
            print('done')
        except Exception:
            self.__db = None
            print('failed')
            raise ValueError('Project file is not valid!')

        # For newly created project and backward compatibility.
        for key in ['name', 'author', 'created', 'modified', 'version']:
            if key not in list(self.db.attrs.keys()):
                self.db.attrs[key] = 'None'

        for key in ['latitude', 'longitude']:
            if key not in list(self.db.attrs.keys()):
                self.db.attrs[key] = 0

        for key in ['wldsets', 'wxdsets']:
            if key not in list(self.db.keys()):
                self.db.create_group(key)
            if 'last_opened' not in list(self.db[key].attrs.keys()):
                # Added in version 0.4.0 (see PR #267)
                self.db[key].attrs['last_opened'] = 'None'

    def close(self):
        """Close the project hdf5 file."""
        try:
            self.db.close()
            self.__db = None
        except AttributeError:
            # projet is None or already closed.
            pass

    def check_project_file(self):
        """Check to ensure that the project hdf5 file is not corrupt."""
        item_names = []
        try:
            self.__db.visit(item_names.append)
        except RuntimeError:
            return False
        else:
            return True

    def get_project_items(self):
        """
        Return a list of addresses for all the items contained in the
        project hdf5 file.
        """
        item_names = []
        try:
            self.__db.visit(item_names.append)
        except RuntimeError:
            return []
        else:
            return item_names

    def backup_project_file(self):
        """Copy the project hdf5 file in a file with a .bak extension."""
        if self.db is not None:
            filename = self.filename
            self.db.close()
            print("Creating a backup of the project hdf5 file... ", end='')
            try:
                copyfile(filename, filename + '.bak')
            except (OSError, PermissionError):
                print('failed')
                return False
            else:
                print('done')
                return True
            finally:
                self.load_projet(filename)

    def repack_project_file(self, reload=True):
        """
        Repack the project hdf5 file to reclaim free space from deleted data.
        The repacked file is saved with a .repack file extension.
        """
        print("Repacking project hdf5 file... ")
        self.db.flush()
        filename = self.filename
        proj_items = self.get_project_items()
        self.close()

        # Try to delete the .repack file from the disk first.
        if osp.exists(filename + '.repack'):
            try:
                os.remove(filename + '.repack')
            except (OSError, PermissionError):
                print('Project repacking failed.')
                print("Reason: failed to delete the old .repack file.")
                if reload is True:
                    self.load_projet(filename)
                return False

        # Repack the project hdf5 file.
        cmd = ['h5repack', '-i', filename, '-o', filename + '.repack']
        sp = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        sp.wait()
        if not osp.exists(filename + '.repack'):
            print('Project repacking failed.')
            print("Reason: failed to repack the project file.")
            if reload is True:
                self.load_projet(filename)
            return False

        # Check that the structure of the repacked project file was
        # preserved.
        repack_proj = ProjetReader(filename + '.repack')
        repack_proj_items = repack_proj.get_project_items()
        repack_proj.close()

        if proj_items == repack_proj_items:
            # Replace the old project with the repacked one.
            try:
                copyfile(filename + '.repack', filename)
            except (OSError, PermissionError, IOError):
                print('Project repacking failed.')
                print("Reason: failed to replace the project file with the "
                      "repacked one.")
                if reload is True:
                    self.load_projet(filename)
                return False
            else:
                print('done')
                if reload is True:
                    self.load_projet(filename)
                return True
        else:
            print('Project repacking failed.')
            print("Reason: the project structure was not preserved "
                  "during repacking.")
            if reload is True:
                self.load_projet(filename)
            return False

    # ---- Project Properties
    @property
    def name(self):
        return self.db.attrs['name']

    @name.setter
    def name(self, x):
        self.db.attrs['name'] = x

    @property
    def author(self):
        return self.db.attrs['author']

    @author.setter
    def author(self, x):
        self.db.attrs['author'] = x

    @property
    def created(self):
        return self.db.attrs['created']

    @created.setter
    def created(self, x):
        self.db.attrs['created'] = x

    @property
    def modified(self):
        return self.db.attrs['modified']

    @modified.setter
    def modified(self, x):
        self.db.attrs['modified'] = x

    @property
    def version(self):
        return self.db.attrs['version']

    @version.setter
    def version(self, x):
        self.db.attrs['version'] = x

    @property
    def lat(self):
        return self.db.attrs['latitude']

    @lat.setter
    def lat(self, x):
        self.db.attrs['latitude'] = x

    @property
    def lon(self):
        return self.db.attrs['longitude']

    @lon.setter
    def lon(self, x):
        self.db.attrs['longitude'] = x

    # ---- Water Levels Dataset Handlers

    @property
    def wldsets(self):
        """
        Return a list of the names of all the water level datasets stored in
        the project hdf5 file.
        """
        return list(self.db['wldsets'].keys())

    def get_last_opened_wldset(self):
        """
        Return the name of the last opened water level dataset in the project
        if any.
        """
        name = self.db['wldsets'].attrs['last_opened']
        return None if name == 'None' else name

    def get_wldset(self, name):
        """
        Return the water level dataset corresponding to the provided name.
        """
        if name in self.wldsets:
            self.db['wldsets'].attrs['last_opened'] = name
            return WLDataFrameHDF5(self.db['wldsets/%s' % name])
        else:
            return None

    def add_wldset(self, name, df):
        """
        Add the water level dataset to the project hdf5 file.

        A dataset name must be at least one charater long and can't contain
        any of the following special characters: \\ / : * ? " < > |
        """
        if not is_dsetname_valid(name):
            raise ValueError("The name of the dataset is not valid.")

        try:
            grp = self.db['wldsets'].create_group(name)

            # Water level data
            grp.create_dataset('Time', data=df['Time'])
            grp.create_dataset('WL', data=df['WL'])
            grp.create_dataset('BP', data=df['BP'])
            grp.create_dataset('ET', data=df['ET'])

            # Piezometric well info
            grp.attrs['filename'] = df['filename']
            grp.attrs['Well'] = df['Well']
            grp.attrs['Well ID'] = df['Well ID']
            grp.attrs['Latitude'] = df['Latitude']
            grp.attrs['Longitude'] = df['Longitude']
            grp.attrs['Elevation'] = df['Elevation']
            grp.attrs['Municipality'] = df['Municipality']
            grp.attrs['Province'] = df['Province']

            # Master Recession Curve
            mrc = grp.create_group('mrc')
            mrc.attrs['exists'] = 0
            mrc.create_dataset('params', data=(0, 0), dtype='float64')
            mrc.create_dataset('peak_indx', data=np.array([]),
                               dtype='int16', maxshape=(None,))
            mrc.create_dataset('recess', data=np.array([]),
                               dtype='float64', maxshape=(None,))
            mrc.create_dataset('time', data=np.array([]),
                               dtype='float64', maxshape=(None,))

            # Barometric Response Function
            grp.create_group('brf')

            # GLUE (recharge, evapotranspiration, runoff, water levels)
            # Added in version 0.3.1 (see PR #184)
            grp.create_group('glue')

            # Hydrograph layout
            grp.create_group('layout')

            # Manual water level measurements
            mmeas = grp.create_group('manual')
            mmeas.create_dataset('Time', data=np.array([]), maxshape=(None,))
            mmeas.create_dataset('WL', data=np.array([]), maxshape=(None,))

            self.db.flush()

            print('New dataset created sucessfully')
        except Exception:
            print('Unable to save dataset to project db')
            del self.db['wldsets'][name]

        return WLDataFrameHDF5(grp)

    def del_wldset(self, name):
        """Delete the specified water level dataset."""
        del self.db['wldsets/%s' % name]
        self.db.flush()

    # ---- Weather Dataset Handlers

    @property
    def wxdsets(self):
        """
        Return a list of the names of all the weather datasets stored in
        the project hdf5 file.
        """
        return list(self.db['wxdsets'].keys())

    def get_last_opened_wxdset(self):
        """
        Return the name of the last opened weather dataset in the project
        if any.
        """
        name = self.db['wxdsets'].attrs['last_opened']
        return None if name == 'None' else name

    def get_wxdset(self, name):
        """
        Return the weather dataset corresponding to the provided name.
        """
        if name in self.wxdsets:
            self.db['wxdsets'].attrs['last_opened'] = name
            return WXDataFrameHDF5(self.db['wxdsets/%s' % name])
        else:
            return None

    def add_wxdset(self, name, df):
        """
        Add the weather dataset to the project hdf5 file.

        A dataset name must be at least one charater long and can't contain
        any of the following special characters: \\ / : * ? " < > |
        """
        if not is_dsetname_valid(name):
            raise ValueError("The name of the dataset is not valid.")

        grp = self.db['wxdsets'].create_group(name)

        grp.attrs['filename'] = df['filename']
        grp.attrs['Station Name'] = df['Station Name']
        grp.attrs['Latitude'] = df['Latitude']
        grp.attrs['Longitude'] = df['Longitude']
        grp.attrs['Elevation'] = df['Elevation']
        grp.attrs['Province'] = df['Province']
        grp.attrs['Climate Identifier'] = df['Climate Identifier']

        grp.create_dataset('Time', data=df['Time'])
        grp.create_dataset('Year', data=df['Year'])
        grp.create_dataset('Month', data=df['Month'])
        grp.create_dataset('Day', data=df['Day'])
        grp.create_dataset('Tmax', data=df['Tmax'])
        grp.create_dataset('Tavg', data=df['Tavg'])
        grp.create_dataset('Tmin', data=df['Tmin'])
        grp.create_dataset('Ptot', data=df['Ptot'])
        grp.create_dataset('Rain', data=df['Rain'])
        grp.create_dataset('Snow', data=df['Snow'])
        grp.create_dataset('PET', data=df['PET'])

        grp.create_dataset('Missing Tmax', data=df['Missing Tmax'])
        grp.create_dataset('Missing Tmin', data=df['Missing Tmin'])
        grp.create_dataset('Missing Tavg', data=df['Missing Tavg'])
        grp.create_dataset('Missing Ptot', data=df['Missing Ptot'])

        grp_yrly = grp.create_group('yearly')
        for vbr in df['yearly'].keys():
            grp_yrly.create_dataset(vbr, data=df['yearly'][vbr])

        grp_mtly = grp.create_group('monthly')
        for vbr in df['monthly'].keys():
            grp_mtly.create_dataset(vbr, data=df['monthly'][vbr])

        grp_norm = grp.create_group('normals')
        for vbr in df['normals'].keys():
            grp_norm.create_dataset(vbr, data=df['normals'][vbr])

        print('New dataset created sucessfully')

        self.db.flush()

    def del_wxdset(self, name):
        """Delete the specified weather dataset."""
        del self.db['wxdsets/%s' % name]
        self.db.flush()


class WLDataFrameHDF5(WLDataFrameBase):
    """
    This is a wrapper around the h5py group that is used to store
    water level datasets. It mimick the structure of the DataFrame that
    is returned when loading water level dataset from an Excel file in
    reader_waterlvl module.
    """

    def __init__(self, hdf5group, *args, **kwargs):
        super(WLDataFrameHDF5, self).__init__(*args, **kwargs)
        self.__load_dataset__(hdf5group)

    def __load_dataset__(self, hdf5group):
        self.dset = hdf5group
        self._undo_stack = []
        self._waterlevels = self.dset['WL'][...]
        self._datetimes = self.dset['Time'][...]

        # Make older datasets compatible with newer format.
        if 'Well ID' not in list(self.dset.attrs.keys()):
            # Added in version 0.2.1 (see PR #124).
            self.dset.attrs['Well ID'] = ""
            self.dset.file.flush()
        if 'Province' not in list(self.dset.attrs.keys()):
            # Added in version 0.2.1 (see PR #124).
            self.dset.attrs['Province'] = ""
            self.dset.file.flush()
        if 'glue' not in list(self.dset.keys()):
            # Added in version 0.3.1 (see PR #184)
            self.dset.create_group('glue')
            self.dset.file.flush()

    def __getitem__(self, key):
        if key in list(self.dset.attrs.keys()):
            return self.dset.attrs[key]
        else:
            return self.dset[key][...]

    @property
    def name(self):
        return osp.basename(self.dset.name)

    # ---- Water levels
    def commit(self):
        """Commit the changes made to the water level data to the project."""
        if self.has_uncommited_changes:
            self.dset['WL'][:] = np.copy(self.waterlevels)
            self.dset.file.flush()
            self._undo_stack = []
            print('Changes commited successfully.')

    # ---- Manual measurements
    def set_wlmeas(self, time, wl):
        """Overwrite the water level measurements for this dataset."""
        try:
            self.dset['manual/Time'].resize(np.shape(time))
            self.dset['manual/Time'][:] = time
            self.dset['manual/WL'].resize(np.shape(wl))
            self.dset['manual/WL'][:] = wl
        except TypeError:
            del self.dset['manual']
            mmeas = self.dset.create_group('manual')
            mmeas.create_dataset('Time', data=time, maxshape=(None,))
            mmeas.create_dataset('WL', data=wl, maxshape=(None,))
        self.dset.file.flush()

    def get_wlmeas(self):
        """Get the water level measurements for this dataset."""
        grp = self.dset.require_group('manual')
        return grp['Time'][...], grp['WL'][...]

    # ---- Master recession curve

    def set_mrc(self, A, B, peak_indx, time, recess):
        """Save the mrc results to the hdf5 project file."""
        self.dset['mrc/params'][:] = (A, B)

        self.dset['mrc/peak_indx'].resize(np.shape(peak_indx))
        self.dset['mrc/peak_indx'][:] = np.array(peak_indx)

        self.dset['mrc/time'].resize(np.shape(time))
        self.dset['mrc/time'][:] = time

        self.dset['mrc/recess'].resize(np.shape(recess))
        self.dset['mrc/recess'][:] = recess

        self.dset['mrc'].attrs['exists'] = 1

        self.dset.file.flush()

    def mrc_exists(self):
        """Return whether a mrc results is saved in the hdf5 project file."""
        if 'mrc' not in list(self.dset.keys()):
            mrc = self.dset.create_group('mrc')
            mrc.attrs['exists'] = 0
            mrc.create_dataset('params', data=(0, 0), dtype='float64')
            mrc.create_dataset('peak_indx', data=np.array([]),
                               dtype='int16', maxshape=(None,))
            mrc.create_dataset('recess', data=np.array([]),
                               dtype='float64', maxshape=(None,))
            mrc.create_dataset('time', data=np.array([]),
                               dtype='float64', maxshape=(None,))
        return bool(self.dset['mrc'].attrs['exists'])

    def save_mrc_tofile(self, filename):
        """Save the master recession curve results to a file."""
        fcontent = []

        # Format the file header.
        keys = ['Well', 'Well ID', 'Province', 'Latitude', 'Longitude',
                'Elevation', 'Municipality']
        for key in keys:
            fcontent.append([key, self[key]])

        # Format the mrc results summary.
        A, B = self['mrc/params']
        fcontent.extend([
            [''],
            ['dh/dt(mm/d) = -%f*h(mbgs) + %f' % (A, B)],
            ['A (1/d)', A],
            ['B (m/d)', B],
            ['RMSE (m)', calcul_rmse(self['WL'], self['mrc/recess'])],
            [''],
            ['Observed and Predicted Water Level'],
            ['Time', 'hrecess(mbgs)', 'hobs(mbgs)']
            ])

        # Format the observed and simulated data.
        data = np.vstack([self['Time'], self['WL'], self['mrc/recess']])
        data = nan_as_text_tolist(np.array(data).transpose())
        fcontent.extend(data)

        save_content_to_file(filename, fcontent)

    # ---- GLUE water budget and water level evaluation

    def glue_idnums(self):
        """Return the id numbers of all the previously saved GLUE results"""
        return list(self.dset['glue'].keys())

    def glue_count(self):
        """Return the number of GLUE results saved in this dataset."""
        return len(self.glue_idnums())

    def save_glue(self, gluedf):
        """Save GLUE results in the project hdf file."""
        if list(self.dset['glue'].keys()):
            idnum = np.array(list(self.dset['glue'].keys())).astype(int)
            idnum = np.max(idnum) + 1
        else:
            idnum = 1
        idnum = str(idnum)

        grp = self.dset['glue'].create_group(idnum)
        save_dict_to_h5grp(grp, gluedf)
        self.dset.file.flush()
        print('GLUE results saved successfully')

    def get_glue(self, idnum):
        """Get GLUE results at idnum."""
        if idnum in self.glue_idnums():
            return GLUEDataFrameHDF5(self.dset['glue'][idnum])

    def get_glue_at(self, idx):
        """Return GLUE results stored at the specified index."""
        try:
            idnum = self.glue_idnums()[idx]
        except IndexError:
            return None
        else:
            return self.get_glue(idnum)

    def del_glue(self, idnum):
        """Delete GLUE results at idnum."""
        if idnum in self.glue_idnums():
            del self.dset['glue'][idnum]
            self.dset.file.flush()
            print('GLUE data %s deleted successfully' % idnum)
        else:
            print('GLUE data %s does not exist' % idnum)

    def clear_glue(self):
        """Delete all GLUE results from the dataset."""
        while self.glue_count():
            self.del_glue(self.glue_idnums()[0])

    # ---- Barometric response function

    def saved_brf(self):
        """
        Return the list of ids referencing to the BRF evaluations saved for
        this dataset.
        """
        grp = self.dset.require_group('brf')
        return list(grp.keys())

    def brf_count(self):
        """Return the number of BRF evaluation saved for this datased."""
        return len(list(self.dset['brf'].keys()))

    def save_brfperiod(self, period):
        """
        Save the specified period as a list containing a start and end date
        in the Excel numerical date format.
        """
        period = [float(val) for val in period]
        if len(period) != 2:
            raise ValueError("The size of the specified 'period' must be 2.")
        grp = self.dset.require_group('brf')
        grp.attrs['period'] = period
        self.dset.file.flush()

    def get_brfperiod(self):
        """
        Return a list with the start and end date of the last period
        saved by the user to evaluate the BRF.
        """
        grp = self.dset.require_group('brf')
        if 'period' not in list(grp.attrs.keys()):
            # Added in version 0.3.4 (see PR #240).
            return [None, None]
        else:
            return list(grp.attrs['period'])

    def get_brfname_at(self, index):
        if index < self.brf_count():
            names = list(self.dset['brf'].keys())
            names = np.array(names).astype(int)
            names.sort()
            return str(names[index])
        else:
            return None

    def get_brf(self, name):
        grp = self.dset['brf'][name]
        return (grp['lag'][...], grp['A'][...], grp['err'][...],
                grp['date start'][...], grp['date end'][...])

    def save_brf(self, lag, A, err, date_start, date_end):
        if list(self.dset['brf'].keys()):
            idnum = np.array(list(self.dset['brf'].keys())).astype(int)
            idnum = np.max(idnum) + 1
        else:
            idnum = 1
        idnum = str(idnum)

        grp = self.dset['brf'].require_group(idnum)
        grp.create_dataset('lag', data=lag, dtype='float64')
        grp.create_dataset('A', data=A, dtype='float64')
        grp.create_dataset('err', data=err, dtype='float64')
        grp.create_dataset('date start', data=date_start, dtype='int16')
        grp.create_dataset('date end', data=date_end, dtype='int16')
        self.dset.file.flush()
        print('BRF results saved successfully')

    def del_brf(self, name):
        """Delete the BRF evaluation saved with the specified name."""
        if name in list(self.dset['brf'].keys()):
            del self.dset['brf'][name]
            self.dset.file.flush()
            print('BRF %s deleted successfully' % name)
        else:
            print('BRF does not exist')

    # ---- Hydrograph layout

    def save_layout(self, layout):
        """Save the layout in the project hdf5 file."""
        grp = self.dset['layout']
        for key in list(layout.keys()):
            if key == 'colors':
                grp_colors = grp.require_group(key)
                for color in layout['colors'].keys():
                    grp_colors.attrs[color] = layout['colors'][color]
            else:
                if isinstance(layout[key], type(None)):
                    grp.attrs[key] = '__None__'
                elif isinstance(layout[key], bool):
                    grp.attrs[key] = '__' + str(layout[key]) + '__'
                else:
                    grp.attrs[key] = layout[key]
        self.dset.file.flush()

    def get_layout(self):
        """Return the layout dict that is saved in the project hdf5 file."""
        if 'TIMEmin' not in self.dset['layout'].attrs.keys():
            return None
        layout = {}
        for key in list(self.dset['layout'].attrs.keys()):
            layout[key] = self.dset['layout'].attrs[key]
            if layout[key] == '__None__':
                layout[key] = None
            elif layout[key] == '__True__':
                layout[key] = True
            elif layout[key] == '__False__':
                layout[key] = False

        layout['colors'] = {}
        grp_colors = self.dset['layout'].require_group('colors')
        for key in list(grp_colors.attrs.keys()):
            layout['colors'][key] = grp_colors.attrs[key].tolist()

        keys = list(layout.keys())
        if 'meteo_on' not in keys:
            # Added in version 0.3.2 (see PR #201)
            layout['meteo_on'] = True
        if 'glue_wl_on' not in keys:
            # Added in version 0.3.2 (see PR #202)
            layout['glue_wl_on'] = False
        if 'mrc_wl_on' not in keys:
            # Added in version 0.3.3 (see PR #225)
            layout['mrc_wl_on'] = False
        if 'figframe_lw' not in keys:
            # Added in version 0.3.3 (see PR #228)
            layout['figframe_lw'] = 0

        return layout


class WXDataFrameHDF5(WXDataFrameBase):
    """
    This is a wrapper around the h5py group to read the weather data
    from the project.
    """
    def __init__(self, dataset, *args, **kwargs):
        super(WXDataFrameHDF5, self).__init__(*args, **kwargs)
        self.__load_dataset__(dataset)

    def __getitem__(self, key):
        if key in list(self.store.attrs.keys()):
            return self.store.attrs[key]
        elif key in ['normals', 'yearly', 'monthly']:
            x = {}
            for vrb in self.store[key].keys():
                x[vrb] = self.store[key][vrb][...]
            if key == 'normals' and 'Period' not in x.keys():
                # This is needed for backward compatibility with
                # gwhat < 0.2.3 (see PR#142).
                x['Period'] = (np.min(self.store['Year']),
                               np.max(self.store['Year']))
            return x
        elif key == 'daily':
            vrbs = ['Year', 'Month', 'Day', 'Tmin', 'Tavg', 'Tmax',
                    'Rain', 'Snow', 'Ptot', 'PET']
            x = {}
            for vrb in vrbs:
                x[vrb] = self.store[vrb][...]
            return x
        else:
            return self.store[key][...]

    def __setitem__(self, key, value):
        return NotImplementedError

    def __iter__(self):
        return NotImplementedError

    def __len__(self, key):
        return NotImplementedError

    def __load_dataset__(self, dataset):
        """Saves the h5py dataset to the store."""
        self.store = dataset

    @property
    def name(self):
        return osp.basename(self.store.name)


class GLUEDataFrameHDF5(GLUEDataFrameBase):
    """
    This is a wrapper around the h5py group to read the GLUE results
    from the project.
    """
    def __init__(self, data, *args, **kwargs):
        super(GLUEDataFrameHDF5, self).__init__(*args, **kwargs)
        self.__load_data__(data)

    def __getitem__(self, key):
        """Return the value saved in the store at key."""
        if key not in self.store.keys():
            raise KeyError(key)

        if isinstance(self.store[key], h5py._hl.dataset.Dataset):
            return self.store[key][...]
        elif isinstance(self.store[key], h5py._hl.group.Group):
            return load_dict_from_h5grp(self.store[key])
        else:
            return None

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __load_data__(self, data):
        """Saves the h5py glue data to the store."""
        self.store = data


def is_dsetname_valid(dsetname):
    """
    Check if the dataset name respect the established guidelines to avoid
    problem with the hdf5 format.
    """
    return (dsetname != '' and
            not any(char in dsetname for char in INVALID_CHARS))


def make_dsetname_valid(dsetname):
    """Replace all invalid characters in the name by an underscore."""
    for char in INVALID_CHARS:
        dsetname = dsetname.replace(char, '_')
    return dsetname


def save_dict_to_h5grp(h5grp, dic):
    """
    Save the content of a dictionay recursively in a hdf5.
    Based on answers provided at
    https://codereview.stackexchange.com/questions/120802
    """
    for key, item in dic.items():
        if isinstance(item, dict):
            save_dict_to_h5grp(h5grp.require_group(key), item)
        else:
            h5grp.create_dataset(key, data=item)


def load_dict_from_h5grp(h5grp):
    """
    Retrieve the content of a hdf5 group and organize it in a dictionary.
    Based on answers provided at
    https://codereview.stackexchange.com/questions/120802
    """
    dic = {}
    for key, item in h5grp.items():
        if isinstance(item, h5py._hl.dataset.Dataset):
            dic[key] = item[...]
        elif isinstance(item, h5py._hl.group.Group):
            dic[key] = load_dict_from_h5grp(item)
    return dic


if __name__ == '__main__':
    FNAME = ("C:\\Users\\User\\gwhat\\Projects\\Example\\Example.gwt")
    PROJET = ProjetReader(FNAME)

    WLDSET = PROJET.get_wldset('3040002.0')
    print(WLDSET.glue_idnums())

    GLUEDF = WLDSET.get_glue('1')
    glue_count = GLUEDF['count']
    dly_glue = GLUEDF['daily budget']

    PROJET.db.close()
