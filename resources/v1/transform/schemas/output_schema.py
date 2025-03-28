from marshmallow import ValidationError

def validate_output_format(format):
    valid_formats = ['geojson', 'shp', 'gpkg', 'dxf', 'csv', 'esrijson']
    if format not in valid_formats:
        raise ValidationError(f"Invalid output format. Supported formats are: {', '.join(valid_formats)}.")

def validate_output_crs(crs):
    # NOTE in here you can add in specific validation rules around what CRS you want to enforce as outputs
    pass