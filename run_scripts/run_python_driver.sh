#!/bin/bash
#SBATCH -t 0:07:00
#SBATCH -p fpga
#SBATCH --gres=fpga:u280:3
#SBATCH -o python_driver_run%j.out
#SBATCH --constraint=xilinx_u280_xrt2.14

module reset
ml fpga &> /dev/null
ml xilinx/xrt/2.14 &> /dev/null
# ml lang/Python/3.10.4-GCCcore-11.3.0-bare &> /dev/null
ml devel/Boost/1.81.0-GCC-12.2.0
ml compiler/GCC/12.2.0

xbutil examine -d 0000:a1:00.1
xbutil reset -d 0000:a1:00.1
sleep 2s

echo "STARTING DRIVER"
cd "$1"
python3 driver.py --exec_mode throughput_test --bitfile ../bitfile/finn-accel.xclbin --batchsize 10000
cat nw_metrics.txt
