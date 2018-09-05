import os
import subprocess

def psqltoshp(country, pgpath, pghost, pgport, pguser, pgpassword, pgdatabase, save_data_path):

    # exporting water cover from postgres
    print("Exporting water cover from postgres")
    path = os.path.join(save_data_path , "{0}_water_cover.shp".format(country))
    cmd = 'pgsql2shp -f {0} -h localhost -u {2} {3}"SELECT id, water_cover, geom FROM {1}_cover_analysis"'.format(path, country, pguser, pgdatabase)
    subprocess.call(cmd, shell=True)

    # # exporting roads
    print("Exporting roads from postgres")
    path = os.path.join(save_data_path , "{0}_roads.shp".format(country))
    cmd = 'pgsql2shp -f {0} -h localhost -u {2} {3} "SELECT id, rdist, geom FROM {1}_cover_analysis"'.format(path, country, pguser, pgdatabase)
    subprocess.call(cmd, shell=True)

    # exporting corine 1990
    print("Exporting corine 1990 from postgres")
    path = os.path.join(save_data_path , "{0}_corine1990.shp".format(country))
    cmd = 'pgsql2shp -f {0} -h localhost -u {2} {3} "SELECT id, corine_cover90, geom FROM {1}_cover_analysis"'.format(path, country, pguser, pgdatabase)
    subprocess.call(cmd, shell=True)

    # exporting corine 2012
    print("Exporting corine 2012 from postgres")
    path = os.path.join(save_data_path , "{0}_corine2012.shp".format(country))
    cmd = 'pgsql2shp -f {0} -h localhost -u {2} {3} "SELECT id, corine_cover, geom FROM {1}_cover_analysis"'.format(path, country, pguser, pgdatabase)
    subprocess.call(cmd, shell=True)



def shptoraster(country, xmin, xmax, ymin, ymax, xres, yres, save_data_path):
    # Rasterizing water_cover layer
    print("Rasterizing water_cover layer")
    src_file = os.path.join(save_data_path , "{0}_water_cover.shp".format(country))
    dst_file = os.path.join(save_data_path , "{0}_water_cover.tif".format(country))
    cmd = 'gdal_rasterize -a WATER_COVE -te {0} {1} {2} {3} -tr {4} {5} {6} {7}'.format(xmin, ymin, xmax, ymax, xres, yres, src_file, dst_file)
    subprocess.call(cmd, shell=True)

    # Rasterizing roads layer
    print("Rasterizing roads layer")
    src_file = os.path.join(save_data_path , "{0}_roads.shp".format(country))
    dst_file = os.path.join(save_data_path , "{0}_roads.tif".format(country))
    cmd = 'gdal_rasterize -a RDIST -te {0} {1} {2} {3} -tr {4} {5} {6} {7}'.format(xmin, ymin, xmax, ymax, xres, yres, src_file, dst_file)
    subprocess.call(cmd, shell=True)

    # Rasterizing corine 1990 layer
    print("Rasterizing corine 1990 layer")
    src_file = os.path.join(save_data_path , "{0}_corine1990.shp".format(country))
    dst_file = os.path.join(save_data_path , "{0}_corine1990.tif".format(country))
    cmd = 'gdal_rasterize -a CORINE_COV -te {0} {1} {2} {3} -tr {4} {5} {6} {7}'.format(xmin, ymin, xmax, ymax, xres, yres, src_file, dst_file)
    subprocess.call(cmd, shell=True)

    # Rasterizing corine 2012 layer
    print("Rasterizing corine 2012 layer")
    src_file = os.path.join(save_data_path , "{0}_corine2012.shp".format(country))
    dst_file = os.path.join(save_data_path , "{0}_corine2012.tif".format(country))
    cmd = 'gdal_rasterize -a CORINE_COV -te {0} {1} {2} {3} -tr {4} {5} {6} {7}'.format(xmin, ymin, xmax, ymax, xres, yres, src_file, dst_file)
    subprocess.call(cmd, shell=True)
