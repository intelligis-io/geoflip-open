import uuid
from utils.logger import get_logger

from celery import shared_task
from flask import request, make_response, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from resources.v1.transform.format.output_manager import generate_output_file_stream
from resources.v1.transform.schemas import GeoJSONSchema, GeoJSONMergeSchema, GeoJSONAppendSchema

from .service import handle_geojson_transform, handle_geojson_merge, handle_geojson_append
logger = get_logger(__name__)

@shared_task(bind=True, ignore_result=False)
def create_geojson_transform_task(self, request_size, geojson_data, request_id, user_id, apikey_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip GEOJSON task has started'})
    return handle_geojson_transform(request_size, geojson_data, request_id, user_id, apikey_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_geojson_merge_task(self, request_size, geojson_data, request_id, user_id, apikey_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip GEOJSON merge task has started'})
    return handle_geojson_merge(request_size, geojson_data, request_id, user_id, apikey_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_geojson_append_task(self, request_size, geojson_data, request_id, user_id, apikey_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip GEOJSON append task has started'})
    return handle_geojson_append(request_size, geojson_data, request_id, user_id, apikey_id, celery_task=self)

GeojsonBlueprint = Blueprint("GeoJSON", __name__, description="GeoJSON transformation endpoints")

@GeojsonBlueprint.route("/v1/transform/geojson", methods=['POST'])
class Geojson(MethodView):
    @GeojsonBlueprint.arguments(GeoJSONSchema, location="json", description="Payload containing GeoJSON data to transform, and requested transform inputs")
    def post(self, geojson_data):
        request_id = str(uuid.uuid4())
        request_size = request.content_length
        
        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_geojson_transform_task.delay(request_size, geojson_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip GPKG task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_geojson_transform(request_size, geojson_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the Geojson: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=geojson_data["to_file"])

        return response

@GeojsonBlueprint.route("/v1/transform/geojson/merge")
class GeojsonMerge(MethodView):
    @GeojsonBlueprint.arguments(GeoJSONMergeSchema, location="json", description="Payload containing a list of GeoJSON objects to merge and transform, and the requested transform inputs")
    def post(self, geojson_data):
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_geojson_merge_task.delay(request_size, geojson_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip GPKG merge task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_geojson_merge(request_size, geojson_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the Geojson: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=geojson_data["to_file"])

        return response
    
@GeojsonBlueprint.route("/v1/transform/geojson/append")
class GeojsonAppend(MethodView):
    @GeojsonBlueprint.arguments(GeoJSONAppendSchema, location="json", description="Payload containing the target geojson and a list of GeoJSON objects to append to the target geojson and transform, and the requested transform inputs")
    def post(self, geojson_data):
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_geojson_append_task.delay(request_size, geojson_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip GPKG append task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_geojson_append(request_size, geojson_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the Geojson: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=geojson_data["to_file"])

        return response
