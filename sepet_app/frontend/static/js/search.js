document.addEventListener('DOMContentLoaded', function() {
    const loadingOverlay = document.getElementById('loading-overlay');

    function showLoadingOverlay() {
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
    }

    function hideLoadingOverlay() {
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }

    // Hide loading overlay if the page has fully loaded (e.g., after a redirect or initial load)
    // This is important for cases where the back button might be used or if the page loads very quickly
    window.addEventListener('load', hideLoadingOverlay);

    function handleFormSubmission(event, inputElement = null) {
        let proceed = true;
        if (inputElement && inputElement.value.trim() === '') {
            proceed = false;
        }

        if (proceed) {
            showLoadingOverlay();
        } else {
            event.preventDefault(); // Prevent submission if validation fails
        }
    }

    // Handle header search form submission
    const headerSearchForm = document.querySelector('.header-search-form');
    const headerSearchBar = headerSearchForm ? headerSearchForm.querySelector('.shared-search-bar') : null;
    if (headerSearchForm) {
        headerSearchForm.addEventListener('submit', function(event) {
            handleFormSubmission(event, headerSearchBar);
        });
    }

    // Handle filter form submission on products page
    const filterForm = document.querySelector('.filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(event) {
            handleFormSubmission(event); // No specific input validation needed here as the form has filters
        });
    }
});
