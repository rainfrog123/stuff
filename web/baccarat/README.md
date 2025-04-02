# Baccarat Auto-Betting System

This repository contains various scripts for automating betting in online Baccarat games. The scripts are designed to work with Pragmatic Play Live casino games.

## Project Structure

All files are now in a single, flat directory structure for simplicity:

```
/allah/stuff/web/baccarat/
│
├── anti-inactivity.js              # Basic anti-inactivity script
├── baccarat-auto-bet.js            # Main auto-betting script
├── baccarat-hft-bet.js             # High-frequency trading betting script
├── baccarat-smart-auto-betting.js  # Smart auto-betting system
├── baccarat-smart-betting-v2.3.js  # Updated smart betting system v2.3
├── balance-detector.js             # Script for detecting balance
├── betting-bot.js                  # Alternative betting bot implementation
├── betting-handler-random-split.js # Handler for randomized betting splits
├── betting-logic.js                # Core betting logic implementation
├── betting-strategy-v2.js          # Betting strategy version 2
├── blackjack-readable.js           # Human-readable blackjack script
├── blackjack.js                    # Optimized blackjack game script
├── detect-elements-enhanced.js     # Enhanced element detection
├── detect-elements-v1.7.js         # Element detection v1.7
├── detect-elements.js              # Basic element detection
├── enhanced-anti-inactivity.js     # Enhanced anti-inactivity script
├── enhanced-anti-inactivity-backup.js # Backup of anti-inactivity script
├── example-chromium.png            # Example image asset
├── log-tie.js                      # Script to log tie occurrences
├── monitor-tie-results.js          # Monitor for tie results
├── new-method-located.js           # Implementation of new betting method
├── simple-bet.js                   # Simple betting implementation
├── stake.ipynb                     # Analysis notebook
├── tampermonkey-backup-2024-12-17.zip # Backup of Tampermonkey scripts
├── test-chip.js                    # Script for testing chip selection
├── tie-monitor-enhanced.js         # Enhanced tie monitoring
└── README.md                       # This documentation file
```

## Main Scripts

- **baccarat-auto-bet.js**: The primary betting script that places bets on banker or player based on TIE counter changes
- **baccarat-hft-bet.js**: High-frequency trading version that monitors any counter changes for placing bets
- **baccarat-smart-betting-v2.3.js**: Latest version of the smart betting system with improved algorithms
- **betting-strategy-v2.js**: Second version of the betting strategy with enhanced decision making
- **balance-detector.js**: Script to detect and monitor your balance
- **enhanced-anti-inactivity.js**: Prevents being marked as inactive in the game

## Utility Scripts

- **detect-elements-*.js**: Various scripts for detecting and interacting with game elements
- **monitor-tie-results.js**: Specifically monitors tie results for analysis
- **tie-monitor-enhanced.js**: Enhanced version with better tie detection and analysis
- **log-tie.js**: Logs tie occurrences for pattern analysis

## Usage

To use these scripts, you need to load them into a browser extension like Tampermonkey. The scripts are designed to run on Pragmatic Play Live casino websites.

For best results with the auto-betting systems:
1. Open the Baccarat game in your browser
2. Make sure the script is loaded and running
3. The script will automatically place bets based on the specified conditions

## Win/Loss Tracking

The betting scripts now include win/loss tracking functionality:
- Tracks wins, losses, and ties for each table
- Calculates win rates and net profit
- Provides detailed statistics in the console
- Logs results every minute for analysis

## Notes

- Always gamble responsibly
- Test scripts with small bet amounts first
- These scripts are for educational purposes only 