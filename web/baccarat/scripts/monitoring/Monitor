// ==UserScript==
// @name         Monitor TIE Results and Random Bet Calculation X2
// @namespace    http://tampermonkey.net/
// @version      2.7
// @description  Monitor TIE results, dynamically calculate random bet amounts, and simulate betting with multiple clicks for a total bet amount using 0.2 chips.
// @author       Your Name
// @match        *://client.pragmaticplaylive.net/desktop/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @grant        GM_log
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    const bankerPrefix = "betPositionBGTemp mobile banker";
    const playerPrefix = "betPositionBGTemp mobile player";

    // Function to generate a random number between 0 and 1
    function random() {
        return Math.random();
    }

    // Simulate clicks for a total bet amount using 0.2 chips
    function simulateBetClicks(button, totalAmount) {
        const chipValue = 0.2;
        const clicks = Math.floor(totalAmount / chipValue);

        for (let i = 0; i < clicks; i++) {
            setTimeout(() => {
                button.click();
                console.log(`Clicked ${i + 1} out of ${clicks} for bet amount: ${totalAmount}`);
            }, i * 10); // 10ms delay between clicks to avoid issues
        }
    }

    // Retrieve balance from localStorage
    function getBalanceFromLocalStorage() {
        const balance = parseFloat(localStorage.getItem('currentBalance'));
        if (isNaN(balance)) {
            console.warn('No valid balance found in localStorage. Defaulting to 0.');
            return 0;
        }
        console.log('Retrieved Balance from localStorage:', balance);
        return balance;
    }

    // Observer for TIE results and betting logic
    function monitorTieResultsAndClickButtons() {
        const counters = document.querySelectorAll('.TileStatistics_round-mobile-counter__cjd3w');

        counters.forEach(function (counter) {
            var parentElement = counter.parentElement.parentElement.parentElement.parentElement.parentElement;

            // Extract name or identifier for logging
            var fullText = parentElement.textContent;
            var extractedPart = fullText.split('$')[0].trim();

            console.log(`[${extractedPart}] Monitoring TIE results.`);

            var tieCounter = counter.nextElementSibling.nextElementSibling.nextElementSibling;

            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' || mutation.type === 'characterData') {
                        var newValue = tieCounter.textContent.match(/\d+/)[0];
                        console.log(`[${extractedPart}] TIE counter changed to: ${newValue}`);

                        // Find player and banker buttons
                        const bankerButton = Array.from(parentElement.querySelectorAll("*"))
                            .find((el) => {
                                return typeof el.className === "string" && el.className.includes(bankerPrefix);
                            });

                        const playerButton = Array.from(parentElement.querySelectorAll("*"))
                            .find((el) => {
                                return typeof el.className === "string" && el.className.includes(playerPrefix);
                            });

                        if (bankerButton || playerButton) {
                            const balance = getBalanceFromLocalStorage();
                            if (balance <= 0) {
                                console.warn(`[${extractedPart}] Insufficient balance to place a bet.`);
                                return;
                            }

                            const adjustedBalance = balance < 100 ? balance : balance % 100;
                            const randomValue = random();
                            let betAmount = Math.round((randomValue * (adjustedBalance / 2)) * 100) / 100;

                            if (betAmount < 0.2) betAmount = 0.2;

                            console.log(`[${extractedPart}] Calculated Bet Amount: ${betAmount}`);

                            // Random choice between player or banker
                            const randomChoice = Math.random() < 0.5 ? "banker" : "player";
                            const targetButton = randomChoice === "banker" ? bankerButton : playerButton;

                            if (targetButton) {
                                console.log(`[${extractedPart}] Betting on: ${randomChoice.toUpperCase()} based on random decision.`);
                                setTimeout(() => {
                                    simulateBetClicks(targetButton, betAmount);
                                }, 5000); // 5-second delay before betting
                            } else {
                                console.warn(`[${extractedPart}] No valid button to click.`);
                            }
                        }
                    }
                });
            });

            observer.observe(tieCounter, {
                childList: true,
                characterData: true,
                subtree: true,
            });
        });

        console.log("Monitoring for TIE counter changes...");
    }

    // Start monitoring
    monitorTieResultsAndClickButtons();
})();
