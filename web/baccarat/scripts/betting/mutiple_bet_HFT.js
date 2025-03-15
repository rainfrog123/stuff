// ==UserScript==
// @name         Baccarat HFT Auto-Betting System
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  High-Frequency Trading system that places bets on banker or player whenever any counter changes
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
        minCounterValue: 2,              // Minimum counter value required to place a bet
        maxCounterValue: 50,             // Maximum counter value allowed to place a bet
        debounceTime: 2000               // Time to wait before processing another counter change (ms)
    };

    // Store the last bet time for each table to prevent multiple bets
    const lastBetTime = {};
    
    // Store the last processed counter values to prevent duplicate processing
    const lastProcessedCounters = {};

    // Generate a cryptographically secure random number between 0 and 1
    function secureRandom() {
        // Use Web Crypto API for better randomness
        const array = new Uint32Array(1);
        window.crypto.getRandomValues(array);
        // Convert to a number between 0 and 1
        return array[0] / (0xFFFFFFFF + 1);
    }

    // Generate a true binary 50:50 choice (0 or 1)
    function secureBinaryChoice() {
        // Get 8 random bits and use just 1 bit for the decision
        // This ensures a perfect 50:50 distribution
        const array = new Uint8Array(1);
        window.crypto.getRandomValues(array);
        // Use just the least significant bit (0 or 1)
        return array[0] & 1;
    }

    // Get random delay
    function getRandomDelay() {
        return CONFIG.betDelayMin + (secureRandom() * CONFIG.betDelayRandom);
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
        
        // Cap the balance at 100 for calculation purposes
        const effectiveBalance = balance > 100 ? 100 : balance;
        
        const maxBetAmount = effectiveBalance * CONFIG.maxBalancePercentage;
        const randomValue = secureRandom();
        let betAmount = Math.round((randomValue * maxBetAmount) * 100) / 100;
        
        return Math.max(betAmount, CONFIG.minBetAmount);
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

    // Check if enough time has passed since the last bet
    function canPlaceBet(tableId) {
        const now = Date.now();
        if (!lastBetTime[tableId]) {
            lastBetTime[tableId] = 0;
        }
        
        // Check if enough time has passed since the last bet
        if (now - lastBetTime[tableId] < CONFIG.debounceTime) {
            return false;
        }
        
        // Update the last bet time immediately
        lastBetTime[tableId] = now;
        return true;
    }

    // Place bet with cryptographically secure random choice between banker and player
    function placeBet(tableId, bankerButton, playerButton, counterValue) {
        // Check if we can place a bet (debounce)
        if (!canPlaceBet(tableId)) {
            console.log(
                `%c${tableId}: %cSkipping bet for counter ${counterValue} (too soon after last bet)`,
                `color: ${getTableColor(tableId)}; font-weight: bold`,
                'color: #999; font-style: italic'
            );
            return;
        }
        
        const betAmount = calculateBetAmount();
        if (betAmount <= 0 || (!bankerButton && !playerButton)) return;
        
        // Use cryptographically secure binary choice for perfect 50:50 distribution
        const randomChoice = secureBinaryChoice() === 0 ? "banker" : "player";
        const targetButton = randomChoice === "banker" ? bankerButton : playerButton;
        
        if (!targetButton) {
            console.log(
                `%c${tableId}: %cCannot find ${randomChoice} button, skipping bet`,
                `color: ${getTableColor(tableId)}; font-weight: bold`,
                'color: #FF0000; font-weight: bold'
            );
            return;
        }
        
        // Colorful logging based on table and bet type
        const colors = {
            banker: '#FF5722', // Orange for banker
            player: '#2196F3'  // Blue for player
        };
        
        // Generate a consistent color for the table name based on the table ID
        const tableColor = getTableColor(tableId);
        
        // Log with colors and counter value
        console.log(
            `%c${tableId}: %cBetting ${betAmount} on %c${randomChoice.toUpperCase()} %cafter counter change to ${counterValue}`,
            `color: ${tableColor}; font-weight: bold`,
            'color: #333',
            `color: ${colors[randomChoice]}; font-weight: bold`,
            'color: #666'
        );
        
        // Add random delay before placing bet
        setTimeout(() => {
            simulateBetClicks(targetButton, betAmount);
        }, getRandomDelay());
    }

    // Setup observer for counter changes
    function setupCounterObserver(counter) {
        if (!counter) return;
        
        try {
            const parentElement = counter.parentElement?.parentElement?.parentElement?.parentElement?.parentElement;
            if (!parentElement) return;
            
            const tableId = getTableIdentifier(parentElement);
            
            // Initialize the last processed counter for this table
            if (!lastProcessedCounters[tableId]) {
                lastProcessedCounters[tableId] = '';
            }
            
            // Find betting buttons
            const { bankerButton, playerButton } = findBettingButtons(parentElement);
            
            // Store the last value to detect changes
            let lastValue = counter.textContent || '';
            
            // Create and setup the observer
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList' || mutation.type === 'characterData') {
                        const currentValue = counter.textContent || '';
                        
                        // Only proceed if the value has changed and hasn't been processed recently
                        if (currentValue !== lastValue && currentValue !== lastProcessedCounters[tableId]) {
                            // Update the last value
                            lastValue = currentValue;
                            
                            // Update the last processed counter immediately to prevent duplicate processing
                            lastProcessedCounters[tableId] = currentValue;
                            
                            // Extract the numeric value from the counter text (e.g., "#27" -> 27)
                            const numericMatch = currentValue.match(/#(\d+)/);
                            if (!numericMatch) continue;
                            
                            const numericValue = parseInt(numericMatch[1], 10);
                            
                            // Only place bet if counter value is within the allowed range
                            if (numericValue > CONFIG.minCounterValue && numericValue < CONFIG.maxCounterValue) {
                                // Place bet on counter change
                                placeBet(tableId, bankerButton, playerButton, currentValue);
                            } else {
                                // Log skipping bet due to counter value outside range
                                const tableColor = getTableColor(tableId);
                                let reason = numericValue <= CONFIG.minCounterValue ? 
                                    `value ≤ ${CONFIG.minCounterValue}` : 
                                    `value ≥ ${CONFIG.maxCounterValue}`;
                                
                                console.log(
                                    `%c${tableId}: %cSkipping bet for counter ${currentValue} (${reason})`,
                                    `color: ${tableColor}; font-weight: bold`,
                                    'color: #999; font-style: italic'
                                );
                            }
                            break; // Process only once per batch of mutations
                        }
                    }
                }
            });
            
            // Start observing the counter itself
            observer.observe(counter, {
                childList: true,
                characterData: true,
                subtree: true,
            });
            
            // Log with table color
            const tableColor = getTableColor(tableId);
            console.log(
                `%c${tableId}: %cHFT Monitoring for counter changes (will bet when ${CONFIG.minCounterValue} < counter < ${CONFIG.maxCounterValue})...`,
                `color: ${tableColor}; font-weight: bold`,
                'color: #666; font-style: italic'
            );
        } catch (error) {
            // Silently ignore errors
        }
    }

    // Start monitoring for counters
    function startMonitoring() {
        try {
            const counters = document.querySelectorAll(CONFIG.counterSelector);
            
            if (!counters || counters.length === 0) {
                setTimeout(startMonitoring, 5000);
                return;
            }
            
            // Setup observers for each counter
            counters.forEach(setupCounterObserver);
            
            // Colorful logging for system start
            console.log(
                '%cHFT Monitoring system started successfully (betting when ' + 
                CONFIG.minCounterValue + ' < counter < ' + CONFIG.maxCounterValue + 
                ', using cryptographically secure random selection)',
                'color: #4CAF50; font-weight: bold; font-size: 14px'
            );
        } catch (error) {
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