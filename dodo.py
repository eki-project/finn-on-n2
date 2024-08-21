# Python do-it file for managing FINN, the Finn-cpp-driver and running synthesis jobs
# Work in progress!

# TODO: Default config files for multiple environments, make them usable for example via something like
# doit setenv cluster

import subprocess
import sys
import os
import shutil
from typing import Any, Generator, Optional
from doit.exceptions import BaseFail
import toml
from doit.action import CmdAction
from doit.reporter import ConsoleReporter
from doit.task import Task
import shlex
import hashlib

class CustomReporter(ConsoleReporter):
    def __init__(self, outstream, options):
        super().__init__(outstream, options)
    
    def execute_task(self, task: Task):
        if task.actions and (task.name[0] != '_'):
            if task.name != "init":
                self.write(f"[ running: {task.name} ]\n")
            else:
                self.write(f"[ finn-on-n2 setup ]\nCloning FINN and setting up scripts now.\nFor further information consult the README.\n\n")

    def add_success(self, task):
        self.write(f"[ success: {task.name} ]\n")
    
    def add_failure(self, task, fail: BaseFail):
        self.write(f"[ failure in task {task.name}: {fail.get_name()} ]\n")
        

#* Helper functions
def execute_in_finn(command_list: list[str]):
    subprocess.run(command_list, cwd="finn")


def execute_here(command_list: list[str]):
    subprocess.run(command_list)


def read_from_file(fname: str, binary: bool = False) -> Optional[str]:
    try:
        with open(fname, 'r' if not binary else 'rb') as f:
            return f.read()
    except:
        return None


def get_config_hash() -> str:
    if not os.path.isfile("config.toml"):
        print("Cannot create hash of non existing configuration!")
        sys.exit() 

    h = hashlib.sha256()
    h.update(read_from_file("config.toml", binary=True))
    return h.hexdigest()


def write_config_hash(hash: str):
    with open(".info", 'w+') as f:
        f.write(hash)


def check_config_outdated() -> bool:
    if not os.path.isfile(".info"):
        return True
    conf = read_from_file("config.toml")
    if conf is None:
        print("ERROR: No config file found!")
        sys.exit()
    
    old_hash = read_from_file(".info")
    new_hash = get_config_hash()
    return old_hash != new_hash


def check_params(params: list[str]):
    if len(params) > 1:
        print("Received more than argument, please only supply one!")
        sys.exit()
    if len(params) == 0:
        print("Please supply the required argument for this function!")
        sys.exit()




#* Import configuration
config = None
with open("config.toml", "r") as f:
    config = toml.loads(f.read())
if config is None:
    print("Failed to read config file! Check for syntax errors!")
    sys.exit()


#* DOIT Configuration
DOIT_CONFIG = {
    "action_string_formatting": "new", 
    "default_tasks": ["init"],
    "reporter": CustomReporter
}


#* TASK Configuration
environment = config["general"]["used_environment"]
dev_mode = config["general"]["dev_mode"]
driver_required_commands = config["environment"][environment]["driver_compiler_prefix_commands"]
job_exec_prefix = config["environment"][environment]["job_execution"]

finn_build_script = config["environment"][environment]["finn_build_script"]
finn_build_script_template = config["environment"][environment]["finn_build_script_template"]
cppdriver_run_script = config["environment"][environment]["cppdriver_run_script"]
pythondriver_run_script = config["environment"][environment]["pythondriver_run_script"]

finn_repos = config["finn"]["repositories"]
finn_default_repo_name = config["finn"]["default_repository"]
finn_default_repo = finn_repos[finn_default_repo_name]
finn_default_branch = config["finn"]["default_branch"]
if "default_commit_hash" in config["finn"].keys():
    finn_default_commit = config["finn"]["default_commit_hash"]
else:
    finn_default_commit = ""
finn_build_template = config["finn"]["build_template"]

config_envvars = config["build"]["envvars"]

# The folder which _contains_ finn, FINN_TMP, SINGULARITY_CACHE, etc.
os.environ["FINN_WORKDIR"] = os.path.abspath(os.getcwd())

# The path to the GHA or Path, which builds the singularity/apptainer image
if environment == "cluster":
    print("Cluster environment selected: Using Singularity instead of Docker!")
    os.environ["FINN_SINGULARITY"] = config["general"]["singularity_image"]


