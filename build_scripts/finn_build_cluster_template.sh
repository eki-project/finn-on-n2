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

WORKING_DIR=<FINN_WORKDIR>

# For FINN
module reset
module load system singularity

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


<SET_ENVVARS>



cd $WORKING_DIR/finn
./run-docker.sh build_custom $1
