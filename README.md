# PopNet
PopNet uses a Convolutional Neural Network to predict the future spatial population distribution based on existing population projections.

> The code in this repository is a result of a Master's thesis in Geoinformatics at Aalborg University Copenhagen, available for download from the [AAU Project Library](https://projekter.aau.dk/projekter/en/studentthesis/projecting-spatial-population-distribution-using-a-convolutional-neural-network(4a535d5e-73b7-4088-9559-9c28da1528d6).html). The thesis contains a much more detailed description of what is going on here, so please refer to that if you get stuck along the way with the condensed documentation provided here.

⚡️ Note that the instructions provided here are currently **limited to countries in Europe**. Most of the datasets used in the process are only available for EU countries and would need to be replaced with other data when running the analysis for countries outside the EU.

## Instructions/dependencies

For the data preparation part, the following dependencies need to be installed:

- [GDAL](https://www.gdal.org)
- [PostGIS](https://postgis.net)
- [Python3](https://www.python.org) with:
	- [osgeo.ogr](https://gdal.org/python/)
	- [osgeo.gdal](https://gdal.org/python/)
	- [psycopg2](http://initd.org/psycopg/)

Besides PostGIS and the GDAL binaries, the Python dependencies can be set up in a separate [Conda](https://www.anaconda.com/download/) environment by running:

```
conda create --name popnet_prepare
conda activate popnet_prepare
conda install gdal
conda install psycopg2
```

The following datasets need to be downloaded:

- [Corine Land Cover 1990](https://land.copernicus.eu/pan-european/corine-land-cover/clc-1990?tab=download) in SpatiaLite format
- [Corine Land Cover 2012](https://land.copernicus.eu/pan-european/corine-land-cover/clc-2012?tab=download) in SpatiaLite format
- [Copernicus slope](https://land.copernicus.eu/pan-european/satellite-derived-products/eu-dem/eu-dem-v1-0-and-derived-products/slope?tab=download) (The *Slope Full European Coverage* file)
- [European train stations](https://public.opendatasoft.com/explore/dataset/european-train-stations/information/) in shape file format (```.shp```)
- [Administrative boundaries](https://gadm.org/download_world.html) at levels 0 and 2 in shape file format (```.shp```)  
- [Lakes](https://www.eea.europa.eu/data-and-maps/data/european-catchments-and-rivers-network#tab-gis-data)  in shape file format (```.shp```). The database comes in SpatiaLite format; I had to export the lakes layer from it and retroject it to EPSG:4326 to make the code run
- [Population grid](http://cidportal.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GPW4_GLOBE_R2015A/) from JRC's [Global Human Settlement Layer](https://ghsl.jrc.ec.europa.eu/datasets.php) (each layer needs to be downloaded for 1975, 1990, 2000, and 2015 at 250m resolution)
- [Global Roads Open Access Data Set](http://sedac.ciesin.columbia.edu/data/set/groads-global-roads-open-access-v1/data-download) in shape file format (```.shp```)  


Everything should be place in a folder called ```data```, sitting in the ```data_scripts``` folder. Its content should look like this:


        data
        ├── GADM
        │   ├── gadm36_0.cpg
        │   ├── gadm36_0.dbf
        │   ├── gadm36_0.prj
        │   ├── gadm36_0.shp
        │   ├── gadm36_0.shx
        │   ├── gadm36_1.cpg
        │   ├── gadm36_1.dbf
        │   ├── gadm36_1.prj
        │   ├── gadm36_1.shp
        │   ├── gadm36_1.shx
        │   ├── gadm36_2.cpg
        │   ├── gadm36_2.dbf
        │   ├── gadm36_2.prj
        │   ├── gadm36_2.shp
        │   ├── gadm36_2.shx
        │   ├── gadm36_3.cpg
        │   ├── gadm36_3.dbf
        │   ├── gadm36_3.prj
        │   ├── gadm36_3.shp
        │   ├── gadm36_3.shx
        │   ├── gadm36_4.cpg
        │   ├── gadm36_4.dbf
        │   ├── gadm36_4.prj
        │   ├── gadm36_4.shp
        │   ├── gadm36_4.shx
        │   ├── gadm36_5.cpg
        │   ├── gadm36_5.dbf
        │   ├── gadm36_5.prj
        │   ├── gadm36_5.shp
        │   └── gadm36_5.shx
        ├── GHS
        │   ├── GHS_POP_GPW41975_GLOBE_R2015A_54009_250_v1_0
        │   │   ├── GHSL_data_access_v1.3.pdf
        │   │   ├── GHS_POP_GPW41975_GLOBE_R2015A_54009_250_v1_0.tif
        │   │   ├── GHS_POP_GPW41975_GLOBE_R2015A_54009_250_v1_0.tif.ovr
        │   │   └── GHS_POP_GPW41975_GLOBE_R2015A_54009_250_v1_0.tif.xml
        │   ├── GHS_POP_GPW41990_GLOBE_R2015A_54009_250_v1_0
        │   │   ├── GHSL_data_access_v1.3.pdf
        │   │   ├── GHS_POP_GPW41990_GLOBE_R2015A_54009_250_v1_0.tif
        │   │   ├── GHS_POP_GPW41990_GLOBE_R2015A_54009_250_v1_0.tif.aux.xml
        │   │   ├── GHS_POP_GPW41990_GLOBE_R2015A_54009_250_v1_0.tif.ovr
        │   │   └── GHS_POP_GPW41990_GLOBE_R2015A_54009_250_v1_0.tif.xml
        │   ├── GHS_POP_GPW42000_GLOBE_R2015A_54009_250_v1_0
        │   │   ├── GHSL_data_access_v1.3.pdf
        │   │   ├── GHS_POP_GPW42000_GLOBE_R2015A_54009_250_v1_0.tif
        │   │   ├── GHS_POP_GPW42000_GLOBE_R2015A_54009_250_v1_0.tif.aux.xml
        │   │   ├── GHS_POP_GPW42000_GLOBE_R2015A_54009_250_v1_0.tif.ovr
        │   │   └── GHS_POP_GPW42000_GLOBE_R2015A_54009_250_v1_0.tif.xml
        │   └── GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0
        │       ├── GHSL_data_access_v1.3.pdf
        │       ├── GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tfw
        │       ├── GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tif
        │       ├── GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tif.aux.xml
        │       ├── GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tif.ovr
        │       └── GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tif.xml
        └── ancillary
            ├── corine
            │   ├── clc12_Version_18_5a_sqLite
            │   │   ├── CLC_country_coverage_v18_5.pdf
            │   │   ├── How\ use\ ESRI\ FGDB\ in\ QGIS.doc
            │   │   ├── Legend
            │   │   │   ├── CLC_legend.clr
            │   │   │   ├── clc_legend.avl
            │   │   │   ├── clc_legend.csv
            │   │   │   ├── clc_legend.dbf
            │   │   │   ├── clc_legend.lyr
            │   │   │   ├── clc_legend.qml
            │   │   │   ├── clc_legend.sld
            │   │   │   ├── clc_legend.txt
            │   │   │   ├── clc_legend.xls
            │   │   │   └── clc_legend_qgis.txt
            │   │   ├── clc12_Version_18_5.sqlite
            │   │   ├── clc_12_18_5a_vector.xml
            │   │   ├── readme_V18_5.txt
            │   │   └── readme_V18_5_clc12.txt
            │   └── clc90_Version_18_5_sqlite
            │       ├── CLC_country_coverage_v18_5.pdf
            │       ├── How\ use\ ESRI\ FGDB\ in\ QGIS.doc
            │       ├── Legend
            │       │   ├── CLC_legend.clr
            │       │   ├── clc_legend.avl
            │       │   ├── clc_legend.csv
            │       │   ├── clc_legend.dbf
            │       │   ├── clc_legend.lyr
            │       │   ├── clc_legend.qml
            │       │   ├── clc_legend.sld
            │       │   ├── clc_legend.txt
            │       │   ├── clc_legend.xls
            │       │   └── clc_legend_qgis.txt
            │       ├── clc90_Version_18_5.sqlite
            │       ├── readme_V18_5.txt
            │       └── readme_V18_5_clc90.txt
            ├── eu_lakes.cpg
            ├── eu_lakes.dbf
            ├── eu_lakes.prj
            ├── eu_lakes.qpj
            ├── eu_lakes.shp
            ├── eu_lakes.shx
            ├── european-train-stations
            │   ├── european-train-stations.dbf
            │   ├── european-train-stations.prj
            │   ├── european-train-stations.shp
            │   └── european-train-stations.shx
            ├── groads_europe
            │   ├── gROADS-v1-europe.dbf
            │   ├── gROADS-v1-europe.prj
            │   ├── gROADS-v1-europe.sbn
            │   ├── gROADS-v1-europe.sbx
            │   ├── gROADS-v1-europe.shp
            │   ├── gROADS-v1-europe.shp.xml
            │   └── gROADS-v1-europe.shx
            └── slope
                └── eudem_slop_3035_europe.tif


When everything is in place, you are ready to run ```main.py``` to run the data preparation. Make sure to check and eventually change the configuration options at the top of that script.

Good luck...
