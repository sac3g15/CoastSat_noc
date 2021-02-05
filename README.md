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

The underlying approach of the CoastSat toolkit are described in detail in:
* Vos K., Splinter K.D., Harley M.D., Simmons J.A., Turner I.L. (2019). CoastSat: a Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling and Software*. 122, 104528. https://doi.org/10.1016/j.envsoft.2019.104528
Example applications and accuracy of the resulting satellite-derived shorelines are discussed in:
* Vos K., Harley M.D., Splinter K.D., Simmons J.A., Turner I.L. (2019). Sub-annual to multi-decadal shoreline variability from publicly available satellite imagery. *Coastal Engineering*. 150, 160–174. https://doi.org/10.1016/j.coastaleng.2019.04.004

Section 2 includes instructions written by Vos et al. (2019).

Extensions to this toolbox:
- [Cleaning shoreline output + Shoreline Change using DSAS]()         
 If you wish to clean the output of the shoreline data  Section 5 includes direct references from the DSAS user guide by Himmelstoss et al. (2018).

**WARNING**. The Coastsat code here has been altered, therefore the latest updates, issues and pull requests on Github may not be relevant to this workflow.

### Acknowledgements
Thanks to Kilian Vos and colleagues for providing the open-sourced Coastsat repository. Also, thanks to USGS for providing the open-sourced Digital Shoreline Analysis System plug-in. Both provide the basis for this workflow which would not exist without it. 


### Description

