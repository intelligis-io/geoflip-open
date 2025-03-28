import geopandas as gpd
import os

import shutil
from pyproj.exceptions import CRSError

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import create_output_response
from resources.v1.transform.transformations import apply_transformations, UnsupportedTransformationError
from resources.v1.transform.transformations import merge_geodataframes, append_geodataframes

logger = get_logger(__name__)

def handle_gpkg_transform(request_size, file_path, uploads_dir, gpkg_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = gpkg_data["to_file"]

    # Load the geopackage
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading GPKG file'})
    try:
        gdf = gpd.read_file(file_path)
        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error handling the GPKG file: {e}")
        raise ValueError(f"Error handling GPKG file: {e} - api usage as not been recorded.")

    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in gpkg_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(gdf, gpkg_data)
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {gpkg_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(gpkg_data, request_id, gdf, to_file=to_file)
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
    output_format = gpkg_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Geopackage transformation successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "GPKG",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file":to_file
    }

    return result

def handle_gpkg_merge(request_size, file_paths, uploads_dir, gpkg_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = gpkg_data["to_file"]

    # Load the geopackage
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading GPKG files'})
    try:
        gdfs = []
        for file_path in file_paths:
            gdf = gpd.read_file(file_path)

            filename = os.path.basename(file_path)
            gdf["source"] = filename
            gdfs.append(gdf) 

        merged_gdf = merge_geodataframes(gdfs)

        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error handling the GPKG files: {e}")
        raise ValueError(f"Error handling GPKG files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in gpkg_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(merged_gdf, gpkg_data)
        transformations_applied.insert(0, f"merge {len(gdfs)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {gpkg_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(gpkg_data, request_id, gdf, to_file=to_file)
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
    output_format = gpkg_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Geopackage merge successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "GPKG",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file":to_file
    }

    return result

def handle_gpkg_append(request_size, target_filepath, append_filepaths, uploads_dir, gpkg_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = gpkg_data["to_file"]

    # load the target and append geodataframes
    gdfs_to_append = []
    try:
        target_gdf = gpd.read_file(target_filepath)

        for filepath in append_filepaths:

            gdf = gpd.read_file(filepath)
            gdfs_to_append.append(gdf) 

        appended_gdf = append_geodataframes(target_gdf, gdfs_to_append)

        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error handling the GPKG files: {e}")
        raise ValueError(f"Error handling GPKG files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    try:
        gdf, transformations_applied = apply_transformations(appended_gdf, gpkg_data)
        transformations_applied.insert(0, f"append {len(gdfs_to_append)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")
        
    # Create output response
    try:
        response_size, output_file_response = create_output_response(gpkg_data, request_id, gdf, to_file=to_file)
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
    output_format = gpkg_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Geopackage append successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "GPKG",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file":to_file
    }

    return result