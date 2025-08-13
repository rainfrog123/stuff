// ==UserScript==
// @name         ChatGPT 4o/o3 Model Toggle
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Toggle between ChatGPT 4o and o3 models with debugging
// @author       Assistant
// @match        https://chatgpt.com/*
// @match        https://chat.openai.com/*
// @grant        unsafeWindow
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @run-at       document-idle
// @icon         https://www.google.com/s2/favicons?sz=64&domain=chatgpt.com
// ==/UserScript==

(function() {
    'use strict';

    // Debug logging function
    function debugLog(message, data = null) {
        const timestamp = new Date().toISOString();
        console.log(`[ChatGPT Toggle] ${timestamp}: ${message}`, data || '');
        
        // Store debug logs for later inspection
        const logs = GM_getValue('debug_logs', []);
        logs.push(`${timestamp}: ${message} ${data ? JSON.stringify(data) : ''}`);
        
        // Keep only last 100 logs
        if (logs.length > 100) {
            logs.splice(0, logs.length - 100);
        }
        
        GM_setValue('debug_logs', logs);
    }

    // Configuration
    const CONFIG = {
        models: {
            'gpt-4o': {
                name: '4o',
                fullName: 'GPT-4o',
                value: 'gpt-4o'
            },
            'o3': {
                name: 'o3',
                fullName: 'o3',
                value: 'o3'
            }
        },
        defaultModel: 'gpt-4o',
        toggleKey: 'x', // Key to toggle models
        buttonPosition: 'top-right' // Position of toggle button
    };

    let currentModel = GM_getValue('current_model', CONFIG.defaultModel);
    let isInitialized = false;
    let toggleButton = null;
    let originalFetch = null;

    debugLog('Script starting', { currentModel, CONFIG });

    // Model toggle functionality
    class ModelToggle {
        constructor() {
            this.init();
        }

        async init() {
            debugLog('Initializing ModelToggle');
            
            try {
                await this.waitForPageLoad();
                this.setupFetchHook();
                this.createToggleButton();
                this.setupKeyboardShortcut();
                this.setupMenuCommands();
                this.observePageChanges();
                
                isInitialized = true;
                debugLog('ModelToggle initialized successfully');
            } catch (error) {
                debugLog('Error initializing ModelToggle', error.message);
            }
        }

        async waitForPageLoad() {
            return new Promise((resolve) => {
                if (document.readyState === 'complete') {
                    resolve();
                } else {
                    window.addEventListener('load', resolve);
                }
            });
        }

        setupFetchHook() {
            debugLog('Setting up fetch hook');
            
            if (!originalFetch) {
                originalFetch = unsafeWindow.fetch;
            }

            unsafeWindow.fetch = async (resource, config = {}) => {
                try {
                    // Check if this is a conversation API call
                    if (typeof resource === 'string' && 
                        resource.includes('/backend-api/conversation') &&
                        config.method === 'POST' &&
                        config.body) {
                        
                        debugLog('Intercepting conversation request', { url: resource, currentModel });
                        
                        const body = JSON.parse(config.body);
                        
                        // Modify the model in the request
                        if (body && currentModel !== 'auto') {
                            const oldModel = body.model;
                            body.model = currentModel;
                            config.body = JSON.stringify(body);
                            
                            debugLog('Model changed in request', { 
                                from: oldModel, 
                                to: currentModel,
                                requestBody: body 
                            });
                        }
                    }
                } catch (error) {
                    debugLog('Error processing fetch request', error.message);
                }

                return originalFetch(resource, config);
            };

            debugLog('Fetch hook setup complete');
        }

        createToggleButton() {
            debugLog('Creating toggle button');

            // Remove existing button if any
            if (toggleButton) {
                toggleButton.remove();
            }

            toggleButton = document.createElement('div');
            toggleButton.id = 'model-toggle-button';
            toggleButton.innerHTML = `
                <button type="button" style="
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-family: system-ui, -apple-system, sans-serif;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    transition: all 0.2s ease;
                    min-width: 60px;
                    text-align: center;
                " 
                onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 6px 16px rgba(0,0,0,0.2)'"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)'"
                title="Toggle between GPT-4o and o3 models (Ctrl+X)">
                    ${CONFIG.models[currentModel]?.name || 'Unknown'}
                </button>
            `;

            const button = toggleButton.querySelector('button');
            button.addEventListener('click', () => this.toggleModel());

            document.body.appendChild(toggleButton);
            debugLog('Toggle button created and added to page');
        }

        async toggleModel() {
            const modelKeys = Object.keys(CONFIG.models);
            const currentIndex = modelKeys.indexOf(currentModel);
            const nextIndex = (currentIndex + 1) % modelKeys.length;
            const newModel = modelKeys[nextIndex];

            debugLog('Toggling model', { 
                from: currentModel, 
                to: newModel,
                fromName: CONFIG.models[currentModel]?.name,
                toName: CONFIG.models[newModel]?.name 
            });

            currentModel = newModel;
            GM_setValue('current_model', currentModel);

            this.updateButtonText();
            this.showNotification(`Switched to ${CONFIG.models[currentModel].fullName}`);

            debugLog('Model toggled successfully', { newModel: currentModel });
        }

        updateButtonText() {
            if (toggleButton) {
                const button = toggleButton.querySelector('button');
                if (button) {
                    button.textContent = CONFIG.models[currentModel]?.name || 'Unknown';
                    debugLog('Button text updated', { newText: button.textContent });
                }
            }
        }

        showNotification(message) {
            debugLog('Showing notification', message);

            // Remove existing notifications
            const existingNotifications = document.querySelectorAll('.model-toggle-notification');
            existingNotifications.forEach(n => n.remove());

            const notification = document.createElement('div');
            notification.className = 'model-toggle-notification';
            notification.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 10001;
                background: #10b981;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 14px;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transform: translateX(100%);
                transition: transform 0.3s ease;
            `;
            notification.textContent = message;

            document.body.appendChild(notification);

            // Animate in
            requestAnimationFrame(() => {
                notification.style.transform = 'translateX(0)';
            });

            // Remove after 3 seconds
            setTimeout(() => {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }

        setupKeyboardShortcut() {
            debugLog('Setting up keyboard shortcuts');

            document.addEventListener('keydown', (event) => {
                // Check for Ctrl+X combination
                if (event.key === CONFIG.toggleKey && event.ctrlKey && !event.altKey) {
                    event.preventDefault();
                    debugLog('Keyboard shortcut triggered', { key: event.key, ctrlKey: event.ctrlKey, altKey: event.altKey });
                    this.toggleModel();
                }
            });

            debugLog('Keyboard shortcuts setup complete');
        }

        setupMenuCommands() {
            debugLog('Setting up menu commands');

            GM_registerMenuCommand('Toggle Model', () => {
                this.toggleModel();
            });

            GM_registerMenuCommand('Show Debug Logs', () => {
                const logs = GM_getValue('debug_logs', []);
                console.group('ChatGPT Model Toggle Debug Logs');
                logs.forEach(log => console.log(log));
                console.groupEnd();
                alert(`Debug logs (${logs.length} entries) have been output to the console.`);
            });

            GM_registerMenuCommand('Clear Debug Logs', () => {
                GM_setValue('debug_logs', []);
                debugLog('Debug logs cleared');
                alert('Debug logs cleared.');
            });

            GM_registerMenuCommand('Reset to GPT-4o', () => {
                currentModel = 'gpt-4o';
                GM_setValue('current_model', currentModel);
                this.updateButtonText();
                this.showNotification('Reset to GPT-4o');
                debugLog('Model reset to GPT-4o');
            });

            debugLog('Menu commands setup complete');
        }

        observePageChanges() {
            debugLog('Setting up page change observer');

            const observer = new MutationObserver((mutations) => {
                let shouldReinitialize = false;

                mutations.forEach((mutation) => {
                    // Check if the toggle button was removed
                    if (mutation.type === 'childList') {
                        mutation.removedNodes.forEach((node) => {
                            if (node.id === 'model-toggle-button') {
                                shouldReinitialize = true;
                            }
                        });
                    }
                });

                if (shouldReinitialize) {
                    debugLog('Page change detected, recreating toggle button');
                    setTimeout(() => this.createToggleButton(), 1000);
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            debugLog('Page change observer setup complete');
        }

        // Method to get current status for debugging
        getStatus() {
            return {
                isInitialized,
                currentModel,
                modelName: CONFIG.models[currentModel]?.name,
                hasToggleButton: !!document.getElementById('model-toggle-button'),
                fetchHooked: unsafeWindow.fetch !== originalFetch
            };
        }
    }

    // Initialize the model toggle
    const modelToggle = new ModelToggle();

    // Expose debugging functions to global scope
    unsafeWindow.chatgptModelToggle = {
        toggle: () => modelToggle.toggleModel(),
        getStatus: () => modelToggle.getStatus(),
        setModel: (model) => {
            if (CONFIG.models[model]) {
                currentModel = model;
                GM_setValue('current_model', currentModel);
                modelToggle.updateButtonText();
                modelToggle.showNotification(`Switched to ${CONFIG.models[model].fullName}`);
                debugLog('Model set via API', { model });
            } else {
                debugLog('Invalid model specified', { model, availableModels: Object.keys(CONFIG.models) });
            }
        },
        getLogs: () => GM_getValue('debug_logs', []),
        clearLogs: () => {
            GM_setValue('debug_logs', []);
            debugLog('Logs cleared via API');
        }
    };

    debugLog('Script initialization complete', {
        version: '1.0.0',
        currentModel,
        modelsAvailable: Object.keys(CONFIG.models)
    });

})(); 