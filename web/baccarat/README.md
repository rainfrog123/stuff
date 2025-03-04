# Baccarat Automation Project

This project contains scripts and tools for automating and analyzing Baccarat gameplay.

## Directory Structure

### `/scripts`
- **betting/**: Contains betting automation scripts
  - `betting_handler_random_split.js`: Handles random split betting strategy
  - `betting_logic.js`: Core betting logic implementation
  - `mutiple_bet.js`: Handles multiple bet scenarios
  - `test_chip.js`: Testing script for chip functionality
  - `betting-2.js`: Alternative betting implementation

- **monitoring/**: Contains monitoring and analysis scripts
  - `Monitor_TIE_Results_and_Random_Bet_Calculation_X2.js`: Monitors TIE results and calculates random bets
  - `Monitor`: General monitoring script
  - `new_method_located.js`: New betting method implementation
  - `log_tie.js`: Logging script for TIE results

- **utils/**: Utility scripts
  - `Anti-Inactivity`: Prevents session timeout
  - `Detect_Elements`: Element detection utilities

### `/game`
- Contains core game logic and implementation
- `blackjack.js`: Main game implementation
- `blackjack.readable.js`: Human-readable version of game logic

### `/analysis`
- Contains analysis notebooks and tools
- `stake.ipynb`: Jupyter notebook for stake analysis

### `/assets`
- Contains static assets and resources
- `example-chromium.png`: Example image

### `/backups`
- Contains Tampermonkey backups
- Organized by date

## Usage

1. Install required browser extensions (Tampermonkey)
2. Load the appropriate scripts based on your needs
3. Configure betting parameters in the betting scripts
4. Run monitoring scripts to track results

## Notes

- Keep backups up to date
- Monitor system resources when running multiple scripts
- Test betting strategies with small stakes first 