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
            // If we are on the products page, we need to preserve the filters
            if (window.location.pathname.includes('/products')) {
                event.preventDefault(); // Stop the form from submitting normally

                // Get the new search query
                const newQuery = headerSearchBar.value.trim();

                // Start building the new URL
                const params = new URLSearchParams();
                params.set('q', newQuery);

                // Get existing filters from the filter form
                const filterForm = document.querySelector('.filter-form');
                if (filterForm) {
                    // Get selected shops
                    const shopCheckboxes = filterForm.querySelectorAll('input[name="shops"]:checked');
                    shopCheckboxes.forEach(checkbox => {
                        params.append('shops', checkbox.value);
                    });

                    // Get date range
                    const dateRangeInput = filterForm.querySelector('input[name="date_range"]');
                    if (dateRangeInput) {
                        params.set('date_range', dateRangeInput.value);
                    }

                    // Get category
                    const categorySelect = filterForm.querySelector('select[name="category"]');
                    if (categorySelect) {
                        params.set('category', categorySelect.value);
                    }
                }

                // Show loading overlay
                showLoadingOverlay();

                // Navigate to the new URL
                window.location.href = '/products?' + params.toString();

            } else {
                // For other pages, just handle the submission normally
                handleFormSubmission(event, headerSearchBar);
            }
        });
    }

    // Handle filter form submission on products page
    const filterForm = document.querySelector('.filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(event) {
            handleFormSubmission(event); // No specific input validation needed here as the form has filters
        });
    }

    // Handle toggle "Select All" / "Deselect All" for shop filters
    const toggleShopsBtn = document.getElementById('toggle-shops-btn');
    const shopCheckboxes = document.querySelectorAll('input[name="shops"]');

    function allShopsSelected() {
        return Array.from(shopCheckboxes).every(checkbox => checkbox.checked);
    }

    function updateButtonText() {
        if (allShopsSelected()) {
            toggleShopsBtn.textContent = 'Tümünü Kaldır';
        } else {
            toggleShopsBtn.textContent = 'Tümünü Seç';
        }
    }

    if (toggleShopsBtn) {
        // Set initial button text on page load
        updateButtonText();

        toggleShopsBtn.addEventListener('click', function() {
            const selectAll = !allShopsSelected();
            shopCheckboxes.forEach(function(checkbox) {
                checkbox.checked = selectAll;
            });
            updateButtonText();
        });

        // Also update button text if a user manually changes a checkbox
        shopCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateButtonText);
        });
    }
});
