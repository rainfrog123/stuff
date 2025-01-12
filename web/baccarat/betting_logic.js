// ==UserScript==
// @name         Betting Handler with Random Split Logic and Adjusted Calculation
// @namespace    http://tampermonkey.net/
// @version      1.9
// @description  Receives betting signal, calculates bet based on adjusted balance, and clicks the appropriate Player or Banker button, with random bet amount logic.
// @author       You
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    console.log("Betting Handler Script Initialized: Listening for ResultDetected event...");

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

    function getChipElement(chipValue) {
        const chipSelectors = {
            20: "span:nth-child(4)", // New chip value
            5: "span:nth-child(3)",
            1: "span:nth-child(2)",
            0.2: "span:nth-child(1)",
        };
        return document.querySelector(`#scalable > div.css-1fee25s.e1vfy7cn1 > div.css-1t0bgiz.e1vfy7cn0 > ${chipSelectors[chipValue]}`);
    }

    async function getBalance() {
        return new Promise((resolve) => {
            setTimeout(() => {
                const balanceElement = document.querySelector('.balanceContainer .balance .amt');
                if (balanceElement) {
                    const balanceText = balanceElement.textContent.replace('$', '').trim();
                    const balance = parseFloat(balanceText);
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
            }, 3000);
        });
    }

    function splitBetAmount(amount) {
        amount = parseFloat(amount);
        if (isNaN(amount)) {
            console.error("Invalid amount passed to splitBetAmount:", amount);
            return [];
        }

        const chips = [20, 5, 1, 0.2]; // Include the new chip
        const chunks = [];

        for (const chip of chips) {
            while (amount >= chip) {
                chunks.push(chip);
                amount = parseFloat((amount - chip).toFixed(2));
            }
        }

        if (amount > 0) {
            console.warn(`Remaining balance ${amount.toFixed(2)} could not be placed using available chips.`);
        }

        return chunks;
    }

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

    function handleBet() {
        getBalance().then((balance) => {
            if (balance <= 0) {
                console.warn("Insufficient balance to place a bet.");
                return;
            }

            const adjustedBalance = balance < 100 ? balance : balance % 100; // Use full balance if less than 100, otherwise last two digits
            const randomBetAmount = (Math.random() * (adjustedBalance / 2)).toFixed(2); // Random value between 0 and 1/2 of the adjusted balance

            let betAmount = parseFloat(randomBetAmount);
            if (betAmount < 0.2) {
                betAmount = 0.2; // Ensure the minimum bet is 0.2
            }

            console.log(`Balance: $${balance}, Adjusted Balance: ${adjustedBalance}, Calculated Bet Amount: ${betAmount}`);

            const betChunks = splitBetAmount(betAmount);
            console.log("Bet chunks:", betChunks);

            const betChoice = Math.random() < 0.5 ? "Player" : "Banker";
            console.log(`Betting: ${betChoice}`);

            setTimeout(() => {
                const targetButton = getButton(betChoice);
                if (targetButton) {
                    placeBet(betChunks, targetButton);
                } else {
                    console.warn(`${betChoice} button not found!`);
                }
            }, 2000);
        });
    }

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
