from coastsat.SDS_download import *


def retrieve_images(inputs):
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
    im_dict_T1 = check_images_available(inputs)

    # create a new directory for this site with the name of the site
    im_folder = os.path.join(inputs['filepath'], inputs['sitename'])
    if not os.path.exists(im_folder): os.makedirs(im_folder)

    suffix = '.tif'

    for satname in im_dict_T1.keys():

        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, satname)
        # initialise variables and loop through images
        georef_accs = []
        filenames = []
        all_names = []
        im_epsg = []

        for i in range(15):

            ## least cloudy is first image
            im_meta = im_dict_T1[satname][i]

            print(f'    date : {im_meta["properties"]["DATATAKE_IDENTIFIER"][5:13]}')
            print(f'    cloud: {im_meta["properties"]["CLOUDY_PIXEL_PERCENTAGE"]:3.1f}%')

            # get time of acquisition (UNIX time) and convert to datetime
            t = im_meta['properties']['system:time_start']
            im_timestamp = datetime.fromtimestamp(t / 1000, tz=pytz.utc)
            im_date = im_timestamp.strftime('%Y-%m-%d-%H-%M-%S')

            # get epsg code
            im_epsg.append(int(im_meta['bands'][0]['crs'][5:]))

            # Sentinel-2 products don't provide a georeferencing accuracy (RMSE as in Landsat)
            # but they have a flag indicating if the geometric quality control was passed or failed
            # if passed a value of 1 is stored if failed a value of -1 is stored in the metadata
            # the name of the property containing the flag changes across the S2 archive
            # check which flag name is used for the image and store the 1/-1 for acc_georef
            flag_names = ['GEOMETRIC_QUALITY_FLAG', 'GEOMETRIC_QUALITY', 'quality_check']
            for key in flag_names:
                if key in im_meta['properties'].keys(): break
            if im_meta['properties'][key] == 'PASSED':
                acc_georef = 1
            else:
                acc_georef = -1

            georef_accs.append(acc_georef)

            bands = {}
            im_fn = {}

            # first delete dimensions key from dictionnary
            # otherwise the entire image is extracted (don't know why)
            im_bands = im_meta['bands']
            for j in range(len(im_bands)):
                del im_bands[j]['dimensions']

            bands['10m'] = [im_bands[1], im_bands[2], im_bands[3], im_bands[7]]  # multispectral bands
            bands['20m'] = [im_bands[11]]  # SWIR band
            bands['60m'] = [im_bands[15]]  # QA band

            for key in bands.keys():
                im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + suffix

            # check for 2 or 3 images taken on the same date
            # and add 'dup' or 'tri' to the name respectively
            if any(im_fn['10m'] in _ for _ in all_names):
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + '_dup' + suffix

                if im_fn['10m'] in all_names:
                    for key in bands.keys():
                        im_fn[key] = im_date + '_' + satname + '_' + inputs[
                            'sitename'] + '_' + key + '_tri' + suffix

            all_names.append(im_fn['10m'])
            filenames.append(im_fn['10m'])

            # download .tif from EE (multispectral bands at 3 different resolutions)
            while True:
                try:
                    im_ee = ee.Image(im_meta['id'])
                    local_data_10m = download_tif(im_ee, inputs['polygon'], bands['10m'], filepaths[1])
                    local_data_20m = download_tif(im_ee, inputs['polygon'], bands['20m'], filepaths[2])
                    local_data_60m = download_tif(im_ee, inputs['polygon'], bands['60m'], filepaths[3])
                    break
                except:
                    continue
            # rename the files as the image is downloaded as 'data.tif'
            try:  # 10m
                os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['10m']))
            except:  # overwrite if already exists
                os.remove(os.path.join(filepaths[1], im_fn['10m']))
                os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['10m']))
            try:  # 20m
                os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['20m']))
            except:  # overwrite if already exists
                os.remove(os.path.join(filepaths[2], im_fn['20m']))
                os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['20m']))
            try:  # 60m
                os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['60m']))
            except:  # overwrite if already exists
                os.remove(os.path.join(filepaths[3], im_fn['60m']))
                os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['60m']))
            # metadata for .txt file
            filename_txt = im_fn['10m'].replace('_10m', '').replace('.tif', '')
            metadict = {'filename': im_fn['10m'], 'acc_georef': georef_accs[i],
                        'epsg': im_epsg[i]}

            # write metadata
            with open(os.path.join(filepaths[0], filename_txt + '.txt'), 'w') as f:
                for key in metadict.keys():
                    f.write('%s\t%s\n' % (key, metadict[key]))

    # once all images have been downloaded, load metadata from .txt files
    metadata = get_metadata(inputs)

    # save metadata dict
    with open(os.path.join(im_folder, inputs['sitename'] + '_metadata' + '.pkl'), 'wb') as f:
        pickle.dump(metadata, f)

    return metadata


