from datetime import datetime
from pydantic import BaseModel


class SoftDeleteResponse(BaseModel):
    success: bool
    message: str
    entity_id: str
    entity_type: str
    status: str
    deleted_at: datetime | None