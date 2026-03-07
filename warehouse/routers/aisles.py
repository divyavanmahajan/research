from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_user, require_admin
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/aisles", response_class=HTMLResponse)
def list_aisles(
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    aisles = db.query(models.Aisle).order_by(models.Aisle.code).all()
    return templates.TemplateResponse(
        "aisles.html",
        {"request": request, "aisles": aisles, "user": user, "msg": msg, "error": error},
    )


@router.post("/aisles")
def create_aisle(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    code = code.strip().upper()
    if db.query(models.Aisle).filter(models.Aisle.code == code).first():
        return RedirectResponse(f"/aisles?error=Aisle+{code}+already+exists", status_code=303)
    db.add(models.Aisle(code=code, name=name.strip()))
    db.commit()
    return RedirectResponse(f"/aisles?msg=Aisle+{code}+created", status_code=303)


@router.post("/aisles/{aisle_id}/delete")
def delete_aisle(
    aisle_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    aisle = db.get(models.Aisle, aisle_id)
    if aisle:
        db.delete(aisle)
        db.commit()
    return RedirectResponse("/aisles?msg=Aisle+deleted", status_code=303)
