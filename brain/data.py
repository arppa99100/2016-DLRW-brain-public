# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Roman C. Podolski <roman.podolski@tum.de>
#

"""
TODO Write docstring

"""

from __future__ import print_function

import os
import errno
import zipfile as z
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import collections
from random import shuffle as shuf

import scipy.io as spio
import scipy
import numpy as np
import globals as st
import glob
import re
from datetime import datetime

# load DATA_PATH from globals
DATA_DIR = st.DATA_PATH

#TODO: add parameters for type of target
#    - intention to reach and grasp
#    - onset of the load phase, i.e., intention to apply lifting forces
#    - the object
#    - replacement of object
#    - hand positions and velocitys (this one is going to be difficult)
def load_data(participant):
    """
    TODO: add detailed documentation

    """

    download_way_eeg_gal(participant)
    unzip_way_eeg_gal(participant)

    mat_file = os.path.join(DATA_DIR, 'P%d_AllLifts.mat' % participant)
    hand_start = loadnestedmat(mat_file)['P']['AllLifts'][:, 33]

    mat_file_list = glob.glob('%s/WS_P%d_*.mat' % (DATA_DIR, participant))
    storage = []
    for mat_file in mat_file_list:
        print('load windowed eeg data for participant #%d - name:'
              % participant, end=' ')
        data = loadnestedmat(mat_file)['ws']
        print('%s, series #%d ...' % (data['name'], data['series']), end=' ')
        i = 0
        for w in data['win']:
            X = np.asarray(w['eeg'])
            eeg_t = np.asarray(w['eeg_t'])
            led_on = np.asarray(w['LEDon'])
            Y = np.zeros_like(w['eeg_t'])

            # set all targets, withing a range of 150 - 250 ms after the LED
            # turns on, to class 1
            Y[np.logical_and(
                eeg_t >= led_on + .150, eeg_t <= led_on + .250)] = 1
            Y[np.logical_and(
                eeg_t >= hand_start[i] - .1, eeg_t <= hand_start[i] + .05)] = 2
            storage.append((X, Y))
            i += 1

        print('done!')

    s = len(storage) // 100 * 10

    train_x = [i[0] for i in storage[:len(storage) - 2 * s]]
    train_y = [i[1] for i in storage[:len(storage) - 2 * s]]
    train_set = (train_x, train_y)

    valid_x = [i[0] for i in storage[len(storage) - 2*s:len(storage) - s]]
    valid_y = [i[1] for i in storage[len(storage) - 2*s:len(storage) - s]]
    valid_set = (valid_x, valid_y)

    test_x = [i[0] for i in storage[len(storage) - s:]]
    test_y = [i[1] for i in storage[len(storage) - s:]]
    test_set = (test_x, test_y)

    return train_set, valid_set, test_set


def load_eeg(participant):
    """TODO: Docstring for load_eeg.

    :participant: TODO
    :returns: TODO

    """

    mat_file = os.path.join(DATA_DIR, 'HS_P%d_ST.mat' % participant)
    if(not os.path.isfile(mat_file)):
        unzip_way_eeg_gal(participant)
    data = loadnestedmat(mat_file)['hs']
    print('loading eeg data for participant #%d: %s ' % (
        participant, data['name']
    ))
    eeg_x = data['eeg']['sig']
    # TODO: load targets
    eeg_y = [] # targets currently unknown
    return eeg_x, eeg_y

def download_way_eeg_gal(participant, dir=DATA_DIR):
    """Downloads the WAY-EEG-GAL dataset

    Downloads the zipped WAY-EEG-GAL dataset of one given participant

    :type participant: int
    :param participant: participant data to download

    :type dir: string
    :param dir: path to dataset folder
    """

    origins = [('P1.zip', 'https://ndownloader.figshare.com/files/3229301'),
               ('P2.zip', 'https://ndownloader.figshare.com/files/3229304'),
               ('P3.zip', 'https://ndownloader.figshare.com/files/3229307'),
               ('P4.zip', 'https://ndownloader.figshare.com/files/3229310'),
               ('P5.zip', 'https://ndownloader.figshare.com/files/3229313'),
               ('P6.zip', 'https://ndownloader.figshare.com/files/3209486'),
               ('P7.zip', 'https://ndownloader.figshare.com/files/3209501'),
               ('P8.zip', 'https://ndownloader.figshare.com/files/3209504'),
               ('P9.zip', 'https://ndownloader.figshare.com/files/3209495'),
               ('P10.zip', 'https://ndownloader.figshare.com/files/3209492'),
               ('P11.zip', 'https://ndownloader.figshare.com/files/3209498'),
               ('P12.zip', 'https://ndownloader.figshare.com/files/3209489')]

    data_file, url = origins[participant - 1]

    try:
        os.makedirs(dir)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dir):
            pass
        else:
            raise

    new_path = os.path.join(dir, data_file)

    if(not os.path.isfile(new_path)):
        from six.moves import urllib
        import progressbar as pb

        print('Downloading %s from %s saving to %s ...\n' % (
            data_file, url, new_path
        ))

        widgets = [
            pb.Percentage(), ' ',
            pb.Timer(), ' ',
            pb.Bar(), ' ',
            pb.AnimatedMarker(), ' ',
            pb.ETA()
        ]

        # TODO: clint also offers a progress bar, use the one from clint
        pbar = pb.ProgressBar(widgets=widgets).start()

        def rephook(blocks_transfered, block_size, total_size):
            pbar.maxval = total_size // block_size + 1
            pbar.update(blocks_transfered)

        try:
            urllib.request.urlretrieve(url, new_path, reporthook=rephook)
        except OSError as exc:
            os.remove(new_path)
            return download_way_eeg_gal(participant, dir)

        pbar.finish()


