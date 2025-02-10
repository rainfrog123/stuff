import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider
} from '@mui/material';
import { format, differenceInDays } from 'date-fns';

const Summary = ({ formData, onBack, rates }) => {
  const [calculation, setCalculation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    calculatePrice();
  }, []);

  const calculatePrice = async () => {
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

  if (loading) {
    return (
      <Box sx={{ minHeight: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Typography>Calculating...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ minHeight: 300, display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Typography color="error">Error: {error}</Typography>
        <Button onClick={onBack}>Back</Button>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: 300, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h6" gutterBottom>
        Booking Summary
      </Typography>

      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Property: {formData.property === 'Alt_CM' ? 'Alt Chiang Mai' : 'Alt Ping River'}
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          Calculation Type: {
            formData.calculationType === 'new' ? 'New Booking' :
            formData.calculationType === 'extension' ? 'Booking Extension' :
            'New Booking with Room Type Change'
          }
        </Typography>

        <TableContainer sx={{ mt: 3 }}>
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
              {calculation?.periods?.map((period, index) => (
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

        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1">
            Capacity: {formData.capacity} {formData.capacity === '2' && '(+20% surcharge)'}
          </Typography>
          {calculation?.longStayDiscount > 0 && (
            <Typography variant="subtitle1">
              Long-stay Discount: {calculation.longStayDiscount}%
            </Typography>
          )}
          {formData.extraDiscount > 0 && (
            <Typography variant="subtitle1">
              Extra Discount: {formData.extraDiscount}%
            </Typography>
          )}
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="subtitle1">
            Subtotal: {formatCurrency(calculation?.subtotal || 0)}
          </Typography>
          <Typography variant="subtitle1">
            VAT (7%): {formatCurrency(calculation?.vat || 0)}
          </Typography>
          <Typography variant="h6">
            Total: {formatCurrency(calculation?.total || 0)}
          </Typography>
        </Box>
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 'auto' }}>
        <Button onClick={onBack}>
          Back
        </Button>
        <Button
          variant="contained"
          onClick={() => window.print()}
        >
          Print
        </Button>
      </Box>
    </Box>
  );
};

export default Summary; 