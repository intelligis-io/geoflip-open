import geopandas as gpd
import os

import shutil
from pyproj.exceptions import CRSError

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import create_output_response
from resources.v1.transform.transformations import apply_transformations, UnsupportedTransformationError
from resources.v1.transform.transformations import merge_geodataframes, append_geodataframes

logger = get_logger(__name__)

def handle_dxf_transform(request_size, file_path, uploads_dir, dxf_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = dxf_data["to_file"]

    # Load the dxf
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading DXF file'})
    try:
        gdf = gpd.read_file(file_path)
        gdf.crs = dxf_data['input_crs']
        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error handling the DXF file: {e}")
        raise ValueError(f"Error handling DXF file: {e} - api usage as not been recorded.")

    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in dxf_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(gdf, dxf_data)
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {dxf_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(dxf_data, request_id, gdf, to_file=to_file)
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
    output_format = dxf_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "DXF transformation successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "DXF",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result

def handle_dxf_merge(request_size, file_paths, input_crs_mapping, uploads_dir, dxf_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = dxf_data["to_file"]

    # load and merge the DXF files
    try:
        gdfs = []
        for file_path, crs in zip(file_paths, input_crs_mapping):
            gdf = gpd.read_file(file_path)
            gdf.crs = crs
            filename = os.path.basename(file_path)
            gdf["source"] = filename
            gdfs.append(gdf)

        merged_gdf = merge_geodataframes(gdfs)
        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except ValueError as e:
        logger.error(f"Invalid input files: {e}")
        raise ValueError(f"Invalid input: {e} - api usage has not been recorded.")
    except Exception as e:
        logger.error(f"Error handling the DXF files: {e}")
        raise ValueError(f"Error handling DXF files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    try:
        gdf, transformations_applied = apply_transformations(merged_gdf, dxf_data)
        transformations_applied.insert(0, f"merge {len(gdfs)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage has not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    try:
        response_size, output_file_response = create_output_response(dxf_data, request_id, gdf, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage has not been recorded.")
        raise ValueError(f"{e} - api usage has not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage has not been recorded.")
        raise ValueError(f"{e} - api usage has not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage has not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage has not been recorded.")  

    # Reporting API usage for successful processing
    output_format = dxf_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "DXF merge successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "DXF",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result

def handle_dxf_append(request_size, target_filepath, append_filepaths, append_crs_mapping, uploads_dir, dxf_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = dxf_data["to_file"]

    # Load and append the DXF files
    try:
        gdfs_to_append = []
        target_gdf = gpd.read_file(target_filepath)
        target_gdf.crs = dxf_data['input_crs']

        for file_path, crs in zip(append_filepaths, append_crs_mapping):
            gdf = gpd.read_file(file_path)
            gdf.crs = crs
            gdfs_to_append.append(gdf)

        # Append the DXF files to the target DXF file, 1 unit consumed for performing the merge operation
        appended_gdf = append_geodataframes(target_gdf, gdfs_to_append)

        # Cleanup
        shutil.rmtree(uploads_dir, ignore_errors=True)
    except ValueError as e:
        logger.error(f"Invalid input files: {e}")
        raise ValueError(f"Invalid input: {e} - api usage has not been recorded.")
    except Exception as e:
        logger.error(f"Error handling the DXF files: {e}")
        raise ValueError(f"Error handling DXF files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    try:
        gdf, transformations_applied = apply_transformations(appended_gdf, dxf_data)
        transformations_applied.insert(0, f"append {len(gdfs_to_append)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage has not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")
        
    # Create output response
    try:
        response_size, output_file_response = create_output_response(dxf_data, request_id, gdf, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage has not been recorded.")
        raise ValueError(f"{e} - api usage has not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage has not been recorded.")
        raise ValueError(f"{e} - api usage has not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage has not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage has not been recorded.")  

    # Reporting API usage for successful processing
    output_format = dxf_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "DXF append successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "DXF",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result