// Product CRUD operations and reviews

class ProductAPI {
  static async addProduct(productData) {
      try {
          console.log('Sending product data:', productData); // Debug log
          const response = await fetch('/api/products/add/', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify(productData)
          });
          
          return await response.json();
      } catch (error) {
          console.error('Error adding product:', error);
          return { success: false, error: 'Network error' };
      }
  }

  static async updateProduct(productId, productData) {
      try {
          console.log('Updating product data:', productData); // Debug log
          const response = await fetch(`/api/products/${productId}/update/`, {
              method: 'PUT',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify(productData)
          });
          
          return await response.json();
      } catch (error) {
          console.error('Error updating product:', error);
          return { success: false, error: 'Network error' };
      }
  }

  static async deleteProduct(productId) {
      try {
          const response = await fetch(`/api/products/${productId}/delete/`, {
              method: 'DELETE'
          });
          
          return await response.json();
      } catch (error) {
          console.error('Error deleting product:', error);
          return { success: false, error: 'Network error' };
      }
  }

    static async addReview(reviewData) {
        try {
            const response = await fetch('/api/reviews/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(reviewData)
            });
            
            return await response.json();
        } catch (error) {
            console.error('Error adding review:', error);
            return { success: false, error: 'Network error' };
        }
    }

  static async fetchPokemonData(pokemonName) {
      try {
          const response = await fetch(`/api/pokemon/${pokemonName.toLowerCase()}/`);
          return await response.json();
      } catch (error) {
          console.error('Error fetching Pokemon data:', error);
          return null;
      }
  }

  static async fetchWeatherData(cityName) {
      try {
          const response = await fetch(`/api/weather/${encodeURIComponent(cityName)}/`);
          return await response.json();
      } catch (error) {
          console.error('Error fetching weather data:', error);
          return null;
      }
  }
}

// Product Form Handler
class ProductFormHandler {
    constructor(formId, isEditMode = false) {
        this.form = document.getElementById(formId);
        this.isEditMode = isEditMode;
        
        if (this.form) {
            this.setupForm();
        }
    }
    
    setupForm() {
        if (this.form.hasAttribute('data-handler-initialized')) {
            return; // Skip if already initialized
        }
        this.form.setAttribute('data-handler-initialized', 'true');
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = this.getFormData();
            let result;
            
            if (this.isEditMode) {
                const productId = this.form.dataset.productId;
                result = await ProductAPI.updateProduct(productId, formData);
            } else {
                result = await ProductAPI.addProduct(formData);
            }
            
            if (result.success) {
                showNotification(this.isEditMode ? 'Product updated successfully!' : 'Product added successfully!');
                if (!this.isEditMode && result.product_id) {
                    window.location.href = `/products/${result.product_id}/`;
                }
            } else {
                showNotification(`Error: ${result.error}`, 'error');
            }
        });
    }
    
    getFormData() {
        const quantityInput = this.form.querySelector('[name="quantity"]');
        const quantityValue = quantityInput ? parseInt(quantityInput.value) : 0;
        const imageName = this.form.querySelector('[name="imageName"]') ? 
                      this.form.querySelector('[name="imageName"]').value : 
                      'default.jpg';
        
        // For debugging - log the quantity
        console.log('Quantity value:', quantityValue, 'Input field:', quantityInput);
        
        return {
            name: this.form.querySelector('[name="name"]').value,
            description: this.form.querySelector('[name="description"]').value,
            features: this.form.querySelector('[name="features"]').value,
            price: parseFloat(this.form.querySelector('[name="price"]').value),
            rating: parseFloat(this.form.querySelector('[name="rating"]').value || 0),
            category: this.form.querySelector('[name="category"]').value,
            pokemon: this.form.querySelector('[name="pokemon"]')?.value || '',
            location: this.form.querySelector('[name="location"]')?.value || '',
            imageName: imageName,
            quantity: quantityValue // Using the extracted quantity
        };
    }
  }

// Review Form Handler
class ReviewFormHandler {
    constructor(formId) {
        this.form = document.getElementById(formId);
        
        if (this.form) {
            this.setupForm();
        }
    }
    
    setupForm() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Validate form
            if (!this.validateForm()) {
                return;
            }
            
