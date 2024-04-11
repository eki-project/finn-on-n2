#!/bin/bash 

echo "Running the test script"

WORKING_DIR=<FINN_WORKDIR>

mkdir -p $WORKING_DIR/SINGULARITY_CACHE
mkdir -p $WORKING_DIR/SINGULARITY_TMP
mkdir -p $WORKING_DIR/FINN_TMP

<SET_ENVVARS>

cd $WORKING_DIR/finn
./run-docker.sh quicktest