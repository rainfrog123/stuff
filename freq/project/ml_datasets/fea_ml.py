# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
import talib as ta
dataset_path = "TEMAReversal_MLStrategy_ml_dataset.feather"
summary_path = "TEMAReversal_MLStrategy_ml_dataset_summary.json"
df = pd.read_feather(dataset_path)
json_data = json.load(open(summary_path))
# show row 500 in full column
# %%
with pd.option_context('display.max_columns', None):
    display(df.iloc[[500]])

# %%
# add ema_20
df['EMA_20'] = ta.EMA(df['close'], timeperiod=20)
df['EMA_50'] = ta.EMA(df['close'], timeperiod=50)
