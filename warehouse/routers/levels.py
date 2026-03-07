from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_user, require_admin
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/racks/{rack_id}/levels", response_class=HTMLResponse)
def list_levels(
    rack_id: int,
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    rack = db.get(models.Rack, rack_id)
    if not rack:
        return RedirectResponse("/structure?error=Rack+not+found", status_code=303)
    levels = (
        db.query(models.Level)
        .filter(models.Level.rack_id == rack_id)
        .order_by(models.Level.level_num)
        .all()
    )
    return templates.TemplateResponse(
        "levels.html",
        {"request": request, "rack": rack, "levels": levels, "user": user,
         "msg": msg, "error": error},
    )


@router.post("/racks/{rack_id}/levels")
def create_level(
    rack_id: int,
    level_num: int = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    rack = db.get(models.Rack, rack_id)
    if not rack:
        return RedirectResponse("/structure?error=Rack+not+found", status_code=303)
    if level_num not in (1, 2, 3):
        return RedirectResponse(
            f"/racks/{rack_id}/levels?error=Level+number+must+be+1,+2,+or+3", status_code=303
        )
    existing = (
        db.query(models.Level)
        .filter(models.Level.rack_id == rack_id, models.Level.level_num == level_num)
        .first()
    )
    if existing:
        return RedirectResponse(
            f"/racks/{rack_id}/levels?error=Level+{level_num}+already+exists", status_code=303
        )
    db.add(models.Level(rack_id=rack_id, level_num=level_num))
    db.commit()
    return RedirectResponse(f"/racks/{rack_id}/levels?msg=Level+{level_num}+created", status_code=303)


@router.post("/levels/{level_id}/delete")
def delete_level(
    level_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    level = db.get(models.Level, level_id)
    rack_id = level.rack_id if level else None
    if level:
        db.delete(level)
        db.commit()
    redirect = f"/racks/{rack_id}/levels?msg=Level+deleted" if rack_id else "/structure"
    return RedirectResponse(redirect, status_code=303)
