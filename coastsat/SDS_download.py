"""
This module contains all the functions needed to download the satellite images 
from the Google Earth Engine server
    
Author: Kilian Vos, Water Research Laboratory, University of New South Wales
"""

# load modules
import os
import numpy as np
import matplotlib.pyplot as plt
import pdb
import numpy
# earth engine modules
import ee
from urllib.request import urlretrieve
import zipfile
import copy
from datetime import date

# additional modules
from datetime import datetime, timedelta
import pytz
import pickle
import pprint
from skimage import morphology, transform
from scipy import ndimage

# CoastSat modules
#from coastsat import SDS_preprocess, SDS_tools, gdal_merge

np.seterr(all='ignore') # raise/ignore divisions by 0 and nans


def check_images_available(inputs):
    """
    Create the structure of subfolders for each satellite mission
     
    KV WRL 2018       
  
    Arguments:
    -----------
    inputs: dict 
        inputs dictionnary
    
    Returns:
    -----------
    im_dict_T1: list of dict
        list of images in Tier 1 and Level-1C
    im_dict_T2: list of dict
        list of images in Tier 2 (Landsat only)   
    """
    
    # check if EE was initialised or not
    try:
        ee.ImageCollection('LANDSAT/LT05/C01/T1_TOA')
    except:
        ee.Initialize()
    
    print('Images available between %s and %s:'%(inputs['dates'][0],inputs['dates'][1]), end='\n')          
    # check how many images are available in Tier 1 and Sentinel Level-1C
    col_names_T1 = {'L5':'LANDSAT/LT05/C01/T1_TOA',
                 'L7':'LANDSAT/LE07/C01/T1_TOA',
                 'L8':'LANDSAT/LC08/C01/T1_TOA',
                 'S2':'COPERNICUS/S2'}
    
    print('- In Landsat Tier 1 & Sentinel-2 Level-1C:')
    im_dict_T1 = dict([])
    sum_img = 0
    for sat_list in inputs['sat_list']:
        
        # get list of images in EE collection
        while True:
            try:
                ee_col = ee.ImageCollection(col_names_T1[sat_list])
                col = ee_col.filterBounds(ee.Geometry.Polygon(inputs['polygon']))\
                            .filterDate(inputs['dates'][0],inputs['dates'][1])
                im_list = col.getInfo().get('features')
                break
            except:
                continue
        # remove very cloudy images (>95% cloud cover)
        im_list_upt = remove_cloudy_images(im_list, sat_list)
        sum_img = sum_img + len(im_list_upt)
        print('  %s: %d images'%(sat_list,len(im_list_upt)))
        im_dict_T1[sat_list] = im_list_upt
        
        print('  Total: %d images'%sum_img)
    
        return im_dict_T1, sum_img

def obtain_image_median(collection, time_range, area, satname):
    """ Selection of median from a collection of images in the Earth Engine library
    See also: https://developers.google.com/earth-engine/reducers_image_collection

    Parameters:
        collection (): name of the collection
        time_range (['YYYY-MT-DY','YYYY-MT-DY']): must be inside the available data
        area (ee.geometry.Geometry): area of interest

    Returns:
        image_median (ee.image.Image)
     """
    collect = ee.ImageCollection(collection)
    if satname == ['L7']:
        ## Filter by time range and location
        collection_time = collect.filterDate(time_range[0], time_range[1])
        image_area = collection_time.filterBounds(area)
        image_2 = image_area.filterMetadata('CLOUD_COVER','less_than', 40)
        image_median = image_2.median()
        return image_median

    if satname == ['L8']:
        ## Filter by time range and location
        collection_time = collect.filterDate(time_range[0], time_range[1])
        image_area = collection_time.filterBounds(area)
        image_2 = image_area.filterMetadata('CLOUD_COVER','less_than', 40)
        image_median = image_2.median()
        return image_median

    elif satname == ['S2']:
        ## Filter by time range and location
        collection_time = collect.filterDate(time_range[0], time_range[1])
        image_area = collection_time.filterBounds(area)
        image_2 = image_area.filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than', 40)
        image_median = image_2.median()
        return image_median    


