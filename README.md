# finn on noctua2
__IMPORANT__: _Please make sure that you know the contents of the configuration file. The data from the configuration file is used for paths and commands and will be executed. Read the config file beforehand to avoid unwanted code execution!_
# Usage
* This requires the updated run-docker.sh script with Singularity support: https://github.com/Xilinx/finn/pull/868
* Remember to specify your own project in the sbatch parameters for cluster usage
* You need to have Vitis / Vivado activated in your environment

Run 

```
doit
```

to set up the environment. Everything will be contained in this git repository directory.

To run a FINN flow on a given ONNX file, do

```
doit finn myFile.onnx
```

(The file can be anywhere on your filesystem and will be copied into the project directory)

If you want to run a file again, you can now do

```
doit finnp myFile
```

which will run FINN on the project directory that was created for you when first running `doit finn`.


For a complete usage manual refer to the N2 documentation.

If something does not work as expected, please open an issue, or write directly to `bjarne.wintermann@uni-paderborn.de`

# Default File Structure
This is the default file structure after a finn and driver were installed and an example ONNX file was compiled and executed on FPGA:
```
dodo.py
build_template.py
finn_build_single_job.sh
finn
 |--- ...
finn-cpp-driver
 |--- ...
myproject
 |--- myproject.onnx
 |--- build.py
 |--- build_results
       |--- ...
       |--- deploy
             |--- bitfile
                   |--- finn-accel.xclbin
             |--- driver
                   |--- driver.py
                   |--- finn (compiled executable)
                   |--- write_to_fpga.sh
                   |--- config.json
                   |--- FinnDatatypesHeader.h
```

## To do
- [ ] Collect common functions in one module