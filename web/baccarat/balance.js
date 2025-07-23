// ==UserScript==
// @name         Baccarat Balance Detector
// @namespace    http://tampermonkey.net/
// @version      1.4
// @description  Detects balance using a specific selector and stores it in localStorage (no UI indicator)
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccarat/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_log
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // ==========================================
    // CONFIGURATION SETTINGS
    // ==========================================
    const CONFIG = {
        // Balance detection settings
        STORAGE_KEY: 'currentBalance',    // Key used in localStorage

        // DOM selectors for different game interfaces
        SELECTORS: {
            // Only use this specific selector for balance
            //BACCARAT_BALANCE: '[data-testid="wallet-balance-value"] span span', // Updated selector
            //BACCARAT_BALANCE: '.sm_sn.iI_iJ .sm_sp span', // Updated selector
            BACCARAT_BALANCE: '.tw_tz span', // Updated selector
        },

        // Balance validation settings
        VALIDATION: {
            MIN_VALID_BALANCE: 0.1,       // Minimum valid balance
            MAX_VALID_BALANCE: 100000,    // Maximum valid balance
        },

        // Debug settings
        DEBUG: true,
        VERBOSE: false,  // Set to true for more detailed logging
    };

    // ==========================================
    // STATE TRACKING
    // ==========================================
    const STATE = {
        lastConfirmedBalance: null,   // Last confirmed valid balance
        lastUpdateTime: 0,            // Last time balance was updated
    };

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================

    /**
     * Logger utility with different log levels
     */
    const Logger = {
        info: (message) => {
            if (CONFIG.DEBUG) console.log(`[Balance] ${message}`);
        },
        verbose: (message) => {
            if (CONFIG.DEBUG && CONFIG.VERBOSE) console.log(`[Balance] ${message}`);
        },
        warn: (message) => console.warn(`[Balance] ${message}`),
        error: (message) => console.error(`[Balance] ${message}`)
    };

    /**
     * Extract numeric value from text
     * @param {string} text - Text to extract from
     * @returns {number|null} - Extracted number or null
     */
    function extractNumericValue(text) {
        if (!text) return null;

        // Remove all non-numeric characters except decimal point
        const numericString = text.replace(/[^0-9.]/g, '');
        const value = parseFloat(numericString);

        return !isNaN(value) ? value : null;
    }

    // ==========================================
    // BALANCE DETECTION FUNCTIONS
    // ==========================================

    /**
     * Try to detect balance using the specific selector
     */
    function detectBalance() {
        try {
            // Get all elements matching our selector
            const balanceElements = document.querySelectorAll(CONFIG.SELECTORS.BACCARAT_BALANCE);

            if (balanceElements.length === 0) {
                Logger.verbose('No balance elements found');
                return;
            }

            // Log how many elements were found
            if (balanceElements.length > 1) {
                Logger.verbose(`Found ${balanceElements.length} balance elements`);
            }

            // Process each element
            for (const element of balanceElements) {
                const balance = extractNumericValue(element.textContent);

                if (balance !== null && balance >= CONFIG.VALIDATION.MIN_VALID_BALANCE) {
                    Logger.verbose(`Balance detected: ${balance.toFixed(2)}`);

                    // Get previous balance for comparison
                    const previousBalance = localStorage.getItem(CONFIG.STORAGE_KEY);
                    const previousBalanceNum = previousBalance ? parseFloat(previousBalance) : null;

                    // Update storage if balance changed
                    if (previousBalanceNum !== balance) {
                        Logger.info(`Balance updated: ${balance.toFixed(2)}`);

                        // Store in localStorage
                        localStorage.setItem(CONFIG.STORAGE_KEY, balance.toString());

                        // Also store timestamp of last update
                        localStorage.setItem(`${CONFIG.STORAGE_KEY}_timestamp`, Date.now().toString());

                        // Update last confirmed balance
                        STATE.lastConfirmedBalance = balance;
                        STATE.lastUpdateTime = Date.now();
                    }
                }
            }
        } catch (error) {
            Logger.error(`Error detecting balance: ${error.message}`);
        }
    }

    // ==========================================
    // BALANCE CHANGE OBSERVER
    // ==========================================

    /**
     * Set up a MutationObserver to detect DOM changes
     */
    function setupBalanceObserver() {
        // Create a MutationObserver to watch for changes to the balance element
        const observer = new MutationObserver((mutations) => {
            // Check if any of the mutations affect our balance elements
            const shouldCheckBalance = mutations.some(mutation => {
                // Check if the mutation target matches our selector
                if (mutation.target.matches && mutation.target.matches(CONFIG.SELECTORS.BACCARAT_BALANCE)) {
                    return true;
                }

                // Check if any added nodes match our selector
                if (mutation.addedNodes.length) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            if (node.matches && node.matches(CONFIG.SELECTORS.BACCARAT_BALANCE)) {
                                return true;
                            }
                            if (node.querySelector && node.querySelector(CONFIG.SELECTORS.BACCARAT_BALANCE)) {
                                return true;
                            }
                        }
                    }
                }

                return false;
            });

            // If relevant changes detected, check balance immediately
            if (shouldCheckBalance) {
                detectBalance();
            }
        });

        // Start observing the document with the configured parameters
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            characterDataOldValue: true
        });

        Logger.info('Balance observer set up');

        // Also run periodic checks as a fallback
        setInterval(detectBalance, 2000);
    }

    // ==========================================
    // INITIALIZATION
    // ==========================================

    /**
     * Initialize the balance detector
     */
    function initialize() {
        Logger.info('Balance Detector v1.4 initialized');
        Logger.info('Using selector: ' + CONFIG.SELECTORS.BACCARAT_BALANCE);

        // Run initial detection
        setTimeout(detectBalance, 1000);

        // Set up observer for real-time detection
        setTimeout(setupBalanceObserver, 2000);

        // Status indicator disabled - no UI elements shown
    }

    /**
     * Create a small status indicator - DISABLED
     */
    function createStatusIndicator() {
        // Status indicator disabled - function kept for compatibility
    }

    // Start the script when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();
