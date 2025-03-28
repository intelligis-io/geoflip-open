from marshmallow import Schema, fields, validates_schema, ValidationError, INCLUDE
from flask_smorest.fields import Upload
import json
from .transformation_schema import TransformationSchema
from .output_schema import validate_output_format, validate_output_crs
from .files_schema import MultipleFilesField

class JSONString(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            shp_data = json.loads(value)
            errors = ShapefileSchema().validate(shp_data)

            if errors:
                raise ValidationError(errors)
            
            if "transformations" not in shp_data:
                shp_data["transformations"] = []

            if "to_file" not in shp_data:
                shp_data["to_file"] = False

            return shp_data
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in 'config' field.")

class MultipartFormSHPConfigValidator(Schema):
    config = JSONString(required=True, metadata={"description":"Configuration data for the transformation as a JSON string"})

class MultipartFormSHPFileValidator(Schema):
    file = Upload(format="binary", required=True, metadata={"description":"A zip file containing all the required shapefile components"})

class MultipartFormSHPMergeFilesValidator(Schema):
    files = MultipleFilesField(required=True, metadata={"description": "A list of zip files containing all the required shapefile components"})

class ShapefileSchema(Schema):
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