def check_training_images_available(inputs):
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

    # check if dates are in correct order
    dates = [datetime.strptime(_,'%Y-%m-%d') for _ in inputs['dates']]
    if  dates[1] <= dates[0]:
        raise Exception('Verify that your dates are in the correct order')

    # check if EE was initialised or not
    try:
        ee.ImageCollection('LANDSAT/LT05/C01/T1_TOA')
    except:
        ee.Initialize()

    # check how many images are available in Tier 1 and Sentinel Level-1C
    col_names_T1 = {'L5':'LANDSAT/LT05/C01/T1_TOA',
                 'L7':'LANDSAT/LE07/C01/T1_TOA',
                 'L8':'LANDSAT/LC08/C01/T1_TOA',
                 'S2':'COPERNICUS/S2'}

    im_dict_T1 = {}
    for satname in inputs['sat_list']:

        print(satname)
        print(inputs['polygon'])
        print(inputs['dates'])

        # get list of images in EE collection
        while True:
            try:

                ee_col = ee.ImageCollection(col_names_T1[satname])\
                            .filterBounds(ee.Geometry.Polygon(inputs['polygon'])) \
                            .filterDate(inputs['dates'][0],inputs['dates'][1]) \
                            .sort('CLOUDY_PIXEL_PERCENTAGE')

                im_list = ee_col.getInfo().get('features')
                break
            except:
                continue

        im_dict_T1[satname] = im_list

    return im_dict_T1


