import datetime

from pydantic import BaseModel

from database.models import DCMNodeEndpoint


class IncomingDetails(BaseModel):
    endpoint: DCMNodeEndpoint
    path: str
    last_timestamp: datetime.datetime
    first_timestamp: datetime.datetime
    TransferSyntaxUID: str
