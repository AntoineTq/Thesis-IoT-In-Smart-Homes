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

rm -rf "$DATA_DIR/"
rm -rf "$MODEL_DIR/"
rm -rf "$PERIOD_EXTRACTION_DIR/freq_period/idle/"

echo $SCRIPT_DIR
echo "idle 0. Hostname-IP mapping"
python3 $PIPELINE_DIR/s1_decode_dns_tls.py $INPUT_DIR/idle_dns.txt > $LOGS_DIR/idle/0-dns-mapping-idle.log 2> $LOGS_DIR/idle/log.error

echo "idle 1. Run decoding"
python3 $PIPELINE_DIR/s1_decode_idle.py $INPUT_DIR/idle_inputs.txt $DATA_DIR/idle-decoded/ $NPROCS > $LOGS_DIR/idle/1-decoding.log 2>> $LOGS_DIR/idle/log.error

echo "idle 2. Feature extraction on decoded traffic"
python3 $PIPELINE_DIR/s2_get_features.py $DATA_DIR/idle-decoded/ $DATA_DIR/idle-features/ $NPROCS > $LOGS_DIR/idle/2-features.log 2>> $LOGS_DIR/idle/log.error

echo "idle 3. Periodic traffic extraction"
python3 $PERIOD_EXTRACTION_DIR/periodicity_inference.py > $LOGS_DIR/idle/3-1-period-extraction.log 2>> $LOGS_DIR/idle/log.error
python3 $PERIOD_EXTRACTION_DIR/fingerprint_generation.py > $LOGS_DIR/idle/3-2-fingerprint-generation.log 2>> $LOGS_DIR/idle/log.error

echo "idle 4. Preprocessing"
python3 $PIPELINE_DIR/s4_preprocess_feature_new.py -i $DATA_DIR/idle-features/ -o $DATA_DIR/idle/ > $LOGS_DIR/idle/4-preprocess-idle.log 2>> $LOGS_DIR/idle/log.error

echo "idle 5. Train filter model on idle traffic"
python3 $PIPELINE_DIR/s5_periodic_filter.py -i $DATA_DIR/idle-train-std/ -o $MODEL_DIR/filter > $LOGS_DIR/idle/5-train-idle.log 2>> $LOGS_DIR/idle/log.error
