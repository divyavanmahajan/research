from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_user
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/structure", response_class=HTMLResponse)
def structure_page(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    aisles = db.query(models.Aisle).order_by(models.Aisle.code).all()
    return templates.TemplateResponse(
        "structure.html", {"request": request, "aisles": aisles, "user": user}
    )


@router.get("/structure/aisles/{aisle_id}/racks", response_class=HTMLResponse)
def aisle_racks_partial(
    aisle_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    aisle = db.get(models.Aisle, aisle_id)
    if not aisle:
        return HTMLResponse("<tr><td colspan='5' class='text-red-500 px-4 py-2'>Aisle not found</td></tr>")
    racks = (
        db.query(models.Rack)
        .filter(models.Rack.aisle_id == aisle_id)
        .order_by(models.Rack.code)
        .all()
    )
    return templates.TemplateResponse(
        "partials/rack_row.html",
        {"request": request, "racks": racks, "aisle": aisle, "user": user},
    )