def unzip_way_eeg_gal(participant, dir=DATA_DIR):
    """TODO: Docstring for unzip_way_eeg_gal.

    :participant: TODO

    """
    try:
        new_path = os.path.join(dir, 'P%d.zip' % participant)
        with z.ZipFile(new_path, 'r') as data_zip:
            for fname in data_zip.namelist():
                fpath = os.path.join(dir, fname)

                if(not os.path.isfile(fpath)):
                    print('Extracting %s to %s ...' % (fname, fpath))
                    data_zip.extract(fname, dir)
    except z.BadZipfile:
        os.remove(new_path)
        download_way_eeg_gal(participant, dir)


def loadnestedmat(filename):
    '''
    this function should be called instead of direct spio.loadmat-    as
    it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    '''
    data = spio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    return _check_keys(data)

def _check_keys(dictt):
    '''
    checks if entries in dictionary are mat-objects. If yes
    todict is called to change them to nested dictionaries
    '''
    for key in dictt:
        if isinstance(dictt[key], spio.matlab.mio5_params.mat_struct):
            dictt[key] = _todict(dictt[key])
    return dictt

def _todict(matobj):
    '''
    A recursive function which constructs from matobjects nested dictionaries
    '''
    dict = {}
    for strg in matobj._fieldnames:
        elem = matobj.__dict__[strg]
        if type(elem).__module__ == np.ndarray.__module__ and any(isinstance(x, scipy.io.matlab.mio5_params.mat_struct) for x in elem):
            elem = [_todict(a) for a in elem]
        if isinstance(elem, spio.matlab.mio5_params.mat_struct):
            dict[strg] = _todict(elem)
        else:
            dict[strg] = elem
    return dict

def extract_mat(zf, filename, relative_path=''):
    '''
    Comment from phil:
    Would seem logic to exctract here only and not to return anything, as this is loadnestedmat() for
    '''
    try:
        zf.extract(filename, path=relative_path+st.MAT_SUBDIR)
        return loadnestedmat(relative_path+st.MAT_SUBDIR+filename)
    except KeyError:
        print('ERROR: Did not find %s in zip file' % filename)

class Regexhandler(object):

    def __init__(self, reg):
        self.regex = reg

    def _extract(self, match):
        if match is not None:
            match = match.regs[0][1]
        end_pattern = re.compile('_|\.mat')
        end = end_pattern.search(self.regex, match)
        if end is not None:
            end = end.regs[0][0]
        return self.regex[match: end]

    def get_series(self):
        try:
            start_pattern = re.compile('_S')
            series_start = start_pattern.search(self.regex)
            return self._extract(series_start)
        except:
            raise Exception('Failed to extract series')

    def get_participant(self):
        try:
            start_pattern = re.compile('_P')
            participant_start = start_pattern.search(self.regex)
            return self._extract(participant_start)
        except:
            raise Exception('Failed to extract participant')

def getTables(regex):
    '''
    A function that returns all Tables matching to a particular regular expression
    Also extracts Tables that aren't yet present in st.MAT_SUBDIR

    e.g. r'WS_P1_S[0-9].mat' should return all windowed session tables as a list from Person 1
    '''

    reghandler = Regexhandler(regex)
    series_regex = reghandler.get_series()
    participant_regex = reghandler.get_participant()

    data = []
    archive_files = glob.glob(st.DATA_PATH + '/' + st.P_FILE_REGEX)
    for archive in archive_files:
        f_zip = z.ZipFile(archive, 'r')
        mat_file_list = f_zip.namelist()
        for f_mat in mat_file_list:
            if re.search(regex, f_mat):
                mat = extract_mat(f_zip, f_mat)
                ws = mat.get('ws')
                participant = ws.get('participant')
                series = ws.get('series')

                series_pattern = re.compile(series_regex)
                series_target = series_pattern.search(str(series))

                series_pattern = re.compile(participant_regex)
                participant_target = series_pattern.search(str(participant))

                if (series_target is not None) and (participant_target is not None):
                    ws = mat.get('ws')
                    for win in enumerate(ws.get('win')):
                        data.append(win[1])
    return data

