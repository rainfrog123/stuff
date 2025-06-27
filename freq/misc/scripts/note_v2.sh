### DATA COMMANDS ###
freqtrade download-data -c config.json --userdir /allah/stuff/freq/project_1/user_data --timerange 20240101- --timeframes 1m 3m 5m 15m 30m 1h 4h --datadir /allah/freqtrade/user_data/data/binance
# Alt: --config /allah/stuff/freq/userdir/mutiple_coins_v2.json --timerange 20241220-

### CORE COMMANDS ###
# Live Trading
freqtrade trade --strategy TrendReversalLabelingStrategy_Prod --userdir /allah/stuff/freq/project_1/user_data --config /allah/stuff/freq/project_1/user_data/config_prod.json
# Utils
freqtrade trades-to-ohlcv --exchange binance -t 5m 1h 1d --pairs BTC/USDT:USDT
freqtrade list-strategies --strategy-path /allah/stuff/freq/userdir/strategies

### BACKTESTING ###
freqtrade backtesting --strategy FreqAIDynamicClassifierStrategy --userdir /allah/stuff/freq/project_1/user_data --config /allah/stuff/freq/project_1/user_data/config_freqai.json --timerange 20250110-20250111 --datadir /allah/freqtrade/user_data/data/binance --cache none --starting-balance 10000 --eps --export=signals --fee 0 --freqaimodel PyTorchMLPClassifier
freqtrade backtesting --strategy TrendReversalLabelingStrategy --userdir /allah/stuff/freq/project_1/user_data --config /allah/stuff/freq/project_1/user_data/config.json --timerange 20250110-20250111 --datadir /allah/freqtrade/user_data/data/binance --cache none --starting-balance 10000 --eps --export=signals --fee 0

# Alt timeranges: --timerange 20170110- --starting-balance 10000000
# Alt strats: MultiTimeframeTEMAAgreement, freqai_opaq_classifier

### HYPEROPT ###
freqtrade hyperopt --strategy TrendReversalLabelingStrategy --hyperopt-loss MultiMetricHyperOptLoss --spaces stoploss -e 100 --timerange 20250101- -c config.json --disable-param-export --starting-balance 10000 --userdir /allah/stuff/freq/project_1/user_data --datadir /allah/freqtrade/user_data/data/binance --fee 0
# Alt losses: SharpeHyperOptLossDaily, ShortTradeDurHyperOptLoss
# Alt spaces: buy sell stoploss

### SYSTEM ###
socat TCP-LISTEN:19020,fork TCP:172.104.124.82:9000
# Cron: 0 * * * * /bin/bash -c 'source /allah/freqtrade/.venv/bin/activate && cd /allah/freqtrade/ && freqtrade download-data -c config.json --timerange 20220101- --timeframes 1m 3m 5m 15m 30m 1h 4h'