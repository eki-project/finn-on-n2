import finn.builder.build_dataflow as build
import finn.builder.build_dataflow_config as build_cfg
import os
import shutil

# This is templated and will be replaced when building
model_file = "<ONNX_INPUT_NAME>"

rtlsim_output_dir = "output_ipstitch_ooc_rtlsim"

# Delete previous run results if exist
if os.path.exists(rtlsim_output_dir):
    shutil.rmtree(rtlsim_output_dir)
    print("Previous run results deleted!")

import time
cfg_stitched_ip = build.DataflowBuildConfig(
    steps = [
        "step_qonnx_to_finn",
        "step_tidy_up",
        "step_streamline",
        "step_convert_to_hls",
        "step_create_dataflow_partition",
        "step_target_fps_parallelization",
        "step_apply_folding_config",
        "step_generate_estimate_reports",
        "step_hls_codegen",
        "step_hls_ipgen",
        "step_set_fifo_depths",
        "step_create_stitched_ip",
        "step_measure_rtlsim_performance",
        "step_out_of_context_synthesis",
        "step_synthesize_bitfile",
        "step_make_cpp_driver",
        "step_make_pynq_driver",
        "step_deployment_package",
    ],
    output_dir          = "out_dir",
    vitis_platform      = "xilinx_u280_gen3x16_xdma_1_202211_1",
    board               = "U280",
    mvau_wwidth_max     = 80,
    target_fps          = 1000000,
    synth_clk_period_ns = 10.0,
    force_rtl_conv_inp_gen = True,
    # enable_build_pdb_debug = False,
    auto_fifo_depths = True,
    rtlsim_use_vivado_comps = False,
    split_large_fifos = True,
    shell_flow_type = build_cfg.ShellFlowType.VITIS_ALVEO,
    #fpga_part           = "xc7z020clg400-1",
    generate_outputs=[
        build_cfg.DataflowOutputType.STITCHED_IP,
        build_cfg.DataflowOutputType.RTLSIM_PERFORMANCE,
        build_cfg.DataflowOutputType.OOC_SYNTH,
        build_cfg.DataflowOutputType.BITFILE,
        build_cfg.DataflowOutputType.PYNQ_DRIVER,
        build_cfg.DataflowOutputType.DEPLOYMENT_PACKAGE,
        ]
    )

build.build_dataflow_cfg(model_file, cfg_stitched_ip)

