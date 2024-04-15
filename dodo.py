# Python do-it file for managing FINN, the Finn-cpp-driver and running synthesis jobs
# Work in progress!

# TODO: Default config files for multiple environments, make them usable for example via something like
# doit setenv cluster

import subprocess
import sys
import os
import shutil
import toml
from doit.action import CmdAction

#* Import configuration
config = None
with open("config.toml", "r") as f:
    config = toml.loads(f.read())
if config is None:
    print("Failed to read config file! Check for syntax errors!")
    sys.exit()


#* DOIT Configuration
DOIT_CONFIG = {"action_string_formatting": "new", "default_tasks": ["finn-doit-setup"]}


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
finn_build_template = config["finn"]["build_template"]

config_envvars = config["build"]["envvars"]

# The folder which _contains_ finn, FINN_TMP, SINGULARITY_CACHE, etc.
os.environ["FINN_WORKDIR"] = os.path.abspath(os.getcwd())

# The path to the GHA or Path, which builds the singularity/apptainer image
if environment == "cluster":
    print("Cluster environment selected: Using Singularity instead of Docker!")
    os.environ["FINN_SINGULARITY"] = config["general"]["singularity_image"]

# Insert a name to use the given task as a subtask
def decorate_with_name(task):
    name = task.__name__.replace("task_", "")
    t = task()
    t.update({"name": "subtask-" + name})
    return t


# * SETUP
def task_finn_doit_setup():
    # Only download the driver and its dependencies as well, if the dev mode is active, to save time for normal users
    if dev_mode:
        print("Currently, building the C++ driver in dev mode is unsupported. Please set dev mode to false in the config.toml file!\nExiting.")
        sys.exit()
    
    yield {
        "basename": "finn-doit-setup",
        "doc": "Retrieve FINN and create build shell scripts. If you update the env vars in config.toml it suffices to call \"setenvvars\" again to create new build scritps",
        "task_dep": ["getfinn", "setenvvars"],
        "actions": []
    }


# * WRITE ENVIRONMENT VARIABLES INTO BUILD SCRIPT AND MAKE A USABLE COPY OF THAT SCRIPT (INSTANTIATED)
def task_setenvvars():
    def edit_template():
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

        print()
        
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
        
    def delete_old_script():
        subprocess.run(["rm", "-f", "finn_build_single_job.sh"], stdout=subprocess.PIPE)

    return {
        "doc": "Deletes the current build jobscripts and creates new ones, using the environment variables in the configuration. If needed, you can use the variable $WORKING_DIR to refer to the directory the dodo file resides in, or just pass absolute paths.",
        "verbosity": 2,
        "actions": [
            (delete_old_script,),
            (edit_template,)
        ]
    }


# * CLONE FINN
def task_getfinn():
    def clone(source):
        # TODO: Solve this using doit's choice system
        if source not in finn_repos.keys():
            print("Invalid source repo! Valid choices are: " + str(finn_repos.keys()))
            sys.exit()

        if os.path.isdir("finn"):
            return

        subprocess.run(["git", "clone", finn_repos[source]], stdout=subprocess.PIPE)
        

    def renameIfEki():
        if os.path.isdir("finn-internal"):
            os.rename("finn-internal", "finn")

    def initSubmodules():
        subprocess.run(["git", "submodule", "init"], cwd="finn", stdout=subprocess.PIPE)
        subprocess.run(["git", "submodule", "update"], cwd="finn", stdout=subprocess.PIPE)

    def checkoutBranch(branch):
        subprocess.run(["git", "checkout", branch], cwd="finn")

    return {
        "doc": "Clone the specified repository and switch to a given branch. Should only be executed once. Defaults are set in config.toml",
        "params": [
            {
                "name": "branch",
                "long": "branch",
                "short": "b",
                "type": str,
                "default": finn_default_branch,
            },
            {
                "name": "source",
                "long": "source",
                "short": "s",
                "type": str,
                "default": finn_default_repo_name,
            },
        ],
        "actions": [
            (clone,),
            (renameIfEki,),
            (checkoutBranch,),
            (initSubmodules,)
        ],
    }


# * FORCE GIT PULL ON FINN ITSELF
def task_ffupdate():
    return {
        "doc": "FINN forced-update. Overwrite all changes locally and pull from origin",
        "actions": [CmdAction("git pull;git reset --hard;git pull", cwd="finn")],
        "verbosity": 2,
    }


#### FOR FINN PROJECT CREATION ####
ProjectDirectoryPath = str
ProjectName = str

