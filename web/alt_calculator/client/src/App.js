import React, { useState } from 'react';
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
  Divider,
  IconButton,
} from '@mui/material';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { differenceInDays, startOfToday } from 'date-fns';
import Summary from './components/Summary';
import { RATES_DATA } from './constants/rates';
import DeleteIcon from '@mui/icons-material/Delete';

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
    h6: {
      fontSize: '1.125rem',
      fontWeight: 500,
      color: '#1d1d1f',
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
          padding: '24px',
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
          padding: '8px 16px',
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
            backgroundColor: 'rgba(0,0,0,0.02)',
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
    MuiDivider: {
      styleOverrides: {
        root: {
          margin: '24px 0',
          borderColor: '#e1e1e6',
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
      checkIn: startOfToday(),
      checkOut: null,
      season: 'High',
    }
  ]);
  const [formData, setFormData] = useState({
    property: '',
    extraDiscount: 0,
    checkIn: null,
    checkOut: null,
    hasRoomChange: false
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

      // If this is a check-out date change, update the next period's check-in date
      if (field === 'checkOut' && index < newPeriods.length - 1) {
        newPeriods[index + 1] = {
          ...newPeriods[index + 1],
          checkIn: value
        };
      }

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
        checkIn: lastPeriod?.checkOut || startOfToday(),
        checkOut: null,
        season: lastPeriod?.season || 'High',
      }
    ]);
  };

  const getRoomTypes = () => {
    if (!formData.property) return [];
    return RATES_DATA[formData.property].roomTypes || [];
  };

  const getLongStayDiscount = (totalNights) => {
    if (totalNights >= 29) return 0.50;
    if (totalNights >= 19) return 0.35;
    if (totalNights >= 9) return 0.20;
    return 0;
  };

  const calculateTotal = () => {
    if (!formData.property) {
      alert('Please select a property');
      return;
    }

    if (roomPeriods.some(p => !p.roomType || !p.checkIn || !p.checkOut || !p.capacity || !p.season)) {
      alert('Please fill in all room period details');
      return;
    }

    const totalNights = roomPeriods.reduce((sum, period) => {
      const nights = differenceInDays(new Date(period.checkOut), new Date(period.checkIn));
      return sum + nights;
    }, 0);

    const longStayDiscount = getLongStayDiscount(totalNights);

    const results = roomPeriods.map(period => {
      const startDate = new Date(period.checkIn);
      const endDate = new Date(period.checkOut);
      const nights = differenceInDays(endDate, startDate);
      const baseRate = RATES_DATA[formData.property][period.season][period.roomType];
      
      let rate = baseRate;
      if (period.capacity === '2') {
        rate *= 1.2;
      }

      return {
        ...period,
        checkIn: startDate,
        checkOut: endDate,
        nights,
        baseRate: rate, // This is the rate after capacity adjustment but before long-stay discount
        rate: rate * (1 - longStayDiscount),
        subtotal: rate * nights
      };
    });

    const subtotalBeforeDiscounts = results.reduce((sum, r) => sum + r.subtotal, 0);
    const longStayDiscountAmount = subtotalBeforeDiscounts * longStayDiscount;
    const subtotalAfterLongStay = subtotalBeforeDiscounts - longStayDiscountAmount;
    const extraDiscount = subtotalAfterLongStay * (formData.extraDiscount / 100);
    const totalBeforeVat = subtotalAfterLongStay - extraDiscount;
    const vat = totalBeforeVat * 0.07;
    const grandTotal = totalBeforeVat + vat;

    setCalculation({
      periods: results,
      subtotalBeforeDiscounts,
      longStayDiscountAmount,
      extraDiscount,
      vat,
      grandTotal,
      longStayDiscount: longStayDiscount * 100,
      totalNights
    });
  };

  const deleteRoomPeriod = (indexToDelete) => {
    setRoomPeriods(prev => prev.filter((_, index) => index !== indexToDelete));
  };

  const renderRoomPeriod = (period, index) => (
    <Box key={period.id} sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, justifyContent: 'space-between' }}>
        <Typography variant="h6">
          Room Period {index + 1}
        </Typography>
        {index > 0 && (
          <IconButton 
            onClick={() => deleteRoomPeriod(index)}
            color="error"
            size="small"
            sx={{ ml: 1 }}
          >
            <DeleteIcon />
          </IconButton>
        )}
      </Box>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
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
          <FormControl fullWidth>
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
          <FormControl fullWidth>
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
          <Box sx={{ display: 'flex', gap: 2 }}>
            <DatePicker
              label="Check-in Date"
              value={period.checkIn}
              onChange={(date) => handleRoomPeriodChange(index, 'checkIn', date)}
              renderInput={(params) => <TextField {...params} fullWidth />}
              minDate={index === 0 ? startOfToday() : roomPeriods[index - 1]?.checkOut || startOfToday()}
            />
            <DatePicker
              label="Check-out Date"
              value={period.checkOut}
              onChange={(date) => handleRoomPeriodChange(index, 'checkOut', date)}
              renderInput={(params) => <TextField {...params} fullWidth />}
              minDate={period.checkIn || startOfToday()}
              disabled={!period.checkIn}
            />
          </Box>
        </Grid>
      </Grid>
      {index < roomPeriods.length - 1 && <Divider sx={{ my: 3 }} />}
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Typography variant="h4" align="center" gutterBottom sx={{ mb: 4 }}>
            Alt Calculator
          </Typography>
          <Paper>
            <Box sx={{ mb: 3 }}>
              <FormControl fullWidth>
                <InputLabel>Property</InputLabel>
                <Select 
                  value={formData.property} 
                  label="Property" 
                  onChange={handleChange('property')}
                >
                  <MenuItem value="Alt_CM">Alt Chiang Mai</MenuItem>
                  <MenuItem value="Alt_PR">Alt Ping River</MenuItem>
                </Select>
              </FormControl>
            </Box>

            {roomPeriods.map((period, index) => renderRoomPeriod(period, index))}
            
            <Box sx={{ mb: 3 }}>
              <Button 
                onClick={addRoomPeriod} 
                variant="outlined" 
                fullWidth
                sx={{ height: 48 }}
              >
                Add Room Period
              </Button>
            </Box>

            <Box sx={{ mb: 3 }}>
              <TextField
                fullWidth
                label="Extra Discount (%)"
                type="number"
                value={formData.extraDiscount}
                onChange={handleChange('extraDiscount')}
                InputProps={{ inputProps: { min: 0, max: 100 } }}
              />
            </Box>

            <Button
              variant="contained"
              fullWidth
              onClick={calculateTotal}
              sx={{ height: 48 }}
            >
              Calculate
            </Button>
          </Paper>

          {calculation && (
            <Box sx={{ mt: 3 }}>
              <Summary calculation={calculation} formData={formData} />
            </Box>
          )}
        </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;
