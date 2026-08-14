#!/usr/bin/env python3
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2026 Met Office. All rights reserved.
 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    write_namcouple_ocn_utils.py

DESCRIPTION
    Ocean only utilities functions for writing namcouple on the fly
'''
import sys
try:
    import f90nml
except ImportError:
    pass
import error

# Ocean resolutions
OCEAN_RESOLS_PRE_NEMO4_2 = {'orca2': [182, 149],
                            'orca1': [362, 332],
                            'orca025': [1442, 1021],
                            'orca12': [4322, 3059],
                            'orca36': [12960, 10850]}
OCEAN_RESOLS_FROM_NEMO4_2 = {'orca2': [180, 148],
                             'orca1': [360, 331],
                             'orca075': [480, 350],
                             'orca025': [1440, 1020],
                             'orca12': [4320, 3058],
                             'orca36': [12958, 10849]}

def get_ocean_resol(nemo_name, nemo_nl_file, nemo_version, run_info):
    '''
    Determine the ocean resolution.
    This function is only used when creating the namcouple at run time.
    '''

    # Set variable names
    grid_name = nemo_name + '_grid'
    resol_name = nemo_name + '_resol'
    dt_name = nemo_name + '_dt'

    # See if resolution is contained within namelists (existent of
    # namelist_cfg has already been checked)
    ocean_nml = f90nml.read(nemo_nl_file)

    # Check the required entries exist
    if 'namcfg' not in ocean_nml:
        sys.stderr.write('[FAIL] namcfg not found in namelist_cfg\n')
        sys.exit(error.MISSING_OCN_RESOL_NML)

    if 'jpiglo' in ocean_nml['namcfg']:
        # Resolution is contained within namelists

        if 'jpiglo' not in ocean_nml['namcfg'] or \
           'jpjglo' not in ocean_nml['namcfg'] or \
           'cp_cfg' not in ocean_nml['namcfg'] or \
           'jp_cfg' not in ocean_nml['namcfg']:
            sys.stderr.write('[FAIL] cp_cfg, jp_cfg, jpiglo or jpjglo are '
                             'missing from namelist namcf in namelist_cfg\n')
            sys.exit(error.MISSING_OCN_RESOL)

        # Check it is on orca grid
        if ocean_nml['namcfg']['cp_cfg'] != 'orca':
            sys.stderr.write('[FAIL] we can currently only handle the '
                             'ORCA grid\n')
            sys.exit(error.NOT_ORCA_GRID)

        # Check this is a grid we recognise
        if ocean_nml['namcfg']['jp_cfg'] == 25:
            run_info[grid_name] = 'orca025'
        else:
            run_info[grid_name] = 'orca' + str(ocean_nml['namcfg']['jp_cfg'])

        # Store the ocean resolution
        run_info[resol_name] = [ocean_nml['namcfg']['jpiglo'],
                                ocean_nml['namcfg']['jpjglo']]

    else:
        # Resolution should be contained within a domain_cfg netCDF file.
        # Rather than read this file, assume resolution is declared.
        if grid_name not in run_info:
            sys.stderr.write('[FAIL] it is necessary to declare the ocean '
                             'resolution by setting the %_RES environment '
                             'variable.' % nemo_name)
            sys.exit(error.NOT_DECLARE_OCN_RES)
        else:
            # Determine the ocean resolution
            if nemo_version < 402:
                # Pre-NEMO4.2 have haloes
                if run_info[grid_name] not in OCEAN_RESOLS_PRE_NEMO4_2:
                    sys.stderr.write('[FAIL] the ocean resolution for %s is '
                                     'unknown\n' % run_info[grid_name])
                    sys.exit(error.UNKNOWN_OCN_RESOL)
                else:
                    run_info[resol_name] = \
                        [OCEAN_RESOLS_PRE_NEMO4_2[run_info[grid_name]][0],
                         OCEAN_RESOLS_PRE_NEMO4_2[run_info[grid_name]][1]]
            else:
                # From NEMO4.2 there are no haloes
                if run_info[grid_name] not in OCEAN_RESOLS_FROM_NEMO4_2:
                    sys.stderr.write('[FAIL] the ocean resolution for %s is '
                                     'unknown\n' % run_info[grid_name])
                    sys.exit(error.UNKNOWN_OCN_RESOL)
                else:
                    run_info[resol_name] = \
                        [OCEAN_RESOLS_FROM_NEMO4_2[run_info[grid_name]][0],
                         OCEAN_RESOLS_FROM_NEMO4_2[run_info[grid_name]][1]]

    # Store the timestep
    if 'rn_dt' in ocean_nml['namdom']:
        # If coupling a coarsened biogeochemistry (BGC) this is required to
        # determine the coupling frequency between physical ocean and BGC.
        # Not needed otherwise.
        run_info[dt_name] = ocean_nml['namdom']['rn_dt']

    return run_info
