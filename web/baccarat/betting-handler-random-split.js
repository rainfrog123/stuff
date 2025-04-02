// ==UserScript==
// @name         Betting Handler with Crypto Randomness and Round-based Betting Delay
// @namespace    http://tampermonkey.net/
// @version      2.2
// @description  Receives betting signal, waits a random number of rounds (2-5), calculates bet based on adjusted balance, and clicks the appropriate Player or Banker button.
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
                localStorage.setItem('currentBalance', balance);
                console.log(`Balance updated in localStorage: ${balance}`);
                return balance;
            } else {
                console.warn("Invalid balance format!");
            }
        } else {
            console.warn("Unable to retrieve balance!");
        }
        return 0;
    }

    function updateBalancePeriodically() {
        setInterval(getBalance, 5000); // Update every second
    }

    function placeBet(targetButton, betAmount) {
        const chipElement = getChipElement();
        if (chipElement) {
            simulateClick(chipElement);
            simulateClick(targetButton);
            console.log(`Placed a bet of ${betAmount}`);
        } else {
            console.warn(`Chip of ${betAmount} not found!`);
        }
    }

    let roundsToWait = Math.floor(random(2, 6)); // Wait between 2-5 rounds before betting
    let currentRoundCount = 0;

    function handleBet() {
        currentRoundCount++;

        console.log(`Waiting Rounds: ${roundsToWait}, Current Round: ${currentRoundCount}`);

        if (currentRoundCount < roundsToWait) {
            console.log(`Skipping this round. Waiting for ${roundsToWait} rounds.`);
            return;
        }

        console.log(`Betting after ${roundsToWait} rounds!`);

        currentRoundCount = 0; // Reset counter
        roundsToWait = Math.floor(random(2, 6)); // Set new random rounds to wait

        const balance = getBalance();
        if (balance < 0.2) {
            console.warn("Insufficient balance to place a bet.");
            return;
        }

        console.log(`Balance: $${balance}`);

        // ✅ Randomized bet amount, ensuring it's below 1/4 of adjusted balance
        const adjustedBalance = balance < 100 ? balance : balance % 100;
        let maxBetLimit = adjustedBalance / 4;
        let randomBetFactor = random(0.1, 0.9); // Random factor between 0.1 - 0.9
        let betAmount = Math.round((randomBetFactor * maxBetLimit) * 100) / 100;

        if (betAmount < 0.2) betAmount = 0.2; // Minimum bet 0.2

        console.log(`Calculated Bet Amount: ${betAmount}`);

        // ✅ Randomly choose between Banker or Player
        const betChoice = random(0, 1) < 0.5 ? "Player" : "Banker";
        console.log(`Betting on: ${betChoice}`);

        setTimeout(() => {
            const targetButton = getButton(betChoice);
            if (targetButton) {
                placeBet(targetButton, betAmount);
            } else {
                console.warn(`${betChoice} button not found!`);
            }
        }, 3000); // Keep a fixed 2-second delay for natural behavior
    }

    window.addEventListener('ResultDetected', function (e) {
        const { name } = e.detail;
        console.log(`Received ResultDetected event with name: ${name}`);

        if (["B", "T", "P"].includes(name)) { // ✅ Now tracks B, T, P rounds instead of just B
            console.log(`${name} detected! Tracking rounds.`);
            handleBet();
        } else {
            console.log(`Ignored result: ${name}`);
        }
    });

    // Start periodic balance updates
    updateBalancePeriodically();
})();
