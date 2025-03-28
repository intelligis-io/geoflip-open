import geopandas as gpd

from pyproj.exceptions import CRSError

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import create_output_response
from resources.v1.transform.transformations import apply_transformations, UnsupportedTransformationError
from resources.v1.transform.transformations import merge_geodataframes, append_geodataframes


logger = get_logger(__name__)

def handle_geojson_transform(request_size, geojson_data, request_id, celery_task=None):
    transformations_applied = []
    to_file=geojson_data["to_file"]

    # Load the geojson
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading GEOJSON data'})
    try:
        gdf = gpd.GeoDataFrame.from_features(geojson_data['input_geojson'], crs="EPSG:4326")
    except Exception as e:
        logger.error(f"Error converting input GeoJSON to GeoDataFrame: {e}")
        raise ValueError("Invalid GeoJSON data, please check the input data - api usage as not been recorded.")
    
    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in geojson_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(gdf, geojson_data)
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {geojson_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(geojson_data, request_id, gdf, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage as not been recorded.")        
    
    # inform stripe of the api call
    output_format = geojson_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Geojson transformation successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "GEOJSON",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file":to_file
    }

    return result

def handle_geojson_merge(request_size, geojson_data, request_id, celery_task=None):
    transformations_applied = []
    to_file = geojson_data["to_file"]

    # Load the geojson
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading GEOJSON data'})
    try:
        input_geojsons = geojson_data.get('input_geojson_list')
        if not input_geojsons or not isinstance(input_geojsons, list):
            raise ValueError("Invalid input: 'input_geojson_list' must be a list of GeoJSON objects.")

        gdfs = []
        for idx, geojson in enumerate(input_geojsons):
            gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs="EPSG:4326")
            gdf["source"] = f"geojson [{idx}]"
            gdfs.append(gdf)

        gdf = merge_geodataframes(gdfs)
    except Exception as e:
        logger.error(f"Error handling the GeoJSON files: {e}")
        raise ValueError(f"Error handling GeoJSON files: {e} - api usage has not been recorded.")
    
    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in geojson_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(gdf, geojson_data)
        transformations_applied.insert(0, f"merge {len(gdfs)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {geojson_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(geojson_data, request_id, gdf, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage as not been recorded.")        
    
    # inform stripe of the api call
    output_format = geojson_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Geojson merge successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "GEOJSON",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result

def handle_geojson_append(request_size, geojson_data, request_id, celery_task=None):
    transformations_applied = []
    to_file=geojson_data["to_file"]

    # Load the geojson
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': 'Loading GEOJSON data'})

    append_geojsons = geojson_data.get('append_geojson_list')
    if not append_geojsons or not isinstance(append_geojsons, list):
        raise ValueError("Invalid input: 'append_geojson_list' must be a list of GeoJSON objects.")

    gdfs_to_append = []
    try:
        target_gdf = gpd.GeoDataFrame.from_features(geojson_data['target_geojson'], crs="EPSG:4326")

        for geojson in append_geojsons:
            append_gdf = gpd.GeoDataFrame.from_features(geojson['features'], crs="EPSG:4326")
            gdfs_to_append.append(append_gdf)

        gdf = append_geodataframes(target_gdf, gdfs_to_append)
    except Exception as e:
        logger.error(f"Error handling the GeoJSON files: {e}")
        raise ValueError(f"Error handling GeoJSON files: {e} - api usage has not been recorded.")

    # Apply transformations if any
    if celery_task is not None:
        transformations_string = "/".join(item["type"] for item in geojson_data["transformations"])
        celery_task.update_state(state='PROCESSING', meta={'message': f'Applying transformations: {transformations_string}'})
    try:
        gdf, transformations_applied = apply_transformations(gdf, geojson_data)
        transformations_applied.insert(0, f"append {len(gdfs_to_append)} files")
    except UnsupportedTransformationError as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Unsupported transformation type - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"Error applying transformations: {e}")
        raise ValueError("Error applying transformations - api usage as not been recorded.")

    # Create output response
    if celery_task is not None:
        celery_task.update_state(state='PROCESSING', meta={'message': f'Creating output {geojson_data['output_format']}'})
    try:
        response_size, output_file_response = create_output_response(geojson_data, request_id, gdf, to_file=to_file)
    except ValueError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except CRSError as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise ValueError(f"{e} - api usage as not been recorded.")
    except Exception as e:
        logger.error(f"{e} - api usage as not been recorded.")
        raise RuntimeError("There was an error handling this request - api usage as not been recorded.")        
    
    # inform stripe of the api call
    output_format = geojson_data['output_format'].upper()
    transformations = "/".join(transformations_applied)

    # this needs to be a json response for async
    result = {
        "message": "Geojson append successful",
        "response_size": response_size,
        "request_size": request_size,
        "transformations": transformations,
        "input_format": "GEOJSON",
        "output_format": output_format,
        "output_file_response": output_file_response,
        "to_file": to_file
    }

    return result

