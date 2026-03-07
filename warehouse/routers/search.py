from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from auth import require_user
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    return templates.TemplateResponse(
        "search.html", {"request": request, "user": user, "results": [], "query": ""}
    )


@router.get("/search/results", response_class=HTMLResponse)
def search_results(
    request: Request,
    q: str = Query(""),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    q = q.strip()
    if not q:
        items = []
    else:
        items = (
            db.query(models.Item)
            .filter(
                or_(
                    models.Item.name.ilike(f"%{q}%"),
                    models.Item.sku.ilike(f"%{q}%"),
                    models.Item.description.ilike(f"%{q}%"),
                )
            )
            .order_by(models.Item.name)
            .all()
        )

    # Build result rows: item + all bin locations
    results = []
    for item in items:
        locations = []
        for bi in item.bin_items:
            locations.append({
                "location_code": bi.bin.location_code,
                "bin_id": bi.bin_id,
                "quantity": bi.quantity,
            })
        results.append({"item": item, "locations": locations})

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/search_results.html",
            {"request": request, "results": results, "query": q, "user": user},
        )
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "results": results, "query": q, "user": user},
    )
