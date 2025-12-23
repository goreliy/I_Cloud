"""Web interface routes"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Response, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.config import settings
from app.dependencies import get_current_user_optional
from app.models.user import User
from app.services import channel_service, auth_service, widget_version_service
from app.schemas.channel import ChannelCreate, ChannelUpdate
from app.schemas.user import UserCreate

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def get_template_context(request: Request, user: Optional[User] = None):
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


def require_auth(current_user: Optional[User], request: Request):
    """Check if user is authenticated when auth is enabled"""
    if settings.AUTH_ENABLED and not current_user:
        # Redirect to login with next parameter
        root_path = settings.ROOT_PATH or ""
        next_path = request.url.path
        # Убираем ROOT_PATH из next_path, если он там есть
        if root_path and next_path.startswith(root_path):
            next_path = next_path[len(root_path):]
        return make_redirect(f"/login?next={next_path}")
    return None


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Home page"""
    context = get_template_context(request, current_user)
    return templates.TemplateResponse("index.html", context)


@router.get("/channels", response_class=HTMLResponse)
def channels_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Channels list page"""
    channels = channel_service.get_channels(db, current_user)
    context = get_template_context(request, current_user)
    context["channels"] = channels
    return templates.TemplateResponse("channels.html", context)


@router.get("/channels/create", response_class=HTMLResponse)
def create_channel_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Create channel page"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    context = get_template_context(request, current_user)
    context["channel"] = None
    return templates.TemplateResponse("channel_form.html", context)


@router.post("/channels/create")
async def create_channel_submit(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    timezone: str = Form("UTC"),
    public: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Create channel form submission"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    # Convert checkbox value to boolean
    is_public = public == "on" if public else False
    
    channel_create = ChannelCreate(
        name=name,
        description=description or "",
        timezone=timezone,
        public=is_public
    )
    
    channel = channel_service.create_channel(db, channel_create, current_user)
    return make_redirect(f"/channels/{channel.id}")


@router.get("/channels/{channel_id}", response_class=HTMLResponse)
def channel_detail_page(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Channel detail page"""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get API keys if user is owner
    api_keys = []
    write_key = None
    read_key = None
    if not settings.AUTH_ENABLED or (current_user and channel.user_id == current_user.id):
        api_keys = channel_service.get_channel_api_keys(db, channel_id)
        # Find write and read keys
        for key in api_keys:
            if key.is_active:
                if key.type == "write" and not write_key:
                    write_key = key
                elif key.type == "read" and not read_key:
                    read_key = key
    
    # Get widgets
    from app.models.custom_widget import CustomWidget
    import json
    widgets = db.query(CustomWidget).filter(
        CustomWidget.channel_id == channel_id,
        CustomWidget.is_active == True
    ).order_by(CustomWidget.position).all()
    
    widgets_json = json.dumps([
        {
            "id": w.id,
            "name": w.name,
            "svg_file_url": w.svg_file_url,
            "svg_bindings": w.svg_bindings,
            "width": w.width,
            "height": w.height
        }
        for w in widgets
    ])
    
    # Build base URL with ROOT_PATH
    root_path = settings.ROOT_PATH or ""
    base_url = f"{request.url.scheme}://{request.url.hostname}"
    # Add port only if it's not standard (80 for http, 443 for https) and not None
    if request.url.port and request.url.port not in (80, 443):
        base_url += f":{request.url.port}"
    base_url += root_path
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    context["api_keys"] = api_keys
    context["write_key"] = write_key.key if write_key else None
    context["read_key"] = read_key.key if read_key else None
    context["base_url"] = base_url
    context["widgets"] = widgets
    context["widgets_json"] = widgets_json
    return templates.TemplateResponse("channel_detail.html", context)


@router.get("/channels/{channel_id}/edit", response_class=HTMLResponse)
def edit_channel_page(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Edit channel page"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can edit")
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    return templates.TemplateResponse("channel_form.html", context)