def retrieve_images(inputs, settings):
    """
    Downloads all images from Landsat 5, Landsat 7, Landsat 8 and Sentinel-2
    covering the area of interest and acquired between the specified dates.
    The downloaded images are in .TIF format and organised in subfolders, divided
    by satellite mission. The bands are also subdivided by pixel resolution.

    KV WRL 2018

    Arguments:
    -----------
    inputs: dict with the following keys
        'sitename': str
            name of the site
        'polygon': list
            polygon containing the lon/lat coordinates to be extracted,
            longitudes in the first column and latitudes in the second column,
            there are 5 pairs of lat/lon with the fifth point equal to the first point:
            ```
            polygon = [[[151.3, -33.7],[151.4, -33.7],[151.4, -33.8],[151.3, -33.8],
            [151.3, -33.7]]]
            ```
        'dates': list of str
            list that contains 2 strings with the initial and final dates in
            format 'yyyy-mm-dd':
            ```
            dates = ['1987-01-01', '2018-01-01']
            ```
        'sat_list': list of str
            list that contains the names of the satellite missions to include:
            ```
            sat_list = ['L5', 'L7', 'L8', 'S2']
            ```
        'filepath_data': str
            filepath to the directory where the images are downloaded

    Returns:
    -----------
    metadata: dict
        contains the information about the satellite images that were downloaded:
        date, filename, georeferencing accuracy and image coordinate reference system

    """
    
    # initialise connection with GEE server
    ee.Initialize()
    
    # check image availabiliy and retrieve list of images
    im_dict_T1, sum_img = check_images_available(inputs)
    
    # create a new directory for this site with the name of the site
    im_folder = os.path.join(inputs['filepath'],inputs['sitename'])
    if not os.path.exists(im_folder): os.makedirs(im_folder)    

    print('\nDownloading images:')
    suffix = '.tif'
    satname =  inputs['sat_list']
    
    # Landsat 5 download   
    if satname == ['L5']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'L5')
        # initialise variables and loop through images
        filenames = []; all_names = [];
        #for year in sat_list:
        median_img = obtain_image_median('LANDSAT/LT05/C01/T1_TOA',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),inputs['sat_list'])
        
        print('Median Processed')                 
        #extract year
        first_date = inputs["dates"][0]
        year = first_date[:-6]
        
        im_fn = dict([])
        im_fn[''] = 'L5' + '_' + inputs['sitename'] + '_median_' + year + suffix 
        # if two images taken at the same date add 'dup' to the name (duplicate)
        if any(im_fn[''] in _ for _ in all_names):
            im_fn[''] = 'L5' + '_' + inputs['sitename'] + '_dup' + suffix
        all_names.append(im_fn[''])
        filenames.append(im_fn[''])
        
        ##Extract band metadata and define those to download
        metadata = median_img.getInfo()
        im_bands = metadata['bands']
        
        bands = dict([])
        bands[''] = [im_bands[0], im_bands[1], im_bands[2], im_bands[3],
                             im_bands[4], im_bands[7]] 
        
        displacement = Landsat_Coregistration(inputs)
        print ('displacement calculated')

        #Apply XY displacement values from overlapping images to the median composite
        registered = median_img.displace(displacement, mode="bicubic")     
        print ('Registered')
        
        # download .tif from EE
        get_url('data', registered, ee.Number(30), inputs['polygon'], filepaths[1], bands[''])
        print ('Downloaded')
        
        #rename the file as the image is downloaded as 'data.tif'
        #locate download
        local_data = filepaths[1] + '\data.tif'

        try:
            os.rename(local_data, os.path.join(filepaths[1], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data, os.path.join(filepaths[1], im_fn['']))
        #metadata for .txt file
        filename_txt = im_fn[''].replace('.tif','')
        metadict = {'filename':im_fn[''],
                    'epsg':metadata['bands'][0]['crs'][5:],
                    'dates': str(year),
                    'median_no': sum_img} 
  
    
# Landsat 7 download                
    elif satname == ['L7']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'L7')
        # initialise variables and loop through images
        filenames = []; all_names = [];
        #for year in sat_list:
        median_img = obtain_image_median('LANDSAT/LE07/C01/T1_TOA',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),
                                         inputs['sat_list'])
        
        print('Median Processed')                 
        #extract year
        first_date = inputs["dates"][0]
        year = first_date[:-6]
        
        im_fn = dict([])
        im_fn[''] = 'L7' + '_' + inputs['sitename'] + '_median_' + year + suffix 
        # if two images taken at the same date add 'dup' to the name (duplicate)
        if any(im_fn[''] in _ for _ in all_names):
            im_fn[''] = 'L7' + '_' + inputs['sitename'] + '_dup' + suffix
        all_names.append(im_fn[''])
        filenames.append(im_fn[''])
        
        ##Extract band metadata and define those to download
        metadata = median_img.getInfo()
        im_bands = metadata['bands']
        
        bands = dict([])
        bands['pan'] = [im_bands[8]] # panchromatic band
        bands['ms'] = [im_bands[0], im_bands[1], im_bands[2], im_bands[3],
                       im_bands[4], im_bands[9]] # multispectral bands
         
        displacement = Landsat_Coregistration(inputs)

        #Apply XY displacement values from overlapping images to the median composite
        registered = median_img.displace(displacement, mode="bicubic")     
        print ('Registered')
     
        #download .tif from EE
        get_url('data', registered, ee.Number(30), inputs['polygon'], filepaths[2], bands['ms'])
        get_url('data', registered, ee.Number(15), inputs['polygon'], filepaths[1], bands['pan'])
        print ('Downloaded')
        
        #rename the file as the image is downloaded as 'data.tif'
        #locate download
        local_data = filepaths[2] + '\data.tif'
        local_data_pan = filepaths[1] + '\data.tif'
                
        try:
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[2], im_fn['']))
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))
       
        try:
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))
        
       #metadata for .txt file
        filename_txt = im_fn[''].replace('.tif','')
        metadict = {'filename':im_fn[''],
                    'epsg':metadata['bands'][0]['crs'][5:],
                    'dates': str(year),
                    'median_no': sum_img} 
  
    # Landsat 8 download                
    elif satname == ['L8']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'L8')
        # initialise variables and loop through images
        filenames = []; all_names = [];
        #for year in sat_list:
        median_img = obtain_image_median('LANDSAT/LC08/C01/T1_TOA',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),inputs['sat_list'])
        
        print('Median Processed')                 
        #extract year
        first_date = inputs["dates"][0]
        year = first_date[:-6]
        
        im_fn = dict([])
        im_fn[''] = 'L8' + '_' + inputs['sitename'] + '_median_' + year + suffix 
        # if two images taken at the same date add 'dup' to the name (duplicate)
        if any(im_fn[''] in _ for _ in all_names):
            im_fn[''] = 'L8' + '_' + inputs['sitename'] + '_dup' + suffix
        all_names.append(im_fn[''])
        filenames.append(im_fn[''])
        
        ##Extract band metadata and define those to download
        metadata = median_img.getInfo()
        im_bands = metadata['bands']
        
        bands = dict([])
        bands['pan'] = [im_bands[7]] # panchromatic band
        bands['ms'] = [im_bands[1], im_bands[2], im_bands[3], im_bands[4],
                       im_bands[5], im_bands[11]] # multispectral bands
        
        displacement = Landsat_Coregistration(inputs)

        #Apply XY displacement values from overlapping images to the median composite
        registered = median_img.displace(displacement, mode="bicubic")     
        print ('Co-registered')
                
        #download .tif from EE
        get_url('data', registered, ee.Number(30), inputs['polygon'], filepaths[2], bands['ms'])
        get_url('data', registered, ee.Number(15), inputs['polygon'], filepaths[1], bands['pan'])
        print ('Downloaded')
        
        #rename the file as the image is downloaded as 'data.tif'
        #locate download
        local_data = filepaths[2] + '\data.tif'
        local_data_pan = filepaths[1] + '\data.tif'
                
        try:
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[2], im_fn['']))
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))
       
        try:
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))
        
       #metadata for .txt file
        filename_txt = im_fn[''].replace('.tif','')
        metadict = {'filename':im_fn[''],
                    'epsg':metadata['bands'][0]['crs'][5:],
                    'dates': str(year),
                    'median_no': sum_img} 
  
        # Sentinel 2 download                
    elif satname == ['S2']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'S2')
        # initialise variables and loop through images
        filenames = []; all_names = [];
        #for year in sat_list:
        median_img = obtain_image_median('COPERNICUS/S2',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),inputs['sat_list'])
        print('Median processed')
          
        #extract year
        first_date = inputs["dates"][0]
        year = first_date[:-6]
        
        im_fn = dict([])
        im_fn[''] = 'S2' + '_' + inputs['sitename'] + '_median_' + year + suffix 
        # if two images taken at the same date add 'dup' to the name (duplicate)
        if any(im_fn[''] in _ for _ in all_names):
            im_fn[''] = 'S2' + '_' + inputs['sitename'] + '_dup' + suffix
        all_names.append(im_fn[''])
        filenames.append(im_fn[''])
        
        ##Extract band metadata and define those to download
        metadata = median_img.getInfo()
        im_bands = metadata['bands']
              
        bands = dict([])
        bands['10m'] = [im_bands[1], im_bands[2], im_bands[3], im_bands[7]] # multispectral bands
        bands['20m'] = [im_bands[11]] # SWIR band
        bands['60m'] = [im_bands[15]] # QA band
           
        #download .tif from EE
        get_url('data', median_img,ee.Number(10), inputs['polygon'], filepaths[1], bands['10m'])
        get_url('data', median_img,ee.Number(20), inputs['polygon'], filepaths[2], bands['20m'])
        get_url('data', median_img, ee.Number(60), inputs['polygon'], filepaths[3], bands['20m'])
        print ('Downloaded')
        
        #rename the file as the image is downloaded as 'data.tif'
        #locate download
        local_data_10m = filepaths[1] + '\data.tif'
        local_data_20m = filepaths[2] + '\data.tif'
        local_data_60m = filepaths[3] + '\data.tif'
                
        try:
            os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['']))
       
        try:
            os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[2], im_fn['']))
            os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['']))
        
        try:
            os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['']))
        except: # overwrite if already exists
            os.remove(os.path.join(filepaths[3], im_fn['']))
            os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['']))
        
       #metadata for .txt file
        filename_txt = im_fn[''].replace('.tif','')
        metadict = {'filename':im_fn[''],
                    'epsg': metadata['bands'][0]['crs'][5:],
                    'dates': str(year),
                    'median_no': sum_img } 
  
    # write metadata
    with open(os.path.join(filepaths[0],filename_txt + '.txt'), 'w') as f:
          for key in metadict.keys():
                f.write('%s\t%s\n'%(key,metadict[key]))                                 
    print('')
             
    # once all images have been downloaded, load metadata from .txt files
    metadata = get_metadata(inputs)
          
    # save metadata dict
    with open(os.path.join(im_folder, inputs['sitename'] + '_metadata' + '.pkl'), 'wb') as f:
        pickle.dump(metadata, f)

    return metadata

