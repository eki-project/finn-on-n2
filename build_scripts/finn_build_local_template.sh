#!/bin/bash 

echo "Running the local build script"

WORKING_DIR=<FINN_WORKDIR>

mkdir -p $WORKING_DIR/SINGULARITY_CACHE
mkdir -p $WORKING_DIR/SINGULARITY_TMP
mkdir -p $WORKING_DIR/FINN_TMP

<SET_ENVVARS>

cd $WORKING_DIR/finn
./run-docker.sh build_custom $1 $2