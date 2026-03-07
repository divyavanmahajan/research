from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_user
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    bins = db.query(models.Bin).all()
    bins.sort(key=lambda b: b.location_code)
    items = db.query(models.Item).order_by(models.Item.name).all()
    bin_items = db.query(models.BinItem).all()
    return templates.TemplateResponse(
        "inventory.html",
        {
            "request": request,
            "bins": bins,
            "items": items,
            "bin_items": bin_items,
            "user": user,
            "msg": msg,
            "error": error,
        },
    )


@router.post("/inventory/add")
def add_inventory(
    request: Request,
    bin_id: int = Form(...),
    item_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if quantity <= 0:
        return RedirectResponse("/inventory?error=Quantity+must+be+positive", status_code=303)

    bin_ = db.get(models.Bin, bin_id)
    item = db.get(models.Item, item_id)
    if not bin_ or not item:
        return RedirectResponse("/inventory?error=Invalid+bin+or+item", status_code=303)

    # Volume check
    needed = item.volume_cm3 * quantity
    available = bin_.volume_cm3 - bin_.used_volume_cm3
    if needed > available:
        return RedirectResponse(
            f"/inventory?error=Not+enough+space+in+bin+(need+{needed:.0f}cm³,+available+{available:.0f}cm³)",
            status_code=303,
        )

    existing = (
        db.query(models.BinItem)
        .filter(models.BinItem.bin_id == bin_id, models.BinItem.item_id == item_id)
        .first()
    )
    if existing:
        existing.quantity += quantity
    else:
        db.add(models.BinItem(bin_id=bin_id, item_id=item_id, quantity=quantity))
    db.commit()
    return RedirectResponse("/inventory?msg=Inventory+updated", status_code=303)


@router.post("/inventory/remove")
def remove_inventory(
    request: Request,
    bin_id: int = Form(...),
    item_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if quantity <= 0:
        return RedirectResponse("/inventory?error=Quantity+must+be+positive", status_code=303)

    existing = (
        db.query(models.BinItem)
        .filter(models.BinItem.bin_id == bin_id, models.BinItem.item_id == item_id)
        .first()
    )
    if not existing:
        return RedirectResponse("/inventory?error=Item+not+found+in+this+bin", status_code=303)

    if quantity >= existing.quantity:
        db.delete(existing)
    else:
        existing.quantity -= quantity
    db.commit()
    return RedirectResponse("/inventory?msg=Inventory+updated", status_code=303)
