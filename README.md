# finn-on-n2
__IMPORANT__: _Please make sure that you know the contents of the configuration file. The data from the configuration file is used for paths and commands and will be executed. Read the config file beforehand to avoid unwanted code execution!_

This git repository is supposed to help making the setup of FINN easier by automating tasks using the _doit_ package.

# Usage
* __If you want to run this on a cluster and thus have to use singularity this requires the updated run-docker.sh script with Singularity support: https://github.com/Xilinx/finn/pull/868__
* Remember to specify your own project in the sbatch parameters for cluster usage
* You need to have Vitis / Vivado activated in your environment

## Installation
* Clone this repository
* Look into the .toml configuration file. Set the values you need and save. Important lines are:
  * ```used_environment```: Set this to an environment defined below, depending on your needs
  * ```singularity_image```: Set this to your path / GHA where the singularity or docker image can be found (only used if on cluster)
  * ```default_repository``` / ```default_branch```: From where to clone FINN
  * ```(VIVADO/VITIS/HLS)_PATH```: From where to source the toolchains. Point them to the year/version directory (e.g. Vivado/2022.1)
  * ```FINN_XILINX_(VERSION)```: This needs to be set _aswell_. Match the tool agnostic part of the path from VIVADO, VITIS, HLS paths
* Run ```doit```. This will clone FINN, set environment variables and instantiate build scripts. If you ever change the environment vars in the config, run ```doit setenvvars``` to update the scripts.

## Usage
If you have an ONNX file ready to use (say for example ~/Documents/mynet.onnx), simply do

```
doit create ~/Documents/mynet.onnx
```

this has to be done only once. Afterwards you will find a project directory in this repo named after the file and with a build script instantiated.

To run the FINN flow simply run

```
doit execute mynet
```

If you later on want to restart the flow but only want to execute for example everything after ```step_hls_codegen``` again, simply use

```
doit resume mynet step_hls_codegen
```

(_For this to work, the FINN_TMP files may NOT be deleted, and the step has to have been reached before!_)


If something does not work as expected, please open an issue, or write directly to `bjarne.wintermann@uni-paderborn.de`
