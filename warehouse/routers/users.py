from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth import require_admin, hash_password
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/users", response_class=HTMLResponse)
def list_users(
    request: Request,
    msg: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    users = db.query(models.User).order_by(models.User.username).all()
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "users": users, "user": user, "msg": msg, "error": error},
    )


@router.post("/users")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("operator"),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    username = username.strip()
    if role not in ("admin", "operator"):
        return RedirectResponse("/users?error=Invalid+role", status_code=303)
    if db.query(models.User).filter(models.User.username == username).first():
        return RedirectResponse(f"/users?error=Username+{username}+already+exists", status_code=303)
    db.add(models.User(username=username, password_hash=hash_password(password), role=role))
    db.commit()
    return RedirectResponse(f"/users?msg=User+{username}+created", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    if user_id == admin.id:
        return RedirectResponse("/users?error=Cannot+delete+your+own+account", status_code=303)
    user = db.get(models.User, user_id)
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse("/users?msg=User+deleted", status_code=303)
