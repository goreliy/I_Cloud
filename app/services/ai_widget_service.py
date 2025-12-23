"""Сервис для работы с ИИ-генерацией виджетов и предпромптами."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from sqlalchemy.orm import Session

from app.models.ai_service import AIService, AIServicePromptOverride, AIScope
from app.models.channel import Channel
from app.models.custom_widget import CustomWidget
from app.models.api_key import ApiKey
from app.models.feed import Feed
from app.services import channel_service, feed_service


@dataclass
class PromptBundle:
    common: str
    html: str
    css: str
    js: str
    refine: str
    context: Dict[str, str]


DEFAULT_PROMPT_COMMON = """Вы выступаете как специалист по фронтенд-визуализации данных для IoT/SCADA панели.
Работаете для канала "{channel_name}" (ID {channel_id}).

Задача: создать кастомный виджет для отображения данных с облачного сервера. Он должен корректно работать внутри div блока с id="{widget_dom_id}".

Данные канала:
- Имя: {channel_name}
- Описание: {channel_description}
- Текущие значения полей: {latest_fields}
- Метки полей: {field_labels}

API записи (HTTP GET/POST):
- URL: {write_api_url}
- Пример запроса: {write_api_example}

API чтения последнего значения (JSON):
- URL: {read_last_api_url}
- Пример запроса: {read_last_api_example}

Формат ответа: подготовьте отдельные блоки HTML, CSS и JS, которые можно вставить на страницу без дополнительных зависимостей. Используйте JavaScript без внешних библиотек (только нативный ES6)."""

DEFAULT_PROMPT_HTML = """Сгенерируйте HTML разметку виджета. Используйте контейнер <div id=\"{widget_dom_id}\"> как корневой элемент. Добавьте элементы для отображения основных данных. Не подключайте внешние стили, только классы/идентификаторы."""

DEFAULT_PROMPT_CSS = """Сгенерируйте CSS стили для виджета. Используйте префикс #{widget_dom_id} для всех селекторов, чтобы исключить конфликты. Стили должны быть самодостаточными."""

DEFAULT_PROMPT_JS = """Сгенерируйте JavaScript код для:
1. Инициализации виджета после загрузки страницы.
2. Периодического опроса {read_last_api_url} каждые {polling_interval_seconds} секунд (используйте fetch с обработкой ошибок).
3. Обновления DOM и визуальных элементов в зависимости от полученных данных.
4. Отправки команд (если необходимы) через {write_api_url} методом fetch.

Ожидаемый формат: чистый JS без оберток, внутри IIFE (function() {{ ... }})();, используя константы CHANNEL_ID={channel_id}, WIDGET_ID={widget_id}."""

DEFAULT_PROMPT_REFINE = """Я получил результат, но хочу доработать. Исходный промпт:
---
{original_prompt}
---
Ответ сервиса:
---
{previous_response}
---
Нужно учесть:
{feedback}

Сформируй обновлённые HTML, CSS и JS с учётом замечаний. Ответ также разделяй по блокам."""


def _render_template(template: Optional[str], context: Dict[str, str], fallback: str) -> str:
    content = template or fallback
    try:
        return content.format(**context)
    except KeyError:
        # Если пользовательский шаблон содержит неизвестные плейсхолдеры, оставим как есть
        return content


def _collect_field_labels(channel: Channel) -> Dict[str, str]:
    labels = {}
    for idx in range(1, 9):
        label_value = getattr(channel, f"field{idx}_label", None) or f"Field {idx}"
        labels[f"field{idx}"] = label_value
    return labels


def _format_latest_feed(feed: Optional[Feed]) -> str:
    if not feed:
        return "данные отсутствуют"
    values = []
    for idx in range(1, 9):
        value = getattr(feed, f"field{idx}")
        values.append(f"field{idx}={value}")
    return ", ".join(values)


def _resolve_prompt_templates(
    db: Session,
    service: AIService,
    channel: Optional[Channel] = None,
    widget: Optional[CustomWidget] = None,
) -> Dict[str, Optional[str]]:
    templates = {
        "common": service.default_prompt_common,
        "html": service.default_prompt_html,
        "css": service.default_prompt_css,
        "js": service.default_prompt_js,
        "refine": service.default_prompt_refine,
    }

    overrides: Sequence[AIServicePromptOverride] = db.query(AIServicePromptOverride).filter(
        AIServicePromptOverride.service_id == service.id
    ).all()

    # Применяем по приоритету: глобальный < канал < виджет
    for override in overrides:
        if override.scope == AIScope.GLOBAL:
            templates = _apply_override(templates, override)
        elif override.scope == AIScope.CHANNEL and channel and override.channel_id == channel.id:
            templates = _apply_override(templates, override)
        elif override.scope == AIScope.WIDGET and widget and override.widget_id == widget.id:
            templates = _apply_override(templates, override)

    return templates


def get_prompt_templates(
    db: Session,
    service: AIService,
    channel: Optional[Channel] = None,
    widget: Optional[CustomWidget] = None,
) -> Dict[str, Optional[str]]:
    """Публичная обёртка для получения шаблонов предпромпта."""
    return _resolve_prompt_templates(db, service, channel, widget)


