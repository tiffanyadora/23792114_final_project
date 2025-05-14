// Handles all API interactions for the e-commerce site

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a product detail page
    const productId = new URLSearchParams(window.location.search).get('id') || 
                      window.location.pathname.split('/').filter(Boolean).pop();
    
    if (productId && document.querySelector('.product-details')) {
        console.log("Detected product page with ID:", productId);
        loadProductDetails(productId);
    }
});

window.loadProductDetails = function(productId) {
    console.log("Loading product details for ID:", productId);
    
    // First make sure the containers exist
    ensurePokemonContainer();
    ensureWeatherContainer();
    
    // Clear existing containers
    const pokemonContainer = document.getElementById('pokemon-container');
    const weatherContainer = document.getElementById('weather-container');
    
    if (pokemonContainer) {
        pokemonContainer.innerHTML = '<p>Loading Pokémon data...</p>';
    }
    
    if (weatherContainer) {
        weatherContainer.innerHTML = '<p>Loading weather data...</p>';
    }
    
    // Request to fetch the data
    fetch(`/api/products/${productId}/`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Product API response:", data);
            if (data.success && data.product) {
                // Update stock status based on API response quantity
                const productQuantity = data.product.quantity || 0;
                updateStockStatus(productQuantity);

                // If product has Pokemon data from API response, use it directly
                if (data.pokemon) {
                    displayPokemonData(data.pokemon);
                }
                // Otherwise, fetch Pokemon data separately if product has pokemon name
                else if (data.product.pokemon) {
                    fetch(`/api/pokemon/${data.product.pokemon}/`)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Pokemon API error! Status: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(pokemonData => {
                            if (pokemonData.success) {
                                displayPokemonData(pokemonData);
                            } else {
                                handlePokemonError(pokemonData.error || 'Failed to load Pokémon data');
                            }
                        })
                        .catch(error => {
                            console.error("Pokemon fetch error:", error);
                            handlePokemonError('Error loading Pokémon data');
                        });
                } else {
                    handlePokemonError('No Pokémon associated with this product');
                }
                
                // If product has weather data from API response, use it directly  
                if (data.weather) {
                    displayWeatherData(data.weather);
                }
                // Otherwise, fetch weather data separately if product has location
                else if (data.product.location) {
                    fetch(`/api/weather/${data.product.location}/`)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Weather API error! Status: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(weatherData => {
                            if (weatherData.success) {
                                displayWeatherData(weatherData);
                            } else {
                                handleWeatherError(weatherData.error || 'Weather information unavailable');
                            }
                        })
                        .catch(error => {
                            console.error("Weather fetch error:", error);
                            handleWeatherError('Error loading weather data');
                        });
                } else {
                    handleWeatherError('No location data available');
                }
            } else {
                throw new Error('Invalid product data response');
            }
        })
        .catch(error => {
            console.error('Error fetching product details:', error);
            handlePokemonError('Error loading Pokémon data: ' + error.message);
            handleWeatherError('Error loading weather data: ' + error.message);
        });
};

/**
 * Function to update the stock status!
 */

function updateStockStatus(quantity) {
    const stockStatusElement = document.querySelector('.stock-status');
    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    const quantityInput = document.getElementById('quantity');
    
    if (stockStatusElement) {
        if (quantity > 0) {
            stockStatusElement.innerHTML = `<p class="in-stock">In Stock: ${quantity} available</p>`;
            
            // Enable add to cart button
            if (addToCartBtn) {
                addToCartBtn.disabled = false;
                addToCartBtn.innerHTML = '<i class="fa-solid fa-shopping-cart"></i> Add to Cart';
            }
            
            // Set max quantity
            if (quantityInput) {
                quantityInput.setAttribute('max', quantity);
                // If current value exceeds stock, adjust it
                if (parseInt(quantityInput.value) > quantity) {
                    quantityInput.value = quantity;
                }
            }
        } else {
            stockStatusElement.innerHTML = '<p class="out-of-stock">Out of Stock</p>';
            
            // Disable add to cart button
            if (addToCartBtn) {
                addToCartBtn.disabled = true;
                addToCartBtn.innerHTML = 'Out of Stock';
            }
            
            // Disable quantity input
            if (quantityInput) {
                quantityInput.disabled = true;
            }
        }
    }
}

/**
 * Creates or make sure the Pokemon container exists in the DOM!
 */
function ensurePokemonContainer() {
    if (!document.getElementById('pokemon-container')) {
        const container = document.createElement('div');
        container.id = 'pokemon-container';
        container.className = 'pokemon-data mt-4 p-3';
        
        // Insert after product description
        const productDesc = document.querySelector('.product-description');
        productDesc.parentNode.insertBefore(container, productDesc.nextSibling);
    }
}

/**
 * Creates or make sure the Weather container exists in the DOM!
 */
function ensureWeatherContainer() {
    if (!document.getElementById('weather-container')) {
        const container = document.createElement('div');
        container.id = 'weather-container';
        container.className = 'weather-data mt-4 p-3';
        
        // Insert after Pokemon container
        const pokemonContainer = document.getElementById('pokemon-container');
        pokemonContainer.parentNode.insertBefore(container, pokemonContainer.nextSibling);
    }
}

/**
 * Display Pokemon data in the UI!
 * @param {Object} pokemonData - Pokemon data from the API
 */