def check_singularity():
    """Return whether singularity is mentioned in the run_docker script"""
    if not os.path.isfile(os.path.join("finn", "run-docker.sh")):
        print("Setup not configured correctly. finn is either not installed or finn/run-docker.sh is specifically missing! Run doit once to clone FINN.")
        #sys.exit()
        return True # TODO: Fix more permanently
    with open(os.path.join("finn", "run-docker.sh"), 'r') as f:
        text = f.read()
        return ("singularity" in text) or ("SINGULARITY" in text)


if (environment == "cluster" or ("FINN_SINGULARITY" in os.environ.keys() and os.environ["FINN_SINGULARITY"] != "")) and not check_singularity():
    print("WARNING: You have selected the cluster environment but your run-docker.sh file does not mention singularity. If the job failes with \"docker: Command not found\" remember to patch the singularity PR into FINN before executing!")

#* Function for updating build scripts based on a configuration file
def instantiate_buildscripts():
    # Read template file
    text = ""
    if not os.path.isfile(finn_build_script_template):
        print("The template file for the FINN build shell script could not be found!")
        sys.exit()

    with open(finn_build_script_template, 'r') as f:
        text = f.read()
    
    # Insert variables
    text = text.replace("<FINN_WORKDIR>", os.environ["FINN_WORKDIR"])
    vars = ""
    for envvar_name, envvar_value in config_envvars.items():
        vars += f"export {envvar_name}=\"{envvar_value}\"\n"
    text = text.replace("<SET_ENVVARS>", vars)

    # Check for toolchain path
    if "VIVADO_PATH" not in config_envvars.keys() or ("VIVADO_PATH" in config_envvars.keys() and config_envvars["VIVADO_PATH"] == ""):
        print("WARNING: VIVADO_PATH not set and not provided in config.toml. This needs to be set to ensure working toolchains. Either set the path in config.toml or supply it otherwise to the container!") 
    if "VITIS_PATH" not in config_envvars.keys() or ("VITIS_PATH" in config_envvars.keys() and config_envvars["VITIS_PATH"] == ""):
        print("WARNING: VITIS_PATH not set and not provided in config.toml. This needs to be set to ensure working toolchains. Either set the path in config.toml or supply it otherwise to the container!") 
    if "HLS_PATH" not in config_envvars.keys() or ("HLS_PATH" in config_envvars.keys() and config_envvars["HLS_PATH"] == ""):
        print("WARNING: HLS_PATH not set and not provided in config.toml. This needs to be set to ensure working toolchains. Either set the path in config.toml or supply it otherwise to the container!") 
    if "VIVADO_PATH" in config_envvars.keys() and "FINN_XILINX_PATH" in config_envvars.keys() and not config_envvars["VIVADO_PATH"].startswith(config_envvars["FINN_XILINX_PATH"]):
        print("WARNING: The paths or versions of FINN_XILINX_PATH and VIVADO_PATH don't match. This will cause failure when using the toolchains. Fix this in config.toml!")
    if "VITIS_PATH" in config_envvars.keys() and "FINN_XILINX_PATH" in config_envvars.keys() and not config_envvars["VITIS_PATH"].startswith(config_envvars["FINN_XILINX_PATH"]):
        print("WARNING: The paths or versions of FINN_XILINX_PATH and VITIS_PATH don't match. This will cause failure when using the toolchains. Fix this in config.toml!")
    if "HLS_PATH" in config_envvars.keys() and "FINN_XILINX_PATH" in config_envvars.keys() and not config_envvars["HLS_PATH"].startswith(config_envvars["FINN_XILINX_PATH"]):
        print("WARNING: The paths or versions of FINN_XILINX_PATH and HLS_PATH don't match. This will cause failure when using the toolchains. Fix this in config.toml!")
    # TODO: Make checks for versions as well

    # Write back out
    with open(finn_build_script, 'w+') as f:
        f.write(text)


#* Update scripts if a change in the config was detected
if check_config_outdated():
    print("Detected outdated configuration. Re-instantiating build scripts now.")
    instantiate_buildscripts()
    new_hash = get_config_hash()
    write_config_hash(new_hash)



# ******** TASKS ******** #

#* Update finn-on-n2
def task_update():
    def update():
        subprocess.run("git stash push -q;git pull;git stash pop -q", shell=True)
    return {
        "doc": " | Updates finn-on-n2. Local changes (for example to configurations) are preserved",
        "actions": [
            update
        ]
    }


