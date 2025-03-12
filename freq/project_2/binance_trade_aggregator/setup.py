from setuptools import setup, find_packages

setup(
    name="binance_trade_aggregator",
    version="0.1.0",
    description="Tools to aggregate and analyze Binance ETH/USDT trade data from Parquet files",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas>=1.5.0",
        "pyarrow>=10.0.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.12.0",
        "tqdm>=4.64.0",
    ],
    entry_points={
        "console_scripts": [
            "aggregate-trades=binance_trade_aggregator.aggregate_trades:main",
        ],
    },
    python_requires=">=3.11",
) 
