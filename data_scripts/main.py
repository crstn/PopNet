# Main Script for data preparation -------------------------------------------------------------------------------------
# imports
import os
from process import process_data

# ATTENTION ------------------------------------------------------------------------------------------------------------
# Before running this script, a database should be created in postgres and the database information entered below, if
# it's not the same. Furthermore, the Project_data folder, scound be placed in the same folder as the scripts
# (main, process, import_to_postgres, postgres_to_shp, postgres_queries and rast_to_vec_grid)

# Folder strudture:
# scripts
# Project_data

# Specify country to extract data from ---------------------------------------------------------------------------------
country = 'Denmark'

# choose processes to run ----------------------------------------------------------------------------------------------
# Initial preparation of Population raster and slope ("yes" / "no")
init_prep = "yes"
#Import data to postgres? ("yes" / "no")
init_import_to_postgres = "yes"
# Run postgres queries? ("yes" / "no")
init_run_queries = "yes"
# calculate multiple train buffers? (dict{'column_name':biffersize in meters} or one ("yes", buffersize in meters)?
#multiple_train = "yes"
#multiple_train_dict = {'station2':2000, 'station5':5000, 'station10':10000, 'station20':20000}
#one_train_buffer = "yes", 10000

# export data from postgres? ("yes" / "no")
init_export_data = "yes"
# rasterize data from postgres? ("yes" / "no")
init_rasterize_data = "yes"
# Merge data from postgres? ("yes" / "no")
init_merge_data = "yes"

# Specify database information -----------------------------------------------------------------------------------------
# path to postgresql bin folder
pgpath = '/usr/local/bin/psql'
pghost = 'localhost'
pgport = '5432'
pguser = 'carsten'
pgpassword = ''
pgdatabase = 'popnet'

# DIFFERENT PATHS ------------------------------------------------------------------------------------------------------
# Get path to main script
python_script_dir =          os.path.dirname(os.path.abspath(__file__))

# Paths for the data / folders in the Project_data folder --------------------------------------------------------------
#path to ancillary data folder
ancillary_data_folder_path = os.path.join(python_script_dir , "data", "ancillary")
#path to GADM folder
gadm_folder_path =           os.path.join(python_script_dir , "data", "GADM")
#path to GHS folder
ghs_folder_path =            os.path.join(python_script_dir , "data", "GHS")

# Paths to storage during the data preparation (AUTOMATICALLY CREATED) -------------------------------------------------
#path to temp folder - will contain temporary files
temp_folder_path =           os.path.join(python_script_dir , "temp")
#Files to be merged folder
merge_folder_path =          os.path.join(python_script_dir , "Tif_to_merge")
#path to data folder to store the final tif files
finished_data_path =         os.path.join(python_script_dir , "Finished_data")



# Process all data -----------------------------------------------------------------------------------------------------
process_data(country, pgpath, pghost, pgport, pguser, pgpassword, pgdatabase, ancillary_data_folder_path,
             gadm_folder_path, ghs_folder_path, temp_folder_path, merge_folder_path, finished_data_path,
             init_prep, init_import_to_postgres, init_run_queries,
             init_export_data, init_rasterize_data, init_merge_data)
