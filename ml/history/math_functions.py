import pandas as pd

df1 = pd.read_json('2022-09-24 11:15:13.538366.json')                      
df2 = pd.read_json('2022-09-24 11:37:17.163630.json')                      
df1['long_profit'] = (df1['profit_ratio'].multiply(100)).round(2)
df1['short_profit'] = (df2['profit_ratio'].multiply(100)).round(2)

# df = df1[df.long_profit.notna()]
# df[df.long_profit.notna()]
df = df1
df.loc[(df.long_profit > 0) & (df.short_profit < 0), 'label'] = 'long'
df.loc[(df.long_profit < 0) & (df.short_profit > 0), 'label'] = 'short'
df.loc[(~df['label'].isin(['long', 'short'])) & (df.long_profit.notna()), 'label'] = 'hold'
""" prepare labels """
df.loc[(df['trade'] == 1)& (df.macd > df.macdsignal), 'position'] = 'bottom' 
df.loc[(df['trade'] == 1)& (df.macd < df.macdsignal), 'position'] = 'top'




# df.loc[(df['trade'] == 1)& (df.sma9 > df.sma21), 'position'] = 'top' 
# df.loc[(df['trade'] == 1)& (df.sma9 < df.sma21), 'position'] = 'bottom'
# df.loc[(df['position'] == 'top') & (df['label'] == 'long')]
# df.loc[(df['position'] == 'bottom') & (df['label'] == 'short')]


