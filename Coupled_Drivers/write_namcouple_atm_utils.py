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
    write_namcouple_atm_utils.py

DESCRIPTION
    Utility functions for writing namcouple on the fly which are usually
    only called by um_driver.py or jnr_driver.py, although it's possible
    for function 'core_namcouple_vars' to be called by nemo_driver.py.
'''
import os
import sys
try:
    import f90nml
except ImportError:
    pass

def get_atmos_resol(um_name, um_resol_file, run_info):
    '''
    Determine the atmosphere resolution.
    This function is only used when creating the namcouple at run time.
    '''

    # Check that resolution file exists
    if not os.path.isfile(um_resol_file):
        sys.stderr.write('[FAIL] not found %s file.\n' % um_resol_file)
        sys.exit(error.MISSING_FILE_SIZES)

    # Read the resolution file
    sizes_nml = f90nml.read(um_resol_file)

    # Check the horizontal resolution variables exist
    if 'nlsizes' not in sizes_nml:
        sys.stderr.write('[FAIL] nlsizes not found in %s\n' % \
                             um_resol_file)
        sys.exit(error.MISSING_ATM_RESOL_NML)
    if 'global_row_length' not in sizes_nml['nlsizes'] or \
            'global_rows' not in sizes_nml['nlsizes'] or \
            'st_levels' not in sizes_nml['nlsizes']:
        sys.stderr.write('[FAIL] global_row_length, global_rows or st_levels '
                         'missing from namelist nlsizes in %s\n' % \
                             um_resol_file)
        sys.exit(error.MISSING_ATM_HORIZ_RESOL)

    # Store the grid
    atmos_resol = int(sizes_nml['nlsizes']['global_row_length'] / 2)
    atmos_grid_name = um_name + '_grid'
    if um_name == 'JNR':
        run_info[atmos_grid_name] = 'n' + str(atmos_resol) + 'j'
    else:
        run_info[atmos_grid_name] = 'n' + str(atmos_resol)

    # Store the resolution
    atmos_resol_name = um_name + '_resol'
    run_info[atmos_resol_name] = [sizes_nml['nlsizes']['global_row_length'],
                                  sizes_nml['nlsizes']['global_rows']]

    # Check that vertical resolution exists
    if 'model_levels' not in sizes_nml['nlsizes']:
        sys.stderr.write('[FAIL] model_levels is missing from namelist '
                         'nlsizes in %s\n' % um_resol_file)
        sys.exit(error.MISSING_ATM_VERT_RESOL)

    # Store the vertical levels for atmosphere
    atmos_lev_name = um_name + '_model_levels'
    run_info[atmos_lev_name] = sizes_nml['nlsizes']['model_levels']

    # Store soil levels
    atmos_lev_name = um_name + '_soil_levels'
    run_info[atmos_lev_name] = sizes_nml['nlsizes']['st_levels']

    return run_info

def get_jules_levels(jules_resol_file):
    '''
    Determine the number of vegetation tiles and non-vegetation tiles.
    This function is only used when creating the namcouple at run time.
    '''

    # Check that resolution file exists
    if not os.path.isfile(jules_resol_file):
        sys.stderr.write('[FAIL] not found %s file.\n' % jules_resol_file)
        sys.exit(error.MISSING_FILE_SHARED)

    # Read the resolution file
    sizes_nml = f90nml.read(jules_resol_file)

    # Check that soil depth, which is given by the number of elements in
    # in dzsoil_io, exists
    if 'jules_soil' not in sizes_nml:
        sys.stderr.write('[FAIL] jules_soil not found in %s\n' % \
                         jules_resol_file)
        sys.exit(error.MISSING_JULES_RESOL_NML)

    # Check that tile information exists
    if 'jules_surface_types' not in sizes_nml:
        sys.stderr.write('[FAIL] jules_surface_types not found in %s\n' % \
                         jules_resol_file)
        sys.exit(error.MISSING_JULES_RESOL_NML)
    # 'npft' is the number of plant functional or vegetation tiles, and
    # 'nnvg' is the number of non-vegetation tiles.
    if 'npft' not in sizes_nml['jules_surface_types'] or \
       'nnvg' not in sizes_nml['jules_surface_types']:
        sys.stderr.write('[FAIL] npft or nnvg is missing from namelist '
                         'jules_surface_types in %s\n' % jules_resol_file)
        sys.exit(error.MISSING_JULES_TILE_INFO)

    # Return number of plant function tiles (npft) and
    # number of non-vegetation tiles (nnvg).
    return sizes_nml['jules_surface_types']['npft'], \
        sizes_nml['jules_surface_types']['nnvg']

def _determine_rmp_mapping(rmp_mapping):
    '''
    Determine the rmp mapping from the string rmp_mapping
    '''

    remap = {}
    # Separate by the number of rmp mappings
    for remap_str in rmp_mapping.split(';'):

        # The default mapping type
        mapping_type = -99

        # Determine the stash fields which this remapping applies to.
        i_colon = remap_str.find(':')
        if i_colon > 0:
            stash_list = []
            for stash_code in remap_str[i_colon+1:].split(','):
                stash_list.append(int(stash_code))
            remap_str = remap_str[:i_colon]
        else:
            stash_list = ['default']

        # Determine the mapping type
        if remap_str.find('BICUBIC') > -1:
            mapping_type = 3
        else:
            i_ext = remap_str.find('_1st')
            if i_ext > 0:
                mapping_type = 1
                remap_str = remap_str[0:i_ext]
            else:
                i_ext = remap_str.find('_2nd')
                if i_ext > 0:
                    mapping_type = 2
                    remap_str = remap_str[0:i_ext]

        # Store remapping and the mapping type
        for stash_name in stash_list:
            if stash_name != 'default':
                stash_name = '{:05d}'.format(stash_name)
            remap[stash_name] = {'mapping': remap_str, 'map_type': mapping_type}

    # Return remapping information
    return remap

def _add_hybrid_cpl(n_cpl_freq, cpl_list, origin, dest, name_out_ident,
                    rmp_mapping, hybrid_weight, cpl_tstep_info):
    '''
    Write the hybrid coupling fields into hybrid_snd_list.
    This function is only used when creating the namcouple at run time.
    '''

    if cpl_list:

        # Determine the remapping
        remap = _determine_rmp_mapping(rmp_mapping)

        # Ensure we have a list
        if isinstance(cpl_list, int):
            # Convert single integer to a list
            cpl_list = [cpl_list]

        # Loop across the fields to couple
        hybrid_snd_list = []
        for stash_code in cpl_list:

            # See if coupling frequency has been overridden
            if stash_code in cpl_tstep_info:
                override_cpl_freq = cpl_tstep_info[stash_code]
            else:
                override_cpl_freq = None

            if stash_code < 0:
                # Passing a scalar
                stash_name = '{:03d}'.format(-1 * stash_code)
                name_out = 'sc' + stash_name + name_out_ident
                remapping = 'OneVal'
                mapping_type = 1
            else:
                stash_name = '{:05d}'.format(stash_code)
                name_out = stash_name + name_out_ident + '001s'

                if stash_name in remap:
                    remapping = remap[stash_name]['mapping']
                    mapping_type = remap[stash_name]['map_type']
                else:
                    if 'default' in remap:
                        remapping = remap['default']['mapping']
                        mapping_type = remap['default']['map_type']
                    else:
                        sys.stderr.write('[FAIL] Require a default remapping '
                                         'in hybrid_rmp_mapping.\n')
                        sys.exit(error.MISSING_DEFAULT_RMP)

            # Add entry
            import write_namcouple
            hybrid_snd_list.append(
                write_namcouple.NamcoupleEntry(name_out,
                                               (100000 + stash_code),
                                               '?', origin, dest, -99, '?',
                                               remapping, mapping_type,
                                               hybrid_weight, True, False,
                                               n_cpl_freq, override_cpl_freq))

            # Move to next entry
            hybrid_weight += 1
    else:
        # There's no extra coupling fields
        hybrid_snd_list = None

    return hybrid_weight, hybrid_snd_list

def read_hybrid_coupling(hybrid_file_nml, run_info, oasis_nml):
    '''
    Read the hybrid coupling namelist and store the hybrid coupling
    fields.
    This function is only used when creating the namcouple at run time.
    '''
    # Default option is to send no fields
    hybrid_snd_list = None

    # Determine if hybrid sending file is present
    if os.path.exists(hybrid_file_nml):
        # Determine if this Snr->Jnr or Jnr->Snr coupling
        if hybrid_file_nml == 'HYBRID_SNR2JNR':
            # These are Snr->Jnr fields
            origin = 'ATM'
            dest = 'JNR'
            name_out_ident = 's'
        else:
            # These are Jnr->Snr fields
            origin = 'JNR'
            dest = 'ATM'
            name_out_ident = 'j'

        # Check we have the data in oasis_nml which we need
        if 'hybrid_weight' not in oasis_nml['oasis_send_nml']:
            sys.stderr.write('[FAIL] entry hybrid_weight missing '
                             'from namelist oasis_send_nml.\n')
            sys.exit(error.MISSING_HYBRID_WEIGHT)
        else:
            hybrid_weight = oasis_nml['oasis_send_nml']['hybrid_weight']
        if 'hybrid_rmp_mapping' not in oasis_nml['oasis_send_nml']:
            sys.stderr.write('[FAIL] entry hybrid_rmp_mapping missing '
                             'from namelist oasis_send_nml.\n')
            sys.exit(error.MISSING_HYBRID_RMP_MAPPING)
        else:
            rmp_mapping = oasis_nml['oasis_send_nml']['hybrid_rmp_mapping']

        # Read the hybrid namelist
        hybrid_nml = f90nml.read(hybrid_file_nml)

        # Check we have the expected information
        if 'hybrid_cpl' not in hybrid_nml:
            sys.stderr.write('[FAIL] namelist hybrid_cpl is missing '
                             'from %s.\n' % hybrid_nml)
            sys.exit(error.MISSING_HYBRID_NML)
        if 'cpl_hybrid' not in hybrid_nml['hybrid_cpl']:
            sys.stderr.write('[FAIL] entry cpl_hybrid is missing '
                             'from namelist hybrid_cpl in %s.\n' %
                             hybrid_nml)
            sys.exit(error.MISSING_HYBRID_SEND)

        # Default option is to have no stats
        if 'i_hybrid_stats' not in hybrid_nml['hybrid_cpl']:
            hybrid_nml['hybrid_cpl']['i_hybrid_stats'] = 0

        # Check for any overrides to the coupling frequencies
        cpl_tstep_info = {}
        if 'cpl_tstep' in hybrid_nml['hybrid_cpl']:
            n_overrides = int(len(hybrid_nml['hybrid_cpl']['cpl_tstep']) / 2)
            for i in range(n_overrides):
                cpl_tstep_info[hybrid_nml['hybrid_cpl']['cpl_tstep'][2*i]] \
                    = hybrid_nml['hybrid_cpl']['cpl_tstep'][2*i+1]

        # Check that we have some hybrid fields to send
        if hybrid_nml['hybrid_cpl']['cpl_hybrid']:
            if hybrid_nml['hybrid_cpl']['l_hybrid_overw'] or \
               hybrid_nml['hybrid_cpl']['i_hybrid_stats'] > 0:
                hybrid_weight, hybrid_snd_list \
                    = _add_hybrid_cpl(0, hybrid_nml['hybrid_cpl']['cpl_hybrid'],
                                      origin, dest, name_out_ident,
                                      rmp_mapping, hybrid_weight,
                                      cpl_tstep_info)

                # Are there any extra stats to send
                if hybrid_nml['hybrid_cpl']['i_hybrid_stats'] > 0 and \
                        'cpl_hybrid_stats' in hybrid_nml['hybrid_cpl']:
                    hybrid_weight, hybrid_snd_stat_list = _add_hybrid_cpl(
                        1, hybrid_nml['hybrid_cpl']['cpl_hybrid_stats'],
                        origin, dest, name_out_ident, rmp_mapping,
                        hybrid_weight, cpl_tstep_info)

                    if hybrid_snd_stat_list:
                        hybrid_snd_list.extend(hybrid_snd_stat_list)

                # Need to store value of i_hybrid_stats in case it's
                # true and any of the coupling frequencies need
                # modifying as a consequence.
                if hybrid_nml['hybrid_cpl']['i_hybrid_stats'] > 0:
                    flag_name = 'l_hyb_stats_' + origin + '2' + dest
                    run_info[flag_name] = True

        # See if any additional radiation fields are required.
        if 'hybrid_jnr' in hybrid_nml:
            if 'cpl_hybrid_rad_sw' in hybrid_nml['hybrid_jnr'] or \
               'cpl_hybrid_rad_lw' in hybrid_nml['hybrid_jnr']:

                # See if there an update to weighting for hybrid radiation
                # coupling fields
                if 'hybrid_rad_weight' in oasis_nml['oasis_send_nml']:
                    hybrid_weight \
                        = oasis_nml['oasis_send_nml']['hybrid_rad_weight']

                # Store SW radiation coupling fields in hybrid_snd_rad_sw_list
                if 'cpl_hybrid_rad_sw' in hybrid_nml['hybrid_jnr']:
                    hybrid_weight, hybrid_snd_rad_sw_list = _add_hybrid_cpl(
                        0, hybrid_nml['hybrid_jnr']['cpl_hybrid_rad_sw'],
                        origin, dest, name_out_ident,
                        rmp_mapping, hybrid_weight, cpl_tstep_info)

                    # Add radiation coupling fields to list of hybrid coupling
                    # fields
                    if hybrid_snd_rad_sw_list:
                        if hybrid_snd_list:
                            hybrid_snd_list.extend(hybrid_snd_rad_sw_list)
                        else:
                            hybrid_snd_list = hybrid_snd_rad_sw_list

                # Store LW radiation coupling fields in hybrid_snd_rad_lw_list
                if 'cpl_hybrid_rad_lw' in hybrid_nml['hybrid_jnr']:
                    hybrid_weight, hybrid_snd_rad_lw_list = _add_hybrid_cpl(
                        0, hybrid_nml['hybrid_jnr']['cpl_hybrid_rad_lw'],
                        origin, dest, name_out_ident,
                        rmp_mapping, hybrid_weight, cpl_tstep_info)

                    # Add radiation coupling fields to list of hybrid coupling
                    # fields
                    if hybrid_snd_rad_lw_list:
                        if hybrid_snd_list:
                            hybrid_snd_list.extend(hybrid_snd_rad_lw_list)
                        else:
                            hybrid_snd_list = hybrid_snd_rad_lw_list

    return run_info, hybrid_snd_list

def core_namcouple_vars(input_namelist, run_info):
    '''
    Store core namcouple variables.
    This is usually called from um_driver.py but can be called from
    nemo_driver.py if the UM is not the coupled model.
    '''
    # The namcoupled debug value
    if 'nlogprt' in input_namelist:
        run_info['nlogprt'] = input_namelist['nlogprt']
        if isinstance(run_info['nlogprt'], int):
            # Convert single integer to a list
            run_info['nlogprt'] = [run_info['nlogprt']]
    else:
        run_info['nlogprt'] = 0
    # Determine if any namcouple coupling should use EXPOUT
    if 'expout' in input_namelist:
        if isinstance(input_namelist['expout'], list):
            run_info['expout'] = input_namelist['expout']
        else:
            run_info['expout'] = [input_namelist['expout']]
    # Determine if any remapping file need to be created by OASIS-mct
    if 'rmp_create' in input_namelist:
        if isinstance(input_namelist['rmp_create'], list):
            run_info['rmp_create'] = \
                input_namelist['rmp_create']
        else:
            run_info['rmp_create'] = \
                [input_namelist['rmp_create']]

    return run_info
