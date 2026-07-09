from enum import Enum

from tortoise import fields
from tortoise.models import Model


class Borough(str, Enum):
    MANHATTAN = "MANHATTAN"
    BRONX = "BRONX"
    BROOKLYN = "BROOKLYN"
    QUEENS = "QUEENS"
    STATEN_ISLAND = "STATEN ISLAND"


class Complaint(Model):
    unique_key = fields.BigIntField(pk=True, generated=False)
    created_date = fields.DatetimeField(index=True)
    closed_date = fields.DatetimeField(null=True)
    complaint_type = fields.TextField()
    descriptor = fields.TextField(null=True)
    borough = fields.CharEnumField(Borough, max_length=20, null=True)
    incident_zip = fields.TextField(null=True)
    agency = fields.TextField(null=True)
    status = fields.TextField(null=True)
    latitude = fields.FloatField(null=True)
    longitude = fields.FloatField(null=True)

    class Meta:
        table = "complaints"
        indexes = (
            ("borough", "created_date"),
            ("complaint_type", "created_date"),
        )

    def __str__(self) -> str:
        return f"Complaint({self.unique_key})"
