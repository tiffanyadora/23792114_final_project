// Product Searching Feature

document.addEventListener('DOMContentLoaded', function() {
    // Initialize search elements
    const searchForm = document.querySelector('form[action*="search"]');
    const searchInput = document.querySelector('input[name="query"]');
    const filtersContainer = document.getElementById('search-filters');
    const resultsContainer = document.getElementById('search-results');
    const suggestionsContainer = document.getElementById('search-suggestions');
    const recentSearchesContainer = document.getElementById('recent-search-buttons');
    const productSort = document.getElementById('product-sort');
    
    // Sorting Options for dropdown
    if (productSort) {
        // Name filter (Ascending and Descending)
        const nameAscOption = document.createElement('option');
        nameAscOption.value = 'name-asc';
        nameAscOption.textContent = 'Name: A to Z';
        
        const nameDescOption = document.createElement('option');
        nameDescOption.value = 'name-desc';
        nameDescOption.textContent = 'Name: Z to A';
        
        productSort.appendChild(nameAscOption);
        productSort.appendChild(nameDescOption);
    }
    
    // Recent searches functionality
    function loadRecentSearches() {
        let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        
        // Display last 3 recent searches
        if (recentSearchesContainer) {
            recentSearchesContainer.innerHTML = '';
            
            // Take last 3 searches (most recent first)
            const lastThreeSearches = recentSearches.slice(-3).reverse();
            
            lastThreeSearches.forEach(query => {
                const searchButton = document.createElement('button');
                searchButton.className = 'recent-search-btn mx-1 py-1 px-2';
                searchButton.textContent = query;
                searchButton.addEventListener('click', function() {
                    // Redirect to search with this query
                    window.location.href = `/search/?query=${encodeURIComponent(query)}`;
                });
                
                recentSearchesContainer.appendChild(searchButton);
            });
            
            // Show or hide recent searches section based on whether there are any
            const recentSearchesSection = document.getElementById('recent-searches-section');
            if (recentSearchesSection) {
                recentSearchesSection.style.display = lastThreeSearches.length > 0 ? 'flex' : 'none';
            }
        }
        
        // Fill search input with most recent search if it exists
        if (searchInput && recentSearches.length > 0) {
            const mostRecentSearch = recentSearches[recentSearches.length - 1];
            searchInput.value = mostRecentSearch;
            
            // Also fill mobile search if it exists
            const mobileSearchInput = document.querySelector('.mobile-search-input');
            if (mobileSearchInput) {
                mobileSearchInput.value = mostRecentSearch;
            }
        }
    }
    
    function saveRecentSearch(query) {
        // Don't save empty queries
        if (!query) return;
        
        let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        
        // Remove this query if it already exists (to avoid duplicates)
        recentSearches = recentSearches.filter(item => item !== query);
        
        // Add the new query
        recentSearches.push(query);
        
        // Keep only the last 10 searches
        if (recentSearches.length > 10) {
            recentSearches = recentSearches.slice(-10);
        }
        
        localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    }
    
    // Load recent searches when page loads
    loadRecentSearches();
    
    // Save the current search query if one exists
    const urlParams = new URLSearchParams(window.location.search);
    const currentQuery = urlParams.get('query');
    if (currentQuery) {
        saveRecentSearch(currentQuery);
    }
    
    // Live search functionality
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            // Only perform search if query is at least 2 characters
            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    performLiveSearch(query);
                }, 300);
            } else if (resultsContainer) {
                // Clear results if query is too short
                resultsContainer.innerHTML = '';
                if (suggestionsContainer) {
                    suggestionsContainer.innerHTML = '';
                    suggestionsContainer.classList.add('hidden');
                }
            }
        });
    }
    
    // Handle form submission to save search
    if (searchForm) {
        searchForm.addEventListener('submit', function(event) {
            const query = searchInput.value.trim();
            if (query) {
                saveRecentSearch(query);
            }
        });
        
        // Also handle mobile search form
        const mobileSearchForm = document.querySelector('.mobile-search-expanded');
        if (mobileSearchForm) {
            mobileSearchForm.addEventListener('submit', function(event) {
                const mobileQuery = document.querySelector('.mobile-search-input').value.trim();
                if (mobileQuery) {
                    saveRecentSearch(mobileQuery);
                }
            });
        }
    }
    
    // Search filters handling
    if (filtersContainer) {
        // Category filter
        const categorySelect = filtersContainer.querySelector('select[name="category"]');
        if (categorySelect) {
            categorySelect.addEventListener('change', function() {
                if (searchForm) {
                    searchForm.dispatchEvent(new Event('submit'));
                }
            });
        }
        
        // Price range filters
        const minPriceInput = filtersContainer.querySelector('input[name="min_price"]');
        const maxPriceInput = filtersContainer.querySelector('input[name="max_price"]');
        
        if (minPriceInput && maxPriceInput) {
            [minPriceInput, maxPriceInput].forEach(input => {
                input.addEventListener('change', function() {
                    if (searchForm) {
                        searchForm.dispatchEvent(new Event('submit'));
                    }
                });
            });
        }
        
        // Rating filter
        const ratingSelect = filtersContainer.querySelector('select[name="min_rating"]');
        if (ratingSelect) {
            ratingSelect.addEventListener('change', function() {
                if (searchForm) {
                    searchForm.dispatchEvent(new Event('submit'));
                }
            });
        }
    }
    
    // Perform live search with filters
    function performLiveSearch(query) {
        // Get filter values
        let filters = {};
        
        if (filtersContainer) {
            const categorySelect = filtersContainer.querySelector('select[name="category"]');
            if (categorySelect && categorySelect.value) {
                filters.category = categorySelect.value;
            }
            
            const minPriceInput = filtersContainer.querySelector('input[name="min_price"]');
            if (minPriceInput && minPriceInput.value) {
                filters.min_price = minPriceInput.value;
            }
            
            const maxPriceInput = filtersContainer.querySelector('input[name="max_price"]');
            if (maxPriceInput && maxPriceInput.value) {
                filters.max_price = maxPriceInput.value;
            }
            
            const ratingSelect = filtersContainer.querySelector('select[name="min_rating"]');
            if (ratingSelect && ratingSelect.value) {
                filters.min_rating = ratingSelect.value;
            }
        }
        
        // Build query string
        let queryString = `query=${encodeURIComponent(query)}`;
        
        for (const [key, value] of Object.entries(filters)) {
            queryString += `&${key}=${encodeURIComponent(value)}`;
        }
        
        // Fetch search results
        fetch(`/api/search?${queryString}`)
            .then(response => response.json())
            .then(data => {
                if (resultsContainer) {
                    if (data.results.length > 0) {
                        displaySearchResults(data.results);
                    } else {
                        resultsContainer.innerHTML = '<p>No products found</p>';
                        
                        // Show suggestions if available
                        if (data.suggestions && data.suggestions.length > 0 && suggestionsContainer) {
                            displaySearchSuggestions(data.suggestions);
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error performing search:', error);
                if (resultsContainer) {
                    resultsContainer.innerHTML = '<p>Error performing search</p>';
                }
            });
    }
    
    // Display search results
    function displaySearchResults(results) {
        if (!resultsContainer) return;
        
        resultsContainer.innerHTML = '';
        
        // Create product cards
        results.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';
            
            const productLink = document.createElement('a');
            productLink.href = `/product?id=${product.id}`;
            
            // Product image
            const imageDiv = document.createElement('div');
            imageDiv.className = 'product-image';
            const img = document.createElement('img');
            img.src = `/static/images/${product.image}`;
            img.alt = product.name;
            imageDiv.appendChild(img);
            
            // Product info
            const infoDiv = document.createElement('div');
            infoDiv.className = 'product-info p-3';
            
            const title = document.createElement('h3');
            title.className = 'mb-1';
            title.textContent = product.name;
            
            const price = document.createElement('p');
            price.className = 'product-price';
            price.textContent = `$${product.price.toFixed(2)}`;
            
            const rating = document.createElement('div');
            rating.className = 'product-rating d-flex align-center mb-1';
            
            // Generate stars
            for (let i = 0; i < Math.floor(product.rating); i++) {
                const star = document.createElement('i');
                star.className = 'fa-solid fa-star';
                rating.appendChild(star);
            }
            
            // Add half star if needed
            if (product.rating % 1 >= 0.5) {
                const halfStar = document.createElement('i');
                halfStar.className = 'fa-solid fa-star-half-alt';
                rating.appendChild(halfStar);
            }
            
            const ratingText = document.createElement('span');
            ratingText.className = 'ml-1';
            ratingText.textContent = product.rating.toFixed(1);
            rating.appendChild(ratingText);
            
            // Assemble the card
            infoDiv.appendChild(title);
            infoDiv.appendChild(price);
            infoDiv.appendChild(rating);
            
            productLink.appendChild(imageDiv);
            productLink.appendChild(infoDiv);
            
            productCard.appendChild(productLink);
            resultsContainer.appendChild(productCard);
        });
    }
    
    // Display search suggestions
    function displaySearchSuggestions(suggestions) {
        if (!suggestionsContainer) return;
        
        suggestionsContainer.innerHTML = '';
        suggestionsContainer.classList.remove('hidden');
        
        const heading = document.createElement('h3');
        heading.textContent = 'Did you mean:';
        suggestionsContainer.appendChild(heading);
        
        const suggestionsList = document.createElement('ul');
        suggestionsList.className = 'suggestions-list';
        
        suggestions.forEach(product => {
            const listItem = document.createElement('li');
            
            const link = document.createElement('a');
            link.href = `/product?id=${product.id}`;
            link.textContent = product.name;
            
            listItem.appendChild(link);
            suggestionsList.appendChild(listItem);
        });
        
        suggestionsContainer.appendChild(suggestionsList);
    }
});