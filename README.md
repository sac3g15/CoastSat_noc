# CoastSat_nocs

CoastSat_nocs is an open-source software toolkit written in Python that enables users to obtain time-series of shoreline position at any coastline worldwide from 30+ years (and growing) of Landsat 7, 8 and Sentinel-2. This is a toolkit which has been developed by Vos et al., 2019 originally named Coastsat found here (https://github.com/kvos/CoastSat).

Coastsat_nocs has banched from coastsat to include the following changes:
* Retrieve median composites of satellite data - I.e. ‘['2000-01-01', '2000-12-31']’ creates a single shoreline from all satellite images in the year 2000.
* The user can loop through multiple study areas rather than a single polygon
* Multiple date ranges (+ satellites) can be specified
* A co-registration process from Landsat to Sentinel-2*
* Automated shoreline editing models
* Instructions for shoreline change rate and forecasting (10- and 20-Year) using Digital Shoreline Analysis System (DSAS) - ArcMap plug-in.
* Landsat 5 not available in this code – working on solution

*Coregistration process uses displace() and displacement() from GEE. In some areas there remains a coregistration issue which can be seen when there are large and unexpected distances between shorelines delineated between Landsat and Sentinel images. GEE documents are relatviely unclear on the exact methods of the functions used to coregister images, but we are working on this issue.

The underlying approach of the CoastSat toolkit are described in detail in:
* Vos K., Splinter K.D., Harley M.D., Simmons J.A., Turner I.L. (2019). CoastSat: a Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling and Software*. 122, 104528. https://doi.org/10.1016/j.envsoft.2019.104528
Example applications and accuracy of the resulting satellite-derived shorelines are discussed in:
* Vos K., Harley M.D., Splinter K.D., Simmons J.A., Turner I.L. (2019). Sub-annual to multi-decadal shoreline variability from publicly available satellite imagery. *Coastal Engineering*. 150, 160–174. https://doi.org/10.1016/j.coastaleng.2019.04.004

Section 2.1 and 2.2 includes direct instructions written by Vos et al. (2019). Section 2.3 includes direct references from the DSAS user guide by Himmelstoss et al. (2018).
**WARNING**. The Coastsat code here has been altered, therefore the latest updates, issues and pull requests on Github may not be relevant to this workflow. The following changes have been made to the Coastsat module:


### Description

Satellite remote sensing can provide low-cost long-term shoreline data capable of resolving the temporal scales of interest to coastal scientists and engineers at sites where no in-situ field measurements are available. CoastSat_noc enables the non-expert user to extract shorelines from Landsat 7, Landsat 8 and Sentinel-2 images.
The shoreline detection algorithm implemented in CoastSat is optimised for sandy beach coastlines.   It combines a sub-pixel border segmentation and an image classification component, which refines the segmentation into four distinct categories such that the shoreline detection is specific to the sand/water interface.

The toolbox has three main functionalities:
- assisted retrieval from Google Earth Engine of all available satellite images spanning the user-defined region of interest and time period
- automated extraction of shorelines from all the selected images using a sub-pixel resolution technique
- intersection of the 2D shorelines with user-defined shore-normal transects


**If you like the repo put a star on it!**

## 1. Installation
To run the examples you will need to install the coastsat environment and activate Google Earth Engine API (instructions in the main [CoastSat toolbox] (https://github.com/kvos/CoastSat)).

## 2. Usage

An example of how to run the software in a Jupyter Notebook is provided in the repository (`StudyArea_shoreline.ipyNote:`). To run this, first activate your `coastsat` environment with `conda activate coastsat` (if not already active), and then type:

```
jupyter notebook
```

A web browser window will open. Point to the directory where you downloaded this repository and click on `StudyArea_shoreline.ipyNote:`.

A Jupyter Notebook combines formatted text and code. To run the code, place your cursor inside one of the code sections and click on the `run cell` button and progress forward.

### 3. Retrieval of the satellite images - Process shoreline mapping tool
To retrieve from the GEE server the available satellite images cropped around the user-defined region of coastline for the particular time period of interest, the following variables are required:

Task time = ~10 mins

1.  Open Jupyter Notebook (following instructions in ‘Usage’)
    1. Download ‘CoastSat-master_vSC’ and navigate to StudyArea_shoreline, copy, then rename StudyArea_shoreline.ipyNote:. E.g. ‘Tunisia_shoreline_2000_2020’
    2. Edit the following variables:
2. `Coordinate_List`- list of the coordinates of the region of interest (longitude/latitude pairs in WGS84) - see below for an example of how to extract ROI coordinates
3. `All_dates` - dates over which the images will be retrieved (e.g., `dates = ['2017-12-01', '2018-01-01']`)
4. `All_sats`: satellite missions to consider (e.g., `sat_list = ['L7', 'L8', 'S2']` for Landsat 7, 8 and Sentinel-2 collections)
5. `Sitename`: name of the site (this is the name of the subfolder where the images and other accompanying files will be stored)
6. `Settings`
    1. `Output_epsg` = Country-specific coordinate system (see https://epsg.io/)

### 3.1 Example of how to create a coordinate list at study site
This section demonstrates a simple way to create a coordinate list of a study area needed for the code above. It creates boxes around the coastline which are used as the limits to download a subset of satellite images. The coastline can be manually delineated if a small study area is here a country-scale analysis 
Task time = ~10 mins
1. Open ArcGIS map document and save in appropriate directory
2. First, we create a coastline of the study area. (See Note: below if the study area is large – e.g. Country-scale).
3. In the geodatabase, create a feature class (right-click geodatabase) and select a line feature.
4. In the Edit window, select ‘create features’ and draw a coastline in the region of interest.

```diff
! **Note**: If the study site is large, you can convert administrative boundary polygons into lines
!           from the Humanitarian Data Exchange (https://data.humdata.org/).
! Download the top-level (0) boundary.
! 1. Extract into directory with map document. Import into map document geodatabase.
! 2. Check line. Does it fit the shoreline roughly (within ~800m)?
!    If not, retrieve boundary from different source or draw a rough shoreline.
! 3. Convert the boundary polygon to a polyline. 
!     1. Feature to line
!     2. Input = Top-level admin boundary
!     3. Output = Geodatabase
! 4. Use split tool to remove inland lines and save single coastal line]
```

5. Create regions of interest (ROI) boxes along coast.
```Note:: Google earth Engine has a limited image size of ~100km2 which can be downloaded at a single time. The use of smaller ROIs also reduces the volume of data downloaded.
a.	Strip Map Index Features
b.	Length along line = 11km
c.	Perpendicular to the line = 2
d.	Overlap = 0
vi.	Zoom to individual ROIs to ensure that all possible shorelines are contained within the box.
a.	Edit those using ‘edit vertices’ or ‘reshape’ tools.
Note:: Try not to create/remove boxes, if needed, maintain a continuous page number between ROIs
I.	Extract Coordinates
Once the ROIs have been established, we need to extract the coordinates to a list in order to run the modified coastsat script. The first of four ArcGIS models is used. These models combine multiple ArcGIS functions in a clear chain structure that can be viewed in the edit window (Right click model in toolbox > Edit). The model can also be run via the edit window which can be more reliable if a process fails. A breakdown of the processes in the models is below for clarity, understanding and scrutiny, with the hope to make this process full open sourced in the future.
i.	In map document, in Catalog window. Under toolboxes > right click > Add Toolbox > navigate to CoastSat-master_vSC > ShorelineChangeTools > ShorelineChange.tbx
ii.	Double click ‘Extract Coordinates’ to open processor
iii.	Input ROIs and the output location folder (e.g. ‘CoastSat-master_vSC’)
iv.	Run.

Once the table is saved the coordinates are in a table format, but we need a list…
v.	Open in excel. Delete Column OBJECTID and top row, then click save
vi.	Re-open the saved file in a text editor (notepad/notepad++)
vii.	Find and Replace.
viii.	Find ‘ ” ’. Replace ‘ ‘.
ix.	Find ‘ ]]), ’. Replace ‘ ]]),\ ‘.
x.	Remove \ symbol on the last coordinate

## Issues
Having a problem? Post an issue in the [Issues page](https://github.com/kvos/coastsat/issues) (please do not email).

## Contributing
If you are willing to contribute, check out our todo list in the [Projects page](https://github.com/kvos/CoastSat/projects/1).
1. Fork the repository (https://github.com/kvos/coastsat/fork).
A fork is a copy on which you can make your changes.
2. Create a new branch on your fork
3. Commit your changes and push them to your branch
4. When the branch is ready to be merged, create a Pull Request (how to make a clean pull request explained [here](https://gist.github.com/MarcDiethelm/7303312))

## References

1. Vos K., Harley M.D., Splinter K.D., Simmons J.A., Turner I.L. (2019). Sub-annual to multi-decadal shoreline variability from publicly available satellite imagery. *Coastal Engineering*. 150, 160–174. https://doi.org/10.1016/j.coastaleng.2019.04.004

2. Vos K., Splinter K.D.,Harley M.D., Simmons J.A., Turner I.L. (2019). CoastSat: a Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling and Software*. 122, 104528. https://doi.org/10.1016/j.envsoft.2019.104528

3. Training dataset used for pixel classification in CoastSat: https://doi.org/10.5281/zenodo.3334147
