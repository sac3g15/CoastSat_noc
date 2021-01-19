"""
This module contains all the functions needed to download the satellite images 
from the Google Earth Engine server
    
Author: Kilian Vos, Water Research Laboratory, University of New South Wales
"""

# load modules
import os
import numpy as npypers
import matplotlib.pyplot as plt
import pdb
import numpy as np
# earth engine modules
import ee
from urllib.request import urlretrieve
import zipfile
import copy
from datetime import date
from dateutil.relativedelta import *

# additional modules
from datetime import datetime, timedelta
import pytz
import pickle
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
        ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
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
        print('  %s: %d images'%(sat_list,len(im_list)))
    
        return im_dict_T1, sum_img


def get_s2_sr_cld_col(aoi, start_date, end_date, CLOUD_FILTER):
    """
    ### Build a Sentinel-2 collection

    [Sentinel-2 surface reflectance]
    (https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)
    and [Sentinel-2 cloud probability]
    (https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_CLOUD_PROBABILITY)
    are two different image collections. Each collection must be filtered
    similarly (e.g., by date and bounds) and then the two filtered collections
    must be joined.

    Define a function to filter the SR and s2cloudless collections
    according to area of interest and date parameters, then join them on
    the `system:index` property. The result is a copy of the SR collection
    where each image has a new `'s2cloudless'` property whose value is the
    corresponding s2cloudless image.

    Parameters
    ----------
    aoi : TYPE
        DESCRIPTION.
    start_date : TYPE
        DESCRIPTION.
    end_date : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    ##Print Images in Collection
    #List Images in Collection
    img_list = s2_sr_col.toList(500)
    sum_img = len(img_list.getInfo())
    print ('- Cloud minimal images in Median:')
    print ('   S2: ' + str(sum_img))   

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    })), sum_img
    

def obtain_image_median(collection, time_range, area, satname, settings):
    """ Selection of median from a collection of images in the Earth Engine library
    See also: https://developers.google.com/earth-engine/reducers_image_collection

    Parameters:
        collection (): name of the collection
        time_range (['YYYY-MT-DY','YYYY-MT-DY']): must be inside the available data
        area (ee.geometry.Geometry): area of interest
        satname: Satellite inital; 'L7', 'L8' or 'S2'
        settings: Use of 'LCloudScore' - Mean cloud score value in image. Value 
        between 1-100

    Returns:
        image_median (ee.image.Image)
     """
    collect = ee.ImageCollection(collection)
    
    #Set bands to be extracted
    LC8_BANDS = ['B2',   'B3',    'B4',  'B5',  'B6',    'B7',    'B10', 'BQA'] ## Landsat 8
    LC7_BANDS = ['B1',   'B2',    'B3',  'B4',  'B5',    'B7',    'B6_VCID_2','BQA'] ## Landsat 7
    LC5_BANDS = ['B1',   'B2',    'B3',  'B4',  'B5',    'B7',    'B6', 'BQA'] ## Landsat 5
    STD_NAMES = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'temp', 'BQA']

    if satname == ['L5']:
       ## Filter by time range and location
       collection = (collect.filterDate(time_range[0], time_range[1])
                     .filterBounds(area))

       def LandsatCloudScore(image):
           """ Computes mean cloud score value in a single image in a collection
           
           """
           # Compute a cloud score band.
           cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
           cloudiness = cloud.reduceRegion(
               reducer = 'mean',
               geometry = area,
               scale = 30)
           return image.set(cloudiness)
       
       # Apply Cloud Score layer to each image, then filter collection
       withCloudiness = collection.map(LandsatCloudScore)
       filteredCollection = (withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore']))
                             .select(LC5_BANDS, STD_NAMES))
       
       def LandsatCloudMask(image):
            """
            Creates cloud mask from Landsat Cloud Score and user defined threshold
        
            Parameters
            ----------
                image : image in image collection, defined using .map
        
            Returns
            -------
            masked : image array
                Single masked image within a collection
                
            """    
            # Compute a cloud score band.
            cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
            cloudmask = cloud.lt(settings['LCloudThreshold'])
            masked = image.updateMask(cloudmask)            
            return masked
       
       # Apply cloud masking to all images within collection then select bands
       maskedcollection = filteredCollection.map(LandsatCloudMask)
       filteredCollection_masked = maskedcollection.select(LC7_BANDS, STD_NAMES)
       
       ##Print Images in Collection
       #List Images in Collection
       img_list = filteredCollection.toList(500)
       img_count = len(img_list.getInfo())
       print ('- Cloud minimal images in Median:')
       print ('   L5: ' + str(img_count))       
       
       if settings['add_L7_to_L5'] == True:

           #Add Landsat 7 to Collection
           collect = ee.ImageCollection('LANDSAT/LE07/C01/T1_TOA')           
           ## Filter by time range and location
           L7_collection = (collect.filterDate(time_range[0], time_range[1])
                      .filterBounds(area))

           def LandsatCloudScore(L7_image):
                """ Computes mean cloud score value in a single image in a collection
                
                """
                # Compute a cloud score band.
                L7_cloud = ee.Algorithms.Landsat.simpleCloudScore(L7_image).select('cloud')
                L7_cloudiness = L7_cloud.reduceRegion(
                    reducer = 'mean',
                    geometry = area,
                    scale = 30)                
                return L7_image.set(L7_cloudiness)

           # Apply Cloud Score layer to each image, then filter collection            
           L7_withCloudiness = L7_collection.map(LandsatCloudScore)
           L7_filteredCollection = (L7_withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore']))
                                    .select(LC7_BANDS, STD_NAMES))
           def LandsatCloudMask(image):
                """
                Creates cloud mask from Landsat Cloud Score and user defined threshold
            
                Parameters
                ----------
                    image : image in image collection, defined using .map
            
                Returns
                -------
                masked : image array
                    Single masked image within a collection
                    
                """    
                # Compute a cloud score band.
                cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
                cloudmask = cloud.lt(settings['LCloudThreshold'])
                masked = image.updateMask(cloudmask)            
                return masked
       
           # Apply cloud masking to all images within collection then select bands
           maskedcollection = filteredCollection.map(LandsatCloudMask)
           filteredCollection_masked = maskedcollection.select(LC7_BANDS, STD_NAMES) 
           
           ##Print Images in Collection
           #List Images in Collection           
           L7_img_list = L7_filteredCollection.toList(500)
           L7_count = len(L7_img_list.getInfo())
           print ('   L7: ' + str(L7_count))
           
           # Merge collection with Landsat 5
           combined_collection = filteredCollection.merge(L7_filteredCollection)
           image_median = combined_collection.median()
           sum_img = img_count + L7_count
           print ('   Total: ' + str(img_count + L7_count))
                  
       else:
           #Take median of Collection
           image_median = filteredCollection.median()
           sum_img = img_count
           print ('   Total: ' + str(img_count))
       
       return image_median, sum_img

 
    if satname == ['L7']:
       ## Filter by time range and location
       collection = (collect.filterDate(time_range[0], time_range[1])
                     .filterBounds(area))

       def LandsatCloudScore(image):
            """ Computes mean cloud score value in a single image in a collection
           
            """
            # Compute a cloud score band.
            cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
            cloudiness = cloud.reduceRegion(
                reducer = 'mean',
                geometry = area,
                scale = 30)
            return image.set(cloudiness)
        
       # Apply Cloud Score layer to each image, then filter collection
       withCloudiness = collection.map(LandsatCloudScore)
       filteredCollection_no_pan = (withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore'])))     

       def LandsatCloudMask(image):
            """
            Creates cloud mask from Landsat Cloud Score and user defined threshold
        
            Parameters
            ----------
                image : image in image collection, defined using .map
        
            Returns
            -------
            masked : image array
                Single masked image within a collection
                
            """    
            # Compute a cloud score band.
            cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
            cloudmask = cloud.lt(settings['LCloudThreshold'])
            masked = image.updateMask(cloudmask)            
            return masked
       
       # Apply cloud masking to all images within collection then select bands
       maskedcollection = filteredCollection_no_pan.map(LandsatCloudMask)
       filteredCollection_masked = maskedcollection.select(LC7_BANDS, STD_NAMES)
       
       ##Print Images in Collection
       #List Images in Collection
       img_list = filteredCollection_no_pan.toList(500)
       img_count = len(img_list.getInfo())
       print ('- Cloud minimal images in Median:')
       print ('   L7: ' + str(img_count))       
       
       if settings['add_L5_to_L7'] == True:
           
           #Add Landsat 7 to Collection
           collect = ee.ImageCollection('LANDSAT/LT05/C01/T1_TOA')           
           ## Filter by time range and location
           L5_collection = (collect.filterDate(time_range[0], time_range[1])
                      .filterBounds(area))

           def LandsatCloudScore(L5_image):
                """ Computes mean cloud score value in a single image in a collection
                
                """
                # Compute a cloud score band.
                L5_cloud = ee.Algorithms.Landsat.simpleCloudScore(L5_image).select('cloud')
                L5_cloudiness = L5_cloud.reduceRegion(
                    reducer = 'mean',
                    geometry = area,
                    scale = 30)
                
                return L5_image.set(L5_cloudiness)
            
           L5_withCloudiness = L5_collection.map(LandsatCloudScore)
           L5_filteredCollection = (L5_withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore']))
                                    .select(LC5_BANDS, STD_NAMES))
           ##Print Images in Collection
           #List Images in Collection
           L5_img_list = L5_filteredCollection.toList(500)
           L5_count = len(L5_img_list.getInfo())
           print ('   L5: ' + str(L5_count))
           
           def LandsatCloudMask(image):
                """
                Creates cloud mask from Landsat Cloud Score and user defined threshold
            
                Parameters
                ----------
                    image : image in image collection, defined using .map
            
                Returns
                -------
                masked : image array
                    Single masked image within a collection
                    
                """    
                # Compute a cloud score band.
                cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
                cloudmask = cloud.lt(settings['LCloudThreshold'])
                masked = image.updateMask(cloudmask)            
                return masked

           if L5_count > 0:
               
               # Apply cloud masking to all images within collection then select bands
               maskedcollection = filteredCollection_no_pan.map(LandsatCloudMask)
               filteredCollection_masked = maskedcollection.select(LC7_BANDS, STD_NAMES)
                          
               # Merge Collections
               filteredCollection_masked = filteredCollection_masked.merge(L5_filteredCollection)
               sum_img = img_count + L5_count
               print ('   Total: ' + str(sum_img))
           else:
               sum_img = img_count
               print ('   Total: ' + str(sum_img))
               pass
                  
               
       # Take median of Collection
       image_median_no_pan = filteredCollection_masked.median()

                       
       ## Add panchromatic band to collection from Landsat 7
       # Add Panchromatic Band
       panchromatic = ['B8']
       panchromatic_name = ['pan']
       filteredCollection_pan = (withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore'])))
        
       # Repeat masking process and take median
       maskedcollection_pan = filteredCollection_pan.map(LandsatCloudMask)
       filteredCollection_masked_pan = maskedcollection_pan.select(panchromatic, panchromatic_name)
       img_median_pan = filteredCollection_masked_pan.median()
        
       # Combine multiplspectral and panchromatic bands
       image_median = image_median_no_pan.addBands(img_median_pan)
           
       return image_median, sum_img
   
    if satname == ['L8']:
       ## Filter by time range and location
       L8_collection = (collect.filterDate(time_range[0], time_range[1])
                     .filterBounds(area))

       def LandsatCloudScore(image):
           """ Computes mean cloud score value in a single image in a collection
           
           """
           # Compute a cloud score band.
           L8_cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
           L8_cloudiness = L8_cloud.reduceRegion(
               reducer = 'mean',
               geometry = area,
               scale = 30)
           return image.set(L8_cloudiness)
       
       # Apply cloud masking to all images within collection then select bands       
       L8_withCloudiness = L8_collection.map(LandsatCloudScore)
       L8_filteredCollection = (L8_withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore'])))   

       def LandsatCloudMask(image):
             """
             Creates cloud mask from Landsat Cloud Score and user defined threshold
         
             Parameters
             ----------
                 image : image in image collection, defined using .map
         
             Returns
             -------
             masked : image array
                 Single masked image within a collection
                 
             """    
             # Compute a cloud score band.
             cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
             cloudmask = cloud.lt(settings['LCloudThreshold'])
             masked = image.updateMask(cloudmask)            
             return masked
       
        
       ## Need to add panchromatic band to collection
       #Add Panchromatic Band
       panchromatic = ['B8']
       panchromatic_name = ['pan']
       
       # Apply cloud masking to all images within collection then select bands
       maskedcollection = L8_filteredCollection.map(LandsatCloudMask)
       filteredCollection_masked = maskedcollection.select(LC8_BANDS + panchromatic , STD_NAMES + panchromatic_name)
       
       ##Print Images in Collection
       #List Images in Collection
       img_list = L8_filteredCollection.toList(500)
       img_count = len(img_list.getInfo())
       print ('- Cloud minimal images in Median:')
       print ('   L8: ' + str(img_count))       
       
       if settings['add_L7_to_L8'] == True:
           
           #Add Landsat 7 to Collection
           collect = ee.ImageCollection('LANDSAT/LE07/C01/T1_TOA')           
           ## Filter by time range and location
           L7_collection = (collect.filterDate(time_range[0], time_range[1])
                      .filterBounds(area))

           def LandsatCloudScore(L7_image):
                """ Computes mean cloud score value in a single image in a collection
                
                """
                # Compute a cloud score band.
                L7_cloud = ee.Algorithms.Landsat.simpleCloudScore(L7_image).select('cloud')
                L7_cloudiness = L7_cloud.reduceRegion(
                    reducer = 'mean',
                    geometry = area,
                    scale = 30)
                
                return L7_image.set(L7_cloudiness)
            
           # Apply cloud masking to all images within collection then select bands       
           L7_withCloudiness = L7_collection.map(LandsatCloudScore)
           L7_filteredCollection = (L7_withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore'])))   
                
           def LandsatCloudMask(image):
                 """
                 Creates cloud mask from Landsat Cloud Score and user defined threshold
             
                 Parameters
                 ----------
                     image : image in image collection, defined using .map
             
                 Returns
                 -------
                 masked : image array
                     Single masked image within a collection
                     
                 """    
                 # Compute a cloud score band.
                 cloud = ee.Algorithms.Landsat.simpleCloudScore(image).select('cloud')
                 cloudmask = cloud.lt(settings['LCloudThreshold'])
                 masked = image.updateMask(cloudmask)            
                 return masked
           
           # Apply cloud masking to all images within collection then select bands
           maskedcollection = L7_filteredCollection.map(LandsatCloudMask)
           L7_filteredCollection_masked = maskedcollection.select(LC7_BANDS + panchromatic, STD_NAMES + panchromatic_name)  
           
           ## Print Images in Collection
           # List Images in Collection
           L7_img_list = L7_filteredCollection.toList(500)
           L7_count = len(L7_img_list.getInfo())
           print ('   L7: ' + str(L7_count))
           
           # Merge Collections
           filteredCollection = filteredCollection_masked.merge(L7_filteredCollection_masked)
           sum_img = img_count + L7_count
           print ('   Total: ' + str(img_count + L7_count))
                  
       else:
           sum_img = img_count
           print ('   Total: ' + str(img_count))
           pass
       
       #Take median of Collection
       image_median = filteredCollection.median()

       
       return image_median, sum_img

    elif satname == ['S2']:
        
        def add_cloud_bands(img):
            """
            Cloud components
            Define a function to add the s2cloudless probability layer and
            derived cloud mask as bands to an S2 SR image input.
        
            Parameters
            ----------
            img : TYPE
                DESCRIPTION.
        
            Returns
            -------
            TYPE
                DESCRIPTION.
        
            """
            # Get s2cloudless image, subset the probability band.
            cld_prb = ee.Image(img.get('s2cloudless')).select('probability')
        
            # Condition s2cloudless by the probability threshold value.
            is_cloud = cld_prb.gt(settings['CLD_PRB_THRESH']).rename('clouds')
        
            # Add the cloud probability layer and cloud mask as image bands.
            return img.addBands(ee.Image([cld_prb, is_cloud]))
        
        def add_shadow_bands(img):
            """
            #### Cloud shadow components
        
            Define a function to add dark pixels, cloud projection, and identified
            shadows as bands to an S2 SR image input. Note that the image input needs
            to be the result of the above `add_cloud_bands` function because it
            relies on knowing which pixels are considered cloudy (`'clouds'` band).
        
            Parameters
            ----------
            img : TYPE
                DESCRIPTION.
        
            Returns
            -------
            TYPE
                DESCRIPTION.
        
            """
            # Identify water pixels from the SCL band.
            not_water = img.select('SCL').neq(6)
        
            # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
            SR_BAND_SCALE = 1e4
            dark_pixels = img.select('B8').lt(settings['NIR_DRK_THRESH']*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')
        
            # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
            shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));
        
            # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
            cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, settings['CLD_PRJ_DIST']*10)
                .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
                .select('distance')
                .mask()
                .rename('cloud_transform'))
        
            # Identify the intersection of dark pixels with cloud shadow projection.
            shadows = cld_proj.multiply(dark_pixels).rename('shadows')
        
            # Add dark pixels, cloud projection, and identified shadows as image bands.
            return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))
        
        def add_cld_shdw_mask(img):
            """
            #### Final cloud-shadow mask
        
            Define a function to assemble all of the cloud and cloud shadow components and produce the final mask.
        
            """
            
            # Add cloud component bands.
            img_cloud = add_cloud_bands(img)
        
            # Add cloud shadow component bands.
            img_cloud_shadow = add_shadow_bands(img_cloud)
        
            # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
            is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)
        
            # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
            # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
            is_cld_shdw = (is_cld_shdw.focal_min(2).focal_max(settings['BUFFER']*2/20)
                .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
                .rename('cloudmask'))
        
            # Add the final cloud-shadow mask to the image.
            return img_cloud_shadow.addBands(is_cld_shdw)
        
        def apply_cld_shdw_mask(img):
            """
            ### Define cloud mask application function
        
            Define a function to apply the cloud mask to each image in the collection.
            
            """
            # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
            not_cld_shdw = img.select('cloudmask').Not()
        
            # Subset reflectance bands and update their masks, return the result.
            return img.select('B.*').updateMask(not_cld_shdw)
        
        s2_sr_cld_col, sum_img = get_s2_sr_cld_col(area, time_range[0], time_range[1], settings['CLOUD_FILTER'])
        image_median = (s2_sr_cld_col.map(add_cld_shdw_mask)
                             .map(apply_cld_shdw_mask)
                             .median())
        
        # collection_time = collect.filterDate(time_range[0], time_range[1])
        # image_area = collection_time.filterBounds(area)
        # image_2 = image_area.filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than', 40)
        # image_median = image_2.median()
        return image_median, sum_img 

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
        median_img, sum_img = obtain_image_median('LANDSAT/LT05/C01/T1_TOA',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),inputs['sat_list'], settings)
      
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
        bands[''] = ['blue', 'green', 'red', 'nir','swir1','BQA']

        if settings['coregistration'] == True:

            displacement = Landsat_Coregistration(inputs)
            print ('displacement calculated')
    
            #Apply XY displacement values from overlapping images to the median composite
            registered = median_img.displace(displacement, mode="bicubic")     
            print ('Registered')
            
            # download .tif from EE
            get_url('data', registered, 30, inputs['polygon'], filepaths[1], bands[''])
            print ('Downloaded')
        
        else:
            # download .tif from EE
            get_url('data', median_img, ee.Number(30), inputs['polygon'], filepaths[1], bands[''])
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
        median_img, sum_img = obtain_image_median('LANDSAT/LE07/C01/T1_TOA',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),
                                         inputs['sat_list'],
                                         settings)
        
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
        bands['pan'] = ['pan'] # panchromatic band
        bands['ms'] = ['blue', 'green', 'red', 'nir','swir1','BQA']
        
        if settings['coregistration'] == True:
            displacement = Landsat_Coregistration(inputs)
            
            #Apply XY displacement values from overlapping images to the median composite
            registered = median_img.displace(displacement, mode="bicubic")     
            print ('Co-registered')
         
            #download .tif from EE
            get_url('data', registered, 30, inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', registered, 15, inputs['polygon'], filepaths[1], bands['pan'])
            print ('Downloaded')
        else:
            #download .tif from EE
            get_url('data', median_img, ee.Number(30), inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', median_img, ee.Number(15), inputs['polygon'], filepaths[1], bands['pan'])
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
        median_img, sum_img = obtain_image_median('LANDSAT/LC08/C01/T1_TOA',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),inputs['sat_list'],
                                         settings)
        
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
        bands['pan'] = ['pan'] # panchromatic band
        bands['ms'] = ['blue', 'green', 'red', 'nir','swir1','BQA']
        
        if settings['coregistration'] == True:
       
            displacement = Landsat_Coregistration(inputs)
    
            #Apply XY displacement values from overlapping images to the median composite
            registered = median_img.displace(displacement, mode="bicubic")     
            print ('Co-registered')
                    
            #download .tif from EE
            get_url('data', registered, 30, inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', registered, 15, inputs['polygon'], filepaths[1], bands['pan'])
            print ('Downloaded')
            
        else:
             #download .tif from EE
            get_url('data', median_img, ee.Number(30), inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', median_img, ee.Number(15), inputs['polygon'], filepaths[1], bands['pan'])
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
        median_img, sum_img = obtain_image_median('COPERNICUS/S2',
                                         inputs['dates'],
                                         ee.Geometry.Polygon(inputs['polygon']),inputs['sat_list'],
                                         settings)
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
        #im_bands = metadata['bands']
              
        bands = dict([])
        bands['10m'] = ['B2', 'B3', 'B4', 'B8'] # multispectral bands
        bands['20m'] = ['B12'] # SWIR band
        bands['60m'] = ['QA60'] # QA band
           
        #download .tif from EE
        get_url('data', median_img, ee.Number(10), inputs['polygon'], filepaths[1], bands['10m'])
        get_url('data', median_img, ee.Number(20), inputs['polygon'], filepaths[2], bands['20m'])
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
        'bands': bands
        })

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
        #Find Overlapping cloud-minimal image of Landsat 8 and Sentinel 2
        #Landsat 8 image
        L8_reference = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')\
                        .filterDate('2017-03-28', '9999-03-01')\
                        .filterBounds(ee.Geometry.Polygon(inputs['polygon']))\
                        .filterMetadata('CLOUD_COVER','less_than', 50)\
                        .sort('CLOUD_COVER')\
                        .first()\
                        .select('B2','B3','B4')


        # Extract Date and find S2 image within 4 months
        cloud = L8_reference.get('CLOUD_COVER').getInfo()
        time = (L8_reference.get('system:index').getInfo())
        year = time[12:16]
        month = time[16:18]
        day = time[18:20]
        L8_date = datetime(int(year), int(month), int(day))
        #print('Landsat co-registration (slave) image date: ', L8_date)
        print('Landsat co-registration (slave) image cloud cover: ', cloud)        
        s2_start_date = L8_date + relativedelta(months=-3)
        s2_end_date = L8_date + relativedelta(months=+3)
        
        #Sentinel 2 image
        S2_reference = ee.ImageCollection('COPERNICUS/S2_SR')\
            .filterDate(str(s2_start_date)[:10], str(s2_end_date)[:10])\
            .filterBounds(ee.Geometry.Polygon(inputs['polygon']))\
            .filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than', 50)\
            .sort('CLOUDY_PIXEL_PERCENTAGE')\
            .first()\
            .select('B2','B3','B4')
        
        cloud = S2_reference.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        # time = (S2_reference.get('system:index').getInfo())
        # print(time)
        # year = time[0:3]
        # month = time[3:6]
        # day = time[6:8]
        # s2_date = datetime(int(year), int(month), int(day))
        # print('Sentinel co-registration (master) image date: ', s2_date)    
        print('Sentinel co-registration (master) image cloud cover: ', cloud)
        
        #Extract Projection of Landsat 8 image
        proj = L8_reference.projection()
        
        #Match the Sentinel 2 resolution with Landsat 8 image
        S2_reduced = S2_reference.reduceResolution(reducer = ee.Reducer.mean(), maxPixels = 1024)
        S2_reproject = S2_reduced.reproject(crs=proj)
        
        #Find X and Y components (in meters) of the displacement vector at each pixel.
        displacement = L8_reference.displacement(
            referenceImage = S2_reproject,
            maxOffset= 50.0,
            stiffness = 10,
            )

        return displacement
