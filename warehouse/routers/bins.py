from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_user, require_admin
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/bins", response_class=HTMLResponse)
def list_bins(
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    bins = db.query(models.Bin).all()
    # sort by location code
    bins.sort(key=lambda b: b.location_code)
    return templates.TemplateResponse(
        "bins.html",
        {"request": request, "bins": bins, "user": user, "msg": msg, "error": error},
    )


@router.get("/levels/{level_id}/bins", response_class=HTMLResponse)
def list_bins_for_level(
    level_id: int,
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    level = db.get(models.Level, level_id)
    if not level:
        return RedirectResponse("/bins?error=Level+not+found", status_code=303)
    bins = (
        db.query(models.Bin)
        .filter(models.Bin.level_id == level_id)
        .order_by(models.Bin.code)
        .all()
    )
    return templates.TemplateResponse(
        "level_bins.html",
        {"request": request, "level": level, "bins": bins, "user": user,
         "msg": msg, "error": error},
    )


@router.post("/levels/{level_id}/bins")
def create_bin(
    level_id: int,
    code: str = Form(...),
    size_category: str = Form("M"),
    width_cm: float = Form(...),
    height_cm: float = Form(...),
    depth_cm: float = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    level = db.get(models.Level, level_id)
    if not level:
        return RedirectResponse("/bins?error=Level+not+found", status_code=303)
    code = code.strip().upper()
    existing = (
        db.query(models.Bin)
        .filter(models.Bin.level_id == level_id, models.Bin.code == code)
        .first()
    )
    if existing:
        return RedirectResponse(
            f"/levels/{level_id}/bins?error=Bin+{code}+already+exists+on+this+level",
            status_code=303,
        )
    db.add(models.Bin(
        level_id=level_id,
        code=code,
        size_category=size_category,
        width_cm=width_cm,
        height_cm=height_cm,
        depth_cm=depth_cm,
    ))
    db.commit()
    return RedirectResponse(f"/levels/{level_id}/bins?msg=Bin+{code}+created", status_code=303)


@router.post("/bins/{bin_id}/delete")
def delete_bin(
    bin_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    bin_ = db.get(models.Bin, bin_id)
    level_id = bin_.level_id if bin_ else None
    if bin_:
        db.delete(bin_)
        db.commit()
    redirect = f"/levels/{level_id}/bins?msg=Bin+deleted" if level_id else "/bins"
    return RedirectResponse(redirect, status_code=303)