            const formData = this.getFormData();
            const result = await ProductAPI.addReview(formData);
            
            if (result.success) {
                showNotification('Review added successfully!');
                // Add the new review to the page without reloading
                this.addReviewToPage(result.review);
                // Reset the form
                this.form.reset();
                // Reset star rating visual
                document.querySelectorAll('.rating-input label').forEach(label => {
                    label.classList.remove('selected');
                });
            } else {
                showNotification(`Error: ${result.error}`, 'error');
            }
        });
    }
    
    validateForm() {
        const username = this.form.querySelector('[name="username"]').value.trim();
        const rating = this.form.querySelector('[name="rating"]:checked');
        const comment = this.form.querySelector('[name="comment"]').value.trim();
        
        if (!username) {
            showNotification('Please enter your name', 'error');
            return false;
        }
        
        if (!rating) {
            showNotification('Please select a rating', 'error');
            return false;
        }
        
        if (!comment) {
            showNotification('Please enter a review comment', 'error');
            return false;
        }
        
        return true;
    }
    
    getFormData() {
        return {
            product_id: this.form.dataset.productId,
            username: this.form.querySelector('[name="username"]').value.trim(),
            rating: parseInt(this.form.querySelector('[name="rating"]:checked').value),
            comment: this.form.querySelector('[name="comment"]').value.trim()
        };
    }
    
    addReviewToPage(review) {
        const reviewsList = document.getElementById('reviews-list');
        if (!reviewsList) return;
        
        // If there's a "no reviews" message, remove it
        const noReviews = reviewsList.querySelector('.no-reviews');
        if (noReviews) {
            noReviews.remove();
        }
        
        // Create the review element
        const reviewElement = document.createElement('div');
        reviewElement.className = 'review';
        
        // Format date nicely
        const date = new Date(review.created_at || new Date());
        const formattedDate = date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
        
        reviewElement.innerHTML = `
            <div class="review-header">
                <h4>${review.username}</h4>
                <div class="rating">
                    ${this.generateStars(review.rating)}
                </div>
                <span class="review-date">${formattedDate}</span>
            </div>
            <div class="review-content">
                <p>${review.comment}</p>
            </div>
        `;
        
        // Add the new review at the top of the list
        reviewsList.prepend(reviewElement);
        
        // Update average rating if displayed
        const productRating = document.querySelector('.product-rating');
        if (productRating && review.product_avg_rating) {
            productRating.innerHTML = this.generateProductRating(review.product_avg_rating);
        }
    }
    
    generateStars(rating) {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            stars += i <= rating ? '★' : '☆';
        }
        return stars;
    }
    
    generateProductRating(rating) {
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        
        let html = '';
        
        // Add full stars
        for (let i = 0; i < fullStars; i++) {
            html += '<i class="fa-solid fa-star"></i>';
        }
        
        // Add half star if needed
        if (hasHalfStar) {
            html += '<i class="fa-solid fa-star-half-alt"></i>';
        }
        
        // Add empty stars
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        for (let i = 0; i < emptyStars; i++) {
            html += '<i class="fa-regular fa-star"></i>';
        }
        
        html += `<span class="ml-2">${rating.toFixed(1)}</span>`;
        
        return html;
    }
}

function showNotification(message, type = 'success') {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
      notification.classList.add('show');
  }, 10);
  
  setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => {
          notification.remove();
      }, 300);
  }, 3000);
}

// Initialize forms when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Check for product forms
  if (document.getElementById('add-product-form')) {
      new ProductFormHandler('add-product-form');
  }
  
  if (document.getElementById('edit-product-form')) {
      new ProductFormHandler('edit-product-form', true);
  }
  
  // Setup product deletion
  const deleteProductBtn = document.getElementById('delete-product-btn');
  if (deleteProductBtn) {
      deleteProductBtn.addEventListener('click', async (e) => {
          e.preventDefault();
          
          if (confirm('Are you sure you want to delete this product?')) {
              const productId = deleteProductBtn.dataset.productId;
              const result = await ProductAPI.deleteProduct(productId);
              
              if (result.success) {
                  showNotification('Product deleted successfully!');
                  window.location.href = '/';
              } else {
                  showNotification(`Error: ${result.error}`, 'error');
              }
          }
      });
  }
});