def _apply_override(
    templates: Dict[str, Optional[str]],
    override: AIServicePromptOverride,
) -> Dict[str, Optional[str]]:
    result = templates.copy()
    if override.prompt_common:
        result["common"] = override.prompt_common
    if override.prompt_html:
        result["html"] = override.prompt_html
    if override.prompt_css:
        result["css"] = override.prompt_css
    if override.prompt_js:
        result["js"] = override.prompt_js
    if override.prompt_refine:
        result["refine"] = override.prompt_refine
    return result


def get_services(db: Session, include_disabled: bool = False) -> Sequence[AIService]:
    query = db.query(AIService).order_by(AIService.display_order.asc(), AIService.id.asc())
    if not include_disabled:
        query = query.filter(AIService.is_enabled == True)
    return query.all()


def get_service(db: Session, service_id: int) -> Optional[AIService]:
    return db.query(AIService).filter(AIService.id == service_id).first()


def get_service_by_alias(db: Session, alias: str) -> Optional[AIService]:
    return db.query(AIService).filter(AIService.alias == alias).first()


def create_service(db: Session, service: AIService) -> AIService:
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def update_service(db: Session, service: AIService, data: Dict) -> AIService:
    for field, value in data.items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service: AIService) -> None:
    db.delete(service)
    db.commit()


def save_override(
    db: Session,
    override: AIServicePromptOverride,
) -> AIServicePromptOverride:
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


def delete_override(db: Session, override: AIServicePromptOverride) -> None:
    db.delete(override)
    db.commit()


def get_overrides_for_service(
    db: Session,
    service_id: int,
    channel_id: Optional[int] = None,
    widget_id: Optional[int] = None,
) -> Sequence[AIServicePromptOverride]:
    query = db.query(AIServicePromptOverride).filter(
        AIServicePromptOverride.service_id == service_id
    )
    if channel_id is not None:
        query = query.filter(
            (AIServicePromptOverride.scope == AIScope.CHANNEL) &
            (AIServicePromptOverride.channel_id == channel_id)
        )
    if widget_id is not None:
        query = query.filter(
            (AIServicePromptOverride.scope == AIScope.WIDGET) &
            (AIServicePromptOverride.widget_id == widget_id)
        )
    return query.order_by(AIServicePromptOverride.updated_at.desc()).all()


def build_prompt(
    db: Session,
    service: AIService,
    channel: Channel,
    base_url: str,
    widget: Optional[CustomWidget] = None,
    polling_interval_seconds: int = 5,
) -> PromptBundle:
    """Собрать текст предпромпта с подстановкой данных канала."""

    api_keys = channel_service.get_channel_api_keys(db, channel.id)
    write_key = _pick_api_key(api_keys, "write")
    read_key = _pick_api_key(api_keys, "read")

    write_url = f"{base_url}/update?api_key={write_key.key if write_key else 'WRITE_KEY'}&field1=VALUE"
    write_example = f"curl \"{base_url}/update?api_key={(write_key.key if write_key else 'WRITE_KEY')}&field1=23.5&field2=60\""

    read_last_url = f"{base_url}/api/channels/{channel.id}/feeds/last.json"
    if read_key:
        read_last_url += f"?api_key={read_key.key}"
    read_last_example = f"curl \"{read_last_url}\""

    latest_feed = feed_service.get_last_feed(db, channel.id)

    widget_dom_id = f"html-widget-{widget.id}" if widget else "generated-widget-preview"

    context = {
        "channel_id": str(channel.id),
        "channel_name": channel.name,
        "channel_description": channel.description or "(описание отсутствует)",
        "widget_id": str(widget.id) if widget else "0",
        "widget_dom_id": widget_dom_id,
        "latest_fields": _format_latest_feed(latest_feed),
        "field_labels": ", ".join(
            f"{name}={label}" for name, label in _collect_field_labels(channel).items()
        ),
        "write_api_url": write_url,
        "write_api_example": write_example,
        "read_last_api_url": read_last_url,
        "read_last_api_example": read_last_example,
        "polling_interval_seconds": str(polling_interval_seconds),
    }

    templates = _resolve_prompt_templates(db, service, channel, widget)

    return PromptBundle(
        common=_render_template(templates.get("common"), context, DEFAULT_PROMPT_COMMON),
        html=_render_template(templates.get("html"), context, DEFAULT_PROMPT_HTML),
        css=_render_template(templates.get("css"), context, DEFAULT_PROMPT_CSS),
        js=_render_template(templates.get("js"), context, DEFAULT_PROMPT_JS),
        refine=_render_template(templates.get("refine"), context, DEFAULT_PROMPT_REFINE),
        context=context,
    )


def build_refine_prompt(
    service: AIService,
    original_prompt: str,
    previous_response: str,
    feedback: str,
    templates: Optional[Dict[str, Optional[str]]] = None,
) -> str:
    """Сформировать уточняющий промпт для повторного запроса."""
    template = None
    if templates:
        template = templates.get("refine")
    context = {
        "original_prompt": original_prompt,
        "previous_response": previous_response,
        "feedback": feedback,
    }
    return _render_template(template, context, DEFAULT_PROMPT_REFINE)


def _pick_api_key(keys: Sequence[ApiKey], key_type: str) -> Optional[ApiKey]:
    for key in keys:
        if key.type == key_type and key.is_active:
            return key
    return None

