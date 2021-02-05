# CoastSat_nocs

CoastSat_nocs is an open-source software toolkit written in Python that enables users to obtain shoreline change statistics and forecasts at any sandy coastline worldwide using Landsat 5, 7, 8 and Sentinel-2. This is a toolkit is that has been modified from coastsat - an [open sourced code](https://github.com/kvos/CoastSat) by Vos et al., 2019  and uses [DSAS shoreline analysis](https://www.usgs.gov/centers/whcmsc/science/digital-shoreline-analysis-system-dsas) plug-in in ArcMap.

Coastsat_nocs has branched from coastsat with the intention of producing large-scale shoreline change analysis. The following changes have been made:
* Retrieve median composites of satellite data - I.e. ‘['2000-01-01', '2000-12-31']’ single shoreline from annual composite.
* The user can loop through multiple study areas rather than a single polygon
* Multiple date ranges (+ satellites) can be specified
* Landsat collections can be merged to increase the number of images used in the median
* Improved cloud masking process using Landsat Cloud Score and the Sentinel 2 Cloud Probabiity layer
* Automated shoreline cleaning models
* Instructions for shoreline change rate and forecasting (10- and 20-Year) using Digital Shoreline Analysis System (DSAS) - ArcMap plug-in.
* A co-registration process **Performance not validated and is inconsistent - users encouraged to visualise differences between Landsat and Sentinel 2 before proceeding with calculating change between them** 

The underlying approach of the CoastSat toolkit are described in detail in:
* Vos K., Splinter K.D., Harley M.D., Simmons J.A., Turner I.L. (2019). CoastSat: a Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling and Software*. 122, 104528. https://doi.org/10.1016/j.envsoft.2019.104528
Example applications and accuracy of the resulting satellite-derived shorelines are discussed in:
* Vos K., Harley M.D., Splinter K.D., Simmons J.A., Turner I.L. (2019). Sub-annual to multi-decadal shoreline variability from publicly available satellite imagery. *Coastal Engineering*. 150, 160–174. https://doi.org/10.1016/j.coastaleng.2019.04.004

Section 2 includes instructions written by Vos et al. (2019).

If errors persist please checking the section 'Potential Errors / Solutions' at the bottom of the page. Errors still occur? Please raise an issue.

Extensions to this toolbox:
- [Cleaning shoreline output + Shoreline Change using DSAS](https://github.com/sac3g15/coastsat_noc/blob/main/clean_DSAS_models_README.md) - direct references from the DSAS user guide by Himmelstoss et al. (2018).

**WARNING**. The Coastsat code here has been altered, therefore the latest updates, issues and pull requests on the Coastsat Github page may not be relevant to this workflow.

### Acknowledgements
Thanks to Kilian Vos and colleagues for providing the open-sourced Coastsat repository. Also, thanks to USGS for providing the open-sourced Digital Shoreline Analysis System plug-in. Both provide the basis for this workflow which would not exist without it. 


### Description

This document provides a user guide to mapping shoreline change rates and forecast future shorelines (over a 10- and 20-year period. Example products can be viewed/downloaded via the [EO4SD data portal](http://eo4sd.brockmann-consult.de/), which contains all datasets produced within the project. 

Previously, our understanding of shoreline dynamics was limited to single photogrammetry or in-situ beach sampling. Satellites have greatly enhanced our ability to measure coastal change over large areas and short periods. This has changed our approach from ground-based methods such as measuring the movement of morphological features (e.g. the edge of a cliff) or measuring the height of volume changes in the coastal zone (e.g. 3D mapping horizontal to the coast). Thanks to free, open-sourced tools by Vos et al. (2019) and Himmelstoss et al. (2018), large scale shoreline analysis can be carried out quickly. 

[Global shoreline change data](https://aqua-monitor.appspot.com/?datasets=shoreline) by Luijendijk et al. (2018) uses annual composites of satellite images dating from 1984-2016 and computed transects at 500m intervals across the world. Erosion and accretion are calculated based on a linear fit of shorelines delineated from each tile by classifying sandy beaches. This guide implements a similar methodology and exemplifies a similar output. Here, users can use up to date imagery to produce median composites to analyse over a custom period. A higher resolution can be achieved using smaller intervals between transects, and future shorelines can be mapped over a 10- or 20-year period. This guide outputs the following key datasets:

- Shorelines at user defined time periods
- Shoreline Change Transects - user defined intervals (here we use 50m)
- 10-year Forecast shoreline
- 10-year Forecast shoreline Uncertainty 
- 20-year Forecast shoreline
- 20-year Forecast shoreline Uncertainty
- Erosion Areas
- Accretion Areas

![picture alt](https://storage.googleapis.com/eo4sd-271513.appspot.com/Help%20Guides/Github_images/Coastsat_nocs_outline.png "Coastsat_nocs outline")


## LIMITATIONS
Landsat / Sentinel co-registration issue - The option for cor-egistration between the satellites has been set up within the code. However, the GEE functions displace() and displacement() to perform co-registration have proved inconsistent in preliminary studies, therefore the interpretation results should be taken carefully. GEE documents are relatviely unclear on the exact methods of the functions used to coregister images, but we are working on this issue. More details [here](#Comment-on-Co-registration "Goto Comment-on-Co-registration")

Cloud persistance - In cloud presistant areas and where there are few images in the median collection (count can be found in 'median_no' in shoreline attribute table), clouds can remain in the image. Due to their spectral similarity to sand, some false shorelines can be delineated.

Data gaps in Landat 7 - Despite median temporal filtering, as a result as a result of the data gap in Landsat 7, some images produce broken lines along the shore. Therefore, when extracting the baseline, some areas fail to have a baseline recording. I often fill these gaps by manually filling in the next closest (time) shoreline.


## 1. Installation
To run the examples you will need to install the coastsat environment and activate Google Earth Engine API (instructions in section 1 from the [CoastSat toolbox](https://github.com/kvos/CoastSat#1-installation)).

## 2. Usage

An example of how to run the software in a Jupyter Notebook is provided in the repository (`StudyArea_shoreline.ipyNote:`). To run this, first activate your `coastsat` environment with `conda activate coastsat` (if not already active), and then type:

```
jupyter notebook
```

A web browser window will open. Point to the directory where you downloaded this repository and click on `StudyArea_shoreline.ipyNote:`.

A Jupyter Notebook combines formatted text and code. To run the code, place your cursor inside the first of the code section and click on the `run cell` button and progress forward, pause at the second code block (in grey)

### 3. Retrieval of the satellite images - Process shoreline mapping tool
The jupyter notebook is where you can customise the processing to your needs. Here, we use an example in Senegal. The  - i.e. boundaries of study area and time, the following variables are required:

1. `Coordinate_List`- list of the coordinates of the region of interest (longitude/latitude pairs in WGS84) - see below for an example of how to extract ROI coordinates
2. `All_dates` - dates over which the images will be retrieved (e.g., `dates = ['2017-12-01', '2018-01-01']`)
3. `All_sats`: satellite missions to consider (e.g., `sat_list = ['L7', 'L8', 'S2']` for Landsat 7, 8 and Sentinel-2 collections).

        FYI.    Landsat 5 = 1984-01-01 - 2012-05-05 (Limited Coverage in some areas)
                Landsat 7 = January 1999 - Present
                Landsat 8 = April 2013 - Present
                Sentinel 2 = 2015-06-23 – Present

4. `Sitename`: name of the site (this is the name of the subfolder where the images and other accompanying files will be stored)
5. `Settings`: Some of the settings mimic the original. Here are the added parameters:
    1. `Output_epsg` = Country-specific coordinate system (see https://epsg.io/)
    2. `coregistration` = True/False
    3. Image Download parameters to refine cloud thresholds, merge Landsat satellites and shadow thresholds in Sentinel 2 
        
There are additional parameters (`min_beach_size`, `buffer_size`, `min_length_sl`, `cloud_mask_issue` and `sand_color`) that can be tuned to optimise the shoreline detection in a specific area.

### 3.1 Example of how to create a coordinate list at study site
This section demonstrates a simple way to create a coordinate list of a study area needed for the code above. It creates boxes around the coastline which are used as the limits to download a subset of satellite images. The coastline can be manually delineated if a small study area is here a country-scale analysis, likewise, the user can digitise ROI's (smaller than 100km2) instead of following the code below.

```diff
! Note:: Google earth Engine has a limited image size of ~100km2 which can be downloaded at a single time.
! The use of smaller ROIs also reduces the volume of data downloaded.
```
1. Open ArcGIS map document and save in appropriate directory
2. First, we create a coastline of the study area. (See below if the study area is large – e.g. Country-scale).
3. In the geodatabase, create a feature class (right-click geodatabase) and select a line feature.
4. In the Edit window, select ‘create features’ and draw a coastline in the region of interest.
```diff
! Note: If the study site is large, you can convert administrative boundary polygons into lines
!           from the Humanitarian Data Exchange (https://data.humdata.org/).
! 1. Download the top-level (0) boundary.
! 2. Extract into directory with map document. Import into map document geodatabase.
! 3. Check line. Does it fit the shoreline roughly (within ~800m)?
!    If not, retrieve boundary from different source or draw a rough shoreline.
! 4. Convert the boundary polygon to a polyline. 
!     1. Tool: Feature to line
!     2. Input = Top-level admin boundary
!     3. Output = Geodatabase
! 5. Use split tool to remove inland lines and save single coastal line]
```
5. Create regions of interest (ROI) boxes along coast.

    1. Tool: Strip Map Index Features
    2. Length along line = 11km
    3. Perpendicular to the line = 2
    4. Overlap = 0

6. Zoom to individual ROIs to ensure that all possible shorelines are contained within the box - Roughly each ROI box is within 300m of the shore.
    1. Edit ROIs using ‘edit vertices’ or ‘reshape’ tools.
```diff
! Tip: Raster products work in rectangular shapes, therefore thought these rois are at an angle,
!      Google will download an image at the maximum and minimum XY positions.
!      When adjusting the ROIs along the coast, keep this in mind to minimise overlap and
!      prevent longer processing times through larger images.
``` 

### 3.2 Extract Coordinates
Once the ROIs have been established, we need to extract the coordinates to a list in order to run the modified coastsat script. The tool 'extract coordinates' is used, these models combine multiple ArcGIS functions in a clear chain structure that can be viewed in the edit window (Right click model in toolbox > Edit). The model can be run by double clicking the name in the catalog pane as well as in the edit window which can be more reliable if a process fails in the geoprocessing pane.

1. In map document, in Catalog window. Under toolboxes > right click > Add Toolbox > navigate to CoastSat-master_vSC > ShorelineChangeTools > ShorelineChange.tbx
2. Double click ‘Extract Coordinates’ to open processor
3. Input ROI created above, and select the output location folder (e.g. ‘CoastSat_nocs-main’) - this is where a spreadsheet of coordinates will be created, therefore is has to be located in a folder rather than within a geodatabase
4. Run.

This will create a spreasheet of coordinates which we then need to make a list.
1. Open in excel. Delete Column OBJECTID and top row, then click save
2. Re-open the saved file in a text editor (e.g. notepad/notepad++)
3. Find and Replace.
4. Find ‘ ” ’. Replace ‘ ‘.
5. Find ‘ ]]), ’. Replace ‘ ]]),\ ‘.
6. Remove \ symbol on the last coordinate

A breakdown of the processes in the models is given in the below for clarity, understanding and scrutiny, with the hope to make this process free (i.e. no ArcGIS) in the future.

<details>
           <summary>Model Breakdown - Extract Coordinates</summary>
           <p>

1.	Extract coordinates of outer boundaries of the ROIs
    1. Feature vertices to points
    2. Input = ROIs
    3. Point type  = All vertices
2. Find XY position
    1. Add fields (XY) (x2)
    2. Input = ROI points
    3. Field type = Double
    4.Calculate geometry (right click field name)
        1. x = x-point coordinate
        2. y = y-point coordinate
        3. Use decimal degree format
3. Find max/min XY coordinates
    1. Dissolve
    2. Dissolve Field = Pg_no
    3. Statistics fields
        1. max x
        2. min x
        3. max y
        4. min y
    4. Create multipart features – checked
    5. Unsplit lines – unchecked
4.	Combine coordinates
    1. Add field (‘xytext’)
    2. Calculate field
    3. Field name = xytext
    4. xytext = "([[" + str(!MAX_x!) + "," + str(!MAX_y!) + "],[" + str(!MAX_x!) + "," + str(!MIN_y!) + "],[" + str(!MIN_x!) + "," + str(!MAX_y!) + "],["  + str(!MIN_x!) + "," + str(!MIN_y!) + "]]),"
5.	Export attribute table
    1. Right click layer in contents panel
    2. Export table
    3. Save in directory as .csv
    4. Output fields = xytext
</p>
         </details>


### 3.3	Begin processing
1. Open Jupyter Notebook (following instructions in ‘Usage’), if not already open, and navigate to `StudyArea_shoreline.ipyNote:`
2. Hit run on the initial settings and the edited code after “1. Retrieval of the images from GEE”
3. After a few minutes of processing, navigate to the data folder in Coastsat_master. Find the output. geojson file and export to software to ensure the correct output is viewed.

```diff
! Note: The following shows a common error:
!   ‘HTTPError: HTTP Error 500: Internal Server Error’.
! This is due to a network error with Google Earth Engine which is caused by a timeout using
! the getDownloadURL function – looking into this issue. This error can be frequent, and occurs
! less frequently during evenings (GMT). If this occurs:
!   i.	Find number of folders in C:\Coastsat_master\data. E.g. Tunisia_ 27.
!   ii.	Remove last folder (as shorelines haven’t been created for this folder). I.e. Delete Tunisia_27
!   iii. Cut and paste the first 26 ROIs. I keep them in code and comment them out
!   iv.	In the For loop, change sitename to “Sitename = counter + 27 “
!   v.	Re-run model. The model will continue to process shorelines from the previous point.
!   vi.	Repeat this process if it occurs again. Maintain continuous file number to prevent overwrite. 
```

**Need to Clean the shoreline output? See [clean_DSAS_models](https://github.com/sac3g15/coastsat_noc/blob/main/clean_DSAS_models_README.md)**

## Potential Errors / Solutions

    *EEException: Image.select: Parameter 'input' is required.**

This error is caused by a lack of images in the Landsat/Sentinel collection for the Co-registration process, after refining the cloud cover and date (i.e. within a 2 month window) . Simply change the date into another year, or raise the maximum cloud cover % in the SDS_download file in the Coastsat folder. Change this under the function ‘Landsat_coregistration’ for the variable ‘dated’. For example, change “L8_reference = .filterDate('2017-01-01', '2018-01-01')” to “L8_reference = .filterDate('2018-01-01', '2019-01-01')” AND do the same for Sentinel-2 9 lines below.

#### Comment on Co-registration ####

Depedant on the loction, there can be a miss alignment (or miss registration) between L8 and S2 images, which varies geographically and can exceed 38 meters [Storey et al., 2016]. It is mainly due to the residual geolocation errors in the Landsat framework which based upon the Global Land Survey images. Despite implementing a co-registration process, there are occasionally differences between shorelines between Landsat and Sentinel-2 images. Whilst local ‘rubber sheet’ deformations were used to match images from the two satellites, further interrogation of the offset images showed that the offset images used to co-register the images greatly depends on the images used in the analysis, i.e. Offset values from a two-month period in 2016 are not similar to those produced in the same two-month period in 2017. The explanation for this different is unknown at the time of this report.  It was deemed suitable to maintaining this co-registration process despite occasional improper warping to minimise the difference between Landsat and Sentinel shorelines. A further enquiry into the processes within the function displacement and displace is needed to understand the how this is affecting the co-registration between the images. Satellite mapping of shorelines is generally accurate to 10m (ref USGS), this is indicative of the uncertainties in the processing. There are continued efforts to provide a more detailed quantification of the uncertainties within the co-registration process and median composites outside this report.

Still having a problem? Post an issue in the [Issues page](https://github.com/sac3g15/coastsat_noc/issues) (please do not email).

#### Algorthim Development Decisions ####

Landsat Cloud Mask Cloud Score = 25, less than that, sand gets scored highly and is therefore masked

## References

- Himmelstoss, E.A., Henderson, R.E., Kratzmann, M.G., and Farris, A.S., 2018, Digital Shoreline Analysis System (DSAS) version 5.0 user guide: U.S. Geological Survey Open-File Report 2018–1179, 110 p., https://doi.org/10.3133/ofr20181179.
- Kalman, R.E., 1960. A new approach to linear filtering and prediction problems.
- Long, J.W., and Plant, N.G., 2012, Extended Kalman Filter framework for forecasting shoreline evolution: Geophysical Research Letters, v. 39, no. 13, p. 1–6.
- Luijendijk, A., Hagenaars, G., Ranasinghe, R., Baart, F., Donchyts, G. and Aarninkhof, S., 2018. The state of the world’s beaches. Scientific reports, 8(1), pp.1-11.
- Storey, J.; Roy, D.P.; Masek, J.; Gascon, F.; Dwyer, J.; Choate, M. A note on the temporary misregistration of Landsat-8 Operational Land Imager (OLI) and Sentinel-2 Multi Spectral Instrument (MSI) imagery. Remote Sens. Environ. 2016, 186,
- Vos, K., Harley, M.D., Splinter, K.D., Simmons, J.A. and Turner, I.L., 2019b. Sub-annual to multi-decadal shoreline variability from publicly available satellite imagery. Coastal Engineering, 150, pp.160-174.
- Vos, K., Splinter, K.D., Harley, M.D., Simmons, J.A. and Turner, I.L., 2019a. Coastsat: A Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. Environmental Modelling & Software, 122, p.104528.


