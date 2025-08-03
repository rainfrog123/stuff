# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
dataset_path = "TEMAReversal_MLStrategy_ml_dataset.feather"
summary_path = "TEMAReversal_MLStrategy_ml_dataset_summary.json"
df = pd.read_feather(dataset_path)
json_data = json.load(open(summary_path))
# %%
# ta-lib build features
df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()