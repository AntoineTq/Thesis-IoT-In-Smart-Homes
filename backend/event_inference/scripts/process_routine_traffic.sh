#!/bin/bash

# Antoine Tacq
# Run the BehavIoT pipeline scripts for routine traffic:

# Constants
NPROCS=$(nproc) # Number of processors
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )  # This script's path
# Useful directories
EVENT_INFERENCE_DIR=$SCRIPT_DIR/..
PIPELINE_DIR=$EVENT_INFERENCE_DIR/pipeline
INPUT_DIR=$EVENT_INFERENCE_DIR/inputs
DATA_DIR=$EVENT_INFERENCE_DIR/data
LOGS_DIR=$EVENT_INFERENCE_DIR/logs
PERIOD_EXTRACTION_DIR=$EVENT_INFERENCE_DIR/period_extraction
MODEL_DIR=$EVENT_INFERENCE_DIR/model

rm -rf "$DATA_DIR/routine-decoded/"
rm -rf "$DATA_DIR/routine-features/"
rm -rf "$DATA_DIR/routines-std/"
rm -rf "$DATA_DIR/routines-pca/"
rm -rf "$DATA_DIR/routines-filtered-std/"
rm -rf "$DATA_DIR/routines-filtered-std-time/"

echo "routine 0. Hostname-IP mapping"
python3 $PIPELINE_DIR/s1_decode_dns_tls.py $INPUT_DIR/routine_dns.txt > $LOGS_DIR/routine/0-routine-decode-dns.log 2> $LOGS_DIR/routine/log.error

echo "routine 1. Run decoding"
python3 $PIPELINE_DIR/s1_decode_activity.py $INPUT_DIR/routine-dataset.txt $DATA_DIR/routine-decoded/ > $LOGS_DIR/routine/1-routine-decode-activity.log 2>> $LOGS_DIR/routine/log.error

echo "routine 2. Feature extraction on decoded traffic"
python3 $PIPELINE_DIR/s2_get_features.py $DATA_DIR/routine-decoded/ $DATA_DIR/routine-features/ > $LOGS_DIR/routine/2-features-routine.log 2>> $LOGS_DIR/routine/log.error

echo "routine 3. Periodic traffic extraction"
python3 $PERIOD_EXTRACTION_DIR/periodicity_inference.py > $LOGS_DIR/routine/3-1-periodicity-inference.log 2>> $LOGS_DIR/routine/log.error
python3 $PERIOD_EXTRACTION_DIR/fingerprint_generation.py > $LOGS_DIR/routine/3-2-fingerprint-generation.log 2>> $LOGS_DIR/routine/log.error


echo "routine 4. preprocess"
python3 $PIPELINE_DIR/s4_preprocess_feature_new.py -i $DATA_DIR/idle-features/ -o $DATA_DIR/idle/ > $LOGS_DIR/routine/4-preprocess.log 2>> $LOGS_DIR/routine/log.error

echo "routine 5. periodic event inference and filtering"
python3 $PIPELINE_DIR/s5_periodic_time_filter.py -i $DATA_DIR/routines-std/ -o $MODEL_DIR/time_filter/ > $LOGS_DIR/routine/5-1-periodic-filter-routines.log 2>> $LOGS_DIR/routine/log.error
python3 $PIPELINE_DIR/s5_filter_by_periodic_after_time.py -i routines -o $MODEL_DIR/filter > $LOGS_DIR/routine/5-2-filter-routines.log 2>> $LOGS_DIR/routine/log.error

echo "routine 6. User event inference"
python3 $PIPELINE_DIR/s6_binary_predict_whostname.py -i $DATA_DIR/routines-filtered-std/ -o $MODEL_DIR/binary-whostname > $LOGS_DIR/routine/6-predict-routines-binary-whostname.log 2>> $LOGS_DIR/routine/log.error

