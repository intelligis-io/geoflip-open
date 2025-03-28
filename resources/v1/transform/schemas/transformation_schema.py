from marshmallow import Schema, fields, validates_schema, validate
from ..transformations.validators.buffer_validator import validate_buffer_request
from ..transformations.validators.clip_validator import validate_clip_request
from ..transformations.validators.erase_validator import validate_erase_request
from ..transformations.validators.dissolve_validator import validate_dissolve_request
from ..transformations.validators.union_validator import validate_union_request
from marshmallow import ValidationError


class TransformationSchema(Schema):
    type = fields.Str(
        required=True, validate=validate.OneOf(["buffer", "clip", "erase", "dissolve", "union"])
    )
    distance = fields.Float(required=False)
    units = fields.Str(required=False)
    simplify_tolerance = fields.Float(required=False)
    clipping_geojson = fields.Dict(required=False)
    erasing_geojson = fields.Dict(required=False)
    by = fields.List(fields.Str(), required=False)

    @validates_schema
    def check_required_fields(self, data, **kwargs):
        match data["type"]:
            case "buffer":
                validate_buffer_request(data)
            case "clip":
                validate_clip_request(data)
            case "erase":
                validate_erase_request(data)
            case "dissolve":
                validate_dissolve_request(data)
            case "union":
                validate_union_request(data)
            case _:
                raise ValidationError("Invalid transformation type.")
