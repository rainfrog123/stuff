// ==UserScript==
// @name         Baccarat Smart Auto Betting System
// @namespace    http://tampermonkey.net/
// @version      9.4
// @description  Advanced auto betting system for Baccarat with enhanced randomness
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_log
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        CHIPS: {
            SMALL: {
                VALUE: 0.2,
                SELECTOR: '#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > span:nth-child(1)'
            },
            MEDIUM: {
                VALUE: 1.0,
                SELECTOR: '#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > span:nth-child(2)'
            }
        },
        MIN_BET: 0.2,
        BET_PERCENTAGE: {
            MIN: 0.25,
            MAX: 0.5
        },
        DELAYS: {
            BET: { MIN: 5000, MAX: 8000 },
            CLICK: { MIN: 3, MAX: 15 }
        },
        ROUNDS: { 
            MIN: 1, 
            MAX: 3
        },
        SELECTORS: {
            PLAYER: '.PLAYER_PATH .betspotAsset',
            BANKER: '.BANKER_PATH .betspotAsset',
            BALANCE: '.balanceContainer .balance .amt'
        },
        DEBUG: false,
        RETRY_INTERVAL: 5000
    };

    // STATE object to track script state
    const STATE = {
        running: false,
        currentBet: null,
        currentBetPercentage: 0,
        stats: { wins: 0, losses: 0, ties: 0, totalWon: 0, totalLost: 0 },
        roundCounter: 0,
        currentRound: 0,
        roundsToWait: 0,
        lastBetTime: 0,
        isProcessingBet: false,
        isBettingLocked: false,
        waitingForResult: false,
        lastResult: null,
        lastDetectedResult: null,
        errorCount: 0,
        sessionBets: { Player: 0, Banker: 0, total: 0 },
        lastBet: null,
        currentMaxBet: 0,
        entropyPool: new Uint32Array(16),
        lastRandomValues: new Uint8Array(4),
        
        resetRoundCounter() {
            this.roundCounter = 0;
            this.roundsToWait = Math.floor(getRandomNumber(CONFIG.ROUNDS.MIN, CONFIG.ROUNDS.MAX));
            utils.log(`⏳ Waiting ${this.roundsToWait} rounds before betting`);
        },
        
        incrementRound() {
            this.roundCounter++;
            const remaining = this.roundsToWait - this.roundCounter;
            if (remaining > 0) {
                utils.log(`⏳ Waiting ${remaining} rounds before betting`);
                return false;
            } else {
                utils.log(`✅ Ready to bet now!`);
                return true;
            }
        }
    };

    // Utility functions
    const utils = {
        getRandomNumber: (min, max) => {
            return min + Math.random() * (max - min);
        },
        
        log: (message, type = "info") => {
            console.log(`[Bet] ${message}`);
        },
        
        getElement: (selector, name) => {
            const element = document.querySelector(selector);
            if (!element && CONFIG.DEBUG) console.warn(`[Bet] ${name || 'Element'} not found`);
            return element;
        },
        
        retry: async (fn, maxRetries = 3, interval = CONFIG.RETRY_INTERVAL) => {
            let retries = 0;
            while (true) {
                try {
                    return await fn();
                } catch (error) {
                    retries++;
                    if (retries >= maxRetries) throw error;
                    await new Promise(resolve => setTimeout(resolve, interval));
                }
            }
        },
        
        checkUIReady: () => {
            // Implementation of checkUIReady function
        }
    };

    // Core betting functions
    const betting = {
        getBalance: () => {
            const balanceElement = utils.getElement(CONFIG.SELECTORS.BALANCE, 'Balance');
            if (!balanceElement) return null;
            
            const balance = parseFloat(balanceElement.textContent.replace(/[^0-9.]/g, ''));
            return (!isNaN(balance) && balance >= CONFIG.MIN_BET) ? balance : null;
        },
        
        calculateBetAmount: () => {
            const balance = betting.getBalance();
            if (!balance) return null;
            
            // Generate random bet percentage
            const randomBetPercentage = utils.getRandomNumber(CONFIG.BET_PERCENTAGE.MIN, CONFIG.BET_PERCENTAGE.MAX);
            
            // Calculate max bet based on balance
            const maxBet = balance * randomBetPercentage;
            
            // Store for logging
            STATE.currentMaxBet = maxBet;
            STATE.currentBetPercentage = randomBetPercentage;
            
            // Calculate bet amount with minimum of 0.2
            let betAmount = Math.round(utils.getRandomNumber(CONFIG.MIN_BET, maxBet) * 10) / 10;
            
            // Ensure minimum bet is 0.2
            betAmount = Math.max(betAmount, 0.2);
            
            return betAmount;
        },
        
        chooseBetType: () => {
            // Simple 50:50 choice
            const choice = Math.random() < 0.5 ? "Player" : "Banker";
            STATE.sessionBets[choice]++;
            STATE.sessionBets.total++;
            return choice;
        },
        
        placeBet: async (betType, amount) => {
            try {
                if (STATE.waitingForResult) {
                    utils.log("Still waiting for result from previous bet", "warn");
                    return false;
                }
                
                // Select bet spot
                const betSelector = betType === "Player" ? CONFIG.SELECTORS.PLAYER : CONFIG.SELECTORS.BANKER;
                const betElement = utils.getElement(betSelector, betType);
                if (!betElement) return false;
                
                // Improved chip selection logic
                let remainingAmount = amount;
                let actualBetAmount = 0;
                
                // Use medium chips (1.0) first if amount >= 1.0
                if (remainingAmount >= CONFIG.CHIPS.MEDIUM.VALUE) {
                    const mediumChipElement = utils.getElement(CONFIG.CHIPS.MEDIUM.SELECTOR, 'Medium Chip');
                    if (mediumChipElement) {
                        // Click on medium chip
                        mediumChipElement.click();
                        await new Promise(resolve => setTimeout(resolve, utils.getRandomNumber(CONFIG.DELAYS.CLICK.MIN, CONFIG.DELAYS.CLICK.MAX)));
                        
                        // Calculate how many medium chips to place
                        const mediumChips = Math.floor(remainingAmount / CONFIG.CHIPS.MEDIUM.VALUE);
                        
                        // Place medium chips
                        for (let i = 0; i < mediumChips; i++) {
                            betElement.click();
                            await new Promise(resolve => setTimeout(resolve, utils.getRandomNumber(CONFIG.DELAYS.CLICK.MIN, CONFIG.DELAYS.CLICK.MAX)));
                            actualBetAmount += CONFIG.CHIPS.MEDIUM.VALUE;
                        }
                        
                        remainingAmount -= mediumChips * CONFIG.CHIPS.MEDIUM.VALUE;
                        remainingAmount = Math.round(remainingAmount * 10) / 10; // Fix floating point issues
                    }
                }
                
                // Use small chips (0.2) for the remainder if needed
                if (remainingAmount >= CONFIG.CHIPS.SMALL.VALUE) {
                    const smallChipElement = utils.getElement(CONFIG.CHIPS.SMALL.SELECTOR, 'Small Chip');
                    if (smallChipElement) {
                        // Click on small chip
                        smallChipElement.click();
                        await new Promise(resolve => setTimeout(resolve, utils.getRandomNumber(CONFIG.DELAYS.CLICK.MIN, CONFIG.DELAYS.CLICK.MAX)));
                        
                        // Calculate how many small chips to place
                        const smallChips = Math.round(remainingAmount / CONFIG.CHIPS.SMALL.VALUE);
                        
                        // Place small chips
                        for (let i = 0; i < smallChips; i++) {
                            betElement.click();
                            await new Promise(resolve => setTimeout(resolve, utils.getRandomNumber(CONFIG.DELAYS.CLICK.MIN, CONFIG.DELAYS.CLICK.MAX)));
                            actualBetAmount += CONFIG.CHIPS.SMALL.VALUE;
                        }
                    }
                }
                
                // Record bet with actual amount placed
                STATE.lastBet = { type: betType, amount: actualBetAmount };
                STATE.waitingForResult = true;
                
                utils.log(`✅ Bet placed: ${betType} $${actualBetAmount.toFixed(1)}`);
                STATE.errorCount = 0;
                
                // Reset round counter after successful bet to start waiting for next bet
                STATE.resetRoundCounter();
                
                return true;
            } catch (error) {
                utils.log(`Error: ${error.message}`, "error");
                STATE.errorCount++;
                return false;
            } finally {
                STATE.isProcessingBet = false;
            }
        },
        
        handleBet: () => {
            // Prevent multiple bets in quick succession
            const now = Date.now();
            const timeSinceLastBet = now - STATE.lastBetTime;
            
            // Skip if already processing or locked
            if (STATE.isProcessingBet || STATE.isBettingLocked) return;
            
            // Ensure minimum time between bets
            if (timeSinceLastBet < 10000) return;
            
            // Check if we should bet this round
            if (!STATE.incrementRound()) return;
            
            // Set processing flag
            STATE.isProcessingBet = true;
            
            // Calculate bet amount - only reset counter after a successful bet
            const betAmount = betting.calculateBetAmount();
            if (!betAmount) {
                STATE.isProcessingBet = false;
                return;
            }
            
            const betChoice = betting.chooseBetType();
            
            // Use variable delay
            const delay = utils.getRandomNumber(CONFIG.DELAYS.BET.MIN, CONFIG.DELAYS.BET.MAX);
            
            // Log bet preparation
            utils.log(`Preparing ${betChoice} bet: $${betAmount.toFixed(1)} (${(STATE.currentBetPercentage * 100).toFixed(0)}% of $${betting.getBalance().toFixed(1)})`);
            
            // Lock betting
            STATE.isBettingLocked = true;
            STATE.lastBetTime = now;
            
            setTimeout(() => {
                utils.retry(() => betting.placeBet(betChoice, betAmount))
                    .catch(error => utils.log(`Failed to place bet: ${error.message}`, "error"))
                    .finally(() => {
                        STATE.isProcessingBet = false;
                        // Release the lock after 15 seconds
                        setTimeout(() => {
                            STATE.isBettingLocked = false;
                        }, 15000);
                    });
            }, delay);
        }
    };

    // Event listener for game results
    window.addEventListener('ResultDetected', function(e) {
        const { name } = e.detail;
        if (["B", "T", "P"].includes(name)) {
            // Simplified logging - just log the result without details
            if (CONFIG.DEBUG) utils.log(`Result: ${name}`);
            
            // Check if we were waiting for a result after betting
            if (STATE.waitingForResult && STATE.lastBet) {
                // Determine if we won or lost
                if (name === "T") {
                    utils.log(`🔄 TIE - Bet returned`);
                    STATE.stats.ties++;
                } else if ((STATE.lastBet.type === "Player" && name === "P") || 
                           (STATE.lastBet.type === "Banker" && name === "B")) {
                    // Win
                    let winAmount = STATE.lastBet.type === "Player" ? 
                        STATE.lastBet.amount : // Player pays 1:1
                        STATE.lastBet.amount * 0.95; // Banker pays 0.95:1 (5% commission)
                    
                    STATE.stats.wins++;
                    STATE.stats.totalWon += winAmount;
                    utils.log(`✅ WIN: +$${winAmount.toFixed(2)}`);
                } else {
                    // Loss
                    STATE.stats.losses++;
                    STATE.stats.totalLost += STATE.lastBet.amount;
                    utils.log(`❌ LOSS: -$${STATE.lastBet.amount.toFixed(2)}`);
                }
                
                // Reset waiting flag
                STATE.waitingForResult = false;
                STATE.lastBet = null;
                
                // Refresh entropy pool occasionally
                if (Math.random() < 0.3) { // 30% chance
                    refreshEntropy();
                    utils.log("🔄 Refreshing entropy");
                }
            }
            
            STATE.lastDetectedResult = name;
            
            // Use variable delay with Math.random
            const betDelay = 300 + Math.floor(utils.getRandomNumber(0, 400));
            setTimeout(() => betting.handleBet(), betDelay);
        }
    });

    // Create or update visual status display
    function updateStatusDisplay() {
        let statusDiv = document.getElementById('baccarat-status-display');
        
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'baccarat-status-display';
            statusDiv.style.position = 'fixed';
            statusDiv.style.top = '10px';
            statusDiv.style.right = '10px';
            statusDiv.style.backgroundColor = 'rgba(0,0,0,0.8)';
            statusDiv.style.color = 'white';
            statusDiv.style.padding = '10px';
            statusDiv.style.borderRadius = '5px';
            statusDiv.style.zIndex = '9999';
            statusDiv.style.fontFamily = 'Arial, sans-serif';
            statusDiv.style.fontSize = '14px';
            statusDiv.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
            document.body.appendChild(statusDiv);
        }
        
        const netProfit = STATE.stats.totalWon - STATE.stats.totalLost;
        const profitSymbol = netProfit >= 0 ? '+' : '';
        const winRate = STATE.stats.wins + STATE.stats.losses > 0 
            ? Math.round((STATE.stats.wins / (STATE.stats.wins + STATE.stats.losses)) * 100) 
            : 0;
            
        const profitColor = netProfit >= 0 ? 'lime' : 'red';
        
        statusDiv.innerHTML = `
            <div style="font-weight: bold; text-align: center; margin-bottom: 5px; border-bottom: 1px solid #444; padding-bottom: 5px;">
                BACCARAT SMART BETTING v9.4
            </div>
            <div style="margin: 5px 0;">
                Record: <b>${STATE.stats.wins}W-${STATE.stats.losses}L-${STATE.stats.ties}T</b> (${winRate}% win)
            </div>
            <div style="margin: 5px 0;">
                Profit: <b style="color: ${profitColor}">${profitSymbol}$${netProfit.toFixed(2)}</b>
            </div>
            <div style="margin: 5px 0; font-size: 12px;">
                Won: $${STATE.stats.totalWon.toFixed(2)} | Lost: $${STATE.stats.totalLost.toFixed(2)}
            </div>
            <div style="margin-top: 8px; font-size: 11px; text-align: center; color: #aaa;">
                Ctrl+Alt+R to reset stats
            </div>
        `;
    }
    
    // Update status display periodically
    setInterval(updateStatusDisplay, 5000);

    // Function to reset stats
    function resetStats() {
        STATE.stats = { wins: 0, losses: 0, ties: 0, totalWon: 0, totalLost: 0 };
        GM_setValue('baccarat_stats', JSON.stringify(STATE.stats));
        utils.log("📊 Stats reset");
        updateStatusDisplay();
    }
    
    // Add keyboard shortcut to reset stats (Ctrl+Alt+R)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.altKey && e.key === 'r') {
            resetStats();
        }
    });

    // Initialize random state with Math.random
    function initializeRandomState() {
        return {
            randomValues: Array(5).fill(0).map(() => Math.random()),
            lastRandomValues: Array(5).fill(0).map(() => Math.random()),
            entropyPool: Array(10).fill(0).map(() => Math.random())
        };
    }

    // Refresh entropy with Math.random
    function refreshEntropy() {
        STATE.entropyPool = Array(10).fill(0).map(() => Math.random());
        STATE.lastRandomValues = Array(5).fill(0).map(() => Math.random());
    }

    // Initialize
    function initialize() {
        utils.log("Script initialized v9.4");
        
        // Load saved stats if available
        const savedStats = GM_getValue('baccarat_stats', null);
        if (savedStats) {
            try {
                STATE.stats = JSON.parse(savedStats);
                const netProfit = STATE.stats.totalWon - STATE.stats.totalLost;
                utils.log(`📊 Loaded stats: ${STATE.stats.wins}W-${STATE.stats.losses}L (${netProfit >= 0 ? '+' : ''}$${netProfit.toFixed(2)})`);
            } catch (e) {
                utils.log("Error loading stats, starting fresh", "warn");
                STATE.stats = { wins: 0, losses: 0, ties: 0, totalWon: 0, totalLost: 0 };
            }
        }
        
        // Initialize the round counter
        STATE.resetRoundCounter();
        
        // Check if UI is ready
        utils.retry(utils.checkUIReady, 5, 2000)
            .then(() => utils.log("UI ready"))
            .catch(() => utils.log("UI check timed out", "warn"));
            
        // Save stats periodically
        setInterval(() => {
            GM_setValue('baccarat_stats', JSON.stringify(STATE.stats));
        }, 30000);
        
        // Show status display immediately
        setTimeout(updateStatusDisplay, 2000);
        
        // Initialize entropy pool
        STATE.entropyPool = Array(10).fill(0).map(() => Math.random());
        STATE.lastRandomValues = Array(5).fill(0).map(() => Math.random());
    }
    
    // Start the script
    initialize();
})(); 