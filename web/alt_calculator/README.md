# Alt Calculator App

A calculator application for Alt properties with dynamic rate management.

## Features

- Property selection (Alt_CM or Alt_PR)
- Room type selection based on property
- Seasonal rates (High, Medium, Low)
- Booking date selection
- Capacity-based pricing (1 or 2 persons, +20% for 2 persons)
- Long-stay discounts:
  - 15+ days: 20% off
  - 30+ days: 30% off
  - 60+ days: 50% off
- Manual discounts
- Room change options
- Automatic VAT calculation (7%)
- Dynamic rate management through API

## Prerequisites

- Flutter SDK (3.0.0 or higher)
- Dart SDK (2.17.0 or higher)
- A code editor (VS Code, Android Studio, etc.)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
```

2. Navigate to the project directory:
```bash
cd alt_calculator
```

3. Install dependencies:
```bash
flutter pub get
```

4. Run the app:
```bash
flutter run
```

## Usage

1. Select a property (Alt_CM or Alt_PR)
2. Choose the calculation type (New Booking, Extension, or Room Change)
3. Select room type
4. Choose check-in and check-out dates
5. Set the season (High, Medium, Low)
6. Adjust capacity (1 or 2 persons)
7. Apply any manual discounts
8. Toggle long-stay discount if applicable
9. Click "Calculate Price" to see the total

## Pricing Details

### Base Prices
- Alt_CM:
  - Flexie: ฿12,000
  - Flexie Plus: ฿14,000
  - Ensuite Single: ฿16,000
- Alt_PR:
  - Flexie: ฿13,000
  - Ensuite Standard: ฿15,000
  - Ensuite King: ฿17,000

### Rate Adjustments
- Seasonal Rates:
  - High Season: +20%
  - Medium Season: Standard Rate
  - Low Season: -20%
- Capacity:
  - 2 Persons: +20%
- Long-stay Discounts:
  - 15+ days: 20% off
  - 30+ days: 30% off
  - 60+ days: 50% off
- VAT: 7%

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 