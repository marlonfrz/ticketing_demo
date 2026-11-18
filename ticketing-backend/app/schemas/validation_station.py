from datetime import datetime

from pydantic import BaseModel, Field


class ValidationQuotaRequestCreate(BaseModel):
    requested_count: int = Field(..., ge=1, le=100)
    promoter_note: str | None = Field(default=None, max_length=1000)


class ValidationQuotaRequestReview(BaseModel):
    approved_count: int | None = Field(default=None, ge=0, le=100)
    status: str
    admin_note: str | None = Field(default=None, max_length=1000)


class ValidationQuotaRequestResponse(BaseModel):
    id: str
    session_id: str
    event_id: str
    event_title: str
    session_label: str
    requested_count: int
    approved_count: int | None
    status: str
    promoter_note: str | None
    admin_note: str | None
    requested_by_user_id: str
    requested_by_name: str
    reviewed_by_user_id: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ValidationStationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    responsible_name: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class ValidationStationActivate(BaseModel):
    token: str = Field(..., min_length=20, max_length=255)
    responsible_name: str | None = Field(default=None, max_length=255)


class ValidationStationResponse(BaseModel):
    id: str
    session_id: str
    event_id: str
    event_title: str
    session_label: str
    name: str
    responsible_name: str | None
    notes: str | None
    status: str
    validated_count: int = 0
    activated_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ValidationStationLinkResponse(BaseModel):
    station: ValidationStationResponse
    activation_url: str
    activation_expires_at: datetime


class ValidationStationActivityResponse(BaseModel):
    id: str
    validation_station_id: str
    validation_station_name: str
    ticket_id: str | None
    ticket_code: str | None
    result: str
    message: str
    validation_type: str
    notes: str | None
    validated_at: datetime


class ValidationStationActivityListResponse(BaseModel):
    station: ValidationStationResponse
    items: list[ValidationStationActivityResponse]
    total: int
    limit: int
    offset: int


class ValidationSessionManagementResponse(BaseModel):
    session_id: str
    approved_quota: int
    occupied_slots: int
    available_slots: int
    validated_count: int
    latest_request: ValidationQuotaRequestResponse | None
    requests: list[ValidationQuotaRequestResponse]
    stations: list[ValidationStationResponse]
    recent_validations: list[ValidationStationActivityResponse]


class ValidationStationSessionResponse(BaseModel):
    station: ValidationStationResponse


class ValidationStationScanRequest(BaseModel):
    qr_token: str = Field(..., min_length=4, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class ValidationStationIncidentRequest(BaseModel):
    message: str = Field(..., min_length=4, max_length=1000)
    qr_token: str | None = Field(default=None, max_length=255)
