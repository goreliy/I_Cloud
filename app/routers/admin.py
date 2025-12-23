"""Admin panel routes"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import psutil

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.channel import Channel
from app.models.feed import Feed
from app.models.request_log import RequestLog
from app.config import settings
import psutil as _psutil
from app.services.mem_buffer import mem_buffer
from app.services import auth_service
from app.schemas.user import UserUpdate, UserDetailResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get system statistics"""
    total_users = db.query(User).count()
    total_channels = db.query(Channel).count()
    total_feeds = db.query(Feed).count()
    
    # Active users (with at least one channel)
    active_users = db.query(func.count(func.distinct(Channel.user_id))).scalar()
    
    # Public channels
    public_channels = db.query(Channel).filter(Channel.public == True).count()
    
    # Recent feeds (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_feeds = db.query(Feed).filter(Feed.created_at >= yesterday).count()
    
    # Request stats (last 24 hours)
    recent_requests = db.query(RequestLog).filter(RequestLog.timestamp >= yesterday).count()
    
    # Average response time
    avg_response_time = db.query(func.avg(RequestLog.response_time)).filter(
        RequestLog.timestamp >= yesterday
    ).scalar() or 0
    
    # System stats
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "total_users": total_users,
        "active_users": active_users or 0,
        "total_channels": total_channels,
        "public_channels": public_channels,
        "total_feeds": total_feeds,
        "recent_feeds_24h": recent_feeds,
        "recent_requests_24h": recent_requests,
        "avg_response_time": round(avg_response_time, 2),
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent
    }


@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    sort: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all users with sorting"""
    query = db.query(User)
    
    # Apply sorting
    if order == "desc":
        query = query.order_by(desc(getattr(User, sort, User.created_at)))
    else:
        query = query.order_by(getattr(User, sort, User.created_at))
    
    users = query.offset(skip).limit(limit).all()
    
    # Add channel count and profile for each user
    users_with_stats = []
    for user in users:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        user_dict = {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "display_name": profile.display_name if profile else None,
            "channel_count": db.query(Channel).filter(Channel.user_id == user.id).count()
        }
        users_with_stats.append(user_dict)
    
    return users_with_stats


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get user details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    channel_count = db.query(Channel).filter(Channel.user_id == user_id).count()
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login,
        display_name=profile.display_name,
        channel_count=channel_count,
    )


@router.put("/users/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Update user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-demotion from admin
    if user_id == admin.id and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="Cannot remove admin status from yourself")
    
    # Update user fields
    if payload.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = payload.email
    
    if payload.is_active is not None:
        user.is_active = payload.is_active
    
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    
    # Update profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
    
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    
    db.commit()
    db.refresh(user)
    db.refresh(profile)
    
    channel_count = db.query(Channel).filter(Channel.user_id == user_id).count()
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login,
        display_name=profile.display_name,
        channel_count=channel_count,
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Check if user has channels
    channel_count = db.query(Channel).filter(Channel.user_id == user_id).count()
    if channel_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete user with {channel_count} channel(s). Delete channels first."
        )
    
    db.delete(user)
    db.commit()
    
    return {"status": "ok", "message": "User deleted"}


@router.post("/users/{user_id}/force-password-change")
def force_password_change(
    user_id: int,
    new_password: Optional[str] = Query(None),
    method: str = Query("direct"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Force password change for user.
    
    Args:
        user_id: User ID
        new_password: New password (required if method='direct')
        method: 'direct' to set password directly, 'email' to send reset link
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if method == "direct":
        if not new_password:
            raise HTTPException(status_code=400, detail="new_password is required for direct method")
        
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        user.hashed_password = auth_service.get_password_hash(new_password)
        db.commit()
        
        return {"status": "ok", "message": "Password changed successfully"}
    
    elif method == "email":
        # Generate reset token
        from datetime import timedelta
        token_expires = timedelta(hours=24)
        reset_token = auth_service.create_access_token(
            data={"sub": str(user.id), "type": "password_reset"},
            expires_delta=token_expires
        )
        
        # TODO: Send email with reset link
        # For now, return the token (in production, send via email)
        reset_url = f"/reset-password?token={reset_token}"
        
        return {
            "status": "ok",
            "message": "Password reset link generated",
            "reset_url": reset_url,  # Remove in production, send via email
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid method. Use 'direct' or 'email'")


@router.post("/users/{user_id}/send-reset-link")
def send_reset_link(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Send password reset link to user"""
    return force_password_change(user_id=user_id, method="email", db=db, admin=admin)


