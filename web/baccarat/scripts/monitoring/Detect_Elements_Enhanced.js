// ==UserScript==
// @name         Detect Elements and Dispatch Event with Warning
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Enhanced element detection (B, P, T) with improved event dispatching, warning system, and error handling.
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // Configuration
    const CONFIG = {
        WARNING_TIMEOUT: 200000,    // 200 seconds (3.33 minutes)
        CHECK_INTERVAL: 5000,       // Check every 5 seconds
        OBSERVER_DELAY: 3000,       // Delay before starting observer
        MAX_WARNINGS: 3,            // Maximum number of warnings before reset
        SELECTORS: {
            BANKER: 'div[size="29"].css-1izvc1b.emeliqj3',
            PLAYER: 'div[size="29"].css-1ht4bdf.emeliqj3',
            TIE: 'div[size="29"].css-6jbyia.emeliqj3',
            VALUE: 'div[font-size="20"].desktop.css-ocqnkq.emeliqj2'
        }
    };

    // Function to check if a node matches the criteria for B, P, or T elements
    function isTargetElement(node) {
        if (!node || node.nodeType !== 1) return false;

        try {
            const isBanker = node.matches(CONFIG.SELECTORS.BANKER);
            const isPlayer = node.matches(CONFIG.SELECTORS.PLAYER);
            const isTie = node.matches(CONFIG.SELECTORS.TIE);
            const hasValue = node.querySelector(CONFIG.SELECTORS.VALUE) !== null;

            return (isBanker || isPlayer || isTie) && hasValue;
        } catch (error) {
            console.error("Error checking target element:", error);
            return false;
        }
    }

    // Function to get result type from element
    function getResultType(node) {
        try {
            if (node.matches(CONFIG.SELECTORS.BANKER)) return 'B';
            if (node.matches(CONFIG.SELECTORS.PLAYER)) return 'P';
            if (node.matches(CONFIG.SELECTORS.TIE)) return 'T';
            return null;
        } catch (error) {
            console.error("Error getting result type:", error);
            return null;
        }
    }

    // Function to dispatch a custom event with enhanced error handling
    function dispatchCustomEvent(name) {
        try {
            const event = new CustomEvent('ResultDetected', {
                detail: { 
                    name,
                    timestamp: new Date().toISOString()
                }
            });
            window.dispatchEvent(event);
            return true;
        } catch (error) {
            console.error("Error dispatching event:", error);
            return false;
        }
    }

    // Function to handle newly added nodes
    function handleAddedNodes(mutation) {
        mutation.addedNodes.forEach(node => {
            if (isTargetElement(node)) {
                const result = getResultType(node);
                if (result) {
                    dispatchCustomEvent(result);
                }
            }
        });
    }

    // Initialize MutationObserver with error handling
    function startObserver() {
        try {
            const observer = new MutationObserver((mutationsList) => {
                for (const mutation of mutationsList) {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        handleAddedNodes(mutation);
                    }
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            console.log('MutationObserver initialized successfully');
            return observer;
        } catch (error) {
            console.error("Error initializing MutationObserver:", error);
            return null;
        }
    }

    // Initialize the script
    console.log("Enhanced Element Detection Script Initialized");
    console.log("Version: 2.0");
    console.log("Configuration:", CONFIG);

    // Delay the observer start
    console.log(`Waiting ${CONFIG.OBSERVER_DELAY/1000} seconds before starting the observer...`);
    setTimeout(() => {
        const observer = startObserver();
        if (!observer) {
            console.error("Failed to start observer. Script may not function correctly.");
        }
    }, CONFIG.OBSERVER_DELAY);
})(); 