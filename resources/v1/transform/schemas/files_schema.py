from marshmallow import fields, ValidationError
from flask_smorest.fields import Upload

class MultipleFilesField(fields.List):
    def __init__(self, cls_or_instance=Upload(format="binary"), **kwargs):
        super().__init__(cls_or_instance, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, list):
            raise ValidationError("Expected a list of files.")
        return super()._deserialize(value, attr, data, **kwargs)