def obtain_median_image(collection, time_range, area, satname, settings):
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

    # Set bands to be extracted
    LC8_BANDS = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10', 'BQA']  ## Landsat 8
    LC7_BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6_VCID_2', 'BQA']  ## Landsat 7
    LC5_BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6', 'BQA']  ## Landsat 5
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
                reducer='mean',
                geometry=area,
                scale=30)
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
        # List Images in Collection
        img_list = filteredCollection.toList(500)
        img_count = len(img_list.getInfo())
        print('- Cloud minimal images in Median:')
        print('   L5: ' + str(img_count))

        if settings['add_L7_to_L5'] == True:

            # Add Landsat 7 to Collection
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
                    reducer='mean',
                    geometry=area,
                    scale=30)
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
            # List Images in Collection
            L7_img_list = L7_filteredCollection.toList(500)
            L7_count = len(L7_img_list.getInfo())
            print('   L7: ' + str(L7_count))

            # Merge collection with Landsat 5
            combined_collection = filteredCollection.merge(L7_filteredCollection)
            image_median = combined_collection.median()
            sum_img = img_count + L7_count
            print('   Total: ' + str(img_count + L7_count))

        else:
            # Take median of Collection
            image_median = filteredCollection.median()
            sum_img = img_count
            print('   Total: ' + str(img_count))

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
                reducer='mean',
                geometry=area,
                scale=30)
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
        # List Images in Collection
        img_list = filteredCollection_no_pan.toList(500)
        img_count = len(img_list.getInfo())
        print('- Cloud minimal images in Median:')
        print('   L7: ' + str(img_count))

        if settings['add_L5_to_L7'] == True:

            # Add Landsat 7 to Collection
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
                    reducer='mean',
                    geometry=area,
                    scale=30)

                return L5_image.set(L5_cloudiness)

            L5_withCloudiness = L5_collection.map(LandsatCloudScore)
            L5_filteredCollection = (L5_withCloudiness.filter(ee.Filter.lt('cloud', settings['LCloudScore']))
                                     .select(LC5_BANDS, STD_NAMES))
            ##Print Images in Collection
            # List Images in Collection
            L5_img_list = L5_filteredCollection.toList(500)
            L5_count = len(L5_img_list.getInfo())
            print('   L5: ' + str(L5_count))

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
                print('   Total: ' + str(sum_img))
            else:
                sum_img = img_count
                print('   Total: ' + str(sum_img))
                pass
        else:
            sum_img = img_count
            print('   Total: ' + str(sum_img))

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
                reducer='mean',
                geometry=area,
                scale=30)
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
        # Add Panchromatic Band
        panchromatic = ['B8']
        panchromatic_name = ['pan']

        # Apply cloud masking to all images within collection then select bands
        maskedcollection = L8_filteredCollection.map(LandsatCloudMask)
        filteredCollection_masked = maskedcollection.select(LC8_BANDS + panchromatic, STD_NAMES + panchromatic_name)

        ##Print Images in Collection
        # List Images in Collection
        img_list = L8_filteredCollection.toList(500)
        img_count = len(img_list.getInfo())
        print('- Cloud minimal images in Median:')
        print('   L8: ' + str(img_count))

        if settings['add_L7_to_L8'] == True:

            # Add Landsat 7 to Collection
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
                    reducer='mean',
                    geometry=area,
                    scale=30)

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
            L7_filteredCollection_masked = maskedcollection.select(LC7_BANDS + panchromatic,
                                                                   STD_NAMES + panchromatic_name)

            ## Print Images in Collection
            # List Images in Collection
            L7_img_list = L7_filteredCollection.toList(500)
            L7_count = len(L7_img_list.getInfo())
            print('   L7: ' + str(L7_count))

            # Merge Collections
            L8_filteredCollection = filteredCollection_masked.merge(L7_filteredCollection_masked)
            sum_img = img_count + L7_count
            print('   Total: ' + str(img_count + L7_count))

        else:
            sum_img = img_count
            print('   Total: ' + str(img_count))
            pass

        # Take median of Collection
        image_median = L8_filteredCollection.median()

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
            dark_pixels = img.select('B8').lt(settings['NIR_DRK_THRESH'] * SR_BAND_SCALE).multiply(not_water).rename(
                'dark_pixels')

            # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
            shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

            # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
            cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, settings['CLD_PRJ_DIST'] * 10)
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

            # End date from user input range
            user_end = time_range[0].split("-")
            # Period of Sentinel 2 data before Surface reflectance data is available
            start = datetime(2015, 6, 23)
            end = datetime(2019, 1, 28)

            # Is start date within pre S2_SR period?
            if time_in_range(start, end, datetime(int(user_end[0]), int(user_end[1]), int(user_end[2]))) == False:
                # Add cloud shadow component bands.
                img_cloud_shadow = add_shadow_bands(img_cloud)
                # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
                is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

            else:
                # Add cloud shadow component bands.
                img_cloud_shadow = img_cloud
                # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
                is_cld_shdw = img_cloud.select('clouds').gt(0)

            # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
            # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
            is_cld_shdw = (is_cld_shdw.focal_min(2).focal_max(settings['BUFFER'] * 2 / 20)
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

        # Build masks and apply to S2 image
        s2_sr_cld_col, sum_img = get_s2_sr_cld_col(area, time_range[0], time_range[1], settings['CLOUD_FILTER'])

        image_median = (s2_sr_cld_col.map(add_cld_shdw_mask)
                        .map(apply_cld_shdw_mask)
                        .median())

        # collection_time = collect.filterDate(time_range[0], time_range[1])
        # image_area = collection_time.filterBounds(area)
        # image_2 = image_area.filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than', 40)
        # image_median = image_2.median()
        return image_median, sum_img


def retrieve_median_image(settings, inputs):
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

    #inputs = settings['inputs']

    # initialise connection with GEE server
    ee.Initialize()

    # create a new directory for this site with the name of the site
    im_folder = os.path.join(inputs['filepath'], inputs['sitename'])
    if not os.path.exists(im_folder): os.makedirs(im_folder)

    print('\nDownloading images:')
    suffix = '.tif'
    satname = inputs['sat_list']

    # Landsat 5 download
    if satname == ['L5']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'L5')
        # initialise variables and loop through images
        filenames = [];
        all_names = [];
        # for year in sat_list:
        median_img, sum_img = obtain_median_image('LANDSAT/LT05/C01/T1_TOA',
                                                  inputs['dates'],
                                                  ee.Geometry.Polygon(inputs['polygon']),
                                                  inputs['sat_list'],
                                                  settings)

        print('Median Processed')
        # extract year
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
        bands[''] = ['blue', 'green', 'red', 'nir', 'swir1', 'BQA']

        if settings['coregistration'] == True:

            displacement = Landsat_Coregistration(inputs)
            print('displacement calculated')

            # Apply XY displacement values from overlapping images to the median composite
            registered = median_img.displace(displacement, mode="bicubic")
            print('Registered')

            # download .tif from EE
            get_url('data', registered, 30, inputs['polygon'], filepaths[1], bands[''])
            print('Downloaded')

        else:
            # download .tif from EE
            get_url('data', median_img, ee.Number(30), inputs['polygon'], filepaths[1], bands[''])
            print('Downloaded')

            # rename the file as the image is downloaded as 'data.tif'
        # locate download
        local_data = filepaths[1] + '\data.tif'

        try:
            os.rename(local_data, os.path.join(filepaths[1], im_fn['']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data, os.path.join(filepaths[1], im_fn['']))
        # metadata for .txt file
        filename_txt = im_fn[''].replace('.tif', '')
        metadict = {'filename': im_fn[''],
                    'epsg': metadata['bands'][0]['crs'][5:],
                    'start_date': inputs['dates'][0],
                    'end_date': inputs['dates'][1],
                    'median_no': sum_img}

    # Landsat 7 download
    elif satname == ['L7']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'L7')
        # initialise variables and loop through images
        filenames = [];
        all_names = [];
        # for year in sat_list:
        median_img, sum_img = obtain_median_image('LANDSAT/LE07/C01/T1_TOA',
                                                  inputs['dates'],
                                                  ee.Geometry.Polygon(inputs['polygon']),
                                                  inputs['sat_list'],
                                                  settings)

        print('Median Processed')
        # extract year
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
        bands['pan'] = ['pan']  # panchromatic band
        bands['ms'] = ['blue', 'green', 'red', 'nir', 'swir1', 'BQA']

        if settings['coregistration'] == True:
            displacement = Landsat_Coregistration(inputs)

            # Apply XY displacement values from overlapping images to the median composite
            registered = median_img.displace(displacement, mode="bicubic")
            print('Co-registered')

            # download .tif from EE
            get_url('data', registered, 30, inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', registered, 15, inputs['polygon'], filepaths[1], bands['pan'])
            print('Downloaded')
        else:
            # download .tif from EE
            get_url('data', median_img, ee.Number(30), inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', median_img, ee.Number(15), inputs['polygon'], filepaths[1], bands['pan'])
            print('Downloaded')

            # rename the file as the image is downloaded as 'data.tif'
        # locate download
        local_data = filepaths[2] + '\data.tif'
        local_data_pan = filepaths[1] + '\data.tif'

        try:
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[2], im_fn['']))
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))

        try:
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))

        # metadata for .txt file
        filename_txt = im_fn[''].replace('.tif', '')
        metadict = {'filename': im_fn[''],
                    'epsg': metadata['bands'][0]['crs'][5:],
                    'start_date': inputs['dates'][0],
                    'end_date': inputs['dates'][1],
                    'median_no': sum_img}

        # Landsat 8 download
    elif satname == ['L8']:
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'L8')
        # initialise variables and loop through images
        filenames = [];
        all_names = [];
        # for year in sat_list:
        median_img, sum_img = obtain_median_image('LANDSAT/LC08/C01/T1_TOA',
                                                  inputs['dates'],
                                                  ee.Geometry.Polygon(inputs['polygon']), inputs['sat_list'],
                                                  settings)

        print('Median Processed')
        # extract year
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

        if settings['add_L7_to_L8'] == False:

            bands = dict([])
            bands['pan'] = ['B8']  # panchromatic band
            bands['ms'] = ['B2', 'B3', 'B4', 'B5', 'B6', 'BQA']
        else:
            bands = dict([])
            bands['pan'] = ['pan']  # panchromatic band
            bands['ms'] = ['blue', 'green', 'red', 'nir', 'swir1', 'BQA']

        if settings['coregistration'] == True:

            displacement = Landsat_Coregistration(inputs)

            # Apply XY displacement values from overlapping images to the median composite
            registered = median_img.displace(displacement, mode="bicubic")
            print('Co-registered')

            # download .tif from EE
            get_url('data', registered, 30, inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', registered, 15, inputs['polygon'], filepaths[1], bands['pan'])
            print('Downloaded')

        else:
            # download .tif from EE
            get_url('data', median_img, ee.Number(30), inputs['polygon'], filepaths[2], bands['ms'])
            get_url('data', median_img, ee.Number(15), inputs['polygon'], filepaths[1], bands['pan'])
            print('Downloaded')

            # rename the file as the image is downloaded as 'data.tif'
        # locate download
        local_data = filepaths[2] + '\data.tif'
        local_data_pan = filepaths[1] + '\data.tif'

        try:
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[2], im_fn['']))
            os.rename(local_data, os.path.join(filepaths[2], im_fn['']))

        try:
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['']))
            os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['']))

        # metadata for .txt file
        filename_txt = im_fn[''].replace('.tif', '')
        metadict = {'filename': im_fn[''],
                    'epsg': metadata['bands'][0]['crs'][5:],
                    'start_date': inputs['dates'][0],
                    'end_date': inputs['dates'][1],
                    'median_no': sum_img}

        # Sentinel 2 download
    elif satname == ['S2']:

        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, 'S2')

        # initialise variables and loop through images
        filenames = []
        all_names = []
        # for year in sat_list:
        median_img, sum_img = obtain_median_image('COPERNICUS/S2',
                                                  inputs['dates'],
                                                  ee.Geometry.Polygon(inputs['polygon']), inputs['sat_list'],
                                                  settings)
        print('Median processed')

        im_date = inputs['dates'][0] + '-00-00-00'
        # extract year
