from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_user, require_admin
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/aisles/{aisle_id}/racks", response_class=HTMLResponse)
def list_racks(
    aisle_id: int,
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    aisle = db.get(models.Aisle, aisle_id)
    if not aisle:
        return RedirectResponse("/structure?error=Aisle+not+found", status_code=303)
    racks = (
        db.query(models.Rack)
        .filter(models.Rack.aisle_id == aisle_id)
        .order_by(models.Rack.code)
        .all()
    )
    # HTMX partial or full page
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/rack_row.html",
            {"request": request, "racks": racks, "aisle": aisle, "user": user},
        )
    return templates.TemplateResponse(
        "racks.html",
        {"request": request, "aisle": aisle, "racks": racks, "user": user,
         "msg": msg, "error": error},
    )


@router.post("/aisles/{aisle_id}/racks")
def create_rack(
    aisle_id: int,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    aisle = db.get(models.Aisle, aisle_id)
    if not aisle:
        return RedirectResponse("/structure?error=Aisle+not+found", status_code=303)
    code = code.strip().upper()
    existing = (
        db.query(models.Rack)
        .filter(models.Rack.aisle_id == aisle_id, models.Rack.code == code)
        .first()
    )
    if existing:
        return RedirectResponse(
            f"/aisles/{aisle_id}/racks?error=Rack+{code}+already+exists+in+this+aisle",
            status_code=303,
        )
    db.add(models.Rack(aisle_id=aisle_id, code=code, name=name.strip()))
    db.commit()
    return RedirectResponse(f"/aisles/{aisle_id}/racks?msg=Rack+{code}+created", status_code=303)


@router.post("/racks/{rack_id}/delete")
def delete_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    rack = db.get(models.Rack, rack_id)
    aisle_id = rack.aisle_id if rack else None
    if rack:
        db.delete(rack)
        db.commit()
    redirect = f"/aisles/{aisle_id}/racks?msg=Rack+deleted" if aisle_id else "/structure"
    return RedirectResponse(redirect, status_code=303)
