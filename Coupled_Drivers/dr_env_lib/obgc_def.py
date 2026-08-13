#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    obgc_def.py

DESCRIPTION
    Definition of the environment variables required for a OBGC model
    run
'''

# Variables required for both initalise and finalise
OBGC_ENVIRONMENT_VARS_COMMON = {
    'OBGC_NL': {'default_val': 'namelist_bgc_cfg'},
    }

OBGC_ENVIRONMENT_VARS_INITIAL = {
    'OBGC_EXEC': {'desc': ('OBGC executable (OBGC_EXEC=<full path to'
                            ' exec>)')},
    'OBGC_NPROC': {'desc': 'Number of OBGC processors'},
    'OBGC_IPROC': {'desc': 'Number of OBGC processors in the i direction'},
    'OBGC_JPROC': {'desc': 'Number of OBGC processors in the j direction'},
    'OBGC_LINK': {'default_val': 'obgc.exe'},
    'OBGC_RES': {'default_val': ''},
    'ROSE_LAUNCHER_PREOPTS_OBGC': {'default_val': 'unset',
                                   'triggers': [
                                       [lambda my_val: my_val == 'unset',
                                        ['OBGC_NODES', 'OMPTHR_OBGC',
                                         'OBGC_HYPERTHRDS']]]},
    'OBGC_NODES': {},
    'OMPTHR_OBGC': {},
    'OBGC_HYPERTHRDS': {}
    }

OBGC_ENVIRONMENT_VARS_FINAL = {}
# Merge inital and final with common
OBGC_ENVIRONMENT_VARS_INITIAL = {**OBGC_ENVIRONMENT_VARS_COMMON,
                                 **OBGC_ENVIRONMENT_VARS_INITIAL}
OBGC_ENVIRONMENT_VARS_FINAL = {**OBGC_ENVIRONMENT_VARS_COMMON,
                               **OBGC_ENVIRONMENT_VARS_FINAL}
