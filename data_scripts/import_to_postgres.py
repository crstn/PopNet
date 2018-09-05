#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ogr
import subprocess
import psycopg2

def import_to_postgres(country, pgpath, pghost, pgport, pguser, pgpassword, pgdatabase,
                       temp_folder_path, ancillary_data_folder_path, overwrite=True):


    if overwrite:
        print("♻️ Deleting old database tables for fresh import.")

        cmd = 'dropdb {0}'.format(pgdatabase)
        os.system(cmd)

        cmd = 'createdb -O {0} {1}'.format(pguser, pgdatabase)
        os.system(cmd)

        cmd = 'psql -d {0} -U {1} -c "create extension postgis;"'.format(pgdatabase, pguser)
        os.system(cmd)


        # Adding EPSG:54009 to postgres if it doesn't exist -----------------------------------------------------
        # connect to postgres
        conn = psycopg2.connect(database=pgdatabase, user=pguser, host=pghost, password=pgpassword)
        cur = conn.cursor()

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
            cur.execute("""INSERT into spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext) values
            ( 54009, 'ESRI', 54009, '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs ',
            'PROJCS[{0},GEOGCS[{1},DATUM[{2},SPHEROID[{3},6378137,298.257223563]],
            PRIMEM[{4},0],UNIT[{5},0.017453292519943295]],PROJECTION[{6}],PARAMETER[{7},0],
            PARAMETER[{8},0],PARAMETER[{9},0],UNIT[{10},1],AUTHORITY[{11}]]');"""
                        .format(projs, geogcs, datum, spheroid, primem, unit_degree, projection,
                                param_easting, param_northing, param_central, unit_meter, authority))
            conn.commit()
        # closing connection
        cur.close()
        conn.close()



    # ----- Importing data to postgres ---------------------------------------------------------------------------------
    # Importing corine layers by quering data inside country extent
    # Tranforming gadm country layer to srs 3035
    inshp = os.path.join(temp_folder_path , "GADM_{0}.shp".format(country))
    outshp = os.path.join(temp_folder_path , "GADM_{0}_3035.shp".format(country))
    cmd = 'ogr2ogr -f "ESRI Shapefile" -t_srs EPSG:3035 {0} {1}'.format(outshp, inshp)

    subprocess.call(cmd, shell=True)

    # Get a Layer's Extent
    inShapefile = os.path.join(temp_folder_path , "GADM_{0}_3035.shp".format(country))
    inD = ogr.GetDriverByName("ESRI Shapefile")
    inData = inD.Open(inShapefile, 0)
    inLa = inData.GetLayer()
    extent = inLa.GetExtent()
    xmin = extent[0]
    ymin = extent[2]
    xmax = extent[1]
    ymax = extent[3]

    # Loading corine 2012 into postgres
    print("Importing corine 2012 to postgres")
    clc12path = os.path.join(ancillary_data_folder_path , "corine", "clc12_Version_18_5a_sqLite", "clc12_Version_18_5.sqlite")
    cmds = 'ogr2ogr -overwrite -lco GEOMETRY_NAME=geom -lco SCHEMA=public -f "PostgreSQL" \
    PG:"host={0} port={1} user={2} dbname={3} password={4}" \
    -t_srs "EPSG:3035" {5} -sql "SELECT * FROM clc12_Version_18_5 \
    WHERE code_12 = 124 OR code_12 = 121 OR code_12 = 311 OR code_12 = 312 OR code_12 = 313" \
    -spat {6} {7} {8} {9} -nln {10}_corine'.format(pghost, pgport, pguser, pgdatabase, pgpassword, clc12path, xmin, ymin, xmax, ymax, country)
    subprocess.call(cmds, shell=True)

    # Loading corine 1990 into postgres
    print("Importing corine 1990 to postgres")
    clc90path = os.path.join(ancillary_data_folder_path , "corine", "clc90_Version_18_5_sqlite", "clc90_Version_18_5.sqlite")
    cmds = 'ogr2ogr -overwrite -lco GEOMETRY_NAME=geom -lco SCHEMA=public -f "PostgreSQL" \
    PG:"host={0} port={1} user={2} dbname={3} password={4}" \
    -t_srs "EPSG:3035" {5} -sql "SELECT * FROM clc90_Version_18_5 \
    WHERE code_90 = 124 OR code_90 = 121 OR code_90 = 311 OR code_90 = 312 OR code_90 = 313" \
    -spat {6} {7} {8} {9} -nln {10}_corine90'.format(pghost, pgport, pguser, pgdatabase, pgpassword, clc90path, xmin, ymin, xmax, ymax, country)
    subprocess.call(cmds, shell=True)

    # Loading trainstations into postgres
    print("Importing train stations to postgres")
    trainpath = os.path.join(temp_folder_path , "european_train_stations.shp")
    cmds =  'ogr2ogr -overwrite -lco GEOMETRY_NAME=geom -lco SCHEMA=public -f "PostgreSQL" \
            PG:"host={0} port={1} user={2} dbname={3} password={4}" \
            {5} -sql "select * from european_train_stations" -nln {6}_train'.format(pghost, pgport, pguser, pgdatabase, pgpassword,trainpath, country)
    subprocess.call(cmds, shell=True)


    # Loading vector grid into postgresql
    print("Importing vectorgrid to postgres")
    gridpath = os.path.join(temp_folder_path , "{0}_2015vector.shp".format(country))
    cmds = 'ogr2ogr --config PG_USE_COPY YES -gt 65536 -f PGDump /vsistdout/ \
       {0} -lco GEOMETRY_NAME=geom -lco SCHEMA=public -lco \
       CREATE_SCHEMA=OFF -lco SPATIAL_INDEX=OFF | psql -d {1} -U {2} -q; \
       psql -d {1} -U {2} -c "SELECT UpdateGeometrySRID(\'{3}_2015vector\',\'geom\',54009);"'.format(gridpath, pgdatabase, pguser, country.lower())

    os.system(cmds)

    # Loading iteration grid into postgres
    print("Importing iteration grid to postgres")
    ite_path = os.path.join(temp_folder_path , "{0}_iteration_grid.shp".format(country))
    cmds = 'shp2pgsql -I -s 54009 {0} public.{1}_iteration_grid | psql -d {2} -U {3} -q'.format(ite_path, country, pgdatabase, pguser)

    os.system(cmds)

    # Loading gadm into postgres
    print("Importing GADM to postgres")
    gadmpath = os.path.join(temp_folder_path , "GADM_{0}.shp".format(country))
    cmds = 'shp2pgsql -I -s 4326:54009 {0} public.{1}_adm | psql -d {2} -U {3} -q'.format(gadmpath, country, pgdatabase, pguser)

    os.system(cmds)

    # Loading water into postgres
    print("Importing water to postgres")
    lakespath = os.path.join(temp_folder_path , "eu_lakes_{0}.shp".format(country))
    cmds = 'shp2pgsql -I -s 4326:54009 {0} public.{1}_lakes | psql -d {2} -U {3} -q'.format(lakespath, country, pgdatabase, pguser)

    os.system(cmds)

    # Loading groads into postgres
    print("Importing roads to postgres")
    roadpath = os.path.join(ancillary_data_folder_path , "groads_europe", "gROADS-v1-europe.shp")
    cmds = 'shp2pgsql -I -s 4326:54009 {0} public.{1}_groads | psql -d {2} -U {3} -q'.format(roadpath, country, pgdatabase, pguser)

    os.system(cmds)

    # Loading municipalities into postgres
    print("Importing municipalities to postgres")
    munipath = os.path.join(temp_folder_path , "{0}_municipal.shp".format(country))
    cmds = 'shp2pgsql -I -s 4326:54009 {0} public.{1}_municipal | psql -d {2} -U {3} -q'.format(munipath, country, pgdatabase, pguser)

    #subprocess.call(cmds, shell=True)
    os.system(cmds)

    # #Delete files in the temp folder
    # print("Deleting temp folder content")
    # os.chdir(temp_folder_path)
    # for root, dirs, files in os.walk(".", topdown=False):
    #     for file in files:
    #         print(os.path.join(root, file))
    #         os.remove(os.path.join(root, file))