def get_project_dir_name(name: list[str]) -> tuple[ProjectDirectoryPath, ProjectName]:
    #! This expects a LIST (as pos_arg from doit)
    pname = os.path.basename(name[0]).replace(".onnx", "")
    pdir = os.path.join(".", pname)
    return pdir, pname


def create_project_dir_if_needed(name: list[str]) -> None:
    pdir, pname = get_project_dir_name(name)
    if not os.path.isdir(pdir):
        os.mkdir(pdir)
        print("Created project folder under the path " + pdir)


def copy_onnx_file(name: list[str]) -> None:
    """Copy the targeted onnx file into the project directory. If there already is one, it doesn't get replaced."""
    pdir, pname = get_project_dir_name(name)
    if not os.path.isfile(os.path.join(pdir, pname + ".onnx")):
        subprocess.run(["cp", name[0], pdir])


def inst_build_template(name: list[str]) -> None:
    """Copy and instantiate the build template into the given project directory"""
    pdir, pname = get_project_dir_name(name)
    basename = pname + ".onnx"
    if not os.path.isfile(os.path.join(pdir, "build.py")):
        buildscript = None
        with open(finn_build_template, 'r') as f:
            buildscript = f.read()
        with open(os.path.join(pdir, "build.py"), 'w+') as f:
            f.write(buildscript.replace("<ONNX_INPUT_NAME>", basename))
        print("build.py templated! Please edit the build.py to your liking.")


# * MAKE FINN PROJECT
def task_create():
    return {
        "doc": "Create a finn project folder. Only executes the different steps if required",
        "actions": [
            (create_project_dir_if_needed,),
            (copy_onnx_file,),
            (inst_build_template,),
        ],
        "pos_arg": "name",
        "verbosity": 2,
    }


# * DELETE OLD FINN FILES
def task_cleanup():
    return {
        "doc": "Clean up files created during a FINN run. This includes FINN project files and directories (!!) as well as logs (only in the cluster env).",
        "actions": [
            CmdAction(["rm", "*.out"]),
            CmdAction(["rm", "-r", "FINN_TMP/*"])
        ]
    }


# * RUN FINN FLOW ON TARGET PROJECT
def task_execute():
    def run_synth_for_onnx_name(name):
        pdir = os.path.join(".", name[0])
        if not os.path.isdir(pdir):
            print("Error: Project directory " + pdir + " doesnt exist!")
            sys.exit()

        # TODO: This is a workaround. As soon as custom argument passes are possible, deprecate the use of env variables
        os.environ["BUILD_FLOW_RESUME_STEP"] = ""
        subprocess.run([job_exec_prefix, finn_build_script, os.path.abspath(pdir)])

    return {
        "doc": "Execute a finn compilation and synthesis based on a project name. Requires the project directory to exist first already.",
        "pos_arg": "name",
        "actions": [
            (run_synth_for_onnx_name,),
        ],
        "verbosity": 2,
    }


# * RESUME FORM PREVIOUS STEP
def task_resume():
    def run_synth_for_onnx_name_from_step(name):
        pdir = os.path.join(".", name[0])
        step = name[1]
        if not os.path.isdir(pdir):
            print("Error: Project directory " + pdir + " doesnt exist!")
            sys.exit()
        
        # TODO: This is a workaround. As soon as custom argument passes are possible, deprecate the use of env variables
        os.environ["BUILD_FLOW_RESUME_STEP"] = step
        subprocess.run([job_exec_prefix, finn_build_script, os.path.abspath(pdir)])

    return {
        "doc": "Execute a finn compilation and synthesis based on a project name. Requires the project directory to exist first already. (doit resume <project-name> <step-name>)",
        "pos_arg": "name",
        "actions": [
            (run_synth_for_onnx_name_from_step,),
        ],
        "verbosity": 2,
    }


# TODO: Only test for now, change that
# * RUN PYTHON DRIVER IF EXISTING
def task_pythondriver():
    def run_python_driver(arg):
        pdir, pname = get_project_dir_name(arg)
        if not os.path.isdir(pdir):
            print("No project directory found under the name " + pname + " and path " + os.path.abspath(pdir))
        output_dirs = [x for x in os.listdir(pdir) if x.startswith("out_")]
        if len(output_dirs) == 0:
            print(
                "Project with input name "
                + pname
                + " has no output folder! (Searched in "
                + os.path.abspath(pdir)
                + ")"
            )
        driver_dir = os.path.join(os.path.abspath(pdir), output_dirs[0], "deploy", "driver")
        subprocess.run([job_exec_prefix, pythondriver_run_script, driver_dir])

    return {
        "doc": "Execute the python driver of a project, print the results on screen",
        "pos_arg": "arg",
        "actions": [(run_python_driver,)],
        "verbosity": 2,
    }