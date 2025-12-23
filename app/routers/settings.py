"""User settings routes"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, File, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileUpdate
from app.services import upload_service, auth_service

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")


def get_template_context(request: Request, user: User):
    """Get base template context"""
    root_path = settings.ROOT_PATH or ""
    base_url = f"{request.url.scheme}://{request.url.netloc}{root_path}"
    return {
        "request": request,
        "app_name": settings.APP_NAME,
        "auth_enabled": settings.AUTH_ENABLED,
        "user": user,
        "root_path": root_path,
        "current_url": str(request.url),
        "base_url": base_url
    }


def make_redirect(url: str, status_code: int = status.HTTP_303_SEE_OTHER) -> RedirectResponse:
    """Create RedirectResponse with ROOT_PATH prefix if needed"""
    root_path = settings.ROOT_PATH or ""
    if not root_path:
        return RedirectResponse(url=url, status_code=status_code)
    
    # Если URL уже содержит ROOT_PATH, убираем его перед добавлением
    if url.startswith(root_path):
        url = url[len(root_path):]
    
    # Добавляем ROOT_PATH к относительным путям
    if url.startswith("/"):
        url = f"{root_path}{url}"
    elif not url.startswith(("http://", "https://", "//")):
        # Если это не абсолютный URL и не начинается с /, добавляем ROOT_PATH
        url = f"{root_path}/{url}"
    
    return RedirectResponse(url=url, status_code=status_code)


@router.get("", response_class=HTMLResponse)
def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User settings page"""
    # Get or create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    context = get_template_context(request, current_user)
    context["profile"] = profile
    return templates.TemplateResponse("settings.html", context)


@router.post("")
async def update_settings(
    request: Request,
    display_name: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings"""
    # Get or create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    # Update fields
    if display_name is not None:
        profile.display_name = display_name
    if bio is not None:
        profile.bio = bio
    if website is not None:
        profile.website = website
    if location is not None:
        profile.location = location
    
    db.commit()
    
    return make_redirect("/settings?success=1")


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload user avatar"""
    # Get or create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()
    
    # Delete old avatar if exists
    if profile.avatar_url:
        upload_service.delete_file(profile.avatar_url)
    
    # Save new avatar
    avatar_url = await upload_service.save_avatar(file, current_user.id)
    profile.avatar_url = avatar_url
    
    db.commit()
    
    return make_redirect("/settings?avatar=1")


@router.get("/security", response_class=HTMLResponse)
def security_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Security settings page"""
    context = get_template_context(request, current_user)
    return templates.TemplateResponse("settings_security.html", context)


@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not auth_service.verify_password(current_password, current_user.hashed_password):
        context = get_template_context(request, current_user)
        context["error"] = "Неверный текущий пароль"
        return templates.TemplateResponse("settings_security.html", context, status_code=400)
    
    # Check if new passwords match
    if new_password != confirm_password:
        context = get_template_context(request, current_user)
        context["error"] = "Новые пароли не совпадают"
        return templates.TemplateResponse("settings_security.html", context, status_code=400)
    
    # Validate password strength (minimum 6 characters)
    if len(new_password) < 6:
        context = get_template_context(request, current_user)
        context["error"] = "Пароль должен содержать минимум 6 символов"
        return templates.TemplateResponse("settings_security.html", context, status_code=400)
    
    # Update password
    current_user.hashed_password = auth_service.get_password_hash(new_password)
    db.commit()
    
    return make_redirect("/settings/security?success=1")
















