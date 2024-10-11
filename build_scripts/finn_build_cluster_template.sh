#!/bin/bash 

# Project

# Job time limit [days-hours]
#SBATCH -t 6:00:00

# Resources
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -o finn_compile_job_%j.out
#SBATCH -p normal
#SBATCH --cpus-per-task 8
#SBATCH --mem-per-cpu 16G

echo "Running the cluster/remote build script"

WORKING_DIR=<FINN_WORKDIR>

model_dir=$1
model_dir=${model_dir##*"$WORKING_DIR"}

# For FINN
module reset
module load system singularity
ml lib/gurobi/1102

ml fpga
ml xilinx/xrt/2.14
ml xilinx/vitis/22.1

# For FINN C++ Driver
ml devel/Doxygen/1.9.5-GCCcore-12.2.0
ml compiler/GCC/12.2.0
ml devel/CMake/3.24.3-GCCcore-12.2.0

mkdir -p $WORKING_DIR/SINGULARITY_CACHE
mkdir -p $WORKING_DIR/SINGULARITY_TMP
mkdir -p $WORKING_DIR/FINN_TMP

if [ -d "/dev/shm" ]; then
  echo "Copying file to ramdisk"
  cp -r $WORKING_DIR /dev/shm/temporary_finn_dir
  WORKING_DIR=/dev/shm/temporary_finn_dir
  echo "Done."
fi


<SET_ENVVARS>


cd $WORKING_DIR/finn
./run-docker.sh build_custom $1

if [ -d "/dev/shm" ]; then
    echo "Copying files back"
    # Copy back FINN_TMP files
    cp -r $WORKING_DIR/FINN_TMP <FINN_WORKDIR>/FINN_TMP

    # Copy back model files
    cp -r "$WORKING_DIR""$model_dir" <FINN_WORKDIR>"$model_dir"

fi