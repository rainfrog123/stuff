// ==UserScript==
// @name         Baccarat Smart Auto-Betting System with True Random Distribution
// @namespace    http://tampermonkey.net/
// @version      2.3
// @description  Advanced baccarat betting automation with cryptographic randomization, dynamic bet sizing, and intelligent round-based delays for natural betting patterns.
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    console.log("Betting Handler Script Initialized: Listening for ResultDetected event...");

    // Standard random number generator
    function random(min, max) {
        return min + (Math.random()) * (max - min); // Returns a number in range [min, max)
    }

    function simulateClick(element) {
        if (element) {
            element.click();
        } else {
            console.warn("Element not found!");
        }
    }

    function getButton(type) {
        return document.querySelector(
            type === "Player"
                ? '.PLAYER_PATH .betspotAsset'
                : '.BANKER_PATH .betspotAsset'
        );
    }

    function getChipElement() {
        return document.querySelector(`#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > span:nth-child(1)`);
    }

    function getBalance() {
        const balanceElement = document.querySelector('.balanceContainer .balance .amt');
        if (balanceElement) {
            const balanceText = balanceElement.textContent.replace('$', '').trim();
            const balance = parseFloat(balanceText);
            if (!isNaN(balance)) {
                return balance;
            }
            console.warn("Invalid balance format!");
        } else {
            console.warn("Unable to retrieve balance!");
        }
        return 0;
    }

    function placeBet(targetButton, betAmount) {
        const chipElement = getChipElement();
        if (!chipElement) {
            console.warn(`Chip element not found!`);
            return;
        }

        // Calculate number of clicks needed (each click = 0.2)
        const clicksNeeded = Math.floor(betAmount / 0.2);
        console.log(`Need to click ${clicksNeeded} times for bet amount: ${betAmount}`);

        // First click to select the chip
        simulateClick(chipElement);

        // Perform the required number of clicks with small random delays
        for (let i = 0; i < clicksNeeded; i++) {
            setTimeout(() => {
                simulateClick(targetButton);
                console.log(`Click ${i + 1} of ${clicksNeeded}`);
            }, i * 5 + Math.floor(random(1, 3))); // 50ms base delay + random 10-30ms
        }
    }

    // Initialize with truly random wait rounds between 1-3
    let roundsToWait = Math.floor(random(1, 4)); // 1-3 rounds
    let currentRoundCount = 0;

    function calculateBetAmount() {
        const balance = getBalance();
        if (balance < 0.2) {
            console.warn("Insufficient balance to place a bet.");
            return null;
        }

        console.log(`Current Balance: $${balance}`);

        // Use 1/2 of balance as max bet limit
        const maxBetLimit = balance / 2;

        // Generate multiple random values for better distribution
        const r1 = random(0, 1);
        const r2 = random(0, 1);
        const r3 = random(0, 1);

        // Average of multiple random values for smoother distribution
        const randomFactor = (r1 + r2 + r3) / 3;

        // Calculate bet amount with enhanced randomization
        let betAmount = Math.round((randomFactor * maxBetLimit) * 100) / 100;

        // Ensure minimum bet of 0.2
        if (betAmount < 0.2) betAmount = 0.2;

        console.log(`Calculated Bet Amount: ${betAmount}`);
        return betAmount;
    }

    function handleBet() {
        currentRoundCount++;

        console.log(`Waiting Rounds: ${roundsToWait}, Current Round: ${currentRoundCount}`);

        if (currentRoundCount < roundsToWait) {
            console.log(`Skipping this round. Waiting for ${roundsToWait} rounds.`);
            return;
        }

        console.log(`Betting after ${roundsToWait} rounds!`);

        // Reset counter and set new random rounds to wait (1-3)
        currentRoundCount = 0;
        roundsToWait = Math.floor(random(1, 4));

        const betAmount = calculateBetAmount();
        if (!betAmount) return;

        // Enhanced randomization for bet choice using multiple random values
        const r1 = random(0, 1);
        const r2 = random(0, 1);
        const betChoice = ((r1 + r2) / 2) < 0.5 ? "Player" : "Banker";

        console.log(`Betting on: ${betChoice}`);

        // Random delay between 3-5 seconds
        const delay = Math.floor(random(3000, 5000));
        setTimeout(() => {
            const targetButton = getButton(betChoice);
            if (targetButton) {
                placeBet(targetButton, betAmount);
            } else {
                console.warn(`${betChoice} button not found!`);
            }
        }, delay);
    }

    window.addEventListener('ResultDetected', function (e) {
        const { name } = e.detail;
        console.log(`Received ResultDetected event with name: ${name}`);

        if (["B", "T", "P"].includes(name)) {
            console.log(`${name} detected! Tracking rounds.`);
            handleBet();
        } else {
            console.log(`Ignored result: ${name}`);
        }
    });
})(); 