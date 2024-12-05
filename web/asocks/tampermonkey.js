// ==UserScript==
// @name         Scrape BIN Column
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Scrape BIN column data from a table
// @author       You
// @match       https://bclub.tk/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    // Wait for the page to load
    window.addEventListener('load', () => {
        // Select the table body containing the rows (use the ID 'itemsBody')
        const tableBody = document.querySelector('#itemsBody');

        if (tableBody) {
            const rows = tableBody.querySelectorAll('tr'); // Get all rows in the table body
            const extractedData = []; // Array to store the extracted data

            rows.forEach(row => {
                // Get the BIN column (second column in each row)
                const binCell = row.querySelector('td:nth-child(2)');
                const binValue = binCell ? binCell.textContent.trim() : null;

                // Get the Expiry column (fifth column in each row)
                const expiryCell = row.querySelector('td:nth-child(5)');
                const expiryValue = expiryCell ? expiryCell.textContent.trim() : null;

                // Get the Price column (14th column in each row)
                const priceCell = row.querySelector('td:nth-child(14)');
                const priceValue = priceCell ? priceCell.textContent.trim() : null;

                if (binValue || expiryValue || priceValue) {
                    extractedData.push({
                        BIN: binValue,
                        Expiry: expiryValue,
                        Price: priceValue
                    });
                }
            });

            // Log the extracted data to the console
            console.log('Extracted Data:', extractedData);

            // (Optional) Send the extracted data to a server or save as a file
            // Example: Sending to server
            // fetch('https://your-server.com/api', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ extractedData }),
            // });
        } else {
            console.warn('Table body with ID "itemsBody" not found!');
        }
    });
})();