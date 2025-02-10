const express = require('express');
const cors = require('cors');
const fs = require('fs');
const { parse } = require('csv-parse');
const path = require('path');
const { differenceInDays, addDays, isBefore, isAfter } = require('date-fns');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Function to parse rates from CSV
const parseRates = async () => {
  const rates = {
    Alt_CM: {},
    Alt_PR: {}
  };

  return new Promise((resolve, reject) => {
    fs.createReadStream(path.join(__dirname, '../Alt_ Rates for Calculator App - Sheet1.csv'))
      .pipe(parse({ delimiter: ',' }))
      .on('data', (row) => {
        if (row[0] === 'Alt_ChiangMai') {
          const roomTypes = row.slice(1).filter(Boolean);
          rates.Alt_CM.roomTypes = roomTypes;
        } else if (row[0] === 'Alt_PingRiver') {
          const roomTypes = row.slice(1).filter(Boolean);
          rates.Alt_PR.roomTypes = roomTypes;
        } else if (row[0] === 'Rack' || row[0] === 'High' || row[0] === 'Medium' || row[0] === 'Low') {
          const season = row[0];
          const values = row.slice(1).map(rate => parseFloat(rate.replace(/,/g, '')));
          
          if (rates.Alt_CM.roomTypes && !rates.Alt_CM[season]) {
            rates.Alt_CM[season] = {};
            rates.Alt_CM.roomTypes.forEach((type, index) => {
              rates.Alt_CM[season][type] = values[index];
            });
          } else if (rates.Alt_PR.roomTypes && !rates.Alt_PR[season]) {
            rates.Alt_PR[season] = {};
            rates.Alt_PR.roomTypes.forEach((type, index) => {
              rates.Alt_PR[season][type] = values[index];
            });
          }
        }
      })
      .on('end', () => resolve(rates))
      .on('error', reject);
  });
};

// Helper function to get room rate
const getRoomRate = (rates, property, roomType, season = 'Medium') => {
  return rates[property][season][roomType];
};

// Helper function to calculate long-stay discount
const getLongStayDiscount = (nights) => {
  if (nights >= 29) return 50;
  if (nights >= 19) return 35;
  if (nights >= 9) return 20;
  return 0;
};

// Helper function to calculate periods for a booking
const calculatePeriods = (formData, rates) => {
  const periods = [];
  let currentDate = new Date(formData.checkIn);
  const endDate = new Date(formData.checkOut);
  
  // Initial period
  let currentPeriod = {
    startDate: currentDate,
    roomType: formData.roomType,
    capacity: formData.capacity
  };

  // Sort room changes by date
  const sortedChanges = formData.roomChanges
    ? [...formData.roomChanges].sort((a, b) => new Date(a.date) - new Date(b.date))
    : [];

  // Process each room change
  for (const change of sortedChanges) {
    const changeDate = new Date(change.date);
    
    // Close current period
    currentPeriod.endDate = changeDate;
    currentPeriod.nights = differenceInDays(currentPeriod.endDate, currentPeriod.startDate);
    periods.push(currentPeriod);

    // Start new period
    currentPeriod = {
      startDate: changeDate,
      endDate: null,
      roomType: change.roomType,
      capacity: change.capacity || formData.capacity
    };
  }

  // Close final period
  currentPeriod.endDate = endDate;
  currentPeriod.nights = differenceInDays(currentPeriod.endDate, currentPeriod.startDate);
  periods.push(currentPeriod);

  return periods;
};

// Endpoint to get rates
app.get('/api/rates', async (req, res) => {
  try {
    const rates = await parseRates();
    res.json(rates);
  } catch (error) {
    res.status(500).json({ error: 'Failed to parse rates' });
  }
});

// Calculate pricing endpoint
app.post('/api/calculate', async (req, res) => {
  try {
    const rates = await parseRates();
    const {
      property,
      roomType,
      checkIn,
      checkOut,
      capacity,
      extraDiscount,
      roomChanges,
      calculationType,
      originalCheckIn,
      overrideSevenDayRule
    } = req.body;

    // Calculate periods
    const periods = calculatePeriods(req.body, rates);

    // Calculate total nights for long-stay discount
    const totalNights = periods.reduce((sum, period) => sum + period.nights, 0);
    
    // Determine if long-stay discount applies
    let applyLongStayDiscount = false;
    if (calculationType === 'extension') {
      if (overrideSevenDayRule) {
        applyLongStayDiscount = true;
      } else {
        const daysSinceCheckIn = differenceInDays(new Date(), new Date(originalCheckIn));
        applyLongStayDiscount = daysSinceCheckIn <= 7;
      }
    } else {
      applyLongStayDiscount = true;
    }

    const longStayDiscount = applyLongStayDiscount ? getLongStayDiscount(totalNights) : 0;

    // Calculate price for each period
    let subtotal = 0;
    periods.forEach(period => {
      const baseRate = getRoomRate(rates, property, period.roomType);
      let rate = baseRate;

      // Apply capacity surcharge
      if (period.capacity === '2') {
        rate *= 1.2;
      }

      // Apply long-stay discount
      if (applyLongStayDiscount) {
        rate *= (1 - longStayDiscount / 100);
      }

      // Apply extra discount
      if (extraDiscount > 0) {
        rate *= (1 - extraDiscount / 100);
      }

      period.rate = rate;
      period.subtotal = rate * period.nights;
      subtotal += period.subtotal;
    });

    // Calculate VAT
    const vat = subtotal * 0.07;
    const total = subtotal + vat;

    res.json({
      periods,
      subtotal,
      vat,
      total,
      longStayDiscount: applyLongStayDiscount ? longStayDiscount : 0
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to calculate price' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 