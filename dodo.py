# Python do-it file for managing FINN, the Finn-cpp-driver and running synthesis jobs
# Work in progress!

import subprocess
import sys
import os
import json
import platform
import shutil
import copy
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
# TODO: Implement possibility to specify board and part numbers here

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

finndriver_default_repo = config["finn_driver"]["default_repository"]
finndriver_default_branch = config["finn_driver"]["default_branch"]
finndriver_default_compilemode = config["finn_driver"]["default_compile_mode"]

config_envvars = config["build"]["envvars"]

# The folder which _contains_ finn, FINN_TMP, SINGULARITY_CACHE, etc.
os.environ["FINN_WORKDIR"] = os.path.abspath(os.getcwd())

# The path to the GHA, which builds the singularity/apptainer image
os.environ["FINN_SINGULARITY"] = config["general"]["finn_singularity_gha"]

# Insert a name to use the given task as a subtask
def decorate_with_name(task):
    name = task.__name__.replace("task_", "")
    t = task()
    t.update({"name": "subtask-" + name})
    return t


# * SETUP
def task_finn_doit_setup():
    td = ["getfinn", "setenvvars"]
    # Only download the driver and its dependencies as well, if the dev mode is active, to save time for normal users
    if dev_mode:
        import sys
        print("Building the C++ driver from this script is currently unsupported. Please set the dev mode flag to false for the time being.\nExiting..")
        sys.exit()
        td += ["getfinndriver", "dmkbuildfolder"]
    
    yield {
        "basename": "finn-doit-setup",
        "doc": "Does a first time setup install finn, finn-cpp-driver and creating an envinfo.json, containing user data",
        "task_dep": td,
        "actions": []
    }

# * WRITE ENVIRONMENT VARIABLES INTO BUILD SCRIPT
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

        # Write back out
        with open(finn_build_script, 'w+') as f:
            f.write(text)
        
    def delete_old_script():
        subprocess.run(["rm", "-f", "finn_build_single_job.sh"], stdout=subprocess.PIPE)

    return {
        "doc": "Deletes the current build jobscript and creates a new one, using the environment variables in the configuration. If needed, you can use the variable $WORKING_DIR to refer to the directory the dodo file resides in, or just pass absolute paths.",
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
        "doc": "Clone the specified repository and switch to a given branch. Should only be executed once",
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
        "doc": "FINN forced-update. Overwrite all changes locally and pull form origin",
        "actions": [CmdAction("git pull;git reset --hard;git pull", cwd="finn")],
        "verbosity": 2,
    }


#### FOR FINN PROJECT CREATION ####
def get_project_dir_name(name):
    #! This expects a LIST (as pos_arg from doit)
    pname = os.path.basename(name[0]).replace(".onnx", "")
    pdir = os.path.join(".", pname)
    return pdir, pname


def purge_old_builds_func(builddir: str, purge_older_builds: bool):
    if purge_older_builds:
        # TODO
        pass

def create_project_dir_if_needed(name):
    pdir, pname = get_project_dir_name(name)
    if not os.path.isdir(pdir):
        os.mkdir(pdir)
        print("Created project folder under the path " + pdir)
    purge_old_builds_func(pdir, True)


def copy_onnx_file(name):
    pdir, pname = get_project_dir_name(name)
    if not os.path.isfile(os.path.join(pdir, pname + ".onnx")):
        subprocess.run(["cp", name[0], pdir])


def inst_build_template(name):
    pdir, pname = get_project_dir_name(name)
    basename = pname + ".onnx"
    if not os.path.isfile(os.path.join(pdir, "build.py")):
        buildscript = None
        with open(finn_build_template, 'r') as f:
            buildscript = f.read()
        with open(os.path.join(pdir, "build.py"), 'w+') as f:
            f.write(buildscript.replace("<ONNX_INPUT_NAME>", basename))
        print("build.py templated! Please edit the build.py to your liking.")


# * MAKE FINN PROJECT FOLDER
def task_fmkproject():
    return {
        "doc": "Create a finn project folder. Only executes the different steps, depending on whether they are needed",
        "actions": [
            (create_project_dir_if_needed,),
            (copy_onnx_file,),
            (inst_build_template,),
        ],
        "pos_arg": "name",
        "verbosity": 2,
    }


def task_finn():
    def run_synth_for_onnx_name(name):
        pname = os.path.basename(name[0]).replace(".onnx", "")
        basename = pname + ".onnx"
        pdir = os.path.join(".", pname)
        subprocess.run([job_exec_prefix, finn_build_script, os.path.abspath(pdir)])

    return {
        "doc": "Execute a finn compilation and synthesis, based on a given input file. Also creates a project if not already existing.",
        "pos_arg": "name",
        "actions": [
            (create_project_dir_if_needed,),
            (copy_onnx_file,),
            (inst_build_template,),
            (run_synth_for_onnx_name,),
        ],
        "verbosity": 2,
    }

