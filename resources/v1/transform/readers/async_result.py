import json
import os

from flask_smorest import Blueprint, abort
from flask.views import MethodView
from celery.result import AsyncResult

from resources.v1.transform.schemas import AsyncTaskResultSchema
from flask import current_app, g

from resources.v1.transform.format.output_manager import generate_output_file_stream
from db import redis_client

AsyncTaskResultBlueprint = Blueprint("Async Task Result", __name__, description="Async result and output endpoints")

@AsyncTaskResultBlueprint.route("/v1/transform/result/<string:task_id>", methods=['GET'])
class AsyncTaskResult(MethodView):
    @AsyncTaskResultBlueprint.response(200, AsyncTaskResultSchema, description="async task result")
    def get(self, task_id):
        try:
            result = AsyncResult(task_id)
            response_data = {'state': result.state}

            if result.state == 'PENDING':
                response_data['message'] = f'Task id {task_id} is pending execution or no longer exists'

            elif result.state == 'STARTED':
                if 'message' in result.info:
                    response_data['message'] = result.info['message']

            elif result.state == 'PROCESSING':
                if 'message' in result.info:
                    response_data['message'] = result.info['message']

            elif result.state == 'SUCCESS':
                user_id = g.user.user_id
                transform_result = result.result
                transform_result["user_id"] = user_id

                redis_data = json.dumps(transform_result)
                output_id = f"o_{task_id}"
                # Check if the key already exists in Redis
                if not redis_client.exists(output_id):
                    # Key doesn't exist, so we create it
                    redis_client.set(output_id, redis_data)

                response_data['message'] = 'Task completed successfully'
                response_data['output_url'] = f"{os.getenv('API_URL')}/v1/transform/output/{output_id}"

                result.forget()
            else:
                response_data['message'] = "Task failed during processing"
                response_data['error'] = str(result.info)
                response_data["state"] = "FAILURE"

            return response_data
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            abort(500, message=f"Server error: {str(e)}")
        
@AsyncTaskResultBlueprint.route("/v1/transform/output/<string:output_id>", methods=['GET'])
class AsyncTaskOutput(MethodView):
    def get(self, output_id):
        user_id = g.user.user_id

        try:
            result_data = json.loads(redis_client.get(output_id))
        except TypeError:
            abort(404, message="Output ID not found")
        
        if result_data["user_id"] != user_id:
            abort(404, message="User does not have access to this output")

        response = generate_output_file_stream(result_data, to_file=result_data["to_file"])
        redis_client.delete(output_id)

        return response