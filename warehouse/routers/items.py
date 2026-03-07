from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

import models
from auth import require_user, require_admin
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/items", response_class=HTMLResponse)
def list_items(
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    items = db.query(models.Item).order_by(models.Item.sku).all()
    return templates.TemplateResponse(
        "items.html",
        {"request": request, "items": items, "user": user, "msg": msg, "error": error},
    )


@router.post("/items")
def create_item(
    request: Request,
    sku: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    width_cm: float = Form(...),
    height_cm: float = Form(...),
    depth_cm: float = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    sku = sku.strip().upper()
    if db.query(models.Item).filter(models.Item.sku == sku).first():
        return RedirectResponse(f"/items?error=SKU+{sku}+already+exists", status_code=303)
    db.add(models.Item(
        sku=sku,
        name=name.strip(),
        description=description.strip(),
        width_cm=width_cm,
        height_cm=height_cm,
        depth_cm=depth_cm,
    ))
    db.commit()
    return RedirectResponse(f"/items?msg=Item+{sku}+created", status_code=303)


@router.post("/items/{item_id}/delete")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    item = db.get(models.Item, item_id)
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/items?msg=Item+deleted", status_code=303)
