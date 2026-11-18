from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_promoter_or_admin
from app.core.rate_limit import public_relations_register_rate_limit
from app.models.user import User
from app.schemas.public_relations import (
    PublicRelationsRegisterInfoResponse,
    PublicRelationsRegisterRequest,
    PublicRelationsRegisterResponse,
    PublicRelationsSummaryResponse,
)
from app.services.public_relations_service import (
    get_public_relations_registration_info,
    list_public_relations_summary,
    register_public_relations,
)


router = APIRouter(tags=["public-relations"])


@router.get(
    "/events/{event_id}/public-relations/register-info",
    response_model=PublicRelationsRegisterInfoResponse,
)
def public_relations_register_info_route(event_id: str, db: Session = Depends(get_db)):
    return get_public_relations_registration_info(db, event_id)


@router.post(
    "/events/{event_id}/public-relations/register",
    response_model=PublicRelationsRegisterResponse,
)
def register_public_relations_route(
    event_id: str,
    data: PublicRelationsRegisterRequest,
    db: Session = Depends(get_db),
    _: None = Depends(public_relations_register_rate_limit),
):
    return register_public_relations(db, event_id, data)


@router.get(
    "/events/{event_id}/public-relations",
    response_model=list[PublicRelationsSummaryResponse],
)
def list_public_relations_summary_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return list_public_relations_summary(db, event_id, current_user)
