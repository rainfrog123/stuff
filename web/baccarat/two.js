// ==UserScript==
// @name         Baccarat Simple v2 - Refactored
// @namespace    http://tampermonkey.net/
// @version      4.0
// @description  Updated for new DOM structure - Bet fixed $0.2 every 3-5 rounds
// @author       you
// @match        *://client.pragmaticplaylive.net/desktop/baccarat/*
// @grant        unsafeWindow
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    /**
     * Configuration and utilities
     */
    const CONFIG = {
        CLICK_JITTER: [25, 55],     // ms between events
        ROUND_DELAY: 8000,          // ms after result before betting
        MIN_BET: 0.2,               // Fixed bet amount ($0.2)
        DEBUG: false,               // Enable debug logging
        SELECTORS: {
            // Game state selectors
            roundNumber: '.ju_jv',                              // Round number display
            counters: '.jN_jZ',                                 // Counter values
            counterTypes: '.jN_jQ',                             // P/B/T indicators
            
            // Betting area selectors  
            leftBetRoot: '#leftBetTextRoot',                    // Player betting area
            rightBetRoot: '#rightBetTextRoot',                  // Banker betting area
            centerBetRoot: '#centerTopBet',                     // Tie betting area
            
            // Chip selectors (need to be updated based on actual interface)
            chipContainer: '[class*="chip"]',                   // Chip container
            activeChip: '[aria-pressed="true"]',                // Currently selected chip
            
            // Clickable betting spots
            playerBetSpot: '#leftBetTextRoot [tabindex="-1"]',  // Player click area
            bankerBetSpot: '#rightBetTextRoot [tabindex="-1"]', // Banker click area
        }
    };

    /**
     * Enhanced logging utility
     */
    class Logger {
        static log(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const emoji = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️';
            console.log(`[${timestamp}] [SmartBet] ${emoji} ${message}`);
        }

        static debug(message) {
            if (CONFIG.DEBUG) {
                this.log(`[DEBUG] ${message}`, 'info');
            }
        }

        static error(message, error = null) {
            this.log(message, 'error');
            if (error) console.error(error);
        }

        static warn(message) {
            this.log(message, 'warn');
        }

        static success(message) {
            this.log(message, 'success');
        }
    }

    /**
     * DOM utilities for new interface
     */
    class DOMUtils {
        /**
         * Get current round number
         */
        static getRoundNumber() {
            try {
                const element = document.querySelector(CONFIG.SELECTORS.roundNumber);
                const text = element?.textContent?.trim();
                if (!text) return 0;
                // Extract number from "#45" format
                const match = text.match(/#(\d+)/);
                return match ? parseInt(match[1], 10) : 0;
            } catch (error) {
                Logger.debug(`Error getting round number: ${error.message}`);
                return 0;
            }
        }

        /**
         * Read counter values and types
         */
        static readCounters() {
            const counters = { P: 0, B: 0, T: 0 };
            
            try {
                const values = document.querySelectorAll(CONFIG.SELECTORS.counters);
                const types = document.querySelectorAll(CONFIG.SELECTORS.counterTypes);
                
                Logger.debug(`Found ${values.length} counter values and ${types.length} counter types`);
                
                // Match values with types
                for (let i = 0; i < Math.min(values.length, types.length); i++) {
                    const type = types[i]?.textContent?.trim();
                    const value = parseInt(values[i]?.textContent?.trim() || '0', 10);
                    
                    Logger.debug(`Counter ${i}: type="${type}", value="${value}"`);
                    
                    if (type && !isNaN(value) && counters.hasOwnProperty(type)) {
                        counters[type] = value;
                    }
                }
                
                Logger.debug(`Final counters: P=${counters.P}, B=${counters.B}, T=${counters.T}`);
            } catch (error) {
                Logger.error('Error reading counters:', error);
            }
            
            return counters;
        }

        /**
         * Find appropriate chip for betting
         */
        static findChip() {
            try {
                // Try to find currently selected chip
                let chip = document.querySelector(CONFIG.SELECTORS.activeChip);
                if (chip) {
                    Logger.debug('Found active chip');
                    return chip;
                }

                // Fallback: find any available chip
                const chips = document.querySelectorAll(CONFIG.SELECTORS.chipContainer);
                if (chips.length > 0) {
                    Logger.debug(`Found ${chips.length} chips, using first one`);
                    return chips[0];
                }

                Logger.warn('No chips found');
                return null;
            } catch (error) {
                Logger.error('Error finding chip:', error);
                return null;
            }
        }

        /**
         * Get player betting area
         */
        static getPlayerBetSpot() {
            try {
                const spot = document.querySelector(CONFIG.SELECTORS.playerBetSpot);
                Logger.debug(`Player bet spot found: ${!!spot}`);
                return spot;
            } catch (error) {
                Logger.error('Error finding player bet spot:', error);
                return null;
            }
        }

        /**
         * Get banker betting area
         */
        static getBankerBetSpot() {
            try {
                const spot = document.querySelector(CONFIG.SELECTORS.bankerBetSpot);
                Logger.debug(`Banker bet spot found: ${!!spot}`);
                return spot;
            } catch (error) {
                Logger.error('Error finding banker bet spot:', error);
                return null;
            }
        }

        /**
         * Check if essential elements are available
         */
        static areElementsReady() {
            const playerSpot = this.getPlayerBetSpot();
            const bankerSpot = this.getBankerBetSpot();
            const chip = this.findChip();
            
            const ready = !!(playerSpot && bankerSpot && chip);
            Logger.debug(`Elements ready: player=${!!playerSpot}, banker=${!!bankerSpot}, chip=${!!chip}`);
            
            return ready;
        }
    }

    /**
     * Enhanced betting logic
     */
    class BettingLogic {
        /**
         * Perform enhanced click simulation
         */
        static simulateClick(element) {
            try {
                const rect = element.getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;

                // Enhanced event simulation
                const events = [
                    { type: 'pointerdown', delay: 0 },
                    { type: 'mousedown', delay: 10 },
                    { type: 'pointerup', delay: CONFIG.CLICK_JITTER[0] },
                    { type: 'mouseup', delay: CONFIG.CLICK_JITTER[0] + 10 },
                    { type: 'click', delay: CONFIG.CLICK_JITTER[1] }
                ];

                events.forEach(({ type, delay }) => {
                    setTimeout(() => {
                        element.dispatchEvent(new PointerEvent(type, {
                            bubbles: true,
                            cancelable: true,
                            pointerType: 'mouse',
                            view: unsafeWindow,
                            clientX: x,
                            clientY: y
                        }));
                    }, delay);
                });

                return true;
            } catch (error) {
                Logger.error(`Error simulating click: ${error.message}`, error);
                return false;
            }
        }

        /**
         * Place a bet on specified side
         */
        static async placeBet(side, amount) {
            try {
                Logger.log(`💰 Attempting to bet $${amount} on ${side}`);

                // Get betting elements
                const chip = DOMUtils.findChip();
                const betSpot = side === 'Player' ? DOMUtils.getPlayerBetSpot() : DOMUtils.getBankerBetSpot();

                if (!chip || !betSpot) {
                    Logger.error(`Missing elements: chip=${!!chip}, betSpot=${!!betSpot}`);
                    return false;
                }

                // Click chip first
                Logger.debug('Clicking chip...');
                if (!this.simulateClick(chip)) {
                    Logger.error('Failed to click chip');
                    return false;
                }

                // Wait a moment
                await new Promise(resolve => setTimeout(resolve, CONFIG.CLICK_JITTER[1] + 50));

                // Click betting spot
                Logger.debug(`Clicking ${side} betting spot...`);
                if (!this.simulateClick(betSpot)) {
                    Logger.error(`Failed to click ${side} betting spot`);
                    return false;
                }

                Logger.success(`✅ Bet placed on ${side} for $${amount}`);
                return true;
                
            } catch (error) {
                Logger.error(`Error placing bet: ${error.message}`, error);
                return false;
            }
        }
    }

    /**
     * Game state tracking and management
     */
    class GameStateManager {
        constructor() {
            this.round = 0;
            this.roundsSinceLastBet = 0;
            this.nextBetRound = this.getRandomBetInterval();
            this.waitingForResult = false;
            this.previousCounters = { P: 0, B: 0, T: 0 };
            this.isRunning = false;
        }

        /**
         * Get random interval between 3-5 rounds
         */
        getRandomBetInterval() {
            return Math.floor(Math.random() * 3) + 3; // 3-5 rounds
        }

        /**
         * Detect if a new round has started based on counter changes
         */
        detectNewRound() {
            const currentCounters = DOMUtils.readCounters();
            const roundNumber = DOMUtils.getRoundNumber();
            
            // Check if any counter increased (indicating a result)
            const hasCounterIncrease = 
                currentCounters.P > this.previousCounters.P ||
                currentCounters.B > this.previousCounters.B ||
                currentCounters.T > this.previousCounters.T;

            if (hasCounterIncrease) {
                // Determine winner
                const winner = this.determineWinner(currentCounters, this.previousCounters);
                
                Logger.log(`🎯 Round ${roundNumber} result: ${winner}`);
                Logger.debug(`Counters changed: P:${this.previousCounters.P}→${currentCounters.P}, B:${this.previousCounters.B}→${currentCounters.B}, T:${this.previousCounters.T}→${currentCounters.T}`);
                
                this.onRoundComplete(winner);
            }

            this.previousCounters = { ...currentCounters };
        }

        /**
         * Determine winner based on counter changes
         */
        determineWinner(current, previous) {
            const deltaP = current.P - previous.P;
            const deltaB = current.B - previous.B;
            const deltaT = current.T - previous.T;

            if (deltaP > deltaB && deltaP > deltaT) return 'Player';
            if (deltaB > deltaP && deltaB > deltaT) return 'Banker';
            if (deltaT > deltaP && deltaT > deltaB) return 'Tie';
            return 'Unknown';
        }

        /**
         * Handle round completion
         */
        onRoundComplete(winner) {
            this.waitingForResult = false;
            this.round++;
            this.roundsSinceLastBet++;

            Logger.log(`�� Round ${this.round} completed. Rounds since last bet: ${this.roundsSinceLastBet}/${this.nextBetRound}`);

            // Check if it's time to bet
            if (this.roundsSinceLastBet >= this.nextBetRound) {
                this.scheduleBet();
            }
        }

        /**
         * Schedule the next bet
         */
        scheduleBet() {
            if (this.waitingForResult) {
                Logger.debug('Already waiting for result, skipping bet');
                return;
            }

            Logger.log(`⏰ Scheduling bet in ${CONFIG.ROUND_DELAY}ms...`);
            
            setTimeout(async () => {
                if (!this.waitingForResult && DOMUtils.areElementsReady()) {
                    const side = Math.random() < 0.5 ? 'Player' : 'Banker';
                    const success = await BettingLogic.placeBet(side, CONFIG.MIN_BET);
                    
                    if (success) {
                        this.waitingForResult = true;
                        this.roundsSinceLastBet = 0;
                        this.nextBetRound = this.getRandomBetInterval();
                        Logger.log(`⏳ Next bet scheduled in ${this.nextBetRound} round(s)`);
                    } else {
                        Logger.warn('Bet failed, will retry next round');
                    }
                } else {
                    Logger.warn('Cannot bet: waiting for result or elements not ready');
                }
            }, CONFIG.ROUND_DELAY);
        }

        /**
         * Start monitoring the game
         */
        start() {
            if (this.isRunning) {
                Logger.warn('Game state manager already running');
                return;
            }

            Logger.success('🟢 SmartBet v4.0 started - monitoring game state');
            this.isRunning = true;

            // Initialize counters
            this.previousCounters = DOMUtils.readCounters();
            
            // Start monitoring loop
            this.monitorInterval = setInterval(() => {
                this.detectNewRound();
            }, 1000); // Check every second
        }

        /**
         * Stop monitoring
         */
        stop() {
            if (this.monitorInterval) {
                clearInterval(this.monitorInterval);
                this.monitorInterval = null;
            }
            this.isRunning = false;
            Logger.log('🔴 SmartBet stopped');
        }

        /**
         * Get current status
         */
        getStatus() {
            const roundsLeft = this.nextBetRound - this.roundsSinceLastBet;
            return {
                round: this.round,
                roundsLeft: Math.max(0, roundsLeft),
                waitingForResult: this.waitingForResult,
                isRunning: this.isRunning
            };
        }
    }

    /**
     * Enhanced HUD display
     */
    class HUDManager {
        constructor(gameStateManager) {
            this.gameState = gameStateManager;
            this.createHUD();
        }

        createHUD() {
            this.hud = document.createElement('div');
            Object.assign(this.hud.style, {
                position: 'fixed',
                bottom: '10px',
                left: '10px',
                background: 'rgba(0, 0, 0, 0.8)',
                color: '#00ff00',
                font: '12px "Courier New", monospace',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #00ff00',
                zIndex: '99999',
                minWidth: '250px',
                boxShadow: '0 2px 10px rgba(0, 0, 0, 0.5)'
            });

            document.body.appendChild(this.hud);
            this.startUpdating();
        }

        startUpdating() {
            this.updateInterval = setInterval(() => {
                this.updateDisplay();
            }, 500);
        }

        updateDisplay() {
            try {
                const status = this.gameState.getStatus();
                const balance = this.getBalance();
                const roundNumber = DOMUtils.getRoundNumber();
                const counters = DOMUtils.readCounters();
                
                const statusText = status.waitingForResult ? '⏳ Waiting' : '🟢 Ready';
                const roundsText = status.roundsLeft === 0 ? 'BETTING NOW' : `${status.roundsLeft} round${status.roundsLeft !== 1 ? 's' : ''}`;
                
                this.hud.innerHTML = `
                    <div><strong>🎰 SmartBet v4.0</strong></div>
                    <div>Status: ${statusText}</div>
                    <div>Round: #${roundNumber} (${status.round} tracked)</div>
                    <div>Next bet: ${roundsText}</div>
                    <div>Counters: P:${counters.P} B:${counters.B} T:${counters.T}</div>
                    <div>Balance: $${balance.toFixed(2)}</div>
                `;
            } catch (error) {
                Logger.debug(`HUD update error: ${error.message}`);
            }
        }

        getBalance() {
            try {
                return parseFloat(localStorage.getItem('currentBalance')) || 0;
            } catch {
                return 0;
            }
        }

        destroy() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
            }
            if (this.hud && this.hud.parentNode) {
                this.hud.parentNode.removeChild(this.hud);
            }
        }
    }

    /**
     * Main application initialization
     */
    class SmartBetApp {
        constructor() {
            this.gameState = new GameStateManager();
            this.hud = null;
        }

        async initialize() {
            Logger.log('🚀 Initializing SmartBet v4.0...');

            // Wait for DOM to be ready
            await this.waitForDOM();
            
            // Start game monitoring
            this.gameState.start();
            
            // Create HUD
            this.hud = new HUDManager(this.gameState);
            
            // Expose global controls
            this.exposeGlobalAPI();
            
            Logger.success('✅ SmartBet v4.0 initialized successfully');
        }

        async waitForDOM() {
            const checkElements = () => {
                const hasRoundNumber = !!document.querySelector(CONFIG.SELECTORS.roundNumber);
                const hasCounters = document.querySelectorAll(CONFIG.SELECTORS.counters).length > 0;
                const hasBetSpots = !!(document.querySelector(CONFIG.SELECTORS.leftBetRoot) && 
                                     document.querySelector(CONFIG.SELECTORS.rightBetRoot));
                
                Logger.debug(`DOM check: round=${hasRoundNumber}, counters=${hasCounters}, betSpots=${hasBetSpots}`);
                return hasRoundNumber && hasCounters && hasBetSpots;
            };

            if (checkElements()) {
                Logger.debug('DOM ready immediately');
                return;
            }

            Logger.log('⏳ Waiting for DOM elements...');
            
            return new Promise((resolve) => {
                const observer = new MutationObserver(() => {
                    if (checkElements()) {
                        observer.disconnect();
                        Logger.success('✅ DOM elements ready');
                        resolve();
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                // Timeout after 30 seconds
                setTimeout(() => {
                    observer.disconnect();
                    Logger.warn('⚠️ DOM wait timeout, proceeding anyway');
                    resolve();
                }, 30000);
            });
        }

        exposeGlobalAPI() {
            window.smartBet = {
                start: () => this.gameState.start(),
                stop: () => this.gameState.stop(),
                status: () => this.gameState.getStatus(),
                debug: (enabled = true) => { CONFIG.DEBUG = enabled; },
                testBet: (side = 'Player') => BettingLogic.placeBet(side, CONFIG.MIN_BET),
                config: CONFIG
            };

            Logger.log('🔧 Global API exposed as window.smartBet');
        }
    }

    // Initialize the application
    const app = new SmartBetApp();
    app.initialize().catch(error => {
        Logger.error('Failed to initialize SmartBet:', error);
    });

})();