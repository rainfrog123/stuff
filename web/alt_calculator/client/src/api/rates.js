import { kv } from '@vercel/kv';

export const RATES_KEY = 'rates_data';

export async function getRates() {
  try {
    const rates = await kv.get(RATES_KEY);
    return rates || null;
  } catch (error) {
    console.error('Error fetching rates:', error);
    throw error;
  }
}

export async function updateRates(newRates) {
  try {
    await kv.set(RATES_KEY, newRates);
    return true;
  } catch (error) {
    console.error('Error updating rates:', error);
    throw error;
  }
}

// Initialize rates if they don't exist
export async function initializeRates(initialRates) {
  const existingRates = await getRates();
  if (!existingRates) {
    await updateRates(initialRates);
  }
  return await getRates();
}