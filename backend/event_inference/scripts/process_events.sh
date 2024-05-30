#!/bin/bash

# Run the BehavIoT pipeline scripts for idle traffic:
# Decoding

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

echo "event 0. Hostname-IP mapping"
python3 $PIPELINE_DIR/s1_decode_dns_tls.py $INPUT_DIR/activity_dns.txt > $LOGS_DIR/event/0-dns-mapping-activity.log 2> $LOGS_DIR/event/log.error

echo "event 1. Run decoding"
python3 $PIPELINE_DIR/s1_decode_activity.py $INPUT_DIR/train.txt $DATA_DIR/train-decoded/ $NPROCS > $LOGS_DIR/event/1--1decode-train.log 2>> $LOGS_DIR/event/log.error
python3 $PIPELINE_DIR/s1_decode_activity.py $INPUT_DIR/test.txt $DATA_DIR/test-decoded/ $NPROCS > $LOGS_DIR/event/1-2-decode-test.log 2>> $LOGS_DIR/event/log.error

echo "event 2. Feature extraction on decoded traffic"
python3 $PIPELINE_DIR/s2_get_features.py $DATA_DIR/train-decoded/ $DATA_DIR/train-features/ > $LOGS_DIR/event/2-2-features-train.log 2>> $LOGS_DIR/event/log.error
python3 $PIPELINE_DIR/s2_get_features.py $DATA_DIR/test-decoded/ $DATA_DIR/test-features/ > $LOGS_DIR/event/2-3-features-test.log 2>> $LOGS_DIR/event/log.error

echo "event 3. Periodic traffic extraction"
python3 $PERIOD_EXTRACTION_DIR/periodicity_inference.py > $LOGS_DIR/event/3-1-periodicity-inference.log 2>> $LOGS_DIR/event/log.error
python3 $PERIOD_EXTRACTION_DIR/fingerprint_generation.py > $LOGS_DIR/event/3-2-fingerprint-generation.log 2>> $LOGS_DIR/event/log.error

echo "event 4. Preprocessing"
python3 $PIPELINE_DIR/s4_preprocess_feature_new.py -i $DATA_DIR/idle-features/ -o $DATA_DIR/idle/ > $LOGS_DIR/event/4-preprocess-idle.log 2>> $LOGS_DIR/event/log.error

echo "event 5. Train filter model on idle traffic"
python3 $PIPELINE_DIR/s5_periodic_filter.py -i $DATA_DIR/idle-train-std/ -o $MODEL_DIR/filter > $LOGS_DIR/event/5-1-train-idle.log 2>> $LOGS_DIR/event/log.error
python3 $PIPELINE_DIR/s5_filter_by_periodic.py -i train -o $MODEL_DIR/filter > $LOGS_DIR/event/5-2-filter-train.log 2>> $LOGS_DIR/event/log.error
python3 $PIPELINE_DIR/s5_filter_by_periodic.py -i test -o $MODEL_DIR/filter > $LOGS_DIR/event/5-3-filter-test.log 2>> $LOGS_DIR/event/log.error

echo "event 6. Train fingerprint and binary model"
python3 $PIPELINE_DIR/s6_activity_fingerprint.py -i $DATA_DIR/train-filtered-std/ -o $MODEL_DIR/fingerprint/ > $LOGS_DIR/event/6-1-train-fingerprint.log 2>> $LOGS_DIR/event/log.error
python3 $PIPELINE_DIR/s6_binary_model_whostname.py -i $DATA_DIR/train-filtered-std/ -o $MODEL_DIR/binary-whostname > $LOGS_DIR/event/6-2-train-binary-whostname.log 2>> $LOGS_DIR/event/log.error

#echo "event 7. Deviation score"
#python3 $PIPELINE_DIR/periodic_deviation_score.py -i $DATA_DIR/idle-2021-train-std/ -o $MODEL_DIR/time_score_newT_train_idle > $LOGS_DIR/event/7-1-deviation-score-train.log 2> $LOGS_DIR/event/7-1-deviation-score-train.error
#python3 $PIPELINE_DIR/periodic_deviation_score.py -i $DATA_DIR/idle-2021-test-std/ -o $MODEL_DIR/time_score_newT_test_idle > $LOGS_DIR/event/7-2-deviation-score-test.log 2> $LOGS_DIR/event/7-2-deviation-score-test.error
#python3 $PIPELINE_DIR/periodic_score_analysis.py $MODEL_DIR/time_score_newT_train_idle $MODEL_DIR/time_score_newT_test_idle > $LOGS_DIR/event/7-3-score-analysis.log 2> $LOGS_DIR/event/7-3-score-analysis.error