@router.post("/channels/{channel_id}/edit")
async def edit_channel_submit(
    channel_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    timezone: str = Form("UTC"),
    public: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Edit channel form submission"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can edit")
    
    # Convert checkbox value to boolean
    is_public = public == "on" if public else False
    
    channel_update = ChannelUpdate(
        name=name,
        description=description,
        timezone=timezone,
        public=is_public
    )
    
    channel_service.update_channel(db, channel, channel_update)
    return make_redirect(f"/channels/{channel_id}")


@router.post("/channels/{channel_id}/delete")
async def delete_channel_submit(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Delete channel"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can delete")
    
    channel_service.delete_channel(db, channel)
    return make_redirect("/channels")


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: Optional[str] = None
):
    """Login page"""
    if not settings.AUTH_ENABLED:
        return make_redirect("/")
    
    context = get_template_context(request)
    context["next"] = next
    return templates.TemplateResponse("login.html", context)


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: Optional[str] = None,
):
    """Password reset page by token"""
    if not settings.AUTH_ENABLED:
        return make_redirect("/")
    context = get_template_context(request)
    context["token"] = token
    return templates.TemplateResponse("reset_password.html", context)


@router.post("/reset-password")
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle password reset submission"""
    if not settings.AUTH_ENABLED:
        return make_redirect("/")
    
    # Validate passwords
    if new_password != confirm_password:
        context = get_template_context(request)
        context["token"] = token
        context["error"] = "Пароли не совпадают"
        return templates.TemplateResponse("reset_password.html", context, status_code=400)
    if len(new_password) < 6:
        context = get_template_context(request)
        context["token"] = token
        context["error"] = "Пароль должен содержать минимум 6 символов"
        return templates.TemplateResponse("reset_password.html", context, status_code=400)
    
    user_id = auth_service.verify_password_reset_token(token)
    if not user_id:
        context = get_template_context(request)
        context["error"] = "Недействительная или истекшая ссылка"
        return templates.TemplateResponse("reset_password.html", context, status_code=400)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        context = get_template_context(request)
        context["error"] = "Пользователь не найден"
        return templates.TemplateResponse("reset_password.html", context, status_code=404)
    
    user.hashed_password = auth_service.get_password_hash(new_password)
    db.commit()
    
    return make_redirect("/login?reset=success")

@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Login form submission"""
    if not settings.AUTH_ENABLED:
        return make_redirect("/")
    
    user = auth_service.authenticate_user(db, email, password)
    if not user:
        context = get_template_context(request)
        context["error"] = "Неверный email или пароль"
        return templates.TemplateResponse("login.html", context, status_code=400)
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create JWT token with expiration
    token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=token_expires
    )
    
    # Redirect to next page or default to channels
    redirect_url = next if next else "/channels"
    response = make_redirect(redirect_url)
    
    # Set cookie with proper settings
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Register page"""
    if not settings.AUTH_ENABLED:
        return make_redirect("/")
    
    context = get_template_context(request)
    return templates.TemplateResponse("register.html", context)


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    """Register form submission"""
    if not settings.AUTH_ENABLED:
        return make_redirect("/")
    
    context = get_template_context(request)
    
    # Validate passwords match
    if password != password_confirm:
        context["error"] = "Пароли не совпадают"
        return templates.TemplateResponse("register.html", context)
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        context["error"] = "Email уже зарегистрирован"
        return templates.TemplateResponse("register.html", context)
    
    # Create user
    user_create = UserCreate(email=email, password=password)
    auth_service.create_user(db, user_create)
    
    return make_redirect("/login")


@router.get("/logout")
def logout():
    """Logout"""
    response = make_redirect("/")
    response.delete_cookie(key="access_token")
    return response


# ========== ADMIN WEB PAGES ==========

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Admin dashboard page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    context = get_template_context(request, current_user)
    return templates.TemplateResponse("admin/dashboard.html", context)


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Admin users management page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    context = get_template_context(request, current_user)
    return templates.TemplateResponse("admin/users.html", context)


@router.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
def admin_user_edit_page(
    user_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Admin user edit page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from app.models.user_profile import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    context = get_template_context(request, current_user)
    context["edit_user"] = user
    context["edit_profile"] = profile
    return templates.TemplateResponse("admin/user_edit.html", context)


@router.get("/admin/channels", response_class=HTMLResponse)
def admin_channels_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Admin channels management page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    context = get_template_context(request, current_user)
    return templates.TemplateResponse("admin/channels.html", context)


@router.get("/admin/channels/{channel_id}/stats", response_class=HTMLResponse)
def admin_channel_stats_page(
    channel_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Admin channel statistics page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.models.channel import Channel
    from app.services import channel_stats
    
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    stats = channel_stats.calculate_channel_stats(channel_id, db)
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    context["stats"] = stats
    return templates.TemplateResponse("admin/channel_stats.html", context)


@router.get("/admin/requests", response_class=HTMLResponse)
def admin_requests_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Admin API requests monitoring page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    context = get_template_context(request, current_user)
    return templates.TemplateResponse("admin/api_requests.html", context)


@router.get("/admin/stress-test", response_class=HTMLResponse)
def admin_stress_test_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Admin stress test page"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.models.channel import Channel
    channels = db.query(Channel).all()
    
    context = get_template_context(request, current_user)
    context['channels'] = channels
    context['max_workers'] = settings.STRESS_TEST_MAX_WORKERS
    context['max_rps'] = settings.STRESS_TEST_MAX_RPS
    context['max_duration'] = settings.STRESS_TEST_MAX_DURATION
    context['server_workers'] = settings.WORKERS
    
    return templates.TemplateResponse("admin/stress_test.html", context)


@router.get("/admin/archive", response_class=HTMLResponse)
def admin_archive_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    context = get_template_context(request, current_user)
    return templates.TemplateResponse("admin/archive.html", context)


@router.get("/admin/ai-services", response_class=HTMLResponse)
def admin_ai_services_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Admin page for AI services management"""
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    context = get_template_context(request, current_user)
    return templates.TemplateResponse("admin/ai_services.html", context)


