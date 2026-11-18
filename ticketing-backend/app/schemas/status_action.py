from datetime import datetime
from pydantic import BaseModel


class StatusActionResponse(BaseModel):
    success: bool
    message: str
    entity_id: str
    entity_type: str
    status: str
    changed_at: datetime | None