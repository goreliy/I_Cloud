"""Сервис управления версиями пользовательских виджетов."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import difflib

from sqlalchemy.orm import Session

from app.models.custom_widget import CustomWidget
from app.models.widget_version import WidgetVersion


@dataclass
class VersionDiff:
    html: str
    css: str
    js: str


def create_version(
    db: Session,
    widget: CustomWidget,
    *,
    ai_service_id: Optional[int] = None,
    prompt_used: Optional[str] = None,
    comment: Optional[str] = None,
    created_by: Optional[int] = None,
) -> WidgetVersion:
    version = WidgetVersion(
        widget_id=widget.id,
        ai_service_id=ai_service_id,
        prompt_used=prompt_used,
        comment=comment,
        html_code=widget.html_code,
        css_code=widget.css_code,
        js_code=widget.js_code,
        created_by=created_by,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_versions(db: Session, widget_id: int, limit: int = 20) -> List[WidgetVersion]:
    return (
        db.query(WidgetVersion)
        .filter(WidgetVersion.widget_id == widget_id)
        .order_by(WidgetVersion.created_at.desc())
        .limit(limit)
        .all()
    )


def get_version(db: Session, version_id: int) -> Optional[WidgetVersion]:
    return db.query(WidgetVersion).filter(WidgetVersion.id == version_id).first()


def restore_version(db: Session, widget: CustomWidget, version: WidgetVersion) -> CustomWidget:
    widget.html_code = version.html_code
    widget.css_code = version.css_code
    widget.js_code = version.js_code
    db.commit()
    db.refresh(widget)
    return widget


def diff_between_versions(old: WidgetVersion, new: WidgetVersion) -> VersionDiff:
    return VersionDiff(
        html=_diff_text(old.html_code or "", new.html_code or ""),
        css=_diff_text(old.css_code or "", new.css_code or ""),
        js=_diff_text(old.js_code or "", new.js_code or ""),
    )


def diff_with_current(widget: CustomWidget, version: WidgetVersion) -> VersionDiff:
    return VersionDiff(
        html=_diff_text(version.html_code or "", widget.html_code or ""),
        css=_diff_text(version.css_code or "", widget.css_code or ""),
        js=_diff_text(version.js_code or "", widget.js_code or ""),
    )


def _diff_text(old: str, new: str) -> str:
    diff = difflib.unified_diff(
        (old or "").splitlines(True),
        (new or "").splitlines(True),
        lineterm="",
        fromfile="old",
        tofile="new",
    )
    return "".join(diff)

