import datetime

from pydantic import BaseModel

class Incoming(BaseModel):
    path: str
    last_timestamp: datetime.datetime
    first_timestamp: datetime.datetime
    PatientID: str
    StudyDescription: str
    SeriesDescription: str
    Modality: str
