#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2023 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    obgc_driver.py

DESCRIPTION
    Driver for the separate ocean biogeochemistry executable, called from 
    link_drivers.
'''
import re
import os
import sys
import shutil
import common
import nemo_driver
import dr_env_lib.obgc_def
import dr_env_lib.env_lib
import top_controller

def _check_obgc_nl(envar_container):
    '''
    As the environment variable OBGC_NL is required by both the setup
    and finalise functions, this will be encapsulated here
    '''
    # Information will be retrieved from this file during the running of the
    # driver, so check it exists
    if not os.path.isfile(envar_container['OBGC_NL']):
        sys.stderr.write('[FAIL] Can not find the nemo namelist file %s\n' %
                         envar_container['OBGC_NL'])
        sys.exit(error.MISSING_DRIVER_FILE_ERROR)
    else:
        return 0

def _load_environment_variables(obgc_envar):
    '''
    Load the OBGC environment variables required for the model run into the
    obgc_envar container
    '''
    # Load the obgc namelist environment variable
    obgc_envar = dr_env_lib.env_lib.load_envar_from_definition(
        obgc_envar, dr_env_lib.obgc_def.OBGC_ENVIRONMENT_VARS_INITIAL)
    _ = _check_obgc_nl(obgc_envar)

    return obgc_envar

def _setup_executable(common_env, nemo_envar):
    '''
    Setup the environment and any files required by the executable
    '''
    sys.stdout.write('[INFO] Running OBGC as a separate executable\n')

    # Create the environment variable container
    obgc_envar = dr_env_lib.env_lib.LoadEnvar()
    # Load the environment variables required
    obgc_envar = _load_environment_variables(obgc_envar)

    # Link the ocean biogeochemistry (OBGC) executable
    common.remove_file(obgc_envar['OBGC_LINK'])
    os.symlink(obgc_envar['OBGC_EXEC'],
               obgc_envar['OBGC_LINK'])

    # If the timestep for OBGC is guaranteed to be the same as
    # nemo executable then all variables could be passed through
    # nemo_envar. However, while this is likely, it's possible
    # OBGC is using a different timestep, so some variables
    # do need to be read from namelist_bgc_cfc.
    history_obgc_nl = nemo_envar['history_nemo_nl'].replace('namelist_cfg',
                                                            'namelist_bgc_cfg')
    print("history_obgc_nl=",history_obgc_nl)
    gl_first_step_match = 'nn_it000='
    gl_step_int_match = 'rn_dt='
    gl_last_step_match = 'nn_itend='

    # First timestep of the previous cycle
    _, first_step_val = common.exec_subproc(['grep', gl_first_step_match,
                                             history_obgc_nl])

    obgc_first_step = int(re.findall(r'.+=(.+),', first_step_val)[0])

    # Last timestep of the previous cycle
    _, last_step_val = common.exec_subproc(['grep', gl_last_step_match,
                                            history_obgc_nl])
    obgc_last_step = re.findall(r'.+=(.+),', last_step_val)[0]

    # Determine (as an integer) the number of seconds per model timestep
    _, obgc_step_int_val = common.exec_subproc(['grep', gl_step_int_match,
                                                obgc_envar['OBGC_NL']])
    obgc_step_int = int(re.findall(r'.+=(\d*)', obgc_step_int_val)[0])

    print("obgc_first_step,obgc_last_step,obgc_step_int=",
          obgc_first_step,obgc_last_step,obgc_step_int)

    # Determine obgc_next_step and obgc_final_step
    if nemo_envar['restart_ctl'] == 0:
        obgc_next_step = obgc_first_step
    else:
        obgc_next_step = int(obgc_last_step) + 1
    obgc_final_step = (nemo_envar['tot_runlen_sec'] // obgc_step_int) + \
                      obgc_next_step - 1

    # Will update the main namelist by generating the argument list for
    # update_nemo_nl
    update_nl_cmd = '--file %s --runid %so --restart %s --restart_ctl %s ' \
                    '--next_step %i --final_step %s --start_date %s ' \
                    '--leapyear %i --iproc %s --jproc %s --verbose' % \
                    (obgc_envar['OBGC_NL'], \
                     common_env['RUNID'], \
                     nemo_envar['ln_restart'], \
                     nemo_envar['restart_ctl'], \
                     obgc_next_step, \
                     obgc_final_step, \
                     nemo_envar['nemo_ndate0'], \
                     nemo_envar['nleapy'], \
                     obgc_envar['OBGC_IPROC'], \
                     obgc_envar['OBGC_JPROC'])

    update_nl_cmd = './update_nemo_nl %s' % update_nl_cmd

    # Refactor to use the safe exec subproc
    update_nl_rcode, _ = common.__exec_subproc_true_shell([update_nl_cmd])
    if update_nl_rcode != 0:
        sys.stderr.write('[FAIL] Error updating OBGC namelist\n')
        sys.exit(error.SUBPROC_ERROR)

    # Run the setup for passive tracers
    controller_mode = "run_controller"
    top_controller.run_controller(common_env,
                                  nemo_envar['restart_ctl'],
                                  int(obgc_envar['OBGC_NPROC']),
                                  common_env['RUNID'],
                                  common_env['DRIVERS_VERIFY_RST'],
                                  nemo_envar['nemo_dump_time'],
                                  controller_mode)

    return obgc_envar

def _set_launcher_command(launcher, obgc_envar):
    '''
    Setup the launcher command for the executable
    '''
    if obgc_envar['ROSE_LAUNCHER_PREOPTS_OBGC'] == 'unset':
        ss = False
        obgc_envar['ROSE_LAUNCHER_PREOPTS_OBGC'] = \
            common.set_aprun_options(obgc_envar['OBGC_NPROC'], \
                obgc_envar['OCEAN_NODES'], obgc_envar['OMPTHR_OBGC'], \
                    obgc_envar['OBGC_HYPERTHRDS'], ss) \
                        if launcher == 'aprun' else ''

    launch_cmd = '%s ./%s' % \
        (obgc_envar['ROSE_LAUNCHER_PREOPTS_OBGC'], \
             obgc_envar['OBGC_LINK'])

    # Put in quotes to allow this environment variable to be exported as it
    # contains (or can contain) spaces
    obgc_envar['ROSE_LAUNCHER_PREOPTS_OBGC'] = "'%s'" % \
        obgc_envar['ROSE_LAUNCHER_PREOPTS_OBGC']
    return launch_cmd

def write_obgc_out_to_stdout():
    '''
    Write the contents of bgc.output to standard out
    '''
    # Append the ocean output and solver stat file to standard out. Use an
    # iterator to read the files, incase they are too large to fit into
    # memory. 
    obgc_stdout_file = 'bgc.output'
    # Not sure we have any solver stat files for OBGC
    #nemo40_solver_file = 'run.stat'
    for obgc_output_file in [obgc_stdout_file]:
        # The output file from NEMO4.0 has some suspect utf8 encoding,
        # this try/except will handle it
        if os.path.isfile(obgc_output_file):
            sys.stdout.write('[INFO] OBGC output from file %s\n' %
                             obgc_output_file)
            with open(obgc_output_file, 'r', encoding='utf-8') as n_out:
                for line in n_out:
                    try:
                        sys.stdout.write(line)
                    except UnicodeEncodeError:
                        pass
        else:
            sys.stdout.write('[INFO] OBGC output file %s not avaliable\n'
                             % obgc_output_file)

def _finalize_executable(common_env):
    '''
    Finalize the OBGC run, copy the nemo namelist to the restart directory
    for the next cycle, update standard out, and ensure that no errors
    have been found in the NEMO execution.
    '''
    sys.stdout.write('[INFO] finalizing OBGC\n')
    sys.stdout.write('[INFO] running finalize in %s\n' % os.getcwd())

    # Write OBGC to standard output
    write_obgc_out_to_stdout()

    _, error_count = common.__exec_subproc_true_shell([ \
            'grep "E R R O R" bgc.output | wc -l'])
    if int(error_count) >= 1:
        sys.stderr.write('[FAIL] An error has been found with the OBGC run.'
                         ' Please investigate the bgc.output file for more'
                         ' details\n')
        sys.exit(error.COMPONENT_MODEL_ERROR)

    # Move the main namelist to the restart directory to allow the next cycle
    # to pick it up
    obgc_envar_fin = dr_env_lib.env_lib.LoadEnvar()
    obgc_envar_fin = dr_env_lib.env_lib.load_envar_from_definition(
        obgc_envar_fin, dr_env_lib.obgc_def.OBGC_ENVIRONMENT_VARS_FINAL)
    obgc_rst = nemo_driver.get_nemorst(obgc_envar_fin['OBGC_NL'])
    if os.path.isdir(obgc_rst) and \
            os.path.isfile(obgc_envar_fin['OBGC_NL']):
        shutil.copy(obgc_envar_fin['OBGC_NL'], obgc_rst)

    # Run finalize in top controller
    controller_mode = "finalize"
    top_controller.run_controller([], [], [], [], [], [], controller_mode)

def run_driver(envar_insts, mode, run_info):
    '''
    Run the driver, and return an instance of LoadEnvar and as string
    containing the launcher command for the OBGC model
    '''
    common_env = envar_insts['common']
    if mode == 'run_driver':
        if 'nemo' not in envar_insts:
            sys.stderr.write("[FAIL] require 'nemo' to appear before 'obgc' "
                             "in 'models' list")
            sys.exit(999)
        nemo_envar = envar_insts['nemo']
        exe_envar = _setup_executable(common_env, nemo_envar)
        launch_cmd = _set_launcher_command(common_env['ROSE_LAUNCHER'],
                                           exe_envar)
        # Save for later - marc 31/3/23
        #if run_info['l_namcouple']:
        #    model_snd_list = None
        #else:
        #    run_info, model_snd_list = \
        #        _sent_coupling_fields(exe_envar, run_info)
        model_snd_list = None
    elif mode == 'finalize':
        _finalize_executable(common_env)
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    elif mode == 'failure':
        # subset of operations of the model fails
        # Save for later - marc 31/3/23
        #write_ocean_out_to_stdout()
        exe_envar = None
        launch_cmd = None
        model_snd_list = None
    return exe_envar, launch_cmd, run_info, model_snd_list
