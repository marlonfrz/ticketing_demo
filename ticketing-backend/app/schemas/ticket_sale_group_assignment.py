from pydantic import BaseModel, Field


class AssignTicketTypeToSaleGroupRequest(BaseModel):
    sale_group_id: str
    sale_order: int = Field(..., gt=0)


class RemoveTicketTypeFromSaleGroupResponse(BaseModel):
    success: bool
    message: str
    ticket_type_id: str
    sale_group_id: str | None
    sale_order: int | None