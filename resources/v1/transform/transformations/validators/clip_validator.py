from marshmallow import ValidationError

def validate_clip_request(data):
    if 'clipping_geojson' not in data:
        raise ValidationError("'clipping_geojson' must be provided for 'clip' transformations.")
    else:
        required_keys = ['type', 'features']
        if not all(key in data['clipping_geojson'] for key in required_keys):
            raise ValidationError("Invalid clipping_geojson format.")