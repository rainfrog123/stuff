    // ==UserScript==
    // @name         Baccarat Auto-Betting System
    // @namespace    http://tampermonkey.net/
    // @version      3.1
    // @description  Automatically places bets on banker or player regardless of TIE count
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
                
                // Remove UI elements if any
                if (window.BACCARAT_AUTO_BETTING_INSTANCE.panel && 
                    window.BACCARAT_AUTO_BETTING_INSTANCE.panel.parentNode) {
                    window.BACCARAT_AUTO_BETTING_INSTANCE.panel.parentNode.removeChild(
                        window.BACCARAT_AUTO_BETTING_INSTANCE.panel
                    );
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
            panel: null,
            version: '3.1'
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
            maxTablesToMonitor: 5,           // Maximum number of tables to bet on (increased from 3 to 5)
            tableAnalysisInterval: 30000,    // Analyze tables every 30 seconds
            recentRoundsToConsider: 20,      // Consider only the most recent 20 rounds for alternation rate
            minRoundsForAnalysis: 10,        // Minimum rounds needed for analysis
            targetTables: []                 // Array to store target tables for betting
        };

        // Store table information globally
        const TABLES = {
            data: {},             // Table data including scores and patterns
            lastAnalysis: 0,      // Timestamp of last analysis
            observers: new Map(), // Map of active observers
            betCount: 0,          // Counter for bets placed since last analysis
            betsBeforeRecalc: 1   // Recalculate after every bet
        };

        // Generate a random number between 0 and 1
        function random() {
            // Use standard Math.random()
            return Math.random();
        }

        // Generate a binary 50:50 choice (0 or 1)
        function binaryChoice() {
            // Simple Math.random() for 50:50 choice
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
            // E.g., 102 becomes 2, 278 becomes 78
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
                // Find the big road SVG element - this selector may need adjustment
                const bigRoadSvg = tableElement.querySelector('.TileStatistics_bigroad-mobile-container__PDt8X');
                if (!bigRoadSvg) return [];
                
                // Extract all use elements which represent the markers
                const markers = Array.from(bigRoadSvg.querySelectorAll('use'));
                
                // Map markers to results (P for Player, B for Banker, T for Tie)
                const results = markers.map(marker => {
                    const href = marker.getAttribute('xlink:href') || '';
                    if (href.includes('bigroad-P')) return 'P'; // Player
                    if (href.includes('bigroad-B')) return 'B'; // Banker
                    if (href.includes('bigroad-T')) return 'T'; // Tie
                    return null;
                }).filter(result => result !== null);
                
                return results;
            } catch (error) {
                console.error('Error extracting big road data:', error);
                return [];
            }
        }

        // Calculate alternation rate for the most recent N rounds
        function calculateRecentAlternationRate(results) {
            if (results.length < CONFIG.minRoundsForAnalysis) return 0;
            
            // Get only the most recent rounds (capped at recentRoundsToConsider)
            const recentResults = results.slice(-CONFIG.recentRoundsToConsider);
            
            if (recentResults.length <= 1) return 0;
            
            // Count alternations in recent results
            let alternations = 0;
            for (let i = 1; i < recentResults.length; i++) {
                if (recentResults[i] !== recentResults[i-1]) {
                    alternations++;
                }
            }
            
            // Calculate alternation rate (0-1)
            return alternations / (recentResults.length - 1);
        }

        // Calculate total score for a table based on its results
        function calculateTableScore(results) {
            // No calculation if minimum rounds not met
            if (results.length < CONFIG.minRoundsForAnalysis) return 0;
            
            // Score is solely based on recent alternation rate
            return calculateRecentAlternationRate(results);
        }

        // Count tie results in a table
        function countTies(results) {
            if (results.length < CONFIG.minRoundsForAnalysis) return 999; // High value for tables with insufficient data
            
            // Count ties in the results
            return results.filter(result => result === 'T').length;
        }

        // Analyze all tables and update scores
        function analyzeAllTables() {
            try {
                // Find all table elements
                const counters = document.querySelectorAll(CONFIG.counterSelector);
                if (!counters || counters.length === 0) return;
                
                // Process each table
                counters.forEach(counter => {
                    const parentElement = counter.parentElement?.parentElement?.parentElement?.parentElement?.parentElement;
                    if (!parentElement) return;
                    
                    const tableId = getTableIdentifier(parentElement);
                    
                    // Extract results from big road
                    const results = extractBigRoadData(parentElement);
                    
                    // Calculate recent alternation rate (keeping for reference)
                    const recentResults = results.slice(-CONFIG.recentRoundsToConsider);
                    
                    let alternationPct = 0;
                    if (recentResults.length > 1) {
                        let alternations = 0;
                        for (let i = 1; i < recentResults.length; i++) {
                            if (recentResults[i] !== recentResults[i-1]) {
                                alternations++;
                            }
                        }
                        alternationPct = (alternations / (recentResults.length - 1)) * 100;
                    }
                    
                    // Count ties in the results
                    const tieCount = countTies(results);
                    
                    // Store or update table data
                    TABLES.data[tableId] = {
                        element: parentElement,
                        counter: counter,
                        results: results,
                        recentResults: recentResults,
                        score: calculateTableScore(results), // Keep for reference
                        alternationPct: alternationPct,      // Keep for reference
                        tieCount: tieCount,                  // New property for tie count
                        lastUpdated: Date.now()
                    };
                });
                
                // Sort tables by tie count (ascending) and select top tables
                const sortedTables = Object.entries(TABLES.data)
                    .sort((a, b) => a[1].tieCount - b[1].tieCount)
                    .slice(0, CONFIG.maxTablesToMonitor)
                    .map(entry => entry[0]);
                
                // Update target tables
                CONFIG.targetTables = sortedTables;
                
                // Log table analysis
                console.log(
                    '%cTable Analysis Completed',
                    'color: #4CAF50; font-weight: bold; font-size: 14px'
                );
                
                // Log top tables
                console.log(
                    '%cTop Tables for Betting (Least Ties):',
                    'color: #FF9800; font-weight: bold; font-size: 12px'
                );
                
                sortedTables.forEach((tableId, index) => {
                    const table = TABLES.data[tableId];
                    const tableColor = getTableColor(tableId);
                    console.log(
                        `%c${index + 1}. ${tableId}: %cTie Count: ${table.tieCount} | Recent Rounds: ${table.recentResults.length} of ${table.results.length}`,
                        `color: ${tableColor}; font-weight: bold`,
                        'color: #333'
                    );
                });
                
                // Update timestamp
                TABLES.lastAnalysis = Date.now();
                
                // Clean up observers and setup new ones for top tables
                updateObservers();
                
            } catch (error) {
                console.error('Error analyzing tables:', error);
            }
        }

        // Update observers for target tables
        function updateObservers() {
            // Clear all existing observers that are not in target tables
            for (const [tableId, observer] of TABLES.observers.entries()) {
                if (!CONFIG.targetTables.includes(tableId)) {
                    observer.disconnect();
                    TABLES.observers.delete(tableId);
                    console.log(`Stopped monitoring table: ${tableId}`);
                }
            }
            
            // Setup observers for target tables
            CONFIG.targetTables.forEach(tableId => {
                if (!TABLES.observers.has(tableId) && TABLES.data[tableId]) {
                    const counter = TABLES.data[tableId].counter;
                    setupTieCounterObserver(counter);
                }
            });
        }

        // Setup observer for TIE counter changes
        function setupTieCounterObserver(counter) {
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
                            
                            // Place bet on every round
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
                
                // Store observer reference both in TABLES and in the global instance
                TABLES.observers.set(tableId, observer);
                window.BACCARAT_AUTO_BETTING_INSTANCE.observers.add(observer);
                
                // Log with table color
                const tableColor = getTableColor(tableId);
                console.log(
                    `%c${tableId}: %cStarted monitoring for betting on EVERY round (top table)`,
                    `color: ${tableColor}; font-weight: bold`,
                    'color: #666; font-style: italic'
                );
            } catch (error) {
                console.error('Error setting up observer:', error);
            }
        }

        // Place bet on a randomly chosen side
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
            
            // Use binary choice for 50:50 distribution
            const randomChoice = binaryChoice() === 0 ? "banker" : "player";
            const targetButton = randomChoice === "banker" ? bankerButton : playerButton;
            
            if (!targetButton) return;
            
            // Colorful logging based on table and bet type
            const colors = {
                banker: '#FF5722', // Orange for banker
                player: '#2196F3'  // Blue for player
            };
            

            // Generate a consistent color for the table name based on the table ID
            const tableColor = getTableColor(tableId);
            
            // Log with colors, round number and calculation details
            console.log(
                `%c${tableId}: %c${randomChoice.toUpperCase()} $${betAmount} %c[${balance.toFixed(0)}→${effectiveBalance.toFixed(0)}→$${betAmount}]`,
                `color: ${tableColor}; font-weight: bold`,
                `color: ${colors[randomChoice]}; font-weight: bold`,
                'color: #999; font-style: italic'
            );
            
            // Add random delay before placing bet
            setTimeout(() => {
                simulateBetClicks(targetButton, betAmount);
            }, getRandomDelay());
            
            // Increment bet counter
            TABLES.betCount++;
            
            // Check if we should recalculate scores
            if (TABLES.betCount >= TABLES.betsBeforeRecalc) {
                console.log(
                    '%cRecalculating scores after each bet',
                    'color: #FF9800; font-style: italic;'
                );
                // Reset counter
                TABLES.betCount = 0;
                // Recalculate after a delay to allow game state to update
                setTimeout(() => {
                    analyzeAllTables();
                }, 2000);
            }
        }

        // Create a simple stats panel to show top tables
        function createStatsPanel() {
            const panel = document.createElement('div');
            panel.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px;
                border-radius: 5px;
                z-index: 10000;
                font-family: Arial, sans-serif;
                font-size: 12px;
                min-width: 200px;
                max-width: 300px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
                transition: opacity 0.3s ease;
            `;
            
            // Create a close/hide button
            const closeButton = document.createElement('div');
            closeButton.innerHTML = '✕';
            closeButton.style.cssText = `
                position: absolute;
                top: 5px;
                right: 10px;
                cursor: pointer;
                font-size: 16px;
                color: #AAA;
            `;
            closeButton.addEventListener('click', function() {
                panel.style.opacity = '0';
                setTimeout(() => {
                    panel.style.display = 'none';
                }, 300);
                // Set hidden state
                window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden = true;
            });
            
            // Create a show/hide toggle button that stays visible
            const toggleButton = document.createElement('div');
            toggleButton.innerHTML = '🎲';
            toggleButton.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                width: 30px;
                height: 30px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                border-radius: 50%;
                text-align: center;
                line-height: 30px;
                cursor: pointer;
                z-index: 10001;
                box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
                font-size: 16px;
                display: none;
            `;
            toggleButton.addEventListener('click', function() {
                if (window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden) {
                    panel.style.display = 'block';
                    setTimeout(() => {
                        panel.style.opacity = '1';
                    }, 10);
                    toggleButton.style.display = 'none';
                    window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden = false;
                }
            });
            
            // Add the toggle button to the body
            document.body.appendChild(toggleButton);
            
            // Store toggle button reference
            window.BACCARAT_AUTO_BETTING_INSTANCE.toggleButton = toggleButton;
            
            // Create header with title
            const header = document.createElement('div');
            header.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            `;
            
            const title = document.createElement('h3');
            title.textContent = 'Baccarat Auto-Betting';
            title.style.cssText = `
                margin: 0;
                color: #4CAF50;
                padding-right: 20px;
            `;
            
            header.appendChild(title);
            header.appendChild(closeButton);
            
            panel.appendChild(header);
            
            // Add content div
            const content = document.createElement('div');
            content.id = 'stats-content';
            panel.appendChild(content);
            
            document.body.appendChild(panel);
            
            // Add keyboard shortcut to toggle panel (Alt+B)
            document.addEventListener('keydown', function(e) {
                // Alt+B to toggle
                if (e.altKey && e.key === 'b') {
                    if (window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden) {
                        panel.style.display = 'block';
                        setTimeout(() => {
                            panel.style.opacity = '1';
                        }, 10);
                        toggleButton.style.display = 'none';
                        window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden = false;
                    } else {
                        panel.style.opacity = '0';
                        setTimeout(() => {
                            panel.style.display = 'none';
                        }, 300);
                        toggleButton.style.display = 'block';
                        window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden = true;
                    }
                }
            });
            
            // Update stats panel with current stats
            function updateStatsPanel() {
                const content = document.getElementById('stats-content');
                if (!content) return;
                
                let html = '<div style="margin-bottom: 5px;"><b>Top Tables (Least Ties):</b></div>';
                
                if (CONFIG.targetTables.length === 0) {
                    html += '<div style="color: #FFD700;">Analyzing tables...</div>';
                } else {
                    CONFIG.targetTables.forEach((tableId, index) => {
                        const table = TABLES.data[tableId];
                        if (!table) return;
                        
                        const tableColor = getTableColor(tableId);
                        
                        // Display recent pattern for better visualization
                        const recentPattern = table.recentResults.join('');
                        
                        html += `
                            <div style="margin-bottom: 5px; border-bottom: 1px solid #444; padding-bottom: 5px;">
                                <div style="color: ${tableColor}; font-weight: bold;">${index + 1}. ${tableId}</div>
                                <div>Tie Count: <span style="color:#FFD700">${table.tieCount}</span></div>
                                <div>Recent (${table.recentResults.length} of ${table.results.length}): <span style="color: #FFD700;">${recentPattern}</span></div>
                                <div>Full Road: ${table.results.join('')}</div>
                            </div>
                        `;
                    });
                }
                
                html += `<div style="margin-top: 10px; font-size: 10px; color: #AAA;">Recalculating after every bet</div>`;
                html += `<div style="margin-top: 5px; font-size: 10px; color: #AAA;">Alt+B to toggle panel visibility</div>`;
                
                content.innerHTML = html;
            }
            
            // Update stats panel regularly
            const intervalId = setInterval(updateStatsPanel, 1000);
            window.BACCARAT_AUTO_BETTING_INSTANCE.intervals.add(intervalId);
            
            // Store panel reference for cleanup
            window.BACCARAT_AUTO_BETTING_INSTANCE.panel = panel;
            window.BACCARAT_AUTO_BETTING_INSTANCE.panelHidden = false;
            
            return panel;
        }

        // Start monitoring for TIE counters
        function startMonitoring() {
            try {
                // Initial analysis of all tables
                analyzeAllTables();
                
                // Initialize bet counter
                TABLES.betCount = 0;
                
                // Create stats panel
                createStatsPanel();
                
                // Colorful logging for system start
                console.log(
                    '%cEnhanced Monitoring system started successfully (v' + window.BACCARAT_AUTO_BETTING_INSTANCE.version + ')',
                    'color: #4CAF50; font-weight: bold; font-size: 14px'
                );
                console.log(
                    '%cScores will be recalculated after every 10 bets',
                    'color: #4CAF50; font-style: italic;'
                );
            } catch (error) {
                console.error('Error starting monitoring:', error);
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
