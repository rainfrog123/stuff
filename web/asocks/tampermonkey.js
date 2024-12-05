// ==UserScript==
// @name         Scrape Full Table Data (Filtered by Base Column)
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Scrape full table data filtered by Base column from all pages
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

                // Only save rows where the Base column includes '1205'
                if (base && base.includes('1205')) {
                    extractedData.push({
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



curl -H "Referer: your domain" "https://data.handyapi.com/bin/510805"