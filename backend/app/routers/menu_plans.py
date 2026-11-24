from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response

from app.dependencies import get_current_session, get_db
from app.schemas.e2e import (
    MenuGenerateInput,
    MenuItemLock,
    MenuItemUpdate,
    MenuRegenerateInput,
    UndoInput,
)
from app.schemas.error import ErrorResponse
from app.services import menu_plan_service

router = APIRouter(
    prefix="/menu-plans",
    tags=["Menu plans"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422)},
)


@router.post("/generate", status_code=201)
def generate(
    payload: MenuGenerateInput,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.generate(db, session["session_id"], payload)


@router.get("")
def list_plans(
    member_id: Annotated[int | None, Query(alias="memberId", gt=0)] = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.list_plans(
        db, session["session_id"], member_id, limit, cursor
    )


@router.get("/{planId}/items/{itemId}/alternatives")
def alternatives(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    item_id: Annotated[int, Path(alias="itemId", gt=0)],
    limit: int = Query(default=5, ge=1, le=10),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.alternatives(
        db, session["session_id"], plan_id, item_id, limit
    )


@router.patch("/{planId}/items/{itemId}")
def change_item(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    item_id: Annotated[int, Path(alias="itemId", gt=0)],
    payload: MenuItemUpdate,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.change_item(
        db, session["session_id"], plan_id, item_id, payload
    )


@router.put("/{planId}/items/{itemId}/lock")
def lock_item(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    item_id: Annotated[int, Path(alias="itemId", gt=0)],
    payload: MenuItemLock,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.lock_item(
        db, session["session_id"], plan_id, item_id, payload.locked
    )


@router.post("/{planId}/regenerate")
def regenerate(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    payload: MenuRegenerateInput,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.regenerate(db, session["session_id"], plan_id, payload)


@router.post("/{planId}/undo")
def undo(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    payload: UndoInput,
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.undo(db, session["session_id"], plan_id, payload.steps)


@router.post("/{planId}/validate")
def validate(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.validate(db, session["session_id"], plan_id)


@router.get("/{planId}/export")
def export(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    output_format: Literal["pdf", "html"] = Query(default="pdf", alias="format"),
    font_scale: Literal["normal", "large", "xlarge"] = Query(
        default="large", alias="fontScale"
    ),
    include_nutrition: bool = Query(default=True, alias="includeNutrition"),
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return menu_plan_service.export(
        db,
        session["session_id"],
        plan_id,
        output_format,
        font_scale,
        include_nutrition,
    )


@router.delete("/{planId}", status_code=204)
def delete(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    menu_plan_service.delete(db, session["session_id"], plan_id)
    return Response(status_code=204)


@router.get("/{planId}")
def get_plan(
    plan_id: Annotated[int, Path(alias="planId", gt=0)],
    session=Depends(get_current_session),
    db=Depends(get_db),
):
    return {"data": menu_plan_service.detail(db, session["session_id"], plan_id)}
