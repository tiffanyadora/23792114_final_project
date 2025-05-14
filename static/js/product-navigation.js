// For navigation within the website's pages

let currentPageContent = '';
let isHomePage = true;

// Create a custom event that will be dispatched after navigation or page load
const pageContentUpdatedEvent = new Event('pageContentUpdated');

document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM fully loaded - setting up navigation');
  
  // Save the initial page content
  currentPageContent = document.body.innerHTML;
  
  // Determine if we're on the home page or product detail page
  isHomePage = window.location.pathname === '/' || window.location.pathname === '/index.html';
  console.log('Is home page:', isHomePage);
  
  // Add event listeners to product cards for dynamic navigation
  setupProductNavigation();
  console.log('Navigation setup complete');
  
  // Initialize all required systems on initial page load
  initializeAllSystems();
  
  // Add event listener to logo for returning to home
  const logo = document.querySelector('.logo-container');
  if (logo) {
    logo.addEventListener('click', function(e) {
      e.preventDefault();
      if (!isHomePage) {
        navigateToHome();
      }
    });
  }
  
  // Listen for browser back/forward navigation
  window.addEventListener('popstate', handlePopState);
});

// Initialize all JavaScript systems
function initializeAllSystems() {
  console.log('Initializing all systems');
  
  // Cart functionality
  if (typeof window.cartManager !== 'undefined') {
    if (window.cartManager.loadCart) {
      window.cartManager.loadCart();
    }
  }
  
  // Initialize review system
  if (typeof initializeCommentSystem === 'function') {
    initializeCommentSystem();
  }
  
  // Initialize like system
  if (typeof initializeLikeSystem === 'function') {
    initializeLikeSystem();
  }
  
  // Initialize search functionality
  setupSearch();
  
  // Load product details if on a product page
  const productDetailContainer = document.querySelector('.product-details');
  if (productDetailContainer) {
    const productId = productDetailContainer.dataset.productId;
    if (productId && typeof window.loadProductDetails === 'function') {
      window.loadProductDetails(productId);
    }
  }
  
  // Set up admin tools if present
  if (document.getElementById('add-product-btn')) {
    setupAdminTools();
  }
  
  // Set up sorting if present
  if (document.getElementById('product-sort')) {
    setupSorting();
  }

  // Dispatch custom event to notify other scripts that page content has been updated
  document.dispatchEvent(pageContentUpdatedEvent);
}

