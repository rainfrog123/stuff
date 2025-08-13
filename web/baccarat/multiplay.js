// ==UserScript==
// @name         multiplay
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Monitors all baccarat tables data and tracks changes
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/multibaccarat/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    const CONFIG = {
        TILE_SELECTOR: '.TileComponent_tileMobile__2wg6p',
        CHECK_INTERVAL: 1000, // Check every second
        DEBUG: false,
        BET_DELAY: 5000, // 3s delay before betting
        TOP_COUNT: 5, // Top N tables to bet on
        BALANCE_KEY: 'currentBalance', // Same key as balance detector
        MIN_BET_FRACTION: 1/8, // 1/8 of balance
        MAX_BET_FRACTION: 1/2, // 1/2 of balance
        CLICK_VALUE: 0.2 // Each click = 0.2
    };

    class CryptoRandom {
        static randomBool() {
            return crypto.getRandomValues(new Uint8Array(1))[0] & 1;
        }
        static randomFloat() {
            const array = new Uint32Array(1);
            crypto.getRandomValues(array);
            return array[0] / (0xFFFFFFFF + 1);
        }
        static randomInt(min, max) {
            return Math.floor(this.randomFloat() * (max - min + 1)) + min;
        }
        static randomSide() {
            return this.randomBool() ? 'Player' : 'Banker';
        }
    }

    class TableData {
        constructor(element, id) {
            this.element = element;
            this.id = id;
            this.data = {};
            this.previousData = {};
        }

        parseTableData() {
            try {
                const text = this.element.innerText;
                const lines = text.split('\n').map(line => line.trim()).filter(line => line);
                
                const newData = {
                    name: '',
                    minBet: '',
                    maxBet: '',
                    roundNumber: 0,
                    currentResult: '',
                    counters: { P: 0, B: 0, T: 0 },
                    additionalNumbers: [],
                    lastResults: [],
                    tableId: '',
                    rawText: text,
                    timestamp: Date.now()
                };

                // Parse each line
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    
                    // Table name (first line, usually contains "Baccarat")
                    if (i === 0 && line.includes('Baccarat')) {
                        newData.name = line;
                    }
                    
                    // Minimum bet (starts with $ but not -$)
                    else if (line.startsWith('$') && !line.startsWith('-$')) {
                        newData.minBet = line;
                    }
                    
                    // Maximum bet (starts with -$, remove the negative sign)
                    else if (line.startsWith('-$')) {
                        newData.maxBet = line.substring(1); // Remove the - sign
                    }
                    
                    // Round number (starts with #)
                    else if (line.startsWith('#')) {
                        newData.roundNumber = parseInt(line.substring(1)) || 0;
                    }
                    
                    // Current result (single letter P, B, or T)
                    else if (line.length === 1 && ['P', 'B', 'T'].includes(line)) {
                        newData.currentResult = line;
                    }
                    
                    // Counters (number following P, B, T)
                    else if (/^\d+$/.test(line)) {
                        const prevLine = lines[i-1];
                        if (prevLine === 'P') newData.counters.P = parseInt(line);
                        else if (prevLine === 'B') newData.counters.B = parseInt(line);
                        else if (prevLine === 'T') newData.counters.T = parseInt(line);
                        else newData.additionalNumbers.push(parseInt(line));
                    }
                    
                    // Last results (sequences of P, B, T)
                    else if (/^[PBT]+$/.test(line) && line.length > 1) {
                        newData.lastResults = line.split('');
                    }
                    
                    // Table ID (starts with ID:)
                    else if (line.startsWith('ID:')) {
                        newData.tableId = line;
                    }
                }

                return newData;
            } catch (error) {
                console.error(`[TableMonitor] Error parsing table ${this.id}:`, error);
                return null;
            }
        }

        update() {
            this.previousData = { ...this.data };
            const newData = this.parseTableData();
            
            if (newData) {
                this.data = newData;
                this.detectChanges();
                return true;
            }
            return false;
        }

        detectChanges() {
            const changes = [];
            
            // Round number change
            if (this.previousData.roundNumber && this.data.roundNumber !== this.previousData.roundNumber) {
                const diff = this.data.roundNumber - this.previousData.roundNumber;
                changes.push(`Round #${this.previousData.roundNumber} → #${this.data.roundNumber} (${diff > 0 ? '+' : ''}${diff})`);
            }
            
            // Counter changes
            ['P', 'B', 'T'].forEach(side => {
                if (this.previousData.counters && this.data.counters[side] !== this.previousData.counters[side]) {
                    const diff = this.data.counters[side] - (this.previousData.counters[side] || 0);
                    changes.push(`${side} ${this.previousData.counters[side] || 0} → ${this.data.counters[side]} (${diff > 0 ? '+' : ''}${diff})`);
                }
            });
            
            // Current result change
            if (this.previousData.currentResult && this.data.currentResult !== this.previousData.currentResult) {
                changes.push(`Result ${this.previousData.currentResult} → ${this.data.currentResult}`);
            }
            
            // Last results change
            if (this.previousData.lastResults && JSON.stringify(this.data.lastResults) !== JSON.stringify(this.previousData.lastResults)) {
                changes.push(`Results ${this.previousData.lastResults.join('')} → ${this.data.lastResults.join('')}`);
            }

            if (changes.length > 0 && CONFIG.DEBUG) {
                console.log(`[TableMonitor] ${this.data.name || `Table ${this.id}`}:`);
                changes.forEach(change => console.log(`  📊 ${change}`));
            }
        }

        getStatus() {
            return {
                id: this.id,
                name: this.data.name,
                round: this.data.roundNumber,
                result: this.data.currentResult,
                counters: this.data.counters,
                bettingLimits: `${this.data.minBet} - ${this.data.maxBet}`,
                tableId: this.data.tableId,
                lastUpdate: new Date(this.data.timestamp).toLocaleTimeString()
            };
        }
    }

    class TableMonitor {
        constructor() {
            this.tables = new Map();
            this.isRunning = false;
            this.intervalId = null;
        }

        findTables() {
            const tiles = document.querySelectorAll(CONFIG.TILE_SELECTOR);
            const currentTableIds = new Set();

            tiles.forEach((tile, index) => {
                const tableId = `table_${index}`;
                currentTableIds.add(tableId);

                if (!this.tables.has(tableId)) {
                    // New table found
                    const tableData = new TableData(tile, tableId);
                    tableData.update();
                    this.tables.set(tableId, tableData);
                    if (CONFIG.DEBUG) console.log(`[TableMonitor] New table detected: ${tableData.data.name || tableId}`);
                } else {
                    // Update existing table
                    const tableData = this.tables.get(tableId);
                    tableData.element = tile; // Update element reference
                    tableData.update();
                }
            });

            // Remove tables that no longer exist
            for (const [tableId, tableData] of this.tables) {
                if (!currentTableIds.has(tableId)) {
                    if (CONFIG.DEBUG) console.log(`[TableMonitor] Table removed: ${tableData.data.name || tableId}`);
                    this.tables.delete(tableId);
                }
            }

            return tiles.length;
        }

        start() {
            if (this.isRunning) return;

            if (CONFIG.DEBUG) console.log('[TableMonitor] Starting table monitoring...');
            this.isRunning = true;

            // Initial scan
            const tableCount = this.findTables();
            if (CONFIG.DEBUG) console.log(`[TableMonitor] Found ${tableCount} tables`);

            // Set up periodic monitoring
            this.intervalId = setInterval(() => {
                if (this.isRunning) {
                    this.findTables();
                }
            }, CONFIG.CHECK_INTERVAL);

            if (CONFIG.DEBUG) console.log(`[TableMonitor] Monitoring ${this.tables.size} tables every ${CONFIG.CHECK_INTERVAL}ms`);
        }

        stop() {
            if (!this.isRunning) return;

            if (CONFIG.DEBUG) console.log('[TableMonitor] Stopping table monitoring...');
            this.isRunning = false;

            if (this.intervalId) {
                clearInterval(this.intervalId);
                this.intervalId = null;
            }
        }

        getTableData(tableId) {
            const table = this.tables.get(tableId);
            return table ? table.data : null;
        }

        getAllTables() {
            const result = {};
            for (const [tableId, tableData] of this.tables) {
                result[tableId] = tableData.data;
            }
            return result;
        }

        getTableStatus() {
            const status = [];
            for (const [tableId, tableData] of this.tables) {
                status.push(tableData.getStatus());
            }
            return status;
        }

        printStatus() {
            console.log('\n[TableMonitor] Current Status:');
            const status = this.getTableStatus();
            status.forEach(table => {
                console.log(`📋 ${table.name}`);
                console.log(`   Round: #${table.round} | Result: ${table.result} | P:${table.counters.P} B:${table.counters.B} T:${table.counters.T}`);
                console.log(`   Betting Limits: ${table.bettingLimits} | ${table.tableId} | Updated: ${table.lastUpdate}`);
            });
        }
    }

    class BettingManager {
        constructor(monitor) {
            this.monitor = monitor;
            this.betList = [];
            this.currentIndex = 0;
            this.isRunning = false;
            this.currentTable = null;
            this.lastRound = 0;
            this.waitingForFinish = false;
            this.betSide = '';
            this.lastBetAmount = 0;
        }

        getBalance() {
            const balance = localStorage.getItem(CONFIG.BALANCE_KEY);
            return balance ? parseFloat(balance) : 0;
        }

        calcBetAmount() {
            const balance = this.getBalance();
            if (balance < CONFIG.CLICK_VALUE) return { amount: 0, clicks: 0 };

            const minBet = balance * CONFIG.MIN_BET_FRACTION;
            const maxBet = balance * CONFIG.MAX_BET_FRACTION;
            const randomBet = minBet + CryptoRandom.randomFloat() * (maxBet - minBet);
            
            const clicks = Math.max(1, Math.floor(randomBet / CONFIG.CLICK_VALUE));
            const amount = clicks * CONFIG.CLICK_VALUE;
            
            return { amount, clicks };
        }

        start() {
            if (this.isRunning) return;
            this.isRunning = true;
            this.refreshBetList();
            this.processNext();
            console.log('[Betting] Started sequential betting');
        }

        stop() {
            this.isRunning = false;
            this.currentTable = null;
            if (CONFIG.DEBUG) console.log('[Betting] Stopped');
        }

        refreshBetList() {
            const ranked = [];
            for (const [id, table] of this.monitor.tables) {
                const { P, B, T } = table.data.counters;
                const total = P + B + T;
                if (total > 20) {
                    const diff = Math.abs(B - P);
                    const ratio = total > 0 ? diff / total : 1;
                    ranked.push({ id, P, B, diff, ratio, total });
                }
            }
            this.betList = ranked.sort((a, b) => a.ratio - b.ratio).slice(0, CONFIG.TOP_COUNT);
            this.currentIndex = 0;
            console.log(`[Betting] Refreshed list: ${this.betList.length} tables`);
        }

        processNext() {
            if (!this.isRunning) return;

            if (this.currentIndex >= this.betList.length) {
                this.currentIndex = 0;
                this.refreshBetList();
                this.processNext();
                return;
            }

            const tableInfo = this.betList[this.currentIndex];
            this.currentTable = this.monitor.tables.get(tableInfo.id);
            
            if (!this.currentTable) {
                this.currentIndex++;
                setTimeout(() => this.processNext(), 100);
                return;
            }

            this.lastRound = this.currentTable.data.roundNumber;
            this.waitForRoundEnd();
        }

        waitForRoundEnd() {
            if (!this.isRunning || !this.currentTable) return;

            const currentRound = this.currentTable.data.roundNumber;
            
            if (currentRound !== this.lastRound) {
                this.lastRound = currentRound;
                setTimeout(() => this.placeBet(), CONFIG.BET_DELAY);
            } else {
                setTimeout(() => this.waitForRoundEnd(), 500);
            }
        }

        async placeBet() {
            if (!this.isRunning || !this.currentTable) return;

            const { amount, clicks } = this.calcBetAmount();
            if (clicks === 0) {
                if (CONFIG.DEBUG) console.log(`[Betting] Insufficient balance for ${this.currentTable.id}`);
                this.moveToNext();
                return;
            }

            this.betSide = CryptoRandom.randomSide();
            this.lastBetAmount = amount;
            
            const success = this.betSide === 'Player' ? 
                await this.betPlayer(this.currentTable.id, clicks) : 
                await this.betBanker(this.currentTable.id, clicks);

            if (success) {
                this.waitingForFinish = true;
                const table = this.currentTable.data;
                const balance = this.getBalance();
                console.log(`[Betting] ${table.name || this.currentTable.id}`);
                console.log(`  Round #${table.roundNumber} | P:${table.counters.P} B:${table.counters.B} T:${table.counters.T} | Current: ${table.currentResult}`);
                console.log(`  Bet ${this.betSide} $${amount.toFixed(2)} (${clicks} clicks) | Balance: $${balance.toFixed(2)}`);
                console.log(`  ${table.bettingLimits || `${table.minBet} - ${table.maxBet}`} | ${table.tableId}`);
                this.waitForBetFinish();
            } else {
                this.moveToNext();
            }
        }

        waitForBetFinish() {
            if (!this.isRunning || !this.currentTable) return;

            const currentRound = this.currentTable.data.roundNumber;
            
            if (currentRound !== this.lastRound) {
                this.waitingForFinish = false;
                this.moveToNext();
            } else {
                setTimeout(() => this.waitForBetFinish(), 500);
            }
        }

        moveToNext() {
            this.currentIndex++;
            this.currentTable = null;
            setTimeout(() => this.processNext(), 100);
        }

        async betPlayer(id, clicks = 1) {
            const ele = this.monitor.tables.get(id)?.element;
            if (!ele) return false;
            const btn = ele.querySelector('div.betPositionBGTemp.mobile.player');
            if (!btn) return false;

            for (let i = 0; i < clicks; i++) {
                btn.click();
                if (i < clicks - 1) await new Promise(resolve => setTimeout(resolve, 50));
            }
            return true;
        }

        async betBanker(id, clicks = 1) {
            const ele = this.monitor.tables.get(id)?.element;
            if (!ele) return false;
            const btn = ele.querySelector('div.betPositionBGTemp.mobile.banker');
            if (!btn) return false;

            for (let i = 0; i < clicks; i++) {
                btn.click();
                if (i < clicks - 1) await new Promise(resolve => setTimeout(resolve, 50));
            }
            return true;
        }

        getStatus() {
            return {
                running: this.isRunning,
                listLength: this.betList.length,
                currentIndex: this.currentIndex,
                currentTable: this.currentTable?.id || null,
                lastRound: this.lastRound,
                waitingForFinish: this.waitingForFinish,
                betSide: this.betSide,
                lastBetAmount: this.lastBetAmount,
                balance: this.getBalance()
            };
        }
    }

    // Initialize the monitor and betting manager
    const monitor = new TableMonitor();
    const betting = new BettingManager(monitor);

    // Start monitoring after DOM is ready
    setTimeout(() => {
        monitor.start();
        if (CONFIG.DEBUG) console.log('[TableMonitor] table checker v1.0 initialized');
        
        // Auto-start betting after tables are detected
            setTimeout(() => {
            betting.start();
            if (CONFIG.DEBUG) console.log('[Betting] Auto-started');
            }, 10000);
    }, 2000);

    // Global API
    window.tableMonitor = {
        start: () => monitor.start(),
        stop: () => monitor.stop(),
        status: () => monitor.printStatus(),
        getTables: () => monitor.getAllTables(),
        getTable: (id) => monitor.getTableData(id),
        count: () => monitor.tables.size,
        list: () => {
            console.log('Available tables:');
            monitor.tables.forEach((table, id) => {
                console.log(`${id}: ${table.data.name || 'Unknown'} - Round #${table.data.roundNumber}`);
            });
        },
        toggleLogging: () => {
            CONFIG.DEBUG = !CONFIG.DEBUG;
            console.log(`[TableMonitor] Logging ${CONFIG.DEBUG ? 'enabled' : 'disabled'}`);
        },
        getEle: (id) => {
            const table = monitor.tables.get(id);
            return table ? table.element : null;
        },
        betPlayer: (id, clicks = 1) => betting.betPlayer(id, clicks),
        betBanker: (id, clicks = 1) => betting.betBanker(id, clicks),
        getBalance: () => betting.getBalance(),
        calcBet: () => betting.calcBetAmount(),
        rank: () => {
            const ranked = [];
            for (const [id, table] of monitor.tables) {
                const { P, B, T } = table.data.counters;
                const total = P + B + T;
                if (total > 20) {
                    const diff = Math.abs(B - P);
                    const ratio = total > 0 ? diff / total : 1;
                    ranked.push({ id, name: table.data.name, P, B, diff, ratio, total });
                }
            }
            return ranked.sort((a, b) => a.ratio - b.ratio);
        },
        startBetting: () => betting.start(),
        stopBetting: () => betting.stop(),
        bettingStatus: () => betting.getStatus()
    };

    if (CONFIG.DEBUG) {
        console.log('[TableMonitor] API available: window.tableMonitor');
        console.log('Monitor: start(), stop(), status(), getTables(), getEle(id), rank(), list(), count(), toggleLogging()');
        console.log('Betting: betPlayer(id, clicks), betBanker(id, clicks), startBetting(), stopBetting(), bettingStatus()');
        console.log('Balance: getBalance(), calcBet()');
    }

})();

// dont remove my quick commands
// window.tableMonitor.betPlayer('table_0');
// window.tableMonitor.getEle('table_0');
// window.tableMonitor.status();
// window.tableMonitor.rank();
// window.tableMonitor.startBetting();
// window.tableMonitor.bettingStatus();
// window.tableMonitor.stopBetting();
// window.tableMonitor.getTables();
// window.tableMonitor.getBalance();
// window.tableMonitor.calcBet();