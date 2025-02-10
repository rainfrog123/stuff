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
} from '@mui/material';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

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
    }
  ]);
  const [formData, setFormData] = useState({
    property: '',
    calculationType: 'new',
    season: 'High',
    extraDiscount: 0,
  });
  const [rates, setRates] = useState(null);

  useEffect(() => {
    fetch('http://localhost:5000/api/rates')
      .then(res => res.json())
      .then(data => setRates(data))
      .catch(err => console.error('Error fetching rates:', err));
  }, []);

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
      }
    ]);
  };

  const getRoomTypes = () => {
    if (!rates || !formData.property) return [];
    return rates[formData.property].roomTypes.map(type => 
      type.replace(/\s*\(\d+\)$/, '')
    ) || [];
  };

  const renderRoomPeriod = (period, index) => (
    <Box key={period.id} sx={{ mb: 1.5 }}>
      <Typography 
        variant="subtitle1" 
        sx={{ 
          mb: 1,
          color: '#1d1d1f',
        }}
      >
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
              MenuProps={{
                PaperProps: {
                  sx: {
                    borderRadius: '8px',
                    mt: 0.5,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                  },
                },
              }}
            >
              {getRoomTypes().map((type) => (
                <MenuItem key={type} value={type}>{type}</MenuItem>
              ))}
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
              MenuProps={{
                PaperProps: {
                  sx: {
                    borderRadius: '8px',
                    mt: 0.5,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                  },
                },
              }}
            >
              <MenuItem value="1">1 Person</MenuItem>
              <MenuItem value="2">2 Persons</MenuItem>
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

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Container maxWidth="md" sx={{ mt: 2, mb: 2 }}>
          <Typography variant="h4" component="h1" align="center" sx={{ mb: 2 }}>
            Alt Calculator
          </Typography>

          <Paper>
            <Grid container spacing={1.5}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Property</InputLabel>
                  <Select
                    value={formData.property}
                    label="Property"
                    onChange={handleChange('property')}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          borderRadius: '8px',
                          mt: 0.5,
                          boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                        },
                      },
                    }}
                  >
                    <MenuItem value="Alt_CM">Alt Chiang Mai</MenuItem>
                    <MenuItem value="Alt_PR">Alt Ping River</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Calculation Type</InputLabel>
                  <Select
                    value={formData.calculationType}
                    label="Calculation Type"
                    onChange={handleChange('calculationType')}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          borderRadius: '8px',
                          mt: 0.5,
                          boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                        },
                      },
                    }}
                  >
                    <MenuItem value="new">New Booking</MenuItem>
                    <MenuItem value="extension">Booking Extension</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                {roomPeriods.map((period, index) => renderRoomPeriod(period, index))}
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="outlined"
                  onClick={addRoomPeriod}
                  disabled={roomPeriods.length >= 3}
                  size="small"
                  sx={{ 
                    py: 0.75,
                    fontSize: '0.8125rem',
                  }}
                >
                  Add Room Period
                </Button>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Season</InputLabel>
                  <Select
                    value={formData.season}
                    label="Season"
                    onChange={handleChange('season')}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          borderRadius: '8px',
                          mt: 0.5,
                          boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                        },
                      },
                    }}
                  >
                    <MenuItem value="High">High Season</MenuItem>
                    <MenuItem value="Medium">Medium Season</MenuItem>
                    <MenuItem value="Low">Low Season</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Extra Discount (%)"
                  type="number"
                  value={formData.extraDiscount}
                  onChange={handleChange('extraDiscount')}
                  inputProps={{ min: 0, max: 15 }}
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  fullWidth
                  sx={{ 
                    mt: 0.5,
                    py: 1.25,
                  }}
                >
                  Calculate
                </Button>
              </Grid>
            </Grid>
          </Paper>
        </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;
