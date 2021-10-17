from coastsat.SDS_classify import *
from coastsat import NOC_shoreline


def label_images_4classes(metadata, settings):
    """
    Load satellite images and interactively label different classes (hard-coded)

    KV WRL 2019

    Arguments:
    -----------
    metadata: dict
        contains all the information about the satellite images that were downloaded
    settings: dict with the following keys
        'cloud_thresh': float
            value between 0 and 1 indicating the maximum cloud fraction in
            the cropped image that is accepted
        'cloud_mask_issue': boolean
            True if there is an issue with the cloud mask and sand pixels
            are erroneously being masked on the images
        'labels': dict
            list of label names (key) and label numbers (value) for each class
        'flood_fill': boolean
            True to use the flood_fill functionality when labelling sand pixels
        'tolerance': float
            tolerance value for flood fill when labelling the sand pixels
        'filepath_train': str
            directory in which to save the labelled data
        'inputs': dict
            input parameters (sitename, filepath, polygon, dates, sat_list)

    Returns:
    -----------
    Stores the labelled data in the specified directory

    """

    filepath_train = settings['filepath_train']
    # initialize figure
    fig, ax = plt.subplots(1, 1, figsize=[17, 10], tight_layout=True, sharex=True,
                           sharey=True)
    mng = plt.get_current_fig_manager()
    mng.window.showMaximized()

    # loop through satellites
    for satname in metadata.keys():
        filepath = SDS_tools.get_filepath(settings['inputs'], satname)
        filenames = metadata[satname]['filenames']
        # loop through images
        for i in range(len(filenames)):
            # image filename
            fn = SDS_tools.get_filenames(filenames[i], filepath, satname)
            # read and preprocess image
            im_ms, georef, cloud_mask, im_extra, im_QA, im_nodata = SDS_preprocess.preprocess_single(fn, satname,
                                                                                                     settings[
                                                                                                         'cloud_mask_issue'])
            # calculate cloud cover
            cloud_cover = np.divide(sum(sum(cloud_mask.astype(int))),
                                    (cloud_mask.shape[0] * cloud_mask.shape[1]))
            # skip image if cloud cover is above threshold
            if cloud_cover > settings['cloud_thresh'] or cloud_cover == 1:
                continue
            # get individual RGB image
            im_RGB = SDS_preprocess.rescale_image_intensity(im_ms[:, :, [2, 1, 0]], cloud_mask, 99.9)
            im_NDVI = SDS_tools.nd_index(im_ms[:, :, 3], im_ms[:, :, 2], cloud_mask)
            im_NDWI = SDS_tools.nd_index(im_ms[:, :, 3], im_ms[:, :, 1], cloud_mask)
            # initialise labels
            im_viz = im_RGB.copy()
            im_labels = np.zeros([im_RGB.shape[0], im_RGB.shape[1]])
            # show RGB image
            ax.axis('off')
            ax.imshow(im_RGB)
            implot = ax.imshow(im_viz, alpha=0.6)
            filename = filenames[i][:filenames[i].find('.')][:-4]
            ax.set_title(filename)

            ##############################################################
            # select image to label
            ##############################################################
            # set a key event to accept/reject the detections (see https://stackoverflow.com/a/15033071)
            # this variable needs to be immuatable so we can access it after the keypress event
            key_event = {}

            def press(event):
                # store what key was pressed in the dictionary
                key_event['pressed'] = event.key

            # let the user press a key, right arrow to keep the image, left arrow to skip it
            # to break the loop the user can press 'escape'
            while True:
                btn_keep = ax.text(1.1, 0.9, 'keep ⇨', size=12, ha="right", va="top",
                                   transform=ax.transAxes,
                                   bbox=dict(boxstyle="square", ec='k', fc='w'))
                btn_skip = ax.text(-0.1, 0.9, '⇦ skip', size=12, ha="left", va="top",
                                   transform=ax.transAxes,
                                   bbox=dict(boxstyle="square", ec='k', fc='w'))
                btn_esc = ax.text(0.5, 0, '<esc> to quit', size=12, ha="center", va="top",
                                  transform=ax.transAxes,
                                  bbox=dict(boxstyle="square", ec='k', fc='w'))
                fig.canvas.draw_idle()
                fig.canvas.mpl_connect('key_press_event', press)
                plt.waitforbuttonpress()
                # after button is pressed, remove the buttons
                btn_skip.remove()
                btn_keep.remove()
                btn_esc.remove()

                # keep/skip image according to the pressed key, 'escape' to break the loop
                if key_event.get('pressed') == 'right':
                    skip_image = False
                    break
                elif key_event.get('pressed') == 'left':
                    skip_image = True
                    break
                elif key_event.get('pressed') == 'escape':
                    plt.close()
                    raise StopIteration('User cancelled labelling images')
                else:
                    plt.waitforbuttonpress()

            # if user decided to skip show the next image
            if skip_image:
                ax.clear()
                continue
            # otherwise label this image
            else:
                ##############################################################
                # digitize white-water pixels
                ##############################################################
                color_ww = settings['colors']['white-water']
                ax.set_title('Click on individual WHITE-WATER pixels (no flood fill)\nwhen finished press <Enter>')
                # create erase button, if you click there it deletes the last selection
                btn_erase = ax.text(im_ms.shape[1], 0, 'Erase', size=20, ha='right', va='top',
                                    bbox=dict(boxstyle="square", ec='k', fc='w'))
                fig.canvas.draw_idle()
                ww_pixels = []
                while 1:
                    seed = ginput(n=1, timeout=0, show_clicks=True)
                    # if empty break the loop and go to next label
                    if len(seed) == 0:
                        break
                    else:
                        # round to pixel location
                        seed = np.round(seed[0]).astype(int)
                        # if user clicks on erase, delete the last labelled pixels
                    if seed[0] > 0.95 * im_ms.shape[1] and seed[1] < 0.05 * im_ms.shape[0]:
                        if len(ww_pixels) > 0:
                            im_labels[ww_pixels[-1][1], ww_pixels[-1][0]] = 3
                            for k in range(im_viz.shape[2]):
                                im_viz[ww_pixels[-1][1], ww_pixels[-1][0], k] = \
                                                        im_RGB[ww_pixels[-1][1], ww_pixels[-1][0], k]
                            implot.set_data(im_viz)
                            fig.canvas.draw_idle()
                            del ww_pixels[-1]
                    else:

                        # flood fill the NDVI and the NDWI
                        fill_NDVI = flood(im_NDVI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        fill_NDWI = flood(im_NDWI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        # compute the intersection of the two masks
                        fill_ww = np.logical_and(fill_NDVI, fill_NDWI)
                        im_labels[fill_ww] = settings['labels']['white-water']
                        ww_pixels.append(fill_ww)
                        # show the labelled pixels
                        for k in range(im_viz.shape[2]):
                            im_viz[im_labels == settings['labels']['white-water'], k] = color_ww[k]
                        implot.set_data(im_viz)
                        fig.canvas.draw_idle()

                im_ww = im_viz.copy()
                btn_erase.set(text='<Esc> to Erase', fontsize=12)

                ##############################################################
                # digitize water pixels (with lassos)
                ##############################################################
                color_water = settings['colors']['water']
                ax.set_title('Click and hold to draw lassos and select WATER pixels\nwhen finished press <Enter>')
                fig.canvas.draw_idle()
                selector_water = SelectFromImage(ax, implot, color_water)
                key_event = {}
                while True:
                    fig.canvas.draw_idle()
                    fig.canvas.mpl_connect('key_press_event', press)
                    plt.waitforbuttonpress()
                    if key_event.get('pressed') == 'enter':
                        selector_water.disconnect()
                        break
                    elif key_event.get('pressed') == 'escape':
                        selector_water.array = im_ww
                        implot.set_data(selector_water.array)
                        fig.canvas.draw_idle()
                        selector_water.implot = implot
                        selector_water.im_bool = np.zeros(
                            (selector_water.array.shape[0], selector_water.array.shape[1]))
                        selector_water.ind = []
                        # update im_viz and im_labels
                im_viz = selector_water.array
                selector_water.im_bool = selector_water.im_bool.astype(bool)
                im_labels[selector_water.im_bool] = settings['labels']['water']

                ##############################################################
                # digitize land_1 pixels
                ##############################################################
                ax.set_title(
                    'Click on LAND_1 pixels (flood fill activated, tolerance = %.2f)\nwhen finished press <Enter>' %
                    settings['tolerance'])
                # create erase button, if you click there it delets the last selection
                btn_erase = ax.text(im_ms.shape[1], 0, 'Erase', size=20, ha='right', va='top',
                                    bbox=dict(boxstyle="square", ec='k', fc='w'))
                fig.canvas.draw_idle()
                color_land_1 = settings['colors']['land_1']
                land_1_pixels = []
                while 1:
                    seed = ginput(n=1, timeout=0, show_clicks=True)
                    # if empty break the loop and go to next label
                    if len(seed) == 0:
                        break
                    else:
                        # round to pixel location
                        seed = np.round(seed[0]).astype(int)
                        # if user clicks on erase, delete the last selection
                    if seed[0] > 0.95 * im_ms.shape[1] and seed[1] < 0.05 * im_ms.shape[0]:
                        if len(land_1_pixels) > 0:
                            im_labels[land_1_pixels[-1]] = 0
                            for k in range(im_viz.shape[2]):
                                im_viz[land_1_pixels[-1], k] = im_RGB[land_1_pixels[-1], k]
                            implot.set_data(im_viz)
                            fig.canvas.draw_idle()
                            del land_1_pixels[-1]

                    # otherwise label the selected land_1 pixels
                    else:
                        # flood fill the NDVI and the NDWI
                        fill_NDVI = flood(im_NDVI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        fill_NDWI = flood(im_NDWI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        # compute the intersection of the two masks
                        fill_land = np.logical_and(fill_NDVI, fill_NDWI)
                        im_labels[fill_land] = settings['labels']['land_1']
                        land_1_pixels.append(fill_land)
                        # show the labelled pixels
                        for k in range(im_viz.shape[2]):
                            im_viz[im_labels == settings['labels']['land_1'], k] = color_land_1[k]
                        implot.set_data(im_viz)
                        fig.canvas.draw_idle()

                im_ww_water_land1 = im_viz.copy()

                ##############################################################
                # digitize land pixels (with lassos)
                ##############################################################
                color_land_2 = settings['colors']['land_2']
                ax.set_title('Click and hold to draw lassos and select LAND_2 pixels\nwhen finished press <Enter>')
                fig.canvas.draw_idle()
                selector_land = SelectFromImage(ax, implot, color_land_2)
                key_event = {}
                while True:
                    fig.canvas.draw_idle()
                    fig.canvas.mpl_connect('key_press_event', press)
                    plt.waitforbuttonpress()
                    if key_event.get('pressed') == 'enter':
                        selector_land.disconnect()
                        break
                    elif key_event.get('pressed') == 'escape':
                        selector_land.array = im_ww_water_land1
                        implot.set_data(selector_land.array)
                        fig.canvas.draw_idle()
                        selector_land.implot = implot
                        selector_land.im_bool = np.zeros((selector_land.array.shape[0], selector_land.array.shape[1]))
                        selector_land.ind = []
                # update im_viz and im_labels
                im_viz = selector_land.array
                selector_land.im_bool = selector_land.im_bool.astype(bool)
                im_labels[selector_land.im_bool] = settings['labels']['land_2']

                im_ww_water_land1_land2 = im_viz.copy()

                ##############################################################
                # digitize land pixels (with lassos)
                ##############################################################
                color_land_3 = settings['colors']['land_3']
                ax.set_title('Click and hold to draw lassos and select LAND_3 pixels\nwhen finished press <Enter>')
                fig.canvas.draw_idle()
                selector_land = SelectFromImage(ax, implot, color_land_3)
                key_event = {}
                while True:
                    fig.canvas.draw_idle()
                    fig.canvas.mpl_connect('key_press_event', press)
                    plt.waitforbuttonpress()
                    if key_event.get('pressed') == 'enter':
                        selector_land.disconnect()
                        break
                    elif key_event.get('pressed') == 'escape':
                        selector_land.array = im_ww_water_land1_land2
                        implot.set_data(selector_land.array)
                        fig.canvas.draw_idle()
                        selector_land.implot = implot
                        selector_land.im_bool = np.zeros((selector_land.array.shape[0], selector_land.array.shape[1]))
                        selector_land.ind = []
                # update im_labels
                selector_land.im_bool = selector_land.im_bool.astype(bool)
                im_labels[selector_land.im_bool] = settings['labels']['land_3']

                # save labelled image
                ax.set_title(filename)
                fig.canvas.draw_idle()
                fp = os.path.join(filepath_train, settings['inputs']['sitename'])
                if not os.path.exists(fp):
                    os.makedirs(fp)
                fig.savefig(os.path.join(fp, filename + '.jpg'), dpi=150)
                ax.clear()
                # save labels and features
                features = dict([])
                for key in settings['labels'].keys():
                    im_bool = im_labels == settings['labels'][key]
                    features[key] = SDS_shoreline.calculate_features(im_ms, cloud_mask, im_bool)
                training_data = {'labels': im_labels, 'features': features, 'label_ids': settings['labels']}
                with open(os.path.join(fp, filename + '.pkl'), 'wb') as f:
                    pickle.dump(training_data, f)

    # close figure when finished
    plt.close(fig)


def evaluate_classifier_4classes(classifier, metadata, settings, base_path):
    """
    Apply the image classifier to all the images and save the classified images.

    KV WRL 2019

    Arguments:
    -----------
    classifier: joblib object
        classifier model to be used for image classification
    metadata: dict
        contains all the information about the satellite images that were downloaded
    settings: dict with the following keys
        'inputs': dict
            input parameters (sitename, filepath, polygon, dates, sat_list)
        'cloud_thresh': float
            value between 0 and 1 indicating the maximum cloud fraction in
            the cropped image that is accepted
        'cloud_mask_issue': boolean
            True if there is an issue with the cloud mask and sand pixels
            are erroneously being masked on the images
        'output_epsg': int
            output spatial reference system as EPSG code
        'buffer_size': int
            size of the buffer (m) around the sandy pixels over which the pixels
            are considered in the thresholding algorithm
        'min_beach_area': int
            minimum allowable object area (in metres^2) for the class 'sand',
            the area is converted to number of connected pixels
        'min_length_sl': int
            minimum length (in metres) of shoreline contour to be valid

    Returns:
    -----------
    Saves .jpg images with the output of the classification in the folder ./detection

    """

    # create folder called evaluation
    fp = os.path.join(base_path, 'evaluation')
    if not os.path.exists(fp):
        os.makedirs(fp)

    # initialize figure (not interactive)
    plt.ioff()
    fig, ax = plt.subplots(1, 2, figsize=[17, 10], sharex=True, sharey=True,
                           constrained_layout=True)

    # create colormap for labels
    colours = np.zeros((4, 4))
    colours[0, :] = np.array([1, 0, 0, 1])
    colours[1, :] = np.array([0, 1, 0, 1])
    colours[2, :] = np.array([1, 1, 0, 1])
    colours[3, :] = np.array([1, 0, 1, 1])

    # loop through satellites
    for satname in metadata.keys():
        filepath = SDS_tools.get_filepath(settings['inputs'], satname)
        filenames = metadata[satname]['filenames']

        # load classifiers and
        if satname in ['L5', 'L7', 'L8']:
            pixel_size = 15
        elif satname == 'S2':
            pixel_size = 10
        # convert settings['min_beach_area'] and settings['buffer_size'] from metres to pixels

        min_beach_area_pixels = np.ceil(settings['min_beach_area'] / pixel_size ** 2)

        # loop through images
        for i in range(len(filenames)):
            # image filename
            fn = SDS_tools.get_filenames(filenames[i], filepath, satname)
            # read and preprocess image
            im_ms, georef, cloud_mask, im_extra, im_QA, im_nodata = \
                SDS_preprocess.preprocess_single(fn, satname, settings['cloud_mask_issue'])

            # calculate cloud cover
            cloud_cover = np.divide(sum(sum(cloud_mask.astype(int))),
                                    (cloud_mask.shape[0] * cloud_mask.shape[1]))
            # skip image if cloud cover is above threshold
            if cloud_cover > settings['cloud_thresh']:
                continue

            # classify image in 4 classes (sand, whitewater, water, other) with NN classifier
            im_classif, im_labels = NOC_shoreline.classify_image_NN(im_ms, cloud_mask,
                                                                     min_beach_area_pixels, classifier)

            # make a plot
            im_RGB = SDS_preprocess.rescale_image_intensity(im_ms[:, :, [2, 1, 0]], cloud_mask, 99.9)
            # create classified image
            im_class = np.copy(im_RGB)

            for k in range(0, im_labels.shape[2]):
                im_class[im_labels[:, :, k], 0] = colours[k, 0]
                im_class[im_labels[:, :, k], 1] = colours[k, 1]
                im_class[im_labels[:, :, k], 2] = colours[k, 2]

            # show images
            ax[0].imshow(im_RGB)
            #            ax[1].imshow(im_RGB)
            ax[1].imshow(im_class, alpha=0.75)
            ax[0].axis('off')
            ax[1].axis('off')
            filename = filenames[i][:filenames[i].find('.')][:-4]
            ax[0].set_title(filename)
            # save figure
            fig.savefig(os.path.join(fp, settings['inputs']['sitename'] + filename[:19] + '.jpg'), dpi=150)
            # clear axes
            for cax in fig.axes:
                cax.clear()

    # close the figure at the end
    plt.close()


def label_images_5classes(metadata, settings):
    """
    Load satellite images and interactively label different classes (hard-coded)

    KV WRL 2019

    Arguments:
    -----------
    metadata: dict
        contains all the information about the satellite images that were downloaded
    settings: dict with the following keys
        'cloud_thresh': float
            value between 0 and 1 indicating the maximum cloud fraction in
            the cropped image that is accepted
        'cloud_mask_issue': boolean
            True if there is an issue with the cloud mask and sand pixels
            are erroneously being masked on the images
        'labels': dict
            list of label names (key) and label numbers (value) for each class
        'flood_fill': boolean
            True to use the flood_fill functionality when labelling sand pixels
        'tolerance': float
            tolerance value for flood fill when labelling the sand pixels
        'filepath_train': str
            directory in which to save the labelled data
        'inputs': dict
            input parameters (sitename, filepath, polygon, dates, sat_list)

    Returns:
    -----------
    Stores the labelled data in the specified directory

    """

    filepath_train = settings['filepath_train']
    # initialize figure
    fig, ax = plt.subplots(1, 1, figsize=[17, 10], tight_layout=True, sharex=True,
                           sharey=True)
    mng = plt.get_current_fig_manager()
    mng.window.showMaximized()

    # loop through satellites
    for satname in metadata.keys():
        filepath = SDS_tools.get_filepath(settings['inputs'], satname)
        filenames = metadata[satname]['filenames']
        # loop through images
        for i in range(len(filenames)):
            # image filename
            fn = SDS_tools.get_filenames(filenames[i], filepath, satname)
            # read and preprocess image
            im_ms, georef, cloud_mask, im_extra, im_QA, im_nodata = SDS_preprocess.preprocess_single(fn, satname,
                                                                                                     settings[
                                                                                                         'cloud_mask_issue'])
            # calculate cloud cover
            cloud_cover = np.divide(sum(sum(cloud_mask.astype(int))),
                                    (cloud_mask.shape[0] * cloud_mask.shape[1]))
            # skip image if cloud cover is above threshold
            if cloud_cover > settings['cloud_thresh'] or cloud_cover == 1:
                continue
            # get individual RGB image
            im_RGB = SDS_preprocess.rescale_image_intensity(im_ms[:, :, [2, 1, 0]], cloud_mask, 99.9)
            im_NDVI = SDS_tools.nd_index(im_ms[:, :, 3], im_ms[:, :, 2], cloud_mask)
            im_NDWI = SDS_tools.nd_index(im_ms[:, :, 3], im_ms[:, :, 1], cloud_mask)
            # initialise labels
            im_viz = im_RGB.copy()
            im_labels = np.zeros([im_RGB.shape[0], im_RGB.shape[1]])
            # show RGB image
            ax.axis('off')
            ax.imshow(im_RGB)
            implot = ax.imshow(im_viz, alpha=0.6)
            filename = filenames[i][:filenames[i].find('.')][:-4]
            ax.set_title(filename)

            ##############################################################
            # select image to label
            ##############################################################
            # set a key event to accept/reject the detections (see https://stackoverflow.com/a/15033071)
            # this variable needs to be immuatable so we can access it after the keypress event
            key_event = {}

            def press(event):
                # store what key was pressed in the dictionary
                key_event['pressed'] = event.key

            # let the user press a key, right arrow to keep the image, left arrow to skip it
            # to break the loop the user can press 'escape'
            while True:
                btn_keep = ax.text(1.1, 0.9, 'keep ⇨', size=12, ha="right", va="top",
                                   transform=ax.transAxes,
                                   bbox=dict(boxstyle="square", ec='k', fc='w'))
                btn_skip = ax.text(-0.1, 0.9, '⇦ skip', size=12, ha="left", va="top",
                                   transform=ax.transAxes,
                                   bbox=dict(boxstyle="square", ec='k', fc='w'))
                btn_esc = ax.text(0.5, 0, '<esc> to quit', size=12, ha="center", va="top",
                                  transform=ax.transAxes,
                                  bbox=dict(boxstyle="square", ec='k', fc='w'))
                fig.canvas.draw_idle()
                fig.canvas.mpl_connect('key_press_event', press)
                plt.waitforbuttonpress()
                # after button is pressed, remove the buttons
                btn_skip.remove()
                btn_keep.remove()
                btn_esc.remove()

                # keep/skip image according to the pressed key, 'escape' to break the loop
                if key_event.get('pressed') == 'right':
                    skip_image = False
                    break
                elif key_event.get('pressed') == 'left':
                    skip_image = True
                    break
                elif key_event.get('pressed') == 'escape':
                    plt.close()
                    raise StopIteration('User cancelled labelling images')
                else:
                    plt.waitforbuttonpress()

            # if user decided to skip show the next image
            if skip_image:
                ax.clear()
                continue
            # otherwise label this image
            else:
                ##############################################################
                # digitize white-water pixels
                ##############################################################
                color_ww = settings['colors']['white-water']
                ax.set_title('Click on individual WHITE-WATER pixels (no flood fill)\nwhen finished press <Enter>')
                # create erase button, if you click there it deletes the last selection
                btn_erase = ax.text(im_ms.shape[1], 0, 'Erase', size=20, ha='right', va='top',
                                    bbox=dict(boxstyle="square", ec='k', fc='w'))
                fig.canvas.draw_idle()
                ww_pixels = []
                while 1:
                    seed = ginput(n=1, timeout=0, show_clicks=True)
                    # if empty break the loop and go to next label
                    if len(seed) == 0:
                        break
                    else:
                        # round to pixel location
                        seed = np.round(seed[0]).astype(int)
                        # if user clicks on erase, delete the last labelled pixels
                    if seed[0] > 0.95 * im_ms.shape[1] and seed[1] < 0.05 * im_ms.shape[0]:
                        if len(ww_pixels) > 0:
                            im_labels[ww_pixels[-1][1], ww_pixels[-1][0]] = 3
                            for k in range(im_viz.shape[2]):
                                im_viz[ww_pixels[-1][1], ww_pixels[-1][0], k] = \
                                                        im_RGB[ww_pixels[-1][1], ww_pixels[-1][0], k]
                            implot.set_data(im_viz)
                            fig.canvas.draw_idle()
                            del ww_pixels[-1]
                    else:

                        # flood fill the NDVI and the NDWI
                        fill_NDVI = flood(im_NDVI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        fill_NDWI = flood(im_NDWI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        # compute the intersection of the two masks
                        fill_ww = np.logical_and(fill_NDVI, fill_NDWI)
                        im_labels[fill_ww] = settings['labels']['white-water']
                        ww_pixels.append(fill_ww)
                        # show the labelled pixels
                        for k in range(im_viz.shape[2]):
                            im_viz[im_labels == settings['labels']['white-water'], k] = color_ww[k]
                        implot.set_data(im_viz)
                        fig.canvas.draw_idle()

                im_ww = im_viz.copy()
                btn_erase.set(text='<Esc> to Erase', fontsize=12)

                ##############################################################
                # digitize water pixels (with lassos)
                ##############################################################
                color_water = settings['colors']['water']
                ax.set_title('Click and hold to draw lassos and select WATER pixels\nwhen finished press <Enter>')
                fig.canvas.draw_idle()
                selector_water = SelectFromImage(ax, implot, color_water)
                key_event = {}
                while True:
                    fig.canvas.draw_idle()
                    fig.canvas.mpl_connect('key_press_event', press)
                    plt.waitforbuttonpress()
                    if key_event.get('pressed') == 'enter':
                        selector_water.disconnect()
                        break
                    elif key_event.get('pressed') == 'escape':
                        selector_water.array = im_ww
                        implot.set_data(selector_water.array)
                        fig.canvas.draw_idle()
                        selector_water.implot = implot
                        selector_water.im_bool = np.zeros(
                            (selector_water.array.shape[0], selector_water.array.shape[1]))
                        selector_water.ind = []
                        # update im_viz and im_labels
                im_viz = selector_water.array
                selector_water.im_bool = selector_water.im_bool.astype(bool)
                im_labels[selector_water.im_bool] = settings['labels']['water']

                ##############################################################
                # digitize land_1 pixels
                ##############################################################
                ax.set_title(
                    'Click on LAND_1 pixels (flood fill activated, tolerance = %.2f)\nwhen finished press <Enter>' %
                    settings['tolerance'])
                # create erase button, if you click there it delets the last selection
                btn_erase = ax.text(im_ms.shape[1], 0, 'Erase', size=20, ha='right', va='top',
                                    bbox=dict(boxstyle="square", ec='k', fc='w'))
                fig.canvas.draw_idle()
                color_land_1 = settings['colors']['land_1']
                land_1_pixels = []
                while 1:
                    seed = ginput(n=1, timeout=0, show_clicks=True)
                    # if empty break the loop and go to next label
                    if len(seed) == 0:
                        break
                    else:
                        # round to pixel location
                        seed = np.round(seed[0]).astype(int)
                        # if user clicks on erase, delete the last selection
                    if seed[0] > 0.95 * im_ms.shape[1] and seed[1] < 0.05 * im_ms.shape[0]:
                        if len(land_1_pixels) > 0:
                            im_labels[land_1_pixels[-1]] = 0
                            for k in range(im_viz.shape[2]):
                                im_viz[land_1_pixels[-1], k] = im_RGB[land_1_pixels[-1], k]
                            implot.set_data(im_viz)
                            fig.canvas.draw_idle()
                            del land_1_pixels[-1]

                    # otherwise label the selected land_1 pixels
                    else:
                        # flood fill the NDVI and the NDWI
                        fill_NDVI = flood(im_NDVI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        fill_NDWI = flood(im_NDWI, (seed[1], seed[0]), tolerance=settings['tolerance'])
                        # compute the intersection of the two masks
                        fill_land = np.logical_and(fill_NDVI, fill_NDWI)
                        im_labels[fill_land] = settings['labels']['land_1']
                        land_1_pixels.append(fill_land)
                        # show the labelled pixels
                        for k in range(im_viz.shape[2]):
                            im_viz[im_labels == settings['labels']['land_1'], k] = color_land_1[k]
                        implot.set_data(im_viz)
                        fig.canvas.draw_idle()

                im_ww_water_land1 = im_viz.copy()

                ##############################################################
                # digitize land pixels (with lassos)
                ##############################################################
                color_land_2 = settings['colors']['land_2']
                ax.set_title('Click and hold to draw lassos and select LAND_2 pixels\nwhen finished press <Enter>')
                fig.canvas.draw_idle()
                selector_land = SelectFromImage(ax, implot, color_land_2)
                key_event = {}
                while True:
                    fig.canvas.draw_idle()
                    fig.canvas.mpl_connect('key_press_event', press)
                    plt.waitforbuttonpress()
                    if key_event.get('pressed') == 'enter':
                        selector_land.disconnect()
                        break
                    elif key_event.get('pressed') == 'escape':
                        selector_land.array = im_ww_water_land1
                        implot.set_data(selector_land.array)
                        fig.canvas.draw_idle()
                        selector_land.implot = implot
                        selector_land.im_bool = np.zeros((selector_land.array.shape[0], selector_land.array.shape[1]))
                        selector_land.ind = []
                # update im_viz and im_labels
                im_viz = selector_land.array
                selector_land.im_bool = selector_land.im_bool.astype(bool)
                im_labels[selector_land.im_bool] = settings['labels']['land_2']

                im_ww_water_land1_land2 = im_viz.copy()

                ##############################################################
                # digitize land pixels (with lassos)
                ##############################################################
                color_land_3 = settings['colors']['land_3']
                ax.set_title('Click and hold to draw lassos and select LAND_3 pixels\nwhen finished press <Enter>')
                fig.canvas.draw_idle()
                selector_land = SelectFromImage(ax, implot, color_land_3)
                key_event = {}
                while True:
                    fig.canvas.draw_idle()
                    fig.canvas.mpl_connect('key_press_event', press)
                    plt.waitforbuttonpress()
                    if key_event.get('pressed') == 'enter':
                        selector_land.disconnect()
                        break
                    elif key_event.get('pressed') == 'escape':
                        selector_land.array = im_ww_water_land1_land2
                        implot.set_data(selector_land.array)
                        fig.canvas.draw_idle()
                        selector_land.implot = implot
                        selector_land.im_bool = np.zeros((selector_land.array.shape[0], selector_land.array.shape[1]))
                        selector_land.ind = []
                # update im_labels
                selector_land.im_bool = selector_land.im_bool.astype(bool)
                im_labels[selector_land.im_bool] = settings['labels']['land_3']

                # save labelled image
                ax.set_title(filename)
                fig.canvas.draw_idle()
                fp = os.path.join(filepath_train, settings['inputs']['sitename'])
                if not os.path.exists(fp):
                    os.makedirs(fp)
                fig.savefig(os.path.join(fp, filename + '.jpg'), dpi=150)
                ax.clear()
                # save labels and features
                features = dict([])
                for key in settings['labels'].keys():
                    im_bool = im_labels == settings['labels'][key]
                    features[key] = SDS_shoreline.calculate_features(im_ms, cloud_mask, im_bool)
                training_data = {'labels': im_labels, 'features': features, 'label_ids': settings['labels']}
                with open(os.path.join(fp, filename + '.pkl'), 'wb') as f:
                    pickle.dump(training_data, f)

    # close figure when finished
    plt.close(fig)


def evaluate_classifier_5classes(classifier, metadata, settings, base_path):
    """
    Apply the image classifier to all the images and save the classified images.

    KV WRL 2019

    Arguments:
    -----------
    classifier: joblib object
        classifier model to be used for image classification
    metadata: dict
        contains all the information about the satellite images that were downloaded
    settings: dict with the following keys
        'inputs': dict
            input parameters (sitename, filepath, polygon, dates, sat_list)
        'cloud_thresh': float
            value between 0 and 1 indicating the maximum cloud fraction in
            the cropped image that is accepted
        'cloud_mask_issue': boolean
            True if there is an issue with the cloud mask and sand pixels
            are erroneously being masked on the images
        'output_epsg': int
            output spatial reference system as EPSG code
        'buffer_size': int
            size of the buffer (m) around the sandy pixels over which the pixels
            are considered in the thresholding algorithm
        'min_beach_area': int
            minimum allowable object area (in metres^2) for the class 'sand',
            the area is converted to number of connected pixels
        'min_length_sl': int
            minimum length (in metres) of shoreline contour to be valid

    Returns:
    -----------
    Saves .jpg images with the output of the classification in the folder ./detection

    """

    # create folder called evaluation
    fp = os.path.join(base_path, 'evaluation')
    if not os.path.exists(fp):
        os.makedirs(fp)

    # initialize figure (not interactive)
    plt.ioff()
    fig, ax = plt.subplots(1, 2, figsize=[17, 10], sharex=True, sharey=True,
                           constrained_layout=True)

    # create colormap for labels
    colours = np.zeros((5, 4))
    colours[0, :] = np.array([1, 0, 0, 1])
    colours[1, :] = np.array([0, 1, 0, 1])
    colours[2, :] = np.array([1, 1, 0, 1])
    colours[3, :] = np.array([1, 0, 1, 1])
    colours[4, :] = np.array([0, 91 / 255, 1, 1])

    # loop through satellites
    for satname in metadata.keys():
        filepath = SDS_tools.get_filepath(settings['inputs'], satname)
        filenames = metadata[satname]['filenames']

        # load classifiers and
        if satname in ['L5', 'L7', 'L8']:
            pixel_size = 15
        elif satname == 'S2':
            pixel_size = 10
        # convert settings['min_beach_area'] and settings['buffer_size'] from metres to pixels

        min_beach_area_pixels = np.ceil(settings['min_beach_area'] / pixel_size ** 2)

        # loop through images
        for i in range(len(filenames)):
            # image filename
            fn = SDS_tools.get_filenames(filenames[i], filepath, satname)
            # read and preprocess image
            im_ms, georef, cloud_mask, im_extra, im_QA, im_nodata = \
                SDS_preprocess.preprocess_single(fn, satname, settings['cloud_mask_issue'])

            # calculate cloud cover
            cloud_cover = np.divide(sum(sum(cloud_mask.astype(int))),
                                    (cloud_mask.shape[0] * cloud_mask.shape[1]))
            # skip image if cloud cover is above threshold
            if cloud_cover > settings['cloud_thresh']:
                continue

            # classify image in 4 classes (sand, whitewater, water, other) with NN classifier
            im_classif, im_labels = NOC_shoreline.classify_image_NN(im_ms, cloud_mask,
                                                                     min_beach_area_pixels, classifier)

            # make a plot
            im_RGB = SDS_preprocess.rescale_image_intensity(im_ms[:, :, [2, 1, 0]], cloud_mask, 99.9)
            # create classified image
            im_class = np.copy(im_RGB)

            for k in range(0, im_labels.shape[2]):
                im_class[im_labels[:, :, k], 0] = colours[k, 0]
                im_class[im_labels[:, :, k], 1] = colours[k, 1]
                im_class[im_labels[:, :, k], 2] = colours[k, 2]

            # show images
            ax[0].imshow(im_RGB)
            #            ax[1].imshow(im_RGB)
            ax[1].imshow(im_class, alpha=0.75)
            ax[0].axis('off')
            ax[1].axis('off')
            filename = filenames[i][:filenames[i].find('.')][:-4]
            ax[0].set_title(filename)
            # save figure
            fig.savefig(os.path.join(fp, settings['inputs']['sitename'] + filename[:19] + '.jpg'), dpi=150)
            # clear axes
            for cax in fig.axes:
                cax.clear()

    # close the figure at the end
    plt.close()