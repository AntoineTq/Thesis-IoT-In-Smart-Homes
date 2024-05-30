import os
from pathlib import Path
import sys
from datetime import datetime
import utils
import collections
import numpy as np
import math
import matplotlib 
import matplotlib.pyplot as plt
matplotlib.use("Agg")
import matplotlib.ticker as mticker
from collections import Counter
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

# Useful paths
script_path = Path(os.path.abspath(__file__))                # This script's path
script_dir = script_path.parents[0]                          # This script's directory
event_inference_dir = script_path.parents[1]                 # This script's parent directory
cdf_dir = os.path.join(event_inference_dir, "cdf")


def plotting_cdf(score_list, name):

    count_dic = Counter(score_list)
    plt.figure()
    length_list = len(score_list)
    norm_factor = max(score_list)
    requestOrdered = dict(collections.OrderedDict(sorted(count_dic.items(), key=lambda t: t[0])))
    x = np.array(list(requestOrdered.keys())) #/norm_factor    # score 
    y = np.array(list(requestOrdered.values()))/length_list   # num of traces
    
    y = np.cumsum(y)
    plt.plot(x, y, 'r') # , 'o'

    plt.ticklabel_format(style='plain')
    # plt.ticklabel_format(style='sci', scilimits=(0,0), axis='y')
    if 'train' not in name:
        plt.ylim((0.99980,1.00001))
    # plt.grid()
    plt.xlabel('score')
    plt.ylabel('periodic traffic')
    # plt.xscale("log")
    # plt.title('%s'%name)
    plt.tight_layout()
    dic = os.path.join(cdf_dir, f"score_{name}.png")
    plt.savefig(dic)
    dic = os.path.join(cdf_dir, "cdf", f"score_{name}.pdf")
    plt.savefig(dic)


    return 0


def plotting_cdf_list(score_list_list, name, file_list):
    plt.figure()
    color_list = ['r', 'b', 'y', 'g', 'c', 'k']
    for i in range(len(score_list_list)):
        score_list = score_list_list[i]
        cur_file = file_list[i]
        if 'train' in cur_file:
            cur_file = 'train'
        else:
            cur_file = 'test'
        count_dic = Counter(score_list)
        # print(score_list)
        # print(count_dic)
        
        length_list = len(score_list)
        norm_factor = max(score_list)
        # print(count_dic[0])
        count_dic[0.0000001] = count_dic[0]
        count_dic[0] = 1
        requestOrdered = dict(collections.OrderedDict(sorted(count_dic.items(), key=lambda t: t[0])))
        
        x = np.array(list(requestOrdered.keys()))#/norm_factor    # score 
        y = np.array(list(requestOrdered.values()))/length_list   # num of traces
        
        y = np.cumsum(y)
        plt.plot(x, y, label='%s' % cur_file.split('_')[-1], color=color_list[i]) # , 'o'
    
    plt.tight_layout()
    plt.subplots_adjust(left=0.16)
    plt.rcParams.update({'font.size': 15, 'xtick.labelsize': 10, 'ytick.labelsize': 10})
    # plt.rc('font', size=15)  
    plt.rc('axes', labelsize=15)
    plt.rcParams.update({'legend.loc': 'lower right'})
    # plt.rc('axes', titlesize=15)
    # plt.ylim((0.99975,1.00001))
    # plt.vlines(x=1.65, ymin=0.99975, ymax=1, color='k', linestyle='--')
    plt.ylim((0,1.00001))
    plt.vlines(x=1.65, ymin=0, ymax=1, color='k', linestyle='--')
    # plt.vlines(x=0.68, ymin=0, ymax=1, color='k', linestyle='--')
    # plt.vlines(x=0.63, ymin=0, ymax=1, color='k', linestyle='--')
    plt.legend()
    plt.xlabel('Periodic-event deviation metric', fontsize=15)
    plt.ylabel('CDF', fontsize=15)
    
    
    # this is an inset axes over the main axes
    a = plt.axes([.5, .4, .4, .4])
    for i in range(len(score_list_list)):
        score_list = score_list_list[i]
        cur_file = file_list[i]
        if 'train' in cur_file:
            cur_file = 'train'
        else:
            cur_file = 'test'
        count_dic = Counter(score_list)
        # print(score_list)
        # print(count_dic)
        
        length_list = len(score_list)
        norm_factor = max(score_list)
        requestOrdered = dict(collections.OrderedDict(sorted(count_dic.items(), key=lambda t: t[0])))
        x = np.array(list(requestOrdered.keys()))#/norm_factor    # score 
        y = np.array(list(requestOrdered.values()))/length_list   # num of traces
        
        y = np.cumsum(y)
        plt.plot(x, y, label='%s' % cur_file.split('_')[-1], color=color_list[i]) # , 'o'
    plt.rcParams.update({'font.size': 15, 'xtick.labelsize': 10, 'ytick.labelsize': 10})
    plt.ylim((0.99975,1.00001))
    plt.vlines(x=1.65, ymin=0.99975, ymax=1, color='k', linestyle='--')
    plt.title('Zoomed CDF')
    plt.xlabel('', fontsize=15)
    plt.ylabel('', fontsize=15)

    os.makedirs(cdf_dir, exist_ok=True)
    dic = os.path.join(cdf_dir, f"score_{name}_double.pdf")
    plt.savefig(dic)
    dic = os.path.join(cdf_dir, f"score_{name}_double.png")
    plt.savefig(dic) # , bbox_inches="tight"
    return 0



