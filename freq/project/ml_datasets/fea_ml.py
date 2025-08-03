# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path

# %%
# Load the dataset and summary
dataset_path = "TEMAReversal_MLStrategy_ml_dataset.feather"
summary_path = "TEMAReversal_MLStrategy_ml_dataset_summary.json"

# %%
df = pd.read_feather(dataset_path)


# %%
with pd.option_context('display.max_columns', None):
    display(df.head(10))

# %%
# show only trade_open not false
with pd.option_context('display.max_columns', None):
    display(df[df['trade_open']!=False].head(10))


# %%
with pd.option_context('display.max_columns', None):
    display(df.iloc[100:110])

