import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { differenceInDays, isWithinDays } from 'date-fns';
import Summary from './components/Summary';
import { RATES_DATA } from './constants/rates';

const theme = createTheme({
  palette: {
    primary: {
      main: '#007AFF', // Apple blue
    },
    background: {
      default: '#f5f5f7', // Apple light gray
      paper: '#ffffff',
    },
    text: {
      primary: '#1d1d1f', // Apple dark gray
    }
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    h4: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
    subtitle1: {
      fontSize: '0.9375rem',
      fontWeight: 500,
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          borderRadius: '12px',
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          backgroundColor: 'white',
          borderRadius: '8px',
          '& fieldset': {
            borderColor: '#e1e1e6',
          },
          '&:hover fieldset': {
            borderColor: '#b8b8bf !important',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          backgroundColor: 'white',
          borderRadius: '8px',
          '& fieldset': {
            borderColor: '#e1e1e6',
          },
          '&:hover fieldset': {
            borderColor: '#b8b8bf !important',
          },
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          fontSize: '0.8125rem',
          color: '#86868b',
          '&.Mui-focused': {
            color: '#007AFF',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          textTransform: 'none',
          fontWeight: 500,
          fontSize: '0.9375rem',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        outlined: {
          borderColor: '#e1e1e6',
          color: '#1d1d1f',
          '&:hover': {
            borderColor: '#b8b8bf',
            backgroundColor: 'transparent',
          },
        },
        contained: {
          backgroundColor: '#007AFF',
          '&:hover': {
            backgroundColor: '#0066d9',
          },
        },
      },
    },
  },
});

function App() {
  const [roomPeriods, setRoomPeriods] = useState([
    {
      id: 1,
      roomType: '',
      capacity: '1',
      checkIn: null,
      checkOut: null,
      season: 'High',
    }
  ]);
  const [formData, setFormData] = useState({
    property: '',
    calculationType: 'new',
    extraDiscount: 0,
    checkIn: null,      // For new bookings
    checkOut: null,     // For new bookings
    originalCheckIn: null,     // For extensions
    originalCheckOut: null,    // For extensions
    extendedCheckOut: null,   // New field for extension end date
    overrideSevenDayRule: false,
    amountPaid: 0,     // New field for amount already paid
  });
  const [calculation, setCalculation] = useState(null);

  const handleChange = (field) => (event) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleRoomPeriodChange = (index, field, value) => {
    setRoomPeriods(prev => {
      const newPeriods = [...prev];
      newPeriods[index] = {
        ...newPeriods[index],
        [field]: value
      };
      return newPeriods;
    });
  };

  const addRoomPeriod = () => {
    const lastPeriod = roomPeriods[roomPeriods.length - 1];
    setRoomPeriods(prev => [
      ...prev,
      {
        id: prev.length + 1,
        roomType: '',
        capacity: '1',
        checkIn: lastPeriod?.checkOut || null,
        checkOut: null,
        season: 'High',
      }
    ]);
  };

  const getRoomTypes = () => {
    if (!formData.property) return [];
    return RATES_DATA[formData.property].roomTypes || [];
  };

  // Helper function to get long-stay discount
  const getLongStayDiscount = (totalNights, originalCheckIn, isExtension) => {
    // If override is ON, don't include original stay in total nights calculation
    if (isExtension && formData.overrideSevenDayRule) {
      // Only use extension nights for discount calculation
      const extensionNights = differenceInDays(
        new Date(formData.checkOut),
        new Date(formData.originalCheckOut)
      );
      if (extensionNights >= 29) return 0.50;
      if (extensionNights >= 19) return 0.35;
      if (extensionNights >= 9) return 0.20;
      return 0;
    }

    // Normal discount calculation using total nights
    if (totalNights >= 29) return 0.50;
    if (totalNights >= 19) return 0.35;
    if (totalNights >= 9) return 0.20;
    return 0;
  };

  const calculateTotal = () => {
    const isExtension = formData.calculationType === 'extension';
    
    // Validate inputs based on calculation type
    if (!formData.property) {
      alert('Please select a property');
      return;
    }

    if (isExtension) {
      if (!formData.originalCheckIn || !formData.originalCheckOut || !formData.checkOut) {
        alert('Please fill in all required dates');
        return;
      }
      // Validate room periods
      if (roomPeriods.some(p => !p.roomType || !p.capacity)) {
        alert('Please fill in room type and capacity');
        return;
      }
    } else {
      // New booking validation
      if (roomPeriods.some(p => !p.roomType || !p.checkIn || !p.checkOut || !p.capacity || !p.season)) {
        alert('Please fill in all room period details');
        return;
      }
    }

    // Calculate total nights from original check-in to extended check-out for extensions
    let totalNights = 0;
    if (isExtension) {
      totalNights = differenceInDays(
        new Date(formData.checkOut),
        new Date(formData.originalCheckIn)
      );
    } else {
      // For new bookings, sum up all room periods
      totalNights = roomPeriods.reduce((sum, period) => {
        const nights = differenceInDays(new Date(period.checkOut), new Date(period.checkIn));
        return sum + nights;
      }, 0);
    }

    // Get long-stay discount based on total nights
    const longStayDiscount = getLongStayDiscount(
      totalNights,
      formData.originalCheckIn,
      isExtension
    );

    // Calculate for extension period only
    const results = roomPeriods.map(period => {
      // For extensions, use originalCheckIn as start date and checkOut as end date
      const startDate = isExtension ? new Date(formData.originalCheckIn) : new Date(period.checkIn);
      const endDate = isExtension ? new Date(formData.checkOut) : new Date(period.checkOut);
      const nights = differenceInDays(endDate, startDate);
      const baseRate = RATES_DATA[formData.property][period.season][period.roomType];
      
      let rate = baseRate;
      if (period.capacity === '2') {
        rate *= 1.2;
      }
      rate *= (1 - longStayDiscount);

      return {
        ...period,
        checkIn: startDate,
        checkOut: endDate,
        nights,
        baseRate,
        rate,
        subtotal: rate * nights
      };
    });

    // Calculate totals
    const subtotal = results.reduce((sum, r) => sum + r.subtotal, 0);
    const extraDiscount = subtotal * (formData.extraDiscount / 100);
    const totalBeforeVat = subtotal - extraDiscount;
    const vat = totalBeforeVat * 0.07;
    const grandTotal = totalBeforeVat + vat;
    const remainingAmount = isExtension ? grandTotal - Number(formData.amountPaid) : grandTotal;

    setCalculation({
      periods: results,
      subtotal,
      extraDiscount,
      vat,
      grandTotal,
      remainingAmount,
      amountPaid: Number(formData.amountPaid),
      longStayDiscount: longStayDiscount * 100,
      totalNights,
      originalNights: isExtension ? differenceInDays(
        new Date(formData.originalCheckOut),
        new Date(formData.originalCheckIn)
      ) : 0
    });
  };

  const renderRoomPeriod = (period, index) => (
    <Box key={period.id} sx={{ mb: 1.5 }}>
      <Typography variant="subtitle1" sx={{ mb: 1, color: '#1d1d1f' }}>
        Room Period {index + 1}
      </Typography>
      <Grid container spacing={1}>
        <Grid item xs={12}>
          <FormControl fullWidth size="small">
            <InputLabel>Room Type</InputLabel>
            <Select
              value={period.roomType}
              label="Room Type"
              onChange={(e) => handleRoomPeriodChange(index, 'roomType', e.target.value)}
            >
              {getRoomTypes().map((type) => (
                <MenuItem key={type} value={type}>{type}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12}>
          <FormControl fullWidth size="small">
            <InputLabel>Season</InputLabel>
            <Select
              value={period.season}
              label="Season"
              onChange={(e) => handleRoomPeriodChange(index, 'season', e.target.value)}
            >
              <MenuItem value="Rack">Rack Rate</MenuItem>
              <MenuItem value="High">High Season</MenuItem>
              <MenuItem value="Medium">Medium Season</MenuItem>
              <MenuItem value="Low">Low Season</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12}>
          <FormControl fullWidth size="small">
            <InputLabel>Capacity</InputLabel>
            <Select
              value={period.capacity}
              label="Capacity"
              onChange={(e) => handleRoomPeriodChange(index, 'capacity', e.target.value)}
            >
              <MenuItem value="1">1 Person</MenuItem>
              <MenuItem value="2">2 Persons (+20%)</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={6}>
          <DatePicker
            label="Check-in Date"
            value={period.checkIn}
            onChange={(date) => handleRoomPeriodChange(index, 'checkIn', date)}
            renderInput={(params) => <TextField {...params} fullWidth size="small" />}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <DatePicker
            label="Check-out Date"
            value={period.checkOut}
            onChange={(date) => handleRoomPeriodChange(index, 'checkOut', date)}
            renderInput={(params) => <TextField {...params} fullWidth size="small" />}
          />
        </Grid>
      </Grid>
    </Box>
  );

  const handleDateChange = (field) => (date) => {
    setFormData(prev => ({
      ...prev,
      [field]: date
    }));
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Container maxWidth="md" sx={{ mt: 2, mb: 2 }}>
          <Typography variant="h4" align="center" gutterBottom>Alt Calculator</Typography>
          <Paper elevation={1} sx={{ p: 3, borderRadius: 2 }}>
            <Grid container spacing={1.5}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Property</InputLabel>
                  <Select value={formData.property} label="Property" onChange={handleChange('property')}>
                    <MenuItem value="Alt_CM">Alt Chiang Mai</MenuItem>
                    <MenuItem value="Alt_PR">Alt Ping River</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Calculation Type</InputLabel>
                  <Select value={formData.calculationType} label="Calculation Type" onChange={handleChange('calculationType')}>
                    <MenuItem value="new">New Booking</MenuItem>
                    <MenuItem value="extension">Booking Extension</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {formData.calculationType === 'new' && (
                <>
                  {roomPeriods.map((period, index) => renderRoomPeriod(period, index))}
                  <Grid item xs={12}>
                    <Button onClick={addRoomPeriod} variant="outlined" fullWidth>
                      Add Room Period
                    </Button>
                  </Grid>
                </>
              )}

              {formData.calculationType === 'extension' && (
                <Grid container spacing={1.5} sx={{ mt: 1 }}>
                  <Grid item xs={12} md={6}>
                    <DatePicker
                      label="Original Check-in Date"
                      value={formData.originalCheckIn}
                      onChange={(date) => handleDateChange('originalCheckIn')(date)}
                      renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <DatePicker
                      label="Original Check-out Date"
                      value={formData.originalCheckOut}
                      onChange={(date) => handleDateChange('originalCheckOut')(date)}
                      renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <DatePicker
                      label="Extended Check-out Date"
                      value={formData.checkOut}
                      onChange={(date) => handleDateChange('checkOut')(date)}
                      renderInput={(params) => <TextField {...params} fullWidth size="small" />}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Amount Already Paid (฿)"
                      type="number"
                      value={formData.amountPaid}
                      onChange={handleChange('amountPaid')}
                      InputProps={{ inputProps: { min: 0 } }}
                    />
                  </Grid>
                  
                  {roomPeriods.map((period, index) => (
                    <React.Fragment key={period.id}>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Room Type</InputLabel>
                          <Select
                            value={period.roomType}
                            label="Room Type"
                            onChange={(e) => handleRoomPeriodChange(index, 'roomType', e.target.value)}
                          >
                            {getRoomTypes().map((type) => (
                              <MenuItem key={type} value={type}>{type}</MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Season</InputLabel>
                          <Select
                            value={period.season}
                            label="Season"
                            onChange={(e) => handleRoomPeriodChange(index, 'season', e.target.value)}
                          >
                            <MenuItem value="Rack">Rack Rate</MenuItem>
                            <MenuItem value="High">High Season</MenuItem>
                            <MenuItem value="Medium">Medium Season</MenuItem>
                            <MenuItem value="Low">Low Season</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Capacity</InputLabel>
                          <Select
                            value={period.capacity}
                            label="Capacity"
                            onChange={(e) => handleRoomPeriodChange(index, 'capacity', e.target.value)}
                          >
                            <MenuItem value="1">1 Person</MenuItem>
                            <MenuItem value="2">2 Persons (+20%)</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                    </React.Fragment>
                  ))}

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={formData.overrideSevenDayRule}
                          onChange={(e) => handleChange('overrideSevenDayRule')({ target: { value: e.target.checked } })}
                        />
                      }
                      label="Disable Including Original Stay for Long-Stay Discount"
                    />
                  </Grid>
                </Grid>
              )}

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Extra Discount (%)"
                  type="number"
                  value={formData.extraDiscount}
                  onChange={handleChange('extraDiscount')}
                  InputProps={{ inputProps: { min: 0, max: 100 } }}
                />
              </Grid>
            </Grid>

            <Button
              variant="contained"
              fullWidth
              onClick={calculateTotal}
              sx={{ mt: 3, py: 1.25 }}
            >
              Calculate
            </Button>
          </Paper>

          {calculation && <Summary calculation={calculation} formData={formData} />}
        </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;
