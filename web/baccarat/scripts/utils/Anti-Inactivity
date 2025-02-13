// ==UserScript==
// @name         Enhanced Anti-Inactivity Script
// @namespace    http://tampermonkey.net/
// @version      1.1
// @description  Prevents inactivity detection more effectively by simulating natural user actions.
// @author       Your Name
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

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
        // Optional: console.log for debugging
        // console.log('Simulated mouse movement at:', event.clientX, event.clientY);
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
        // Optional: console.log for debugging
        // console.log('Simulated key press:', key);
    }

    // Randomize intervals to make them less predictable
    function randomInterval(min, max) {
        return Math.floor(Math.random() * (max - min + 1) + min);
    }

    // Set up intervals for mouse movement and keypress simulation
    setInterval(simulateMouseMove, randomInterval(20000, 40000)); // Between 20 and 40 seconds
    setInterval(simulateKeyPress, randomInterval(30000, 60000)); // Between 30 and 60 seconds

    console.log("Enhanced Anti-Inactivity Script is now active.");
})();
