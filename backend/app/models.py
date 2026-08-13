import enum

from app.extensions import db


class Borough(str, enum.Enum):
    MANHATTAN = "MANHATTAN"
    BRONX = "BRONX"
    BROOKLYN = "BROOKLYN"
    QUEENS = "QUEENS"
    STATEN_ISLAND = "STATEN ISLAND"


class Complaint(db.Model):
    __tablename__ = "complaints"

    unique_key = db.Column(db.BigInteger, primary_key=True, autoincrement=False)
    created_date = db.Column(db.DateTime(timezone=True), nullable=False)
    closed_date = db.Column(db.DateTime(timezone=True), nullable=True)
    complaint_type = db.Column(db.Text, nullable=False)
    descriptor = db.Column(db.Text, nullable=True)
    resolution_description = db.Column(db.Text, nullable=True)
    borough = db.Column(
        db.Enum(
            Borough,
            name="borough",
            native_enum=False,
            length=20,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    incident_zip = db.Column(db.Text, nullable=True)
    agency = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.Index("idx_complaints_created_date", "created_date"),
        db.Index("idx_complaints_borough_created_date", "borough", "created_date"),
        db.Index("idx_complaints_complaint_type_created_date", "complaint_type", "created_date"),
    )

    def __repr__(self) -> str:
        return f"Complaint({self.unique_key})"
