from marshmallow import ValidationError

def validate_union_request(data):
    # this is not actually since the 'type' key is required in the parent transformation
    # but its included for completeness
    if 'type' not in data:
        raise ValidationError("'type' must be provided for 'union' transformations.")
    if data['type'] != 'union':
        raise ValidationError("Invalid type for 'union' transformation.")