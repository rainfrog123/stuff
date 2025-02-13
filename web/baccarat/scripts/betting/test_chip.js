// ==UserScript==
// @name         Monitor TIE Results and Random Bet Calculation with Iframe Support
// @namespace    http://tampermonkey.net/
// @version      2.4
// @description  Monitor TIE results, dynamically calculate random bet amounts, and simulate betting with multiple clicks for a total bet amount using 0.2 chips. Supports multiple iframes.
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

    const targetPrefix = "GameResultAndYouWin_winContainer__";
    const bankerPrefix = "betPositionBGTemp mobile banker";
    const playerPrefix = "betPositionBGTemp mobile player";

    // Seed-based random generator
    function seedrandom(seed) {
        let x = Math.sin(seed) * 10000;
        return x - Math.floor(x);
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

    // Retrieve current balance by iterating over all iframes
    function findBalance() {
    // Check parent document first
    const parentBalanceElement = document.querySelector('.balanceContainer .balance .amt');
    if (parentBalanceElement) {
        return parseFloat(parentBalanceElement.textContent.replace('$', '').trim()) || 0;
    }

    // Then check iframes
    const iframes = document.querySelectorAll('iframe');
    for (let iframe of iframes) {
        try {
            const iframeDoc = iframe.contentDocument;
            if (iframeDoc) {
                const iframeBalanceElement = iframeDoc.querySelector('.balanceContainer .balance .amt');
                if (iframeBalanceElement) {
                    return parseFloat(iframeBalanceElement.textContent.replace('$', '').trim()) || 0;
                }
            }
        } catch (err) {
            console.warn("Error accessing iframe:", err);
        }
    }

    console.warn("Balance not found!");
    return 0;
}


    // Observer for TIE results and betting logic
    function monitorTieResultsAndClickButtons() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node instanceof HTMLElement) {
                        const classList = node.className.split(/\s+/);
                        const matchedClass = classList.find((cls) => cls.startsWith(targetPrefix));

                        if (matchedClass) {
                            const textContent = node.textContent.trim();
                            if (/TIE/i.test(textContent)) {
                                const parentElement = node.parentElement;

                                if (parentElement) {
                                    const bankerButton = Array.from(parentElement.querySelectorAll("*"))
                                        .find((el) => el.className && typeof el.className === "string" && el.className.includes(bankerPrefix));

                                    const playerButton = Array.from(parentElement.querySelectorAll("*"))
                                        .find((el) => el.className && typeof el.className === "string" && el.className.includes(playerPrefix));

                                    console.log("Matched 'TIE' result container:", {
                                        timestamp: new Date().toISOString(),
                                        bankerButtonFound: !!bankerButton,
                                        playerButtonFound: !!playerButton,
                                    });

                                    if (bankerButton || playerButton) {
                                        const balance = findBalanceInIframes();
                                        if (balance <= 0) {
                                            console.warn("Insufficient balance to place a bet.");
                                            return;
                                        }

                                        const adjustedBalance = balance < 100 ? balance : balance % 100;
                                        const randomValue = seedrandom(Date.now());
                                        let betAmount = Math.round((randomValue * (adjustedBalance / 2)) * 100) / 100;

                                        if (betAmount < 0.2) betAmount = 0.2;

                                        console.log(`Calculated Bet Amount: ${betAmount}`);

                                        const randomChoice = Math.random() < 0.5 ? "banker" : "player";
                                        const targetButton = randomChoice === "banker" ? bankerButton : playerButton;

                                        if (targetButton) {
                                            console.log(`Betting on: ${randomChoice.toUpperCase()}`);
                                            setTimeout(() => {
                                                simulateBetClicks(targetButton, betAmount);
                                            }, 5000); // 5-second delay before betting
                                        } else {
                                            console.warn("No valid button to click.");
                                        }
                                    }
                                }
                            }
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });

        console.log("Monitoring for dynamic TIE results and betting...");
    }

    // Start monitoring
    monitorTieResultsAndClickButtons();
})();
