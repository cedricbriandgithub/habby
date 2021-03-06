"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017-2018

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import os
import numpy as np
from scipy import stats
from scipy import optimize
from scipy import interpolate
import re
import time
import matplotlib.pyplot as plt
import h5py
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src_GUI import output_fig_GUI
from src_GUI import estimhab_GUI
from src import load_hdf5
import matplotlib as mpl


class Stathab:
    """
    The class for the Stathab model
    """
    
    def __init__(self, name_prj, path_prj):
        self.qlist = []  # the list of dicharge for each reach, usually in rivdis.txt
        self.qwh = []  # the discharge, the width and height
        # at least at two different dicharges (rivqvh.txt) a list of np.array
        self.disthmes = [] # the measured distribution of height (rivdist.txt) a list of np.array
        self.qhmoy = []  # the mean height and q (2 first llines of rivdis.txt)
        self.dist_gran = []  # the distribution of granulo (rivgra.txt)-only used by temperate river, a list of np.array
        self.data_ii = []  # only used by tropical river. The slope, waterfall height and length of river
        self.fish_chosen = []  # the name of the fish to be studied, the name should also be in pref.txt
        self.lim_all = []  # the limits or bornes of h,q and granulio (born*.txt)
        self.name_reach = []  # the list with the name of the reaches
        self.j_all = [] # the suitability indices
        self.granulo_mean_all = []  # average granuloa
        self.vclass_all = []  # volume of each velocity classes
        self.hclass_all = []  # surface height for all classes
        self.rclass_all = []   # granulo surface for all classes
        self.h_all = []  # total height of all the reaches
        self.w_all = []   # total width of all the reaches
        self.q_all = []   # discharge
        self.fish_chosen = np.array([])   # the name of the fish
        self.riverint = 0  # the river type (0 temperate, 1 tropicale univartiate, 2 tropical bivariate)
        self.name_reach = []  # the name of the reaches of the river
        self.path_im = path_prj   # path where to save the image
        self.load_ok = False # a boolean to manage the errors
        #  during the load of the files and the hdf5 creation and calculation
        self.path_prj = path_prj
        self.name_prj = name_prj
        # get the option for the figure in a dict
        self.fig_opt = []
        self.path_txt = path_prj # path where to save the text

    def load_stathab_from_txt(self, reachname_file, end_file_reach, name_file_allreach, path):
        """
        A function to read and check the input from stathab based on the text files.
        All files should be in the same folder.
        The file Pref.txt is read in run_stathab.
        If self.fish_chosen is not present, all fish in the preference file are read.

        :param reachname_file: the file with the name of the reaches to study (usually listirv)
        :param end_file_reach: the ending of the files whose names depends on the reach (with .txt or .csv)
        :param name_file_allreach: the name of the file common to all reaches
        :param path: the path to the file
        :return: the inputs needed for run_stathab
        """
        self.load_ok = False
        # self.name_reach
        self.name_reach = load_namereach(path, reachname_file)
        if self.name_reach == [-99]:
            return
        nb_reach = len(self.name_reach)

        # prep
        self.qwh = []
        self.qlist = []
        self.disthmes = []
        self.qhmoy = []
        self.dist_gran = []
        self.data_ii = []

        # read the txt files reach by reach
        for r in range(0, nb_reach):

            for ef in end_file_reach:
                # open rivself.qwh.txt
                if ef[-7:-4] == 'qhw':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    qwh_r = load_float_stathab(filename, True)
                    if np.array_equal(qwh_r, [-99]):  # if failed
                        return
                    else:
                        self.qwh.append(qwh_r)
                    if len(qwh_r[0]) != 3:
                        print('Error: The file called ' + filename + ' is not in the right format. Three columns '
                                                                     'needed. \n')
                        return
                    if len(qwh_r) < 2:
                        print('Error: The file called ' + filename + ' is not in the right format. Minimum two rows '
                                                                     'needed. \n')
                        return

                # open rivdeb.txt
                if ef[-7:-4] == 'deb':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    qlist_r = load_float_stathab(filename, True)
                    if np.array_equal(qlist_r, [-99]):
                        return
                    else:
                        self.qlist.append(qlist_r)
                    if len(qlist_r) < 2:
                        print('Error: two discharges minimum are needed in ' + filename + '\n')
                        return

                # open riv dis
                if ef[-7:-4] == 'dis':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    dis_r = load_float_stathab(filename, True)
                    if np.array_equal(dis_r, [-99]):  # if failed
                        return
                    if len(dis_r) < 4:
                        print('Error: The file called ' + filename + ' is not in the right format. At least four '
                                                                     'values needed. \n')
                        return
                    else:
                        # 0 = the discharge, 1 = the mean depth
                        if len(dis_r[2:]) != 20:
                            print('Warning: the number of class found is not 20 \n')
                        self.disthmes.append(dis_r[2:])
                        self.qhmoy.append(dis_r[:2])

                # open rivgra.txt
                if ef[-7:-4] == 'gra':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    dist_granulo_r = load_float_stathab(filename, True)
                    if np.array_equal(dist_granulo_r, [-99]):  # if failed
                        return
                    if len(dist_granulo_r) != 12:
                        print('Error: The file called ' + filename +
                              ' is not in the right format. 12 roughness classes are needed.\n')
                        return
                    else:
                        self.dist_gran.append(dist_granulo_r)

                # open data_ii.txt (only for tropical rivers)
                if ef[-6:-4] == 'ii':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    data_ii_r = load_float_stathab(filename, False)
                    if np.array_equal(data_ii_r, [-99]):  # if failed
                        return
                    if len(data_ii_r) != 3:
                        print('Error: The file called ' + filename + ' is not in the right format.  Three values needed.\n')
                        return
                    self.data_ii.append(data_ii_r)

        # open the files with the limits of class
        self.lim_all = []
        for b in range(0, len(name_file_allreach)):
            if name_file_allreach[b] != 'Pref.txt':
                filename = name_file_allreach[b]
                filename = os.path.join(path, filename)
                born = load_float_stathab(filename, False)
                if np.array_equal(born, [-99]):
                    return
                if len(born) < 2:
                    print('Error: The file called ' + filename + ' is not in the right format.  '
                                                                 'At least two values needed. \n')
                    return
                else:
                    self.lim_all.append(born)

        # usually not chosen fish if using the txt files
        self.fish_chosen = ['all_fish']
        # but try anyway to find fish
        filename = os.path.join(path, 'fish.txt')
        if os.path.isfile(filename):
            with open(filename, 'rt') as f:
                data = f.read()
            self.fish_chosen = data.split('\n')

        self.load_ok = True

    def load_stathab_from_hdf5(self):
        """
        A function to load the file from an hdf5 whose name is given in the xml project file. If the name of the
        file is a relative path, use the path_prj to create an absolute path.

        It works for tropical and temperate rivers. It checks the river type in the hdf5  files and
        used this river type regardless of the one curently used by the GUI. The method load_hdf5 in stathab_GUI
        get the value of self.riverint from the object mystathab to check the cohrenence between the GUI and the loaded
        hdf5.
        """
        self.load_ok = False
        # find the path to the xml file
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(fname):
            print('Error: The xml project file was not found. Save the project in the General Tab. \n')
            return
        doc = ET.parse(fname)
        root = doc.getroot()
        child = root.find(".//hdf5Stathab")
        if child is None:  # if there is data for STATHAB
            print("Error: No hdf5 file for Stathab is written in the xml project file. \n")
            return
        if not child.text:
            print("Error: No hdf5 file is written in the xml project file. (2) \n")
            return

        # load the h5 file
        fname_h5 = child.text
        blob = estimhab_GUI.StatModUseful()
        blob.path_prj = self.path_prj
        blob.name_prj = self.name_prj
        path_hdf5 = blob.find_path_hdf5_est()
        full_fname_hdf5 = os.path.join(path_hdf5, fname_h5)
        if os.path.isfile(fname_h5) or os.path.isfile(full_fname_hdf5):
            try:
                if os.path.isabs(fname_h5):
                    file_stathab = h5py.File(fname_h5, 'r+')
                else:
                    if self.path_prj:
                        file_stathab = h5py.File(full_fname_hdf5, 'r+')
                    else:
                        print('Error" No path to the project given although a relative path was provided')
                        return
            except OSError:
                print('Error: the hdf5 file could not be loaded.\n')
                return
        else:
            print("Error: The hdf5 file is not found. \n")
            return

        # prepare the data to be found
        basename1 = 'Info_general'

        # find the river type
        rinverint = file_stathab.attrs['riverint']
        try:
            riverint = int(rinverint)
            if riverint >2:
                print('The river type in the hdf5 should be 0,1,or 2.')
                return
        except ValueError:
            print('The river type in the hdf5 was not well formed')
            file_stathab.close()
            return
        self.riverint = riverint  # careful, must be "send" back to the GUI

        # load reach_name
        try:
            gen_dataset = file_stathab[basename1 + "/reach_name"]
        except KeyError:
            file_stathab.close()
            print('Error: the dataset reach_name is missing from the hdf5 file. Is ' + fname_h5 + ' a stathab input? \n')
            return
        if len(list(gen_dataset.values())) == 0:
            print('Error: The data name_reach could not be read. \n')
            return
        gen_dataset = list(gen_dataset.values())[0]
        gen_dataset = np.array(gen_dataset)
        if len(gen_dataset) == 0:
            print('Error: no reach names found in the hdf5 file. \n')
            file_stathab.close()
            return
        # hdf5 cannot strore string directly, needs conversion
        #  array[3,-2] is needed after bytes to string conversion
        for r in range(0, len(gen_dataset)):
            a = str(gen_dataset[r])
            self.name_reach.append(a[3:-2])

        # load limits
        if self.riverint == 0:
            gen_dataset_name = ['lim_h', 'lim_v', 'lim_g']
            for i in range(0, len(gen_dataset_name)):
                try:
                    gen_dataset = file_stathab[basename1 + "/" + gen_dataset_name[i]]
                except KeyError:
                    print("Error: the dataset" + gen_dataset_name[i] + "is missing from the hdf5 file.\n")
                    file_stathab.close()
                    return
                gen_dataset = list(gen_dataset.values())[0]
                if len(np.array(gen_dataset)) < 2:
                    print('Error: Limits of surface/volume could not be extracted from the hdf5 file. \n')
                    file_stathab.close()
                    return
                self.lim_all.append(np.array(gen_dataset))

            # get the chosen fish
            try:
                gen_dataset = file_stathab[basename1 + "/fish_chosen"]
            except KeyError:
                file_stathab.close()
                print('Error: the dataset fish_chosen is missing from the hdf5 file. \n')
                return
            gen_dataset = list(gen_dataset.values())[0]
            gen_dataset = np.array(gen_dataset)
            if len(gen_dataset) == 0:
                pass
                # print('Warning: no fish names found in the hdf5 file from stathab.\n')
                # file_stathab.close()
                # return
            # hdf5 cannot strore string directly, needs conversion
            #  array[3,-2] is needed after bytes to string conversion
            for f in range(0, len(gen_dataset)):
                a = str(gen_dataset[f])
                np.append(self.fish_chosen, a[3:-2])

        # get the data by reach
        if self.riverint == 0:
            reach_dataset_name = ['qlist', 'qwh', 'disthmes', 'qhmoy', 'dist_gran']
            reach_var = [self.qlist, self.qwh, self.disthmes, self.qhmoy, self.dist_gran]
        elif self.riverint == 1 or self.riverint == 2:
            reach_dataset_name = ['qlist', 'qwh', 'data_ii']
            reach_var = [self.qlist, self.qwh, self.data_ii]
        else:
            print('Error: self.riverint should be lower than two.')
            file_stathab.close()
            return

        for r in range(0, len(self.name_reach)):
            for i in range(0, len(reach_dataset_name)):
                try:
                    reach_dataset = file_stathab[self.name_reach[r] + "/" + reach_dataset_name[i]]
                except KeyError:
                    print("Error: the dataset"+ reach_dataset_name[i]+ "is missing from the hdf5 file. \n")
                    file_stathab.close()
                    return
                reach_dataset = list(reach_dataset.values())[0]
                if not reach_dataset:
                    print('Error: The variable ' + reach_dataset_name[r] +'could not be extracted from the hdf5 file.\n')
                reach_var[i].append(reach_dataset)

        self.load_ok = True
        file_stathab.close()

    def create_hdf5(self):
        """
        A function to create an hdf5 file from the loaded txt. It creates "name_prj"_STATHAB.h5, an hdf5 file with the
        info from stathab
        """
        self.load_ok = False

        # create an empty hdf5 file using all default prop.
        fname_no_path = self.name_prj + '_STATHAB' + '.h5'
        path_hdf5 = self.find_path_hdf5_stat()
        fname = os.path.join(path_hdf5, fname_no_path)
        try:
            file = h5py.File(fname, 'w')
        except OSError:
            print('Error: Stathab file could not be loaded \n')
            return

        # create all datasets and group
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version
        file.attrs['path_prj'] = self.path_prj
        file.attrs['name_prj'] = self.name_prj
        file.attrs['riverint'] = self.riverint

        for r in range(0, len(self.name_reach)):
            try:
                filereach = file.create_group(self.name_reach[r])
            except ValueError:  # unable to create group
                new_name = 'unnamed_reach_' + str(r)
                # if two identical names
                if r > 0:
                    if np.any(self.name_reach[r] == self.name_reach[:r-1]):
                        print('Warning: two reach with identical names.\n')
                        new_name = self.name_reach[r] + str(r+1)
                else:
                    print('Warning: Reach name are not compatible with hdf5.\n')
                filereach = file.create_group(new_name)
            # save data for each reach
            try:
                qmesg = filereach.create_group('qlist')
                qmesg.create_dataset(fname_no_path, data=self.qlist[r])
                qwhg = filereach.create_group('qwh')
                qwhg.create_dataset(fname_no_path, data=self.qwh[r])
                if self.riverint == 0:
                    distg = filereach.create_group('disthmes')
                    distg.create_dataset(fname_no_path, data=self.disthmes[r])
                    qhmoyg = filereach.create_group('qhmoy')
                    qhmoyg.create_dataset(fname_no_path, data=self.qhmoy[r])
                    dist_grang = filereach.create_group('dist_gran')
                    dist_grang.create_dataset(fname_no_path, data=self.dist_gran[r])
                if self.riverint > 0:
                    data_iig = filereach.create_group('data_ii')
                    data_iig.create_dataset(fname_no_path, data=self.data_ii[r])
            except IndexError:
                print('Error: the length of the data is not compatible with the number of reach.\n')
                file.close()
                return

        allreach = file.create_group('Info_general')
        reachg = allreach.create_group('reach_name')
        reach_ascii = [n.encode("utf8", "ignore") for n in self.name_reach]  # unicode is not ok with hdf5
        reachg.create_dataset(fname_no_path, (len(reach_ascii), 1), data=reach_ascii)
        if self.riverint == 0:
            limhg = allreach.create_group('lim_h')
            limhg.create_dataset(fname_no_path, [len(self.lim_all[0])], data=self.lim_all[0])
            limvg = allreach.create_group('lim_v')
            limvg.create_dataset(fname_no_path, [len(self.lim_all[1])], data=self.lim_all[1])
            limgg = allreach.create_group('lim_g')
            limgg.create_dataset(fname_no_path, [len(self.lim_all[2])], data=self.lim_all[2])
        fishg = allreach.create_group('fish_chosen')
        fish_chosen_ascii = [n.encode("ascii", "ignore") for n in self.fish_chosen]  # unicode is not ok with hdf5
        fishg.create_dataset(fname_no_path, (len(self.fish_chosen), 1), data=fish_chosen_ascii)
        # close and save hdf5
        file.close()
        self.load_ok = True

    def save_xml_stathab(self, no_hdf5=False):
        """
        The function which saves the function related to stathab in the xml projexct files

        :param no_hdf5: If True, no hdf5 file was created (usually because Stathab crashed at some points)
        """

        fname_no_path = self.name_prj + '_STATHAB' + '.h5'
        if no_hdf5:
            fname_no_path = ''

        # write info in the xml project file
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            print('Error: No project saved. Please create a project first in the Start tab.\n')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//Stathab")
            if child is None:
                stathab_element = ET.SubElement(root, "Stathab")
                hdf5file = ET.SubElement(stathab_element, "hdf5Stathab")
                hdf5file.text = fname_no_path
                hdf5file.set('riverint', str(self.riverint))  # attribute
            else:
                hdf5file = root.find(".//hdf5Stathab")
                if hdf5file is None:
                    hdf5file = ET.SubElement(child, "hdf5Stathab")
                    hdf5file.text = fname_no_path
                else:
                    hdf5file.text = fname_no_path
                hdf5file.set('riverint', str(self.riverint))  # attribute
            doc.write(filename_prj)

    def stathab_calc(self, path_pref='.', name_pref='Pref_latin.txt'):
        """
        The function to calculate stathab output.

        :param path_pref: the path to the preference file
        :param name_pref: the name of the preference file
        :return: the biological preferrence index (np.array of [reach, specices, nbclaq] size), surface or volume by class, etc.
        """

        self.load_ok = False
        # various info
        nbclaq = 50  # number of discharge point where the data have to be calculate
        nbclagg = 12  # number of empirical roughness class
        coeff_granu = np.array([0.00001, 0.0001, 0.00028, 0.00125, 0.005, 0.012, 0.024, 0.048, 0.096, 0.192, 0.640, 1.536])  # WHY?
        nb_reach = len(self.name_reach)
        find_one_fish = False
        [name_fish, coeff_all] = load_pref(name_pref, path_pref)

        # choose which fish are studied
        coeff = np.zeros((len(self.fish_chosen), coeff_all.shape[1]))

        fish_chosen2 = np.array(self.fish_chosen)  # so we can use np.any
        if np.any(fish_chosen2 == 'all_fish'):
            coeff = coeff_all
            self.fish_chosen = name_fish
            find_one_fish = True
        else:
            for f in range(0, len(self.fish_chosen)):
                if self.fish_chosen[f] in name_fish:
                    ind_fish = name_fish.index(self.fish_chosen[f])
                    coeff[f, :] = coeff_all[ind_fish, :]
                    find_one_fish = True
                else:
                    print('Warning: One fish species was not found in the '
                          'Preference file. Fish name: ' + self.fish_chosen[f] +'\n')
        if not find_one_fish:
            print('Error: No fish species have been given or the fish species could not be found.\n')
            return -99

        # the biological preference index for all reach, all species
        self.j_all = np.zeros((nb_reach, len(self.fish_chosen), nbclaq))

        for r in range(0, nb_reach):

            # data for this reach
            try:
                qwh_r = self.qwh[r]
                qhmoy_r = self.qhmoy[r]
                h0 = qhmoy_r[1]
                disthmes_r = self.disthmes[r]
                qlist_r = self.qlist[r]
                dist_gran_r = np.array(self.dist_gran[r])
            except IndexError:
                print('Error: data not coherent with the number of reach \n')
                return
            hclass = np.zeros((len(self.lim_all[0])-1, nbclaq))
            vclass = np.zeros((len(self.lim_all[1])-1, nbclaq))
            rclass = np.zeros((len(self.lim_all[2])-1, nbclaq))
            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))

            # granulometry
            granulo_mean = np.sum(coeff_granu * dist_gran_r)
            self.granulo_mean_all.append(granulo_mean)
            lim_g = self.lim_all[2]
            lim_g[lim_g < 0] = 0
            lim_g[lim_g > 11] = 11
            dist_gs = np.zeros(len(lim_g)-1,)
            for cg in range(0, len(lim_g)-1):
                lim_cg = [np.int(np.floor(lim_g[cg])), np.floor(lim_g[cg+1])]
                dist_chosen = dist_gran_r[np.int(lim_cg[0]):np.int(lim_cg[1])]
                dist_gs[cg] = np.sum(dist_chosen)

            # get the distributions and power law ready
            [h_coeff, w_coeff] = self.power_law(qwh_r)
            sh0 = self.find_sh0_maxvrais(disthmes_r, h0)

            # check if discharge are coherent
            if min(qlist_r) < qwh_r[0, 0]/10 or max(qlist_r) > qwh_r[1, 0]*5:
                print('Warning: Discharge range is far from measured discharge. Results might be unrealisitc. \n')

            # for all discharge
            for qind in range(0, nbclaq):
                lnqs = np.log(min(qlist_r)) + (qind+0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs*h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs*w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs)/(hs*ws)
                dist_hs = self.dist_h(sh0, h0, self.lim_all[0], hs)
                dist_vs = self.dist_v(hs, granulo_mean, self.lim_all[1], vs)
                # multiply by width and surface
                v = ws * hs  # total volume
                vclass[:, qind] = ws*dist_vs*hs
                hclass[:, qind] = dist_hs * ws
                rclass[:, qind] = dist_gs*ws
                # calculate the biological preference index
                j = coeff[:, 0] * v
                for vc in range(0, len(vclass[:, qind])):
                    j += vclass[vc, qind] * coeff[:, vc+1]
                for hc in range(0, len(hclass[:, qind])):
                    j += hclass[hc, qind] * coeff[:, hc + len(vclass[:, qind]) + 1]
                for rc in range(0, len(rclass[:, qind])):
                    j += rclass[rc, qind] * coeff[:, rc + len(hclass[:, qind]) + len(vclass[:, qind])+1]
                self.j_all[r, :, qind] = j
            self.vclass_all.append(vclass)
            self.hclass_all.append(hclass)
            self.rclass_all.append(rclass)
            self.h_all.append(hmod)
            self.w_all.append(wmod)
            self.q_all.append(qmod)

        self.load_ok = True

    def stathab_trop_univ(self, path_bio, by_vol):
        """
        This function calculate the stathab outputs  for the univariate preference file in the case where the river is
        steep and in the tropical regions (usually the islands of Reunion and Guadeloupe).

        :param path_bio: the path to the preference file usually biology/stathab
        :param by_vol: If True the output is by volum (VPU instead of SPU) from the velcoity pref file
        :return: the SPU or VPU
        """

        # various info
        self.load_ok = False
        nb_reach = len(self.name_reach)
        nbclaq = 50  # number of discharge value where the data have to be calculated
        nbclass = 20 # number of height and velcoity class (do not change without changing dist_h_trop and _dist_v_trop)

        # get the preference info based on the files known
        code_fish = self.fish_chosen
        [datah_all, datav_all] = load_pref_trop_uni(code_fish, path_bio)
        nb_fish = len(datah_all)
        pref_v_all = np.zeros((nb_reach, nb_fish, nbclaq))
        pref_h_all = np.zeros((nb_reach, nb_fish, nbclaq))
        if nb_fish == 0:
            print('Error: No fish found \n')
            return

        # the biological preference index for all reach, all species
        self.j_all = np.zeros((nb_reach, len(self.fish_chosen), nbclaq))

        # for each reach
        for r in range(0, nb_reach):

            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))
            try:
                qwh_r = self.qwh[r]
                qlist_r = self.qlist[r]
            except IndexError:
                print('Error: data not coherent with the number of reach \n')
                return

            # get the power law
            [h_coeff, w_coeff] = self.power_law(qwh_r)

            # for each Q
            for qind in range(0, nbclaq):

                # discharge, height and velcoity data
                lnqs = np.log(min(qlist_r)) + (qind + 0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs * h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs) / (hs * ws)

                # get dist h
                [h_dist, h_born] = self.dist_h_trop(vs, hs, self.data_ii[r][0])
                # get dist v
                [v_dist, v_born] = self.dist_v_trop(vs, hs, self.data_ii[r][1], self.data_ii[r][2])

                # calculate J
                for f in range(0, nb_fish):
                    # to be checked
                    pref_h = np.interp(h_born, datah_all[f][:, 0], datah_all[f][:, 1])
                    pref_v = np.interp(v_born, datav_all[f][:, 0], datav_all[f][:, 1])
                    h_index = np.sum(pref_h * h_dist)
                    v_index = np.sum(pref_v * v_dist)
                    pref_h_all[r, f, qind] = h_index * ws
                    pref_v_all[r, f, qind] = v_index * ws * hs
                self.h_all.append(hmod)
                self.w_all.append(wmod)
                self.q_all.append(qmod)

        # why?
        if by_vol:
            self.j_all = pref_v_all
        else:
            self.j_all = pref_h_all

        self.load_ok = True

    def stathab_trop_biv(self, path_bio):
        """
        This function calculate the stathab outputs  for the bivariate preference file in the case where the river is
        steep and in the tropical regions (usually the islands of Reunion and Guadeloupe).

        :param path_bio:
        :return:
        """

        # various info
        self.load_ok = False
        nb_reach = len(self.name_reach)
        nbclaq = 50  # number of discharge value where the data have to be calculated

        # get the preference info based on the files known
        code_fish = self.fish_chosen
        data_pref_all = load_pref_trop_biv(code_fish, path_bio)
        nb_fish = len(data_pref_all)
        if nb_fish == 0:
            print('Error: No fish found \n')
            return

        # the biological preference index for all reach, all species
        self.j_all = np.zeros((nb_reach, len(self.fish_chosen), nbclaq))

        # for each reach
        for r in range(0, nb_reach):

            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))
            try:
                qwh_r = self.qwh[r]
                qlist_r = self.qlist[r]
            except IndexError:
                print('Error: data not coherent with the number of reach \n')
                return

            # get the power law
            [h_coeff, w_coeff] = self.power_law(qwh_r)

            # for each Q
            for qind in range(0, nbclaq):
                # discharge, height and velcoity data
                lnqs = np.log(min(qlist_r)) + (qind + 0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs * h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs) / (hs * ws)

                # get dist h
                [h_dist, h_born] = self.dist_h_trop(vs, hs, self.data_ii[r][0])
                # get dist v
                [v_dist, v_born] = self.dist_v_trop(vs, hs, self.data_ii[r][1], self.data_ii[r][2])

                # change to the vecloity and heigth distribtion because we are in bivariate
                # we nomalize the height distribution (between 0 and 1 ) and mulitply it with the velocity
                h_dist = h_dist / h_born
                h_dist = h_dist / sum(h_dist)  # normalisation to one, (like getting a mini-volum?)
                rep_num = len(h_dist)
                v_dist = np.repeat(v_dist, rep_num)  # [0,1,2] -> [0,0,1,1,2,2]
                h_vol = np.tile(h_dist, (1, rep_num))  # [0,1,2] -> [0,1,2,0,1,2]
                biv_dist = (h_vol * v_dist).T

                # calculate J
                for f in range(0, nb_fish):

                    # interpolate the preference file to the new point
                    data_pref = data_pref_all[f]
                    v_born2 = np.repeat(v_born, rep_num)
                    h_born2 = np.squeeze(np.tile(h_born, (1, rep_num)))
                    point_vh = np.array([v_born2, h_born2]).T
                    pref_here = interpolate.griddata(data_pref[:, :2], data_pref[:,2], point_vh, method='linear')

                    self.j_all[r, f, qind] = np.sum(pref_here * biv_dist.T) * ws*hs
                self.h_all.append(hmod)
                self.w_all.append(wmod)
                self.q_all.append(qmod)

        self.load_ok = True

    def power_law(self, qwh_r):
        """
        The function to calculate power law for discharge and width
        ln(h0 = a1 + a2 ln(Q)

        :param qwh_r: an array where each line in one observatino of Q, width and height
        :return: the coeff of the regression
        """
        # input
        q = qwh_r[:, 0]
        h = qwh_r[:, 1]
        w = qwh_r[:, 2]

        # fit power-law
        h_coeff = np.polyfit(np.log(q), np.log(h), 1)  # h_coeff[1] + ln(Q) *h_coeff[0]
        w_coeff = np.polyfit(np.log(q), np.log(w), 1)

        return h_coeff, w_coeff

    def find_sh0(self, disthmesr, h0):
        """
        the function to find sh0, using a minimzation technique. Not used because the output was string.
        Possibly an error on the bornes? We remplaced this function by the function find_sh0_maxvrais().

        :param disthmesr: the measured distribution of height
        :param h0: the measured mean height
        :return: the optimized sh0
        """

        bornhmes = np.arange(0, len(disthmesr)+1) * 5*h0  # in c code, bornes are 1:n, so if we divide by h -> 1:n * h
        # optimization by non-linear least square
        # if start value equal or above one, the optimization fails.
        [sh0_opt, pcov] = optimize.curve_fit(lambda h, sh0: self.dist_h(sh0, h0, bornhmes, h), h0, disthmesr, p0=0.5)
        return sh0_opt

    def find_sh0_maxvrais(self, disthmesr, h0):
        """
        the function to find sh0, using the maximum of vraisemblance.
        This function aims at reproducing the results from the c++ code. Hence, no use of scipy

        :param disthmesr: the measured distribution of height
        :param h0: the measured mean height
        :return: the optimized sh0
        """
        nbclaemp = 20
        vraismax = -np.inf
        clmax = nbclaemp-1
        sh0 = 0
        for p in range(0, 101):
            sh = p/100
            if sh == 0:
                sh += 0.00001  # no log(0)
            if sh == 1:
                sh -= 0.00001
            vrais = disthmesr[0] * np.log(sh * (1-np.exp(-(1./4.))) + (1-sh)*(stats.norm.cdf(((1./4.)-1)/0.419)))
            vrais += disthmesr[clmax] * np.log(sh * np.exp(-(clmax/4.)) +
                                               (1 - sh) * (1 - stats.norm.cdf(((clmax / 4.) - 1) / 0.419)))
            for cla in range(1, clmax):
                vrais += disthmesr[cla] * np.log(sh * (np.exp(-cla / 4.) - np.exp(-(cla + 1) / 4.))+
                                                 (1 - sh) * (stats.norm.cdf(((cla + 1) / 4. - 1) / 0.419) -
                                                             stats.norm.cdf((cla / 4. - 1) / 0.419)))
            if vrais > vraismax:
                vraismax = vrais
                sh0 = p/100
        return sh0

    def dist_h(self, sh0, h0, bornh, h):
        """
        The calculation of height distribution  acrros the river
        The distribution is a mix of an exponential and guassian.

        :param sh0: the sh of the original data
               sh is the parameter of the distribution, gives the relative importance of ganussian and exp distrbution
        :param h: the mean height data
        :param h0: the mean height
        :param bornh: the limits of each class of height
        :return: disth the distribution of heights across the river for the mean height h.

        """
        # sh
        # sh0 = 0.48
        sh = sh0 - 0.7 * np.log(h/h0)
        if sh > 1:
            sh = 1.
        if sh < 0:
            sh = 0.
        # prep
        nbclass = len(bornh) - 1
        disth = np.zeros((nbclass, ))
        # all class and calcul
        for cl in range(0, nbclass):
            a = bornh[cl] / h
            b = bornh[cl + 1] / h
            c = a
            # why?
            if a <= 0 and cl == 0:
                c = -np.inf
                a = 0
            # based on Lamouroux, 1998 (Depth probability distribution in stream reaches)
            disth[cl] = sh * (np.exp(-a) - np.exp(-b)) + \
                        (1 - sh) * (stats.norm.cdf((b - 1) / 0.419) - stats.norm.cdf((c - 1) / 0.419))
        return disth

    def dengauss(self, x):
        """
        gaussian density, used only for debugging purposes.
        This is not used in Habby, but can be useful if scipy is not available (remplace all stat.norm.cdf with
        dengauss)

        :param x: the parameter of the gaussian
        :return: the gaussian density
        """
        n = 0
        if x > 3.72:
            return 1
        if x < -3.72:
            return 0.
        if x < 0:
            n = -1
            x = -x
        s3 = x
        t1 = x
        k3 = 0
        while True:  # do loop in python?
            k3 += 1
            t2 = (-1) * t1 * x * x / (2 * k3)
            t1 = t2
            t2 = t2/(2 * k3 + 1)
            s3 += t2
            if abs(t2) < 0.000001:
                break
        res = 0.5 + 0.398942 * s3
        if n == -1:
            res = 1-res
        return res

    def dist_v(self, h, d, bornv, v):
        """
        The calculation of velocity distribution across the river
        The distribution is a mix of an exponential and guassian.

        :param h: the height which is related to the mean velocity v
        :param d: granulo moyenne
        :param bornv: the born of the velocity
        :param v: the mean velocity
        :return: the distribution of velocity across the river
        """
        # sv
        fr = v/np.sqrt(9.81*h)
        relrough = d / h
        sv = -0.275 - 0.237 * np.log(fr) + 0.274 * relrough
        if sv < 0:
            sv = 0
        if sv > 1:
            sv = 1
        # prep
        nbclass = len(bornv) - 1
        distv = np.zeros((nbclass,))
        # all class and calcul
        for cl in range(0, nbclass):
            a = bornv[cl] / v
            b = bornv[cl + 1] / v
            c = a
            if a <= 0 and cl == 0:
                c = -np.inf
                a = 0
            # based on Lamouroux, 1995 (predicting velocity frequency distributions)
            # dist = f1(exp) + f2(gaussian) + f3(gaussian)
            distv[cl] = sv * 0.642 * (np.exp(-a / 0.193) - np.exp(-b / 0.193)) \
                + sv * 0.358 * (stats.norm.cdf((b - 2.44) / 1.223) - stats.norm.cdf((c - 2.44) / 1.223))\
                + (1 - sv) * (stats.norm.cdf((b - 1) / 0.611) - stats.norm.cdf((c - 1) / 0.611))
        return distv

    def dist_h_trop(self,v,h, mean_slope):
        """
        This function calulate the height distribution for steep tropical stream based on the R code from
        Girard et al. (stathab_hyd_steep). The frequency distribution is based on empirical data which
        is given in the list of numbers in the codes below. The final frequency distribution is in the form:
        t xf1 + (1-t) x f where t is a function of the froude number and the mean slope of the station.

        The height limits are considered constant here (constrarily to dist_h where they are given in the parameter
        bornh).

        :param v: the velcoity for this discharge
        :param h: the height for this discharge
        :param mean_slope: the mean slope of the station (usally in the data_ii[0] variable)
        :return: the distribution of height

        """

        # general info
        g = 9.80665  # gravitation constant
        fr = v/np.sqrt(g*h)

        # empirical freq. distributions
        fd_h =[0.221545010, 0.193846678, 0.117355060, 0.110029404, 0.074083455, 0.071369872, 0.054854534,
               0.025952644, 0.024479842, 0.021200121, 0.015840696, 0.018349236, 0.010369520, 0.006917000,
               0.005550880, 0.003432236, 0.001366120, 0.003366120, 0.006118644, 0.013972928]
        fc_h = [0.10786195, 0.12074410, 0.14866942, 0.13869359, 0.16721162, 0.11451288, 0.08924672, 0.05603628,
                0.02442850, 0.02209880, 0.01049615, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000,
                0.00000000, 0.00000000, 0.00000000, 0.00000000]

        # get the mixiing parameters
        tmix_lien = -2.775 - 0.838*np.log(fr) + 0.087*mean_slope
        tmix = np.exp(tmix_lien)/(1+np.exp(tmix_lien))

        # height disitrbution
        h_dist = np.zeros((len(fd_h),))
        for i in range(0, len(fd_h)):
            h_dist[i] = tmix * fd_h[i] + (1-tmix) * fc_h[i]

        h_born = np.arange(0.125, 5, 0.25) *h

        return h_dist, h_born

    def dist_v_trop(self,v,h, h_waterfall, length_stat):
        """
        This function calulate the velocity distribution for steep tropical stream based on the R code from
        Girard et al. (stathab_hyd_steep). The frequency distribution is based on empirical data which
        is given in the list of numbers in the codes below. The final frequency distribution is in the form:
        t x f1 + (1-t) x f where t depends on the ratio of the length of station and the height of the waterfall.

        :param v: the velcoity for this discharge
        :param h: the height for this discharge
        :param h_waterfall: the height of the waterfall
        :param length_stat: the length of the station
        :return: the distribution of velocity

        """

        # prep
        g = 9.80665  # gravitation constant
        ichu = h_waterfall/length_stat
        fr = v / np.sqrt(g * h)

        # empirical freq. distributions
        fd_v = [0.367737038, 0.171825373, 0.070912537, 0.049956434, 0.042982367, 0.037409374, 0.032246954,
                0.025315107, 0.019778008, 0.018990529, 0.011506684, 0.018655122, 0.016300231, 0.012822439,
                0.012222620, 0.006738370, 0.007714692, 0.003348316, 0.006082559, 0.001749545, 0.065705701]
        fc_v = [0.113325663, 0.167094505, 0.104591869, 0.091699585, 0.076272551, 0.076247281, 0.075009649,
                0.066482669, 0.057792617, 0.058358048, 0.036947598, 0.025192247, 0.024107747, 0.014137293,
                0.003300867, 0.006857482, 0.002582328, 0.000000000, 0.000000000, 0.000000000, 0.000000000]

        # get the mixing paramter
        if np.isnan(ichu):
            smix_lien = -3.163-1.344*np.log(fr)
        else:
            smix_lien = -4.53-1.58*np.log(fr)+0.159*ichu
        smix = np.exp(smix_lien) / (1 + np.exp(smix_lien))

        # velocity distribution
        v_dist = np.zeros((len(fd_v),))
        for i in range(0, len(fd_v)):
            v_dist[i] = smix * fd_v[i] + (1 - smix) * fc_v[i]

        v_born = np.arange(-0.125, 5, 0.25)*v

        # change the length as needed
        v_born = v_born[1:]
        v_dist[1] = v_dist[0] + v_dist[1]
        v_dist = v_dist[1:]

        return v_dist,v_born

    def savefig_stahab(self, show_class=True):
        """
        A function to save the results in text and the figure. If the argument show_class is True,
        it shows an extra figure with the size of the different height, granulo, and velocity classes. The optional
        figure only works when stathab1 for temperate river is used.

        """
        # figure option
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        plt.rcParams['figure.figsize'] = self.fig_opt['width'], self.fig_opt['height']
        plt.rcParams['font.size'] = self.fig_opt['font_size']
        plt.rcParams['lines.linewidth'] = self.fig_opt['line_width']
        format = int(self.fig_opt['format'])
        plt.rcParams['axes.grid'] = self.fig_opt['grid']
        mpl.rcParams['pdf.fonttype'] = 42
        if self.fig_opt['font_size'] > 7:
            plt.rcParams['legend.fontsize'] = self.fig_opt['font_size'] - 2
        plt.rcParams['legend.loc'] = 'best'
        mpl.interactive(True)
        erase1 = self.fig_opt['erase_id']
        if erase1 == 'True':  # xml in text
            erase1 = True
        else:
            erase1 = False

        if len(self.q_all) < len(self.name_reach):
            print('Error: Could not find discharge data. Figure not plotted. \n')
            return

        for r in range(0, len(self.name_reach)):

            qmod = self.q_all[r]
            if show_class:
                rclass = self.rclass_all[r]
                hclass = self.hclass_all[r]
                vclass = self.vclass_all[r]
                vol = self.h_all[0] * self.w_all[0]

                fig = plt.figure()
                plt.subplot(221)
                if self.fig_opt['language'] == 0:
                    plt.title('Total Volume')
                    plt.ylabel('Volume for 1m of reach [m3]')
                    plt.title('Surface by class for the granulometry')
                elif self.fig_opt['language'] == 1:
                    plt.title('Volume total')
                    plt.ylabel('Volume pour 1m de troncon [m3]')
                else:
                    plt.title('Total Volume')
                    plt.ylabel('Volume for 1m of reach [m3]')
                    plt.title('Surface by class for the granulometry')
                plt.plot(qmod, vol)
                plt.subplot(222)
                if self.fig_opt['language'] == 0:
                    plt.title('Surface by class for the granulometry')
                    plt.ylabel('Surface by class [m$^{2}$]')
                elif self.fig_opt['language'] == 1:
                    plt.title('Surface par classe de granulométrie')
                    plt.ylabel('Surface par classe [m$^{2}$]')
                else:
                    plt.title('Surface by class for the granulometry')
                    plt.ylabel('Surface by class [m$^{2}$]')
                for g in range(0, len(rclass)):
                    plt.plot(qmod, rclass[g], '-', label='Class ' + str(g))
                lgd = plt.legend(bbox_to_anchor=(1.4, 1), loc='upper right', ncol=1)
                plt.subplot(223)
                if self.fig_opt['language'] == 0:
                    plt.title('Surface by class for the height')
                elif self.fig_opt['language'] == 1:
                    plt.title('Surface par classe pour la hauteur')
                else:
                    plt.title('Surface by class for the height')
                for g in range(0, len(hclass)):
                    plt.plot(qmod, hclass[g, :], '-', label='Class ' + str(g))
                plt.xlabel('Q [m$^{3}$/sec]')
                if self.fig_opt['language'] == 0:
                    plt.ylabel('Surface by class [m$^{2}$]')
                elif self.fig_opt['language'] == 1:
                    plt.ylabel('Surface par classe [m$^{2}$]')
                else:
                    plt.ylabel('Surface by class [m$^{2}$]')
                lgd = plt.legend()
                plt.subplot(224)
                if self.fig_opt['language'] == 0:
                    plt.title('Volume by class for the velocity')
                elif self.fig_opt['language'] == 1:
                    plt.title('Volume par classe pour la vitesse')
                else:
                    plt.title('Volume by class for the velocity')
                for g in range(0, len(vclass)):
                    plt.plot(qmod, vclass[g], '-', label='Class ' + str(g))
                plt.xlabel('Q [m$^{3}$/sec]')
                if self.fig_opt['language'] == 0:
                    plt.ylabel('Volume by Class [m$^{3}$]')
                elif self.fig_opt['language'] == 1:
                    plt.ylabel('Volume par classe [m$^{3}$]')
                else:
                    plt.ylabel('Volume by Class [m$^{3}$]')
                lgd = plt.legend(bbox_to_anchor=(1.4, 1), loc='upper right', ncol=1)

                # save the figures
                if not erase1:
                    if format == 0 or format == 1:
                        name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                                "_vel_h_gran_classes" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png')
                    if format == 0 or format == 3:
                        name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                                "_vel_h_gran_classes" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf')
                    if format == 2 or format > 2:
                        name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                                "_vel_h_gran_classes" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.jpg')
                    fig.savefig(os.path.join(self.path_im, name_fig), bbox_extra_artists=(lgd,), bbox_inches='tight',
                                dpi=self.fig_opt['resolution'])
                else:
                    if format == 0 or format == 1:
                        name_fig = os.path.join(self.path_im, self.name_reach[r] + "_vel_h_gran_classes.png")
                    if format == 0 or format == 3:
                        name_fig = os.path.join(self.path_im, self.name_reach[r] + "_vel_h_gran_classes.pdf")
                    if format == 2 or format > 2:
                        name_fig = os.path.join(self.path_im, self.name_reach[r] + "_vel_h_gran_classes.jpg")
                    if os.path.isfile(name_fig):
                        os.remove(name_fig)
                    fig.savefig( name_fig, bbox_extra_artists=(lgd,), bbox_inches='tight',
                                dpi=self.fig_opt['resolution'])

            # suitability index
            if len(self.fish_chosen) > 1:
                j = np.squeeze(self.j_all[0, :, :])
            fig = plt.figure()
            if len(self.fish_chosen) > 1:
                for e in range(0, len(self.fish_chosen)):
                    plt.plot(qmod, j[e, :], '-', label=self.fish_chosen[e])
            else:
                plt.plot(qmod, self.j_all[0, 0, :], '-', label=self.fish_chosen[0])
            plt.xlabel('Q [m$^{3}$/sec]')
            plt.ylabel('Index J [ ]')
            if self.fig_opt['language'] == 0:
                plt.title('Suitability index J - ' + self.name_reach[r])
            elif self.fig_opt['language'] == 1:
                plt.title('Index de suitabilité J - ' + self.name_reach[r])
            else:
                plt.title('Suitability index J - ' + self.name_reach[r])

            lgd = plt.legend(fancybox=True, framealpha=0.5)
            if not erase1:
                if format == 0 or format == 1:
                    name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                            "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S")+'.png')
                if format == 0 or format == 3:
                    name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                            "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf')
                if format == 2:
                    name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                            "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.jpg')
                fig.savefig(name_fig, bbox_extra_artists=(lgd,), bbox_inches='tight',
                            dpi=self.fig_opt['resolution'], transparent=True)
            else:
                if format == 0 or format == 1:
                    name_fig = os.path.join(self.path_im, self.name_reach[r] +"_suitability_index.png")
                if format == 0 or format == 3:
                    name_fig = os.path.join(self.path_im, self.name_reach[r] +"_suitability_index.pdf")
                if format == 2:
                    name_fig = os.path.join(self.path_im, self.name_reach[r] +"_suitability_index.jpg")
                if os.path.isfile(name_fig):
                    os.remove(name_fig)
                fig.savefig(name_fig, bbox_extra_artists=(lgd,), bbox_inches='tight',
                            dpi=self.fig_opt['resolution'], transparent=True)
            plt.show()

    def savetxt_stathab(self):
        """
        A function to save the stathab result in .txt form
        """
        # to know if we kept the old file or we erase them
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        erase1 = self.fig_opt['erase_id']
        if erase1 == 'True':  # xml in text
            erase1 = True
        else:
            erase1 = False

        if not isinstance(self.j_all, np.ndarray):
            print('Error: The suitability index was not in the right format')
            return

        # save txt for each reach
        for r in range(0, len(self.name_reach)):
            j = np.squeeze(self.j_all[r, :, :])
            qmod = self.q_all[r]
            if self.riverint == 0:
                vclass = self.vclass_all[r]
                hclass = self.hclass_all[r]
                rclass = self.rclass_all[r]
            hmod = self.h_all[r]
            wmod = self.w_all[r]
            dummy = np.zeros((len(hmod), 1)) - 99

            # rrd file (only for temperate)
            if self.riverint == 0:
                # depth and dist Q should be added
                data = np.hstack((np.log(qmod), dummy, hmod, wmod, vclass.T, hclass.T, rclass.T))
                if not erase1:
                    namefile = os.path.join(self.path_txt, 'Stathab_' + self.name_reach[r] +
                                            time.strftime("%d_%m_%Y_at_%H_%M_%S")+'rrd.txt')
                else:
                    namefile = os.path.join(self.path_txt, 'Stathab_' + self.name_reach[r] + 'rrd.txt')
                    if os.path.isfile(namefile):
                        os.remove(namefile)
                # header
                txt_header = 'log(Q)\tempty\thmod\twmod'
                for i in range(0, len(vclass)):
                    txt_header += '\tvclass'
                for i in range(0, len(hclass)):
                    txt_header += '\thclass'
                for i in range(0, len(rclass)):
                    txt_header += '\trclass'
                txt_header += '\n'
                # unity
                txt_header += '[log(m3/sec)]\t[]\t[m]\t[m]'
                for i in range(0, len(vclass)):
                    txt_header += '\t[m3]'
                for i in range(0, len(hclass)):
                    txt_header += '\t[m2]'
                for i in range(0, len(rclass)):
                    txt_header += '\t[m2]'
                np.savetxt(namefile, data, delimiter='\t', header=txt_header)

            # rre.txt
            if not erase1:
                namefile = os.path.join(self.path_txt, 'Stathab_' + self.name_reach[r] +
                                        time.strftime("%d_%m_%Y_at_%H_%M_%S") + 'rre.txt')
            else:
                namefile = os.path.join(self.path_txt, 'Stathab_' + self.name_reach[r] + 'rre.txt')
                if os.path.isfile(namefile):
                    os.remove(namefile)
            header_txt = 'Suitability Index \n '
            for f in self.fish_chosen:
                header_txt += f + '\t'
            np.savetxt(namefile, j.T, delimiter='\t', header=header_txt)

    def find_path_hdf5_stat(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in hydro_GUI_2.py
        and in estimhab_GUI. By default,
        path_hdf5 is in the project folder in the folder 'fichier_hdf5'.
        """

        path_hdf5 = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Hdf5")
            if child is None:
                path_hdf5 = self.path_prj
            else:
                path_hdf5 = os.path.join(self.path_prj, child.text)
        else:
           print('Error: Project file is not found')

        return path_hdf5

    def test_stathab(self, path_ori):
        """
        A short function to test part of the outputs of stathab in temperate rivers against the C++ code,
        It is not used in Habby but it is practical to debug.

        :param path_ori: the path to the files from stathab based on the c++ code
        """

        # stathab.txt
        filename = os.path.join(path_ori, 'stathab.txt')
        if os.path.isfile(filename):
            with open(filename, 'rt') as f:
                data = f.read()
        else:
            print('Error: Stathab.txt was not found.\n')
            return -99
        # granulo_mean
        exp_reg1 = 'average\ssubstrate\ssize\s([\d.,]+)\s*'
        mean_sub_ori = re.findall(exp_reg1, data)
        for r in range(0, len(mean_sub_ori)):
            mean_sub_ori_fl = np.float(mean_sub_ori[r])
            if np.abs(mean_sub_ori_fl - self.granulo_mean_all[r]) < 0.0001:
                print('substrate size: ok')
            else:
                print(mean_sub_ori[r])
                print(self.granulo_mean_all[r])

        # rivrrd.txt
        filename = os.path.join(path_ori, self.name_reach[0] + 'rrd.txt')
        vol_all_orr = np.loadtxt(filename)
        q_orr = np.exp(vol_all_orr[:, 0])
        vclass = self.vclass_all[0]
        hclass = self.hclass_all[0]
        rclass = self.rclass_all[0]
        v = self.h_all[0] * self.w_all[0]

        plt.figure()
        plt.subplot(221)
        plt.title('Volume total')
        plt.plot(q_orr, 1*vol_all_orr[:, 3]*vol_all_orr[:, 2], '*')
        plt.plot(q_orr, v)
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Volume for 1m reach [m3]')
        plt.legend(('C++ Code', 'new python code'), loc='upper left')
        plt.subplot(222)
        plt.title('Surface by class for the granulometry')
        for g in range(0, len(rclass)):
            plt.plot(q_orr, vol_all_orr[:, 13+g], '*')
            plt.plot(q_orr, rclass[g], '-')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Surface by Class [m2]')
        plt.subplot(223)
        plt.title('Surface by class for the height')
        for g in range(0, len(hclass)):
            plt.plot(q_orr, vol_all_orr[:, 9 + g], '*')
            plt.plot(q_orr, hclass[g, :], '-')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Surface by Class [m2]')
        plt.subplot(224)
        plt.title('Volume by class for the velocity')
        for g in range(0, len(vclass)):
            plt.plot(q_orr, vol_all_orr[:, 4 + g], '*')
            plt.plot(q_orr, vclass[g], '-')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Volume by Class [m3]')

        # rivrre.txt
        filename = os.path.join(path_ori, self.name_reach[0] + 'rre.txt')
        j_orr = np.loadtxt(filename)
        j = np.squeeze(self.j_all[0, :, :])
        nb_spe = j_orr.shape[1]
        plt.figure()
        for e in range(0, nb_spe):
            plt.plot(q_orr, j_orr[:, e], '*', label=self.fish_chosen[e] + '(C++)')
            plt.plot(q_orr, j[e, :], '-', label=self.fish_chosen[e] + '(Python)')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('J')
        plt.title('Suitability index J - STATHAB')
        lgd = plt.legend(bbox_to_anchor=(1, 1), loc='upper right', ncol=1)
    
        plt.show()

    def test_stathab_trop_biv(self, path_ori):
        """
        A short function to test part of the outputs of the stathab tropical rivers against the R code
        in the bivariate mode. It is not used in Habby but it is practical to debug. Stathab_trop+biv should be
        executed before. For the moment only the fish SIC is tested.

        :param path_ori: the path to the output files from stathab based on the R code

        """

        # load the R output data
        filename = os.path.join(path_ori, 'SIC_ind-vh.csv')
        data_r = np.genfromtxt(filename, skip_header=1, delimiter=";")
        q_r = data_r[:, 2]
        vpu = data_r[:, 6]

        # compare result
        plt.figure()
        plt.title('Stathab - Tropical bivariate - SIC')
        plt.plot(self.q_all[0], self.j_all[0, 0, :],'-')
        plt.plot(q_r, vpu,'x')
        plt.xlabel('Q [m3/sec]')
        plt.ylabel('VPU')
        plt.legend(('Python Code', 'R Code'), loc=2)
        plt.grid('on')
        plt.show()

    def test_stathab_trop_uni(self, path_ori,by_vel=True):
        """
        A short function to test part of the outputs of the stathab tropical rivers against the R code
        in the univariate mode. It is not used in Habby but it is practical to debug. Stathab_trop_uni should be
        executed before. For the moment only the fish SIC is tested.

        :param path_ori: the path to the output files from stathab based on the R code
        :param by_vel: If True, the velcoity-based vpu is used. Otherise, it is height-based spu

        """

        # load the R output data
        if by_vel:
            filename = os.path.join(path_ori, 'SIC_ind-v.csv')
        else:
            filename = os.path.join(path_ori, 'SIC_ind-h.csv')
        data_r = np.genfromtxt(filename, skip_header=1, delimiter=";")
        q_r = data_r[:, 2]
        vpu = data_r[:, 6]

        # compare result
        plt.figure()
        if by_vel:
            plt.title('Stathab - Tropical univariate, based on velocity preference - SIC ')
            plt.ylabel('VPU')
        else:
            plt.title('Stathab - Tropical univariate, based on height preference - SIC ')
            plt.ylabel('SPU')
        plt.plot(self.q_all[0], self.j_all[0, 0, :], '-')
        plt.plot(q_r, vpu, 'x')
        plt.xlabel('Q [m3/sec]')

        plt.legend(('Python Code', 'R Code'), loc=2)
        plt.grid('on')
        plt.show()


def load_float_stathab(filename, check_neg):
    """
    A function to load float with extra checks

    :param filename: the file to load with the path
    :param check_neg: if true negative value are not allowed in the data
    :return: data if ok, -99 if failed
    """

    myfloatdata = [-99]
    still_val_err = True  # if False at the end, the file could be loaded
    if os.path.isfile(filename):
        try:
            myfloatdata = np.loadtxt(filename)
            still_val_err = False
        except ValueError:
            pass
        try:  # because some people add an header to the files in the csv
            myfloatdata = np.loadtxt(filename, skiprows=1, delimiter=";")
            still_val_err = False
        except ValueError:
            pass
        try:  # because there are csv files without header
            myfloatdata = np.loadtxt(filename, delimiter=';')
            still_val_err = False
        except ValueError:
            pass
        if still_val_err:
            print('Error: The file called ' + filename + ' could not be read.(2)\n')
            return [-99]
    else:  # when loading file, python is always case-sensitive because Windows is.
        # so let's insist on this.
        path_here = os.path.dirname(filename)
        all_file = os.listdir(path_here)
        file_found = False
        for f in range(0, len(all_file)):
            if os.path.basename(filename.lower()) == all_file[f].lower():
                file_found = True
                filename = os.path.join(path_here, all_file[f])
                try:
                    myfloatdata = np.loadtxt(filename)
                    still_val_err = False
                except ValueError:
                    pass
                try:  # because some people add an header to the files in the csv
                    myfloatdata = np.loadtxt(filename, skiprows=1, delimiter=";")
                    still_val_err = False
                except ValueError:
                    pass
                try:  # because ther are csv files without header
                    myfloatdata = np.loadtxt(filename, delimiter=';')
                    still_val_err = False
                except ValueError:
                    pass
                if still_val_err:
                    print('Error: The file called ' + filename + ' could not be read.(2)\n')
                    return [-99]
        if not file_found:
            print('Error: The file called ' + filename + ' was not found.\n')
            return [-99]

    if check_neg:
        if np.sum(np.sign(myfloatdata)) < 0:  # if there is negative value
            print('Error: Negative values found in ' + filename + '.\n')
            return [-99]
    return myfloatdata


def load_pref(filepref, path):
    """
    The function loads the different pref coeffficient contained in filepref, for the temperate river from Stathab

    :param filepref: the name of the file (usually Pref.txt)
    :param path: the path to this file
    :return: the name of the fish, a np.array with the differen coeff
    """
    filename_path = os.path.join(path, filepref)
    if os.path.isfile(filename_path):
        with open(filename_path, 'rt') as f:
            data = f.read()
    else:
        print('Error:  The file containing biological models was not found (Pref.txt).\n')
        return [-99], [-99]
    if not data:
        print('Error:  The file containing biological models could not be read (Pref.txt).\n')
        return [-99], [-99]
    # get data line by line
    data = data.split('\n')

    # read the data and pass to float
    name_fish = []
    coeff_all = []
    for l in range(0, len(data)):
        # ignore empty line
        if data[l]:
            data_l = data[l].split()
            name_fish.append(data_l[0])
            coeff_l = list(map(float, data_l[1:]))
            coeff_all.append(coeff_l)
    coeff_all = np.array(coeff_all)

    return name_fish, coeff_all


def load_pref_trop_uni(code_fish, path):
    """
    This function loads the preference files for the univariate data. The file with the univariate data should be in the
    form of xuni-h_XXX where XX is the fish code and x is whatever string. The assumption is that the filename for
    velocity is very similar to the filename for height. In more detail that the string uni-h is changed to uni-v in
    the filename. Otherwise, the file are csv file with two columns: First is velocity or height,
    the second is the preference data.

    :param code_fish: the code for the fish name in three letters (such as ASC)
    :param path: the path to files
    :return: the height data and velcoity data (h, pref) and (v,pref)
    """

    datah_all = []
    datav_all = []

    # get all possible file
    all_files = load_hdf5.get_all_filename(path,'.csv')

    # get the name of univariate height files
    filenamesh = []
    for fi in code_fish:
        for file in all_files:
            if 'uni-h_'+fi in file:
                filenamesh.append(file)

    # load the data
    for fh in filenamesh:
        # get filename with the path
        fv = fh.replace('uni-h','uni-v')
        fileh = os.path.join(path,fh)
        filev = os.path.join(path,fv)

        # load file
        if not os.path.isfile(fileh) or not os.path.isfile(filev):
            print('Warning: One preference file was not found.\n')
        else:
            try:
                datah = np.loadtxt(fileh, skiprows=1, delimiter=';')
                datav = np.loadtxt(filev, skiprows=1, delimiter=';')
                datah_all.append(datah)
                datav_all.append(datav)
            except ValueError:
                print('Warning: One preference file could not be read.\n')

    return datah_all, datav_all


def load_pref_trop_biv(code_fish, path):
    """
    This function loads the bivariate preference files for tropical rivers. The name of the file must be in the form
    of xbiv_XXX.csv where XXX is the three-letters fish code and x is whatever string.

    :param code_fish: the code for the fish name in three letters (such as ASC)
    :param path: the path to files
    :return: the bivariate preferences
    """
    data_all = []

    # get all possible files
    all_files = load_hdf5.get_all_filename(path, '.csv')

    # get the name of univariate height files
    filenames = []
    for fi in code_fish:
        for file in all_files:
            if 'biv_' + fi in file:
                filenames.append(file)

    # load the data
    for f in filenames:
        # get filename with the path
        file = os.path.join(path,f)
        if not os.path.isfile(file):
            print('Warning: One preference file was not found.\n')
        else:
            try:
                data = np.loadtxt(file, skiprows=1, delimiter=';')
                data_all.append(data)
            except ValueError:
                print('Warning: One preference file could not be read.\n')

    return data_all


def load_namereach(path, name_file_reach='listriv'):
    """
    A function to only load the reach names (useful for the GUI). The extension must be .txt or .csv

    :param path : the path to the file listriv.txt or listriv.csv
    :param name_file_reach: In case the file name is not listriv
    :return: the list of reach name
    """
    # find the reaches
    filename = os.path.join(path, name_file_reach + '.txt')
    filename2 = os.path.join(path, name_file_reach + '.csv')
    if os.path.isfile(filename):
        with open(filename, 'rt') as f:
            data = f.read()
    elif os.path.isfile(filename2):
        with open(filename2, 'rt') as f:
            data = f.read()
    else:
        print('Error:  The file containing the names of the reaches was not found (listriv).\n')
        print(filename2)
        return [-99]
    if not data:
        print('Error:  The file containing the names of the reaches could not be read (listriv.txt).\n')
        return [-99]
    # get reach name line by line
    name_reach = data.split('\n')  # in case there is a space in the names of the reaches
    # in case we have an empty line between reaches
    name_reach = [x for x in name_reach if x]

    return name_reach


def main():
    """
    used to test this module.
    """

    # test temperate stathab

    # path = 'D:\Diane_work\model_stat\input_test'
    # path_ori = 'D:\Diane_work\model_stat\stathab_t(1)'
    # #path_ori = r'D:\Diane_work\model_stat\stathab_t(1)\mob_test'
    # end_file_reach = ['deb.txt', 'qhw.txt', 'gra.txt', 'dis.txt']
    # name_file_allreach = ['bornh.txt', 'bornv.txt', 'borng.txt', 'Pref.txt']
    # path_habby = r'C:\Users\diane.von-gunten\HABBY'
    # path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    #
    # mystathab = Stathab('my_test4', path_habby)
    # mystathab.load_stathab_from_txt('listriv.txt', end_file_reach, name_file_allreach, path)
    # mystathab.create_hdf5()
    # mystathab.load_stathab_from_hdf5()
    # mystathab.stathab_calc(path_ori)
    # mystathab.path_im = path_im
    # #mystathab.savefig_stahab()
    # #mystathab.savetxt_stathab()
    # mystathab.test_stathab(path_ori)

    # test tropical stathab
    path_ori = r'D:\Diane_work\model_stat\FSTRESSandtathab\fstress_stathab_C\Stathab2_2014 04_R\Stathab2_2014 04\output'
    path = r'C:\Users\diane.von-gunten\HABBY\test_data\input_stathab2'
    path_prj = r'D:\Diane_work\dummy_folder\Projet1'
    name_prj = 'Projet1'
    path_im = r'D:\Diane_work\dummy_folder\cmd_test'
    path_bio = r'C:\Users\diane.von-gunten\HABBY\biology\stathab'
    name_file_allreach_trop = []
    end_file_reach_trop = ['deb.csv', 'qhw.csv', 'ii.csv']  # .txt or .csv
    biv= False

    mystathab = Stathab(name_prj, path_prj)
    mystathab.riverint = 2
    mystathab.load_stathab_from_txt('listriv', end_file_reach_trop, name_file_allreach_trop, path)
    mystathab.create_hdf5()
    mystathab.fish_chosen = ['SIC']

    if biv:
        mystathab.stathab_trop_biv(path_bio)
        mystathab.test_stathab_trop_biv(path_ori)
    else:
        # False-> height based spu, True-> vpu
        mystathab.stathab_trop_univ(path_bio, False)
        mystathab.test_stathab_trop_uni(path_ori, False)


if __name__ == '__main__':
    main()
