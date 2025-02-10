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
  FormControlLabel,
  Switch,
  Button,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format } from 'date-fns';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [formData, setFormData] = useState({
    property: '',
    calculationType: 'new',
    checkIn: null,
    checkOut: null,
    capacity: '1',
    roomType: '',
    extraDiscount: 0,
    hasRoomChange: false,
    roomChanges: [],
    originalCheckIn: null,
    originalCheckOut: null,
    overrideSevenDayRule: false
  });
  const [rates, setRates] = useState(null);
  const [calculation, setCalculation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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

  const handleDateChange = (field) => (date) => {
    setFormData(prev => ({
      ...prev,
      [field]: date
    }));
  };

  const handleSwitchChange = (field) => (event) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.checked
    }));
  };

  const getRoomTypes = () => {
    if (!rates || !formData.property) return [];
    return rates[formData.property].roomTypes || [];
  };

  const isExtension = formData.calculationType === 'extension';

  const calculatePrice = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:5000/api/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to calculate price');
      }

      const result = await response.json();
      setCalculation(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (date) => {
    return format(new Date(date), 'dd MMM yyyy');
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('th-TH', {
      style: 'currency',
      currency: 'THB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h4" component="h1" gutterBottom align="center">
              Alt Calculator
            </Typography>
            
            <Grid container spacing={3}>
              {/* Left side - Input parameters */}
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
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

                  <FormControl fullWidth>
                    <InputLabel>Calculation Type</InputLabel>
                    <Select
                      value={formData.calculationType}
                      label="Calculation Type"
                      onChange={handleChange('calculationType')}
                    >
                      <MenuItem value="new">New Booking</MenuItem>
                      <MenuItem value="extension">Booking Extension</MenuItem>
                      <MenuItem value="change">New Booking with Room Type Change</MenuItem>
                    </Select>
                  </FormControl>

                  {isExtension && (
                    <>
                      <DatePicker
                        label="Original Check-in Date"
                        value={formData.originalCheckIn}
                        onChange={handleDateChange('originalCheckIn')}
                        renderInput={(params) => <TextField {...params} fullWidth />}
                      />
                      <DatePicker
                        label="Original Check-out Date"
                        value={formData.originalCheckOut}
                        onChange={handleDateChange('originalCheckOut')}
                        renderInput={(params) => <TextField {...params} fullWidth />}
                      />
                    </>
                  )}

                  <DatePicker
                    label={isExtension ? "New Check-out Date" : "Check-in Date"}
                    value={isExtension ? formData.checkOut : formData.checkIn}
                    onChange={handleDateChange(isExtension ? 'checkOut' : 'checkIn')}
                    renderInput={(params) => <TextField {...params} fullWidth />}
                  />

                  {!isExtension && (
                    <DatePicker
                      label="Check-out Date"
                      value={formData.checkOut}
                      onChange={handleDateChange('checkOut')}
                      renderInput={(params) => <TextField {...params} fullWidth />}
                    />
                  )}

                  <FormControl fullWidth>
                    <InputLabel>Capacity</InputLabel>
                    <Select
                      value={formData.capacity}
                      label="Capacity"
                      onChange={handleChange('capacity')}
                    >
                      <MenuItem value="1">1 Person</MenuItem>
                      <MenuItem value="2">2 Persons</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth>
                    <InputLabel>Room Type</InputLabel>
                    <Select
                      value={formData.roomType}
                      label="Room Type"
                      onChange={handleChange('roomType')}
                    >
                      {getRoomTypes().map((type) => (
                        <MenuItem key={type} value={type}>{type}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <TextField
                    fullWidth
                    label="Extra Discount (%)"
                    type="number"
                    value={formData.extraDiscount}
                    onChange={handleChange('extraDiscount')}
                    inputProps={{ min: 0, max: 15 }}
                  />

                  {isExtension && (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={formData.overrideSevenDayRule}
                          onChange={handleSwitchChange('overrideSevenDayRule')}
                        />
                      }
                      label="Override 7-Day Rule for Long-Stay Discount"
                    />
                  )}

                  <Button
                    variant="contained"
                    onClick={calculatePrice}
                    disabled={!formData.property || !formData.roomType || 
                             (!isExtension && (!formData.checkIn || !formData.checkOut)) ||
                             (isExtension && (!formData.originalCheckIn || !formData.originalCheckOut || !formData.checkOut))}
                    size="large"
                  >
                    Calculate
                  </Button>
                </Box>
              </Grid>

              {/* Right side - Results */}
              <Grid item xs={12} md={6}>
                {loading ? (
                  <Typography>Calculating...</Typography>
                ) : error ? (
                  <Typography color="error">Error: {error}</Typography>
                ) : calculation ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <Typography variant="h6">Booking Summary</Typography>

                    <TableContainer>
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell>Period</TableCell>
                            <TableCell>Room Type</TableCell>
                            <TableCell>Nights</TableCell>
                            <TableCell align="right">Rate</TableCell>
                            <TableCell align="right">Subtotal</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {calculation.periods?.map((period, index) => (
                            <TableRow key={index}>
                              <TableCell>
                                {formatDate(period.startDate)} - {formatDate(period.endDate)}
                              </TableCell>
                              <TableCell>{period.roomType}</TableCell>
                              <TableCell>{period.nights}</TableCell>
                              <TableCell align="right">{formatCurrency(period.rate)}</TableCell>
                              <TableCell align="right">{formatCurrency(period.subtotal)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    <Box>
                      <Typography>
                        Capacity: {formData.capacity} {formData.capacity === '2' && '(+20% surcharge)'}
                      </Typography>
                      {calculation.longStayDiscount > 0 && (
                        <Typography>
                          Long-stay Discount: {calculation.longStayDiscount}%
                        </Typography>
                      )}
                      {formData.extraDiscount > 0 && (
                        <Typography>
                          Extra Discount: {formData.extraDiscount}%
                        </Typography>
                      )}
                    </Box>

                    <Divider />

                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Typography>
                        Subtotal: {formatCurrency(calculation.subtotal)}
                      </Typography>
                      <Typography>
                        VAT (7%): {formatCurrency(calculation.vat)}
                      </Typography>
                      <Typography variant="h6">
                        Total: {formatCurrency(calculation.total)}
                      </Typography>
                    </Box>

                    <Button
                      variant="outlined"
                      onClick={() => window.print()}
                      fullWidth
                    >
                      Print
                    </Button>
                  </Box>
                ) : (
                  <Typography color="text.secondary" align="center">
                    Enter booking details and click Calculate to see the results
                  </Typography>
                )}
              </Grid>
            </Grid>
          </Paper>
        </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;
