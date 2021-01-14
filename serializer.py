from marshmallow import Schema
from marshmallow.fields import (
    Integer,
    String,
    Boolean
)


class JobSerializer(Schema):
    degree_required = Boolean()
    for_disabled = Boolean()
    for_students = Boolean()
    full_time = Boolean()
    half_time = Boolean()
    experience = Integer()
    max_salary = Integer()
    min_salary = Integer()
    company = String()
    title = String()
