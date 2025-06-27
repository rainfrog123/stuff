# crypto_blocks.py

import pyarrow.feather as feather
import pandas as pd
import talib
import numpy as np
from pathlib import Path

# Define the Block class
class Block:
    def __init__(self, start_date, end_date, start_price, end_price, duration, data_segment):
        self.start_date = start_date
        self.end_date = end_date
        self.start_price = start_price
        self.end_price = end_price
        self.duration = duration
        self.data_segment = data_segment  # Store all the data points in this block
        self.direction = 'UP' if start_price < end_price else 'DOWN'
        self.features = {}

    def __str__(self):
        return f'Block: {self.start_date} - {self.end_date} ({self.duration} periods)'

    def __repr__(self):
        return str(self)

    def calculate_features(self):
        print(f'Calculating features for block: {self.start_date} - {self.end_date}')
        import 


def load_crypto_data(data_file_path, start_date, end_date):
    """
    Load cryptocurrency data, filter by date range, and calculate TEMA and trend information.
    
    Parameters:
    data_file_path (str): Path to the Feather file containing the dataset.
    start_date (str): The start date for filtering the data in 'YYYY-MM-DD' format.
    end_date (str): The end date for filtering the data in 'YYYY-MM-DD' format.
    
    Returns:
    pd.DataFrame: DataFrame containing the filtered data with TEMA, trend, and trend change information.
    """
    # Load data from Feather file
    crypto_df = feather.read_feather(data_file_path)

    # Convert input dates to datetime format
    start_date = pd.to_datetime(start_date).tz_localize('UTC')
    end_date = pd.to_datetime(end_date).tz_localize('UTC')
    
    # Filter data between the start and end dates
    crypto_df = crypto_df[(crypto_df['date'] >= start_date) & (crypto_df['date'] <= end_date)]

    # Calculate the Triple Exponential Moving Average (TEMA) with a default period of 50
    tema_period = 50
    crypto_df['tema'] = talib.TEMA(crypto_df['close'], timeperiod=tema_period)

    # Determine the trend direction (UP, DOWN, STABLE)
    crypto_df['trend'] = np.where(crypto_df['tema'] > crypto_df['tema'].shift(1), 'UP',
                                  np.where(crypto_df['tema'] < crypto_df['tema'].shift(1), 'DOWN', 'STABLE'))

    # Identify significant trend changes (ignoring 'STABLE' transitions)
    crypto_df['is_trend_change'] = crypto_df['trend'] != crypto_df['trend'].shift(1)
    crypto_df['is_significant_trend_change'] = crypto_df['is_trend_change'] & (crypto_df['trend'] != 'STABLE')

    # Assign a unique group ID to each continuous trend segment
    crypto_df['group_id'] = crypto_df['is_significant_trend_change'].cumsum()

    return crypto_df

def create_blocks(crypto_df):
    """
    Create a list of Block objects from the DataFrame.
    """
    blocks = []

    # Group the data by 'group_id'
    grouped = crypto_df.groupby('group_id')

    # Iterate over each group and create a block
    for group_id, group_data in grouped:
        start_date = group_data['date'].iloc[0]
        end_date = group_data['date'].iloc[-1]
        start_price = group_data['close'].iloc[0]
        end_price = group_data['close'].iloc[-1]
        duration = len(group_data)

        # Create a block object that includes all the data points
        block = Block(
            start_date=start_date,
            end_date=end_date,
            start_price=start_price,
            end_price=end_price,
            duration=duration,
            data_segment=group_data  # Store the entire segment of data
        )

        # Add the block to the list
        blocks.append(block)

    return blocks