# ========== CHANNEL SETTINGS ==========

@router.get("/channels/{channel_id}/settings", response_class=HTMLResponse)
def channel_settings_page(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Channel settings page"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can access settings")
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    return templates.TemplateResponse("channel_settings.html", context)


@router.post("/channels/{channel_id}/settings")
async def update_channel_settings(
    channel_id: int,
    request: Request,
    color_scheme: str = Form("light"),
    custom_css: Optional[str] = Form(None),
    field1_label: Optional[str] = Form(None),
    field2_label: Optional[str] = Form(None),
    field3_label: Optional[str] = Form(None),
    field4_label: Optional[str] = Form(None),
    field5_label: Optional[str] = Form(None),
    field6_label: Optional[str] = Form(None),
    field7_label: Optional[str] = Form(None),
    field8_label: Optional[str] = Form(None),
    field1_visible: Optional[str] = Form(None),
    field2_visible: Optional[str] = Form(None),
    field3_visible: Optional[str] = Form(None),
    field4_visible: Optional[str] = Form(None),
    field5_visible: Optional[str] = Form(None),
    field6_visible: Optional[str] = Form(None),
    field7_visible: Optional[str] = Form(None),
    field8_visible: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Update channel settings"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can update settings")
    
    # Update channel
    channel.color_scheme = color_scheme
    channel.custom_css = custom_css
    channel.field1_label = field1_label
    channel.field2_label = field2_label
    channel.field3_label = field3_label
    channel.field4_label = field4_label
    channel.field5_label = field5_label
    channel.field6_label = field6_label
    channel.field7_label = field7_label
    channel.field8_label = field8_label
    
    # Update visibility (checkbox returns "on" if checked, None if unchecked)
    channel.field1_visible = field1_visible == "on"
    channel.field2_visible = field2_visible == "on"
    channel.field3_visible = field3_visible == "on"
    channel.field4_visible = field4_visible == "on"
    channel.field5_visible = field5_visible == "on"
    channel.field6_visible = field6_visible == "on"
    channel.field7_visible = field7_visible == "on"
    channel.field8_visible = field8_visible == "on"
    
    db.commit()
    
    return make_redirect(f"/channels/{channel_id}/settings?success=1")