def get_url(name, image, scale, region, filepath, bands):
    """It will open and download automatically a zip folder containing Geotiff data of 'image'.
    If additional parameters are needed, see also:
    https://github.com/google/earthengine-api/blob/master/python/ee/image.py

    Parameters:
        name (str): name of the created folder
        image (ee.image.Image): image to export
        scale (int): resolution of export in meters (e.g: 30 for Landsat)
        region (list): region of interest

    Returns:
        path (str)
      """      
      
    path = image.getDownloadURL({
        'name':'data',
        'scale': scale,
        'region': region,
        'filePerBand': False,
        'bands': bands,
        })
    #url = ee.data.makeDownloadUrl(path)
    #print (url)
    local_zip, headers = urlretrieve(path)
    with zipfile.ZipFile(local_zip) as local_zipfile:
        return local_zipfile.extractall(path=str(filepath))

def create_folder_structure(im_folder, sat_list):
    """
    Create the structure of subfolders for each satellite mission
     
    KV WRL 2018       
  
    Arguments:
    -----------
    im_folder: str 
        folder where the images are to be downloaded
    sat_list:
        name of the satellite mission
    
    Returns:
    -----------
    filepaths: list of str
        filepaths of the folders that were created
    """ 
    
    # one folder for the metadata (common to all satellites)
    filepaths = [os.path.join(im_folder, sat_list, 'meta')]
    # subfolders depending on satellite mission
    if sat_list == 'L5':
        filepaths.append(os.path.join(im_folder, sat_list, '30m'))
    elif sat_list in ['L7','L8']:
        filepaths.append(os.path.join(im_folder, sat_list, 'pan'))
        filepaths.append(os.path.join(im_folder, sat_list, 'ms'))
    elif sat_list in ['S2']: 
        filepaths.append(os.path.join(im_folder, sat_list, '10m'))
        filepaths.append(os.path.join(im_folder, sat_list, '20m'))
        filepaths.append(os.path.join(im_folder, sat_list, '60m'))
    # create the subfolders if they don't exist already
    for fp in filepaths: 
        if not os.path.exists(fp): os.makedirs(fp)
    
    return filepaths        

