"""Usage events API: the SPA reports session starts, page views, section opens and heartbeats."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.limiter import limiter, user_rate_key
from app.db.session import get_db
from app.models.user import User
from app.schemas.usage import EventsIn
from app.services import usage_service

router = APIRouter(tags=["events"])


@router.post("/events", status_code=204)
# One visible tab heartbeats 120 times an hour; 600 leaves room for several tabs and devices.
@limiter.limit("600/hour", key_func=user_rate_key)
def post_events(
    request: Request,
    payload: EventsIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    usage_service.record_events(db, current_user.id, payload.events)
    return Response(status_code=204)
