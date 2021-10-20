# Clean shorelines and calculate change
The output of the Coastsat_nocs tool produces a uncleaned product for each year of shoreline data. Here we give an exemplar model within ArcGIS, which automatically cleans the product. Methods to produce shoreline change statistics are also given, walking through the [DSAS shoreline analysis](https://www.usgs.gov/centers/whcmsc/science/digital-shoreline-analysis-system-dsas) plug-in in ArcMap. This also has the ability to forecast change data, through a simple regression for the next 10 and 20 years.

**This file contains direct references from the DSAS user guide by Himmelstoss et al. (2018).**

![picture alt](https://storage.googleapis.com/eo4sd-271513.appspot.com/Help%20Guides/Github_images/Cleaning_process_GitHub.JPG "Coastsat_nocs outline")

### 4. Clean and clip shorelines
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
4. The buffer is set to 1km around the administrative line. This is quite large, but will depend on the accruacy of the administrative line. If an accuracy admin or shoreline reference is available, reduce the buffer to a value as low as possible to remove outliers but encapsulate the shoreline between the time period defined. This adjustment should reduce the volume of manual cleaning in the next stage.

```diff
!   Note: For model structure, right click model > edit in catalog pane.
```

4.	Create an empty line feature class.
    1. Right Click geodatabase > 'new feature class'
    2. Select polyline
    3. Finish and save 'Shorelines'
5.  Once completed, open ‘Clean Shorelines’ in the same toolbox, this uses the two feature classes just created to refine the shoreline within the third model.
5.	Enter the following parameters:
    1. Iterating Folder = Folder containing geojson files (e.g. ‘C:\CoastSat-main\data’)
    2. Coordinate System = Select appropriate coordinate system by searching for the epsg code defined in the settings for shoreline processing (e.g. 32628), and select the projected coordinate system
    3. Output file = Navigate to geodatabase folder and  select "Shorelines”
    4. ROI filtered file = ROI filtered (created above)
    5. Coastal Zone = Admin buffer (created above)
6.	Run.

**If you like the repo put a star on it!**

#### 4.2 Further clean, extract baseline and add attributes ####

**Description:** Some erroneous shorelines remain through the presence of clouds, the shadow/sun interface in mountainous regions or inland waters and rivers. A manual visualisation and edit process is required, before merging all the shorelines and adding fields required for the DSAS change analysis.

1.	Manually view shorelines and remove unwanted vertices from lines using the edit window. This may include deleting unwanted/cloud present lines and unwanted years by using 'Split' or 'Edit Vertices' tools in the edit toolbar.
2.	DSAS requires a date field formatted as mm/dd/yyyy. If using yearly composite, maintain same day and month.
    1. Calculate field 
    2. New field = ‘date_shrt’
    3. Use the following expression:
        1. If individual date (original coastsat output) use:
        ```diff
        Date_shrt = reclass(!date_start!)
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
        Date_shrt = reclass(!date_start!)
        Code Block:
        def reclass(date):
            yyyy = date[:-6]
            mm = date[5:7]
            mm2 = mm[:]
            dd = date[8:10]
            dd2 = dd[-2:]
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


## References

- Himmelstoss, E.A., Henderson, R.E., Kratzmann, M.G., and Farris, A.S., 2018, Digital Shoreline Analysis System (DSAS) version 5.0 user guide: U.S. Geological Survey Open-File Report 2018–1179, 110 p., https://doi.org/10.3133/ofr20181179.
- Kalman, R.E., 1960. A new approach to linear filtering and prediction problems.
- Long, J.W., and Plant, N.G., 2012, Extended Kalman Filter framework for forecasting shoreline evolution: Geophysical Research Letters, v. 39, no. 13, p. 1–6.
- Luijendijk, A., Hagenaars, G., Ranasinghe, R., Baart, F., Donchyts, G. and Aarninkhof, S., 2018. The state of the world’s beaches. Scientific reports, 8(1), pp.1-11.
- Storey, J.; Roy, D.P.; Masek, J.; Gascon, F.; Dwyer, J.; Choate, M. A note on the temporary misregistration of Landsat-8 Operational Land Imager (OLI) and Sentinel-2 Multi Spectral Instrument (MSI) imagery. Remote Sens. Environ. 2016, 186,
- Vos, K., Harley, M.D., Splinter, K.D., Simmons, J.A. and Turner, I.L., 2019b. Sub-annual to multi-decadal shoreline variability from publicly available satellite imagery. Coastal Engineering, 150, pp.160-174.
- Vos, K., Splinter, K.D., Harley, M.D., Simmons, J.A. and Turner, I.L., 2019a. Coastsat: A Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. Environmental Modelling & Software, 122, p.104528.


