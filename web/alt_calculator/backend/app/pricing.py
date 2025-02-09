import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from fastapi import HTTPException

class PricingCalculator:
    # Load rates from JSON
    RATES: Dict[str, Dict[str, Dict[str, float]]] = {}
    DISCOUNTS: Dict = {}
    
    @classmethod
    def load_rates(cls):
        """Load rates from JSON file."""
        json_path = Path(__file__).parent / "data" / "rates.json"
        try:
            with open(json_path, 'r') as f:
                cls.RATES = json.load(f)
        except FileNotFoundError:
            raise ValueError("Rates file not found. Please ensure rates.json exists in the data directory.")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in rates file.")

    @classmethod
    def load_discounts(cls):
        """Load discount configurations from JSON."""
        json_path = Path(__file__).parent / "data" / "discounts.json"
        try:
            with open(json_path, 'r') as f:
                cls.DISCOUNTS = json.load(f)
        except FileNotFoundError:
            raise ValueError("Discounts file not found. Please ensure discounts.json exists in the data directory.")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in discounts file.")

    @classmethod
    def save_rates(cls):
        """Save current rates to JSON file."""
        json_path = Path(__file__).parent / "data" / "rates.json"
        with open(json_path, 'w') as f:
            json.dump(cls.RATES, f, indent=4)

    @classmethod
    def update_rate(cls, property_name: str, room_type: str, rate_type: str, new_rate: float) -> Dict:
        """Update a specific rate and save to JSON."""
        if not cls.RATES:
            cls.load_rates()
            
        if property_name not in cls.RATES:
            raise HTTPException(status_code=404, detail=f"Property {property_name} not found")
            
        if room_type not in cls.RATES[property_name]:
            raise HTTPException(status_code=404, detail=f"Room type {room_type} not found")
            
        if rate_type not in ["Rack", "High", "Medium", "Low"]:
            raise HTTPException(status_code=400, detail=f"Invalid rate type {rate_type}")
            
        cls.RATES[property_name][room_type][rate_type] = new_rate
        cls.save_rates()
        
        return {
            "message": "Rate updated successfully",
            "property": property_name,
            "room_type": room_type,
            "rate_type": rate_type,
            "new_rate": new_rate
        }

    @classmethod
    def get_all_rates(cls) -> Dict:
        """Get all current rates."""
        if not cls.RATES:
            cls.load_rates()
        return cls.RATES

    @classmethod
    def calculate_long_stay_discount(cls, total_nights: int) -> float:
        """Calculate long-stay discount percentage based on total nights."""
        if not cls.DISCOUNTS:
            cls.load_discounts()
            
        discount = 0.0
        for threshold in sorted([int(k) for k in cls.DISCOUNTS["long_stay_discounts"].keys()], reverse=True):
            if total_nights >= threshold:
                return cls.DISCOUNTS["long_stay_discounts"][str(threshold)]["discount"]
        return discount

    @classmethod
    def get_base_price(cls, property_name: str, room_type: str, season: str = "Medium") -> float:
        """Get the base price for a specific property and room type."""
        if not cls.RATES:
            cls.load_rates()
        
        if property_name not in cls.RATES:
            raise HTTPException(status_code=404, detail=f"Property {property_name} not found")
            
        if room_type not in cls.RATES[property_name]:
            raise HTTPException(status_code=404, detail=f"Room type {room_type} not found")
            
        if season not in cls.RATES[property_name][room_type]:
            raise HTTPException(status_code=400, detail=f"Invalid season: {season}")
            
        return float(cls.RATES[property_name][room_type][season])

    @classmethod
    def get_room_capacity(cls, property_name: str, room_type: str) -> int:
        """Get the capacity for a specific room type."""
        if not cls.RATES:
            cls.load_rates()
            
        return cls.RATES[property_name][room_type]["capacity"]

    @classmethod
    def apply_capacity_surcharge(cls, price: float, capacity: int, max_capacity: int) -> float:
        """Apply capacity surcharge for 2 persons if within room capacity."""
        if not cls.DISCOUNTS:
            cls.load_discounts()
            
        if capacity > max_capacity:
            raise HTTPException(
                status_code=400, 
                detail=f"Requested capacity {capacity} exceeds room capacity {max_capacity}"
            )
            
        return price * (1 + cls.DISCOUNTS["capacity_surcharge"]) if capacity == 2 else price

    @staticmethod
    def apply_manual_discount(price: float, discount_percentage: float) -> float:
        """Apply manual discount percentage."""
        if not 0 <= discount_percentage <= 100:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid discount percentage: {discount_percentage}. Must be between 0 and 100."
            )
        return price * (1 - (discount_percentage / 100))

    @classmethod
    def apply_vat(cls, price: float) -> float:
        """Apply VAT."""
        if not cls.DISCOUNTS:
            cls.load_discounts()
        return price * (1 + cls.DISCOUNTS["vat_rate"])

    @staticmethod
    def validate_extension_rule(check_in: datetime, original_checkout: datetime) -> bool:
        """Validate 7-day extension rule."""
        return (check_in - original_checkout).days <= 7

    @classmethod
    def calculate_room_period(
        cls,
        property_name: str,
        room_period: dict,
        season: str,
        long_stay_discount: float
    ) -> dict:
        """Calculate price for a single room period."""
        # Get base price and validate room exists
        base_price = cls.get_base_price(property_name, room_period["room_type"], season)
        
        # Get room capacity
        max_capacity = cls.get_room_capacity(property_name, room_period["room_type"])
        
        # Calculate nights
        nights = (room_period["check_out"] - room_period["check_in"]).days
        if nights <= 0:
            raise HTTPException(
                status_code=400,
                detail="Check-out date must be after check-in date"
            )
        
        # Apply capacity surcharge if needed
        adjusted_price = cls.apply_capacity_surcharge(base_price, room_period["capacity"], max_capacity)
        
        # Apply long stay discount
        if long_stay_discount > 0:
            adjusted_price *= (1 - long_stay_discount)
        
        return {
            "room_type": room_period["room_type"],
            "nights": nights,
            "base_price_per_night": base_price,
            "adjusted_price_per_night": adjusted_price,
            "subtotal": adjusted_price * nights,
            "capacity": room_period["capacity"],
            "max_capacity": max_capacity
        }

    @classmethod
    def calculate_total_price(
        cls,
        property_name: str,
        calculation_type: str,
        room_periods: List[dict],
        season: str = "Medium",
        manual_discount: float = 0.0,
        override_extension_rule: bool = False,
        original_checkout: Optional[datetime] = None
    ) -> Dict:
        """Calculate the total price with all applicable adjustments."""
        if not cls.RATES:
            cls.load_rates()

        warnings = []
        errors = []
        
        # Validate property exists
        if property_name not in cls.RATES:
            raise HTTPException(status_code=404, detail=f"Property {property_name} not found")
        
        # Validate extension rule if applicable
        if calculation_type == "extension" and not override_extension_rule and original_checkout:
            if not cls.validate_extension_rule(room_periods[0]["check_in"], original_checkout):
                warnings.append("Extension exceeds 7-day rule. Manual override required.")

        # Calculate total nights across all periods
        total_nights = sum((period["check_out"] - period["check_in"]).days for period in room_periods)
        if total_nights <= 0:
            raise HTTPException(status_code=400, detail="Total stay duration must be positive")
        
        # Calculate long stay discount based on total stay duration
        long_stay_discount = cls.calculate_long_stay_discount(total_nights)
        
        # Calculate breakdown for each room period
        room_breakdowns = []
        subtotal = 0
        
        for period in room_periods:
            try:
                breakdown = cls.calculate_room_period(
                    property_name,
                    period,
                    season,
                    long_stay_discount
                )
                room_breakdowns.append(breakdown)
                subtotal += breakdown["subtotal"]
            except HTTPException as e:
                errors.append(f"Error calculating period for {period['room_type']}: {e.detail}")
        
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        # Apply manual discount if any
        if manual_discount > 0:
            subtotal = cls.apply_manual_discount(subtotal, manual_discount)

        # Calculate VAT
        total_with_vat = cls.apply_vat(subtotal)
        
        return {
            "property": property_name,
            "calculation_type": calculation_type,
            "season": season,
            "room_breakdowns": room_breakdowns,
            "total_nights": total_nights,
            "long_stay_discount_percentage": long_stay_discount * 100,
            "manual_discount_percentage": manual_discount,
            "subtotal": subtotal,
            "vat_amount": total_with_vat - subtotal,
            "total_price": total_with_vat,
            "warnings": warnings
        }

    @staticmethod
    def apply_long_stay_discount(price: float, number_of_nights: int) -> float:
        """Apply long-stay discount based on duration."""
        if number_of_nights >= 29:
            return price * 0.50  # 50% discount for 29+ nights
        elif number_of_nights >= 19:
            return price * 0.65  # 35% discount for 19-28 nights
        elif number_of_nights >= 9:
            return price * 0.80  # 20% discount for 9-18 nights
        return price  # No discount for less than 9 nights 