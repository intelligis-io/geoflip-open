from marshmallow import ValidationError

def validate_buffer_request(data):
    if 'distance' not in data or 'units' not in data:
        raise ValidationError("Both 'distance' and 'units' must be provided for 'buffer' transformations.")
    else:
        valid_units = ['meters', 'kilometers', 'miles', 'feet']
        if data['units'] not in valid_units:
            raise ValidationError(f"Invalid unit. Supported units are: {', '.join(valid_units)}.")