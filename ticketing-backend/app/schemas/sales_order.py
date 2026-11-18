from pydantic import BaseModel, Field


class SalesOrderItem(BaseModel):
    type: str = Field(..., pattern="^(ticket_type|sale_group)$")
    id: str


class UpdateSalesOrderRequest(BaseModel):
    items: list[SalesOrderItem]


class UpdateGroupTicketTypesOrderRequest(BaseModel):
    ticket_type_ids: list[str]


class OrderActionResponse(BaseModel):
    success: bool
    message: str