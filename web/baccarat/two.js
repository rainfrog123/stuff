// ==UserScript==
// @name         Baccarat Simple v2 - Fixed
// @namespace    http://tampermonkey.net/
// @version      4.3
// @description  Crypto-secure random betting - Fast 0.2 chip (1/8-1/2 balance) every 1-3 rounds
// @author       you
// @match        *://client.pragmaticplaylive.net/desktop/baccarat/*
// @grant        unsafeWindow
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    /**
     * Configuration
     */
    const CONFIG = {
        ROUND_DELAY: 10000,          // ms after result before betting (3 seconds)
        MIN_BET_FRACTION: 1/8,       // Minimum bet: 1/8 of balance
        MAX_BET_FRACTION: 1/2,      // Maximum bet: 1/2 of balance
        DEBUG: true,                // Enable debug logging
        SELECTORS: {
            roundNumber: '.ju_jv',
            counters: '.jN_jZ',
            counterTypes: '.jN_jQ',
            // Simplified betting selectors
            playerArea: '#leftBetTextRoot',
            bankerArea: '#rightBetTextRoot'
        }
    };

    /**
     * Crypto-based random utilities
     */
    class CryptoRandom {
        // Generate secure random boolean
        static randomBool() {
            return crypto.getRandomValues(new Uint8Array(1))[0] & 1;
        }

        // Generate secure random float between 0 and 1
        static randomFloat() {
            const array = new Uint32Array(1);
            crypto.getRandomValues(array);
            return array[0] / (0xFFFFFFFF + 1);
        }

        // Generate secure random integer between min and max (inclusive)
        static randomInt(min, max) {
            return Math.floor(this.randomFloat() * (max - min + 1)) + min;
        }

        // Choose Player or Banker randomly
        static randomSide() {
            return this.randomBool() ? 'Player' : 'Banker';
        }
    }

    /**
     * Simple logger
     */
    class Logger {
        static log(msg) {
            console.log(`[SmartBet] ${new Date().toLocaleTimeString()} - ${msg}`);
        }
        static debug(msg) {
            if (CONFIG.DEBUG) console.log(`[DEBUG] ${msg}`);
        }
    }

    /**
     * Simplified DOM utilities
     */
    class DOMUtils {
        static getRoundNumber() {
            const el = document.querySelector(CONFIG.SELECTORS.roundNumber);
            const match = el?.textContent?.match(/#(\d+)/);
            return match ? parseInt(match[1]) : 0;
        }

        static readCounters() {
            const counters = { P: 0, B: 0, T: 0 };
            const values = document.querySelectorAll(CONFIG.SELECTORS.counters);
            const types = document.querySelectorAll(CONFIG.SELECTORS.counterTypes);
            
            for (let i = 0; i < Math.min(values.length, types.length); i++) {
                const type = types[i]?.textContent?.trim();
                const value = parseInt(values[i]?.textContent?.trim() || '0');
                if (type && !isNaN(value) && counters.hasOwnProperty(type)) {
                    counters[type] = value;
                }
            }
            return counters;
        }

        static getPlayerArea() {
            return document.querySelector(CONFIG.SELECTORS.playerArea);
        }

        static getBankerArea() {
            return document.querySelector(CONFIG.SELECTORS.bankerArea);
        }

        static areElementsReady() {
            return !!(this.getPlayerArea() && this.getBankerArea());
        }
    }

    /**
     * Dynamic betting logic with balance-based amounts
     */
    class BettingLogic {
        static simulateClick(element) {
            try {
                // Simple and effective PointerEvent sequence
                const downEvent = new PointerEvent('pointerdown', {
                    bubbles: true,
                    cancelable: true,
                    pointerType: 'mouse',
                });

                const upEvent = new PointerEvent('pointerup', {
                    bubbles: true,
                    cancelable: true,
                    pointerType: 'mouse',
                });

                element.dispatchEvent(downEvent);
                element.dispatchEvent(upEvent);

                return true;
            } catch (error) {
                Logger.log(`❌ Click simulation error: ${error.message}`);
                return false;
            }
        }

        static getCurrentBalance() {
            try {
                // Use robust method to find balance
                const balanceLabel = [...document.querySelectorAll('div')]
                    .find(el => el.textContent.trim() === 'Balance');
                if (!balanceLabel) return 0;
                
                const balanceContainer = balanceLabel.parentElement;
                if (!balanceContainer) return 0;
                
                const balanceValueDiv = balanceContainer.querySelector('div:not(:first-child) span');
                if (!balanceValueDiv) return 0;
                
                const balanceText = balanceValueDiv.textContent.trim();
                const balance = parseFloat(balanceText.replace(/[^0-9.]/g, ''));
                
                return !isNaN(balance) ? balance : 0;
            } catch {
                return 0;
            }
        }

        static calculateBetAmount(balance) {
            // Random bet between 1/8 and 1/2 of balance using crypto random
            const minBet = balance * CONFIG.MIN_BET_FRACTION;
            const maxBet = balance * CONFIG.MAX_BET_FRACTION;
            const randomBet = minBet + CryptoRandom.randomFloat() * (maxBet - minBet);
            
            // Round to nearest chip value (0.2)
            const chips = Math.max(1, Math.floor(randomBet / 0.2));
            const betAmount = chips * 0.2;
            
            return { betAmount, chips };
        }

        static async placeBet(side) {
            try {
                const balance = this.getCurrentBalance();
                if (balance < 0.2) {
                    Logger.log(`❌ Insufficient balance: $${balance.toFixed(2)}`);
                    return false;
                }

                const { betAmount, chips } = this.calculateBetAmount(balance);
                
                if (chips <= 0) {
                    Logger.log(`❌ No chips to bet (calculated ${chips} chips)`);
                    return false;
                }

                Logger.log(`💰 Betting $${betAmount.toFixed(2)} (${chips} chips) on ${side} | Balance: $${balance.toFixed(2)}`);
                
                const area = side === 'Player' ? DOMUtils.getPlayerArea() : DOMUtils.getBankerArea();
                if (!area) {
                    Logger.log(`❌ ${side} area not found`);
                    return false;
                }

                // Click multiple times for the desired bet amount - FAST clicking
                for (let i = 0; i < chips; i++) {
                    const success = this.simulateClick(area);
                    if (!success) {
                        Logger.log(`❌ Failed to click ${i + 1}/${chips} on ${side}`);
                        return false;
                    }
                    
                    // Very small delay between clicks for speed
                    if (i < chips - 1) {
                        await new Promise(resolve => setTimeout(resolve, 5));
                    }
                }
                
                Logger.log(`✅ ${side} bet placed: $${betAmount.toFixed(2)} (${chips} fast clicks)`);
                return true;
                
            } catch (error) {
                Logger.log(`❌ Bet error: ${error.message}`);
                return false;
            }
        }
    }

    /**
     * Game state manager
     */
    class GameState {
        constructor() {
            this.round = 0;
            this.roundsSinceLastBet = 0;
            this.nextBetRound = this.getRandomInterval();
            this.waitingForResult = false;
            this.previousCounters = { P: 0, B: 0, T: 0 };
            this.isRunning = false;
        }

        getRandomInterval() {
            return CryptoRandom.randomInt(1, 3); // 1-3 rounds using crypto random
        }

        detectNewRound() {
            const current = DOMUtils.readCounters();
            const hasIncrease = 
                current.P > this.previousCounters.P ||
                current.B > this.previousCounters.B ||
                current.T > this.previousCounters.T;

            if (hasIncrease) {
                this.onRoundComplete();
            }
            this.previousCounters = { ...current };
        }

        onRoundComplete() {
            this.waitingForResult = false;
            this.round++;
            this.roundsSinceLastBet++;

            const roundsLeft = this.nextBetRound - this.roundsSinceLastBet;
            Logger.log(`🎯 Round ${this.round} complete. Next bet in: ${roundsLeft} round(s)`);

            if (this.roundsSinceLastBet >= this.nextBetRound) {
                this.scheduleBet();
            }
        }

        scheduleBet() {
            if (this.waitingForResult) return;

            Logger.log(`⏰ Scheduling bet in ${CONFIG.ROUND_DELAY}ms`);
            
            setTimeout(async () => {
                if (!this.waitingForResult && DOMUtils.areElementsReady()) {
                    const side = CryptoRandom.randomSide();
                    const success = await BettingLogic.placeBet(side);
                    
                    if (success) {
                        this.waitingForResult = true;
                        this.roundsSinceLastBet = 0;
                        this.nextBetRound = this.getRandomInterval();
                    }
                }
            }, CONFIG.ROUND_DELAY);
        }

        start() {
            if (this.isRunning) return;
            
            Logger.log('🟢 Started');
            this.isRunning = true;
            this.previousCounters = DOMUtils.readCounters();
            
            this.interval = setInterval(() => {
                this.detectNewRound();
            }, 1000);
        }

        stop() {
            if (this.interval) clearInterval(this.interval);
            this.isRunning = false;
            Logger.log('🔴 Stopped');
        }

        getStatus() {
            return {
                round: this.round,
                roundsLeft: Math.max(0, this.nextBetRound - this.roundsSinceLastBet),
                waiting: this.waitingForResult,
                running: this.isRunning
            };
        }
    }

    /**
     * Minimal HUD
     */
    class MiniHUD {
        constructor(gameState) {
            this.gameState = gameState;
            this.createHUD();
        }

        createHUD() {
            this.hud = document.createElement('div');
            Object.assign(this.hud.style, {
                position: 'fixed',
                bottom: '10px',
                left: '10px',
                background: 'rgba(0, 0, 0, 0.8)',
                color: '#0f0',
                font: '11px monospace',
                padding: '4px 8px',
                borderRadius: '4px',
                zIndex: '99999',
                minWidth: '120px'
            });

            document.body.appendChild(this.hud);
            
            setInterval(() => this.update(), 500);
        }

        getBalance() {
            try {
                // Use robust method to find balance
                const balanceLabel = [...document.querySelectorAll('div')]
                    .find(el => el.textContent.trim() === 'Balance');
                if (!balanceLabel) return 'N/A';
                
                const balanceContainer = balanceLabel.parentElement;
                if (!balanceContainer) return 'N/A';
                
                const balanceValueDiv = balanceContainer.querySelector('div:not(:first-child) span');
                if (!balanceValueDiv) return 'N/A';
                
                return balanceValueDiv.textContent.trim();
            } catch {
                return 'N/A';
            }
        }

        update() {
            const s = this.gameState.getStatus();
            const round = DOMUtils.getRoundNumber();
            const counters = DOMUtils.readCounters();
            const balance = this.getBalance();
            
            const status = s.waiting ? '⏳' : s.running ? '🟢' : '🔴';
            const nextBet = s.roundsLeft === 0 ? 'NOW' : s.roundsLeft;
            
            this.hud.innerHTML = `${status} #${round} | Next: ${nextBet} | ${balance} | P:${counters.P} B:${counters.B} T:${counters.T}`;
        }
    }

    // Initialize
    const gameState = new GameState();
    const hud = new MiniHUD(gameState);

    // Wait for DOM then start
    setTimeout(() => {
        if (DOMUtils.areElementsReady()) {
            gameState.start();
            Logger.log('✅ SmartBet v4.3 ready - Crypto-secure random betting enabled');
        } else {
            Logger.log('⚠️ DOM not ready, retrying...');
            setTimeout(() => gameState.start(), 3000);
        }
    }, 2000);

    // Global API
    window.smartBet = {
        start: () => gameState.start(),
        stop: () => gameState.stop(),
        status: () => gameState.getStatus(),
        testBet: (side = 'Player') => BettingLogic.placeBet(side),
        getBalance: () => BettingLogic.getCurrentBalance(),
        calcBet: () => {
            const balance = BettingLogic.getCurrentBalance();
            const result = BettingLogic.calculateBetAmount(balance);
            console.log(`Balance: $${balance.toFixed(2)}, Bet: $${result.betAmount.toFixed(2)} (${result.chips} chips)`);
            return result;
        },
        // Crypto random test functions
        testRandom: () => {
            console.log('Testing crypto random functions:');
            console.log(`Random bool: ${CryptoRandom.randomBool()}`);
            console.log(`Random float: ${CryptoRandom.randomFloat()}`);
            console.log(`Random int (1-3): ${CryptoRandom.randomInt(1, 3)}`);
            console.log(`Random side: ${CryptoRandom.randomSide()}`);
        },
        randomSide: () => CryptoRandom.randomSide()
    };

})();