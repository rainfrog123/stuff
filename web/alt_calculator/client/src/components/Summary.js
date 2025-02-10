import React from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider
} from '@mui/material';
import { format } from 'date-fns';

const Summary = ({ calculation, formData }) => {
  const formatDate = (date) => {
    console.log('Formatting date:', date);
    if (!date) {
      console.log('Date is null/undefined');
      return 'Invalid Date';
    }
    const parsedDate = new Date(date);
    console.log('Parsed date:', parsedDate);
    console.log('Parsed date year:', parsedDate.getFullYear());
    console.log('Is date valid:', !isNaN(parsedDate.getTime()));
    
    if (isNaN(parsedDate.getTime()) || parsedDate.getFullYear() <= 1970) {
      console.log('Date validation failed');
      return 'Invalid Date';
    }
    return format(parsedDate, 'dd MMM yyyy');
  };
  const formatCurrency = (amount) => 
    new Intl.NumberFormat('th-TH', { 
      style: 'currency', 
      currency: 'THB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);

  const isExtension = formData.calculationType === 'extension';
  const season = calculation.periods[0]?.season || 'N/A';

  return (
    <Box>
      <Typography variant="h6" gutterBottom>Calculation Summary</Typography>
      
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Property: {formData.property === 'Alt_CM' ? 'Alt Chiang Mai' : 'Alt Ping River'}
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          Calculation Type: {formData.calculationType === 'new' ? 'New Booking' : 'Booking Extension'}
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          Season: {season === 'Rack' ? 'Rack Rate' : `${season} Season`}
        </Typography>
        {isExtension && (
          <>
            <Typography variant="subtitle1" gutterBottom>
              Original Stay: {formatDate(formData.originalCheckIn)} - {formatDate(formData.originalCheckOut)}
              {' '}({calculation.originalNights} nights)
            </Typography>
            <Typography variant="subtitle1" gutterBottom>
              Total Period: {formatDate(formData.originalCheckIn)} - {formatDate(formData.checkOut)}
              {' '}({calculation.totalNights} nights)
            </Typography>
            <Typography variant="subtitle1" gutterBottom>
              7-Day Rule Override: {formData.overrideSevenDayRule ? 'Yes' : 'No'}
            </Typography>
          </>
        )}
      </Paper>

      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Period</TableCell>
              <TableCell>Room Type</TableCell>
              <TableCell>Capacity</TableCell>
              <TableCell align="right">Base Rate</TableCell>
              <TableCell align="right">Final Rate</TableCell>
              <TableCell align="right">Nights</TableCell>
              <TableCell align="right">Subtotal</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isExtension && (
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>
                  {formatDate(formData.originalCheckIn)} - {formatDate(formData.originalCheckOut)}
                </TableCell>
                <TableCell>-</TableCell>
                <TableCell>-</TableCell>
                <TableCell align="right">-</TableCell>
                <TableCell align="right">-</TableCell>
                <TableCell align="right">{calculation.originalNights}</TableCell>
                <TableCell align="right" sx={{ color: 'error.main' }}>
                  -{formatCurrency(calculation.amountPaid)}
                </TableCell>
              </TableRow>
            )}
            {calculation.periods.map((period, index) => (
              <TableRow key={index}>
                <TableCell>
                  {formatDate(period.startDate || period.checkIn)} - {formatDate(period.endDate || period.checkOut)}
                </TableCell>
                <TableCell>{period.roomType}</TableCell>
                <TableCell>
                  {period.capacity} {period.capacity === '2' && '(+20%)'}
                </TableCell>
                <TableCell align="right">{formatCurrency(period.baseRate)}</TableCell>
                <TableCell align="right">{formatCurrency(period.rate)}</TableCell>
                <TableCell align="right">{period.nights}</TableCell>
                <TableCell align="right">{formatCurrency(period.subtotal)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Paper elevation={1} sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="subtitle1">
            Total Nights: {calculation.totalNights}
          </Typography>
          {calculation.longStayDiscount > 0 && (
            <Typography variant="subtitle1">
              Long-stay Discount: {calculation.longStayDiscount}%
            </Typography>
          )}
          {formData.extraDiscount > 0 && (
            <Typography variant="subtitle1">
              Extra Discount: {formData.extraDiscount}%
            </Typography>
          )}
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle1">
            Subtotal: {formatCurrency(calculation.subtotal)}
          </Typography>
          {calculation.extraDiscount > 0 && (
            <Typography variant="subtitle1" color="error">
              Extra Discount: -{formatCurrency(calculation.extraDiscount)}
            </Typography>
          )}
          <Typography variant="subtitle1">
            VAT (7%): {formatCurrency(calculation.vat)}
          </Typography>
          <Typography variant="h6" sx={{ mt: 1 }}>
            Total: {formatCurrency(calculation.grandTotal)}
          </Typography>
          {isExtension && (
            <>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" color="text.secondary">
                Amount Already Paid: {formatCurrency(calculation.amountPaid)}
              </Typography>
              <Typography variant="h6" color="primary" sx={{ mt: 1 }}>
                Remaining Amount to Pay: {formatCurrency(calculation.remainingAmount)}
              </Typography>
            </>
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default Summary; 