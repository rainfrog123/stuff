// ==UserScript==
// @name         Betting Handler with Random Split Logic
// @namespace    http://tampermonkey.net/
// @version      1.6
// @description  Receives betting signal, splits the bet amount including decimals, and clicks the appropriate Player or Banker button.
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    console.log("Betting Handler Script Initialized: Listening for ResultDetected event...");

    // Simulate a click on an element
    function simulateClick(element) {
        if (element) {
            element.click();
        } else {
            console.warn("Element not found!");
        }
    }

    // Retrieve the Player or Banker button
    function getButton(type) {
        return document.querySelector(
            type === "Player"
                ? '.PLAYER_PATH .betspotAsset'
                : '.BANKER_PATH .betspotAsset'
        );
    }

    // Retrieve chip elements by value
    function getChipElement(chipValue) {
        const chipSelectors = {
            0.2: "span:nth-child(1)", // Chip 0.2
            1: "span:nth-child(2)",  // Chip 1
            5: "span:nth-child(3)",  // Chip 5
        };
        return document.querySelector(`#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > ${chipSelectors[chipValue]}`);
    }

    // Retrieve the current balance
    async function getBalance() {
        return new Promise((resolve) => {
            setTimeout(() => {
                const balanceElement = document.querySelector('.balanceContainer .balance .amt');
                if (balanceElement) {
                    const balanceText = balanceElement.textContent.replace('$', '').trim();
                    const balance = parseFloat(balanceText); // Exact balance, including decimals
                    if (!isNaN(balance)) {
                        resolve(balance);
                    } else {
                        console.warn("Invalid balance format!");
                        resolve(0);
                    }
                } else {
                    console.warn("Unable to retrieve balance!");
                    resolve(0);
                }
            }, 3000); // 3-second delay
        });
    }

    // Split bet amount into exact chips, including decimals
    function splitBetAmount(amount) {
        amount = parseFloat(amount); // Ensure amount is a number
        if (isNaN(amount)) {
            console.error("Invalid amount passed to splitBetAmount:", amount);
            return [];
        }

        const chips = [5, 1, 0.2]; // Chip values in descending order
        const chunks = [];

        for (const chip of chips) {
            while (amount >= chip) { // Ensure precision
                chunks.push(chip);
                amount = parseFloat((amount - chip).toFixed(2)); // Fix precision issues after subtraction
            }
        }

        if (amount > 0) {
            console.warn(`Remaining balance ${amount.toFixed(2)} could not be placed using available chips.`);
        }

        return chunks;
    }

    // Place bets on the target button
    function placeBet(chunks, targetButton) {
        chunks.forEach((chipValue) => {
            const chipElement = getChipElement(chipValue);
            if (chipElement) {
                simulateClick(chipElement);
                simulateClick(targetButton);
                console.log(`Placed a bet of ${chipValue}`);
            } else {
                console.warn(`Chip ${chipValue} not found!`);
            }
        });
    }

    // Handle the bet
    function handleBet() {
        getBalance().then((balance) => { // Use .then() to handle the Promise
            if (balance <= 0) {
                console.warn("Insufficient balance to place a bet.");
                return;
            }

            // Calculate a random bet amount between 0 and 1/2 of the balance
            let betAmount = (Math.random() * (balance / 2)).toFixed(2);
            if (betAmount < 0.2) {
                betAmount = 0.2;
            }
            console.log(`Balance: $${balance}, Calculated Bet Amount: ${betAmount}`);

            const betChunks = splitBetAmount(betAmount);
            console.log("Bet chunks:", betChunks);

            const initialChoices = ["Player", "Banker"];

            // Randomly choose an initial bet
            const initialChoice = initialChoices[Math.random() < 0.5 ? 0 : 1];

            // Determine the opposite bet
            const betChoice = initialChoice === "Player" ? "Banker" : "Player";

            console.log(`Betting: ${betChoice}`);

            setTimeout(() => {
                const targetButton = getButton(betChoice);
                if (targetButton) {
                    placeBet(betChunks, targetButton);
                } else {
                    console.warn(`${betChoice} button not found!`);
                }
            }, 2000); // Delay of 2 seconds
        });
    }

    // Listen for the ResultDetected event
    window.addEventListener('ResultDetected', function (e) {
        const { name } = e.detail;
        console.log(`Received ResultDetected event with name: ${name}`);

        if (["B", "P", "T"].includes(name)) {
            handleBet();
        } else {
            console.warn("Unrecognized result:", name);
        }
    });
})();
