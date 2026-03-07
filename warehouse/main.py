from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import init_db, get_db, SessionLocal
from auth import NotAuthenticated, NotAuthorized
import models

from routers import auth, aisles, racks, levels, bins, items, inventory, pick, users, search, structure

app = FastAPI(title="Warehouse Management System")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(NotAuthenticated)
async def not_authenticated(_request: Request, _exc: NotAuthenticated):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(NotAuthorized)
async def not_authorized(_request: Request, _exc: NotAuthorized):
    return RedirectResponse("/dashboard?error=You+do+not+have+permission+for+that", status_code=303)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(aisles.router)
app.include_router(racks.router)
app.include_router(levels.router)
app.include_router(bins.router)
app.include_router(items.router)
app.include_router(inventory.router)
app.include_router(pick.router)
app.include_router(users.router)
app.include_router(search.router)
app.include_router(structure.router)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    error: str = "",
    msg: str = "",
):
    from auth import require_user, NotAuthenticated
    token = request.cookies.get("access_token")
    if not token:
        raise NotAuthenticated()
    from auth import decode_token
    payload = decode_token(token)
    if not payload:
        raise NotAuthenticated()

    db: Session = SessionLocal()
    try:
        user = db.get(models.User, int(payload["sub"]))
        if not user:
            raise NotAuthenticated()

        total_aisles = db.query(models.Aisle).count()
        total_racks = db.query(models.Rack).count()
        total_bins = db.query(models.Bin).count()
        total_items = db.query(models.Item).count()

        # Overall capacity
        all_bins = db.query(models.Bin).all()
        if all_bins:
            total_vol = sum(b.volume_cm3 for b in all_bins)
            used_vol = sum(b.used_volume_cm3 for b in all_bins)
            capacity_pct = int(used_vol / total_vol * 100) if total_vol else 0
        else:
            capacity_pct = 0

        recent_sessions = (
            db.query(models.PickSession)
            .order_by(models.PickSession.created_at.desc())
            .limit(5)
            .all()
        )

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "total_aisles": total_aisles,
                "total_racks": total_racks,
                "total_bins": total_bins,
                "total_items": total_items,
                "capacity_pct": capacity_pct,
                "recent_sessions": recent_sessions,
                "error": error,
                "msg": msg,
            },
        )
    finally:
        db.close()


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
