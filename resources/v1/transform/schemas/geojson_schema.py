from marshmallow import Schema, fields, validates_schema, ValidationError, INCLUDE
from .transformation_schema import TransformationSchema
from .output_schema import validate_output_format, validate_output_crs


def is_valid_geojson(data):
    required_keys = ['type', 'features']  # Basic keys for a GeoJSON object
    if not all(key in data for key in required_keys):
        raise ValidationError("Invalid GeoJSON format.")
            
class GeoJSONSchema(Schema):
    input_geojson = fields.Dict(required=True, validate=is_valid_geojson)
    output_format = fields.Str(required=True, validate=validate_output_format)
    to_file = fields.Bool(required=False, load_default=False)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)

    # as long as the output format is not geojson, output_crs is required
    # valid epsg formats are handled by pyproj, which will generate an appropriate error message
    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    class Meta:
        unknown = INCLUDE

class GeoJSONMergeSchema(Schema):
    input_geojson_list = fields.List(fields.Dict(required=True, validate=is_valid_geojson), required=True, metadata={"description":"List of GeoJSON objects to be merged."})
    output_format = fields.Str(required=True, validate=validate_output_format)
    to_file = fields.Bool(required=False, load_default=False)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)

    # as long as the output format is not geojson, output_crs is required
    # valid epsg formats are handled by pyproj, which will generate an appropriate error message
    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    class Meta:
        unknown = INCLUDE

class GeoJSONAppendSchema(Schema):
    append_geojson_list = fields.List(fields.Dict(required=True, validate=is_valid_geojson), required=True, metadata={"description":"List of GeoJSON objects to be merged."})
    target_geojson = fields.Dict(required=True, validate=is_valid_geojson)
    output_format = fields.Str(required=True, validate=validate_output_format)
    to_file = fields.Bool(required=False, load_default=False)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)

    # as long as the output format is not geojson, output_crs is required
    # valid epsg formats are handled by pyproj, which will generate an appropriate error message
    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    class Meta:
        unknown = INCLUDE
