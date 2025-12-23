"""Feed (data) routes - REST API для работы с данными"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
import csv
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

from app.database import get_db
from app.schemas.feed import FeedCreate, FeedResponse
from app.services import channel_service, feed_service, data_processor
from app.config import settings as app_settings
from app.services.mem_buffer import mem_buffer, FeedSpec
from app.dependencies import verify_api_key, get_current_user_optional
from app.models.user import User

router = APIRouter(tags=["feeds"])


_api_key_cache: dict[str, tuple[int, float]] = {}


def _ensure_read_access(
    db: Session,
    channel,
    current_user: Optional[User],
    api_key: Optional[str]
) -> None:
    """Validate that caller can read channel data using user session or read API key."""
    if api_key:
        key_obj = verify_api_key(api_key, "read", db)
        if not key_obj or key_obj.channel_id != channel.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid read API key"
            )
        return

    if not channel_service.check_channel_access(channel, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to private channel"
        )

def _get_channel_by_write_key_cached(db: Session, key: str):
    from time import time as _now
    from app.models.api_key import ApiKey as _ApiKey
    ttl = app_settings.API_KEY_CACHE_TTL
    item = _api_key_cache.get(key)
    now = _now()
    if item and now - item[1] < ttl:
        channel_id = item[0]
        from app.services import channel_service as _cs
        return _cs.get_channel(db, channel_id)
    key_obj = db.query(_ApiKey).filter(
        _ApiKey.key == key,
        _ApiKey.type == "write",
        _ApiKey.is_active == True
    ).first()
    if not key_obj:
        return None
    _api_key_cache[key] = (key_obj.channel_id, now)
    from app.services import channel_service as _cs
    return _cs.get_channel(db, key_obj.channel_id)

@router.post("/update")
@router.get("/update")
async def update_feed(
    api_key: str = Query(..., description="Write API key"),
    field1: Optional[float] = None,
    field2: Optional[float] = None,
    field3: Optional[float] = None,
    field4: Optional[float] = None,
    field5: Optional[float] = None,
    field6: Optional[float] = None,
    field7: Optional[float] = None,
    field8: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    elevation: Optional[float] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Write data to channel
    Supports both GET and POST methods
    """
    # Verify API key and get channel
    from app.config import settings
    from app.models.api_key import ApiKey
    
    if settings.AUTH_ENABLED:
        # In auth mode, verify API key (cached)
        channel = _get_channel_by_write_key_cached(db, api_key)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    else:
        # In no-auth mode, try to find API key (optional)
        # If no key found, user should specify channel somehow
        # For simplicity, we can just reject - use direct channel endpoints
        key_obj = db.query(ApiKey).filter(ApiKey.key == api_key).first()
        if not key_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key not found. Create a channel first and use its API key."
            )
        channel = channel_service.get_channel(db, key_obj.channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Получить выходные поля и последнее значение для сохранения состояния автоматизации
    from app.services.automation_service import get_output_fields
    output_fields = get_output_fields(channel.id, db)
    last_feed = feed_service.get_last_feed(db, channel.id) if output_fields else None
    
    # Словарь для полей, сохраняющий значения выходных полей
    field_values = {
        'field1': field1,
        'field2': field2,
        'field3': field3,
        'field4': field4,
        'field5': field5,
        'field6': field6,
        'field7': field7,
        'field8': field8,
    }
    
    # Для выходных полей: если не указаны явно, взять из последнего feed
    if last_feed:
        for field_name in ['field1', 'field2', 'field3', 'field4', 'field5', 'field6', 'field7', 'field8']:
            if field_values[field_name] is None and field_name in output_fields:
                field_values[field_name] = getattr(last_feed, field_name, None)
    
    # Always do direct write to return real entry_id (ThingSpeak compatible)
    # Memory buffer can be used for internal operations, but /update endpoint
    # must return actual entry_id for compatibility
    feed_data = FeedCreate(
        field1=field_values['field1'],
        field2=field_values['field2'],
        field3=field_values['field3'],
        field4=field_values['field4'],
        field5=field_values['field5'],
        field6=field_values['field6'],
        field7=field_values['field7'],
        field8=field_values['field8'],
        latitude=latitude,
        longitude=longitude,
        elevation=elevation,
        status=status
    )
    
    # Create feed without committing
    feed = feed_service.create_feed(db, channel, feed_data, auto_commit=False)
    
    # Execute automation rules
    from app.services.automation_service import automation_engine
    feed = automation_engine.execute_rules(channel.id, feed, db)
    
    # Now commit with modified feed
    db.commit()
    db.refresh(feed)
    
    # Return entry_id as plain text
    return PlainTextResponse(content=str(feed.entry_id))


@router.get("/channels/{channel_id}/feeds.json")
def get_feeds_json(
    channel_id: int,
    results: int = Query(100, ge=1, le=8000),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    timescale: Optional[int] = Query(None, description="Average by minutes"),
    average: Optional[int] = Query(None, description="Average by minutes"),
    median: Optional[int] = Query(None, description="Calculate median"),
    sum: Optional[int] = Query(None, description="Sum by minutes"),
    round: Optional[int] = Query(None, ge=0, le=10, description="Round to decimals"),
    api_key: Optional[str] = Query(None, description="Read API key"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get feed data in JSON format"""
    from app.dependencies import get_current_user_optional
    from app.models.user import User
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Проверить доступ к приватному каналу
    _ensure_read_access(db, channel, current_user, api_key)
    
    # Get feeds
    feeds = feed_service.get_feeds(db, channel_id, results, start, end)
    
    # Apply data processing
    if timescale:
        processed_data = data_processor.timescale_data(feeds, timescale)
        return {"channel": {"id": channel.id, "name": channel.name}, "feeds": processed_data}
    elif average:
        processed_data = data_processor.calculate_average(feeds, average)
        return {"channel": {"id": channel.id, "name": channel.name}, "feeds": processed_data}
    elif median:
        processed_data = data_processor.calculate_median(feeds)
        return {"channel": {"id": channel.id, "name": channel.name}, "feeds": processed_data}
    elif sum:
        processed_data = data_processor.calculate_sum(feeds, sum)
        return {"channel": {"id": channel.id, "name": channel.name}, "feeds": processed_data}
    
    # Apply rounding if requested
    if round is not None:
        feeds = data_processor.round_values(feeds, round)
    
    # Convert to response format
    feeds_response = [FeedResponse.from_orm(feed) for feed in feeds]
    
    return {
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "description": channel.description,
            "last_entry_id": channel.last_entry_id
        },
        "feeds": feeds_response
    }


@router.get("/channels/{channel_id}/feeds.xml")
def get_feeds_xml(
    channel_id: int,
    results: int = Query(100, ge=1, le=8000),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get feed data in XML format"""
    from app.models.user import User
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Проверить доступ
    if not channel_service.check_channel_access(channel, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to private channel"
        )
    
    feeds = feed_service.get_feeds(db, channel_id, results, start, end)
    
    # Create XML
    root = ET.Element("channel")
    ET.SubElement(root, "id").text = str(channel.id)
    ET.SubElement(root, "name").text = channel.name
    
    feeds_elem = ET.SubElement(root, "feeds")
    for feed in feeds:
        feed_elem = ET.SubElement(feeds_elem, "feed")
        ET.SubElement(feed_elem, "id").text = str(feed.id)
        ET.SubElement(feed_elem, "entry_id").text = str(feed.entry_id)
        ET.SubElement(feed_elem, "created_at").text = feed.created_at.isoformat()
        
        for i in range(1, 9):
            field_name = f"field{i}"
            value = getattr(feed, field_name)
            if value is not None:
                ET.SubElement(feed_elem, field_name).text = str(value)
    
    # Pretty print XML
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    
    return Response(content=xml_str, media_type="application/xml")


@router.get("/channels/{channel_id}/feeds.csv")
def get_feeds_csv(
    channel_id: int,
    results: int = Query(100, ge=1, le=8000),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get feed data in CSV format"""
    from app.models.user import User
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Проверить доступ
    if not channel_service.check_channel_access(channel, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to private channel"
        )
    
    feeds = feed_service.get_feeds(db, channel_id, results, start, end)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "entry_id", "created_at",
        "field1", "field2", "field3", "field4",
        "field5", "field6", "field7", "field8",
        "latitude", "longitude", "elevation", "status"
    ])
    
    # Data rows
    for feed in feeds:
        writer.writerow([
            feed.entry_id,
            feed.created_at.isoformat(),
            feed.field1, feed.field2, feed.field3, feed.field4,
            feed.field5, feed.field6, feed.field7, feed.field8,
            feed.latitude, feed.longitude, feed.elevation, feed.status
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(content=csv_content, media_type="text/csv")


@router.get("/channels/{channel_id}/feeds/last.json")
def get_last_feed(
    channel_id: int,
    api_key: Optional[str] = Query(None, description="Read API key"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get last feed entry"""
    from app.models.user import User
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Проверить доступ
    _ensure_read_access(db, channel, current_user, api_key)
    
    feed = feed_service.get_last_feed(db, channel_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data available"
        )
    
    return {
        "channel": {"id": channel.id, "name": channel.name},
        "feed": FeedResponse.from_orm(feed)
    }


@router.get("/channels/{channel_id}/field/{field_num}.json")
def get_field_data(
    channel_id: int,
    field_num: int,
    results: int = Query(100, ge=1, le=8000),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    api_key: Optional[str] = Query(None, description="Read API key"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get data for specific field"""
    from app.models.user import User
    
    if field_num < 1 or field_num > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field number must be between 1 and 8"
        )
    
    channel = channel_service.get_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Проверить доступ
    _ensure_read_access(db, channel, current_user, api_key)
    
    feeds = feed_service.get_field_data(db, channel_id, field_num, results, start, end)
    
    field_name = f"field{field_num}"
    field_data = []
    for feed in feeds:
        field_data.append({
            "entry_id": feed.entry_id,
            "created_at": feed.created_at,
            field_name: getattr(feed, field_name)
        })
    
    return {
        "channel": {"id": channel.id, "name": channel.name},
        "field": field_num,
        "feeds": field_data
    }

