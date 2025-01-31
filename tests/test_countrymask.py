#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 14 15:13:44 2019

@author: rt17603
"""
import pytest
import os
import glob
import numpy as np
from acrg.name.name import get_country

from acrg import countrymask
from acrg.config.paths import Paths

acrg_path = Paths.acrg
data_path = Paths.data

@pytest.fixture(scope="module")
def country_codes():
    country_codes = ['GBR','ESP','NOR']
    return country_codes

@pytest.fixture(scope="module")
def not_country_codes():
    country_codes = ['BRA','CHN','NZL']
    return country_codes

@pytest.fixture(scope="module")
def mask_with_gaps():
    mask_with_gaps = np.array([[1,1,1,4,4,4],
                               [1,0,1,2,2,2],
                               [1,1,1,2,0,0],
                               [3,3,3,2,2,2],
                               [3,0,3,5,5,5],
                               [3,3,0,5,6,6]])
    return mask_with_gaps

@pytest.fixture(scope="module")
def mask_no_gaps():
    mask_no_gaps = np.array([[1,1,1,4,4,4],
                             [1,1,1,2,2,2],
                             [1,1,1,2,2,0],
                             [3,3,3,2,2,2],
                             [3,3,3,5,5,5],
                             [3,3,0,5,6,6]])
    return mask_no_gaps
    
#%% Tests for domain_volume function

def test_incorrect_domain():
    '''
    Test Exception is raised when incorrect domain is specified as a str
    '''
    with pytest.raises(Exception):# as e_info:
        domain = "MMM"
        countrymask.domain_volume(domain)


def test_wrong_input():
    '''
    Test Exception is raised when incorrect domain is specified as something other than a str
    '''
    with pytest.raises(Exception):# as e_info:
        domain = 1
        countrymask.domain_volume(domain)


@pytest.fixture(scope="module")
def fp_directory():
    fp_dir = os.path.join(acrg_path,"tests/files/LPDM/fp_NAME/")
    return fp_dir


def test_other_directory(fp_directory):
    '''
    Test that function can be used with file read from a different directory
    '''
    domain = "EUROPE"
    fp_lat,fp_lon,fp_height = countrymask.domain_volume(domain,fp_directory=fp_directory)
    
    assert fp_lat is not None
    assert fp_lon is not None
    assert fp_height is not None

        
@pytest.mark.skipif(not glob.glob(os.path.join(data_path,"World_shape_databases")), reason="No access to files in data_path")
def test_convert_lons_0360():
    '''
    Test longitude values are converted to 0-360 range for domains with longitudes > 180 and < 0 (currently only the Arctic domain).
    '''  
    
    domain = 'ARCTIC'
    fp_directory = os.path.join(acrg_path, "tests/files/LPDM/fp_NAME/")
    fp_lat,fp_lon,fp_height = countrymask.domain_volume(domain, fp_directory=fp_directory)
    if any(fp_lon < 0) & any(fp_lon > 180):
        lon_0360 = countrymask.convert_lons_0360(fp_lon)

    assert lon_0360 is not None
    assert all(lon_0360 >= 0) is True
    assert all(lon_0360 < 360) is True

# Tests for create_country_mask_eez
    
@pytest.mark.skipif(not glob.glob(os.path.join(data_path,"World_shape_databases")), reason="No access to files in data_path")
def test_country_match(country_codes,not_country_codes,fp_directory):
    """
    Tests that total (land + ocean) countrymask is equivalent to
    the separate land and ocean masks, up to a threshold number of grid cells.
    Also tests if a couple of expected countries are/are not included.
    """
    
    ds_land = countrymask.create_country_mask_eez(domain='EUROPE',include_land_territories=True,
                                                  include_ocean_territories=False,
                                                  fill_gaps=False,fp_directory=fp_directory,
                                                  output_path=None,save=False)
    
    ds_ocean = countrymask.create_country_mask_eez(domain='EUROPE',include_land_territories=False,
                                                  include_ocean_territories=True,
                                                  fill_gaps=False,fp_directory=fp_directory,
                                                  output_path=None,save=False)
    
    ds_both = countrymask.create_country_mask_eez(domain='EUROPE',include_land_territories=True,
                                                  include_ocean_territories=True,
                                                  fill_gaps=False,fp_directory=fp_directory,
                                                  output_path=None,save=False)
    
    land = ds_land['country'].values
    ocean = ds_ocean['country'].values
    both = ds_both['country'].values
    
    for c_code in country_codes:
        
        country_code_match = [c_code for c in ds_both['country_code'].values if c_code == c]
        
        assert len(country_code_match) == 1
                              
        country_num = np.where(ds_both['country_code'].values == c_code)
        
        country_land_ocean = np.zeros(land.shape)
        country_land_ocean[np.where(land == country_num)] = 1.0
        country_land_ocean[np.where(ocean == country_num)] = 1.0

        country_both = np.zeros(both.shape)
        country_both[np.where(both == country_num)] = 1.0
    
        diff = country_land_ocean - country_both

        assert len(np.nonzero(diff)[0]) == 0.
        
    for not_c_code in not_country_codes:
        
        country_code_match = [not_c_code for c in ds_both['country_code'].values if not_c_code == c]
        
        assert len(country_code_match) == 0
        
def test_fill_gaps(mask_with_gaps,mask_no_gaps,fp_directory):
    """
    Tests that mask_fill_gaps in correctly fills in all gaps in the mask 
    by searching for empty grid cells which are surrounded by identically filled grid cells.
    """
    
    filled_array = countrymask.mask_fill_gaps(mask_with_gaps)
    
    assert np.array_equal(filled_array,mask_no_gaps) == True
    
@pytest.mark.skipif(not glob.glob(os.path.join(data_path,"LPDM/fp_NAME/")), reason="No access to files in data_path")
def test_get_country(fp_directory):
    """
    Creates a countryfile and checks that name.get_country can 
    read this file and extract all required variables.
    Then removes this file.
    """
    
    output_path = os.path.join(acrg_path,'tests/files/LPDM/countries/country_EUROPE')
    
    c_mask = countrymask.create_country_mask_eez(domain='EUROPE',include_land_territories=True,
                                                 include_ocean_territories=True,reset_index=True,
                                                 fill_gaps=False,fp_directory=fp_directory,
                                                 output_path=output_path,save=True)
    
    c_mask_extracted = get_country(domain='EUROPE',country_file=output_path+'.nc')
    
    assert c_mask_extracted
    assert type(c_mask_extracted.country) == np.ndarray
    assert type(c_mask_extracted.name) == np.ndarray
    
    if os.path.exists(output_path+'.nc'):
        os.remove(output_path+'.nc')

# Samoa lat and lon 13.7590° S, 172.1046° W
