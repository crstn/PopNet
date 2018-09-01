# Imports
import subprocess
import os
import gdal
import ogr
import osr
import psycopg2
import time
from postgres_queries import run_queries
from rast_to_vec_grid import rasttovecgrid
from postgres_to_raster import psqltoshp
from postgres_to_raster import shptoraster
from import_to_postgres import import_to_postgres

def process_data(country, pgpath, pghost, pgport, pguser, pgpassword, pgdatabase, ancillary_data_folder_path,
                 gadm_folder_path, ghs_folder_path, temp_folder_path, merge_folder_path, finished_data_path,
                 python_scripts_folder_path, gdal_rasterize_path, init_prep, init_import_to_postgres,
                 init_run_queries, init_export_data, init_rasterize_data, init_merge_data):
    #Start total preparation time timer
    start_total_algorithm_timer = time.time()

    # Create temp folder, merge folder and finished_data folder if they don't exist ----------------------------------------------------------------------
    # create temp folder
    if not os.path.exists(temp_folder_path):
        os.makedirs(temp_folder_path)
    # create merge folder
    if not os.path.exists(merge_folder_path):
        os.makedirs(merge_folder_path)
    # create finished_data folder
    if not os.path.exists(finished_data_path):
        os.makedirs(finished_data_path)
    # create country folder within the finished_data folder
    country_path = os.path.join(finished_data_path,"{0}".format(country))
    if not os.path.exists(country_path):
        os.makedirs(country_path)

    # Extracting country from GADM and creating bounding box -----------------------------------------------------------
    if init_prep == "yes":
        print("------------------------------ PROCESSING POPULATION RASTER ------------------------------")
        print("Extracting {0} from GADM data layer".format(country))
        # select country in GADM and write to new file
        input_gadm_dataset = os.path.join(gadm_folder_path, "gadm28_adm0.shp")
        output_country_shp = os.path.join(temp_folder_path,"GADM_{0}.shp".format(country))
        sql_statement = "NAME_ENGLI='{0}'".format(country)
        country_shp = 'ogr2ogr -where {0} -f "ESRI Shapefile"  {1} {2} -lco ENCODING=UTF-8'\
            .format(sql_statement, output_country_shp, input_gadm_dataset)
        subprocess.call(country_shp, shell=True)

        # create bounding box around chosen country
        # Get a Layer's Extent
        inShapefile = output_country_shp
        inDriver = ogr.GetDriverByName("ESRI Shapefile")
        inDataSource = inDriver.Open(inShapefile, 0)
        inLayer = inDataSource.GetLayer()
        extent = inLayer.GetExtent()

        # Create a Polygon from the extent tuple
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(extent[0], extent[2])
        ring.AddPoint(extent[1], extent[2])
        ring.AddPoint(extent[1], extent[3])
        ring.AddPoint(extent[0], extent[3])
        ring.AddPoint(extent[0], extent[2])
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        # Save extent to a new Shapefile
        outShapefile = os.path.join(temp_folder_path,"extent_{0}.shp".format(country))
        outDriver = ogr.GetDriverByName("ESRI Shapefile")

        # Remove output shapefile if it already exists
        if os.path.exists(outShapefile):
            outDriver.DeleteDataSource(outShapefile)

        # Create the output shapefile
        outDataSource = outDriver.CreateDataSource(outShapefile)
        outLayer = outDataSource.CreateLayer("extent_{0}".format(country), geom_type=ogr.wkbPolygon)

        # Add an ID field
        idField = ogr.FieldDefn("id", ogr.OFTInteger)
        outLayer.CreateField(idField)

        # Create the feature and set values
        featureDefn = outLayer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(poly)
        feature.SetField("id", 1)
        outLayer.CreateFeature(feature)
        feature = None

        # Save and close DataSource
        inDataSource = None
        outDataSource = None

        # create projection file for extent
        driver = ogr.GetDriverByName('ESRI Shapefile')
        dataset = driver.Open(output_country_shp)
        layer = dataset.GetLayer()
        spatialRef = layer.GetSpatialRef()
        in_epsg = int(spatialRef.GetAttrValue('Authority', 1))
        spatialRef.MorphToESRI()
        file = open(os.path.join(temp_folder_path,'extent_{0}.prj'.format(country)), 'w')
        file.write(spatialRef.ExportToWkt())
        file.close()


        # Recalculating coordinate extent of bbox to match ghs pixels and clipping ghs raster layers -----------------------
        print("Extracting {0} from GHS raster layer".format(country))
        for subdir, dirs, files in os.walk(ghs_folder_path):
            for file in files:
                if file.endswith(".tif"):
                    name = file.split(".tif")[0]

                    ghs_file_path = os.path.join(subdir, file)
                    out_file_path = os.path.join(merge_folder_path, "{0}_{1}.tif".format(name, country))
                    country_mask = os.path.join(temp_folder_path, "GADM_{0}.shp".format(country))

                    # open raster and get its georeferencing information
                    dsr = gdal.Open(ghs_file_path, gdal.GA_ReadOnly)
                    gt = dsr.GetGeoTransform()
                    srr = osr.SpatialReference()
                    srr.ImportFromWkt(dsr.GetProjection())

                    # open vector data and get its spatial ref
                    dsv = ogr.Open(country_mask)
                    lyr = dsv.GetLayer(0)
                    srv = lyr.GetSpatialRef()

                    # make object that can transorm coordinates
                    ctrans = osr.CoordinateTransformation(srv, srr)

                    lyr.ResetReading()
                    ft = lyr.GetNextFeature()
                    while ft:
                        # read the geometry and transform it into the raster's SRS
                        geom = ft.GetGeometryRef()
                        geom.Transform(ctrans)
                        # get bounding box for the transformed feature
                        minx, maxx, miny, maxy = geom.GetEnvelope()

                        # compute the pixel-aligned bounding box (larger than the feature's bbox)
                        left = minx - (minx - gt[0]) % gt[1]
                        right = maxx + (gt[1] - ((maxx - gt[0]) % gt[1]))
                        bottom = miny + (gt[5] - ((miny - gt[3]) % gt[5]))
                        top = maxy - (maxy - gt[3]) % gt[5]

                        cmd_clip = 'gdalwarp -te {0} {1} {2} {3} -tr {4} {5} -cutline {6} -srcnodata -3.4028234663852886e+38 \
                                    -dstnodata 0 {7} {8}'.format(
                        str(left), str(bottom), str(right), str(top), str(abs(gt[1])), str(abs(gt[5])),
                        country_mask, ghs_file_path, out_file_path)
                        subprocess.call(cmd_clip, shell=True)

                        ft = lyr.GetNextFeature()
                    ds = None


        # ----- Clipping slope, altering resolution to match ghs pop and recalculating slope values ------------------------
        print("------------------------------ PROCESSING SLOPE ------------------------------")
        print("Extracting slope for {0}".format(country))
        # Getting extent of ghs pop raster
        data = gdal.Open(os.path.join(merge_folder_path, "GHS_POP_1975_{0}.tif".format(country)))
        wkt = data.GetProjection()
        geoTransform = data.GetGeoTransform()
        minx = geoTransform[0]
        maxy = geoTransform[3]
        maxx = minx + geoTransform[1] * data.RasterXSize
        miny = maxy + geoTransform[5] * data.RasterYSize
        data = None

        print("Altering slope raster resolution to 250 meter")
        # Clipping slope and altering resolution
        cutlinefile = os.path.join(temp_folder_path,"GADM_{0}.shp".format(country))
        srcfile = os.path.join(ancillary_data_folder_path,"slope","slope_europe.tif")
        dstfile = os.path.join(temp_folder_path,"slope_250_{0}.tif".format(country))
        cmds = 'gdalwarp -s_srs EPSG:54009 -tr 250 250 -te {0} {1} {2} {3} -cutline {4} -srcnodata 255 -dstnodata 0 {5} {6}'\
            .format(minx, miny, maxx, maxy, cutlinefile, srcfile, dstfile)
        subprocess.call(cmds, shell=True)

        print("Recalculating slope raster values")
        # Recalculate slope raster values of 0 - 250 to real slope value 0 to 90 degrees
        outfile = os.path.join(merge_folder_path,"slope_{0}_finished_vers.tif".format(country))
        cmds = 'python {0}\gdal_calc.py -A {1} --outfile={2} --calc="numpy.arcsin((250-(A))/250)*180/numpy.pi" --NoDataValue=0'\
            .format(python_scripts_folder_path, dstfile, outfile)
        subprocess.call(cmds, shell=False)

        # Clipping lakes layer to country ----------------------------------------------------------------------------------
        print("------------------------------ Creating water layer for {0} ------------------------------".format(country))
        clip_poly = os.path.join(temp_folder_path,"extent_{0}.shp".format(country))
        in_shp = os.path.join(ancillary_data_folder_path,"eu_lakes.shp")
        out_shp = os.path.join(temp_folder_path,"eu_lakes_{0}.shp".format(country))
        cmd_shp_clip = "ogr2ogr -clipsrc {0} {1} {2} -nlt geometry".format(clip_poly, out_shp, in_shp)
        subprocess.call(cmd_shp_clip, shell=True)

        # Creating polygon grid that matches the population grid -----------------------------------------------------------
        print("------------------------------ Creating vector grid for {0} ------------------------------".format(country))
        outpath = os.path.join(temp_folder_path,"{0}_2015vector.shp".format(country))
        rasttovecgrid(outpath, minx, maxx, miny, maxy, 250, 250)

        # Creating polygon grid with larger grid size, to split the smaller grid and iterate in postgis --------------------
        print("------------------------------ Creating larger iteration vector grid for {0} ------------------------------"
              .format(country))
        outpath = os.path.join(temp_folder_path,"{0}_iteration_grid.shp".format(country))
        rasttovecgrid(outpath, minx, maxx, miny, maxy, 50000, 50000)

        # Extracting train stations for the chosen country
        print("------------------------------ Creating train stations for {0} ------------------------------"
              .format(country))
        infile = os.path.join(ancillary_data_folder_path,"european_train_stations\european_train_stations.shp")
        outfile = os.path.join(temp_folder_path,"european_train_stations.shp")
        country_code_dict = {'Denmark': 'DK', 'France': 'FR', 'Deutchland': 'DE'}
        cmds = "ogr2ogr -where country='{0}' {1} {2}".format(country_code_dict[country], outfile, infile)
        subprocess.call(cmds, shell=True)

        # Extracting municipalities from gadm for the chosen country
        print("------------------------------ Creating municipality layer for {0} ------------------------------"
              .format(country))
        infile = os.path.join(gadm_folder_path,"gadm28_adm2.shp")
        outfile = os.path.join(temp_folder_path,"{0}_municipal.shp".format(country))
        cmds = "ogr2ogr -where NAME_0='{0}' {1} {2}".format(country, outfile, infile)
        subprocess.call(cmds, shell=True)

        # Adding postgis and srs 54009 to postgres if it doesn't exist -----------------------------------------------------
        # connect to postgres
        conn = psycopg2.connect(database=pgdatabase, user=pguser, host=pghost, password=pgpassword)
        cur = conn.cursor()

        # check for and add postgis extension if not existing
        cur.execute("SELECT * FROM pg_available_extensions \
                    WHERE name LIKE 'postgis';")
        check_postgis = cur.rowcount
        if check_postgis == 0:
            print("Adding extension postgis")
            cur.execute("CREATE EXTENSION postgis;")
            conn.commit()

        # Check for and add srid 54009 if not existing
        cur.execute("SELECT * From spatial_ref_sys WHERE srid = 54009;")
        check_srid = cur.rowcount
        if check_srid == 0:
            print("Adding SRID 54009 to postgres")
            projs = '"World_Mollweide"'
            geogcs = '"GCS_WGS_1984"'
            datum = '"WGS_1984"'
            spheroid = '"WGS_1984"'
            primem = '"Greenwich"'
            unit_degree = '"Degree"'
            projection = '"Mollweide"'
            param_easting = '"False_Easting"'
            param_northing = '"False_Northing"'
            param_central = '"Central_Meridian"'
            unit_meter = '"Meter"'
            authority = '"ESPG","54009"'
            cur.execute("INSERT into spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext) values \
            ( 54009, 'ESRI', 54009, '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs ', \
            'PROJCS[{0},GEOGCS[{1},DATUM[{2},SPHEROID[{3},6378137,298.257223563]],\
            PRIMEM[{4},0],UNIT[{5},0.017453292519943295]],PROJECTION[{6}],PARAMETER[{7},0],\
            PARAMETER[{8},0],PARAMETER[{9},0],UNIT[{10},1],AUTHORITY[{11}]]');"
                        .format(projs, geogcs, datum, spheroid, primem, unit_degree, projection,
                                param_easting, param_northing, param_central, unit_meter, authority))
            conn.commit()
        # closing connection
        cur.close()
        conn.close()

    # Importing data to postgres--------------------------------------------------------------------------------------
    if init_import_to_postgres == "yes":
        print("------------------------------ IMPORTING DATA TO POSTGRES ------------------------------")
        import_to_postgres(country, pgpath, pghost, pgport, pguser, pgpassword, pgdatabase, temp_folder_path, ancillary_data_folder_path)

    # Running postgres queries -----------------------------------------------------------------------------------------
    if init_run_queries == "yes":
        print("------------------------------ RUNNING POSTGRES QUERIES ------------------------------")
        run_queries(country, pgdatabase, pguser, pghost, pgpassword)

    # Export layers from postgres to shp -------------------------------------------------------------------------------
    if init_export_data == "yes":
        print("------------------------------ EXPORTING DATA FROM POSTGRES ------------------------------")
        psqltoshp(country, pghost, pguser, pgpassword, pgdatabase, temp_folder_path)

    # Rasterize layers from postgres -----------------------------------------------------------------------------------
    if init_rasterize_data == "yes":
        print("------------------------------------ RASTERIZING DATA ------------------------------------")
        shptoraster(country, gdal_rasterize_path, 250, 250, temp_folder_path, merge_folder_path)

    # Merging all ghs files into one multiband raster ------------------------------------------------------------------
    if init_merge_data == "yes":
        print("------------------------------ CREATING MERGED TIFF FILES ------------------------------")
        # Merging files for 1975
        print("Merging files for 1975")
        outfile =          os.path.join(country_path , "{0}.tif".format(1975))
        original_tif_pop = os.path.join(merge_folder_path , "GHS_POP_1975_{0}.tif".format(country))
        water =            os.path.join(merge_folder_path , "{0}_water_cover.tif".format(country))
        road_dist =        os.path.join(merge_folder_path , "{0}_roads.tif".format(country))
        slope =            os.path.join(merge_folder_path , "slope_{0}_finished_vers.tif".format(country))
        corine =           os.path.join(merge_folder_path , "{0}_corine1990.tif".format(country))
        train =            os.path.join(merge_folder_path , "{0}_train_stations.tif".format(country))
        municipal =        os.path.join(merge_folder_path , "{0}_municipality.tif".format(country))
        cmd_tif_merge = "python {0}\gdal_merge.py -o {1} -separate {2} {3} {4} {5} {6} {7} {8}"\
        .format(python_scripts_folder_path, outfile, original_tif_pop,
                water, road_dist, slope, corine, train, municipal)
        subprocess.call(cmd_tif_merge, shell=False)

        # Merging files for 1990
        print("Merging files for 1990")
        outfile =          os.path.join(country_path ,      "{0}.tif".format(1990))
        original_tif_pop = os.path.join(merge_folder_path , "GHS_POP_1990_{0}.tif".format(country))
        water =            os.path.join(merge_folder_path , "{0}_water_cover.tif".format(country))
        road_dist =        os.path.join(merge_folder_path , "{0}_roads.tif".format(country))
        slope =            os.path.join(merge_folder_path , "slope_{0}_finished_vers.tif".format(country))
        corine =           os.path.join(merge_folder_path , "{0}_corine1990.tif".format(country))
        train =            os.path.join(merge_folder_path , "{0}_train_stations.tif".format(country))
        municipal =        os.path.join(merge_folder_path , "{0}_municipality.tif".format(country))
        cmd_tif_merge = "python {0}\gdal_merge.py -o {1} -separate {2} {3} {4} {5} {6} {7} {8}" \
            .format(python_scripts_folder_path, outfile, original_tif_pop,
                    water, road_dist, slope, corine, train, municipal)
        subprocess.call(cmd_tif_merge, shell=False)

        # Merging files for 2000
        print("Merging files for 2000")
        outfile =          os.path.join(country_path ,      "{0}.tif".format(2000))
        original_tif_pop = os.path.join(merge_folder_path , "GHS_POP_2000_{0}.tif".format(country))
        water =            os.path.join(merge_folder_path , "{0}_water_cover.tif".format(country))
        road_dist =        os.path.join(merge_folder_path , "{0}_roads.tif".format(country))
        slope =            os.path.join(merge_folder_path , "slope_{0}_finished_vers.tif".format(country))
        corine =           os.path.join(merge_folder_path , "{0}_corine2012.tif".format(country))
        train =            os.path.join(merge_folder_path , "{0}_train_stations.tif".format(country))
        municipal =        os.path.join(merge_folder_path , "{0}_municipality.tif".format(country))
        cmd_tif_merge = "python {0}\gdal_merge.py -o {1} -separate {2} {3} {4} {5} {6} {7} {8}" \
            .format(python_scripts_folder_path, outfile, original_tif_pop,
                    water, road_dist, slope, corine, train, municipal)
        subprocess.call(cmd_tif_merge, shell=False)

        # Merging files for 2000
        print("Merging files for 2015")
        outfile =          os.path.join(country_path ,      "{0}.tif".format(2015))
        original_tif_pop = os.path.join(merge_folder_path , "GHS_POP_2015_{0}.tif".format(country))
        water =            os.path.join(merge_folder_path , "{0}_water_cover.tif".format(country))
        road_dist =        os.path.join(merge_folder_path , "{0}_roads.tif".format(country))
        slope =            os.path.join(merge_folder_path , "slope_{0}_finished_vers.tif".format(country))
        corine =           os.path.join(merge_folder_path , "{0}_corine2012.tif".format(country))
        train =            os.path.join(merge_folder_path , "{0}_train_stations.tif".format(country))
        municipal =        os.path.join(merge_folder_path , "{0}_municipality.tif".format(country))
        cmd_tif_merge = "python {0}\gdal_merge.py -o {1} -separate {2} {3} {4} {5} {6} {7} {8}" \
            .format(python_scripts_folder_path, outfile, original_tif_pop,
                    water, road_dist, slope, corine, train, municipal)
        subprocess.call(cmd_tif_merge, shell=False)

    # stop total algorithm time timer ----------------------------------------------------------------------------------
    stop_total_algorithm_timer = time.time()
    # calculate total runtime
    total_time_elapsed = (stop_total_algorithm_timer - start_total_algorithm_timer)/60
    print("Total preparation time for {0} is {1} minutes".format(country, total_time_elapsed))
