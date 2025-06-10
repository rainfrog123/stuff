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
            minRoundsForAnalysis: 4,         // Minimum rounds requirement (at least 4 rounds)
            targetTables: [],                // Array to store all eligible tables for betting
            stats: {                         // Statistics for bet placement
                totalBets: 0
            }
        };

        // Store table information globally
        const TABLES = {
            data: {},             // Table data including scores and patterns
            lastAnalysis: 0,      // Timestamp of last analysis
            observers: new Map(), // Map of active observers
            tieCounters: {}       // Track tie counters for each table
        };

        // Generate a random number between 0 and 1
        function random() {
            return Math.random();
        }

        // Generate a binary 50:50 choice (0 or 1) using crypto for better randomness
        function binaryChoice() {
            try {
                // Use crypto.getRandomValues for cryptographically secure randomness
                const array = new Uint8Array(1);
                crypto.getRandomValues(array);
                return array[0] % 2;
            } catch (error) {
                // Fallback to Math.random if crypto API is not available
                console.error('[Baccarat] Crypto API not available, falling back to Math.random');
                return Math.random() < 0.5 ? 0 : 1;
            }
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
            
            const finalBetAmount = Math.max(roundedBetAmount, CONFIG.minBetAmount);
            
            return finalBetAmount;
        }

        // Simulate clicks for a total bet amount
        function simulateBetClicks(button, totalAmount) {
            if (!button || totalAmount <= 0) {
                return;
            }
            
            const clicks = Math.floor(totalAmount / CONFIG.chipValue);
            
            for (let i = 0; i < clicks; i++) {
                setTimeout(() => {
                    try { 
                        button.click();
                    } 
                    catch (error) { 
                        // Ignore click errors
                    }
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

        // Check if the last result was a tie
        function wasLastResultTie(parentElement) {
            try {
                const results = extractBigRoadData(parentElement);
                if (results.length > 0) {
                    return results[results.length - 1] === 'T';
                }
                return false;
            } catch (error) {
                return false;
            }
        }

        // Check if tie counter increased (T+1 condition)
        function checkTieCounterIncrease(tableId, parentElement) {
            try {
                // Find the tie count element (third element in statistics)
                const statsCounts = parentElement.querySelectorAll('.TileStatistics_main-bet-mobile-count__8CSkP');
                if (statsCounts && statsCounts.length >= 3) {
                    const currentTieCount = parseInt(statsCounts[2].textContent, 10) || 0;
                    const previousTieCount = TABLES.tieCounters[tableId] || 0;
                    
                    // Update stored tie count
                    TABLES.tieCounters[tableId] = currentTieCount;
                    
                    // Check if tie counter increased by 1 or more
                    if (currentTieCount > previousTieCount) {
                        console.log(`%c[Baccarat] ${tableId}: Tie counter increased from ${previousTieCount} to ${currentTieCount}, setting T+1 trigger`,
                            'color: #9C27B0; font-weight: bold');
                        return true;
                    }
                }
                return false;
            } catch (error) {
                return false;
            }
        }

        // Analyze all tables and bet on all eligible tables
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
                
                // Set target tables to ALL eligible tables
                CONFIG.targetTables = allEligibleTables;
                
                let tableLog = `%c[Baccarat] Analysis: Found ${tableCount} tables (${allEligibleTables.length} with >${CONFIG.minRoundsForAnalysis-1} rounds)\n`;
                tableLog += `%cBetting on ALL ${CONFIG.targetTables.length} eligible tables\n`;
                console.log(tableLog, 'color: #4CAF50; font-weight: bold', 'color: #FF9800; font-weight: bold');
                
                TABLES.lastAnalysis = Date.now();
                updateObservers();
            } catch (error) {
                console.error('[Baccarat] Error analyzing tables:', error);
            }
        }
        
        // Fisher-Yates shuffle algorithm using crypto for better randomness
        function shuffleArray(array) {
            try {
                for (let i = array.length - 1; i > 0; i--) {
                    // Use crypto.getRandomValues for each swap
                    const randomBytes = new Uint32Array(1);
                    crypto.getRandomValues(randomBytes);
                    const j = randomBytes[0] % (i + 1);
                    [array[i], array[j]] = [array[j], array[i]];
                }
            } catch (error) {
                // Fallback to standard Math.random if crypto API is not available
                console.error('[Baccarat] Crypto API not available for shuffle, falling back to Math.random');
                for (let i = array.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [array[i], array[j]] = [array[j], array[i]];
                }
            }
            return array;
        }

        // Update observers for target tables
        function updateObservers() {
            // Clear ALL existing observers first - complete cleanup
            for (const [tableId, observer] of TABLES.observers.entries()) {
                observer.disconnect();
                window.BACCARAT_AUTO_BETTING_INSTANCE.observers.delete(observer);
            }
            TABLES.observers.clear();
            
            // Setup observers ONLY for current target tables
            CONFIG.targetTables.forEach(tableId => {
                if (TABLES.data[tableId]) {
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
                if (TABLES.observers.has(tableId)) {
                    return;
                }
                
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
                                // Bet on every round finish - simple and direct
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
            if (!CONFIG.targetTables.includes(tableId)) {
                return;
            }
            
            const balance = getBalance();
            if (balance <= 0 || (!bankerButton && !playerButton)) {
                return;
            }
            
            // Calculate the effective balance (modulo 100)
            const effectiveBalance = balance % 100;
            
            // Calculate bet amount - 25% of effective balance
            const rawBetAmount = effectiveBalance * CONFIG.maxBalancePercentage;
            
            // Round to nearest chip value
            const roundedBetAmount = Math.round(rawBetAmount / CONFIG.chipValue) * CONFIG.chipValue;
            
            // Final bet amount
            const betAmount = Math.max(roundedBetAmount, CONFIG.minBetAmount);
            
            // Crypto-secure 50/50 betting
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
            
            // Add random delay before placing bet
            setTimeout(() => {
                // Place the bet - no result tracking
                simulateBetClicks(targetButton, betAmount);
                
                // Simply count the bet
                CONFIG.stats.totalBets++;
            }, getRandomDelay());
        }

        // Function to check if a bet was successfully placed
        function isBetPlaced(parentElement) {
            try {
                // Check for chips with non-zero bet amount
                const chips = parentElement.querySelectorAll('.dndChip[data-betamount]');
                
                for (const chip of chips) {
                    const betAmount = chip.getAttribute('data-betamount');
                    
                    if (betAmount !== "0") {
                        return true;
                    }
                }
                
                // Alternative: Check header for bet amount
                const betAmountText = parentElement.querySelector('.TileHeader_animateMe__og\\+tJ div:not(.TileHeader_addMe__zOi8y)');
                if (betAmountText) {
                    
                    if (betAmountText.textContent.includes('$') && 
                        !betAmountText.textContent.includes('$0')) {
                        return true;
                    }
                }
                
                return false;
            } catch (error) {
                return false;
            }
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
                    '%c[Baccarat] Crypto-Secure All-Table Betting System started (v' + window.BACCARAT_AUTO_BETTING_INSTANCE.version + ')',
                    'color: #4CAF50; font-weight: bold; font-size: 14px'
                );
                console.log(
                    `%c[Baccarat] Monitoring ALL ${engagingTablesCount} eligible tables`,
                    'color: #FF9800; font-weight: bold'
                );
                console.log(
                    `%c[Baccarat] Strategy: Crypto-secure random betting, bet on every round finish, no result tracking`,
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
