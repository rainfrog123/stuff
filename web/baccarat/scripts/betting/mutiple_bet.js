// Function to monitor and log elements with "TIE" in their content along with parent element content
function monitorTieResultsAndClickButtons() {
    const targetPrefix = "GameResultAndYouWin_winContainer__";
    const bankerPrefix = "betPositionBGTemp mobile banker";
    const playerPrefix = "betPositionBGTemp mobile player";

    // Observer to detect changes in the DOM
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                // Ensure the node is an HTMLElement
                if (node.nodeType === 1 && node instanceof HTMLElement) {
                    // Check each class in the node's class list
                    const classList = node.className.split(/\s+/); // Split class string into an array
                    const matchedClass = classList.find((cls) => cls.startsWith(targetPrefix));
                    if (matchedClass) {
                        // Check if the node or its children contain the word "TIE"
                        const textContent = node.textContent.trim();
                        if (/TIE/i.test(textContent)) { // Case-insensitive match for "TIE"
                            const parentElement = node.parentElement; // Get the parent element

                            if (parentElement) {
                                // Dynamically identify the BANKER and PLAYER buttons using the prefixes
                                const bankerButton = Array.from(parentElement.querySelectorAll("*")).find((el) => {
                                    return el.className && typeof el.className === "string" && el.className.includes(bankerPrefix);
                                });

                                const playerButton = Array.from(parentElement.querySelectorAll("*")).find((el) => {
                                    return el.className && typeof el.className === "string" && el.className.includes(playerPrefix);
                                });

                                console.log("Matched 'TIE' result container appeared:", {
                                    timestamp: new Date().toISOString(),
                                    outerHTML: node.outerHTML, // Save the node's outerHTML
                                    textContent: textContent, // Save the visible text content of the node
                                    parentOuterHTML: parentElement.outerHTML, // Save the parent's outerHTML
                                    bankerButtonFound: !!bankerButton, // Check if banker button exists
                                    playerButtonFound: !!playerButton, // Check if player button exists
                                    bankerButtonHTML: bankerButton ? bankerButton.outerHTML : "Not found", // Print banker button details
                                    playerButtonHTML: playerButton ? playerButton.outerHTML : "Not found", // Print player button details
                                });

                                // Randomly click on BANKER or PLAYER after a delay of 2 seconds
                                if (bankerButton || playerButton) {
                                    setTimeout(() => {
                                        const randomChoice = Math.random() < 0.5 ? "banker" : "player";
                                        if (randomChoice === "banker" && bankerButton) {
                                            bankerButton.click();
                                            console.log("Clicked on the BANKER button.");
                                        } else if (randomChoice === "player" && playerButton) {
                                            playerButton.click();
                                            console.log("Clicked on the PLAYER button.");
                                        } else {
                                            console.log("No button to click.");
                                        }
                                    }, 5000); // 5-second delay
                                }
                            }
                        }
                    }
                }
            });
        });
    });

    // Start observing the document body for changes
    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });

    console.log("Monitoring for dynamic TIE results and clicking buttons...");
}

// Run the monitoring function
monitorTieResultsAndClickButtons();




// ==UserScript==
// @name         Monitor TIE Results and Random Bet Calculation
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Monitor TIE results, dynamically calculate random bet amounts, and simulate betting with multiple clicks for a total bet amount using 0.2 chips.
// @author       Your Name
// @match        *://client.pragmaticplaylive.net/desktop/baccaratgame/*
// @grant        none
// ==/UserScript==

    (function() {
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
                }, i * 100); // 200ms delay between clicks to avoid issues
            }
        }

        // Retrieve current balance (mocked or actual implementation)
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
                }, 1000);
            });
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
                                        const bankerButton = Array.from(parentElement.querySelectorAll("*")).find((el) => {
                                            return el.className && typeof el.className === "string" && el.className.includes(bankerPrefix);
                                        });

                                        const playerButton = Array.from(parentElement.querySelectorAll("*")).find((el) => {
                                            return el.className && typeof el.className === "string" && el.className.includes(playerPrefix);
                                        });

                                        console.log("Matched 'TIE' result container:", {
                                            timestamp: new Date().toISOString(),
                                            bankerButtonFound: !!bankerButton,
                                            playerButtonFound: !!playerButton,
                                        });

                                        if (bankerButton || playerButton) {
                                            getBalance().then((balance) => {
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
                                                    }, 5000); // 2-second delay before betting
                                                } else {
                                                    console.warn("No valid button to click.");
                                                }
                                            });
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