def task_cleanup():
    return {
        "doc": "Clean up files created during a FINN run. This includes FINN project files and directories (!!) as well as logs (only in the cluster env).",
        "actions": [
            CmdAction(["rm", "*.out"]),
            CmdAction(["rm", "-r", "FINN_TMP/*"])
        ]

    }


def task_finnp():
    def run_synth_for_onnx_name(name):
        pdir = os.path.join(".", name[0])
        if not os.path.isdir(pdir):
            print("Error: Project directory " + pdir + " doesnt exist!")
            sys.exit()
        subprocess.run([job_exec_prefix, finn_build_script, os.path.abspath(pdir)])

    return {
        "doc": "Execute a finn compilation and synthesis based on a project name. Requires the project directory to exist first already.",
        "pos_arg": "name",
        "actions": [
            (run_synth_for_onnx_name,),
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


# * MAKE BUILD FOLDER FOR FINN COMPILER
def task_dmkbuildfolder():
    def remake_build_folder():
        bdir = os.path.join("finn-cpp-driver", "build")
        if os.path.isdir(bdir):
            shutil.rmtree(bdir) 
        os.mkdir(bdir)

    return {
        "actions": [(remake_build_folder,)],
        "doc": "Delete and remake the finn-cpp-driver/build folder. Does NOT call cmake for config!",
    }


# * CLONE FINN C++ DRIVER
def task_getfinndriver():
    def clone(branch):
        if os.path.isdir("finn-cpp-driver"):
            return

        subprocess.run(["git", "clone", finndriver_default_repo])
        subprocess.run(["git", "checkout", branch], cwd="finn-cpp-driver")
        subprocess.run(["git", "submodule", "init"], cwd="finn-cpp-driver")
        subprocess.run(["git", "submodule", "update"], cwd="finn-cpp-driver")
        subprocess.run(["bash", "buildDependencies.sh"], cwd="finn-cpp-driver")

    return {
        "doc": "Clone the finn-cpp-driver git repository and run the setup script",
        "params": [
            {
                "name": "branch",
                "long": "branch",
                "short": "b",
                "type": str,
                "default": finndriver_default_branch,
            }
        ],
        "actions": [(clone,)],
        "targets": ["finn-cpp-driver/buildDependencies.sh"],
    }


# * FORCE GIT PULL ON FINN DRIVER
def task_dfupdate():
    return {
        "doc": "Driver forced-update. Overwrite all changes locally and pull form origin",
        "actions": [CmdAction("git pull;git reset --hard;git pull", cwd="finn-cpp-driver")],
        "verbosity": 2,
    }


# * EXECUTE FINNBOOST BUILD DEPENDENCIES SCRIPT
def task_dbuilddeps():
    return {
        "doc": "Execute the buildDependencies script to build FinnBoost for the driver. Needs to be done once before compiling for the first time. [This task is never executed automatically]",
        "actions": [
            CmdAction(
                "./buildDependencies.sh",
                cwd="finn-cpp-driver",
            )
        ],
    }


# * COMPILE FINN DRIVER
# TODO: take the name of the project as pos_arg, so that the config.json and Finn.h header can be read directly from the project directory
def task_dcompile():
    return {
        "params": [
            {
                "name": "mode",
                "long": "mode",
                "short": "m",
                "type": str,
                "default": finndriver_default_compilemode,
            }
        ],
        "doc": "Compile the FINN C++ driver in the given mode",
        "targets": ["finn-cpp-driver/build/src/finn"],
        "actions": [
            CmdAction("cmake -DCMAKE_BUILD_TYPE={mode} ..", cwd="finn-cpp-driver/build"),
            CmdAction("cmake --build . --target finn", cwd="finn-cpp-driver/build"),
        ],
        "task_dep": ["dmkbuildfolder"],
        "verbosity": 2,
    }


def task_cppdriver():
    def run_cpp_driver(mode, name):
        outdirs = [x for x in os.listdir(get_project_dir_name(name)) if x.startswith("out")]
        if len(outdirs) == 0:
            print("No output folder available to run driver from. Please finish a FINN compilation first!")
            sys.exit()
        if mode == "test":
            # TODO: Currently if only testing the input parameter has to be filled with an existing file. Fix this
            print("Running driver now!")
            driver_dir = os.path.join(get_project_dir_name(name), outdirs[0], "driver")
            subprocess.run([job_exec_prefix, run_cpp_driver, driver_dir])
            print("Finished running driver!")
        else:
            print("NOT IMPLEMENTED")
            sys.exit()

    return {
        "params": [
            {
                "name": "mode",
                "long": "mode",
                "short": "m",
                "type": str,
                "default": "test",
            }
        ],
        "pos_arg": "name",
        "doc": 'Run the driver of the finished compiled FINN project of the given name. This requires that the results of the compilation are found in a directory starting with "out", which has to contain the bitfile in bitfile/ and the finn executable and the config json in driver/. If multiple dirs with out are given, the first sorted is used',
        "actions": [(run_cpp_driver,)],
        "verbosity": 2,
    }
