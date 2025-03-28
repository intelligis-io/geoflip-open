import os
import uuid

from flask import request, make_response, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.utils import secure_filename

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import generate_output_file_stream

from celery import shared_task
from resources.v1.transform.schemas import MultipartFormSHPConfigValidator, MultipartFormSHPFileValidator, MultipartFormSHPMergeFilesValidator
from .service import handle_shp_transform, handle_shp_merge, handle_shp_append
from utils.file_handling import wait_for_file

logger = get_logger(__name__)

@shared_task(bind=True, ignore_result=False)
def create_shp_transform_task(self, request_size, file_path, extract_path, uploads_dir, shp_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip SHP task has started'})
    return handle_shp_transform(request_size, file_path, extract_path, uploads_dir, shp_data, request_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_shp_merge_task(self, request_size, file_paths, uploads_dir, shp_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip SHP merge task has started'})
    return handle_shp_merge(request_size, file_paths, uploads_dir, shp_data, request_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_shp_append_task(self, request_size, target_filepath, append_filepaths, uploads_dir, shp_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip SHP append task has started'})
    return handle_shp_append(request_size, target_filepath, append_filepaths, uploads_dir, shp_data, request_id, celery_task=self)

ShapefileBlueprint = Blueprint("Shapefile", __name__, description="Shapefile transformation endpoints")
@ShapefileBlueprint.route("/v1/transform/shp", methods=['POST'])
class Shapefile(MethodView):
    @ShapefileBlueprint.arguments(MultipartFormSHPFileValidator, location="files", description="multipart/form-data 'file' containing a shapefile zip")
    @ShapefileBlueprint.arguments(MultipartFormSHPConfigValidator, location="form", description="multipart/form-data containing the transformation configuration")
    def post(self, files, form):
        shp_data = form['config']
        request_id = str(uuid.uuid4())
        request_size = request.content_length

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        #  make a folder to extract the zip file
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # Save and extract ZIP file
        file = files["file"]
        filename = secure_filename(file.filename)
        file_path = os.path.join(uploads_dir, filename)
        file.save(file_path)

        # Check if the file is accessible
        try:
            wait_for_file(file_path)
        except FileNotFoundError as e:
            logger.error(f"File save failed or file not accessible: {e}")
            abort(400, description="File save failed or not accessible.")

        extract_path = os.path.join(uploads_dir, os.path.splitext(filename)[0])

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_shp_transform_task.delay(request_size, file_path, extract_path, uploads_dir, shp_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip SHP task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_shp_transform(request_size, file_path, extract_path, uploads_dir, shp_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the SHP file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=shp_data["to_file"])

        return response
    
@ShapefileBlueprint.route("/v1/transform/shp/merge", methods=['POST'])
class ShapeMerge(MethodView):
    @ShapefileBlueprint.arguments(MultipartFormSHPMergeFilesValidator, location="files", description="multipart/form-data 'files' containing a series of files shapefile zip")
    @ShapefileBlueprint.arguments(MultipartFormSHPConfigValidator, location="form", description="multipart/form-data containing the transformation configuration to be applied after merging")
    def post(self, files, form):
        shp_data = form['config']
        request_id = str(uuid.uuid4())
        request_size = request.content_length

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        #  make a folder to extract the zip file
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # retrieve the files from the request and save them
        filepaths = []
        try:
            for file in files['files']:
                filename = secure_filename(file.filename)
                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)

                # Check if the file is accessible
                try:
                    wait_for_file(file_path)
                except FileNotFoundError as e:
                    logger.error(f"File save failed or file not accessible: {e}")
                    abort(400, description="File save failed or not accessible.")

                filepaths.append(file_path)
        except Exception as e:
            logger.error(f"Error saving the SHP files: {e}")
            abort(400, message=f"Error handling SHP files: {e} - api usage has not been recorded.")

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_shp_merge_task.delay(request_size, filepaths, uploads_dir, shp_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip SHP task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_shp_merge(request_size, filepaths, uploads_dir, shp_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the SHP file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=shp_data["to_file"])

        return response

@ShapefileBlueprint.route("/v1/transform/shp/append", methods=['POST'])
class ShapeAppend(MethodView):
    @ShapefileBlueprint.arguments(MultipartFormSHPFileValidator, location="files", description="multipart/form-data 'file' containing a shapefile zip")
    @ShapefileBlueprint.arguments(MultipartFormSHPMergeFilesValidator, location="files", description="multipart/form-data 'files' containing a series of files shapefile zip")
    @ShapefileBlueprint.arguments(MultipartFormSHPConfigValidator, location="form", description="multipart/form-data containing the transformation configuration to be applied after merging")
    def post(self, target, files, form):
        shp_data = form['config']
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        #  make a folder to extract the zip file
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # retrieve the files from the request and save them
        append_filepaths = []
        try:
            for file in files['files']:
                filename = secure_filename(file.filename)
                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)

                # Check if the file is accessible
                try:
                    wait_for_file(file_path)
                except FileNotFoundError as e:
                    logger.error(f"File save failed or file not accessible: {e}")
                    abort(400, description="File save failed or not accessible.")

                # Check if the file is accessible
                try:
                    wait_for_file(file_path)
                except FileNotFoundError as e:
                    logger.error(f"File save failed or file not accessible: {e}")
                    abort(400, description="File save failed or not accessible.")

                append_filepaths.append(file_path)
        except Exception as e:
            logger.error(f"Error saving the SHP files: {e}")
            abort(400, message=f"Error handling SHP files: {e} - api usage has not been recorded.")

        target_file_path = None
        try:
            # Save and extract ZIP file
            file = target["file"]
            filename = secure_filename(file.filename)
            target_file_path = os.path.join(uploads_dir, filename)
            file.save(target_file_path)

            # Check if the file is accessible
            try:
                wait_for_file(target_file_path)
            except FileNotFoundError as e:
                logger.error(f"File save failed or file not accessible: {e}")
                abort(400, description="File save failed or not accessible.")

        except Exception as e:
            logger.error(f"Error saving the target SHP file: {e}")
            abort(400, message=f"Error saving the target SHP file: {e} - api usage has not been recorded.")

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_shp_append_task.delay(request_size, target_file_path, append_filepaths, uploads_dir, shp_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip SHP append task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_shp_append(request_size, target_file_path, append_filepaths, uploads_dir, shp_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the SHP file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=shp_data["to_file"])

        return response