function displayPokemonData(pokemonData) {
    const container = document.getElementById('pokemon-container');
    if (!pokemonData || !container) return;
    
    // Format types for display
    const types = pokemonData.types ? pokemonData.types.join(', ') : '';
    
    container.innerHTML = `
        <h3 class="mb-3">Product Mascot: ${pokemonData.name}</h3>
        <div class="data-content">
            <div class="pokemon-image">
                ${pokemonData.sprite ? 
                  `<img src="${pokemonData.sprite}" alt="${pokemonData.name}" class="icon-circle">` : 
                  '<div class="pokemon-placeholder">No image available</div>'}
            </div>
            <div class="pokemon-info">
                <p><strong>Type:</strong> ${types || 'Unknown'}</p>
                ${pokemonData.height ? `<p><strong>Height:</strong> ${pokemonData.height / 10}m</p>` : ''}
                ${pokemonData.weight ? `<p><strong>Weight:</strong> ${pokemonData.weight / 10}kg</p>` : ''}
            </div>
        </div>
        <p class="shipping-status mt-3">This product features the ${pokemonData.name} Pokémon as its mascot!</p>
    `;
}

/**
 * Display Weather data in the UI!
 * @param {Object} weatherData - Weather data from the API
 */
function displayWeatherData(weatherData) {
    const container = document.getElementById('weather-container');
    if (!weatherData || !container) return;
    
    // Determine shipping message based on weather conditions
    let shippingMessage = 'Normal shipping times expected.';
    let messageClass = 'text-success';
    
    // Check for severe weather conditions
    const severeConditions = ['Thunderstorm', 'Snow', 'Tornado', 'Hurricane', 'Blizzard'];
    if (severeConditions.includes(weatherData.condition)) {
        shippingMessage = 'Shipping delays possible due to severe weather conditions.';
        messageClass = 'text-danger';
    } else if (weatherData.condition === 'Rain' || weatherData.condition === 'Drizzle') {
        shippingMessage = 'Minor shipping delays possible due to rain.';
        messageClass = 'text-warning';
    }
    
    container.innerHTML = `
        <h3 class="mb-3">Shipping from: ${weatherData.city}</h3>
        <div class="data-content">
            <div class="weather-icon">
                ${weatherData.icon ? 
                  `<img src="https://openweathermap.org/img/wn/${weatherData.icon}@2x.png" alt="${weatherData.condition}" class="icon-circle">` : 
                  '<i class="fa-solid fa-cloud"></i>'}
            </div>
            <div class="weather-info">
                <p><strong>Current Weather:</strong> ${weatherData.description || 'Unknown'}</p>
                <p><strong>Temperature:</strong> ${weatherData.temperature_celsius.toFixed(1)}°C / ${weatherData.temperature_fahrenheit.toFixed(1)}°F</p>
                ${weatherData.humidity ? `<p><strong>Humidity:</strong> ${weatherData.humidity}%</p>` : ''}
                ${weatherData.wind_speed ? `<p><strong>Wind:</strong> ${weatherData.wind_speed} m/s</p>` : ''}
            </div>
        </div>
        <p class="shipping-status ${messageClass} mt-3">${shippingMessage}</p>
    `;
}

/**
 * Handle errors when fetching Pokemon data
 * @param {string} message - Error message to display
 */
function handlePokemonError(message) {
    const container = document.getElementById('pokemon-container');
    if (container) {
        container.innerHTML = `
            <h3 class="mb-3">Product Mascot</h3>
            <div class="error-message">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${message}</p>
            </div>
        `;
    }
}

/**
 * Handle errors when fetching Weather data
 * @param {string} message - Error message to display
 */
function handleWeatherError(message) {
    const container = document.getElementById('weather-container');
    if (container) {
        container.innerHTML = `
            <h3 class="mb-3">Shipping Information</h3>
            <div class="error-message">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${message}</p>
            </div>
            <p class="shipping-status mt-3">Standard shipping times apply.</p>
        `;
    }
}

// Direct API call functions (for front-end use)

// Function to Fetch Pokemon data Directly
function fetchPokemonDirectly(pokemonName, retries = 3, timeout = 5000) {
    return new Promise((resolve, reject) => {
        // Set timeout
        const timeoutId = setTimeout(() => {
            reject(new Error('Request timed out'));
        }, timeout);
        
        // Attempt fetch with retries
        const attemptFetch = (retriesLeft) => {
            fetch(`/api/pokemon/${pokemonName}/`)
                .then(response => {
                    clearTimeout(timeoutId);
                    if (!response.ok) throw new Error('Pokemon API error');
                    return response.json();
                })
                .then(resolve)
                .catch(error => {
                    if (retriesLeft > 0) {
                        console.log(`Retrying Pokemon fetch, ${retriesLeft} attempts left`);
                        setTimeout(() => attemptFetch(retriesLeft - 1), 1000);
                    } else {
                        clearTimeout(timeoutId);
                        reject(error);
                    }
                });
        };
        
        attemptFetch(retries);
    });
}

// Function to Fetch Weather data Directly
function fetchWeatherDirectly(city) {
    return fetch(`/api/weather/${city}/`)
        .then(response => {
            if (!response.ok) throw new Error('Weather API error');
            return response.json();
        });
}