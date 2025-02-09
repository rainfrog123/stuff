from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import BookingCalculationRequest, PriceCalculationResponse
from .pricing import PricingCalculator
from app.routes import rates

app = FastAPI(
    title="Alt Booking Calculator API",
    description="API for calculating booking prices for Alt properties",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include rate management routes
app.include_router(rates.router, prefix="/api")

# Initialize rates on startup
@app.on_event("startup")
async def startup_event():
    PricingCalculator.load_rates()

@app.get("/")
async def read_root():
    return {"message": "Welcome to Alt Booking Calculator API"}

@app.get("/properties")
async def get_properties():
    """Get available properties and their room types."""
    return {
        "properties": {
            "Alt_CM": ["Flexie", "Flexie Plus", "Ensuite Single"],
            "Alt_PR": ["Flexie", "Ensuite Standard", "Ensuite King"]
        }
    }

@app.get("/seasons")
async def get_seasons():
    """Get available seasons and their rates."""
    return {
        "seasons": {
            "High": "+20%",
            "Medium": "Standard Rate",
            "Low": "-20%"
        }
    }

@app.post("/calculate", response_model=PriceCalculationResponse)
async def calculate_price(request: BookingCalculationRequest):
    # Load rates if not already loaded
    if not PricingCalculator.RATES:
        PricingCalculator.load_rates()
        
    # Validate property exists
    if request.property_name not in PricingCalculator.RATES:
        raise HTTPException(status_code=422, detail=f"Invalid property name: {request.property_name}")
    
    # Validate room types
    for period in request.room_periods:
        if period.room_type not in PricingCalculator.RATES[request.property_name]:
            raise HTTPException(status_code=422, detail=f"Invalid room type: {period.room_type}")

    # Calculate price
    result = PricingCalculator.calculate_total_price(
        property_name=request.property_name,
        calculation_type=request.calculation_type,
        room_periods=[{
            "room_type": period.room_type,
            "check_in": period.check_in,
            "check_out": period.check_out,
            "capacity": period.capacity
        } for period in request.room_periods],
        season=request.season,
        manual_discount=request.manual_discount,
        override_extension_rule=request.override_extension_rule
    )
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 