from marshmallow import Schema, fields, validates_schema, ValidationError, INCLUDE
from flask_smorest.fields import Upload
import json
from .transformation_schema import TransformationSchema
from .output_schema import validate_output_format, validate_output_crs
from .files_schema import MultipleFilesField

class DXFJsonConfig(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            dxf_data = json.loads(value)
            errors = DXFSchema().validate(dxf_data)

            if errors:
                raise ValidationError(errors)
            
            if "transformations" not in dxf_data:
                dxf_data["transformations"] = []
            
            if "to_file" not in dxf_data:
                dxf_data["to_file"] = False

            return dxf_data
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in 'config' field.")

class DXFMergeJsonConfig(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            dxf_data = json.loads(value)
            errors = DXFMergeSchema().validate(dxf_data)

            if errors:
                raise ValidationError(errors)
            
            if "transformations" not in dxf_data:
                dxf_data["transformations"] = []

            if "to_file" not in dxf_data:
                dxf_data["to_file"] = False

            return dxf_data
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in 'config' field.")

class DXFAppendJsonConfig(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            dxf_data = json.loads(value)
            errors = DXFAppendSchema().validate(dxf_data)

            if errors:
                raise ValidationError(errors)
            
            if "transformations" not in dxf_data:
                dxf_data["transformations"] = []

            if "to_file" not in dxf_data:
                dxf_data["to_file"] = False
                
            return dxf_data
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in 'config' field.")

class MultipartFormDXFConfigValidator(Schema):
    config = DXFJsonConfig(required=True, metadata={"description":"Configuration data for the transformation as a JSON string"})

class MultipartFormDXFMergeConfigValidator(Schema):
    config = DXFMergeJsonConfig(required=True, metadata={"description":"Configuration data for the merge and transformation as a JSON string"})

class MultipartFormDXFAppendConfigValidator(Schema):
    config = DXFAppendJsonConfig(required=True, metadata={"description":"Configuration data for the append and transformation as a JSON string"})

class MultipartFormDXFFileValidator(Schema):
    file = Upload(format="binary", required=True, metadata={"description":"A .dxf file containing all the required geopackage components"})

class MultipartFormDXFMergeFilesValidator(Schema):
    files = MultipleFilesField(required=True, metadata={"description": "A list of .dxf files."})

class DXFSchema(Schema):
    output_format = fields.Str(required=True, validate=validate_output_format)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)
    to_file = fields.Bool(required=False, load_default=False)
    input_crs = fields.Str(required=True, metadata={"description":"The input CRS of the DXF file"}, error_messages={"required": "The input CRS is required for DXF file inputs, please specify the 'input_crs' field in your request payload."})

    # as long as the output format is not geojson, output_crs is required
    # valid epsg formats are handled by pyproj, which will generate an appropriate error message
    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    class Meta:
        unknown = INCLUDE

class DXFMergeSchema(Schema):
    output_format = fields.Str(required=True, validate=validate_output_format)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)
    to_file = fields.Bool(required=False, load_default=False)
    input_crs_mapping = fields.List(fields.Str(), required=True, metadata={"description": "List of input CRS strings for the DXF files. Provide one CRS to apply to all files, or a matching number of CRS strings to the number of files."})

    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    @validates_schema
    def validate_input_crs_mapping(self, data, **kwargs):
        input_crs_mapping = data.get('input_crs_mapping')
        if isinstance(input_crs_mapping, list):
            if len(input_crs_mapping) == 0:
                raise ValidationError('input_crs_mapping must contain at least one CRS string.')
        else:
            raise ValidationError('input_crs_mapping must be a list.')

    class Meta:
        unknown = INCLUDE

class DXFAppendSchema(Schema):
    output_format = fields.Str(required=True, validate=validate_output_format)
    transformations = fields.List(fields.Nested(TransformationSchema), required=False, load_default=[])
    output_crs = fields.Str(validate=validate_output_crs)
    to_file = fields.Bool(required=False, load_default=False)
    append_crs_mapping = fields.List(fields.Str(), required=True, metadata={"description": "List of input CRS strings for the DXF files. Provide one CRS to apply to all files, or a matching number of CRS strings to the number of files."})
    input_crs = fields.Str(required=True, metadata={"description":"The input CRS of the DXF file"}, error_messages={"required": "The input CRS is required for DXF file input, please specify the 'input_crs' field in your request payload."})

    @validates_schema
    def validate_crs(self, data, **kwargs):
        if data['output_format'] != 'geojson' and 'output_crs' not in data:
            raise ValidationError('output_crs is required when output_format is not geojson.')

    @validates_schema
    def validate_append_crs_mapping(self, data, **kwargs):
        append_crs_mapping = data.get('append_crs_mapping')
        if isinstance(append_crs_mapping, list):
            if len(append_crs_mapping) == 0:
                raise ValidationError('append_crs_mapping must contain at least one CRS string.')
        else:
            raise ValidationError('append_crs_mapping must be a list.')

    class Meta:
        unknown = INCLUDE