#        first_date = inputs["dates"][0]
#        year = first_date[:-6]

        ##Extract band metadata and define those to download
        metadata = median_img.getInfo()
        # im_bands = metadata['bands']

        bands = {}
        bands['10m'] = ['B2', 'B3', 'B4', 'B8']  # multispectral bands
        bands['20m'] = ['B12']  # SWIR band
        bands['60m'] = ['QA60']  # QA band

        im_fn = {}
        for key in bands.keys():
            im_fn[key] = im_date + '_' + satname[0] + '_' + inputs['sitename'] + '_median_' + key + suffix
        # if two images taken at the same date add 'dup' to the name (duplicate)
        if any(im_fn['10m'] in _ for _ in all_names):
            for key in bands.keys():
                im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + '_dup' + suffix
            # also check for triplicates (only on S2 imagery) and add 'tri' to the name
            if im_fn['10m'] in all_names:
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + '_tri' + suffix

        # download .tif from EE
        get_url('data', median_img, ee.Number(10), inputs['polygon'], filepaths[1], bands['10m'])
        get_url('data', median_img, ee.Number(20), inputs['polygon'], filepaths[2], bands['20m'])
        get_url('data', median_img, ee.Number(60), inputs['polygon'], filepaths[3], bands['20m'])
        print('Downloaded')

        # rename the file as the image is downloaded as 'data.tif'
        # locate download
        local_data_10m = filepaths[1] + '\data.tif'
        local_data_20m = filepaths[2] + '\data.tif'
        local_data_60m = filepaths[3] + '\data.tif'

        try:
            os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['10m']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[1], im_fn['10m']))
            os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['10m']))

        try:
            os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['20m']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[2], im_fn['20m']))
            os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['20m']))

        try:
            os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['60m']))
        except:  # overwrite if already exists
            os.remove(os.path.join(filepaths[3], im_fn['60m']))
            os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['60m']))

        # metadata for .txt file
