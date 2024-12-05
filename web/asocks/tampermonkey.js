// ==UserScript==
// @name         Scrape Full Table Data with Position Tracking
// @namespace    http://tampermonkey.net/
// @version      1.6
// @description  Scrape full table data based on dynamically determined base column value and stop on mismatch, with position tracking
// @author       You
// @match        https://bclub.tk/cvv/?page=*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const extractedData = JSON.parse(localStorage.getItem('scrapedData')) || []; // Restore previous data
    let baseName = localStorage.getItem('baseName'); // Retrieve base name from localStorage
    let currentPage = parseInt(new URL(window.location.href).searchParams.get('page')) || 1;

    function scrapeData() {
        const tableBody = document.querySelector('#itemsBody'); // Get table body

        if (tableBody) {
            const rows = tableBody.querySelectorAll('tr'); // Get all rows in the table body

            // Dynamically set the base name from the first row on the first page
            if (!baseName && currentPage === 1 && rows.length > 0) {
                const firstBaseCell = rows[0].querySelector('td:nth-child(13)');
                if (firstBaseCell) {
                    baseName = firstBaseCell.textContent.trim();
                    localStorage.setItem('baseName', baseName); // Save to localStorage for subsequent pages
                    console.log(`Base Name Determined: ${baseName}`);
                }
            }

            let hasMatchingData = false; // Flag to track if matching data is found on this page

            rows.forEach((row, rowIndex) => {
                // Extract all columns
                const bin = row.querySelector('td:nth-child(2)')?.textContent.trim();
                const type = row.querySelector('td:nth-child(3)')?.querySelector('img')?.getAttribute('title') || 'N/A';
                const subtype = row.querySelector('td:nth-child(4)')?.textContent.trim();
                const expiry = row.querySelector('td:nth-child(5)')?.textContent.trim();
                const name = row.querySelector('td:nth-child(6)')?.textContent.trim();
                const country = row.querySelector('td:nth-child(7)')?.querySelector('img')?.getAttribute('title') || 'N/A';
                const state = row.querySelector('td:nth-child(8)')?.textContent.trim();
                const fullAddress = row.querySelector('td:nth-child(9)')?.textContent.trim();
                const zip = row.querySelector('td:nth-child(10)')?.textContent.trim();
                const extra = row.querySelector('td:nth-child(11)')?.textContent.trim();
                const bank = row.querySelector('td:nth-child(12)')?.textContent.trim();
                const base = row.querySelector('td:nth-child(13)')?.textContent.trim();
                const price = row.querySelector('td:nth-child(14)')?.textContent.trim();

                // Only save rows where the Base column matches the determined baseName
                if (base && base === baseName) {
                    extractedData.push({
                        Page: currentPage,
                        Row: rowIndex + 1, // Add 1 because rowIndex is zero-based
                        Bin: bin,
                        Type: type,
                        Subtype: subtype,
                        Expiry: expiry,
                        Name: name,
                        Country: country,
                        State: state,
                        FullAddress: fullAddress,
                        Zip: zip,
                        Extra: extra,
                        Bank: bank,
                        Base: base,
                        Price: price
                    });
                    hasMatchingData = true; // At least one matching row found
                }
            });

            // Save extracted data to localStorage
            localStorage.setItem('scrapedData', JSON.stringify(extractedData));

            console.log(`Page ${currentPage}: Scraped Data`, extractedData);

            // If no matching data is found, stop scraping
            if (!hasMatchingData) {
                console.log('No matching data found. Stopping scraping.');
                saveAndStop();
            }
        } else {
            console.warn(`Table body with ID "itemsBody" not found on page ${currentPage}!`);
        }
    }

    function goToNextPage() {
        const nextPage = currentPage + 1; // Increment the page number
        const nextPageUrl = `https://bclub.tk/cvv/?page=${nextPage}`;
        console.log(`Navigating to: ${nextPageUrl}`);
        window.location.href = nextPageUrl; // Navigate to the next page
    }

    function saveAndStop() {
        // Save final data to JSON file
        const blob = new Blob([JSON.stringify(extractedData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'scraped_data_with_positions.json';
        a.click();
        URL.revokeObjectURL(url);

        console.log('Data saved to "scraped_data_with_positions.json".');

        // Clear localStorage
        localStorage.removeItem('scrapedData');
        localStorage.removeItem('baseName');
    }

    // Wait for the page to load, scrape data, and navigate to the next page
    window.addEventListener('load', () => {
        scrapeData(); // Scrape current page

        if (localStorage.getItem('baseName')) {
            // If base name is set and no stopping condition, continue to the next page
            setTimeout(() => {
                goToNextPage();
            }, 3000); // Wait 3 seconds before navigating to the next page
        }
    });
})();
