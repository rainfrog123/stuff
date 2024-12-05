// ==UserScript==
// @name         Scrape BIN, Expiry, and Price (Filtered by Base Column)
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Scrape BIN, Expiry, and Price columns filtered by Base column from all pages
// @author       You
// @match        https://bclub.tk/cvv/?page=*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const maxPages = 30; // Total number of pages to scrape
    const extractedData = JSON.parse(localStorage.getItem('scrapedData')) || []; // Restore previous data

    // Get the current page from the URL
    let currentPage = parseInt(new URL(window.location.href).searchParams.get('page')) || 1;

    function scrapeData() {
        // Select the table body containing the rows (use the ID 'itemsBody')
        const tableBody = document.querySelector('#itemsBody');

        if (tableBody) {
            const rows = tableBody.querySelectorAll('tr'); // Get all rows in the table body

            rows.forEach(row => {
                // Get the BIN column (2nd column)
                const binCell = row.querySelector('td:nth-child(2)');
                const binValue = binCell ? binCell.textContent.trim() : null;

                // Get the Expiry column (5th column)
                const expiryCell = row.querySelector('td:nth-child(5)');
                const expiryValue = expiryCell ? expiryCell.textContent.trim() : null;

                // Get the Price column (14th column)
                const priceCell = row.querySelector('td:nth-child(14)');
                const priceValue = priceCell ? priceCell.textContent.trim() : null;

                // Get the Base column (13th column)
                const baseCell = row.querySelector('td:nth-child(13)');
                const baseValue = baseCell ? baseCell.textContent.trim() : null;

                // Only save rows where the Base column includes '1205'
                if (baseValue && baseValue.includes('1205')) {
                    extractedData.push({
                        BIN: binValue,
                        Expiry: expiryValue,
                        Price: priceValue,
                        Base: baseValue
                    });
                }
            });

            // Save extracted data to localStorage
            localStorage.setItem('scrapedData', JSON.stringify(extractedData));

            console.log(`Page ${currentPage}: Scraped Data`, extractedData);
        } else {
            console.warn(`Table body with ID "itemsBody" not found on page ${currentPage}!`);
        }
    }

    function goToNextPage() {
        if (currentPage < maxPages) {
            const nextPageUrl = `https://bclub.tk/cvv/?page=${currentPage + 1}`;
            console.log(`Navigating to: ${nextPageUrl}`);
            window.location.href = nextPageUrl; // Navigate to the next page
        } else {
            // All pages scraped
            console.log('Scraping complete. Final data:', extractedData);

            // (Optional) Save data as JSON file
            const blob = new Blob([JSON.stringify(extractedData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'scraped_data.json';
            a.click();
            URL.revokeObjectURL(url);

            console.log('Data saved to "scraped_data.json".');

            // Clear localStorage after saving the file
            localStorage.removeItem('scrapedData');
        }
    }

    // Wait for the page to load, scrape data, and navigate to the next page
    window.addEventListener('load', () => {
        scrapeData(); // Scrape current page

        // Save the next page number to localStorage
        localStorage.setItem('currentPage', currentPage);

        // Navigate to the next page after a delay
        setTimeout(goToNextPage, 3000);
    });
})();
