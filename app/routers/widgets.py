"""Custom widgets API и вспомогательные endpoints для ИИ."""
from __future__ import annotations

from typing import List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user_optional
from app.models.ai_service import AIService, AIServicePromptOverride, AIScope
from app.models.custom_widget import CustomWidget
from app.models.user import User
from app.schemas.ai_service import (
    AIServiceCreate,
    AIServicePromptOverrideResponse,
    AIServicePromptOverrideScopedCreate,
    AIServiceResponse,
    AIServiceUpdate,
)
from app.schemas.custom_widget import CustomWidgetResponse, CustomWidgetUpdate
from app.schemas.widget_version import WidgetVersionResponse
from app.services import (
    ai_widget_service,
    channel_service,
    upload_service,
    widget_version_service,
)


router = APIRouter(prefix="/api/channels", tags=["widgets"])
ai_router = APIRouter(prefix="/api/ai-services", tags=["ai-services"])


class RefinePromptPayload(BaseModel):
    service_alias: str
    original_prompt: str
    previous_response: str
    feedback: str


@router.post("/{channel_id}/widgets", response_model=CustomWidgetResponse, status_code=status.HTTP_201_CREATED)
async def create_widget(
    channel_id: int,
    name: str = Form(...),
    widget_type: str = Form("svg"),
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
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Создать новый виджет."""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Only channel owner can create widgets")

    svg_url = None
    if file and widget_type == "svg":
        svg_url = await upload_service.save_svg_file(file, channel_id)

    widget = CustomWidget(
        channel_id=channel_id,
        name=name,
        widget_type=widget_type,
        svg_file_url=svg_url,
        svg_bindings=svg_bindings,
        html_code=html_code,
        css_code=css_code,
        js_code=js_code,
        width=width,
        height=height,
        position=db.query(CustomWidget).filter(CustomWidget.channel_id == channel_id).count(),
    )

    db.add(widget)
    db.commit()
    db.refresh(widget)

    # Сохраняем первую версию для HTML/JS виджетов
    if widget.widget_type == "html" or any([html_code, css_code, js_code]):
        widget_version_service.create_version(
            db,
            widget,
            ai_service_id=ai_service_id,
            prompt_used=prompt_used,
            comment=version_comment or "Initial version",
            created_by=current_user.id if current_user else None,
        )

    return widget


@router.get("/{channel_id}/widgets", response_model=List[CustomWidgetResponse])
def list_widgets(
    channel_id: int,
    db: Session = Depends(get_db),
):
    """Получить активные виджеты канала."""
    widgets = (
        db.query(CustomWidget)
        .filter(CustomWidget.channel_id == channel_id, CustomWidget.is_active == True)
        .order_by(CustomWidget.position)
        .all()
    )
    return widgets


@router.put("/{channel_id}/widgets/{widget_id}", response_model=CustomWidgetResponse)
async def update_widget(
    channel_id: int,
    widget_id: int,
    widget_update: CustomWidgetUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Обновить параметры виджета."""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    update_data = widget_update.dict(exclude_unset=True)
    version_comment = update_data.pop("version_comment", None)
    ai_service_id = update_data.pop("ai_service_id", None)
    prompt_used = update_data.pop("prompt_used", None)

    for field, value in update_data.items():
        setattr(widget, field, value)

    db.commit()
    db.refresh(widget)

    changed_fields = set(update_data.keys())
    if widget.widget_type == "html" and (
        changed_fields.intersection({"html_code", "css_code", "js_code"})
        or version_comment
        or prompt_used
    ):
        widget_version_service.create_version(
            db,
            widget,
            ai_service_id=ai_service_id,
            prompt_used=prompt_used,
            comment=version_comment or "Auto snapshot",
            created_by=current_user.id if current_user else None,
        )

    return widget


@router.delete("/{channel_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    channel_id: int,
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Удалить виджет."""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    if widget.svg_file_url:
        upload_service.delete_file(widget.svg_file_url)

    db.delete(widget)
    db.commit()


@router.get("/{channel_id}/widgets/prompt")
def generate_prompt(
    channel_id: int,
    request: Request,
    service_alias: str,
    widget_id: Optional[int] = None,
    user_request: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Сформировать предпромпт для генерации виджета."""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget: Optional[CustomWidget] = None
    if widget_id:
        widget = (
            db.query(CustomWidget)
            .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
            .first()
        )
        if not widget:
            raise HTTPException(status_code=404, detail="Widget not found")

    service = ai_widget_service.get_service_by_alias(db, service_alias)
    if not service or not service.is_enabled:
        raise HTTPException(status_code=404, detail="AI service not found")

    base_url = f"{request.url.scheme}://{request.url.netloc}"
    prompt_bundle = ai_widget_service.build_prompt(db, service, channel, base_url, widget=widget)

    # Собрать full_prompt (единый текст) для удобной вставки в чат
    user_part = ("\n\nПользовательское задание:\n" + user_request) if user_request else ""
    full_prompt = (
        prompt_bundle.common
        + user_part
        + "\n\nТребования к разделам ответа (разделите кодовые блоки):\n"
        + "HTML:\n" + prompt_bundle.html + "\n\n"
        + "CSS:\n" + prompt_bundle.css + "\n\n"
        + "JS:\n" + prompt_bundle.js
    )

    return {
        "service": service_alias,
        "prompt": {
            "common": prompt_bundle.common,
            "html": prompt_bundle.html,
            "css": prompt_bundle.css,
            "js": prompt_bundle.js,
            "refine": prompt_bundle.refine,
        },
        "context": prompt_bundle.context,
        "full_prompt": full_prompt,
    }


@router.post("/{channel_id}/widgets/{widget_id}/prompt/refine")
def refine_prompt(
    channel_id: int,
    widget_id: int,
    payload: RefinePromptPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Сформировать уточняющий промпт на основе предыдущего ответа ИИ."""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    service = ai_widget_service.get_service_by_alias(db, payload.service_alias)
    if not service or not service.is_enabled:
        raise HTTPException(status_code=404, detail="AI service not found")

    templates = ai_widget_service.get_prompt_templates(db, service, channel, widget)

    refine_prompt_text = ai_widget_service.build_refine_prompt(
        service,
        original_prompt=payload.original_prompt,
        previous_response=payload.previous_response,
        feedback=payload.feedback,
        templates=templates,
    )

    return {"prompt": refine_prompt_text}


@router.get("/{channel_id}/widgets/{widget_id}/versions", response_model=List[WidgetVersionResponse])
def list_widget_versions(
    channel_id: int,
    widget_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Получить историю версий виджета."""
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    versions = widget_version_service.list_versions(db, widget.id, limit=limit)
    return versions


@router.get("/{channel_id}/widgets/{widget_id}/versions/{version_id}", response_model=WidgetVersionResponse)
def get_widget_version(
    channel_id: int,
    widget_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    version = widget_version_service.get_version(db, version_id)
    if not version or version.widget_id != widget_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/{channel_id}/widgets/{widget_id}/versions/{version_id}/restore", response_model=CustomWidgetResponse)
def restore_widget_version(
    channel_id: int,
    widget_id: int,
    version_id: int,
    comment: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    version = widget_version_service.get_version(db, version_id)
    if not version or version.widget_id != widget.id:
        raise HTTPException(status_code=404, detail="Version not found")

    widget = widget_version_service.restore_version(db, widget, version)

    widget_version_service.create_version(
        db,
        widget,
        ai_service_id=version.ai_service_id,
        prompt_used=version.prompt_used,
        comment=comment or f"Restore from version {version_id}",
        created_by=current_user.id if current_user else None,
    )

    return widget


@router.get("/{channel_id}/ai/services", response_model=List[AIServiceResponse])
def get_channel_ai_services(
    channel_id: int,
    include_disabled: bool = False,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    services = ai_widget_service.get_services(db, include_disabled=include_disabled)
    return services


@router.post("/{channel_id}/ai/prompts", response_model=AIServicePromptOverrideResponse)
def upsert_channel_prompt_override(
    channel_id: int,
    payload: AIServicePromptOverrideScopedCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    override = (
        db.query(AIServicePromptOverride)
        .filter(
            AIServicePromptOverride.service_id == payload.service_id,
            AIServicePromptOverride.scope == AIScope.CHANNEL,
            AIServicePromptOverride.channel_id == channel.id,
        )
        .first()
    )

    if override:
        for field, value in payload.dict(exclude={"service_id"}).items():
            setattr(override, field, value)
        db.commit()
        db.refresh(override)
        return override

    override = AIServicePromptOverride(
        service_id=payload.service_id,
        scope=AIScope.CHANNEL,
        channel_id=channel.id,
        prompt_common=payload.prompt_common,
        prompt_html=payload.prompt_html,
        prompt_css=payload.prompt_css,
        prompt_js=payload.prompt_js,
        prompt_refine=payload.prompt_refine,
        created_by=current_user.id if current_user else None,
    )

    ai_widget_service.save_override(db, override)
    return override


@router.post("/{channel_id}/widgets/{widget_id}/ai/prompts", response_model=AIServicePromptOverrideResponse)
def upsert_widget_prompt_override(
    channel_id: int,
    widget_id: int,
    payload: AIServicePromptOverrideScopedCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    override = (
        db.query(AIServicePromptOverride)
        .filter(
            AIServicePromptOverride.service_id == payload.service_id,
            AIServicePromptOverride.scope == AIScope.WIDGET,
            AIServicePromptOverride.widget_id == widget.id,
        )
        .first()
    )

    if override:
        for field, value in payload.dict(exclude={"service_id"}).items():
            setattr(override, field, value)
        db.commit()
        db.refresh(override)
        return override

    override = AIServicePromptOverride(
        service_id=payload.service_id,
        scope=AIScope.WIDGET,
        channel_id=channel.id,
        widget_id=widget.id,
        prompt_common=payload.prompt_common,
        prompt_html=payload.prompt_html,
        prompt_css=payload.prompt_css,
        prompt_js=payload.prompt_js,
        prompt_refine=payload.prompt_refine,
        created_by=current_user.id if current_user else None,
    )

    ai_widget_service.save_override(db, override)
    return override


@router.delete("/{channel_id}/ai/prompts/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel_prompt_override(
    channel_id: int,
    override_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    override = db.query(AIServicePromptOverride).filter(
        AIServicePromptOverride.id == override_id,
        AIServicePromptOverride.channel_id == channel.id,
    ).first()
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    ai_widget_service.delete_override(db, override)


@router.delete(
    "/{channel_id}/widgets/{widget_id}/ai/prompts/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_widget_prompt_override(
    channel_id: int,
    widget_id: int,
    override_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    override = db.query(AIServicePromptOverride).filter(
        AIServicePromptOverride.id == override_id,
        AIServicePromptOverride.widget_id == widget_id,
    ).first()
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    ai_widget_service.delete_override(db, override)


@router.get(
    "/{channel_id}/widgets/{widget_id}/ai/prompts",
    response_model=List[AIServicePromptOverrideResponse],
)
def list_widget_prompt_overrides(
    channel_id: int,
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    widget = (
        db.query(CustomWidget)
        .filter(CustomWidget.id == widget_id, CustomWidget.channel_id == channel_id)
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    overrides = (
        db.query(AIServicePromptOverride)
        .filter(
            AIServicePromptOverride.scope == AIScope.WIDGET,
            AIServicePromptOverride.widget_id == widget_id,
        )
        .order_by(AIServicePromptOverride.updated_at.desc())
        .all()
    )
    return overrides


@router.get(
    "/{channel_id}/ai/prompts",
    response_model=List[AIServicePromptOverrideResponse],
)
def list_channel_prompt_overrides(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel_service.check_channel_access(channel, current_user, require_owner=True):
        raise HTTPException(status_code=403, detail="Access denied")

    overrides = (
        db.query(AIServicePromptOverride)
        .filter(
            AIServicePromptOverride.scope == AIScope.CHANNEL,
            AIServicePromptOverride.channel_id == channel_id,
        )
        .order_by(AIServicePromptOverride.updated_at.desc())
        .all()
    )
    return overrides


@ai_router.get("", response_model=List[AIServiceResponse])
def list_ai_services(
    include_disabled: bool = False,
    db: Session = Depends(get_db),
):
    services = ai_widget_service.get_services(db, include_disabled=include_disabled)
    return services


@ai_router.post("", response_model=AIServiceResponse, status_code=status.HTTP_201_CREATED)
def create_ai_service(
    payload: AIServiceCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = AIService(**payload.dict())
    ai_widget_service.create_service(db, service)
    return service


@ai_router.put("/{service_id}", response_model=AIServiceResponse)
def update_ai_service(
    service_id: int,
    payload: AIServiceUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = ai_widget_service.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="AI service not found")

    ai_widget_service.update_service(db, service, payload.dict(exclude_unset=True))
    return service


@ai_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    service = ai_widget_service.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="AI service not found")

    ai_widget_service.delete_service(db, service)