def remove_cloudy_images(im_list, sat_list, prc_cloud_cover=40):
    """
    Removes from the EE collection very cloudy images (>95% cloud cover)

    KV WRL 2018       
   
    Arguments:
    -----------
    im_list: list 
        list of images in the collection
    sat_list:
        name of the satellite mission
    prc_cloud_cover: int
        percentage of cloud cover acceptable on the images
    
    Returns:
    -----------
    im_list_upt: list
        updated list of images
    """
    
    # remove very cloudy images from the collection (>95% cloud)
    if sat_list in ['L5','L7','L8']:
        cloud_property = 'CLOUD_COVER'
    elif sat_list in ['S2']:
        cloud_property = 'CLOUDY_PIXEL_PERCENTAGE'
    cloud_cover = [_['properties'][cloud_property] for _ in im_list]
    if np.any([_ > prc_cloud_cover for _ in cloud_cover]):
        idx_delete = np.where([_ > prc_cloud_cover for _ in cloud_cover])[0]
        im_list_upt = [x for k,x in enumerate(im_list) if k not in idx_delete]
    else:
        im_list_upt = im_list
        
    return im_list_upt

def get_metadata(inputs):
    """
    Gets the metadata from the downloaded images by parsing .txt files located 
    in the \meta subfolder. 
    
    KV WRL 2018
        
    Arguments:
    -----------
    inputs: dict with the following fields
        'sitename': str
            name of the site
        'filepath_data': str
            filepath to the directory where the images are downloaded
    
    Returns:
    -----------
    metadata: dict
        contains the information about the satellite images that were downloaded          
    """
    # directory containing the images
    filepath = os.path.join(inputs['filepath'],inputs['sitename'])
    # initialize metadata dict
    metadata = dict([])
    # loop through the satellite missions
    for sat_list in ['L5','L7','L8','S2']:
        # if a folder has been created for the given satellite mission
        if sat_list in os.listdir(filepath):
            # update the metadata dict
            metadata[sat_list] = {'filenames':[], 'epsg':[], 'dates':[], 'median_no':[]}
            # directory where the metadata .txt files are stored
            filepath_meta = os.path.join(filepath, sat_list, 'meta')
            # get the list of filenames and sort it chronologically
            filenames_meta = os.listdir(filepath_meta)
            filenames_meta.sort()
            # loop through the .txt files
            for im_meta in filenames_meta:
                # read them and extract the metadata info: filename, number of images in median
                # epsg code and date
                with open(os.path.join(filepath_meta, im_meta), 'r') as f:
                    filename = f.readline().split('\t')[1].replace('\n','')
                    epsg = int(f.readline().split('\t')[1].replace('\n',''))
                    dates = int(f.readline().split('\t')[1].replace('\n',''))
                    median_no = int(f.readline().split('\t')[1].replace('\n',''))
                    
                # date_str = filename[0:19]
                # date = pytz.utc.localize(datetime(int(date_str[:4]),int(date_str[5:7]),
                #                                   int(date_str[8:10]),int(date_str[11:13]),
                #                                   int(date_str[14:16]),int(date_str[17:19])))
                # store the information in the metadata dict
                metadata[sat_list]['filenames'].append(filename)
                metadata[sat_list]['median_no'].append(median_no)
                metadata[sat_list]['epsg'].append(epsg)
                metadata[sat_list]['dates'].append(dates)
                
    # save a .pkl file containing the metadata dict
    with open(os.path.join(filepath, inputs['sitename'] + '_metadata' + '.pkl'), 'wb') as f:
        pickle.dump(metadata, f)
    
    return metadata

