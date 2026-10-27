"""Asset upload and media library management API endpoints."""

from __future__ import annotations

import os
import shutil
import uuid
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.asset import Asset, AssetPurpose, AssetType
from backend.models.user import User
from backend.schemas.asset import AssetResponse

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    project_id: Optional[uuid.UUID] = Form(None),
    asset_type: str = Form("reference_image"),
    purpose: str = Form("general"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Uploads a reference image, logo, or media file to the local storage."""
    # Ensure directory exists
    assets_dir = os.path.abspath(settings.ASSETS_PATH)
    os.makedirs(assets_dir, exist_ok=True)

    # Generate unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    safe_id = str(uuid.uuid4())
    stored_name = f"{safe_id}{ext}"
    dest_path = os.path.join(assets_dir, stored_name)

    # Stream write file
    file_size = 0
    async with aiofiles.open(dest_path, "wb") as out_file:
        while chunk := await file.read(64 * 1024):
            file_size += len(chunk)
            await out_file.write(chunk)

    try:
        a_type = AssetType(asset_type)
    except Exception:
        a_type = AssetType.reference_image

    try:
        a_purpose = AssetPurpose(purpose)
    except Exception:
        a_purpose = AssetPurpose.general

    # Optional image dimension extraction
    width, height = None, None
    try:
        from PIL import Image
        with Image.open(dest_path) as img:
            width, height = img.size
    except Exception:
        pass

    asset = Asset(
        project_id=project_id,
        user_id=current_user.id,
        filename=stored_name,
        original_filename=file.filename or stored_name,
        file_path=dest_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        asset_type=a_type,
        purpose=a_purpose,
        width=width,
        height=height,
        meta_data={},
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    logger.info("asset_uploaded", filename=stored_name, size_kb=round(file_size / 1024, 1))
    return asset


@router.get("/", response_model=List[AssetResponse])
async def list_user_assets(
    project_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets uploaded by user, optionally filtered by project."""
    stmt = select(Asset).where(Asset.user_id == current_user.id)
    if project_id:
        stmt = stmt.where(Asset.project_id == project_id)
    stmt = stmt.order_by(Asset.created_at.desc())

    res = await db.execute(stmt)
    return res.scalars().all()


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an asset and unlink from disk."""
    asset = await db.get(Asset, asset_id)
    if not asset or asset.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Asset not found")

    if os.path.exists(asset.file_path):
        try:
            os.remove(asset.file_path)
        except Exception:
            pass

    await db.delete(asset)
    await db.commit()
