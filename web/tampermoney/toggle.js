// ==UserScript==
// @name         ChatGPT 4o/o3 Model Toggle
// @namespace    http://tampermonkey.net/
// @version      2.0.0
// @description  Toggle between ChatGPT 4o and o3 models - Ctrl+X to switch
// @author       Assistant
// @match        https://chatgpt.com/*
// @match        https://chat.openai.com/*
// @grant        unsafeWindow
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-idle
// @icon         https://www.google.com/s2/favicons?sz=64&domain=chatgpt.com
// ==/UserScript==

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        models: {
            gpt4o: 'gpt-4o',
            o3: 'o3'
        },
        toggleKey: 'x',
        storageKey: 'chatgpt_model_toggle_v2'
    };

    // State management
    let currentModel = GM_getValue(CONFIG.storageKey, CONFIG.models.gpt4o);

    // Save state
    function saveState() {
        GM_setValue(CONFIG.storageKey, currentModel);
    }



    // Toggle between models
    function toggleModel() {
        currentModel = currentModel === CONFIG.models.gpt4o ? CONFIG.models.o3 : CONFIG.models.gpt4o;
        saveState();
        updateUIHeader();
    }

    // Update the ChatGPT UI header to show current model
    function updateUIHeader() {
        try {
            let modelElement = null;

            // Strategy 1: Look for button with model-switcher-dropdown-button (resized window)
            const modelSwitcherButton = document.querySelector('button[data-testid="model-switcher-dropdown-button"]');
            if (modelSwitcherButton) {
                const targetSpan = modelSwitcherButton.querySelector('span.text-token-text-tertiary');
                if (targetSpan) {
                    const spanText = targetSpan.textContent?.trim().toLowerCase();
                    if (spanText === 'o3' || spanText === '4o' || spanText === 'gpt-4o' || spanText === 'o3-mini') {
                        modelElement = targetSpan;
                    }
                }
            }

            // Strategy 2: Look for div containing "ChatGPT" and find the span with class "text-token-text-tertiary" (original window)
            if (!modelElement) {
                const chatgptHeaderDivs = document.querySelectorAll('div');
                chatgptHeaderDivs.forEach(div => {
                    const divText = div.textContent?.trim();
                    if (divText?.startsWith('ChatGPT ') && divText.length < 20) {
                        const targetSpan = div.querySelector('span.text-token-text-tertiary');
                        if (targetSpan) {
                            const spanText = targetSpan.textContent?.trim().toLowerCase();
                            if (spanText === 'o3' || spanText === '4o' || spanText === 'gpt-4o' || spanText === 'o3-mini') {
                                modelElement = targetSpan;
                                return;
                            }
                        }
                    }
                });
            }

            // Strategy 3: Fallback - Try to find any elements containing model names
            if (!modelElement) {
                const allSpans = document.querySelectorAll('span.text-token-text-tertiary');
                allSpans.forEach(span => {
                    const text = span.textContent?.trim().toLowerCase();
                    if (text === 'o3' || text === '4o' || text === 'gpt-4o' || text === 'o3-mini') {
                        modelElement = span;
                    }
                });
            }

            // Update the model name in the UI
            if (modelElement) {
                const shortName = currentModel === CONFIG.models.gpt4o ? '4o' : 'o3';
                const currentText = modelElement.textContent.trim();
                if (currentText !== shortName) {
                    modelElement.textContent = shortName;
                    modelElement.innerHTML = shortName;

                    // Ensure the change sticks
                    setTimeout(() => {
                        if (modelElement.textContent.trim() !== shortName) {
                            modelElement.textContent = shortName;
                            modelElement.innerHTML = shortName;
                        }
                    }, 50);
                }
            }
        } catch (error) {
            // Silent error handling
        }
    }

    // Intercept fetch requests to modify the model
    function setupFetchInterception() {
        if (!unsafeWindow.originalFetch) {
            unsafeWindow.originalFetch = unsafeWindow.fetch;
        }

        unsafeWindow.fetch = async (resource, config = {}) => {
            try {
                // Check if this is a conversation API call
                if (typeof resource === 'string' &&
                    resource.includes('/backend-api/conversation') &&
                    config.method === 'POST' &&
                    config.body) {

                    const body = JSON.parse(config.body);

                    // Modify the model in the request
                    if (body && currentModel) {
                        body.model = currentModel;
                        config.body = JSON.stringify(body);
                    }
                }
            } catch (error) {
                // If anything goes wrong, continue with original request
            }

            return unsafeWindow.originalFetch(resource, config);
        };
    }

    // Set up keyboard shortcuts
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Check for Ctrl+X combination
            if (event.key === CONFIG.toggleKey && event.ctrlKey && !event.altKey) {
                event.preventDefault();
                toggleModel();
            }
        });
    }

    // Monitor DOM changes to update header
    function setupDOMObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                // Check for changes to text content (like model names in header)
                if (mutation.type === 'characterData' ||
                    (mutation.type === 'childList' && mutation.target.textContent)) {
                    const target = mutation.target;
                    if (target.textContent &&
                        (target.textContent.includes('ChatGPT') ||
                         target.textContent.includes('o3') ||
                         target.textContent.includes('4o'))) {
                        // React immediately to header changes
                        setTimeout(updateUIHeader, 10);
                        setTimeout(updateUIHeader, 100);
                        setTimeout(updateUIHeader, 500);
                    }
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });
    }

    // Start monitoring for header changes
    function startHeaderMonitoring() {
        // Check for header updates more frequently to prevent reversion
        setInterval(() => {
            updateUIHeader();
        }, 500);
    }

    // Initialize the script
    function initialize() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initialize);
            return;
        }

        // Wait a bit for the page to fully load
        setTimeout(() => {
            setupFetchInterception();
            setupKeyboardShortcuts();
            setupDOMObserver();
            startHeaderMonitoring();

            // Initial UI update
            setTimeout(updateUIHeader, 1500);
        }, 1000);
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (observer) {
            observer.disconnect();
        }
    });

    // Start the script
    initialize();

})();