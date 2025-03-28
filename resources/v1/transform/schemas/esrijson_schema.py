from marshmallow import Schema, fields, validates_schema, ValidationError, INCLUDE
from .transformation_schema import TransformationSchema
from .output_schema import validate_output_format, validate_output_crs


def is_valid_esrijson(data):
    """
    Basic validation that checks if the incoming data has
    'spatialReference' (with a 'wkid') and 'features'.
    This can be expanded with additional checks if needed.
    """
    if not isinstance(data, dict):
        raise ValidationError("EsriJSON must be a dictionary.")

    # Check required top-level keys
    if "spatialReference" not in data:
        raise ValidationError("Invalid EsriJSON: missing 'spatialReference'.")
    if "features" not in data:
        raise ValidationError("Invalid EsriJSON: missing 'features'.")

    # Check that wkid exists (this is commonly used in ArcGIS)
    sr = data["spatialReference"]
    if not isinstance(sr, dict) or "wkid" not in sr:
        raise ValidationError("Invalid EsriJSON: 'spatialReference.wkid' is required.")

    # Check that features is a list
    feats = data["features"]
    if not isinstance(feats, list):
        raise ValidationError("Invalid EsriJSON: 'features' must be a list.")

    # Optionally, you could iterate over each feature to ensure it has
    # 'attributes' and 'geometry' keys:
    for feature in feats:
        if "attributes" not in feature or "geometry" not in feature:
            raise ValidationError("Each feature must contain 'attributes' and 'geometry'.")

    # If all checks pass, it's "valid enough" to be processed further.
            
class EsriJSONSchema(Schema):
    """
    Validates an incoming payload that contains EsriJSON input 
    plus optional transformations and output settings.
    """
    input_esrijson = fields.Dict(required=True, validate=is_valid_esrijson)
    output_format = fields.Str(required=True, validate=validate_output_format)
    to_file = fields.Bool(required=False, load_default=False)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)

    @validates_schema
    def validate_crs(self, data, **kwargs):
        # If output_format is not "geojson", then output_crs is required
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    class Meta:
        unknown = INCLUDE

class EsriJSONMergeSchema(Schema):
    input_esrijson_list = fields.List(fields.Dict(required=True, validate=is_valid_esrijson), required=True, metadata={"description":"List of GeoJSON objects to be merged."})
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

class EsriJSONAppendSchema(Schema):
    append_esrijson_list = fields.List(fields.Dict(required=True, validate=is_valid_esrijson), required=True, metadata={"description":"List of GeoJSON objects to be merged."})
    target_esrijson = fields.Dict(required=True, validate=is_valid_esrijson)
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
