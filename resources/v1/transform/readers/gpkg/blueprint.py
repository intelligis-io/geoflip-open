import os
import uuid

from flask import request, make_response, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.utils import secure_filename

from celery import shared_task

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import generate_output_file_stream

from resources.v1.transform.schemas import MultipartFormGPKGConfigValidator, MultipartFormGPKGFileValidator, MultipartFormGPKGMergeFilesValidator 
from .service import handle_gpkg_transform, handle_gpkg_merge, handle_gpkg_append
from utils.file_handling import wait_for_file

logger = get_logger(__name__)

@shared_task(bind=True, ignore_result=False)
def create_gpkg_transform_task(self, request_size, file_path, uploads_dir, gpkg_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip GPKG task has started'})
    return handle_gpkg_transform(request_size, file_path, uploads_dir, gpkg_data, request_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_gpkg_merge_task(self, request_size, file_paths, uploads_dir, gpkg_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip GPKG task has started'})
    return handle_gpkg_merge(request_size, file_paths, uploads_dir, gpkg_data, request_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_gpkg_append_task(self, request_size, target_filepath, append_filepaths, uploads_dir, gpkg_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip GPKG task has started'})
    return handle_gpkg_append(request_size, target_filepath, append_filepaths, uploads_dir, gpkg_data, request_id, celery_task=self)

GeopackageBlueprint = Blueprint("Geopackage", __name__, description="Geopackage transformation endpoints")

@GeopackageBlueprint.route("/v1/transform/gpkg", methods=['POST'])
class Geopackage(MethodView):
    @GeopackageBlueprint.arguments(MultipartFormGPKGFileValidator, location="files", description="multipart/form-data 'file' containing a geopackage file")
    @GeopackageBlueprint.arguments(MultipartFormGPKGConfigValidator, location="form", description="multipart/form-data containing the transformation configuration")
    def post(self, files, form):
        gpkg_data = form['config']
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
        # check that we are getting gpkg files only
        if not filename.lower().endswith('.gpkg'):
            abort(400, message=f"Invalid file type: {file.filename}. Only .gpkg files are accepted.")
    
        file_path = os.path.join(uploads_dir, filename)
        file.save(file_path)

        # Check if the file is accessible
        try:
            wait_for_file(file_path)
        except FileNotFoundError as e:
            logger.error(f"File save failed or file not accessible: {e}")
            abort(400, description="File save failed or not accessible.")

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_gpkg_transform_task.delay(request_size, file_path, uploads_dir, gpkg_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip GPKG task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_gpkg_transform(request_size, file_path, uploads_dir, gpkg_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the GPKG file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=gpkg_data["to_file"])

        return response
    
@GeopackageBlueprint.route("/v1/transform/gpkg/merge", methods=['POST'])
class GPKGMerge(MethodView):
    @GeopackageBlueprint.arguments(MultipartFormGPKGMergeFilesValidator, location="files", description="multipart/form-data 'files' containing a series of gpkg files")
    @GeopackageBlueprint.arguments(MultipartFormGPKGConfigValidator, location="form", description="multipart/form-data containing the transformation configuration to be applied after merging")
    def post(self, files, form):
        gpkg_data = form['config']
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        #  make a folder to extract the zip file
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # Retrieve the geopackages from the request
        filepaths = []
        try:
            for file in files['files']:
                filename = secure_filename(file.filename)

                # check that we are getting gpkg files only
                if not filename.lower().endswith('.gpkg'):
                    abort(400, message=f"Invalid file type: {file.filename}. Only .gpkg files are accepted.")
            
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
            logger.error(f"Error handling the GPKG files: {e}")
            abort(400, message=f"Error handling GPKG files: {e} - api usage has not been recorded.")

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_gpkg_merge_task.delay(request_size, filepaths, uploads_dir, gpkg_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip GPKG task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_gpkg_merge(request_size, filepaths, uploads_dir, gpkg_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the GPKG file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=gpkg_data["to_file"])

        return response
     
@GeopackageBlueprint.route("/v1/transform/gpkg/append", methods=['POST'])
class GPKGAppend(MethodView):
    @GeopackageBlueprint.arguments(MultipartFormGPKGFileValidator, location="files", description="multipart/form-data 'file' containing a geopackage file")
    @GeopackageBlueprint.arguments(MultipartFormGPKGMergeFilesValidator, location="files", description="multipart/form-data 'files' containing a series of gpkg files")
    @GeopackageBlueprint.arguments(MultipartFormGPKGConfigValidator, location="form", description="multipart/form-data containing the transformation configuration to be applied after merging")
    def post(self, target, files, form):
        gpkg_data = form['config']
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        #  make a folder to extract the zip file
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # handle target file
        target_filepath = None
        try:
            file = target["file"]
            filename = secure_filename(file.filename)
            # check that we are getting gpkg files only
            if not filename.lower().endswith('.gpkg'):
                abort(400, message=f"Invalid file type: {file.filename}. Only .gpkg files are accepted.")
        
            target_filepath = os.path.join(uploads_dir, filename)
            file.save(target_filepath)

            # Check if the file is accessible
            try:
                wait_for_file(target_filepath)
            except FileNotFoundError as e:
                logger.error(f"File save failed or file not accessible: {e}")
                abort(400, description="File save failed or not accessible.")
                
        except Exception as e:
            logger.error(f"Error handling the GPKG files: {e}")
            abort(400, message=f"Error handling GPKG files: {e} - api usage has not been recorded.")

        # Retrieve the geopackages from the request
        append_filepaths = []
        try:
            for file in files['files']:
                filename = secure_filename(file.filename)

                # check that we are getting gpkg files only
                if not filename.lower().endswith('.gpkg'):
                    abort(400, message=f"Invalid file type: {file.filename}. Only .gpkg files are accepted.")
            
                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)

                # Check if the file is accessible
                try:
                    wait_for_file(file_path)
                except FileNotFoundError as e:
                    logger.error(f"File save failed or file not accessible: {e}")
                    abort(400, description="File save failed or not accessible.")

                append_filepaths.append(file_path)
        except Exception as e:
            logger.error(f"Error handling the GPKG files: {e}")
            abort(400, message=f"Error handling GPKG files: {e} - api usage has not been recorded.")

        response = None
        if asyncRequest:
            # call the service to handle the shapefile transformation
            result = create_gpkg_append_task.delay(request_size, target_filepath, append_filepaths, uploads_dir, gpkg_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip GPKG task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_gpkg_append(request_size, target_filepath, append_filepaths, uploads_dir, gpkg_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the GPKG file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=gpkg_data["to_file"])

        return response  