// ==UserScript==
// @name         Enhanced Anti-Inactivity Script with Auto-Click (Backup)
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Prevents inactivity detection and auto-clicks the "OK" button when it appears.
// @author       Your Name
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    console.log("Enhanced Anti-Inactivity Script with Auto-Click is now active.");

    // Function to simulate random mouse movements
    function simulateMouseMove() {
        const event = new MouseEvent('mousemove', {
            view: window,
            bubbles: true,
            cancelable: true,
            clientX: Math.random() * window.innerWidth,
            clientY: Math.random() * window.innerHeight
        });
        document.dispatchEvent(event);
        console.log('Simulated mouse movement at:', event.clientX, event.clientY);
    }

    // Function to simulate random keypresses
    function simulateKeyPress() {
        const keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']; // Use arrow keys to avoid input interference
        const key = keys[Math.floor(Math.random() * keys.length)];
        const event = new KeyboardEvent('keydown', {
            key: key,
            bubbles: true,
            cancelable: true
        });
        document.dispatchEvent(event);
        console.log('Simulated key press:', key);
    }

    // Randomize intervals to make them less predictable
    function randomInterval(min, max) {
        return Math.floor(Math.random() * (max - min + 1) + min);
    }

    // Set up intervals for mouse movement and keypress simulation
    setInterval(simulateMouseMove, randomInterval(20000, 40000)); // Between 20 and 40 seconds
    setInterval(simulateKeyPress, randomInterval(30000, 60000)); // Between 30 and 60 seconds

    // Function to check for and click the "OK" button by label
    function checkAndClickOKButton() {
        // Look for the button with label="OK"
        const okButton = document.querySelector('button[label="OK"]');
        if (okButton) {
            okButton.click(); // Click the button
            //console.log('OK button clicked!');
        }
    }

    // Set up a MutationObserver to monitor changes in the DOM
    const observer = new MutationObserver(() => {
        checkAndClickOKButton(); // Check for the button on every DOM change
    });

    // Start observing the document for DOM changes
    observer.observe(document.body, { childList: true, subtree: true });

})(); 