// ==UserScript==
// @name         ChatGPT Auto "Read Aloud"
// @description  Auto-clicks the Read Aloud (朗读) button after each new assistant answer
// @match        https://chat.openai.com/*
// @match        https://chatgpt.com/*
// @match        https://www.chatgpt.com/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';
  
    // Robust selector for the read-aloud button
    const isReadBtn = (el) =>
      el?.tagName === 'BUTTON' &&
      el.getAttribute('data-testid') === 'voice-play-turn-action-button' &&
      el.getAttribute('aria-label')?.toLowerCase().includes('read aloud');
  
    // Click helper with small safety checks
    const tryClick = (btn) => {
      if (!btn) return;
      const pressed = btn.getAttribute('aria-pressed');
      const state = btn.getAttribute('data-state'); // often "closed" before playing
      // Only click if it's not already playing
      if (pressed === 'false' || state === 'closed') {
        btn.click();
      }
    };
  
    // For each newly rendered assistant message, click ONLY its button (avoid re-clicking old ones)
    const markAndClickLatest = () => {
      // Find all read-aloud buttons currently on the page
      const btns = Array.from(document.querySelectorAll('button[data-testid="voice-play-turn-action-button"]'));
      if (!btns.length) return;
  
      // Heuristic: the last one in DOM order is usually the newest assistant turn
      const newest = btns[btns.length - 1];
  
      // Prevent double-clicking the same message
      if (!newest.dataset._autoVoiceClicked) {
        newest.dataset._autoVoiceClicked = '1';
        tryClick(newest);
      }
    };
  
    // MutationObserver（变动观察器）
    const obs = new MutationObserver((mutations) => {
      let shouldCheck = false;
  
      for (const m of mutations) {
        // If a new button appears, or message content finishes rendering, we re-check
        for (const n of m.addedNodes) {
          if (n.nodeType !== 1) continue;
          if (isReadBtn(n) || n.querySelector?.('button[data-testid="voice-play-turn-action-button"]')) {
            shouldCheck = true;
            break;
          }
        }
        if (shouldCheck) break;
      }
  
      if (shouldCheck) {
        // Give the UI a tick to settle, then click
        setTimeout(markAndClickLatest, 120);
      }
    });
  
    obs.observe(document.body, { childList: true, subtree: true });
  
    // In case the page already has a response visible at load
    setTimeout(markAndClickLatest, 500);
  })();
  