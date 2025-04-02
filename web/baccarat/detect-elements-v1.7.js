// ==UserScript==
// @name         Detect Elements and Dispatch Event with Warning
// @namespace    http://tampermonkey.net/
// @version      1.7
// @description  Detect elements (B, P, T) and dispatch an event. Warn if nothing is detected for a defined period.
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    console.log("Script initialized: Watching for B, P, and T elements...");

    // Configuration
    const WARNING_TIMEOUT = 200000; // Time in milliseconds (30 seconds) to send a warning

    let lastDetectionTime = Date.now(); // Track the last detection time

    // Function to check if a node matches the criteria for B, P, or T elements
    function isTargetElement(node) {
        return node.nodeType === 1 && // Ensure it's an element node
            (
                node.matches('div[size="29"].css-1izvc1b.emeliqj3') || // Matches B element
                node.matches('div[size="29"].css-1ht4bdf.emeliqj3') || // Matches P element
                node.matches('div[size="29"].css-6jbyia.emeliqj3')    // Matches T element
            ) &&
            node.querySelector('div[font-size="20"].desktop.css-ocqnkq.emeliqj2') !== null;
    }

    // Function to dispatch a custom event
    function dispatchCustomEvent(name) {
        const event = new CustomEvent('ResultDetected', {
            detail: { name }, // Pass the detected name (B, P, T)
        });
        window.dispatchEvent(event);
        console.log("Event dispatched with name:", name);
    }

    // Function to handle newly added nodes
    function handleAddedNodes(mutation) {
        mutation.addedNodes.forEach(node => {
            if (isTargetElement(node)) {
                const result = node.querySelector('div[font-size="20"].desktop.css-ocqnkq.emeliqj2').textContent.trim();
                console.log(`New Element Detected (${result}):`, node);

                lastDetectionTime = Date.now(); // Update last detection time
                dispatchCustomEvent(result); // Dispatch the event immediately
            }
        });
    }

    // Initialize MutationObserver
    function startObserver() {
        const observer = new MutationObserver((mutationsList) => {
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    handleAddedNodes(mutation);
                }
            }
        });

        // Start observing the document for changes
        observer.observe(document.body, {
            childList: true, // Monitor for added/removed nodes
            subtree: true    // Monitor entire DOM tree
        });

        console.log('MutationObserver initialized: Watching for B, P, and T elements...');
    }

    // Function to check for inactivity and send a warning
    function checkInactivity() {
        const currentTime = Date.now();
        if (currentTime - lastDetectionTime >= WARNING_TIMEOUT) {
            console.warn(`No elements detected for the past ${WARNING_TIMEOUT / 1000} seconds!`);
            alert(`Warning: No B, P, or T elements detected for ${WARNING_TIMEOUT / 1000} seconds.`);
        }
    }

    // Start the inactivity check loop
    setInterval(checkInactivity, 5000); // Check every 5 seconds

    // Delay the observer start by 3 seconds
    console.log('Waiting for 3 seconds before starting the observer...');
    setTimeout(() => {
        startObserver();
    }, 3000); // 3000 milliseconds = 3 seconds

})(); 