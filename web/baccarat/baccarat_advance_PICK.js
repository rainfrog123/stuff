    // ==UserScript==
    // @name         Baccarat Auto-Betting System (Ultra Simplified)
    // @namespace    http://tampermonkey.net/
    // @version      4.1
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
            version: '4.1',
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
            maxTablesToMonitor: 5,           // Maximum number of tables to bet on
            minRoundsForAnalysis: 10,        // Minimum rounds needed for analysis (strict enforcement)
            idealBalanceRange: 10,           // Target range for balanced B/P distribution (±10% from 50/50)
            targetTables: []                 // Array to store target tables for betting
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

        // Generate a binary 50:50 choice (0 or 1)
        function binaryChoice() {
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

        // Analyze all tables and select the best ones
        function analyzeAllTables() {
            try {
                // Find all table elements
                const counters = document.querySelectorAll(CONFIG.counterSelector);
                if (!counters || counters.length === 0) return;
                
                // Process each table
                let tableCount = 0;
                let tablesWithSufficientRounds = 0;
                
                counters.forEach(counter => {
                    const parentElement = counter.parentElement?.parentElement?.parentElement?.parentElement?.parentElement;
                    if (!parentElement) return;
                    
                    const tableId = getTableIdentifier(parentElement);
                    tableCount++;
                    
                    // Extract results from big road
                    const results = extractBigRoadData(parentElement);
                    
                    // Skip tables with insufficient rounds
                    if (results.length < CONFIG.minRoundsForAnalysis) {
                        // Store limited data but mark as insufficient
                        TABLES.data[tableId] = {
                            element: parentElement,
                            counter: counter,
                            results: results,
                            insufficientRounds: true,
                            score: 0,
                            lastUpdated: Date.now()
                        };
                        return; // Skip to next table
                    }
                    
                    tablesWithSufficientRounds++;
                    
                    // Calculate metrics
                    const bankerWinRate = calculateBankerWinRate(results);
                    const playerWinRate = calculatePlayerWinRate(results);
                    const alternatingScore = calculateAlternatingScore(results);
                    
                    // Create table data object
                    const tableData = {
                        element: parentElement,
                        counter: counter,
                        results: results,
                        insufficientRounds: false,
                        bankerWinRate: bankerWinRate,
                        playerWinRate: playerWinRate,
                        alternatingScore: alternatingScore,
                        lastUpdated: Date.now()
                    };
                    
                    // Calculate overall score
                    tableData.score = calculateTableScore(tableData);
                    
                    // Store table data
                    TABLES.data[tableId] = tableData;
                });
                
                // Sort tables by score (descending) and select top tables
                const sortedTables = Object.entries(TABLES.data)
                    .filter(([_, tableData]) => !tableData.insufficientRounds) // Exclude tables with insufficient rounds
                    .sort((a, b) => b[1].score - a[1].score)
                    .slice(0, CONFIG.maxTablesToMonitor)
                    .map(entry => entry[0]);
                
                // Check if the selected tables have changed
                const tablesChanged = hasTablesChanged(CONFIG.targetTables, sortedTables);
                
                // Update target tables
                CONFIG.targetTables = sortedTables;
                
                // Only log if tables have changed or this is the first analysis
                if (tablesChanged || !window.BACCARAT_AUTO_BETTING_INSTANCE.lastTargetTables.length) {
                    // Store current selection for future comparison
                    window.BACCARAT_AUTO_BETTING_INSTANCE.lastTargetTables = [...sortedTables];
                    
                    // Generate a single concise log of all tables
                    let tableLog = `%c[Baccarat] Analysis: ${tablesWithSufficientRounds}/${tableCount} tables with 10+ rounds\n`;
                    
                    // Add selected tables to the log
                    if (sortedTables.length > 0) {
                        tableLog += `%cSelected tables (Alt 70% | BP 30%):\n`;
                        
                        sortedTables.forEach((tableId, index) => {
                            const table = TABLES.data[tableId];
                            const bWinRate = Math.round(table.bankerWinRate);
                            const pWinRate = Math.round(table.playerWinRate);
                            const score = Math.round(table.score);
                            const altRate = Math.round(table.alternatingScore.percentage);
                            const altCount = table.alternatingScore.alternationCount;
                            const rounds = table.results.length;
                            
                            tableLog += `${index + 1}. ${tableId}: Score: ${score} | Alt: ${altRate}% (${altCount}/${rounds-1}) | B/P: ${bWinRate}%/${pWinRate}% | Rounds: ${rounds}\n\n`;
                        });
                    } else {
                        tableLog += `%cNo tables meet criteria`;
                    }
                    
                    // Output the single consolidated log
                    console.log(tableLog, 'color: #4CAF50; font-weight: bold', 'color: #FF9800; font-weight: bold');
                }
                
                // Update timestamp
                TABLES.lastAnalysis = Date.now();
                
                // Clean up observers and setup new ones for top tables
                updateObservers();
                
            } catch (error) {
                console.error('[Baccarat] Error analyzing tables:', error);
            }
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
                            // We observe the round counter directly to bet on every round
                            const roundText = counter.textContent;
                            const roundMatch = roundText.match(/#(\d+)/);
                            if (!roundMatch) continue;
                            
                            // Get the round number
                            const roundNumber = parseInt(roundMatch[1]);
                            
                            // Recalculate tables on every round
                            analyzeAllTables();
                            
                            // Place bet on this table if it's in our target list
                            placeBet(tableId, bankerButton, playerButton, roundNumber);
                            
                            break; // Process only once per batch of mutations
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
                
                return false;
            } catch (error) {
                console.error('[Baccarat] Error checking bet placed:', error);
                return false;
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
            
            // Log bet placement
            console.log(
                `%c[Baccarat] ${tableId}: %c${betChoice.toUpperCase()} $${betAmount} %c[Balance: $${Math.round(balance)}]`,
                `color: ${tableColor}; font-weight: bold`,
                `color: ${colors[betChoice]}; font-weight: bold`,
                'color: #999; font-style: italic'
            );
            
            // Get the parent element to check for bet success
            const parentElement = bankerButton?.parentElement?.parentElement?.parentElement?.parentElement || 
                                  playerButton?.parentElement?.parentElement?.parentElement?.parentElement;
            
            // Store the time before attempting to place the bet
            const betAttemptTime = Date.now();
            
            // Add random delay before placing bet
            setTimeout(() => {
                // Attempt to place the bet
                simulateBetClicks(targetButton, betAmount);
                
                // Check if bet was placed successfully after a short delay
                setTimeout(() => {
                    const success = parentElement && isBetPlaced(parentElement);
                    if (success) {
                        console.log(
                            `%c[Baccarat] ${tableId}: %cBET SUCCESS ✓ %c(${betChoice.toUpperCase()} $${betAmount})`,
                            `color: ${tableColor}; font-weight: bold`,
                            'color: #4CAF50; font-weight: bold',
                            `color: ${colors[betChoice]}`
                        );
                    } else {
                        console.log(
                            `%c[Baccarat] ${tableId}: %cBET FAILED ✗ %c(${betChoice.toUpperCase()} $${betAmount})`,
                            `color: ${tableColor}; font-weight: bold`,
                            'color: #F44336; font-weight: bold',
                            `color: ${colors[betChoice]}`
                        );
                    }
                }, 2000); // Check 2 seconds after placing bet
            }, getRandomDelay());
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
                    '%c[Baccarat] Ultra-simplified system started (v' + window.BACCARAT_AUTO_BETTING_INSTANCE.version + ')',
                    'color: #4CAF50; font-weight: bold; font-size: 14px'
                );
                console.log(
                    `%c[Baccarat] Currently engaging with ${engagingTablesCount} tables (max: ${CONFIG.maxTablesToMonitor})`,
                    'color: #FF9800; font-weight: bold'
                );
                console.log(
                    '%c[Baccarat] Focus: Alternating Pattern (70%) + B/P Balance (30%) | Min 10 Rounds',
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