#* Switch to a template configuration
def task_config():
    def use_config_template(names: list[str]):
        if len(names) > 1:
            print("More than one configuration name provided. Please only pass a single configuration name")
            sys.exit()
        if len(names) == 0:
            print("Please pass a configuration name (names are the toml filenames in configurations/ without the suffix)")
            sys.exit()
        
        fname = names[0]
        available_configs = [fn.replace(".toml", "") for fn in os.listdir("configurations")]
        if fname not in available_configs:
            print("Could not find configuration under configurations/" + fname + ".toml")
            sys.exit()
        
        subprocess.run(shlex.split(f"cp configurations/{fname}.toml ./config.toml"))

    return {
        "doc": " | Usage: doit config <configname>. Sets the current config to configurations/<configname>.toml",
        "actions": [
           use_config_template,
           instantiate_buildscripts
        ],
        "pos_arg": "names"
    }


# * Setup
def task_init():
    # Only download the driver and its dependencies as well, if the dev mode is active, to save time for normal users
    if dev_mode:
        print("Currently, building the C++ driver in dev mode is unsupported. Please set dev mode to false in the config.toml file!\nExiting.")
        sys.exit()

    return {
        "basename": "init",
        "doc": "| Setup. Clones FINN and instantitates script templates.",
        "task_dep": ["clonefinn", "setenvvars"],
        "pos_arg": "params",
        "actions": []
    }


#* Update build scripts manually
def task_setenvvars():
    return {
        "doc": "| Update the build scripts according to your config",
        "verbosity": 2,
        "actions": [
            instantiate_buildscripts
        ]
    }


# * Clone FINN
def task_clonefinn():
    def renameIfEki():
        if os.path.isdir("finn-internal"):
            os.rename("finn-internal", "finn")

    def checkout_if_commit_given(): 
        if finn_default_commit != "":
            execute_in_finn(shlex.split(f"git checkout {finn_default_commit}")) 

    return {
        "doc": "| Clone into the config-given repo, branch and optionally commit ",
        "actions": [
            (execute_here, [shlex.split(f"git clone {finn_default_repo}")]),
            renameIfEki,
            (execute_in_finn, [shlex.split(f"git checkout {finn_default_branch}")]),
            checkout_if_commit_given,
            (execute_in_finn, [shlex.split(f"git submodule init")]),
            (execute_in_finn, [shlex.split(f"git submodule update")]),
            
        ],
    }


#### * FOR FINN PROJECT CREATION * ####
ONNXFilePath = str
ProjectName = str


def onnx_name_to_project_name(name: ONNXFilePath) -> ProjectName:
    return os.path.basename(name).replace(".onnx", "")


def create_project_dir(name: ProjectName):
    if not os.path.isdir(name):
        os.mkdir(name)


def copy_onnx_file_to_project(name: ONNXFilePath):
    if not os.path.isfile(name):
        print(f"Cannot find ONNX file at {name}. Please specify a valid ONNX file path!")
        sys.exit()
    project_name = onnx_name_to_project_name(name)
    target = os.path.join(".", project_name, project_name + ".onnx")
    if not os.path.isfile(target):
        subprocess.run(shlex.split(f"cp {name} {target}"))


def create_finn_build_script(name: ProjectName):
    build_path = os.path.join(".", name, "build.py")
    if not os.path.isfile(build_path):
        buildscript = read_from_file(finn_build_template)
        if buildscript is None:
            print(f"Couldn't find build script template at {finn_build_template}. Please correct your config.toml!")
            sys.exit()
        with open(build_path, 'w+') as f:
            f.write(buildscript.replace("<ONNX_INPUT_NAME>", name + ".onnx"))


# * Make a new FINN project
def task_create():
    def create_project(params: list[str]):
        check_params(params)
        onnx_name = params[0]
        project_name = onnx_name_to_project_name(onnx_name)
        create_project_dir(project_name)
        copy_onnx_file_to_project(onnx_name)
        create_finn_build_script(project_name)

    return {
        "doc": "| Creates a project based on the given file, automatically using the filename as the project name",
        "actions": [
            create_project
        ],
        "pos_arg": "params",
        "verbosity": 2,
    }


# * Delete log and FINN_TMP files
def task_cleanup():
    return {
        "doc": "| Delete log files and FINN_TMP files. Be absolutely sure you know what you are doing",
        "actions": [
            "rm *.out",
            "rm -r FINN_TMP"
        ]
    }


