#!/bin/bash
#SBATCH -t 0:07:00
#SBATCH -p fpga
#SBATCH --gres=fpga:u280:3
#SBATCH -o cpp-finn_out_%j.out
#SBATCH --constraint=xilinx_u280_xrt2.14

ml fpga &> /dev/null
ml xilinx/xrt/2.14 &> /dev/null
ml lang/Python/3.10.4-GCCcore-11.3.0-bare &> /dev/null
ml devel/Boost/1.81.0-GCC-12.2.0
ml compiler/GCC/12.2.0

xbutil examine -d 0
xbutil reset -d 0000:a1:00.1
sleep 2s

echo "STARTING DRIVER"
cd "$1"
./finn --mode test --input cppdconfig.json --configpath cppdconfig.json
