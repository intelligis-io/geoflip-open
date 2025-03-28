import os
import uuid

from flask import request, make_response, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.utils import secure_filename

from celery import shared_task

from utils.logger import get_logger
from resources.v1.transform.format.output_manager import generate_output_file_stream
from resources.v1.transform.schemas import MultipartFormDXFConfigValidator, MultipartFormDXFFileValidator, MultipartFormDXFMergeFilesValidator, MultipartFormDXFMergeConfigValidator, MultipartFormDXFAppendConfigValidator
from .service import handle_dxf_transform, handle_dxf_merge, handle_dxf_append
from utils.file_handling import wait_for_file

logger = get_logger(__name__)

@shared_task(bind=True, ignore_result=False)
def create_dxf_transform_task(self, request_size, file_path, uploads_dir, dxf_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip DXF transform task has started'})
    return handle_dxf_transform(request_size, file_path, uploads_dir, dxf_data, request_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_dxf_merge_task(self, request_size, file_paths, input_crs_mapping, uploads_dir, dxf_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip DXF merge task has started'})
    return handle_dxf_merge(request_size, file_paths, input_crs_mapping, uploads_dir, dxf_data, request_id, celery_task=self)

@shared_task(bind=True, ignore_result=False)
def create_dxf_append_task(self, request_size, target_filepath, append_filepaths, append_crs_mapping, uploads_dir, dxf_data, request_id):
    self.update_state(state='STARTED', meta={'message': 'Geoflip DXF append task has started'})
    return handle_dxf_append(request_size, target_filepath, append_filepaths, append_crs_mapping, uploads_dir, dxf_data, request_id, celery_task=self)

DXFBlueprint = Blueprint("AutoCAD DXF", __name__, description="AutoCAD DXF transformation endpoints")

@DXFBlueprint.route("/v1/transform/dxf", methods=['POST'])
class DXF(MethodView):
    @DXFBlueprint.arguments(MultipartFormDXFFileValidator, location="files", description="multipart/form-data 'file' containing a dxf file")
    @DXFBlueprint.arguments(MultipartFormDXFConfigValidator, location="form", description="multipart/form-data containing the transformation configuration")
    def post(self, files, form):
        dxf_data = form['config']
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
        # check that we are getting dxf files only
        if not filename.lower().endswith('.dxf'):
            abort(400, message=f"Invalid file type: {file.filename}. Only .dxf files are accepted.")
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
            # call the service to handle the dxf transformation
            result = create_dxf_transform_task.delay(request_size, file_path, uploads_dir, dxf_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip DXF task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_dxf_transform(request_size, file_path, uploads_dir, dxf_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the DXF file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=dxf_data["to_file"])

        return response
    
@DXFBlueprint.route("/v1/transform/dxf/merge", methods=['POST'])
class DXFMerge(MethodView):
    @DXFBlueprint.arguments(MultipartFormDXFMergeFilesValidator, location="files", description="multipart/form-data 'files' containing a series of DXF files")
    @DXFBlueprint.arguments(MultipartFormDXFMergeConfigValidator, location="form", description="multipart/form-data containing the transformation configuration to be applied after merging")
    def post(self, files, form):
        dxf_data = form['config']
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        # Make a folder to extract the files
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # save the dxf files out from the request
        file_paths = []
        input_crs_mapping = dxf_data['input_crs_mapping']
        file_list = files['files']
        try:
            if len(input_crs_mapping) == 1:
                input_crs_mapping = input_crs_mapping * len(file_list)
            elif len(input_crs_mapping) != len(file_list):
                raise ValueError("Number of CRS entries must match the number of DXF files.")

            for file in file_list:
                filename = secure_filename(file.filename)
                # check that we are getting dxf files only
                if not filename.lower().endswith('.dxf'):
                    raise ValueError(f"included file type '{file.filename}' is not valid. Only .dxf files are accepted.")

                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)

                # Check if the file is accessible
                try:
                    wait_for_file(file_path)
                except FileNotFoundError as e:
                    logger.error(f"File save failed or file not accessible: {e}")
                    abort(400, description="File save failed or not accessible.")

                file_paths.append(file_path)
        except ValueError as e:
            logger.error(f"Invalid input files: {e}")
            abort(400, message=f"Invalid input: {e} - api usage has not been recorded.")
        except Exception as e:
            logger.error(f"Error handling the DXF files: {e}")
            abort(400, message=f"Error handling DXF files: {e} - api usage has not been recorded.")

        response = None
        if asyncRequest:
            # call the service to handle the dxf merge 
            result = create_dxf_merge_task.delay(request_size, file_paths, input_crs_mapping, uploads_dir, dxf_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip DXF merge task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_dxf_merge(request_size, file_paths, input_crs_mapping, uploads_dir, dxf_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the DXF file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=dxf_data["to_file"])

        return response


@DXFBlueprint.route("/v1/transform/dxf/append", methods=['POST'])
class DXFAppend(MethodView):
    @DXFBlueprint.arguments(MultipartFormDXFFileValidator, location="files", description="multipart/form-data 'file' containing a dxf file")
    @DXFBlueprint.arguments(MultipartFormDXFMergeFilesValidator, location="files", description="multipart/form-data 'files' containing a series of DXF files")
    @DXFBlueprint.arguments(MultipartFormDXFAppendConfigValidator, location="form", description="multipart/form-data containing the transformation configuration to be applied after merging")
    def post(self, target, files, form):
        dxf_data = form['config']
        request_size = request.content_length
        request_id = str(uuid.uuid4())

        # Check if async is passed in the URL as ?async=true or ?async=false
        async_param = request.args.get('async', 'false')  # Defaults to 'false'
        asyncRequest = async_param.lower() == 'true'  # Set asyncRequest to True if async=true

        # Make a folder to extract the files
        uploads_dir = os.path.join(os.getenv("UPLOADS_PATH"), request_id)
        os.makedirs(uploads_dir, exist_ok=True)

        target_filepath = None
        try:
            # Save and extract ZIP file
            file = target["file"]
            filename = secure_filename(file.filename)
            # check that we are getting dxf files only
            if not filename.lower().endswith('.dxf'):
                abort(400, message=f"Invalid file type: {file.filename}. Only .dxf files are accepted.")
            target_filepath = os.path.join(uploads_dir, filename)
            file.save(target_filepath)
            # Check if the file is accessible
            try:
                wait_for_file(target_filepath)
            except FileNotFoundError as e:
                logger.error(f"File save failed or file not accessible: {e}")
                abort(400, description="File save failed or not accessible.")
        except ValueError as e:
            logger.error(f"Invalid input files: {e}")
            abort(400, message=f"Invalid input: {e} - api usage has not been recorded.")
        except Exception as e:
            logger.error(f"Error handling the DXF files: {e}")
            abort(400, message=f"Error handling DXF files: {e} - api usage has not been recorded.")

        # save the dxf files out from the request
        append_filepaths = []
        append_crs_mapping = dxf_data['append_crs_mapping']
        file_list = files['files']
        try:
            if len(append_crs_mapping) == 1:
                append_crs_mapping = append_crs_mapping * len(file_list)
            elif len(append_crs_mapping) != len(file_list):
                raise ValueError("Number of CRS entries must match the number of DXF files.")

            for file in file_list:
                filename = secure_filename(file.filename)
                # check that we are getting dxf files only
                if not filename.lower().endswith('.dxf'):
                    raise ValueError(f"included file type '{file.filename}' is not valid. Only .dxf files are accepted.")

                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)

                # Check if the file is accessible
                try:
                    wait_for_file(file_path)
                except FileNotFoundError as e:
                    logger.error(f"File save failed or file not accessible: {e}")
                    abort(400, description="File save failed or not accessible.")

                append_filepaths.append(file_path)
        except ValueError as e:
            logger.error(f"Invalid input files: {e}")
            abort(400, message=f"Invalid input: {e} - api usage has not been recorded.")
        except Exception as e:
            logger.error(f"Error handling the DXF files: {e}")
            abort(400, message=f"Error handling DXF files: {e} - api usage has not been recorded.")

        response = None
        if asyncRequest:
            # call the service to handle the dxf merge 
            result = create_dxf_append_task.delay(request_size, target_filepath, append_filepaths, append_crs_mapping, uploads_dir, dxf_data, request_id)
            response = make_response(jsonify({
                "message": "Geoflip DXF merge task as been created",
                "task_id": result.id,
                "state": "TASK CREATED"
            }), 202)
        else:
            # this is the normal sync route
            try:
                result = handle_dxf_append(request_size, target_filepath, append_filepaths, append_crs_mapping, uploads_dir, dxf_data, request_id)
            except Exception as e:
                logger.error(f"Error handling the DXF file: {e}")
                abort(400, message=f"Geoflip Error - {e}")

            response = generate_output_file_stream(result, to_file=dxf_data["to_file"])

        return response