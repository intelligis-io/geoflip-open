from marshmallow import ValidationError


def validate_erase_request(data):
    if "erasing_geojson" not in data:
        raise ValidationError(
            "'erasing_geojson' must be provided for 'erase' transformations."
        )
    else:
        required_keys = ["type", "features"]
        if not all(key in data["erasing_geojson"] for key in required_keys):
            raise ValidationError("Invalid erasing_geojson format.")
