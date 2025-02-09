from fastapi import APIRouter, HTTPException
from typing import Dict
from pydantic import BaseModel
from app.pricing import PricingCalculator

router = APIRouter()

class RateUpdate(BaseModel):
    property_name: str
    room_type: str
    rate_type: str
    new_rate: float

@router.get("/rates")
async def get_rates():
    """Get all current rates."""
    return PricingCalculator.get_all_rates()

@router.put("/rates")
async def update_rate(rate_update: RateUpdate):
    """Update a specific rate."""
    try:
        return PricingCalculator.update_rate(
            rate_update.property_name,
            rate_update.room_type,
            rate_update.rate_type,
            rate_update.new_rate
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 