base_dir = os.path.join(event_inference_dir, "model")

if len(sys.argv) < 2: #  and len(sys.argv) != 4
    print('Not enough argv')
    exit(1)

in_dir = sys.argv[1]
in_dir2 = sys.argv[2]
file_list = [in_dir, in_dir2]
mac_dic = utils.read_mac_address()
deviation_score_list_list = []
for in_dir in file_list:
    root_log = os.path.join(in_dir, "time_logs")
    output_dir = os.path.join(in_dir, "alarms")
    os.makedirs(output_dir, exist_ok=True)

    list1 = []
    date_alarm_dic = {}
    periodic_tuple_dic = {}
    deviation_score_list = []
    largest_score = []
    periodic_group = 0
    for log_file in os.listdir(root_log):

        dname = log_file.split('.')[0]

        print(dname)
        periodic_tuple = []
        tmp_host_set = set()
        try:
            fingerprint_file = os.path.join(event_inference_dir, "period_extraction", "freq_period", "fingerprints", f"{dname}.txt")
            with open(fingerprint_file, 'r') as file:
                for line in file:
                    tmp = line.split()
                    # print(tmp)
                    try:
                        tmp_proto = tmp[0]
                        tmp_host = tmp[1]
                        tmp_period = tmp[2]
                    except:
                        print(tmp)
                        exit(1)
                    if tmp_host == '#' or tmp_host  == ' ':
                        tmp_host = ''
                    if tmp_proto == 'SDDP' or tmp_proto == "SSDP" or tmp_proto == 'MDNS':
                        continue
                    if tmp_host in mac_dic or tmp_host == 'multicast' or ':' in tmp_host or '192' in tmp_host:
                        continue
                    periodic_tuple.append((tmp_host, tmp_proto, tmp_period))
                    tmp_host_set.add((tmp_host,tmp_proto))
                    periodic_group += 1

        except:
            print( 'unable to read fingerprint file %s' % dname)
            # return
            exit(1)
        periodic_tuple_dic[dname] = tmp_host_set

        f = open(os.path.join(root_log, log_file))

        cur_host = 0
        cur_protocol = 0

        for line in f:
            if len(line) <= 1 or line.startswith(' ') : # or line.startswith('1') 
                continue
            if line.startswith('------'):
                cur_host = line.split('------')[1].split()[0]
                cur_protocol = line.split('------')[1].split()[1]
                cur_period = line.split('------')[1].split()[2]

                continue
                
            label = line.split(':')[0]
            if label.startswith('Normal'):
                deviation_score_list.append(0)
                continue

            try:
                # deviation_score_list.append(math.log(float(line.split(':')[1].split(',')[0].strip())))
                deviation_score_list.append(math.log(float(line.split(':')[1].split(',')[0].strip())+1))
            except:
                print(line)
                exit(1)
            if math.log(float(line.split(':')[1].split(',')[0].strip())+1) < 0:
                print(line)
                exit(1)

    print(periodic_group)
    print('_'.join(in_dir.split('/')[1].split('_')[2:]))
    # plotting_cdf(deviation_score_list, '%s' % '_'.join(in_dir.split('/')[1].split('_')[2:]))
    deviation_score_list_list.append(deviation_score_list)
plotting_cdf_list(deviation_score_list_list, 'score_idle_train_test_threshold_zoomed', file_list)
exit(1)
# print(date_alarm_dic)
