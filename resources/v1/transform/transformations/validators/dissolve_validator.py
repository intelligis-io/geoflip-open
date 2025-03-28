from marshmallow import ValidationError


def validate_dissolve_request(data):
    if "by" not in data:
        raise ValidationError(
            "'by' must be provided for 'dissolve' transformations."
        )
    else:
        if not(isinstance(data["by"], list) and len(data["by"]) != 0):
            raise ValidationError("Invalid 'by' should be a list of fields with at least 1 field.")
