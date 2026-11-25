from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.core.config import settings
from app.core.exceptions import AppException
from app.dependencies import get_db
from app.schemas.rules import RuleEvaluationInput, RuleScope
from app.services import rules_service

router = APIRouter(prefix="/rules", tags=["Rules"])


def get_evaluation_db():
    if settings.environment not in {"development", "test"}:
        raise AppException("NOT_FOUND", "Not found", 404)
    yield from get_db()


@router.get("")
def list_rules(
    condition: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    nutrient: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    scope: RuleScope | None = None,
    enabled: bool = True,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    return rules_service.list_rules(
        db, condition, nutrient, scope, enabled, limit, cursor
    )


@router.post("/evaluate")
def evaluate_rules(payload: RuleEvaluationInput, db=Depends(get_evaluation_db)):
    return rules_service.evaluate(db, payload)


@router.get("/{ruleId}")
def get_rule(
    rule_id: Annotated[str, Path(alias="ruleId", min_length=1, max_length=80)],
    db=Depends(get_db),
):
    return rules_service.get_rule(db, rule_id)