This document provides a user guide to mapping shoreline change rates and forecast future shorelines (over a 10- and 20-year period. Example products can be viewed/downloaded via the [EO4SD data portal](http://eo4sd.brockmann-consult.de/), which contains all datasets produced within the project. 

Previously, our understanding of shoreline dynamics was limited to single photogrammetry or in-situ beach sampling. Satellites have greatly enhanced our ability to measure coastal change over large areas and short periods. This has changed our approach from ground-based methods such as measuring the movement of morphological features (e.g. the edge of a cliff) or measuring the height of volume changes in the coastal zone (e.g. 3D mapping horizontal to the coast). Thanks to free, open-sourced tools by Vos et al. (2019) and Himmelstoss et al. (2018), large scale shoreline analysis can be carried out quickly. 

[Global shoreline change data](https://aqua-monitor.appspot.com/?datasets=shoreline) by Luijendijk et al. (2018) which uses annual composites of satellite images dating from 1984-2016 and computed transects at 500m intervals across the world. Erosion and accretion are calculated based on a linear fit of shorelines delineated from each tile by classifying sandy beaches. This guide implements a similar methodology and exemplifies a similar output. Here, users can use up to date imagery and define their own time periods of median composites to analyse shorelines at a yearly or monthly basis. A higher resolution can be achieved using smaller intervals between transects, and future shorelines can be mapped over a 10- or 20-year period. This guide outputs the following key datasets:

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
Landsat / Sentinel co-registration issue - Coregistration between the satellites was originally set up within the code, however, inconsistencies in the GEE functions displace() and displacement() resulted in this being temporally removed from the code. GEE documents are relatviely unclear on the exact methods of the functions used to coregister images, but we are working on this issue. More details [here](#Comment-on-Co-registration "Goto Comment-on-Co-registration")

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

A Jupyter Notebook combines formatted text and code. To run the code, place your cursor inside one of the code sections and click on the `run cell` button and progress forward.

### 3. Retrieval of the satellite images - Process shoreline mapping tool
The jupyter notebook is where you can customise the processing to your needs - i.e. boundaries of study area and time, the following variables are required:

1. `Coordinate_List`- list of the coordinates of the region of interest (longitude/latitude pairs in WGS84) - see below for an example of how to extract ROI coordinates
2. `All_dates` - dates over which the images will be retrieved (e.g., `dates = ['2017-12-01', '2018-01-01']`)
3. `All_sats`: satellite missions to consider (e.g., `sat_list = ['L7', 'L8', 'S2']` for Landsat 7, 8 and Sentinel-2 collections).

        FYI.    Landsat 5 = 1984-01-01 - 2012-05-05 (Limited Coverage in some areas)
                Landsat 7 = January 1999 - Present
                Landsat 8 = April 2013 - Present
                Sentinel 2 = 2015-06-23 – Present

4. `Sitename`: name of the site (this is the name of the subfolder where the images and other accompanying files will be stored)
5. `Settings`
    1. `Output_epsg` = Country-specific coordinate system (see https://epsg.io/)

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
!     1. Feature to line
!     2. Input = Top-level admin boundary
!     3. Output = Geodatabase
! 5. Use split tool to remove inland lines and save single coastal line]
```
5. Create regions of interest (ROI) boxes along coast.

    1. Strip Map Index Features
    2. Length along line = 11km
    3. Perpendicular to the line = 2
    4. Overlap = 0

6. Zoom to individual ROIs to ensure that all possible shorelines are contained within the box - Roughly each ROI box is within 300m of the shore.
    1. Edit ROIs using ‘edit vertices’ or ‘reshape’ tools.
```diff
! Tip: Raster products work in rectangular shapes, therefore thought these rois are at an angle,
!      Google will download an image at the maximum and minimum XY positions.
!      When adijusting the ROIs along the coast, keep this in mind to minimise overlap and
!      prevent longer processing times through larger images.
``` 

### 3.2 Extract Coordinates
Once the ROIs have been established, we need to extract the coordinates to a list in order to run the modified coastsat script. The first of four ArcGIS models is used. These models combine multiple ArcGIS functions in a clear chain structure that can be viewed in the edit window (Right click model in toolbox > Edit). The model can be run by double clicking the name in the catalog pane as well as in the edit window which can be more reliable if a process fails in the geoprocessing pane.

1. In map document, in Catalog window. Under toolboxes > right click > Add Toolbox > navigate to CoastSat-master_vSC > ShorelineChangeTools > ShorelineChange.tbx
2. Double click ‘Extract Coordinates’ to open processor
3. Input ROI created above, and select the output location folder (e.g. ‘CoastSat-master_vSC’) - this is where a spreadsheet of coordinates will be created, therefore is has to be located in a folder rather than within a geodatabase
4. Run.

This will create a spreasheet of coordinates which we then need to make a list.
1. Open in excel. Delete Column OBJECTID and top row, then click save
2. Re-open the saved file in a text editor (e.g. notepad/notepad++)
3. Find and Replace.
4. Find ‘ ” ’. Replace ‘ ‘.
5. Find ‘ ]]), ’. Replace ‘ ]]),\ ‘.
6. Remove \ symbol on the last coordinate

A breakdown of the processes in the models is given in the below for clarity, understanding and scrutiny, with the hope to make this process full open sourced (i.e. no ArcGIS) in the future.

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
1. Open Jupyter Notebook (following instructions in ‘Usage’) if not already open and navigate to `StudyArea_shoreline.ipyNote:`
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

### 4. Clean and clip shorelines
**Description:** The output geojson (see below) is a single line which connects all delineated shorelines as well as false lines created by inland or offshore features. Therefore, the raw shorelines produced by the Coastsat module need to be cleaned and clipped to the region of interest.

#### 4.1 Define Shoreline Cleaning Variables and clean shorelines ####
Task time = ~2 mins (+ ~5 mins processing time per 100km2 zone)

**Description:** Despite defining 0% overlap, the ROIs created above will have small interlocking areas between them, these need to be removed so that the shorelines processed can be clipped to prevent overlapping lines. A buffer zone is also created to remove unwanted lines away from the coast. These processes are completed within the second ArcGIS model ‘Shoreline_cleaning_presettings’.
1. Open ArcMap/Pro Map document. In Catalog menu, under toolboxes, double click on ‘Shoreline_cleaning_presettings’
2. Input the following:
    1. ROI filtered output = geodatabase directory > filename (e.g. ‘countryname_ROIs_filtered’)
    2. Regions of Interest = ROIs created above
    3. Administrative Boundary Line = Country admin line
    4. Coastal Zone = Admin Buffer
3. Run.
4. The buffer is set to 1km around the administrative line. THis is quite large, but will depend on the accruacy of the administrative line. If an accuracy admin or shoreline reference is available, reduce the buffer to ~500m which should reduce the volume of manual cleaning in the next stage.

```diff
!   Note: Model detail deemed not necessary for outline,
!         for model structure right click model > edit in catalog pane.
```

4.	Once completed, open ‘Clean Shorelines’ in the same toolbox, this uses the two feature classes just created to refine the shoreline within the third model.
5.	Enter the following parameters:
    1. Iterating Folder = Folder containing geojson files (e.g. ‘C:\Documents\EO4SD\Tunisia\CoastSat-master\data’
    2. Coordinate System = Select appropriate coordinate system by searching for the epsg code defined in the settings for shoreline processing (e.g. 26191), and select the projected coordinate system
    3. Output file = Navigate to batch geodatabase folder and enter “%Name%_cleaned”
    4. ROI filtered file = ROI filtered (created above)
    5. Coastal Zone = Admin buffer (created above)
6.	Run.

```diff
! Note: Using ‘%Name%’ in ArcGIS modal builder prevents overwriting the files
!       by naming each file as its original name in the ‘Coastsat-master\data’ folder.
```
**If you like the repo put a star on it!**

#### 4.2 Further clean, extract baseline and add attributes ####
Task time = ~15mins (dependant on size/complexity of study area)

**Description:** Some erroneous shorelines remain through the presence of clouds, the shadow/sun interface in mountainous regions or inland waters and rivers. A manual visualisation and edit process is required, before merging all the shorelines and adding fields required for the DSAS change analysis.

1.	Manually view shorelines and remove unwanted vertices from lines using the edit window. This may include deleting unwanted/cloud present lines and unwanted years by using Split or Edit Vertices in the edit toolbar.
2.	Combine all shorelines in output batch directory.
    1. Merge
    2. Input = shorelines E.g. ‘Tunisia_1_output_cleaned’, ‘Tunisia_2_output_cleaned’, …
    3. Output = ‘Tunisia_shoreline_2000_2020’
    4. Check the box Add source information to output
3.	DSAS requires a date field formatted as mm/dd/yyyy. If using yearly composite, maintain same day and month.
    1. Calculate field 
    2. New field = ‘date_long’
    3. Use the following expression:
        1. If individual date (original coastsat output) use:
        ```diff
        date_long = reclass(!date!)
        Code Block:
        def reclass(date):
            yyyy = date[:-15]
            mm = date[:-12]
            mm2 = mm[-2:]
            dd = date[:-9]
            dd2 = dd[-2:]
            return mm2 + "/" + dd2 + "/" + yyyy
        ```
        2. If median composite use:
        ```diff
        date_long = reclass(!date!)
        Code Block:
        def reclass(date):
            yyyy = str(int(date))
            mm = "01"
            dd = "01"
            return mm + "/" + dd + "/" + yyyy
        ```
4.	Select by attributes. Year = 2000 (or earliest year shoreline).
    1. Explore along the shoreline to check that a near-complete line has been selected. If not, add next earliest year to selection (by holding the shift button and clicking on the shoreline).
5.	Export selected and save as baseline - ‘Tunisia_baseline_2000_2020’.

##	5. Shoreline Change Statistics (DSAS) ##
Task time = ~1.5 hrs (+1 hr processing time)

Before installing the DSAS v5.0 application, ensure that your system meets the following requirements (installation of new
applications will require administrative rights).
1. Windows 7 or Windows 10 operating system.
2. ArcGIS Desktop Standard 10.4 or 10.5.
    1. ArcGIS .NET support feature (installed by default)
    2. Microsoft .NET framework of 4.5.2 or later (installed by default)
3. The computer’s date format must be set to English (USA), mm/dd/yyyy.
    1. To check your operating system, Click the Start button, enter “Computer” in the search box, right-click “Computer,” and then click “Properties.” Look under “Windows edition” for the version and edition of Windows that your computer is running.
    2. To check the ArcMap version: From ArcMap or ArcCatalog, select Help >> About ArcMap to see the ArcGIS version number.
    3. To verify the date format, go to the Control Panel menu and choose the option for Region and Language. Select “English(United States),” for the format, and make sure the date format is set to “mm/dd/yyyy.”

**Description:** Digital Shoreline Analysis System is a freely available software application that works within the Esri Geographic Information System (ArcGIS) software. DSAS computes rate-of-change statistics for a time series of shoreline vector data. Install the DSAS plug-in [here](https://www.usgs.gov/centers/whcmsc/science/digital-shoreline-analysis-system-dsas?qt-science_center_objects=0#qt-science_center_objects).

1.	Open ArcMap.
2.	In the Catalog panel, connect to the map document folder with the shoreline data.
3.	Create new personal file geodatabase by right clicking on the newly connected folder. New > personal file geodatabase. Rename ‘Shoreline Rates.mdb’
4.	Import baseline and merged shorelines
    1. Right click on ‘Shoreline Rates.mdb’ > Import > Multiple Feature Classes
    2. Navigate to shoreline datasets - ‘Tunisia_baseline_2000_2020’, ‘Tunisia_shoreline_2000_2020’
5.	DSAS plug-in requires the creation of the following fields via the attribute automator
    1. For the baseline, add the DSAS ID field and DSAS search
    2. Populated these fields using calculate field
    3. DSAS ID = ObjectID
    4. DSAS_search = 170

### 5.1 Cast Transects ###
**Description:** Here, the baseline is created by the oldest recorded shoreline delineated using satellite imagery, however a user-defined or secondary shoreline can be substituted. The 170m search limit is set here to prevent the creation of large transects in complex coastal locations such as estuaries or ports, but customise this based on the rate of change in your coastlines. Transects created at this stage greatly impacts the change statistics and should be interpreted carefully. Shallow sloping and frequently changing coastlines are likely to result in transects with extreme erosion or accretion rates and high errors and uncertainties.  It is highly recommended that careful visualization and editing should be carried out along in the study area. Users should look for transects which appear correctly orientated and extent to a reasonable distance between delineated shorelines.

1. Input the following
    1. 170 from baseline
    2. 50 spacing
    3. 500 smoothing distance
    4. Check box - Clip transects to shoreline

### 5.2 Calculate Change Statistics ###
1.	Set statistics (Linear regression)
2.	Shoreline intersection threshold = no. of lines
    1. Select all statistics
    2. Apply shoreline intersection threshold – 6
    3. 95% confidence interval
    4. Create report

### 5.3 Beta Shoreline Forecasting ###
**Description:** The DSAS forecast uses a Kalman filter (Kalman, 1960) to combine observed shoreline positions with model-derived positions to forecast a future shoreline position (10- or 20-year) as developed by Long and Plant (2012). The model begins at the first time-step (the date of the earliest survey) and predicts/forecasts the shoreline position for each successive time step until another shoreline observation is encountered. Whenever a shoreline observation is encountered, the Kalman Filter performs an analysis to minimize the error between the modelled and observed shoreline positions to improve the forecast, including updating the rate and uncertainties (Long and Plant, 2012). 

```diff
! Note: As noted in the DSAS user guide, the forecasts produced by this tool should be used with caution.
!     The processes driving shoreline change are complicated and not always available as model inputs.
!     Many factors that may be important are not considered in this methodology or accounted for within
!     the uncertainty. This methodology assumes that a linear regression thorough past shoreline positions
!     is a good approximation for future shoreline positions; this assumption will not always be valid.
```

### 5.4 Area Statistics ###
Summary statistics are a common necessity among coastal management at both the national and local scale. The following section outlines a simply methodology to calculate areal statistics using
Smoothing lines forecast and 2020 line – 50m PAEK
Line to Feature – input both lines
Buffer left side to cover all polygons to the left of the 2020 shoreline.


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