def getRaw(regex):
    '''
    A function that returns all Tables matching to a particular regular expression
    Also extracts Tables that aren't yet present in st.MAT_SUBDIR

    e.g. r'WS_P1_S[0-9].mat' should return all windowed session tables as a list from Person 1

    This function returns just the raw tables and does not do any preprocessing
    '''


    data = []
    archive_files = glob.glob(st.DATA_PATH + st.P_FILE_REGEX)
    for archive in archive_files:
        f_zip = z.ZipFile(archive, 'r')
        mat_file_list = f_zip.namelist()
        for f_mat in mat_file_list:
            if re.search(regex, f_mat):
                mat = extract_mat(f_zip, f_mat)
                data.append(mat)
    return data

def get_eeg_emg(participant, series, data_selector=None):
    '''
    returns a list of dicts, having event times and dicts of eeg and emg data

    data (eeg/emg) dicts keys: windowed time in seconds from eeg_t/emg_t tables

    eeg data format: 32 channels + 1-5 targets
    emg data format: 5 channels + 1-5 targets

    targets (time windows):
    1. move hand to target:     tHandStart                  till tHandStart + trial_DurReach (= tFirstDigitTouch)
    2. lift object:             tLiftOff                    till LEDOff - 2
    3. hold phase:              LEDOff - 2                  till LEDOff
    4. replace object:          LEDOff                      till tReplace
    5. move hand to start:      tBothRelease                till tHandStop

    :param participant e.g. 1, [0-9]
    :param series e.g. 1, [0-9]
    :param data_selector "eeg", "emg" or None (default), if both data should be loaded.

    :return: list of dicts of eeg, emg data
    '''

    eventNames = ['move hand to target', 'lift object', 'hold phase', 'replace object', 'move hand to start']

    allTrials = []
    allLifts = getRaw(r'P'+str(participant)+'_AllLifts.mat')[0].get('P')
    allLifts_colNames = allLifts.get('ColNames')
    data_allLifts = allLifts.get('AllLifts')
    for sample in data_allLifts:
        allTrials.append(collections.OrderedDict(zip(np.asarray(allLifts_colNames), sample)))

    data = []
    ws_data = getTables(r'WS_P' + str(participant) + '_S' + str(series) + '.mat')
    for trial_id, win in enumerate(ws_data):
    # trial_id = 0
    # win = ws_data[0]

        tHandStart = allTrials[trial_id].get('tHandStart')
        tLiftOff = allTrials[trial_id].get('tLiftOff')
        LEDOff = allTrials[trial_id].get('LEDOff')
        tReplace = allTrials[trial_id].get('tReplace')
        tBothReleased = allTrials[trial_id].get('tBothReleased')
        tHandStop = allTrials[trial_id].get('tHandStop')
        tFirstDigitTouch = allTrials[trial_id].get('tFirstDigitTouch')
        # DurReach = allTrials[trial_id].get('Dur_Reach')
        # DurPreload = allTrials[trial_id].get('Dur_Preload')
        # tGrasp_start = tHandStart + DurReach

        eeg_dict = None
        if data_selector == None or data_selector == "eeg":
            e = win.get('eeg')
            eeg_seqlenght = e.shape[0]
            eeg_data = np.zeros((eeg_seqlenght, st.N_EEG_SENSORS + st.N_EEG_TARGETS))
            eeg_data[:eeg_seqlenght,0:st.N_EEG_SENSORS] = e
            eeg_data = normalize(eeg_data)

            eeg_t = win.get('eeg_t')
            eeg_dict = collections.OrderedDict(zip(eeg_t, eeg_data))

            for item in eeg_dict.iteritems():
                key = item[0]

                item[1][st.N_EEG_SENSORS: st.N_EEG_SENSORS + st.N_EEG_TARGETS] = 0
                if key > tHandStart and key < tFirstDigitTouch and st.SEQ_EEG_TARGETS[0] != -1:
                    item[1][st.N_EEG_SENSORS + st.SEQ_EEG_TARGETS[0]] = 1
                if key > tLiftOff and key < LEDOff - 2 and st.SEQ_EEG_TARGETS[1] != -1:
                    item[1][st.N_EEG_SENSORS + st.SEQ_EEG_TARGETS[1]] = 1
                if key > LEDOff - 2 and key < LEDOff and st.SEQ_EEG_TARGETS[2] != -1:
                    item[1][st.N_EEG_SENSORS + st.SEQ_EEG_TARGETS[2]] = 1
                if key > LEDOff and key < tReplace and st.SEQ_EEG_TARGETS[3] != -1:
                    item[1][st.N_EEG_SENSORS + st.SEQ_EEG_TARGETS[3]] = 1
                if key > tBothReleased and key < tHandStop and st.SEQ_EEG_TARGETS[4] != -1:
                    item[1][st.N_EEG_SENSORS + st.SEQ_EEG_TARGETS[4]] = 1


        # eeg_target_vec = np.asarray([item[32:] for item in eeg_dict.itervalues()])
        # xaxis = range(len(eeg_target_vec))
        # plt.plot(xaxis, eeg_target_vec[:,0])
        # plt.plot(xaxis, eeg_target_vec[:,1])
        # plt.show()

        emg_dict = None
        if data_selector == None or data_selector == "emg":
            e = win.get('emg')
            emg_seqlenght = e.shape[0]
            emg_data = np.zeros((emg_seqlenght, st.N_EMG_SENSORS + st.N_EMG_TARGETS))
            emg_data[:emg_seqlenght,0:st.N_EMG_SENSORS] = e
            emg_data = normalize(emg_data)

            emg_t = win.get('emg_t')
            emg_dict = collections.OrderedDict(zip(emg_t, emg_data))

            for item in emg_dict.iteritems():
                key = item[0]

                item[1][st.N_EMG_SENSORS: st.N_EMG_SENSORS+st.N_EMG_TARGETS] = 0
                if key > tHandStart and key < tFirstDigitTouch and st.SEQ_EMG_TARGETS[0] != -1:
                    item[1][st.N_EMG_SENSORS + st.SEQ_EMG_TARGETS[0]] = 1
                if key > tLiftOff and key < LEDOff - 2 and st.SEQ_EMG_TARGETS[1] != -1:
                    item[1][st.N_EMG_SENSORS + st.SEQ_EMG_TARGETS[1]] = 1
                if key > LEDOff - 2 and key < LEDOff and st.SEQ_EMG_TARGETS[2] != -1:
                    item[1][st.N_EMG_SENSORS + st.SEQ_EMG_TARGETS[2]] = 1
                if key > LEDOff and key < tReplace and st.SEQ_EMG_TARGETS[3] != -1:
                    item[1][st.N_EMG_SENSORS + st.SEQ_EMG_TARGETS[3]] = 1
                if key > tBothReleased and key < tHandStop and st.SEQ_EMG_TARGETS[4] != -1:
                    item[1][st.N_EMG_SENSORS + st.SEQ_EMG_TARGETS[4]] = 1




        data.append({'trial_id': trial_id, 'eeg_target': eeg_dict, 'emg_target': emg_dict,
                     'tHandStart': tHandStart, 'tLiftOff': tLiftOff, 'tBothReleased': tBothReleased,
                     'LEDOff': LEDOff, 'tReplace': tReplace, 'tHandStop': tHandStop,
                     'tFirstDigitTouch': tFirstDigitTouch})

    return data, eventNames

def load_multiple(participant, series, data_selector=None, shuffle=True):
    '''
    this is a wrapper for load_eeg_emg in order to be able to load more than one person/session at once.

    for more information look at load_emg_emg

    :param participant list e.g. [1, 2, 5]
    :param series list [1, 2, 3, 7]
    :param data_selector "eeg", "emg" or None (default), if both data should be loaded.
    :param shuffle determines if data should be shuffled randomly

    :return: list of dicts of eeg, emg data
    '''

    data = []
    for p in participant:
        download_way_eeg_gal(p)
        unzip_way_eeg_gal(p)
        for s in series:
            data_tmp, eventNames = get_eeg_emg(p, s, data_selector)
            data = data + data_tmp

    if shuffle:
        shuf(data)

    return data, eventNames

def normalize(data):
    '''
    :param data:
    :return: normalized data
    '''
    maxx = 1
    minn = -1
    data = np.abs(data)
    data_max = np.max(data, axis=0)
    data_min = np.min(data, axis=0)
    std = (data - data_min) / (data_max - data_min)
    data_scaled = std * (maxx - minn) + minn
    return data_scaled

def toUTCtimestamp(dt, epoch=datetime(1970, 1, 1)):
    td = dt - epoch
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 1e6
