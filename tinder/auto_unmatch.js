// ==UserScript==
// @name         Tinder Auto Unmatcher
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Automatically unmatches Tinder connections
// @author       You
// @match        https://tinder.com/app/recs
// @match        https://tinder.com/app/matches
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    function clickElement(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.click();
        }
    }

    function testTest1111() {
        clickElement(".D\\(f\\):nth-child(1) > .P\\(8px\\):nth-child(1) .Bgc\\(\\$c-ds-background-primary\\) > .D\\(b\\)");
        clickElement(".l17p5q9z");
        clickElement(".My\\(12px\\) .l17p5q9z");
    }

    // Run the test every 100 milliseconds
    setInterval(testTest1111, 100);

    // Auto-refresh the page every 1 minutes (adjust the interval as needed)
    setInterval(function() {
        window.location.href = 'https://tinder.com/app/recs';
    }, 60000); // 600,000 milliseconds = 1 minutes

})();
