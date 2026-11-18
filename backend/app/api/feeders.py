from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.database.session import get_db
import backend.app.models as m
import backend.app.schemas as s

router = APIRouter(prefix="/feeders", tags=["Feeders"])


@router.get("", response_model=List[s.FeederResponse])
def list_feeders(
    substation_id: Optional[int] = Query(None, description="Filter by substation ID"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, TRIPPED, MAINTENANCE)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve all distribution feeders with optional filtering."""
    query = db.query(m.Feeder)
    if substation_id is not None:
        query = query.filter(m.Feeder.substation_id == substation_id)
    if status is not None:
        query = query.filter(m.Feeder.status == status.upper())
    return query.offset(skip).limit(limit).all()


@router.get("/{feeder_id}", response_model=s.FeederDetailResponse)
def get_feeder(feeder_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed feeder information including section count and sections."""
    feeder = db.query(m.Feeder).filter(m.Feeder.id == feeder_id).first()
    if not feeder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feeder with ID {feeder_id} not found."
        )

    sections = db.query(m.FeederSection).filter(m.FeederSection.feeder_id == feeder_id).all()
    substation_name = feeder.substation.name if feeder.substation else None

    # Construct detail response
    res = s.FeederDetailResponse(
        id=feeder.id,
        substation_id=feeder.substation_id,
        substation_name=substation_name,
        feeder_code=feeder.feeder_code,
        name=feeder.name,
        voltage_kv=feeder.voltage_kv,
        rated_current_a=feeder.rated_current_a,
        nominal_capacity_mva=feeder.nominal_capacity_mva,
        status=feeder.status,
        total_length_km=feeder.total_length_km,
        section_count=len(sections),
        sections=[s.FeederSectionResponse.model_validate(sec) for sec in sections],
        created_at=feeder.created_at,
        updated_at=feeder.updated_at,
    )
    return res


@router.post("", response_model=s.FeederResponse, status_code=status.HTTP_201_CREATED)
def create_feeder(feeder_in: s.FeederCreate, db: Session = Depends(get_db)):
    """Register a new distribution feeder."""
    # Check parent substation
    substation = db.query(m.Substation).filter(m.Substation.id == feeder_in.substation_id).first()
    if not substation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parent substation ID {feeder_in.substation_id} does not exist."
        )

    # Check duplicate feeder code
    existing = db.query(m.Feeder).filter(m.Feeder.feeder_code == feeder_in.feeder_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feeder code '{feeder_in.feeder_code}' is already registered."
        )

    feeder = m.Feeder(**feeder_in.model_dump())
    db.add(feeder)
    db.commit()
    db.refresh(feeder)
    return feeder


@router.patch("/{feeder_id}", response_model=s.FeederResponse)
def update_feeder(feeder_id: int, feeder_update: s.FeederUpdate, db: Session = Depends(get_db)):
    """Update feeder attributes (status, rating, capacity)."""
    feeder = db.query(m.Feeder).filter(m.Feeder.id == feeder_id).first()
    if not feeder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feeder with ID {feeder_id} not found."
        )

    update_data = feeder_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feeder, field, value)

    db.commit()
    db.refresh(feeder)
    return feeder
