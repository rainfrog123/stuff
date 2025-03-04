// ==UserScript==
// @name         Baccarat Smart Auto-Betting System
// @namespace    http://tampermonkey.net/
// @version      4.0
// @description  Optimized baccarat betting automation with cryptographic randomization, dynamic bet sizing, and intelligent timing
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
        MIN_BET: 0.2,
        MAX_BET_PERCENTAGE: 0.25,
        DELAYS: {
            BET: { MIN: 3000, MAX: 5000 },
            CLICK: 5
        },
        ROUNDS: { MIN: 1, MAX: 3 },
        SELECTORS: {
            PLAYER: '.PLAYER_PATH .betspotAsset',
            BANKER: '.BANKER_PATH .betspotAsset',
            CHIP: '#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > span:nth-child(1)',
            BALANCE: '.balanceContainer .balance .amt'
        }
    };

    // State tracking
    const STATE = {
        currentRound: 0,
        roundsToWait: 0,
        sessionBets: { Player: 0, Banker: 0, total: 0 },
        resetRoundCounter() {
            this.currentRound = 0;
            this.roundsToWait = Math.floor(secureRandom(CONFIG.ROUNDS.MIN, CONFIG.ROUNDS.MAX + 1));
        }
    };

    // Initialize
    STATE.resetRoundCounter();

    // Utility functions
    const utils = {
        secureRandom: (min, max) => {
            const array = new Uint32Array(1);
            window.crypto.getRandomValues(array);
            return min + (array[0] / (0xFFFFFFFF + 1)) * (max - min);
        },
        
        getElement: (selector, name) => {
            const element = document.querySelector(selector);
            if (!element) console.warn(`[Betting] ${name || 'Element'} not found`);
            return element;
        },
        
        simulateClick: (element) => {
            if (!element) return false;
            try {
                element.click();
                return true;
            } catch (error) {
                console.error("[Betting] Click error:", error);
                return false;
            }
        },
        
        log: (message, type = 'log') => {
            console[type](`[Betting] ${message}`);
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
            
            const maxBet = Math.min(balance * CONFIG.MAX_BET_PERCENTAGE, balance);
            const betAmount = Math.max(CONFIG.MIN_BET, Math.round(utils.secureRandom(CONFIG.MIN_BET, maxBet) * 100) / 100);
            
            utils.log(`Bet: ${betAmount} (Balance: ${balance})`);
            return betAmount;
        },
        
        chooseBetType: () => {
            // Enhanced randomization with slight bias adjustment based on session history
            const sessionTotal = STATE.sessionBets.total;
            let playerProbability = 0.5;
            
            // Adjust probability slightly based on session history (if we have enough data)
            if (sessionTotal > 10) {
                const playerRatio = STATE.sessionBets.Player / sessionTotal;
                // Apply a small correction toward 50/50 distribution
                playerProbability = 0.5 + (0.5 - playerRatio) * 0.2;
            }
            
            const choice = utils.secureRandom(0, 1) < playerProbability ? "Player" : "Banker";
            STATE.sessionBets[choice]++;
            STATE.sessionBets.total++;
            return choice;
        },
        
        placeBet: async (betType, amount) => {
            const targetButton = utils.getElement(
                betType === "Player" ? CONFIG.SELECTORS.PLAYER : CONFIG.SELECTORS.BANKER, 
                betType
            );
            
            const chipElement = utils.getElement(CONFIG.SELECTORS.CHIP, 'Chip');
            if (!targetButton || !chipElement) return false;
            
            // Select chip first
            if (!utils.simulateClick(chipElement)) return false;
            
            // Calculate clicks needed
            const clicksNeeded = Math.floor(amount / CONFIG.MIN_BET);
            let successfulClicks = 0;
            
            // Place bets with slight randomized timing
            for (let i = 0; i < clicksNeeded; i++) {
                await new Promise(resolve => {
                    setTimeout(() => {
                        if (utils.simulateClick(targetButton)) successfulClicks++;
                        resolve();
                    }, i * CONFIG.DELAYS.CLICK + Math.floor(utils.secureRandom(1, 3)));
                });
            }
            
            const actualBet = successfulClicks * CONFIG.MIN_BET;
            utils.log(`Placed ${betType} bet: $${actualBet}`);
            return true;
        },
        
        handleBet: () => {
            STATE.currentRound++;
            
            // Skip if we're waiting for more rounds
            if (STATE.currentRound < STATE.roundsToWait) return;
            
            // Reset counter and calculate new wait period
            STATE.resetRoundCounter();
            
            const betAmount = betting.calculateBetAmount();
            if (!betAmount) return;
            
            const betChoice = betting.chooseBetType();
            const delay = Math.floor(utils.secureRandom(CONFIG.DELAYS.BET.MIN, CONFIG.DELAYS.BET.MAX));
            
            utils.log(`Will bet on ${betChoice} in ${delay}ms`);
            
            setTimeout(() => betting.placeBet(betChoice, betAmount), delay);
        }
    };

    // Event listener for game results
    window.addEventListener('ResultDetected', function(e) {
        const { name } = e.detail;
        if (["B", "T", "P"].includes(name)) {
            betting.handleBet();
        }
    });

    // Initialize
    utils.log("Script initialized v4.0");
})(); 