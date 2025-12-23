"""Upload service for handling file uploads"""
import os
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io


# Allowed extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB
MAX_CHANNEL_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Upload directories
UPLOAD_DIR = "app/static/uploads"
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
CHANNEL_DIR = os.path.join(UPLOAD_DIR, "channels")


def ensure_upload_dirs():
    """Create upload directories if they don't exist"""
    os.makedirs(AVATAR_DIR, exist_ok=True)
    os.makedirs(CHANNEL_DIR, exist_ok=True)


def validate_image(file: UploadFile, max_size: int) -> None:
    """Validate uploaded image file"""
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # Check file size (will be checked during read)
    # Content type check
    if file.content_type and not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )


def resize_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """Resize image while maintaining aspect ratio"""
    # Calculate new size
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return image


async def save_avatar(file: UploadFile, user_id: int) -> str:
    """
    Save avatar image for user
    Returns relative URL path to saved image
    """
    ensure_upload_dirs()
    validate_image(file, MAX_AVATAR_SIZE)
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_AVATAR_SIZE / 1024 / 1024}MB"
        )
    
    # Open and resize image
    try:
        image = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        # Resize to max 300x300
        image = resize_image(image, 300, 300)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    
    # Save image
    image.save(filepath, quality=85, optimize=True)
    
    # Return relative URL
    return f"/static/uploads/avatars/{filename}"


async def save_channel_image(file: UploadFile, channel_id: int, image_type: str = "image") -> str:
    """
    Save channel image (main image or background)
    Returns relative URL path to saved image
    """
    ensure_upload_dirs()
    validate_image(file, MAX_CHANNEL_IMAGE_SIZE)
    
    # Create channel directory
    channel_dir = os.path.join(CHANNEL_DIR, str(channel_id))
    os.makedirs(channel_dir, exist_ok=True)
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_CHANNEL_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_CHANNEL_IMAGE_SIZE / 1024 / 1024}MB"
        )
    
    # Open and resize image
    try:
        image = Image.open(io.BytesIO(content))
        
        # Resize based on type
        if image_type == "image":
            # Channel main image: max 800x600
            image = resize_image(image, 800, 600)
        else:  # background
            # Background: max 1920x1080
            image = resize_image(image, 1920, 1080)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{image_type}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(channel_dir, filename)
    
    # Save image
    image.save(filepath, quality=85, optimize=True)
    
    # Return relative URL
    return f"/static/uploads/channels/{channel_id}/{filename}"


def delete_file(file_path: str) -> None:
    """Delete file if it exists"""
    if file_path and file_path.startswith('/static/'):
        # Convert URL path to filesystem path
        fs_path = file_path.replace('/static/', 'app/static/')
        if os.path.exists(fs_path):
            try:
                os.remove(fs_path)
            except Exception:
                pass  # Ignore errors


async def save_svg_file(file: UploadFile, channel_id: int) -> str:
    """
    Save SVG file for channel widget
    Returns relative URL path to saved SVG
    """
    # Validate extension
    if not file.filename.lower().endswith('.svg'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Только SVG файлы разрешены"
        )
    
    # Read and validate size
    content = await file.read()
    if len(content) > 1024 * 1024:  # 1MB max
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SVG файл слишком большой (максимум 1MB)"
        )
    
    # Decode and sanitize SVG
    try:
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверная кодировка файла"
        )
    
    # Удалить опасные теги для безопасности
    dangerous_tags = ['script', 'object', 'embed', 'iframe', 'link', 'use']
    dangerous_attrs = ['onload', 'onclick', 'onerror', 'onmouseover']
    
    content_lower = content_str.lower()
    for tag in dangerous_tags:
        if f'<{tag}' in content_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SVG не может содержать тег <{tag}> (безопасность)"
            )
    
    for attr in dangerous_attrs:
        if attr in content_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SVG не может содержать атрибут {attr} (безопасность)"
            )
    
    # Создать директорию для SVG
    svg_dir = os.path.join(UPLOAD_DIR, "channels", str(channel_id), "svg")
    os.makedirs(svg_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"widget_{uuid.uuid4().hex[:8]}.svg"
    filepath = os.path.join(svg_dir, filename)
    
    # Save SVG file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_str)
    
    # Return relative URL
    return f"/static/uploads/channels/{channel_id}/svg/{filename}"

