from pathlib import Path

# Ensure the data directory exists
data_dir = Path(__file__).parent
data_dir.mkdir(parents=True, exist_ok=True) 