#        filename_txt = im_fn[''].replace('.tif', '.txt')
#        metadict = {'filename': im_fn[''],
#                    'epsg': metadata['bands'][0]['crs'][5:],
#                    'start_date': inputs['dates'][0],
#                    'end_date': inputs['dates'][1],
#                    'median_no': sum_img}

        filename_txt = im_fn['10m'].replace('_10m', '').replace('tif', 'txt')
        metadict = {'filename': im_fn['10m'],
                    'acc_georef': 1,
                    'epsg': metadata['bands'][0]['crs'][5:],
                    'median_no': sum_img}


        # write metadata
    with open(os.path.join(filepaths[0], filename_txt), 'w') as f:
        for key in metadict.keys():
            f.write('%s\t%s\n' % (key, metadict[key]))
    print('')

    # once all images have been downloaded, load metadata from .txt files
    metadata = get_metadata(inputs)

    # save metadata dict
    with open(os.path.join(im_folder, inputs['sitename'] + '_metadata' + '.pkl'), 'wb') as f:
        pickle.dump(metadata, f)

    return metadata


def retrieve_training_images(inputs):
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
    im_dict_T1, im_dict_T2 = check_images_available(inputs)

    # if user also wants to download T2 images, merge both lists
    if 'include_T2' in inputs.keys():
        for key in inputs['sat_list']:
            if key == 'S2':
                continue
            else:
                im_dict_T1[key] += im_dict_T2[key]

    # remove UTM duplicates in S2 collections (they provide several projections for same images)
    if 'S2' in inputs['sat_list'] and len(im_dict_T1['S2']) > 0:
        im_dict_T1['S2'] = filter_S2_collection(im_dict_T1['S2'])

    # create a new directory for this site with the name of the site
    im_folder = os.path.join(inputs['filepath'], inputs['sitename'])
    if not os.path.exists(im_folder): os.makedirs(im_folder)

    print('\nDownloading images:')
    suffix = '.tif'
    for satname in im_dict_T1.keys():
        print('%s: %d images' % (satname, len(im_dict_T1[satname])))
        # create subfolder structure to store the different bands
        filepaths = create_folder_structure(im_folder, satname)
        # initialise variables and loop through images
        georef_accs = []
        filenames = []
        all_names = []
        im_epsg = []
        for i in range(len(im_dict_T1[satname])):

            im_meta = im_dict_T1[satname][i]

            # get time of acquisition (UNIX time) and convert to datetime
            t = im_meta['properties']['system:time_start']
            im_timestamp = datetime.fromtimestamp(t / 1000, tz=pytz.utc)
            im_date = im_timestamp.strftime('%Y-%m-%d-%H-%M-%S')

            # get epsg code
            im_epsg.append(int(im_meta['bands'][0]['crs'][5:]))

            # get geometric accuracy
            if satname in ['L5', 'L7', 'L8']:
                if 'GEOMETRIC_RMSE_MODEL' in im_meta['properties'].keys():
                    acc_georef = im_meta['properties']['GEOMETRIC_RMSE_MODEL']
                else:
                    acc_georef = 12  # default value of accuracy (RMSE = 12m)
            elif satname in ['S2']:
                # Sentinel-2 products don't provide a georeferencing accuracy (RMSE as in Landsat)
                # but they have a flag indicating if the geometric quality control was passed or failed
                # if passed a value of 1 is stored if failed a value of -1 is stored in the metadata
                # the name of the property containing the flag changes across the S2 archive
                # check which flag name is used for the image and store the 1/-1 for acc_georef
                flag_names = ['GEOMETRIC_QUALITY_FLAG', 'GEOMETRIC_QUALITY', 'quality_check']
                for key in flag_names:
                    if key in im_meta['properties'].keys(): break
                if im_meta['properties'][key] == 'PASSED':
                    acc_georef = 1
                else:
                    acc_georef = -1
            georef_accs.append(acc_georef)

            bands = dict([])
            im_fn = dict([])
            # first delete dimensions key from dictionnary
            # otherwise the entire image is extracted (don't know why)
            im_bands = im_meta['bands']
            for j in range(len(im_bands)): del im_bands[j]['dimensions']

            # Landsat 5 download
            if satname == 'L5':
                bands[''] = [im_bands[0], im_bands[1], im_bands[2], im_bands[3],
                             im_bands[4], im_bands[7]]
                im_fn[''] = im_date + '_' + satname + '_' + inputs['sitename'] + suffix
                # if two images taken at the same date add 'dup' to the name (duplicate)
                if any(im_fn[''] in _ for _ in all_names):
                    im_fn[''] = im_date + '_' + satname + '_' + inputs['sitename'] + '_dup' + suffix
                all_names.append(im_fn[''])
                filenames.append(im_fn[''])
                # download .tif from EE
                while True:
                    try:
                        im_ee = ee.Image(im_meta['id'])
                        local_data = download_tif(im_ee, inputs['polygon'], bands[''], filepaths[1])
                        break
                    except:
                        continue
                # rename the file as the image is downloaded as 'data.tif'
                try:
                    os.rename(local_data, os.path.join(filepaths[1], im_fn['']))
                except:  # overwrite if already exists
                    os.remove(os.path.join(filepaths[1], im_fn['']))
                    os.rename(local_data, os.path.join(filepaths[1], im_fn['']))
                # metadata for .txt file
                filename_txt = im_fn[''].replace('.tif', '')
                metadict = {'filename': im_fn[''], 'acc_georef': georef_accs[i],
                            'epsg': im_epsg[i]}

            # Landsat 7 and 8 download
            elif satname in ['L7', 'L8']:
                if satname == 'L7':
                    bands['pan'] = [im_bands[8]]  # panchromatic band
                    bands['ms'] = [im_bands[0], im_bands[1], im_bands[2], im_bands[3],
                                   im_bands[4], im_bands[9]]  # multispectral bands
                else:
                    bands['pan'] = [im_bands[7]]  # panchromatic band
                    bands['ms'] = [im_bands[1], im_bands[2], im_bands[3], im_bands[4],
                                   im_bands[5], im_bands[11]]  # multispectral bands
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + suffix
                # if two images taken at the same date add 'dup' to the name (duplicate)
                if any(im_fn['pan'] in _ for _ in all_names):
                    for key in bands.keys():
                        im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + '_dup' + suffix
                all_names.append(im_fn['pan'])
                filenames.append(im_fn['pan'])
                # download .tif from EE (panchromatic band and multispectral bands)
                while True:
                    try:
                        im_ee = ee.Image(im_meta['id'])
                        local_data_pan = download_tif(im_ee, inputs['polygon'], bands['pan'], filepaths[1])
                        local_data_ms = download_tif(im_ee, inputs['polygon'], bands['ms'], filepaths[2])
                        break
                    except:
                        continue
                # rename the files as the image is downloaded as 'data.tif'
                try:  # panchromatic
                    os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['pan']))
                except:  # overwrite if already exists
                    os.remove(os.path.join(filepaths[1], im_fn['pan']))
                    os.rename(local_data_pan, os.path.join(filepaths[1], im_fn['pan']))
                try:  # multispectral
                    os.rename(local_data_ms, os.path.join(filepaths[2], im_fn['ms']))
                except:  # overwrite if already exists
                    os.remove(os.path.join(filepaths[2], im_fn['ms']))
                    os.rename(local_data_ms, os.path.join(filepaths[2], im_fn['ms']))
                # metadata for .txt file
                filename_txt = im_fn['pan'].replace('_pan', '').replace('.tif', '')
                metadict = {'filename': im_fn['pan'], 'acc_georef': georef_accs[i],
                            'epsg': im_epsg[i]}

            # Sentinel-2 download
            elif satname in ['S2']:

                bands['10m'] = [im_bands[1], im_bands[2], im_bands[3], im_bands[7]]  # multispectral bands
                bands['20m'] = [im_bands[11]]  # SWIR band
                bands['60m'] = [im_bands[15]]  # QA band
                for key in bands.keys():
                    im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + suffix
                # if two images taken at the same date add 'dup' to the name (duplicate)
                if any(im_fn['10m'] in _ for _ in all_names):
                    for key in bands.keys():
                        im_fn[key] = im_date + '_' + satname + '_' + inputs['sitename'] + '_' + key + '_dup' + suffix
                    # also check for triplicates (only on S2 imagery) and add 'tri' to the name
                    if im_fn['10m'] in all_names:
                        for key in bands.keys():
                            im_fn[key] = im_date + '_' + satname + '_' + inputs[
                                'sitename'] + '_' + key + '_tri' + suffix
                all_names.append(im_fn['10m'])
                filenames.append(im_fn['10m'])

                # download .tif from EE (multispectral bands at 3 different resolutions)
                while True:
                    try:
                        im_ee = ee.Image(im_meta['id'])
                        local_data_10m = download_tif(im_ee, inputs['polygon'], bands['10m'], filepaths[1])
                        #                       local_data_20m = download_tif(im_ee, inputs['polygon'], bands['20m'], filepaths[2])
                        #                       local_data_60m = download_tif(im_ee, inputs['polygon'], bands['60m'], filepaths[3])
                        break
                    except:
                        continue

                # rename the files as the image is downloaded as 'data.tif'
                try:  # 10m
                    os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['10m']))
                except:  # overwrite if already exists
                    os.remove(os.path.join(filepaths[1], im_fn['10m']))
                    os.rename(local_data_10m, os.path.join(filepaths[1], im_fn['10m']))
                try:  # 20m
                    os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['20m']))
                except:  # overwrite if already exists
                    os.remove(os.path.join(filepaths[2], im_fn['20m']))
                    os.rename(local_data_20m, os.path.join(filepaths[2], im_fn['20m']))
                try:  # 60m
                    os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['60m']))
                except:  # overwrite if already exists
                    os.remove(os.path.join(filepaths[3], im_fn['60m']))
                    os.rename(local_data_60m, os.path.join(filepaths[3], im_fn['60m']))
                # metadata for .txt file
                filename_txt = im_fn['10m'].replace('_10m', '').replace('.tif', '')
                metadict = {'filename': im_fn['10m'], 'acc_georef': georef_accs[i],
                            'epsg': im_epsg[i]}

            # write metadata
            with open(os.path.join(filepaths[0], filename_txt + '.txt'), 'w') as f:
                for key in metadict.keys():
                    f.write('%s\t%s\n' % (key, metadict[key]))
            # print percentage completion for user
            print('\r%d%%' % int((i + 1) / len(im_dict_T1[satname]) * 100), end='')

        print('')

    # once all images have been downloaded, load metadata from .txt files
    metadata = get_metadata(inputs)

    # merge overlapping images (necessary only if the polygon is at the boundary of an image)
    if 'S2' in metadata.keys():
        try:
            metadata = merge_overlapping_images(metadata, inputs)
        except:
            print('WARNING: there was an error while merging overlapping S2 images,' +
                  ' please open an issue on Github at https://github.com/kvos/CoastSat/issues' +
                  ' and include your script so we can find out what happened.')

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
        'name': 'data',
        'scale': scale,
        'region': region,
        'filePerBand': False,
        'bands': bands
    })

    local_zip, headers = urlretrieve(path)
    with zipfile.ZipFile(local_zip) as local_zipfile:
        return local_zipfile.extractall(path=str(filepath))


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
    # End date from user input range
    user_end = start_date.split("-")
    # Period of Sentinel 2 data before Surface reflectance data is available
    start = datetime(2015, 6, 23)
    end = datetime(2019, 1, 28)

    # Is end date within pre S2_SR period?
    if time_in_range(start, end, datetime(int(user_end[0]), int(user_end[1]), int(user_end[2]))) == False:
        # Import and filter S2 SR.
        s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))
    else:
        # Import and filter S2 SR.
        s2_sr_col = (ee.ImageCollection('COPERNICUS/S2')
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


def time_in_range(start, end, x):
    """
    Return true if x is in the date range [start, end]

    Parameters
    ----------
    start : datetime(x,y,z)
        Date time format start
    end : datetime(x,y,z)
        Date time format end
    x : datetime(x,y,z)
        Is Date time format within start / end

    Returns
    -------
    TYPE
        True/False.
    """

    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end