#* List all projects
def task_projects():
    def ls_projects():
        exclusion_list = [".mypy_cache", "build_scripts", "configurations", "pre-builds", "run_scripts"]
        dirs = []
        for name in os.listdir("."):
            if (os.path.isdir(name)) and (name not in exclusion_list) and ("build.py" in os.listdir(name)):
                dirs.append(name)
        
        plist = "\n".join([f"\t{n}" for n in dirs])
        print(f"Found {len(dirs)} project folders:")
        print(plist)
    
    return {
        "doc": "| List all projects in this directory",
        "actions": [
            ls_projects
        ],
        "verbosity": 2
    }


# * Run FINN on a project
def task_execute():
    def run_synth_for_onnx_name(params: list[str]):
        if "finn" not in os.listdir("."):
            print("Error: Missing finn directory. Run \"doit\" first to set everything up!")
            sys.exit()
        check_params(params)
        name: ONNXFilePath = params[0]
        if not os.path.isdir(name):
            print("Error: Project directory " + name + " doesn't exist!")
            sys.exit()

        # TODO: This is a workaround. As soon as custom argument passes are possible, deprecate the use of env variables
        os.environ["BUILD_FLOW_RESUME_STEP"] = ""
        subprocess.run([job_exec_prefix, finn_build_script, os.path.abspath(name)])

    return {
        "doc": "| Execute the given project",
        "pos_arg": "params",
        "actions": [
            run_synth_for_onnx_name
        ],
        "verbosity": 2,
    }


# * Resume FINN Flow from a previous step
# TODO: Rework this
def task_resume():
    def run_synth_for_onnx_name_from_step(name):
        if "finn" not in os.listdir("."):
            print("Error: Missing finn directory. Run \"doit\" first to set everything up!")
            sys.exit()
        pdir = os.path.join(".", name[0])
        step = name[1]
        if not os.path.isdir(pdir):
            print("Error: Project directory " + pdir + " doesnt exist!")
            sys.exit()
        
        # TODO: This is a workaround. As soon as custom argument passes are possible, deprecate the use of env variables
        os.environ["BUILD_FLOW_RESUME_STEP"] = step
        subprocess.run([job_exec_prefix, finn_build_script, os.path.abspath(pdir)])

    return {
        "doc": "| Resume a FINN flow. Usage: doit resume <project-name> <step-name>. Step has to have been reached before",
        "pos_arg": "name",
        "actions": [
            (run_synth_for_onnx_name_from_step,),
        ],
        "verbosity": 2,
    }


def task_edit():
    def edit(names):
        if len(names) > 2:
            print("Cannot edit multiple or none projects. Provide a single project name and/or an editor!")
            sys.exit()

        editors = ["vim", "vi", "nano", "gedit", "code"]

        if (len(names) > 1):
            if shutil.which(names[1]) is None:
                print(f"{names[1]} is not available. Chosing another editor")
            else:
                subprocess.run(shlex.split(f"{names[1]} {names[0]}/build.py"))
                return True
        
        for editor in editors:
            if shutil.which(editor) is not None: 
                subprocess.run(shlex.split(f"{editor} {names[0]}/build.py"))
                return True
        
        print(f"None of these editors is available for editing: {editors}!")
        return False
    
    return {
        "doc": "| Open the build.py file of the given project in an available editor. Usage: doit edit <project_dir> <editor>",
        "actions": [
            edit
        ],
        "pos_arg": "names"
    }


# TODO: Only test for now, change that
# * Run python driver test
def task_pythondriver():
    def run_python_driver(params: list[str]):
        check_params(params)
        name = params[0]
        if not os.path.isdir(name):
            print("No project directory found under the name " + name)
        output_dirs = [x for x in os.listdir(name) if x.startswith("out_")]
        if len(output_dirs) == 0:
            print("Tried to find valid output directoy in project directory. Make sure all output directories are prefixed with \"out_\", and contain the file deploy/driver/<...>.xclbin!")
            sys.exit()
        driver_dir = os.path.join(os.path.abspath(name), output_dirs[0], "deploy", "driver")
        subprocess.run([job_exec_prefix, pythondriver_run_script, driver_dir])

    return {
        "doc": "| Execute the python driver with testdata",
        "pos_arg": "params",
        "actions": [(run_python_driver,)],
        "verbosity": 2,
    }
