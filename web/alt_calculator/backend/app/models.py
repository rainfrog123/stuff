from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from enum import Enum

class CalculationType(str, Enum):
    NEW_BOOKING = "new_booking"
    EXTENSION = "extension"
    ROOM_CHANGE = "room_change"

class SeasonType(str, Enum):
    RACK = "Rack"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class RoomPeriod(BaseModel):
    room_type: str
    check_in: datetime
    check_out: datetime
    capacity: int = Field(1, ge=1, le=2)

class BookingCalculationRequest(BaseModel):
    property_name: str = Field(..., description="Property name (Alt_CM or Alt_PR)")
    calculation_type: CalculationType = Field(..., description="Type of calculation")
    room_periods: List[RoomPeriod] = Field(..., max_items=3, description="Room periods, up to 3 changes allowed")
    season: SeasonType = Field(SeasonType.MEDIUM, description="Season type (Rack, High, Medium, Low)")
    manual_discount: float = Field(0.0, ge=0, le=100, description="Manual discount percentage")
    override_extension_rule: bool = Field(False, description="Override 7-day extension rule")

class RoomPeriodBreakdown(BaseModel):
    room_type: str
    nights: int
    base_price_per_night: float
    adjusted_price_per_night: float
    subtotal: float

class PriceCalculationResponse(BaseModel):
    room_breakdowns: List[RoomPeriodBreakdown]
    total_nights: int
    long_stay_discount_percentage: float
    subtotal: float
    vat_amount: float
    total_price: float
    warnings: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "room_breakdowns": [
                    {
                        "room_type": "Ensuite Plus",
                        "nights": 30,
                        "base_price_per_night": 2900.0,
                        "adjusted_price_per_night": 2610.0,
                        "subtotal": 78300.0
                    }
                ],
                "total_nights": 30,
                "long_stay_discount_percentage": 20.0,
                "subtotal": 78300.0,
                "vat_amount": 5481.0,
                "total_price": 83781.0,
                "warnings": []
            }
        } 