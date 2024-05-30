import warnings
import os
from pathlib import Path
import sys
import re
import ast
import argparse
import pickle
import numpy as np
import pandas as pd
import utils
from sklearn.preprocessing import StandardScaler
import time
from multiprocessing import Pool, set_start_method
import Constants as c
warnings.simplefilter("ignore", category=DeprecationWarning)
warnings.simplefilter("ignore", UserWarning)


# Useful paths
script_path = Path(os.path.abspath(__file__))         # This script's path
script_dir = script_path.parents[0]                   # This script's directory
event_inference_dir = script_path.parents[1]          # This script's parent directory
data_dir = os.path.join(event_inference_dir, "data")  # Output data directory

num_pools = 12
non_numerical_features = ['device', 'state', 'event', 'start_time', "remote_ip", "remote_port", "trans_protocol", "raw_protocol", 'protocol', 'hosts']
cols_feat = [feat for feat in utils.get_features() if feat not in non_numerical_features]

model_list = []
root_output = ''
dir_tsne_plots = ''
root_feature = ''
root_model = ''
root_test= ''
root_test_out = ''
#is_error is either 0 or 1
def print_usage(is_error):
    print(c.PREPRO_USAGE, file=sys.stderr) if is_error else print(c.PREPRO_USAGE)
    exit(is_error)


def main():

    global root_output, dir_tsne_plots, root_feature, root_model, root_test, root_test_out

    # Parse Arguments
    parser = argparse.ArgumentParser(usage=c.PREPRO_USAGE, add_help=False)
    parser.add_argument("-i", dest="root_feature", default="")
    parser.add_argument("-o", dest="root_pre_train", default="")
    parser.add_argument("-h", dest="help", action="store_true", default=False)
    args = parser.parse_args()

    if args.help:
        print_usage(0)

    print("Running %s..." % c.PATH)

    # Error checking command line args
    root_feature = args.root_feature
    if root_feature.endswith("/"):
        root_feature = root_feature[:-1]
    root_model = args.root_pre_train
    if root_model.endswith("/"):
        root_model = root_model[:-1]
    print(f"Root model: {root_model}")

    errors = False
    # check -i in features
    if root_feature == "":
        errors = True
        print(c.NO_FEAT_DIR, file=sys.stderr)
    elif not os.path.isdir(root_feature):
        errors = True
        print(c.INVAL % ("Features directory", root_feature, "directory"), file=sys.stderr)
    else:
        if not os.access(root_feature, os.R_OK):
            errors = True
            print(c.NO_PERM % ("features directory", root_feature, "read"), file=sys.stderr)
        if not os.access(root_feature, os.X_OK):
            errors = True
            print(c.NO_PERM % ("features directory", root_feature, "execute"), file=sys.stderr)

    # check -o out models
    if root_model == "":
        errors = True
        print(c.NO_MOD_DIR, file=sys.stderr)
    elif os.path.isdir(root_model):
        if not os.access(root_model, os.W_OK):
            errors = True
            print(c.NO_PERM % ("model directory", root_model, "write"), file=sys.stderr)
        if not os.access(root_model, os.X_OK):
            errors = True
            print(c.NO_PERM % ("model directory", root_model, "execute"), file=sys.stderr)
    else:
        os.makedirs(root_model, exist_ok=True)

    if errors:
        print_usage(1)
    #end error checking

    print(f"Input files located in: {root_feature}\nOutput files placed in: {root_model}")
    root_output = os.path.join(root_model, "output")
    os.makedirs(root_output, exist_ok=True)

    train_models()


def train_models():
    global root_feature, root_model, root_output
    """
    Scan feature folder for each device
    """
    print(f"root_feature: {root_feature}")
    print(f"root_model: {root_model}")
    print(f"root_output: {root_output}")

    lparas = []

    random_state = 422
    print("random_state:", random_state)
    for csv_file in os.listdir(root_feature):
        if csv_file.endswith('.csv'):
            print(csv_file)
            idle_data_file = os.path.join(root_feature, csv_file)
            dname = csv_file[:-4]

            lparas.append((idle_data_file, dname)) #, random_state))

    p = Pool(num_pools)
    t0 = time.time()
    list_results = p.map(eid_wrapper, lparas)
    for ret in list_results:
        if ret is None or len(ret) == 0: continue
        for res in ret:
            tmp_outfile = res[0]
            tmp_res = res[1:]
            with open(tmp_outfile, 'a+') as off:
                # off.write('random_state:',random_state)
                off.write('%s\n' % '\t'.join(map(str, tmp_res)))
                print('Agg saved to %s' % tmp_outfile)
    t1 = time.time()
    print('Time to train all models for %s devices using %s threads: %.2f' % (len(lparas),num_pools, (t1 - t0)))


