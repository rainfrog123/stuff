// ==UserScript==
// @name         Baccarat – Table Rotation Bot (v0.7)
// @namespace    http://tampermonkey.net/
// @version      0.7
// @description  Tracks all tables, randomly selects 10 tables per round for betting rotation.
// @match        *://client.pragmaticplaylive.net/desktop/multibaccarat/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    /**
     * Configuration constants
     */
    const CONFIG = {
        SCAN_INTERVAL_MS: 700,        // How often to rescan the DOM
        CLICK_DELAY_MS: 400,          // Delay from board‑enabled → click bet
        BET_RANDOMISE: 0.5,           // <0.5 = Player, ≥0.5 = Banker
        MAX_TABLES: 45,               // Expected maximum number of tables
        TABLES_PER_ROUND: 10,         // Number of tables to bet on per round
        ROUND_SWITCH_DELAY: 5000,     // Delay before switching to next round (5 seconds)
        DEBUG: false,                 // Enable debug logging
        SELECTORS: {
            tiles: '[class^="TileComponent_tileMobile__"]',
            tableId: '[class^="TileFooter_footerText__"] span',
            tableName: '[class^="TileHeader_cardHeaderTitle__"]',
            roundNumber: '[class^="TileStatistics_round-mobile-counter__"]',
            counters: '[class^="TileStatistics_main-bet-mobile-counter__"]',
            counterType: '[class^="TileStatistics_main-bet-icon-mobile-text__"]',
            counterValue: '[class^="TileStatistics_main-bet-mobile-count__"]',
            disabledBoard: '[class^="TileBetBoard_disabled__"]',
            playerButton: '.betPositionBGTemp.mobile.player',
            bankerButton: '.betPositionBGTemp.mobile.banker',
            betBoard: '[class^="TileBetBoard_cardBetBoardMobile__"]'
        }
    };

    /**
     * Enhanced logging utility
     */
    class Logger {
        static log(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const emoji = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️';
            console.log(`[${timestamp}] ${emoji} ${message}`);
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
     * Represents a single baccarat table with full state tracking
     */
    class BaccaratTable {
        constructor(tableName, tableId) {
            this.tableName = tableName;
            this.tableId = tableId; // Keep current ID for reference but not as primary key
            this.counters = { P: 0, B: 0, T: 0 };
            this.prevCounters = { P: 0, B: 0, T: 0 };
            this.isEnabled = false;
            this.roundNumber = 0;
            this.lastSeen = Date.now();
            this.lastBetTime = null;
            this.betCount = 0;
            this.isActive = false;
            this.consecutiveErrors = 0;
            this.isSelected = false; // Whether this table is in the current rotation
        }

        /**
         * Updates table state from DOM tile and current ID
         */
        updateFromTile(tile, currentTableId) {
            try {
                // Store previous counters
                this.prevCounters = { ...this.counters };
                
                // Update current table ID (it may change)
                this.tableId = currentTableId;
                
                // Read new state
                this.counters = DOMUtils.readCounters(tile);
                this.isEnabled = !DOMUtils.isBoardDisabled(tile);
                this.roundNumber = DOMUtils.getRoundNumber(tile);
                this.lastSeen = Date.now();
                this.isActive = true;
                
                Logger.debug(`Table ${this.tableName} updated: P=${this.counters.P}, B=${this.counters.B}, T=${this.counters.T}, enabled=${this.isEnabled}`);
                return true;
            } catch (error) {
                Logger.error(`Error updating table ${this.tableName}:`, error);
                this.consecutiveErrors++;
                return false;
            }
        }

        /**
         * Calculates counter deltas
         */
        getDeltas() {
            return {
                deltaP: this.counters.P - this.prevCounters.P,
                deltaB: this.counters.B - this.prevCounters.B,
                deltaT: this.counters.T - this.prevCounters.T
            };
        }

        /**
         * Determines if state transition occurred (disabled → enabled)
         */
        hasEnabledTransition(prevEnabled) {
            return !prevEnabled && this.isEnabled;
        }

        /**
         * Records a betting attempt
         */
        recordBet() {
            this.lastBetTime = Date.now();
            this.betCount++;
            this.consecutiveErrors = 0;
        }

        /**
         * Checks if table can accept a bet
         */
        canBet() {
            const timeSinceLastBet = this.lastBetTime ? (Date.now() - this.lastBetTime) : Infinity;
            return this.isEnabled && 
                   this.isSelected && 
                   timeSinceLastBet > CONFIG.CLICK_DELAY_MS * 2 && 
                   this.consecutiveErrors < 3;
        }

        /**
         * Marks table as stale if not seen recently
         */
        checkStale() {
            const timeSinceLastSeen = Date.now() - this.lastSeen;
            if (timeSinceLastSeen > 30000) { // 30 seconds
                this.isActive = false;
                Logger.debug(`Table ${this.tableName} marked as stale`);
            }
        }
    }

    /**
     * Enhanced utility functions for DOM manipulation
     */
    class DOMUtils {
        static getTiles() {
            return document.querySelectorAll(CONFIG.SELECTORS.tiles);
        }

        static isValidTile(tile) {
            if (!tile || !tile.querySelector) return false;
            const hasTableId = !!tile.querySelector(CONFIG.SELECTORS.tableId);
            const hasTableName = !!tile.querySelector(CONFIG.SELECTORS.tableName);
            const hasCounters = !!tile.querySelector(CONFIG.SELECTORS.counters);
            return hasTableId && hasTableName && hasCounters;
        }

        static getTableId(tile) {
            try {
                if (!this.isValidTile(tile)) return null;
                const element = tile.querySelector(CONFIG.SELECTORS.tableId);
                const text = element?.textContent?.trim();
                if (!text) return null;
                const match = text.match(/ID:(\d+)/);
                return match ? match[1] : text.replace('ID:', '').trim();
            } catch (error) {
                Logger.error('Error extracting table ID:', error);
                return null;
            }
        }

        static getTableName(tile) {
            try {
                if (!this.isValidTile(tile)) return 'Unknown';
                const element = tile.querySelector(CONFIG.SELECTORS.tableName);
                return element?.textContent?.trim() || 'Unknown';
            } catch (error) {
                Logger.error('Error extracting table name:', error);
                return 'Unknown';
            }
        }

        static getRoundNumber(tile) {
            try {
                const element = tile.querySelector(CONFIG.SELECTORS.roundNumber);
                const text = element?.textContent?.trim();
                if (!text) return 0;
                const match = text.match(/#(\d+)/);
                return match ? parseInt(match[1], 10) : 0;
            } catch (error) {
                Logger.debug(`Error extracting round number: ${error.message}`);
                return 0;
            }
        }

        static readCounters(tile) {
            const counters = { P: 0, B: 0, T: 0 };
            try {
                if (!this.isValidTile(tile)) return counters;
                const counterElements = tile.querySelectorAll(CONFIG.SELECTORS.counters);
                
                counterElements.forEach((counter) => {
                    const typeElement = counter.querySelector(CONFIG.SELECTORS.counterType);
                    const valueElement = counter.querySelector(CONFIG.SELECTORS.counterValue);
                    const type = typeElement?.textContent?.trim();
                    const value = parseInt(valueElement?.textContent?.trim() || '0', 10);
                    
                    if (type && !isNaN(value) && counters.hasOwnProperty(type)) {
                        counters[type] = value;
                    }
                });
            } catch (error) {
                Logger.error('Error reading counters:', error);
            }
            return counters;
        }

        static isBoardDisabled(tile) {
            try {
                if (!this.isValidTile(tile)) return true;
                const disabledElement = tile.querySelector(CONFIG.SELECTORS.disabledBoard);
                const betBoard = tile.querySelector(CONFIG.SELECTORS.betBoard);
                return !!disabledElement || !betBoard;
            } catch (error) {
                Logger.error('Error checking board status:', error);
                return true;
            }
        }

        static getBettingButtons(tile) {
            try {
                const playerBtn = tile.querySelector(CONFIG.SELECTORS.playerButton);
                const bankerBtn = tile.querySelector(CONFIG.SELECTORS.bankerButton);
                const playerValid = playerBtn && !playerBtn.disabled;
                const bankerValid = bankerBtn && !bankerBtn.disabled;
                
                return {
                    player: playerValid ? playerBtn : null,
                    banker: bankerValid ? bankerBtn : null,
                    valid: playerValid && bankerValid
                };
            } catch (error) {
                Logger.error('Error getting betting buttons:', error);
                return { player: null, banker: null, valid: false };
            }
        }

        static findTileByTableId(tableId) {
            const tiles = Array.from(this.getTiles());
            return tiles.find(tile => this.getTableId(tile) === tableId);
        }

        static findTileByTableName(tableName) {
            const tiles = Array.from(this.getTiles());
            return tiles.find(tile => this.getTableName(tile) === tableName);
        }
    }

    /**
     * Enhanced betting logic
     */
    class BettingLogic {
        static determineWinner(deltaP, deltaB, deltaT) {
            if (deltaP === 0 && deltaB === 0 && deltaT === 0) return 'No Change';
            const maxDelta = Math.max(deltaP, deltaB, deltaT);
            if (maxDelta <= 0) return 'Unknown';
            
            if (deltaP === maxDelta && deltaP > deltaB && deltaP > deltaT) return 'Player';
            if (deltaB === maxDelta && deltaB > deltaP && deltaB > deltaT) return 'Banker';
            if (deltaT === maxDelta && deltaT > deltaP && deltaT > deltaB) return 'Tie';
            return 'Unknown';
        }

        static clickRandomBet(tile, table) {
            try {
                const buttons = DOMUtils.getBettingButtons(tile);
                if (!buttons.valid) {
                    Logger.warn(`Betting buttons not available for table ${table.tableName}`);
                    table.consecutiveErrors++;
                    return false;
                }

                const target = Math.random() < CONFIG.BET_RANDOMISE ? buttons.player : buttons.banker;
                const betType = target === buttons.player ? 'Player' : 'Banker';
                
                // Single click event
                target.dispatchEvent(new MouseEvent('click', { 
                    bubbles: true, 
                    cancelable: true,
                    view: window,
                    detail: 1
                }));

                Logger.success(`🖱️ [Round ${table.roundNumber}] Bet ${betType} on ${table.tableName} (#${table.tableId})`);
                table.recordBet();
                return true;
            } catch (error) {
                Logger.error(`Error clicking bet for table ${table.tableName}:`, error);
                table.consecutiveErrors++;
                return false;
            }
        }
    }

    /**
     * Main table rotation bot
     */
    class TableRotationBot {
        constructor() {
            this.allTables = new Map(); // tableName -> BaccaratTable
            this.selectedTables = new Set(); // Current rotation of 10 table names
            this.roundNumber = 1;
            this.isRunning = false;
            this.scanCount = 0;
            this.startTime = Date.now();
            this.lastRoundSwitch = Date.now();
            this.betsThisRound = 0;
        }

        /**
         * Discovers and tracks all tables
         */
        discoverTables() {
            const tiles = DOMUtils.getTiles();
            let newTablesFound = 0;
            
            tiles.forEach(tile => {
                const tableName = DOMUtils.getTableName(tile);
                const tableId = DOMUtils.getTableId(tile);
                
                if (!tableName || tableName === 'Unknown') return;
                
                if (!this.allTables.has(tableName)) {
                    const table = new BaccaratTable(tableName, tableId);
                    this.allTables.set(tableName, table);
                    newTablesFound++;
                    Logger.log(`🆕 Discovered table: ${tableName} (#${tableId})`);
                }
                
                // Update table state
                const table = this.allTables.get(tableName);
                const prevEnabled = table.isEnabled;
                table.updateFromTile(tile, tableId);
                
                // Check for enabled transition and bet if selected
                if (table.hasEnabledTransition(prevEnabled) && table.isSelected && table.canBet()) {
                    const { deltaP, deltaB, deltaT } = table.getDeltas();
                    const winner = BettingLogic.determineWinner(deltaP, deltaB, deltaT);
                    
                    Logger.log(`✅ ${table.tableName} (#${table.tableId}) ENABLED | Winner: ${winner} | Selected for betting`);
                    
                    setTimeout(() => {
                        const freshTile = DOMUtils.findTileByTableName(tableName);
                        if (freshTile && BettingLogic.clickRandomBet(freshTile, table)) {
                            this.betsThisRound++;
                        }
                    }, CONFIG.CLICK_DELAY_MS);
                }
            });
            
            if (newTablesFound > 0) {
                Logger.success(`📊 Total tables discovered: ${this.allTables.size}/${CONFIG.MAX_TABLES}`);
            }
            
            // Mark stale tables
            this.allTables.forEach(table => table.checkStale());
        }

        /**
         * Randomly selects 10 tables for the current round
         */
        selectTablesForRound() {
            const activeTables = Array.from(this.allTables.values()).filter(table => table.isActive);
            
            if (activeTables.length === 0) {
                Logger.warn('No active tables available for selection');
                return;
            }
            
            // Clear previous selection
            this.selectedTables.clear();
            this.allTables.forEach(table => table.isSelected = false);
            
            // Randomly shuffle and select up to 10 tables
            const shuffled = activeTables.sort(() => Math.random() - 0.5);
            const selected = shuffled.slice(0, Math.min(CONFIG.TABLES_PER_ROUND, activeTables.length));
            
            selected.forEach(table => {
                this.selectedTables.add(table.tableName); // Use tableName as key
                table.isSelected = true;
            });
            
            this.betsThisRound = 0;
            this.lastRoundSwitch = Date.now();
            
            const tableNames = selected.map(t => `${t.tableName}(#${t.tableId})`).join(', ');
            Logger.success(`🎯 Round ${this.roundNumber}: Selected ${selected.length} tables: ${tableNames}`);
        }

        /**
         * Checks if it's time to switch to next round
         */
        shouldSwitchRound() {
            const timeSinceLastSwitch = Date.now() - this.lastRoundSwitch;
            const hasWaitedEnough = timeSinceLastSwitch > CONFIG.ROUND_SWITCH_DELAY;
            
            // Switch if we've waited long enough or all selected tables have been bet on
            const selectedTablesCount = this.selectedTables.size;
            const allSelectedHaveBet = selectedTablesCount > 0 && this.betsThisRound >= selectedTablesCount;
            
            return hasWaitedEnough || allSelectedHaveBet;
        }

        /**
         * Main scan and management cycle
         */
        scanOnce() {
            try {
                this.scanCount++;
                Logger.debug(`Scan #${this.scanCount} - Round ${this.roundNumber}`);
                
                // Discover and update all tables
                this.discoverTables();
                
                // Check if we should switch to next round
                if (this.shouldSwitchRound()) {
                    this.roundNumber++;
                    this.selectTablesForRound();
                }
                
                // Periodic statistics
                if (this.scanCount % 50 === 0) {
                    this.logStatistics();
                }
                
            } catch (error) {
                Logger.error('Error during scan cycle:', error);
            }
        }

        /**
         * Logs comprehensive statistics
         */
        logStatistics() {
            const uptime = Math.round((Date.now() - this.startTime) / 1000);
            const activeCount = Array.from(this.allTables.values()).filter(t => t.isActive).length;
            const totalBets = Array.from(this.allTables.values()).reduce((sum, t) => sum + t.betCount, 0);
            const selectedCount = this.selectedTables.size;
            
            Logger.log(`📊 Stats: Round ${this.roundNumber} | Uptime ${uptime}s | Tables: ${activeCount}/${this.allTables.size} | Selected: ${selectedCount} | Total Bets: ${totalBets} | This Round: ${this.betsThisRound}`);
        }

        /**
         * Starts the bot
         */
        start() {
            if (this.isRunning) {
                Logger.warn('Bot is already running');
                return;
            }

            Logger.success(`♣ Table Rotation Bot v0.7 starting - ${CONFIG.TABLES_PER_ROUND} tables per round`);
            this.isRunning = true;
            this.startTime = Date.now();
            
            // Initial discovery and selection
            this.discoverTables();
            this.selectTablesForRound();
            
            // Start scanning
            this.intervalId = setInterval(() => this.scanOnce(), CONFIG.SCAN_INTERVAL_MS);
        }

        /**
         * Stops the bot
         */
        stop() {
            if (this.intervalId) {
                clearInterval(this.intervalId);
                this.intervalId = null;
            }
            this.isRunning = false;
            this.logStatistics();
            Logger.log('♣ Table Rotation Bot stopped');
        }

        /**
         * Resets all state
         */
        reset() {
            this.allTables.clear();
            this.selectedTables.clear();
            this.roundNumber = 1;
            this.scanCount = 0;
            this.betsThisRound = 0;
            Logger.log('🔄 Bot state reset');
        }

        /**
         * Manually force next round
         */
        nextRound() {
            this.roundNumber++;
            this.selectTablesForRound();
            Logger.log(`🔄 Manually advanced to round ${this.roundNumber}`);
        }
    }

    // Initialize and start the bot
    const bot = new TableRotationBot();
    bot.start();

    // Enhanced global API for debugging/manual control
    window.baccaratBot = {
        bot,
        start: () => bot.start(),
        stop: () => bot.stop(),
        reset: () => bot.reset(),
        nextRound: () => bot.nextRound(),
        stats: () => bot.logStatistics(),
        debug: (enabled = true) => { CONFIG.DEBUG = enabled; },
        tables: () => Array.from(bot.allTables.entries()), // Returns [tableName, tableObject] pairs
        selected: () => Array.from(bot.selectedTables), // Returns array of selected table names
        config: CONFIG,
        round: () => bot.roundNumber
    };

    Logger.success('🎰 Table Rotation Bot loaded and ready!');

})();
  
  