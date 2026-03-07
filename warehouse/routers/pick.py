from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
import picking as pick_algo
from auth import require_user
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── New session (draft basket) ────────────────────────────────────────────────

@router.get("/pick/new", response_class=HTMLResponse)
def new_pick_start(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    """Create a draft session and redirect to the basket builder."""
    session = models.PickSession(operator_id=user.id, status="draft")
    db.add(session)
    db.commit()
    db.refresh(session)
    return RedirectResponse(f"/pick/{session.id}/build", status_code=303)


# ── Basket builder ────────────────────────────────────────────────────────────

@router.get("/pick/{session_id}/build", response_class=HTMLResponse)
def basket_builder(
    session_id: int,
    request: Request,
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    session = db.get(models.PickSession, session_id)
    if not session or session.status != "draft":
        return RedirectResponse("/pick/history?error=Session+not+found+or+not+a+draft", status_code=303)
    items = db.query(models.Item).order_by(models.Item.name).all()
    return templates.TemplateResponse(
        "pick_new.html",
        {"request": request, "session": session, "items": items, "user": user, "error": error},
    )


@router.post("/pick/{session_id}/basket/add")
def basket_add(
    session_id: int,
    request: Request,
    item_id: int = Form(...),
    quantity: int = Form(1),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    session = db.get(models.PickSession, session_id)
    if not session or session.status != "draft":
        return RedirectResponse("/pick/history", status_code=303)

    existing = (
        db.query(models.PickItem)
        .filter(models.PickItem.session_id == session_id, models.PickItem.item_id == item_id)
        .first()
    )
    if existing:
        existing.quantity_requested += quantity
    else:
        db.add(models.PickItem(session_id=session_id, item_id=item_id,
                               quantity_requested=quantity))
    db.commit()

    # Refresh and return updated basket partial for HTMX
    db.refresh(session)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/basket_list.html",
            {"request": request, "session": session, "user": user},
        )
    return RedirectResponse(f"/pick/{session_id}/build", status_code=303)


@router.post("/pick/{session_id}/basket/remove/{item_id}")
def basket_remove(
    session_id: int,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    pi = (
        db.query(models.PickItem)
        .filter(models.PickItem.session_id == session_id, models.PickItem.item_id == item_id)
        .first()
    )
    if pi:
        db.delete(pi)
        db.commit()

    session = db.get(models.PickSession, session_id)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/basket_list.html",
            {"request": request, "session": session, "user": user},
        )
    return RedirectResponse(f"/pick/{session_id}/build", status_code=303)


# ── Route generation ──────────────────────────────────────────────────────────

@router.post("/pick/{session_id}/generate")
def generate_route(
    session_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    session = db.get(models.PickSession, session_id)
    if not session or session.status != "draft":
        return RedirectResponse("/pick/history?error=Invalid+session", status_code=303)
    if not session.pick_items:
        return RedirectResponse(f"/pick/{session_id}/build?error=Basket+is+empty", status_code=303)

    # Assign bins using nearest-aisle greedy selection
    assignments = pick_algo.assign_bins(session.pick_items, db)
    if not assignments:
        return RedirectResponse(
            f"/pick/{session_id}/build?error=No+stock+found+for+requested+items",
            status_code=303,
        )

    # Create unsorted stops
    unsorted = []
    for idx, (bin_, pi) in enumerate(assignments):
        stop = models.PickStop(
            session_id=session_id,
            bin_id=bin_.id,
            item_id=pi.item_id,
            quantity=pi.quantity_requested,
            order_index=idx,
            picked=False,
        )
        db.add(stop)
        unsorted.append(stop)
    db.flush()

    # Sort by S-shape and update order_index
    sorted_stops = pick_algo.compute_route(unsorted)
    for idx, stop in enumerate(sorted_stops):
        stop.order_index = idx

    session.status = "open"
    db.commit()
    return RedirectResponse(f"/pick/{session_id}", status_code=303)


# ── Active pick session ───────────────────────────────────────────────────────

@router.get("/pick/{session_id}", response_class=HTMLResponse)
def pick_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    session = db.get(models.PickSession, session_id)
    if not session:
        return RedirectResponse("/pick/history?error=Session+not+found", status_code=303)
    total = len(session.stops)
    picked = sum(1 for s in session.stops if s.picked)
    return templates.TemplateResponse(
        "pick_session.html",
        {
            "request": request,
            "session": session,
            "user": user,
            "total": total,
            "picked": picked,
            "pct": int(picked / total * 100) if total else 0,
        },
    )


@router.post("/pick/{session_id}/stop/{stop_id}/check")
def check_stop(
    session_id: int,
    stop_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    stop = db.get(models.PickStop, stop_id)
    if not stop or stop.session_id != session_id:
        return RedirectResponse(f"/pick/{session_id}", status_code=303)

    if not stop.picked:
        stop.picked = True
        # Decrement inventory
        bi = (
            db.query(models.BinItem)
            .filter(
                models.BinItem.bin_id == stop.bin_id,
                models.BinItem.item_id == stop.item_id,
            )
            .first()
        )
        if bi:
            if bi.quantity <= stop.quantity:
                db.delete(bi)
            else:
                bi.quantity -= stop.quantity
        db.commit()

    # Check if all stops are done
    session = db.get(models.PickSession, session_id)
    all_done = all(s.picked for s in session.stops)
    if all_done and session.status == "open":
        session.status = "completed"
        db.commit()

    total = len(session.stops)
    picked = sum(1 for s in session.stops if s.picked)
    pct = int(picked / total * 100) if total else 0

    if request.headers.get("HX-Request"):
        stop_html = templates.TemplateResponse(
            "partials/pick_stop.html",
            {"request": request, "stop": stop, "session_id": session_id},
        )
        progress_html = templates.TemplateResponse(
            "partials/pick_progress.html",
            {"request": request, "picked": picked, "total": total, "pct": pct,
             "completed": all_done},
        )
        # Return both fragments using HTMX out-of-band swap for progress
        from fastapi.responses import HTMLResponse as HR
        stop_content = stop_html.body.decode() if hasattr(stop_html, 'body') else ""
        progress_content = progress_html.body.decode() if hasattr(progress_html, 'body') else ""

        # Use a simple approach: return combined HTML with OOB swap
        combined = f"""
<tr id="stop-{stop.id}" class="{'bg-green-50' if stop.picked else ''}">
  <td class="px-4 py-3 text-sm font-mono text-slate-600">{stop.order_index + 1}</td>
  <td class="px-4 py-3">
    <span class="font-mono text-sm font-semibold text-blue-700">{stop.bin.location_code}</span>
  </td>
  <td class="px-4 py-3">
    <div class="font-medium text-slate-800">{stop.item.name}</div>
    <div class="text-xs text-slate-500">{stop.item.sku}</div>
  </td>
  <td class="px-4 py-3 text-center font-semibold">{stop.quantity}</td>
  <td class="px-4 py-3 text-center">
    {'<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">Picked</span>' if stop.picked else ''}
  </td>
</tr>
<div id="progress-bar" hx-swap-oob="true">
  <div class="flex justify-between text-sm mb-1">
    <span class="font-medium text-slate-700">Progress</span>
    <span class="text-slate-500">{picked}/{total} stops</span>
  </div>
  <div class="w-full bg-slate-200 rounded-full h-4">
    <div class="{'bg-green-500' if pct == 100 else 'bg-blue-500'} h-4 rounded-full transition-all duration-300" style="width:{pct}%"></div>
  </div>
  {'<p class="mt-2 text-green-700 font-semibold text-center">All done! Pick session completed.</p>' if all_done else ''}
</div>
"""
        return HTMLResponse(content=combined)

    return RedirectResponse(f"/pick/{session_id}", status_code=303)


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/pick/history", response_class=HTMLResponse)
def pick_history(
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    sessions = (
        db.query(models.PickSession)
        .order_by(models.PickSession.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "pick_history.html",
        {"request": request, "sessions": sessions, "user": user, "msg": msg, "error": error},
    )
