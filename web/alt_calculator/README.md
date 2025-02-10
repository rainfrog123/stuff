# Alt Calculator

A booking cost calculator for Alt properties that handles various pricing scenarios including seasonal rates, long-stay discounts, room type changes, and more.

## Features

- Property selection (Alt Chiang Mai or Alt Ping River)
- Multiple calculation types:
  - New bookings
  - Booking extensions
  - Room type changes
- Automatic rate calculation based on:
  - Seasonal rates
  - Room types
  - Capacity (1 or 2 persons)
  - Long-stay discounts
  - Extra discounts
  - VAT
- Support for up to 3 room type changes
- 7-day extension rule with manual override
- Detailed pricing breakdown
- Printable summaries

## Setup

1. Install dependencies for both server and client:

```bash
# Install server dependencies
cd server
npm install

# Install client dependencies
cd ../client
npm install
```

2. Start the server:

```bash
cd server
node server.js
```

3. Start the client:

```bash
cd client
npm start
```

The application will be available at http://localhost:3000

## Usage

1. Select the property (Alt Chiang Mai or Alt Ping River)
2. Choose the calculation type:
   - New Booking
   - Booking Extension
   - New Booking with Room Type Change
3. Fill in the booking details:
   - Check-in/Check-out dates
   - Room type
   - Capacity
   - Extra discounts
4. Add room type changes if needed
5. Review the summary with detailed pricing breakdown
6. Print or save the calculation

## Technical Details

- Frontend: React with Material-UI
- Backend: Node.js with Express
- Rate data stored in CSV format
- Automatic calculation of:
  - Long-stay discounts (9-18 nights: 20%, 19-28 nights: 35%, 29+ nights: 50%)
  - Capacity surcharge (20% for 2 persons)
  - VAT (7%)
  - Extra discounts (5-15%)

## Development

The project uses:
- React 18
- Material-UI for the UI components
- date-fns for date manipulation
- Express.js for the backend API
- CSV parsing for rate data

To modify the rates, update the `Alt_ Rates for Calculator App - Sheet1.csv` file in the root directory. 