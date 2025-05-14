// Product Sorting Feature

document.addEventListener('DOMContentLoaded', function() {
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
});