def drop_features(df: pd.DataFrame, features: list) -> pd.DataFrame:
    """
    Drop given features from a pandas DataFrame object.

    :param df: input DataFrame
    :param features: list of features to drop
    :return: copy of the DataFrame, with the given features dropped
    """
    try:
        result_df = df.drop(features, axis=1)
    except KeyError as e:
        message = e.args[0]
        pattern = r"\[([^]]*)\]"
        m = re.search(pattern, message)
        if m:
            l = ast.literal_eval(f"[{m.group(1)}]")
            features_to_remove = [feat for feat in features if feat not in l]
            result_df = df.drop(features_to_remove, axis=1)
    return result_df.fillna(-1)


def eid_wrapper(a):
    return eval_individual_device(a[0], a[1]) #, a[2])


def eval_individual_device(idle_data_file, dname):
    global root_feature, root_model, root_test, root_test_out

    
    ## Directories
    # Training
    train_feature_dir = os.path.join(data_dir, "train-features")
    os.makedirs(train_feature_dir, exist_ok=True)
    train_std_dir = os.path.join(data_dir, "train-std")
    os.makedirs(train_std_dir, exist_ok=True)
    train_pca_dir = os.path.join(data_dir, "train-pca")
    os.makedirs(train_pca_dir, exist_ok=True)
    # Testing
    test_feature_dir = os.path.join(data_dir, "test-features")
    os.makedirs(test_feature_dir, exist_ok=True)
    test_std_dir = os.path.join(data_dir, "test-std") 
    os.makedirs(test_std_dir, exist_ok=True)
    test_pca_dir = os.path.join(data_dir, "test-pca")
    os.makedirs(test_pca_dir, exist_ok=True)
    # print('Test feature:',test_feature_dir)

    # train data file, std & pca files
    train_data_file = os.path.join(train_feature_dir, f"{dname}.csv")
    std_train_file = os.path.join(train_std_dir, f"{dname}.csv")
    pca_train_file = os.path.join(train_pca_dir, f"{dname}.csv")

    # test data file, std & pca files
    test_file = os.path.join(test_feature_dir, f"{dname}.csv")
    std_test_file = os.path.join(test_std_dir, f"{dname}.csv")
    pca_test_file = os.path.join(test_pca_dir, f"{dname}.csv")

    #idle_file = os.path.join(data_dir, "idle-2021-features", f"{dname}.csv")
    routines_file = os.path.join(data_dir, "routine-features", f"{dname}.csv")
    if not os.path.isfile(routines_file):
        with_routines = False
    else:
        with_routines = True
        routines_data = pd.read_csv(routines_file)

    
    # idle dirctories
    train_idle_std_dir = os.path.join(data_dir, "idle-train-std")
    os.makedirs(train_idle_std_dir, exist_ok=True)
    train_idle_pca_dir = os.path.join(data_dir, "idle-train-pca")
    os.makedirs(train_idle_pca_dir, exist_ok=True)
    test_idle_std_dir = os.path.join(data_dir, "idle-test-std")
    os.makedirs(test_idle_std_dir, exist_ok=True)
    test_idle_pca_dir = os.path.join(data_dir, "idle-test-pca")
    os.makedirs(test_idle_pca_dir, exist_ok=True)

    # idle std & pca files
    train_idle_std_file = os.path.join(train_idle_std_dir, f"{dname}.csv") 
    train_idle_pca_file = os.path.join(train_idle_pca_dir, f"{dname}.csv")
    test_idle_std_file = os.path.join(test_idle_std_dir, f"{dname}.csv")
    test_idle_pca_file = os.path.join(test_idle_pca_dir, f"{dname}.csv")

    if with_routines:
        routines_std_dir = os.path.join(data_dir, "routines-std")
        os.makedirs(routines_std_dir, exist_ok=True)
        routines_pca_dir = os.path.join(data_dir, "routines-pca")
        os.makedirs(routines_pca_dir, exist_ok=True)
        routines_std_file = os.path.join(routines_std_dir, f"{dname}.csv") 
        routines_pca_file = os.path.join(routines_pca_dir, f"{dname}.csv") 


    if not os.path.isfile(idle_data_file):
        print(f"{dname} idle do not exist")
        return

    only_idle = False
    if not os.path.isfile(train_data_file):
        print(train_data_file)
        # no labeled data file. 
        only_idle = True 
        print('Only Idle: ', dname)
    else:
        train_data = pd.read_csv(train_data_file)
        if dname == 'ikettle':
            test_data = pd.read_csv(train_data_file)
        else:
            test_data = pd.read_csv(test_file)

        # Training data
        X_feature = drop_features(train_data, non_numerical_features)
        train_length = len(X_feature)
        # Testing data
        test_data_feature = drop_features(test_data, non_numerical_features)

        
    # read idle files
    idle_data = pd.read_csv(idle_data_file, low_memory=False)
    if dname=='govee-led1' or dname=='philips-bulb':
            pass
    """else:
        idle_data = idle_data.loc[(idle_data['start_time'] > 1630688400)]
        idle_data = idle_data.loc[(idle_data['start_time'] < 1631120400)]"""
    

    # Idle train test split: 
    if np.min(idle_data['start_time']) <= 1630698400 and np.max(idle_data['start_time']) >= 1631110000:
        split_time = 1631034000
    else: 
        split_time =  np.max(idle_data['start_time']) - (np.max(idle_data['start_time']) - np.min(idle_data['start_time']))/5 
    train_idle_data = idle_data.loc[(idle_data['start_time'] < split_time)]  #  1556420400
    test_idle_data = idle_data.loc[(idle_data['start_time'] >= split_time)] 


    train_idle_feature = train_idle_data.drop(non_numerical_features, axis=1).fillna(-1)
    test_idle_feature = test_idle_data.drop(non_numerical_features, axis=1).fillna(-1)

    # unctrl_data = pd.read_csv(unctrl_file)
    
    
    # test_length = test_data.shape[0]
    
    num_data_points = len(idle_data)
    if num_data_points < 1:
        print('  Not enough data points for %s' % dname)
        return
    # print('\t#Total data points: %d ' % num_data_points)
    
    
    if with_routines:
        routines_feature = routines_data.drop(non_numerical_features, axis=1).fillna(-1)

    
    print('train test idle:', dname, len(train_idle_data), len(test_idle_data))
    if len(train_idle_data)==0 or len(test_idle_data)==0:
        print('Not enough idle data points for:', dname, len(train_idle_data), len(test_idle_data))
        return
    train_idle_len = len(train_idle_feature)

    if only_idle:
        X_feature =  np.array(train_idle_feature)
    else:
        X_feature = pd.concat([X_feature, train_idle_feature])
        X_feature = np.array(X_feature)

    if len(X_feature) <=0:
        print(len(X_feature),dname)
        print('No data')
        exit(1)
    
    # ss
    ss = StandardScaler()
    X_all_std = ss.fit_transform(X_feature)
    if not only_idle:
        test_data_std = ss.transform(test_data_feature)
    test_idle_std = ss.transform(test_idle_feature)
    
    if with_routines:
        routines_std = ss.transform(routines_feature)
        #routines_pca = pca.transform(routines_std)

    '''
    Save ss and pca
    '''
    models_path = os.path.join(event_inference_dir, "model", "SS_PCA")
    os.makedirs(models_path, exist_ok=True)
    saved_dictionary = dict({
        "ss": ss
        #"pca": pca
    })
    model_file_path = os.path.join(models_path, f"{dname}.pkl")
    pickle.dump(saved_dictionary, open(model_file_path, "wb"))

    
    if only_idle:
        X_idle_std = X_all_std
        # X_idle_pca = X_all_pca
    else:
        X_std = X_all_std[:train_length,:] 
        X_idle_std = X_all_std[train_length:,:] 
        # X_pca = X_all_pca[:train_length,:] 
        # X_idle_pca = X_all_pca[train_length:,:]  # .iloc

        X_feature_std = pd.DataFrame(X_std, columns=cols_feat)
        X_feature_std['device'] = train_data.device
        X_feature_std['state'] = train_data.state
        X_feature_std['event'] = train_data.event
        X_feature_std['start_time'] = train_data.start_time
        X_feature_std['protocol'] = train_data.protocol
        X_feature_std['hosts'] = train_data.hosts


        test_data_std = pd.DataFrame(test_data_std, columns=cols_feat)
        test_data_std['device'] = test_data.device
        test_data_std['state'] = test_data.state
        test_data_std['event'] = test_data.event
        test_data_std['start_time'] = test_data.start_time
        test_data_std['protocol'] = test_data.protocol
        test_data_std['hosts'] = test_data.hosts



        X_feature_std.to_csv(std_train_file, index=False)
        test_data_std.to_csv(std_test_file, index=False)



    X_idle_std = pd.DataFrame(X_idle_std, columns=cols_feat)
    X_idle_std['device'] = np.array(train_idle_data.device)
    X_idle_std['state'] = np.array(train_idle_data.state)
    X_idle_std['event'] = np.array(train_idle_data.event)
    X_idle_std['start_time'] = np.array(train_idle_data.start_time)
    X_idle_std['protocol'] = np.array(train_idle_data.protocol)
    X_idle_std['hosts'] = np.array(train_idle_data.hosts)

    

    test_idle_std = pd.DataFrame(test_idle_std, columns=cols_feat)
    test_idle_std['device'] = np.array(test_idle_data.device)
    test_idle_std['state'] = np.array(test_idle_data.state)
    test_idle_std['event'] = np.array(test_idle_data.event)
    test_idle_std['start_time'] = np.array(test_idle_data.start_time)
    test_idle_std['protocol'] = np.array(test_idle_data.protocol)
    test_idle_std['hosts'] = np.array(test_idle_data.hosts)
    # if dname =='google-home-mini':
    #     print('Length check, train idle: ', len(X_idle_std), len(train_idle_data))
    #     print('Length check, test idle: ', len(test_idle_std), len(test_idle_data))
    if with_routines:
        routines_std = pd.DataFrame(routines_std, columns=cols_feat)
        routines_std['device'] = routines_data.device
        routines_std['state'] = routines_data.state
        routines_std['event'] = routines_data.event
        routines_std['start_time'] = routines_data.start_time
        routines_std['protocol'] = routines_data.protocol
        routines_std['hosts'] = routines_data.hosts

        routines_std.to_csv(routines_std_file, index=False)


    
    X_idle_std.to_csv(train_idle_std_file, index=False)
    test_idle_std.to_csv(test_idle_std_file, index=False)
    # unctrl_std.to_csv(unctrl_std_file, index=False)

    """

    X_idle_pca = pd.DataFrame(X_idle_pca)
    X_idle_pca['device'] = np.array(train_idle_data.device)
    X_idle_pca['state'] = np.array(train_idle_data.state)
    X_idle_pca['event'] = np.array(train_idle_data.event)
    X_idle_pca['start_time'] = np.array(train_idle_data.start_time)
    X_idle_pca['protocol'] = np.array(train_idle_data.protocol)
    X_idle_pca['hosts'] = np.array(train_idle_data.hosts)

    

    test_idle_pca = pd.DataFrame(test_idle_pca)
    test_idle_pca['device'] = np.array(test_idle_data.device)
    test_idle_pca['state'] = np.array(test_idle_data.state)
    test_idle_pca['event'] = np.array(test_idle_data.event)
    test_idle_pca['start_time'] = np.array(test_idle_data.start_time)
    test_idle_pca['protocol'] = np.array(test_idle_data.protocol)
    test_idle_pca['hosts'] = np.array(test_idle_data.hosts)

    if with_routines:
        routines_pca = pd.DataFrame(routines_pca)
        routines_pca['device'] = routines_data.device
        routines_pca['state'] = routines_data.state
        routines_pca['event'] = routines_data.event
        routines_pca['start_time'] = routines_data.start_time
        routines_pca['protocol'] = routines_data.protocol
        routines_pca['hosts'] = routines_data.hosts

        routines_pca.to_csv(routines_pca_file, index=False)
    # unctrl_pca = pd.DataFrame(unctrl_pca)
    # unctrl_pca['device'] = unctrl_data.device
    # unctrl_pca['state'] = unctrl_data.state
    # unctrl_pca['event'] = unctrl_data.event
    # unctrl_pca['start_time'] = unctrl_data.start_time
    # unctrl_pca['protocol'] = unctrl_data.protocol
    # unctrl_pca['hosts'] = unctrl_data.hosts

    
    X_idle_pca.to_csv(train_idle_pca_file, index=False)
    test_idle_pca.to_csv(test_idle_pca_file, index=False)

    # unctrl_pca.to_csv(unctrl_pca_file, index=False)
    """



if __name__ == '__main__':
    set_start_method('fork')
    main()
    num_pools = 12
