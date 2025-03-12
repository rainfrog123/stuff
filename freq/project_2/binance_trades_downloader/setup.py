from setuptools import setup, find_packages

setup(
    name="binance_trades_downloader",
    version="0.1.0",
    description="Tools to download and process Binance ETH/USDT trade data",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "pandas>=1.5.0",
        "pyarrow>=10.0.0",
        "tqdm>=4.64.0",
        "humanize>=4.6.0",
    ],
    entry_points={
        "console_scripts": [
            "download-trades=binance_trades_downloader.downloader:download_monthly_trades",
        ],
    },
    python_requires=">=3.11",
) 