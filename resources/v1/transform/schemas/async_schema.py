from marshmallow import Schema, fields


class AsyncTaskResultSchema(Schema):
    state = fields.Str(required=True)
    message = fields.Str(required=False)
    output_url = fields.Str(required=False)
    error = fields.Str(required=False)