// Setup product navigation for all product cards
function setupProductNavigation() {
  // Get all product cards on the page
  const productCards = document.querySelectorAll('.product-card, .suggestion-card');
  console.log(`Found ${productCards.length} product cards to attach events to`);
  
  // Add click event to each product card
  productCards.forEach(card => {
    card.addEventListener('click', function(e) {
      e.preventDefault();
      console.log('Product card clicked:', this);
      
      // Get product ID from data attribute or href
      let productId = this.getAttribute('data-product-id');
      console.log('Data product ID:', productId);
      
      if (!productId) {
        // Try to extract from href
        const href = this.getAttribute('href');
        console.log('Href attribute:', href);
        
        if (href) {
          // Check for /products/123/ pattern
          const matches = href.match(/\/products\/(\d+)\//);
          console.log('URL pattern matches:', matches);
          
          if (matches && matches[1]) {
            productId = matches[1];
          } else {
            // Try query params
            const urlParams = new URLSearchParams(href.split('?')[1] || '');
            productId = urlParams.get('product_id') || urlParams.get('id');
          }
        }
      }
      
      console.log('Final product ID:', productId);
      
      if (productId) {
        navigateToProduct(productId);
      } else {
        console.error('Could not determine product ID from element:', this);
      }
    });
  });
}

// Function to set up search functionality
function setupSearch() {
  const searchForm = document.querySelector('form[action*="search"]');
  const searchInput = document.querySelector('input[name="query"]');
  
  if (searchForm && searchInput) {
    loadRecentSearches();
  }
}

// Function to set up admin tools
function setupAdminTools() {
  const addProductBtn = document.getElementById('add-product-btn');
  if (addProductBtn) {
    addProductBtn.addEventListener('click', function(e) {
      e.preventDefault();
      openProductModal(false);
    });
  }
}

// Function to set up sorting
function setupSorting() {
  const sortSelect = document.getElementById('product-sort');
  const productContainer = document.querySelector('.product-flex');
  
  if (sortSelect && productContainer) {
    sortSelect.addEventListener('change', function() {
      const sortValue = this.value;
      if (!sortValue) return;
      
      const products = Array.from(productContainer.querySelectorAll('.product-card'));
      
      products.sort((a, b) => {
        // For price sorting
        if (sortValue.startsWith('price')) {
          const priceA = parseFloat(a.querySelector('.product-price').textContent.replace('$', ''));
          const priceB = parseFloat(b.querySelector('.product-price').textContent.replace('$', ''));
          
          return sortValue === 'price-asc' ? priceA - priceB : priceB - priceA;
        }
        
        // For rating sorting
        else if (sortValue.startsWith('rating')) {
          const ratingA = parseFloat(a.querySelector('.product-rating span').textContent);
          const ratingB = parseFloat(b.querySelector('.product-rating span').textContent);
          
          return sortValue === 'rating-asc' ? ratingA - ratingB : ratingB - ratingA;
        }
        
        // For name sorting
        else if (sortValue.startsWith('name')) {
          const nameA = a.querySelector('h3').textContent.toLowerCase();
          const nameB = b.querySelector('h3').textContent.toLowerCase();
          
          if (sortValue === 'name-asc') {
            return nameA.localeCompare(nameB);
          } else {
            return nameB.localeCompare(nameA);
          }
        }
        
        return 0;
      });
      
      // Clear container and append sorted products
      productContainer.innerHTML = '';
      products.forEach(product => productContainer.appendChild(product));
    });
  }
}

// Navigate to product detail page
function navigateToProduct(productId) {
  console.log("Navigating to product:", productId);
  
  // Make sure productId is properly formatted
  productId = productId.toString().trim();
  
  // Use the correct URL format
  const url = `/products/${productId}/`;
  console.log("Fetching URL:", url);
  
  // Direct browser navigation
  window.location.href = url;
}

// Handle browser back/forward navigation
function handlePopState(event) {
  console.log('PopState event triggered', event.state);
  
  // Delay the check slightly to ensure the browser has updated the URL
  setTimeout(() => {
    // Check if we're now on the home page
    isHomePage = window.location.pathname === '/' || window.location.pathname === '/index.html';
    
    // If we're on the home page, initialize systems
    if (isHomePage) {
      console.log('Popstate to home page, initializing systems');
      initializeAllSystems();
    }
    // If we're on a product page
    else if (window.location.pathname.includes('/products/')) {
      console.log('Popstate to product page');
      
      // Extract product ID from URL
      const pathSegments = window.location.pathname.split('/').filter(Boolean);
      if (pathSegments.length >= 2 && pathSegments[0] === 'products') {
        const productId = pathSegments[1];
        if (productId && typeof window.loadProductDetails === 'function') {
          console.log('Loading product details for ID:', productId);
          window.loadProductDetails(productId);
        }
      }
      
      // Initialize all systems for product page
      initializeAllSystems();
    }
  }, 100);
}

// Navigate back to home page
function navigateToHome() {
  console.log("Navigating to home");
  
  // Direct navigation is more reliable
  window.location.href = '/';
  
  // If you want to use AJAX navigation in the future, you can uncomment and modify this code:
  /*
  fetch('/')
    .then(response => response.text())
    .then(html => {
      // Update page content
      document.body.innerHTML = html;
      
      // Update browser URL without reloading
      history.pushState({}, '', '/');
      
      // Update page state
      isHomePage = true;
      
      // Initialize all systems
      initializeAllSystems();
    })
    .catch(error => {
      console.error('Error navigating to home:', error);
      // Fallback to traditional navigation if fetch fails
      window.location.href = '/';
    });
  */
}

// Load recent searches for search functionality
function loadRecentSearches() {
  let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
  const recentSearchesContainer = document.getElementById('recent-search-buttons');
  
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
}