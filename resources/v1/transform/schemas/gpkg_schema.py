from marshmallow import Schema, fields, validates_schema, ValidationError, INCLUDE
from flask_smorest.fields import Upload
import json
from .transformation_schema import TransformationSchema
from .output_schema import validate_output_format, validate_output_crs
from .files_schema import MultipleFilesField

class JSONString(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            gpkg_data = json.loads(value)
            errors = GeopackageSchema().validate(gpkg_data)

            if errors:
                raise ValidationError(errors)
            
            if "transformations" not in gpkg_data:
                gpkg_data["transformations"] = []
                
            if "to_file" not in gpkg_data:
                gpkg_data["to_file"] = False

            return gpkg_data
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in 'config' field.")

class MultipartFormGPKGConfigValidator(Schema):
    config = JSONString(required=True, metadata={"description":"Configuration data for the transformation as a JSON string"})

class MultipartFormGPKGFileValidator(Schema):
    file = Upload(format="binary", required=True, metadata={"description":"A .gpkg file containing all the required geopackage components"})

class MultipartFormGPKGMergeFilesValidator(Schema):
    files = MultipleFilesField(required=True, metadata={"description": "A list .gpkg files"})

class GeopackageSchema(Schema):
    output_format = fields.Str(required=True, validate=validate_output_format)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    to_file = fields.Bool(required=False, load_default=False)
    output_crs = fields.Str(validate=validate_output_crs)

    # as long as the output format is not geojson, output_crs is required
    # valid epsg formats are handled by pyproj, which will generate an appropriate error message
    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    class Meta:
        unknown = INCLUDE
