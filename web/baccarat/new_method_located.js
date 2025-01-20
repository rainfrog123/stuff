var counter = document.querySelector('.TileStatistics_round-mobile-counter__cjd3w');
var player_counter = currentElement.nextElementSibling; // Gets the next sibling element
var banker_counter = player_counter.nextElementSibling; // Gets the next sibling element
var tie_counter = banker_counter.nextElementSibling; // Gets the next sibling element
counter.parentElement.parentElement.parentElement.parentElement.parentElement

counter.parentElement.parentElement.parentElement.parentElement.parentElement.textContent

var fullText = counter.parentElement.parentElement.parentElement.parentElement.parentElement.textContent;
var extractedPart = fullText.split('$')[0].trim();  // Splits at the dollar sign and trims whitespace
console.log(extractedPart);  // Output: 'Baccarat 3'

// Select all counters
var counters = document.querySelectorAll('.TileStatistics_round-mobile-counter__cjd3w');

function observeTieCounter(tieCounter) {
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' || mutation.type === 'characterData') {
                var newValue = tieCounter.textContent.match(/\d+/)[0];
                console.log(`Tie counter changed to: ${newValue}`);
            }
        });
    });

    // Configuration of the observer:
    var config = { childList: true, characterData: true, subtree: true };

    // Start observing the specified element for configured mutations
    observer.observe(tieCounter, config);
}


// Iterate through each counter
counters.forEach(function(counter) {
    var player_counter = counter.nextElementSibling;
    var banker_counter = player_counter.nextElementSibling;
    var tie_counter = banker_counter.nextElementSibling;

    // Clean and print initial values
    console.log(`Counter: ${counter.textContent.match(/\d+/)[0]}`);
    console.log(`Player: ${player_counter.textContent.match(/\d+/)[0]}`);
    console.log(`Banker: ${banker_counter.textContent.match(/\d+/)[0]}`);
    console.log(`Tie: ${tie_counter.textContent.match(/\d+/)[0]}`);

    // Set up mutation observer for the tie counter
    observeTieCounter(tie_counter);
});




var counters = document.querySelectorAll('.TileStatistics_round-mobile-counter__cjd3w');

function observeTieCounter(tieCounter, name) {
    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (mutation.type === 'childList' || mutation.type === 'characterData') {
                var newValue = tieCounter.textContent.match(/\d+/)[0];
                console.log(`[${name}] Tie counter changed to: ${newValue}`);
            }
        });
    });

    // Configuration of the observer:
    var config = { childList: true, characterData: true, subtree: true };

    // Start observing the specified element for configured mutations
    observer.observe(tieCounter, config);
}

// Iterate through each counter
counters.forEach(function (counter) {
    var player_counter = counter.nextElementSibling;
    var banker_counter = player_counter.nextElementSibling;
    var tie_counter = banker_counter.nextElementSibling;

    // Extract the name from the parent element
    var parentElement = counter.parentElement.parentElement.parentElement.parentElement.parentElement;
    var fullText = parentElement.textContent;
    var extractedPart = fullText.split('$')[0].trim(); // Extract name before '$'

    // Clean and print initial values
    console.log(`[${extractedPart}] Counter: ${counter.textContent.match(/\d+/)[0]}`);
    console.log(`[${extractedPart}] Player: ${player_counter.textContent.match(/\d+/)[0]}`);
    console.log(`[${extractedPart}] Banker: ${banker_counter.textContent.match(/\d+/)[0]}`);
    console.log(`[${extractedPart}] Tie: ${tie_counter.textContent.match(/\d+/)[0]}`);

    // Set up mutation observer for the tie counter and include the name
    observeTieCounter(tie_counter, extractedPart);
});


// ==UserScript==
// @name         Monitor TIE Results and Random Bet Calculation
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
