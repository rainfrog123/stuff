    // ==UserScript==
    // @name         Baccarat Auto-Betting System (Ultra Simplified)
    // @namespace    http://tampermonkey.net/
    // @version      4.2
    // @description  Minimal auto-betting focused on 50/50 B/P distribution tables only
    // @author       Your Name
    // @match        *://client.pragmaticplaylive.net/desktop/*
    // @grant        GM_xmlhttpRequest
    // @grant        GM_addStyle
    // @grant        GM_log
    // @grant        GM_setValue
    // @grant        GM_getValue
    // @run-at       document-start
    // ==/UserScript==

    (function () {
        'use strict';

        // Clean up any previous instances of the script
        if (window.BACCARAT_AUTO_BETTING_INSTANCE) {
            try {
                // Disconnect all observers
                if (window.BACCARAT_AUTO_BETTING_INSTANCE.observers) {
                    window.BACCARAT_AUTO_BETTING_INSTANCE.observers.forEach(observer => {
                        if (observer && typeof observer.disconnect === 'function') {
                            observer.disconnect();
                        }
                    });
                }
                
                // Clear all intervals
                if (window.BACCARAT_AUTO_BETTING_INSTANCE.intervals) {
                    window.BACCARAT_AUTO_BETTING_INSTANCE.intervals.forEach(intervalId => {
                        clearInterval(intervalId);
                    });
                }
                
                console.log('%cPrevious Baccarat Auto-Betting instance stopped', 
                    'color: #FF5722; font-weight: bold; font-size: 14px');
            } catch (error) {
                console.error('Error cleaning up previous instance:', error);
            }
        }
        
        // Create a new instance tracker
        window.BACCARAT_AUTO_BETTING_INSTANCE = {
            observers: new Set(),
            intervals: new Set(),
            version: '4.2',
            lastTargetTables: []
        };

        // Configuration
        const CONFIG = {
            chipValue: 0.2,                  // Value of each chip click
            minBetAmount: 0.2,               // Minimum bet amount
            maxBalancePercentage: 0.25,      // Maximum percentage of balance to bet
            clickDelay: 10,                  // Delay between clicks in milliseconds
            betDelayMin: 6000,               // Minimum delay before placing bet (ms)
            betDelayRandom: 3000,            // Additional random delay (ms)
            counterSelector: '.TileStatistics_round-mobile-counter__cjd3w',
            bankerPrefix: "betPositionBGTemp mobile banker",
            playerPrefix: "betPositionBGTemp mobile player",
            balanceKey: 'currentBalance',
            maxTablesToMonitor: 1,           // Only one table at a time
            minRoundsForAnalysis: 4,         // Minimum rounds requirement (at least 4 rounds)
            successfulBetsCounter: 0,        // Counter for successful bets
            refreshTablesAfter: 1,           // Always refresh after every successful bet
            targetTables: [],                // Array to store target tables for betting (will only have one)
            stats: {                         // Statistics for bet wins/losses
                totalBets: 0,
                wins: 0,
                losses: 0,
                profitLoss: 0,               // Overall profit/loss
                pendingBets: {}              // Tracks bets waiting for results
            }
        };

        // Store table information globally
        const TABLES = {
            data: {},             // Table data including scores and patterns
            lastAnalysis: 0,      // Timestamp of last analysis
            observers: new Map()  // Map of active observers
        };

        // Generate a random number between 0 and 1
        function random() {
            return Math.random();
        }

        // Generate a binary 50:50 choice (0 or 1) using crypto for better randomness
        function binaryChoice() {
            // Use Math.random for 50/50
            return Math.random() < 0.5 ? 0 : 1;
        }

        // Get random delay
        function getRandomDelay() {
            return CONFIG.betDelayMin + (random() * CONFIG.betDelayRandom);
        }

        // Retrieve balance from localStorage
        function getBalance() {
            const balance = parseFloat(localStorage.getItem(CONFIG.balanceKey));
            return isNaN(balance) ? 0 : balance;
        }

        // Calculate bet amount based on balance
        function calculateBetAmount() {
            const balance = getBalance();
            if (balance <= 0) return 0;
            
            // Use only the remainder after dividing by 100 as a risk control measure
            const effectiveBalance = balance % 100;
            
            // Always bet exactly 1/4 of the effective balance
            const betAmount = effectiveBalance * CONFIG.maxBalancePercentage;
            
            // Round to nearest chip value (0.2, 0.4, 0.6, etc.)
            let roundedBetAmount = Math.round(betAmount / CONFIG.chipValue) * CONFIG.chipValue;
            
            return Math.max(roundedBetAmount, CONFIG.minBetAmount);
        }

        // Simulate clicks for a total bet amount
        function simulateBetClicks(button, totalAmount) {
            if (!button || totalAmount <= 0) return;
            
            const clicks = Math.floor(totalAmount / CONFIG.chipValue);
            
            for (let i = 0; i < clicks; i++) {
                setTimeout(() => {
                    try { button.click(); } 
                    catch (error) { /* Ignore click errors */ }
                }, i * CONFIG.clickDelay);
            }
        }

        // Find betting buttons in parent element
        function findBettingButtons(parentElement) {
            if (!parentElement) return { bankerButton: null, playerButton: null };
            
            try {
                const bankerButton = Array.from(parentElement.querySelectorAll("*"))
                    .find((el) => el.className && typeof el.className === 'string' && el.className.includes(CONFIG.bankerPrefix));

                const playerButton = Array.from(parentElement.querySelectorAll("*"))
                    .find((el) => el.className && typeof el.className === 'string' && el.className.includes(CONFIG.playerPrefix));
                    
                return { bankerButton, playerButton };
            } catch (error) {
                return { bankerButton: null, playerButton: null };
            }
        }

        // Extract table identifier
        function getTableIdentifier(parentElement) {
            try {
                const fullText = parentElement.textContent || '';
                return fullText.split('$')[0].trim() || 'Unknown Table';
            } catch (error) {
                return 'Unknown Table';
            }
        }

        // Generate a consistent color for a table based on its name
        function getTableColor(tableName) {
            // List of distinct colors for different tables
            const tableColors = [
                '#4CAF50', // Green
                '#9C27B0', // Purple
                '#E91E63', // Pink
                '#3F51B5', // Indigo
                '#009688', // Teal
                '#FF9800', // Orange
                '#795548', // Brown
                '#607D8B'  // Blue Grey
            ];
            
            // Generate a hash from the table name to get a consistent color
            let hash = 0;
            for (let i = 0; i < tableName.length; i++) {
                hash = tableName.charCodeAt(i) + ((hash << 5) - hash);
            }
            
            // Use the hash to select a color from the array
            const colorIndex = Math.abs(hash) % tableColors.length;
            return tableColors[colorIndex];
        }

        // Extract big road data from a table element
        function extractBigRoadData(tableElement) {
            try {
                // Find the big road SVG element
                const bigRoadSvg = tableElement.querySelector('.TileStatistics_bigroad-mobile-container__PDt8X');
                if (!bigRoadSvg) return [];
                
                // Extract all SVG use elements which represent the markers
                const markers = Array.from(bigRoadSvg.querySelectorAll('use'));
                
                // Extract all the statistics values to verify tie count
                const statsCounts = tableElement.querySelectorAll('.TileStatistics_main-bet-mobile-count__8CSkP');
                let tieCount = 0;
                
                // The third element should be the tie count (after Player and Banker counts)
                if (statsCounts && statsCounts.length >= 3) {
                    tieCount = parseInt(statsCounts[2].textContent, 10) || 0;
                }
                
                // Map markers to results (P for Player, B for Banker, T for Tie)
                const results = markers.map(marker => {
                    const href = marker.getAttribute('xlink:href') || '';
                    
                    // Improved pattern matching for all possible markers
                    if (href.includes('bigroad-P')) {
                        // Check more specifically for ties by looking at the specific pattern
                        // PP indicates Player with a Tie
                        if (href.includes('bigroad-PP')) return 'T';
                        return 'P'; // Regular Player win
                    }
                    if (href.includes('bigroad-B')) {
                        // Check more specifically for ties by looking at the specific pattern
                        // BB indicates Banker with a Tie
                        if (href.includes('bigroad-BB')) return 'T';
                        return 'B'; // Regular Banker win
                    }
                    
                    // Direct tie markers
                    if (href.includes('bigroad-T')) return 'T';
                    
                    return null;
                }).filter(result => result !== null);
                
                // Verify and correct the tie count if needed
                const detectedTies = results.filter(r => r === 'T').length;
                
                // If there's a significant discrepancy between detected ties and the displayed tie count,
                // we need a fallback approach to add the missing ties
                if (tieCount > 0 && detectedTies === 0) {
                    // Add missing ties to the results - distribute them evenly throughout the results
                    const interval = Math.max(1, Math.floor(results.length / (tieCount + 1)));
                    for (let i = 1; i <= tieCount; i++) {
                        const insertPosition = Math.min(i * interval, results.length);
                        results.splice(insertPosition, 0, 'T');
                    }
                }
                
                return results;
            } catch (error) {
                console.error('Error extracting big road data:', error);
                return [];
            }
        }

        // Calculate banker win percentage
        function calculateBankerWinRate(results) {
            if (!results || results.length === 0) return 0;
            
            // Filter out ties
            const filteredResults = results.filter(r => r === 'B' || r === 'P');
            if (filteredResults.length === 0) return 0;
            
            const bankerWins = filteredResults.filter(r => r === 'B').length;
            return (bankerWins / filteredResults.length) * 100;
        }

        // Calculate player win percentage
        function calculatePlayerWinRate(results) {
            if (!results || results.length === 0) return 0;
            
            // Filter out ties
            const filteredResults = results.filter(r => r === 'B' || r === 'P');
            if (filteredResults.length === 0) return 0;
            
            const playerWins = filteredResults.filter(r => r === 'P').length;
            return (playerWins / filteredResults.length) * 100;
        }

        // Calculate alternating pattern score - restored and improved
        function calculateAlternatingScore(results) {
            if (!results || results.length < 4) return { score: 0, percentage: 0, alternationCount: 0 };
            
            // Filter out ties for alternating pattern detection
            const filteredResults = results.filter(r => r === 'B' || r === 'P');
            if (filteredResults.length < 4) return { score: 0, percentage: 0, alternationCount: 0 };
            
            // Calculate alternating percentage for the entire dataset
            let alternations = 0;
            for (let i = 1; i < filteredResults.length; i++) {
                if (filteredResults[i] !== filteredResults[i - 1]) {
                    alternations++;
                }
            }
            
            const alternatingPercentage = filteredResults.length > 1 
                ? (alternations / (filteredResults.length - 1)) * 100 
                : a0;
                
            // Store the actual count of alternations for display
            const alternationCount = alternations;
            
            // Calculate reliability factor based on number of rounds
            // More rounds = more reliable pattern
            const roundsFactor = Math.min(1, 0.5 + (filteredResults.length / 60)); // Scales from 0.5 to 1.0 as rounds increase
            
            // Calculate score with round-weighted alternating percentage
            const score = alternatingPercentage * roundsFactor;
            
            return { 
                score: score,
                percentage: alternatingPercentage,
                alternationCount: alternationCount
            };
        }

        // Calculate balance score (how close to 50/50 distribution)
        function calculateBalanceScore(bankerWinRate) {
            // Perfect score at 50% banker win rate (50% player win rate)
            const balanceDeviation = Math.abs(bankerWinRate - 50);
            
            // 100 points for perfect 50/50, decreasing as it deviates
            return Math.max(0, 100 - (balanceDeviation * 2));
        }

        // Updated table scoring with alternating pattern (70%) and B/P balance (30%)
        function calculateTableScore(tableData) {
            const { results, bankerWinRate, alternatingScore } = tableData;
            
            // Skip tables with insufficient rounds
            if (results.length < CONFIG.minRoundsForAnalysis) {
                return 0;
            }
            
            // Calculate balance score (how close to 50/50)
            const balanceScore = calculateBalanceScore(bankerWinRate);
            
            // PRIORITIES:
            // 1. High alternating percentage (70% weight)
            // 2. B/P distribution close to 50/50 (30% weight)
            const weightedScore = (alternatingScore.score * 0.7) + (balanceScore * 0.3);
            
            return Math.round(weightedScore);
        }

        // Analyze all tables and randomly select 1 after every successful bet
        function analyzeAllTables() {
            try {
                // Find all table elements
                const counters = document.querySelectorAll(CONFIG.counterSelector);
                if (!counters || counters.length === 0) return;
                let tableCount = 0;
                let allEligibleTables = [];
                counters.forEach(counter => {
                    const parentElement = counter.parentElement?.parentElement?.parentElement?.parentElement?.parentElement;
                    if (!parentElement) return;
                    const tableId = getTableIdentifier(parentElement);
                    tableCount++;
                    let actualRoundCount = 0;
                    const roundText = counter.textContent.trim();
                    if (roundText.startsWith('#')) {
                        const roundNumber = parseInt(roundText.substring(1));
                        if (!isNaN(roundNumber)) {
                            actualRoundCount = roundNumber;
                        }
                    }
                    const results = extractBigRoadData(parentElement);
                    if (actualRoundCount >= CONFIG.minRoundsForAnalysis) {
                        allEligibleTables.push(tableId);
                    }
                    const tableData = {
                        element: parentElement,
                        counter: counter,
                        results: results,
                        roundCount: actualRoundCount,
                        lastUpdated: Date.now()
                    };
                    TABLES.data[tableId] = tableData;
                });
                // Always shuffle and pick one table after every successful bet
                shuffleArray(allEligibleTables);
                const randomTables = allEligibleTables.slice(0, 1); // Only one table
                const tablesChanged = hasTablesChanged(CONFIG.targetTables, randomTables);
                CONFIG.targetTables = randomTables;
                if (tablesChanged || !window.BACCARAT_AUTO_BETTING_INSTANCE.lastTargetTables.length) {
                    window.BACCARAT_AUTO_BETTING_INSTANCE.lastTargetTables = [...randomTables];
                    let tableLog = `%c[Baccarat] Analysis: Found ${tableCount} tables (${allEligibleTables.length} with >${CONFIG.minRoundsForAnalysis-1} rounds)\n`;
                    tableLog += `%cRandomly selected 1 table:\n`;
                    randomTables.forEach((tableId, index) => {
                        const table = TABLES.data[tableId];
                        const rounds = table.roundCount;
                        tableLog += `${index + 1}. ${tableId}: Rounds: ${rounds}\n\n`;
                    });
                    console.log(tableLog, 'color: #4CAF50; font-weight: bold', 'color: #FF9800; font-weight: bold');
                }
                TABLES.lastAnalysis = Date.now();
                updateObservers();
            } catch (error) {
                console.error('[Baccarat] Error analyzing tables:', error);
            }
        }
        
        // Fisher-Yates shuffle algorithm for randomizing tables using crypto for better randomness
        function shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }

        // Check if the list of selected tables has changed
        function hasTablesChanged(oldTables, newTables) {
            if (oldTables.length !== newTables.length) return true;
            
            for (let i = 0; i < oldTables.length; i++) {
                if (oldTables[i] !== newTables[i]) return true;
            }
            
            return false;
        }

        // Update observers for target tables
        function updateObservers() {
            // Clear all existing observers that are not in target tables
            for (const [tableId, observer] of TABLES.observers.entries()) {
                if (!CONFIG.targetTables.includes(tableId)) {
                    observer.disconnect();
                    TABLES.observers.delete(tableId);
                }
            }
            
            // Setup observers for target tables
            CONFIG.targetTables.forEach(tableId => {
                if (!TABLES.observers.has(tableId) && TABLES.data[tableId]) {
                    const counter = TABLES.data[tableId].counter;
                    setupCounterObserver(counter);
                }
            });
        }

        // Setup observer for round counter changes
        function setupCounterObserver(counter) {
            if (!counter) return;
            
            try {
                const parentElement = counter.parentElement?.parentElement?.parentElement?.parentElement?.parentElement;
                if (!parentElement) return;
                
                const tableId = getTableIdentifier(parentElement);
                
                // Check if we already have an observer for this table
                if (TABLES.observers.has(tableId)) return;
                
                // Find betting buttons
                const { bankerButton, playerButton } = findBettingButtons(parentElement);
                
                // Create and setup the observer
                const observer = new MutationObserver((mutations) => {
                    for (const mutation of mutations) {
                        if (mutation.type === 'childList' || mutation.type === 'characterData') {
                            // Improved round number extraction
                            const roundText = counter.textContent.trim();
                            let roundNumber = 0;
                            
                            if (roundText.startsWith('#')) {
                                // Extract number after # character
                                const parsedNumber = parseInt(roundText.substring(1));
                                if (!isNaN(parsedNumber)) {
                                    roundNumber = parsedNumber;
                                }
                            }
                            
                            if (roundNumber > 0) {
                                // Recalculate tables on every round
                                analyzeAllTables();
                                
                                // Place bet on this table if it's in our target list
                                placeBet(tableId, bankerButton, playerButton, roundNumber);
                                
                                break; // Process only once per batch of mutations
                            }
                        }
                    }
                });
                
                // Start observing the round counter directly
                observer.observe(counter, {
                    childList: true,
                    characterData: true,
                    subtree: true,
                });
                
                // Store observer reference
                TABLES.observers.set(tableId, observer);
                window.BACCARAT_AUTO_BETTING_INSTANCE.observers.add(observer);
                
            } catch (error) {
                console.error('[Baccarat] Error setting up observer:', error);
            }
        }

        // Place bet based on 50/50 strategy
        function placeBet(tableId, bankerButton, playerButton, roundNumber) {
            // Only place bets on target tables
            if (!CONFIG.targetTables.includes(tableId)) return;
            
            const balance = getBalance();
            if (balance <= 0 || (!bankerButton && !playerButton)) return;
            
            // Calculate the effective balance (modulo 100)
            const effectiveBalance = balance % 100;
            
            // Calculate bet amount - 25% of effective balance
            const rawBetAmount = effectiveBalance * CONFIG.maxBalancePercentage;
            
            // Round to nearest chip value
            const roundedBetAmount = Math.round(rawBetAmount / CONFIG.chipValue) * CONFIG.chipValue;
            
            // Final bet amount
            const betAmount = Math.max(roundedBetAmount, CONFIG.minBetAmount);
            
            // Random 50/50 betting - core betting strategy
            const betChoice = binaryChoice() === 0 ? "banker" : "player";
            const targetButton = betChoice === "banker" ? bankerButton : playerButton;
            
            if (!targetButton) return;
            
            // Colorful logging for bets
            const colors = {
                banker: '#FF5722', // Orange for banker
                player: '#2196F3'  // Blue for player
            };
            
            // Generate a consistent color for the table name based on the table ID
            const tableColor = getTableColor(tableId);
            
            // Get the parent element to check for bet success
            const parentElement = bankerButton?.parentElement?.parentElement?.parentElement?.parentElement || 
                                  playerButton?.parentElement?.parentElement?.parentElement?.parentElement;
            
            // Log bet placement - like the original working version
            console.log(
                `%c[Baccarat] ${tableId}: %c${betChoice.toUpperCase()} $${betAmount} %c[Balance: $${Math.round(balance)}]`,
                `color: ${tableColor}; font-weight: bold`,
                `color: ${colors[betChoice]}; font-weight: bold`,
                'color: #999; font-style: italic'
            );
            
            // Add random delay before placing bet
            setTimeout(() => {
                // Attempt to place the bet
                simulateBetClicks(targetButton, betAmount);
                
                // Check if bet was placed successfully after a short delay
                setTimeout(() => {
                    // Original success detection logic - more reliable
                    const success = parentElement && isBetPlaced(parentElement);
                    if (success) {
                        // Increment successful bets counter
                        CONFIG.successfulBetsCounter++;
                        
                        // Store the bet info for tracking result later
                        CONFIG.stats.totalBets++;
                        
                        // Track this bet for result checking
                        CONFIG.stats.pendingBets[tableId] = {
                            amount: betAmount,
                            choice: betChoice,
                            roundNumber: roundNumber,
                            timestamp: Date.now()
                        };
                        
                        console.log(
                            `%c[Baccarat] ${tableId}: %cBET SUCCESS ✓ %c(${betChoice.toUpperCase()} $${betAmount}) [${CONFIG.successfulBetsCounter}/${CONFIG.refreshTablesAfter}]`,
                            `color: ${tableColor}; font-weight: bold`,
                            'color: #4CAF50; font-weight: bold',
                            `color: ${colors[betChoice]}`
                        );
                        
                        // Set up result checking
                        checkBetResult(tableId, parentElement, betChoice, betAmount, roundNumber);
                        
                        // Analyze all tables and pick a new table after a successful bet
                        analyzeAllTables();
                    }
                }, 2000); // Back to original 2 second delay
            }, getRandomDelay());
        }

        // Function to check if a bet was successfully placed
        function isBetPlaced(parentElement) {
            try {
                // Check for chips with non-zero bet amount
                const chips = parentElement.querySelectorAll('.dndChip[data-betamount]');
                for (const chip of chips) {
                    if (chip.getAttribute('data-betamount') !== "0") {
                        return true;
                    }
                }
                
                // Alternative: Check header for bet amount
                const betAmountText = parentElement.querySelector('.TileHeader_animateMe__og\\+tJ div:not(.TileHeader_addMe__zOi8y)');
                if (betAmountText && betAmountText.textContent.includes('$') && 
                    !betAmountText.textContent.includes('$0')) {
                    return true;
                }
                
                // If we get here, no bet was detected
                return false;
            } catch (error) {
                console.error('[Baccarat] Error checking bet placed:', error);
                return false; // Return false on error instead of true
            }
        }

        // Function to check bet result (win/loss)
        function checkBetResult(tableId, parentElement, betChoice, betAmount, roundNumber) {
            if (!parentElement) return;
            
            // Set an interval to check for result
            const resultInterval = setInterval(() => {
                try {
                    // Check if this bet is still pending
                    if (!CONFIG.stats.pendingBets[tableId]) {
                        clearInterval(resultInterval);
                        return;
                    }
                    
                    // Look for win message container
                    const winMessage = parentElement.querySelector('.GameResultAndYouWin_winContainer__qC7gx');
                    
                    // Look for the round counter to see if it changed (round is over)
                    const counter = parentElement.querySelector(CONFIG.counterSelector);
                    const newRoundText = counter?.textContent.trim() || '';
                    let newRoundNumber = 0;
                    
                    if (newRoundText.startsWith('#')) {
                        // Extract number after # character
                        const parsedNumber = parseInt(newRoundText.substring(1));
                        if (!isNaN(parsedNumber)) {
                            newRoundNumber = parsedNumber;
                        }
                    }
                    
                    // If round changed and no win message, it's a loss
                    if (newRoundNumber > roundNumber || newRoundNumber === 1) {
                        if (!winMessage) {
                            // It's a loss
                            const tableColor = getTableColor(tableId);
                            
                            // Calculate loss amount (depending on banker/player)
                            const lossAmount = betChoice === 'banker' ? betAmount : betAmount;
                            CONFIG.stats.losses++;
                            CONFIG.stats.profitLoss -= lossAmount;
                            
                            console.log(
                                `%c[Baccarat] ${tableId}: %cBET LOST ✗ %c(${betChoice.toUpperCase()} -$${lossAmount}) %c[W:${CONFIG.stats.wins}/L:${CONFIG.stats.losses}, P/L:$${CONFIG.stats.profitLoss.toFixed(2)}]`,
                                `color: ${tableColor}; font-weight: bold`,
                                'color: #F44336; font-weight: bold',
                                `color: #F44336`,
                                'color: #999; font-style: italic'
                            );
                            
                            // Remove from pending bets
                            delete CONFIG.stats.pendingBets[tableId];
                            clearInterval(resultInterval);
                        }
                    }
                    
                    // Check for win message
                    if (winMessage) {
                        // Find win amount
                        const winAmountEl = winMessage.querySelector('.GameResultAndYouWin_youWinAmount__cu0np');
                        const winAmountText = winAmountEl?.textContent || '';
                        let winAmount = 0;
                        
                        // Extract win amount (format: "$0.40")
                        if (winAmountText.startsWith('$')) {
                            winAmount = parseFloat(winAmountText.substring(1));
                        }
                        
                        // Calculate profit (win amount - bet amount)
                        const profitAmount = winAmount - betAmount;
                        CONFIG.stats.wins++;
                        CONFIG.stats.profitLoss += profitAmount;
                        
                        const tableColor = getTableColor(tableId);
                        console.log(
                            `%c[Baccarat] ${tableId}: %cBET WON ✓ %c(${betChoice.toUpperCase()} +$${profitAmount.toFixed(2)}) %c[W:${CONFIG.stats.wins}/L:${CONFIG.stats.losses}, P/L:$${CONFIG.stats.profitLoss.toFixed(2)}]`,
                            `color: ${tableColor}; font-weight: bold`,
                            'color: #4CAF50; font-weight: bold',
                            `color: #4CAF50`,
                            'color: #999; font-style: italic'
                        );
                        
                        // Remove from pending bets
                        delete CONFIG.stats.pendingBets[tableId];
                        clearInterval(resultInterval);
                    }
                } catch (error) {
                    console.error('[Baccarat] Error checking bet result:', error);
                    clearInterval(resultInterval);
                }
            }, 2000); // Check every 2 seconds
            
            // Store interval reference
            window.BACCARAT_AUTO_BETTING_INSTANCE.intervals.add(resultInterval);
            
            // Safety timeout to clear interval after 2 minutes if no result
            setTimeout(() => {
                clearInterval(resultInterval);
                
                // If still pending, remove from pending bets
                if (CONFIG.stats.pendingBets[tableId]) {
                    console.log(
                        `%c[Baccarat] ${tableId}: %cBet result timeout - could not determine outcome`,
                        `color: ${getTableColor(tableId)}; font-weight: bold`,
                        'color: #FF9800; font-weight: bold'
                    );
                    delete CONFIG.stats.pendingBets[tableId];
                }
            }, 120000); // 2 minute timeout
        }

        // Start monitoring
        function startMonitoring() {
            try {
                // Initial analysis of all tables
                analyzeAllTables();
                
                // Get count of tables we're engaging with
                const engagingTablesCount = CONFIG.targetTables.length;
                
                // Log system start with table count
                console.log(
                    '%c[Baccarat] Random table selection system started (v' + window.BACCARAT_AUTO_BETTING_INSTANCE.version + ')',
                    'color: #4CAF50; font-weight: bold; font-size: 14px'
                );
                console.log(
                    `%c[Baccarat] Currently engaging with ${engagingTablesCount} tables (max: ${CONFIG.maxTablesToMonitor})`,
                    'color: #FF9800; font-weight: bold'
                );
                console.log(
                    '%c[Baccarat] Tables will be randomly selected every 10 successful bets (min 4 rounds)',
                    'color: #4CAF50; font-style: italic;'
                );
            } catch (error) {
                console.error('[Baccarat] Error starting monitoring:', error);
                setTimeout(startMonitoring, 5000);
            }
        }

        // Initialize the system
        function initialize() {
            // Wait for DOM to be fully loaded
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', startMonitoring);
            } else {
                startMonitoring();
            }
        }

        // Start the system
        initialize();
    })();