@router.get("/channels")
def list_all_channels(
    skip: int = 0,
    limit: int = 100,
    sort: str = "created_at",
    order: str = "desc",
    filter_public: Optional[bool] = None,
    include_stats: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all channels with sorting and filtering"""
    from app.services import channel_stats
    
    query = db.query(Channel)
    
    # Apply filter
    if filter_public is not None:
        query = query.filter(Channel.public == filter_public)
    
    # Apply sorting
    if order == "desc":
        query = query.order_by(desc(getattr(Channel, sort, Channel.created_at)))
    else:
        query = query.order_by(getattr(Channel, sort, Channel.created_at))
    
    channels = query.offset(skip).limit(limit).all()
    
    # Add stats for each channel
    channels_with_stats = []
    for channel in channels:
        owner = db.query(User).filter(User.id == channel.user_id).first() if channel.user_id else None
        channel_dict = {
            "id": channel.id,
            "name": channel.name,
            "owner_email": owner.email if owner else "N/A",
            "public": channel.public,
            "entry_count": channel.last_entry_id,
            "created_at": channel.created_at,
            "updated_at": channel.updated_at
        }
        
        if include_stats:
            stats = channel_stats.calculate_channel_stats(channel.id, db)
            channel_dict.update({
                "avg_interval_seconds": stats.avg_interval_seconds,
                "min_interval_seconds": stats.min_interval_seconds,
                "recent_count": stats.recent_count,
            })
        
        channels_with_stats.append(channel_dict)
    
    return channels_with_stats


@router.get("/channels/{channel_id}/stats")
def get_channel_stats(
    channel_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get detailed statistics for a channel"""
    from app.services import channel_stats
    
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    stats = channel_stats.calculate_channel_stats(channel_id, db)
    return stats.to_dict()


@router.get("/requests")
def list_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[int] = None,
    method: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List recent API requests"""
    query = db.query(RequestLog)
    
    # Apply filters
    if status:
        query = query.filter(RequestLog.response_status == status)
    if method:
        query = query.filter(RequestLog.method == method)
    
    # Order by timestamp desc
    query = query.order_by(desc(RequestLog.timestamp))
    
    requests = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": req.id,
            "timestamp": req.timestamp,
            "method": req.method,
            "endpoint": req.endpoint,
            "status": req.response_status,
            "response_time": req.response_time,
            "ip_address": req.ip_address
        }
        for req in requests
    ]


@router.get("/system/health")
def system_health(admin: User = Depends(get_current_admin)):
    """Get system health metrics"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        },
        "membuffer": mem_buffer.stats() if settings.MEMBUFFER_ENABLED else None
    }


@router.get("/process/memory")
def process_memory(admin: User = Depends(get_current_admin)):
    """Get application memory usage (process + children)"""
    try:
        proc = _psutil.Process()
        rss = proc.memory_info().rss
        children_rss = 0
        for ch in proc.children(recursive=True):
            try:
                children_rss += ch.memory_info().rss
            except Exception:
                pass
        total_rss = rss + children_rss
        vm = _psutil.virtual_memory()
        total_mb = vm.total / (1024 ** 2)
        app_mb = total_rss / (1024 ** 2)
        app_percent = (total_rss / vm.total * 100.0) if vm.total else 0.0
        return {
            "rss_bytes": rss,
            "rss_mb": round(rss / (1024 ** 2), 2),
            "children_rss_mb": round(children_rss / (1024 ** 2), 2),
            "total_app_mb": round(app_mb, 2),
            "system_total_mb": round(total_mb, 2),
            "app_percent": round(app_percent, 2)
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/membuffer/stats")
def membuffer_stats(admin: User = Depends(get_current_admin)):
    """Get in-memory buffer stats"""
    if not settings.MEMBUFFER_ENABLED:
        return {"enabled": False}
    return {"enabled": True, **mem_buffer.stats()}


@router.post("/membuffer/flush")
async def membuffer_flush(admin: User = Depends(get_current_admin)):
    """Force flush current queue"""
    if not settings.MEMBUFFER_ENABLED:
        return {"enabled": False}
    await mem_buffer._flush_batch(flush_all=True)
    return {"ok": True, **mem_buffer.stats()}