# ========== CHANNEL WIDGETS ==========

@router.get("/channels/{channel_id}/widgets", response_class=HTMLResponse)
def channel_widgets_page(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Channel widgets management page"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can manage widgets")
    
    # Get widgets
    from app.models.custom_widget import CustomWidget
    widgets = db.query(CustomWidget).filter(
        CustomWidget.channel_id == channel_id
    ).order_by(CustomWidget.position).all()
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    context["widgets"] = widgets
    return templates.TemplateResponse("channel_widgets.html", context)


@router.get("/channels/{channel_id}/widgets/{widget_id}/edit", response_class=HTMLResponse)
def edit_widget_page(
    channel_id: int,
    widget_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Edit widget page"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can edit widgets")
    
    # Get widget
    from app.models.custom_widget import CustomWidget
    widget = db.query(CustomWidget).filter(
        CustomWidget.id == widget_id,
        CustomWidget.channel_id == channel_id
    ).first()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    context["widget"] = widget
    return templates.TemplateResponse("widget_edit.html", context)


@router.post("/channels/{channel_id}/widgets/{widget_id}/edit")
async def update_widget_submit(
    channel_id: int,
    widget_id: int,
    request: Request,
    name: str = Form(...),
    width: int = Form(6),
    height: int = Form(300),
    svg_bindings: Optional[str] = Form(None),
    html_code: Optional[str] = Form(None),
    css_code: Optional[str] = Form(None),
    js_code: Optional[str] = Form(None),
    version_comment: Optional[str] = Form(None),
    ai_service_id: Optional[int] = Form(None),
    prompt_used: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Update widget submission"""
    from app.models.custom_widget import CustomWidget
    from app.services import upload_service
    
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get widget
    widget = db.query(CustomWidget).filter(
        CustomWidget.id == widget_id,
        CustomWidget.channel_id == channel_id
    ).first()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    # Update basic fields
    widget.name = name
    widget.width = width
    widget.height = height
    
    # Update type-specific fields
    if widget.widget_type == 'svg':
        widget.svg_bindings = svg_bindings
        
        # Replace SVG file if uploaded
        if file and file.filename:
            # Delete old SVG
            if widget.svg_file_url:
                upload_service.delete_file(widget.svg_file_url)
            
            # Save new SVG
            svg_url = await upload_service.save_svg_file(file, channel_id)
            widget.svg_file_url = svg_url
    
    elif widget.widget_type == 'html':
        widget.html_code = html_code
        widget.css_code = css_code
        widget.js_code = js_code
    
    db.commit()
    db.refresh(widget)

    if widget.widget_type == 'html':
        widget_version_service.create_version(
            db,
            widget,
            ai_service_id=ai_service_id,
            prompt_used=prompt_used,
            comment=version_comment or "Manual edit",
            created_by=current_user.id if current_user else None,
        )
    
    return make_redirect(f"/channels/{channel_id}/widgets?updated=1")


# ========== CHANNEL AUTOMATION ==========

@router.get("/channels/{channel_id}/automation", response_class=HTMLResponse)
def channel_automation_page(
    channel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Channel automation rules management page"""
    # Check authentication
    redirect = require_auth(current_user, request)
    if redirect:
        return redirect
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can manage automation")
    
    # Get rules
    from app.models.automation_rule import AutomationRule
    rules = db.query(AutomationRule).filter(
        AutomationRule.channel_id == channel_id
    ).order_by(AutomationRule.priority.asc()).all()
    
    context = get_template_context(request, current_user)
    context["channel"] = channel
    context["rules"] = rules
    return templates.TemplateResponse("channel_automation.html", context)

