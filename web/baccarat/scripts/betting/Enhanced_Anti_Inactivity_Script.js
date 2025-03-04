// ==UserScript==
// @name         Enhanced Anti-Inactivity Script with Auto-Click
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Prevents inactivity detection and auto-clicks the "OK" button when it appears with improved performance
// @author       Your Name
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        MOUSE_MOVE: {
            MIN_INTERVAL: 20000, // 20 seconds
            MAX_INTERVAL: 40000  // 40 seconds
        },
        KEY_PRESS: {
            MIN_INTERVAL: 30000, // 30 seconds
            MAX_INTERVAL: 60000  // 60 seconds
        },
        BUTTON_CHECK: {
            INTERVAL: 1000       // 1 second
        },
        DEBUG: false             // Set to true for detailed logging
    };

    // Utility functions
    const utils = {
        log: (message, force = false) => {
            if (CONFIG.DEBUG || force) {
                console.log(`[Anti-Inactivity] ${message}`);
            }
        },
        
        randomInterval: (min, max) => {
            return Math.floor(Math.random() * (max - min + 1) + min);
        },
        
        randomPosition: () => {
            return {
                x: Math.floor(Math.random() * window.innerWidth),
                y: Math.floor(Math.random() * window.innerHeight)
            };
        }
    };

    // Core functionality
    const antiInactivity = {
        // Simulate mouse movement with natural randomization
        simulateMouseMove: () => {
            const pos = utils.randomPosition();
            const event = new MouseEvent('mousemove', {
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: pos.x,
                clientY: pos.y
            });
            document.dispatchEvent(event);
            utils.log(`Mouse movement simulated at: (${pos.x}, ${pos.y})`);
            
            // Schedule next movement with random interval
            setTimeout(
                antiInactivity.simulateMouseMove, 
                utils.randomInterval(CONFIG.MOUSE_MOVE.MIN_INTERVAL, CONFIG.MOUSE_MOVE.MAX_INTERVAL)
            );
        },
        
        // Simulate key press with natural randomization
        simulateKeyPress: () => {
            const keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
            const key = keys[Math.floor(Math.random() * keys.length)];
            
            const event = new KeyboardEvent('keydown', {
                key: key,
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(event);
            utils.log(`Key press simulated: ${key}`);
            
            // Schedule next key press with random interval
            setTimeout(
                antiInactivity.simulateKeyPress, 
                utils.randomInterval(CONFIG.KEY_PRESS.MIN_INTERVAL, CONFIG.KEY_PRESS.MAX_INTERVAL)
            );
        },
        
        // Check for and click OK buttons
        checkAndClickOKButton: () => {
            // Multiple selector strategies for better reliability
            const selectors = [
                'button[label="OK"]',
                'button.ok-button',
                'button:contains("OK")',
                'button.dialog-button[data-action="ok"]',
                '.modal-dialog button.btn-primary'
            ];
            
            for (const selector of selectors) {
                try {
                    const buttons = document.querySelectorAll(selector);
                    for (const button of buttons) {
                        if (button && button.offsetParent !== null) { // Check if visible
                            button.click();
                            utils.log('OK button clicked!', true);
                            return true;
                        }
                    }
                } catch (e) {
                    // Ignore selector errors
                }
            }
            
            return false;
        },
        
        // Initialize the observer for DOM changes
        initObserver: () => {
            const observer = new MutationObserver(() => {
                antiInactivity.checkAndClickOKButton();
            });
            
            // Start observing with optimized configuration
            observer.observe(document.body, { 
                childList: true, 
                subtree: true,
                attributes: false,
                characterData: false
            });
            
            utils.log('DOM observer initialized');
            
            // Also set up a periodic check as a fallback
            setInterval(antiInactivity.checkAndClickOKButton, CONFIG.BUTTON_CHECK.INTERVAL);
        },
        
        // Initialize everything
        init: () => {
            utils.log('Script initialized', true);
            
            // Start with initial random delays
            setTimeout(antiInactivity.simulateMouseMove, utils.randomInterval(1000, 5000));
            setTimeout(antiInactivity.simulateKeyPress, utils.randomInterval(2000, 6000));
            
            // Initialize the observer
            antiInactivity.initObserver();
        }
    };

    // Start the script
    antiInactivity.init();
})(); 