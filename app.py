import os
import pyproj
import shutil

from flask import Flask
from flask_smorest import Api
from dotenv import load_dotenv 
from flask_cors import CORS

from celery_worker import celery_init_app
from utils.logger import get_logger
from db import redis_url

from resources.v1.transform import GeojsonBlueprint
from resources.v1.transform import ShapefileBlueprint
from resources.v1.transform import GeopackageBlueprint
from resources.v1.transform import DXFBlueprint

from resources.v1.transform import AsyncTaskResultBlueprint

logger = get_logger(__name__)

def create_app(db_name=None):
    app = Flask(__name__)
    # Load up the environment variables
    load_dotenv()

    # Get the existing PROJ_LIB path, if set
    existing_proj_lib = os.environ.get('PROJ_LIB', pyproj.datadir.get_data_dir())

    # Define the path to your grid files
    custom_grid_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grids')

    # Copy all files from custom_grid_path to existing_proj_lib
    try:
        if os.path.exists(custom_grid_path):
            for file_name in os.listdir(custom_grid_path):
                source_file = os.path.join(custom_grid_path, file_name)
                destination_file = os.path.join(existing_proj_lib, file_name)
                if os.path.isfile(source_file):
                    if os.path.exists(destination_file):
                        logger.info(f"File {file_name} already exists in {existing_proj_lib}. Skipping.")
                    else:
                        shutil.copy(source_file, destination_file)
                        logger.info(f"Copied {file_name} to {existing_proj_lib}")
            logger.info(f"Finished copying grid files to {existing_proj_lib}")
        else:
            logger.info(f"Custom grid path {custom_grid_path} does not exist.")
    except Exception as e:
        logger.error(f"Error copying files: {e}")

    # Configure Flask app with Celery settings using a dictionary under CELERY key
    app.config.from_mapping(
        CELERY=dict(
            broker_url=redis_url,
            result_backend=redis_url,
            task_time_limit=900,  # 15 minutes (hard limit)
            task_soft_time_limit=840,  # 14 minutes (soft limit)
            worker_prefetch_multiplier=1,  # Disable prefetching
        ),
    )
    celery_init_app(app)

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["API_TITLE"] = "GeoFlip REST API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.1.0"
    if os.getenv("FLASK_ENV") == "development":
        app.config["OPENAPI_URL_PREFIX"] = "/"
        app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
        app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    app.config["API_SPEC_OPTIONS"] = {
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        },
        "security": [{"BearerAuth": []}]
    }
    app.config["API_TITLE"] = "GeoFlip REST API"

    api = Api(app)

    # disable CORS for testing
    if os.getenv("FLASK_ENV") != "testing":
        # Enable CORS for transformation-related blueprints with open access
        CORS(GeojsonBlueprint)
        CORS(ShapefileBlueprint)
        CORS(AsyncTaskResultBlueprint)
        CORS(GeopackageBlueprint)
        CORS(DXFBlueprint)

    # register transformation blueprints
    api.register_blueprint(GeojsonBlueprint)
    api.register_blueprint(ShapefileBlueprint)
    api.register_blueprint(AsyncTaskResultBlueprint)
    api.register_blueprint(GeopackageBlueprint)
    api.register_blueprint(DXFBlueprint)

    return app