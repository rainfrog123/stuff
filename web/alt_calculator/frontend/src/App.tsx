import React, { useState } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Alert,
  ThemeProvider,
  createTheme,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  styled,
  SelectChangeEvent,
  FormLabel,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import axios from 'axios';

const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`;

interface RoomPeriod {
  roomType: string;
  checkIn: Date | null;
  checkOut: Date | null;
  capacity: number;
}

interface PriceResponse {
  room_breakdowns: Array<{
    room_type: string;
    nights: number;
    base_price_per_night: number;
    adjusted_price_per_night: number;
    subtotal: number;
  }>;
  total_nights: number;
  long_stay_discount_percentage: number;
  subtotal: number;
  vat_amount: number;
  total_price: number;
  warnings: string[];
}

const LONG_STAY_TIERS = [
  {
    days: 9,
    discount: 20,
    description: "9-18 nights: 20% discount"
  },
  {
    days: 19,
    discount: 35,
    description: "19-28 nights: 35% discount"
  },
  {
    days: 29,
    discount: 50,
    description: "29+ nights: 50% discount"
  }
];

// Custom theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#2D3250',
      light: '#424769',
    },
    secondary: {
      main: '#676F9D',
    },
    background: {
      default: '#FFFFFF',
      paper: '#F9F9F9',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
        },
      },
    },
  },
});

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  borderRadius: 16,
  boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
  background: 'linear-gradient(145deg, #ffffff 0%, #f9f9f9 100%)',
}));

const ResultCard = styled(Card)(({ theme }) => ({
  background: 'linear-gradient(135deg, #2D3250 0%, #424769 100%)',
  color: 'white',
  marginTop: theme.spacing(3),
}));

export default function App() {
  const [property, setProperty] = useState('');
  const [calculationType, setCalculationType] = useState('new_booking');
  const [roomPeriods, setRoomPeriods] = useState<RoomPeriod[]>([{
    roomType: '',
    checkIn: null,
    checkOut: null,
    capacity: 1,
  }]);
  const [season, setSeason] = useState('Medium');
  const [manualDiscount, setManualDiscount] = useState(0);
  const [isCalculating, setIsCalculating] = useState(false);
  const [result, setResult] = useState<PriceResponse | null>(null);
  const [error, setError] = useState('');

  const availableRoomTypes = property === 'Alt_ChiangMai' 
    ? ['Ensuite Plus (9)', 'Ensuite (10)', 'Ensuite Single (2)', 'Flexie Plus (2)', 'Flexie (4)']
    : ['Ensuite Twin/King (13)', 'Ensuite (9)', 'Ensuite Single (2)', 'Flexie XL (2)', 'Flexie (4)'];

  const handlePropertyChange = (event: SelectChangeEvent) => {
    setProperty(event.target.value);
  };

  const handleCalculationTypeChange = (event: SelectChangeEvent) => {
    setCalculationType(event.target.value);
  };

  const handleRoomTypeChange = (event: SelectChangeEvent, index: number) => {
    const newPeriods = [...roomPeriods];
    newPeriods[index].roomType = event.target.value;
    setRoomPeriods(newPeriods);
  };

  const handleDateChange = (date: Date | null, index: number, field: 'checkIn' | 'checkOut') => {
    const newPeriods = [...roomPeriods];
    newPeriods[index][field] = date;
    setRoomPeriods(newPeriods);
  };

  const handleCapacityChange = (event: SelectChangeEvent<string>, index: number) => {
    const newPeriods = [...roomPeriods];
    newPeriods[index].capacity = Number(event.target.value);
    setRoomPeriods(newPeriods);
  };

  const handleAddRoomPeriod = () => {
    if (roomPeriods.length < 3) {
      setRoomPeriods([...roomPeriods, {
        roomType: '',
        checkIn: null,
        checkOut: null,
        capacity: 1,
      }]);
    }
  };

  const handleRemoveRoomPeriod = (index: number) => {
    if (roomPeriods.length > 1) {
      const newPeriods = roomPeriods.filter((_, i) => i !== index);
      setRoomPeriods(newPeriods);
    }
  };

  const handleCalculate = async () => {
    // Validate required fields
    if (!property) {
      setError('Please select a property');
      return;
    }

    // Validate room periods
    for (const period of roomPeriods) {
      if (!period.roomType) {
        setError('Please select a room type for all periods');
        return;
      }
      if (!period.checkIn || !period.checkOut) {
        setError('Please select check-in and check-out dates for all periods');
        return;
      }
      if (period.checkIn >= period.checkOut) {
        setError('Check-out date must be after check-in date');
        return;
      }
    }

    setIsCalculating(true);
    try {
      const requestData = {
        property_name: property,
        calculation_type: calculationType,
        room_periods: roomPeriods.map(period => ({
          room_type: period.roomType.split(' (')[0], // Remove the capacity number from room type
          check_in: period.checkIn?.toISOString(),
          check_out: period.checkOut?.toISOString(),
          capacity: period.capacity,
        })),
        season,
        manual_discount: manualDiscount,
      };

      console.log('Sending request with data:', requestData);

      const response = await axios.post(`${API_URL}/calculate`, requestData);
      console.log('Received response:', response.data);
      
      setResult(response.data);
      setError('');
    } catch (err: any) {
      console.error('Error details:', err);
      if (err.response) {
        console.error('Response error data:', err.response.data);
        console.error('Response error status:', err.response.status);
        if (err.response.data?.detail) {
          setError(`Error: ${err.response.data.detail}`);
        } else {
          setError(`Server error (${err.response.status}): Please check your inputs and try again.`);
        }
      } else if (err.request) {
        setError('Network error: Could not connect to the server. Please check if the backend is running.');
      } else {
        setError(`Error: ${err.message}`);
      }
    } finally {
      setIsCalculating(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Typography variant="h4" gutterBottom align="center" sx={{ mb: 4 }}>
            Alt Calculator
          </Typography>

          <StyledPaper>
            <Grid container spacing={3}>
              {/* Property Selection */}
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Property</InputLabel>
                  <Select
                    value={property}
                    onChange={handlePropertyChange}
                    label="Property"
                  >
                    <MenuItem value="Alt_ChiangMai">Alt Chiang Mai</MenuItem>
                    <MenuItem value="Alt_PingRiver">Alt Ping River</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* Calculation Type */}
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Calculation Type</InputLabel>
                  <Select
                    value={calculationType}
                    onChange={handleCalculationTypeChange}
                    label="Calculation Type"
                  >
                    <MenuItem value="new_booking">New Booking</MenuItem>
                    <MenuItem value="extension">Booking Extension</MenuItem>
                    <MenuItem value="room_change">Room Type Change</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* Room Periods */}
              {roomPeriods.map((period, index) => (
                <Grid item xs={12} key={index}>
                  <Card sx={{ mb: 2, p: 2 }}>
                    <CardContent>
                      <Grid container spacing={3}>
                        <Grid item xs={12}>
                          <Typography variant="h6" gutterBottom>
                            Room Period {index + 1}
                          </Typography>
                        </Grid>

                        <Grid item xs={12} md={6}>
                          <FormControl fullWidth>
                            <InputLabel>Room Type</InputLabel>
                            <Select
                              value={period.roomType}
                              onChange={(e) => handleRoomTypeChange(e, index)}
                              label="Room Type"
                            >
                              {availableRoomTypes.map((type) => (
                                <MenuItem key={type} value={type}>
                                  {type}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>

                        <Grid item xs={12} md={6}>
                          <FormControl fullWidth>
                            <InputLabel>Capacity</InputLabel>
                            <Select
                              value={period.capacity.toString()}
                              onChange={(e) => handleCapacityChange(e, index)}
                              label="Capacity"
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
                            onChange={(date) => handleDateChange(date, index, 'checkIn')}
                            slotProps={{ textField: { fullWidth: true } }}
                          />
                        </Grid>

                        <Grid item xs={12} md={6}>
                          <DatePicker
                            label="Check-out Date"
                            value={period.checkOut}
                            onChange={(date) => handleDateChange(date, index, 'checkOut')}
                            minDate={period.checkIn || undefined}
                            slotProps={{ textField: { fullWidth: true } }}
                          />
                        </Grid>

                        {index > 0 && (
                          <Grid item xs={12}>
                            <Button
                              variant="outlined"
                              color="error"
                              onClick={() => handleRemoveRoomPeriod(index)}
                              fullWidth
                            >
                              Remove Period
                            </Button>
                          </Grid>
                        )}
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              ))}

              {roomPeriods.length < 3 && (
                <Grid item xs={12}>
                  <Button
                    variant="outlined"
                    onClick={handleAddRoomPeriod}
                    sx={{ mt: 2 }}
                  >
                    Add Room Period
                  </Button>
                </Grid>
              )}

              {/* Season and Discount */}
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Season</InputLabel>
                  <Select
                    value={season}
                    onChange={(e) => setSeason(e.target.value)}
                    label="Season"
                  >
                    <MenuItem value="Rack">Rack Rate</MenuItem>
                    <MenuItem value="High">High Season</MenuItem>
                    <MenuItem value="Medium">Medium Season</MenuItem>
                    <MenuItem value="Low">Low Season</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Manual Discount (%)"
                  type="number"
                  value={manualDiscount}
                  onChange={(e) => setManualDiscount(Number(e.target.value))}
                  InputProps={{ inputProps: { min: 0, max: 100 } }}
                />
              </Grid>
            </Grid>

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
              <Button
                variant="contained"
                size="large"
                onClick={handleCalculate}
                disabled={isCalculating}
                sx={{ minWidth: 200 }}
              >
                {isCalculating ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Calculate Price'
                )}
              </Button>
            </Box>
          </StyledPaper>

          {result && (
            <ResultCard>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Calculation Result
                </Typography>
                <Divider sx={{ my: 2, backgroundColor: 'rgba(255,255,255,0.1)' }} />
                
                {result.room_breakdowns.map((breakdown, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle1">
                      {breakdown.room_type} - {breakdown.nights} nights
                    </Typography>
                    <Typography variant="body2">
                      Base price: ฿{breakdown.base_price_per_night.toLocaleString()} per night
                    </Typography>
                    <Typography variant="body2">
                      Adjusted price: ฿{breakdown.adjusted_price_per_night.toLocaleString()} per night
                    </Typography>
                    <Typography variant="body2">
                      Subtotal: ฿{breakdown.subtotal.toLocaleString()}
                    </Typography>
                  </Box>
                ))}

                <Divider sx={{ my: 2, backgroundColor: 'rgba(255,255,255,0.1)' }} />
                
                <Typography>
                  Long-stay discount: {result.long_stay_discount_percentage}%
                </Typography>
                <Typography>
                  Subtotal: ฿{result.subtotal.toLocaleString()}
                </Typography>
                <Typography>
                  VAT (7%): ฿{result.vat_amount.toLocaleString()}
                </Typography>
                <Typography variant="h6" sx={{ mt: 1 }}>
                  Total Price: ฿{result.total_price.toLocaleString()}
                </Typography>

                {result.warnings?.length > 0 && (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    {result.warnings.join(' ')}
                  </Alert>
                )}

                <FormControl fullWidth sx={{ mt: 2 }}>
                  <FormLabel>Long-stay Discount Tiers</FormLabel>
                  <List dense>
                    {LONG_STAY_TIERS.map((tier) => (
                      <ListItem key={tier.days}>
                        <ListItemText
                          primary={tier.description}
                          secondary={`Minimum ${tier.days} nights for ${tier.discount}% discount`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </FormControl>
              </CardContent>
            </ResultCard>
          )}
        </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
} 