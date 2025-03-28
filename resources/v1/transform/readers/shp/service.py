import fiona
import geopandas as gpd
import os

import zipfile
import shutil
from pyproj.exceptions import CRSError

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import create_output_response
from resources.v1.transform.transformations import apply_transformations, UnsupportedTransformationError
from resources.v1.transform.transformations import merge_geodataframes, append_geodataframes

logger = get_logger(__name__)

def load_shapefile(directory_path):
    """
    Load a shapefile from a specified directory, verifying that all necessary components exist.

    Parameters:
    directory_path (str): The path to the directory containing the shapefile components.

    Returns:
    GeoDataFrame: The GeoDataFrame loaded from the shapefile.

    Raises:
    ValueError: If any required shapefile components are missing.
    """
    required_extensions = ['.shp', '.shx', '.dbf', '.prj']
    found_files = {ext: None for ext in required_extensions}
    
    # Check for the existence of each required file
    for file in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file)
        _, ext = os.path.splitext(file)
        if ext in required_extensions:
            found_files[ext] = file_path
    
    # Verify all required files were found
    missing_files = [ext for ext, path in found_files.items() if path is None]
    if missing_files:
        raise ValueError(f"Missing required files for the shapefile: {', '.join(missing_files)}")
    
    # Use fiona to open the shapefile and get both the GeoDataFrame and schema
    with fiona.open(found_files['.shp']) as src:
        input_gdf = gpd.GeoDataFrame.from_features(src, crs=src.crs)
        schema = src.schema

    return input_gdf, schema

def handle_shp_transform(request_size, file_path, extract_path, uploads_dir, shp_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = shp_data['to_file']

    # Load the shapefile
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading SHP file'})

    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        gdf, schema = load_shapefile(extract_path)

        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error handling the SHP file: {e}")
        raise ValueError(f"Error handling SHP file: {e} - api usage as not been recorded.")
    
    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in shp_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(gdf, shp_data)
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")
    
    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {shp_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(shp_data, request_id, gdf, schema, to_file=to_file, request_size=request_size)
    except ValueError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage as not been recorded.")  

    # Reporting API usage for successful processing
    output_format = shp_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Shapefile transformation successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "SHP",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result

def handle_shp_merge(request_size, file_paths, uploads_dir, shp_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = shp_data['to_file']

    # Load the shapefiles
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading SHP files'})
    try:
        gdfs = []
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            extract_path = os.path.join(uploads_dir, os.path.splitext(filename)[0])

            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            gdf, schema = load_shapefile(extract_path)
            gdf["source"] = filename
            gdfs.append(gdf)

        merged_gdf = merge_geodataframes(gdfs)

        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error loading the SHP files: {e}")
        raise ValueError(f"Error handling SHP files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in shp_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(merged_gdf, shp_data)
        transformations_applied.insert(0, f"merge {len(gdfs)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {shp_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(shp_data, request_id, gdf, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage as not been recorded.")  

    # Reporting API usage for successful processing
    output_format = shp_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Shapefile merge successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "SHP",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result


def handle_shp_append(request_size, target_file_path, append_filepaths, uploads_dir, shp_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = shp_data['to_file']

    # extract and prepare GDF from shp files
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading SHP files'})
    try:
        # extract and load target file to gdf
        target_filename = os.path.basename(target_file_path)
        target_extract_path = os.path.join(uploads_dir, os.path.splitext(target_filename)[0])

        with zipfile.ZipFile(target_file_path, 'r') as zip_ref:
            zip_ref.extractall(target_extract_path)
        target_gdf, target_schema = load_shapefile(target_extract_path)

        # extract and load the append files to gdf
        gdfs_to_append = []
        for append_filepath in append_filepaths:
            append_filename = os.path.basename(append_filepath)
            append_extract_path = os.path.join(uploads_dir, os.path.splitext(append_filename)[0])

            with zipfile.ZipFile(append_filepath, 'r') as zip_ref:
                zip_ref.extractall(append_extract_path)

            append_gdf, append_schema = load_shapefile(append_extract_path)
            gdfs_to_append.append(append_gdf)

        appended_gdf = append_geodataframes(target_gdf, gdfs_to_append)

        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error handling the SHP files: {e}")
        raise ValueError(f"Error handling SHP files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in shp_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(appended_gdf, shp_data)
        transformations_applied.insert(0, f"append {len(gdfs_to_append)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {shp_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(shp_data, request_id, gdf, target_schema, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage as not been recorded.")  

    # Reporting API usage for successful processing
    output_format = shp_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Shapefile append successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "SHP",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file":to_file
    }

    return result