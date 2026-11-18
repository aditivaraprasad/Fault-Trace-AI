from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
import backend.app.models as m
import backend.app.schemas as s

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=List[s.AssetRecordResponse])
def list_assets(
    asset_type: Optional[str] = Query(None, description="Filter by asset type (SECTION, TRANSFORMER, BREAKER, CABLE, etc.)"),
    condition_rating: Optional[str] = Query(None, description="Filter by rating (EXCELLENT, GOOD, FAIR, POOR, CRITICAL)"),
    min_health_index: Optional[float] = Query(None, description="Filter assets with health index >= threshold"),
    max_health_index: Optional[float] = Query(None, description="Filter assets with health index <= threshold"),
    identifier: Optional[str] = Query(None, description="Filter by exact or partial asset identifier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve grid asset health records and condition monitoring metrics."""
    query = db.query(m.AssetRecord)
    if asset_type:
        query = query.filter(m.AssetRecord.asset_type == asset_type.upper())
    if condition_rating:
        query = query.filter(m.AssetRecord.condition_rating == condition_rating.upper())
    if min_health_index is not None:
        query = query.filter(m.AssetRecord.health_index >= min_health_index)
    if max_health_index is not None:
        query = query.filter(m.AssetRecord.health_index <= max_health_index)
    if identifier:
        query = query.filter(m.AssetRecord.asset_identifier.ilike(f"%{identifier}%"))

    return query.order_by(m.AssetRecord.health_index.asc()).offset(skip).limit(limit).all()


@router.get("/{asset_id}", response_model=s.AssetRecordResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific asset record by ID."""
    asset = db.query(m.AssetRecord).filter(m.AssetRecord.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset record with ID {asset_id} not found."
        )
    return asset


@router.post("", response_model=s.AssetRecordResponse, status_code=status.HTTP_201_CREATED)
def create_asset(asset_in: s.AssetRecordCreate, db: Session = Depends(get_db)):
    """Register a new asset condition monitoring record."""
    asset = m.AssetRecord(**asset_in.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/{asset_id}", response_model=s.AssetRecordResponse)
def update_asset(asset_id: int, asset_update: s.AssetRecordUpdate, db: Session = Depends(get_db)):
    """Update asset condition, health index, or maintenance status."""
    asset = db.query(m.AssetRecord).filter(m.AssetRecord.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset record with ID {asset_id} not found."
        )

    update_data = asset_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset
