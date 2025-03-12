// ==UserScript==
// @name         Baccarat Simple 
// @namespace    http://tampermonkey.net/
// @version      1.4
// @description  Places a 0.2 bet on Player or Banker every 4-6 rounds
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_log
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // Simple configuration
    const CONFIG = {
        BET_AMOUNT: 0.2,                  // Fixed bet amount
        ROUNDS_MIN: 4,                    // Minimum rounds to wait before betting
        ROUNDS_MAX: 6,                    // Maximum rounds to wait before betting
        SELECTORS: {
            PLAYER: '.PLAYER_PATH .betspotAsset',
            BANKER: '.BANKER_PATH .betspotAsset',
            BALANCE: '.balanceContainer .balance .amt',
            SMALL_CHIP: '#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > span:nth-child(1)'
        },
        DELAYS: {
            BET: { MIN: 3000, MAX: 5000 },  // Delay before placing bet
            CLICK: { MIN: 10, MAX: 50 }     // Delay between clicks
        }
    };

    // State tracking
    const STATE = {
        roundCounter: 0,
        roundsToWait: 0,
        waitingForResult: false,
        lastBetTime: 0,
        isProcessingBet: false,
        
        // Reset round counter and set random rounds to wait
        resetRoundCounter() {
            this.roundCounter = 0;
            this.roundsToWait = Math.floor(Math.random() * (CONFIG.ROUNDS_MAX - CONFIG.ROUNDS_MIN + 1)) + CONFIG.ROUNDS_MIN;
        },
        
        // Increment round counter and check if it's time to bet
        shouldBet() {
            this.roundCounter++;
            return this.roundCounter >= this.roundsToWait;
        }
    };

    // Initialize state
    STATE.resetRoundCounter();

    // Simple logging function - only used for bet placement
    function log(message) {
        console.log(`[SimpleBet] ${message}`);
    }

    // Get element by selector
    function getElement(selector) {
        return document.querySelector(selector);
    }

    // Get random number between min and max
    function getRandomDelay(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    // Choose randomly between Player and Banker
    function chooseBetType() {
        return Math.random() < 0.5 ? "Player" : "Banker";
    }

    // Place bet on selected side with proper chip selection
    async function placeBet(betType) {
        try {
            // Don't place a bet if we're still waiting for a result or processing
            if (STATE.waitingForResult || STATE.isProcessingBet) {
                return false;
            }
            
            STATE.isProcessingBet = true;
            
            // Select bet spot based on bet type
            const betSelector = betType === "Player" ? CONFIG.SELECTORS.PLAYER : CONFIG.SELECTORS.BANKER;
            const betElement = getElement(betSelector);
            const chipElement = getElement(CONFIG.SELECTORS.SMALL_CHIP);
            
            if (!betElement || !chipElement) {
                STATE.isProcessingBet = false;
                return false;
            }
            
            // First click on the chip to select it
            chipElement.click();
            
            // Wait a random delay between selecting chip and placing bet
            await new Promise(resolve => setTimeout(resolve, getRandomDelay(CONFIG.DELAYS.CLICK.MIN, CONFIG.DELAYS.CLICK.MAX)));
            
            // Then click on the betting spot
            betElement.click();
            
            // Only log when a bet is placed
            log(`Bet placed: ${CONFIG.BET_AMOUNT} on ${betType}`);
            
            // Update state
            STATE.waitingForResult = true;
            STATE.lastBetTime = Date.now();
            
            // Reset round counter for next bet cycle
            STATE.resetRoundCounter();
            
            return true;
        } catch (error) {
            return false;
        } finally {
            // Release the processing flag after a delay
            setTimeout(() => {
                STATE.isProcessingBet = false;
            }, 5000);
        }
    }

    // Handle game results
    window.addEventListener('ResultDetected', function(e) {
        const { name } = e.detail;
        
        if (["B", "T", "P"].includes(name)) {
            // Reset waiting flag if we were waiting for a result
            if (STATE.waitingForResult) {
                STATE.waitingForResult = false;
            }
            
            // Check if it's time to place a bet
            if (STATE.shouldBet()) {
                const betType = chooseBetType();
                
                // Add a random delay before placing the bet
                const betDelay = getRandomDelay(CONFIG.DELAYS.BET.MIN, CONFIG.DELAYS.BET.MAX);
                setTimeout(() => {
                    placeBet(betType);
                }, betDelay);
            }
        }
    });

    // Create a simple status indicator
    function createStatusIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'simple-bet-indicator';
        indicator.style.position = 'fixed';
        indicator.style.bottom = '5px';
        indicator.style.left = '5px';
        indicator.style.backgroundColor = 'rgba(0,0,0,0.5)';
        indicator.style.color = '#00ff00';
        indicator.style.padding = '3px 6px';
        indicator.style.borderRadius = '3px';
        indicator.style.fontSize = '10px';
        indicator.style.zIndex = '9999';
        indicator.style.fontFamily = 'monospace';
        indicator.textContent = 'BET';
        
        document.body.appendChild(indicator);
        
        // Update indicator with current round count
        setInterval(() => {
            indicator.textContent = `${STATE.roundCounter}/${STATE.roundsToWait}`;
        }, 2000);
    }

    // Initialize the script
    function initialize() {
        // Create status indicator after a short delay
        setTimeout(createStatusIndicator, 3000);
    }

    // Start the script when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})(); 