def Landsat_Coregistration(inputs):
        #Co-register with Sentinel image
        #Find Overlapping cloud-minimal (<20%) image of Landsat 8 and Sentinel 2
        #Landsat 8 image
        L8_reference = ee.ImageCollection('LANDSAT/LC08/C01/T1_TOA')\
                       .filterDate('2017-01-01', '2018-12-01')\
                       .filterBounds(ee.Geometry.Polygon(inputs['polygon']))\
                       .filterMetadata('CLOUD_COVER','less_than', 20)\
                       .sort('system:time_start', False).limit(10)\
                       .first()
        
        L8Red = L8_reference.select(4)
        
         #Sentinel 2 image
        S2_reference = ee.ImageCollection('COPERNICUS/S2')\
                       .filterDate('2017-01-01', '2018-12-01')\
                       .filterBounds(ee.Geometry.Polygon(inputs['polygon']))\
                       .filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than', 20)\
                       .sort('system:time_start', False).limit(10)\
                       .first()
        
        S2Red = S2_reference.select(4)

        #Extract Projection of Landsat 8 image
        proj = L8Red.projection()
        
        #Match the Sentinel 2 resolution with Landsat 8 image
        S2_reduced = S2Red.reduceResolution(reducer = ee.Reducer.mean(), maxPixels = 1024)
        S2_reproject = S2_reduced.reproject(crs=proj)
        
        #Find X and Y components (in meters) of the displacement vector at each pixel.
        displacement = L8Red.displacement(
            referenceImage = S2_reproject,
            maxOffset= 50.0,
            stiffness =10,
            )
        print ('Displacement Calculated')
        
        return displacement
