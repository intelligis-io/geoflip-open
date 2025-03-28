
import shutil 
import os

from flask import send_file, after_this_request, make_response
from pyproj.exceptions import CRSError

from .geodataframe import to_shp, to_gpkg, to_dxf, to_geojson, to_csv, to_esrijson, create_esrijson_from_gdf

from utils.logger import get_logger

logger = get_logger(__name__)

def generate_output_file_stream(transform_result, to_file=False):
    output_file_response = transform_result["output_file_response"]

    if transform_result["output_format"] in ("GEOJSON", "ESRIJSON") and not to_file:
        # For GeoJSON, we keep the existing behavior
        response = make_response(output_file_response, 200)
    else:
        file_path = output_file_response
        output_dir = os.path.dirname(file_path)

        @after_this_request
        def cleanup(response):
            shutil.rmtree(output_dir, ignore_errors=True)
            return response

        response = send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='application/octet-stream'
        )

    # Add metadata headers
    response.headers['Metadata-Response-Size'] = str(transform_result["response_size"])
    response.headers['Metadata-Request-Size'] = str(transform_result["request_size"])
    response.headers['Metadata-Transformations'] = str(transform_result["transformations"])
    response.headers['Metadata-Input-Format'] = str(transform_result["input_format"])
    response.headers['Metadata-Output-Format'] = str(transform_result["output_format"])

    return response

def create_output_response(request_data, request_id, gdf, schema=None, to_file=False, request_size=0):
    output_dir = os.path.join(os.getenv("OUTPUT_PATH"), request_id)
    os.makedirs(output_dir, exist_ok=True)

    # convert the GeoDataFrame to desired output format
    match request_data['output_format']:
        case "shp":
            try:
                output_crs = request_data["output_crs"]
                zip_file_path = to_shp(gdf, schema, output_dir, output_crs)

                try:
                    response = zip_file_path
                    response_size = os.path.getsize(zip_file_path)

                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    raise Exception(f"Error preparing download: ({e})")
            except CRSError:
                logger.error(f"Invalid output crs: {output_crs}")
                raise CRSError(f"Invalid output crs: {output_crs}")
            except Exception as e:
                logger.error(f"Error converting to shapefile: {e}")
                raise Exception(f"Error converting to shapefile: ({e})")

        case "geojson":
            if to_file:
                try:
                    geojson_file_path = to_geojson(gdf, output_dir)
                    # Stream and send the GeoJSON file, with cleanup afterward
                    response = geojson_file_path
                    response_size = os.path.getsize(geojson_file_path)
                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    raise Exception(f"Error sending file: ({e})")
            else:
                # return the geojson data
                response = gdf.to_crs("EPSG:4326").to_json()
                response_size = len(str(response).encode('utf-8')) 

        case "gpkg":
            try:
                output_crs = request_data["output_crs"]
                gpkg_file_path = to_gpkg(gdf, output_dir, output_crs)

                try:
                    response = gpkg_file_path
                    response_size = os.path.getsize(gpkg_file_path)
                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    raise Exception(f"Error sending file: ({e})")
            except CRSError:
                logger.error(f"Invalid output crs: {output_crs}")
                raise CRSError(f"Invalid output crs: {output_crs}")
            except Exception as e:
                logger.error(f"Error converting to geopackage: {e}")
                raise Exception(f"Error converting to geopackage: ({e})")
            
        case "dxf":
            try:
                output_crs = request_data["output_crs"]
                dxf_file_path = to_dxf(gdf, output_dir, output_crs)

                try:
                    # Stream and send the GPKG file, with cleanup afterward
                    response = dxf_file_path
                    response_size = os.path.getsize(dxf_file_path)

                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    raise Exception(f"Error sending file: ({e})")
            except CRSError:
                logger.error(f"Invalid output crs: {output_crs}")
                raise CRSError(f"Invalid output crs: {output_crs}")
            except Exception as e:
                logger.error(f"Error converting to dxf: {e}")
                raise Exception(f"Error converting to dxf: ({e})")
            
        case 'csv':
            try:
                output_crs = request_data.get("output_crs", "EPSG:4326")
                csv_file_path = to_csv(gdf, output_dir, output_crs)

                try:
                    response_size = os.path.getsize(csv_file_path)
                    response = csv_file_path
                except Exception as e:
                    logger.error(f"Error sending file: {e}")
                    raise Exception(f"Error sending file: ({e})")

            except CRSError:
                logger.error(f"Invalid output CRS: {output_crs}")
                raise CRSError(f"Invalid output CRS: {output_crs}")
            except Exception as e:
                logger.error(f"Error converting to CSV: {e}")
                raise Exception(f"Error converting to CSV: ({e})")
            
        case "esrijson":
            try:
                output_crs = request_data.get("output_crs", "EPSG:4326")

                if to_file:
                    try:
                        # Stream and send the EsriJSON file, with cleanup afterward
                        esrijson_file_path = to_esrijson(gdf, output_dir, output_crs)
                        response = esrijson_file_path
                        response_size = os.path.getsize(esrijson_file_path)
                    except Exception as e:
                        logger.error(f"Error sending file: {e}")
                        raise Exception(f"Error sending file: ({e})")
                else:
                    # return the esrijson data
                    response = create_esrijson_from_gdf(gdf, output_crs)
                    response_size = len(str(response).encode('utf-8')) 
            except CRSError:
                logger.error(f"Invalid output CRS: {output_crs}")
                raise CRSError(f"Invalid output CRS: {output_crs}")
            except Exception as e:
                logger.error(f"Error converting to esrijson: {e}")
                raise Exception(f"Error converting to esrijson: ({e})")

        case "_":
            logger.error(f"Unsupported output format: {request_data['output_format']}")
            raise ValueError("Unsupported output format")
            
    return response_size, response