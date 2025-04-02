// ==UserScript==
// @name         Baccarat TIE Monitor with Enhanced Random Distribution
// @namespace    http://tampermonkey.net/
// @version      3.0
// @description  Advanced baccarat TIE monitoring system with cryptographic randomization and natural betting patterns
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

    // Standard random number generation
    function random(min, max) {
        return min + Math.random() * (max - min);
    }

    // Random value between 0 and 1
    function getRandomFactor() {
        const randomValue = random(0, 1);
        return randomValue;
    }

    // Track last bet to maintain 1:1 ratio
    let lastBetWasBanker = null;
    let consecutiveSameBets = 0;
    const MAX_CONSECUTIVE = 3;

    function simulateBetClicks(button, totalAmount) {
        const chipValue = 0.2;
        const clicks = Math.floor(totalAmount / chipValue);

        for (let i = 0; i < clicks; i++) {
            setTimeout(() => {
                button.click();
                console.log(`Clicked ${i + 1} out of ${clicks} for bet amount: ${totalAmount}`);
            }, i * 5 + Math.floor(random(1, 3)));
        }
    }

    function getBalanceFromLocalStorage() {
        const balance = parseFloat(localStorage.getItem('currentBalance'));
        if (isNaN(balance)) {
            console.warn('No valid balance found in localStorage. Defaulting to 0.');
            return 0;
        }
        console.log('Retrieved Balance from localStorage:', balance);
        return balance;
    }

    function monitorTieResultsAndClickButtons() {
        const counters = document.querySelectorAll('.TileStatistics_round-mobile-counter__cjd3w');

        counters.forEach(function (counter) {
            var parentElement = counter.parentElement.parentElement.parentElement.parentElement.parentElement;
            
            // Get table name from the parent element
            var tableName = "";
            try {
                const tableNameElement = parentElement.querySelector('.tableName');
                if (tableNameElement) {
                    tableName = tableNameElement.textContent.trim();
                } else {
                    tableName = parentElement.textContent.split('$')[0].trim();
                }
            } catch (e) {
                tableName = "Unknown Table";
                console.warn("Could not get table name:", e);
            }

            console.log(`[${tableName}] Started monitoring TIE results.`);

            var tieCounter = counter.nextElementSibling.nextElementSibling.nextElementSibling;

            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' || mutation.type === 'characterData') {
                        var newValueMatch = tieCounter.textContent.match(/\d+/);
                        if (!newValueMatch) return;

                        var newValue = parseInt(newValueMatch[0]);
                        console.log(`[${tableName}] TIE counter changed to: ${newValue}`);

                        if (newValue <= 2) {
                            console.log(`[${tableName}] TIE counter ${newValue} ≤ 2, skipping bet.`);
                            return;
                        }

                        const bankerButton = Array.from(parentElement.querySelectorAll("*"))
                            .find((el) => typeof el.className === 'string' && el.className.includes(bankerPrefix));

                        const playerButton = Array.from(parentElement.querySelectorAll("*"))
                            .find((el) => typeof el.className === 'string' && el.className.includes(playerPrefix));

                        if (!bankerButton && !playerButton) {
                            console.warn(`[${tableName}] No valid betting button found.`);
                            return;
                        }

                        const balance = getBalanceFromLocalStorage();
                        if (balance <= 0) {
                            console.warn(`[${tableName}] Insufficient balance to place a bet.`);
                            return;
                        }

                        const maxBetLimit = balance / 2;
                        let betAmount = Math.round(random(0.2, maxBetLimit) * 100) / 100;
                        if (betAmount < 0.2) betAmount = 0.2;

                        console.log(`[${tableName}] TIE count: ${newValue}, Current Balance: $${balance}`);
                        console.log(`[${tableName}] Calculated Bet Amount: ${betAmount}`);

                        // Advanced betting choice logic with pattern breaking
                        let betChoice;
                        if (lastBetWasBanker === null) {
                            betChoice = getRandomFactor() < 0.5 ? "banker" : "player"; // Randomly decide
                        } else if (consecutiveSameBets >= MAX_CONSECUTIVE) {
                            betChoice = lastBetWasBanker ? "player" : "banker";
                            consecutiveSameBets = 0;
                        } else {
                            betChoice = getRandomFactor() < 0.5 ? "banker" : "player"; // Randomly decide
                            if ((betChoice === "banker") === lastBetWasBanker) {
                                consecutiveSameBets++;
                            } else {
                                consecutiveSameBets = 0;
                            }
                        }
                        
                        lastBetWasBanker = betChoice === "banker";
                        const targetButton = betChoice === "banker" ? bankerButton : playerButton;

                        if (targetButton) {
                            console.log(`[${tableName}] TIE count ${newValue} > 2, Betting on: ${betChoice.toUpperCase()}`);
                            const delay = Math.floor(random(6000, 10000));
                            setTimeout(() => {
                                simulateBetClicks(targetButton, betAmount);
                            }, delay);
                        } else {
                            console.warn(`[${tableName}] No valid button to click.`);
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

        console.log("Started monitoring tables for TIE counter changes...");
    }

    monitorTieResultsAndClickButtons();
})();
