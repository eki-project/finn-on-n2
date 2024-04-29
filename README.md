# finn-on-n2
__IMPORANT__: _Please make sure that you know the contents of the configuration file. The data from the configuration file is used for paths and commands and will be executed. Read the config file beforehand to avoid unwanted code execution!_

This git repository is supposed to help making the setup of FINN easier by automating tasks using the _doit_ package.

# Usage
* __If you want to run this on a cluster and thus have to use singularity this requires the updated run-docker.sh script with Singularity support: https://github.com/Xilinx/finn/pull/868__
  * If you start a job on a cluster and expect it to use singularity, and you get the message "docker" not found, that is likely because the singularity support was not patched in!
* Remember to specify your own project in the sbatch parameters for cluster usage
* You need to have Vitis / Vivado activated in your environment
* Note that _currently_ the default configuration points to a commit before v0.10 was released for stability reasons. You can still use it for v0.10 of course, but expect that you will have to update some details

## TL;DR
```
git clone git@github.com:eki-project/finn-on-n2.git   # Clone this repository
cd finn-on-n2                                         # Jump into repo
doit config local                                     # Load a config (can also be skipped)
vim config.toml                                       # Edit the configuration to fit your needs
doit create ~/models/my_model.onnx                    # Create a project based on a given onnx file (gets copied)
doit edit my_model                                    # Optional: Edit the build script of that project
doit execute my_model                                 # Start the FINN flow
```

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



### Soon to be supported
If you later on want to restart the flow but only want to execute for example everything after ```step_hls_codegen``` again, simply use

```
doit resume mynet step_hls_codegen
```

(_For this to work, the FINN_TMP files may NOT be deleted, and the step has to have been reached before!_)


If something does not work as expected, please open an issue, or write directly to `bjarne.wintermann@uni-paderborn.de`
