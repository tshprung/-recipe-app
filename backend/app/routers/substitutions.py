from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/substitutions", tags=["substitutions"])


@router.post("/report", status_code=201)
def report_substitution(
    payload: schemas.SubstitutionReportRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sub = models.IngredientSubstitution(
        ingredient_name=payload.original_label,
        source_country=payload.source_country,
        target_country=payload.target_country,
        substitution=payload.better_substitution,
        created_by_user_id=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(sub)
    db.commit()
    return {"ok": True}
