// Product review submission, display, editing and deletion with role-based permissions

class ReviewSystem {
    constructor() {
        this.reviewForm = document.getElementById('review-form');
        this.reviewsList = document.getElementById('reviews-list');
        this.productId = this.reviewForm ? this.reviewForm.dataset.productId : null;
        this.isEditing = false;
        this.currentReviewId = null;
        this.originalFormValues = null;
        this.currentUserRole = document.body.dataset.userRole || 'guest'; // Get user role from data attribute
        this.currentUsername = document.body.dataset.username || ''; // Get username from data attribute
        this.canReviewProduct = false; // Track if the user can review this product

        // Initialize when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            if (this.productId) {
                // Check if user can review this product
                this.checkReviewEligibility();
            }
            
            if (this.reviewForm) {
                // Initialize form event listeners
                this.initFormEventListeners();
                
                // Initialize review list event listeners for edit/delete
                this.initReviewListEventListeners();
                
                // Initialize star rating system
                this.initializeRatingStars();
                
                // Add cancel button for edit mode
                this.setupCancelButton();
            }
            
            // Apply role-based permissions to review elements
            this.applyRoleBasedPermissions();
            
            console.log('ReviewSystem initialized');
        });
    }
    
    checkReviewEligibility() {
        // Only check if user is logged in
        if (!this.currentUsername) {
            return;
        }

        // Make API call to check if user can review this product
        fetch(`/api/reviews/can-review/${this.productId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.canReviewProduct = data.can_review;
                    this.updateReviewFormVisibility(data.can_review, data.reason);
                }
            })
            .catch(error => {
                console.error('Error checking review eligibility:', error);
            });
    }
    
    updateReviewFormVisibility(canReview, reason) {
        if (!this.reviewForm) return;
        
        const addReviewSection = this.reviewForm.closest('.add-review');
        if (!addReviewSection) return;
        
        if (!canReview) {
            // Hide form and show message
            addReviewSection.style.display = 'none';
            
            const messageElement = document.createElement('div');
            messageElement.className = 'review-eligibility-notice';
            messageElement.innerHTML = `<p>${reason || 'You cannot review this product.'}</p>`;
            
            // Insert the message after the review form
            addReviewSection.parentNode.insertBefore(messageElement, addReviewSection.nextSibling);
        } else {
            // Ensure the form is visible
            addReviewSection.style.display = 'block';
            
            // Remove any existing notice
            const existingNotice = addReviewSection.parentNode.querySelector('.review-eligibility-notice');
            if (existingNotice) {
                existingNotice.remove();
            }
        }
    }

    applyRoleBasedPermissions() {
        // Show/hide review form based on permissions
        if (this.reviewForm) {
            // Check if user is logged in
            const isAuthenticated = this.currentUsername !== '';
            
            // Check if user is review banned
            const isReviewBanned = document.body.dataset.isReviewBanned === 'true';
            
            if (!isAuthenticated) {
                // Hide form and show login prompt
                this.reviewForm.closest('.add-review').style.display = 'none';
                const loginPrompt = document.createElement('div');
                loginPrompt.className = 'login-prompt';
                loginPrompt.innerHTML = '<p>Please <a href="/login/?next=' + window.location.pathname + '">login</a> to write a review.</p>';
                this.reviewForm.closest('.add-review').parentNode.appendChild(loginPrompt);
            } else if (isReviewBanned) {
                // Hide form and show banned message
                this.reviewForm.closest('.add-review').style.display = 'none';
                const bannedMessage = document.createElement('div');
                bannedMessage.className = 'review-ban-notice';
                bannedMessage.innerHTML = '<p>You are currently not able to write reviews due to violations of our review policy.</p>';
                this.reviewForm.closest('.add-review').parentNode.appendChild(bannedMessage);
            }
            // Note: If user is authenticated and not banned, the form visibility will be controlled by checkReviewEligibility
        }
        
        // Apply permissions to review items
        if (this.reviewsList) {
            const reviewItems = this.reviewsList.querySelectorAll('.review');
            reviewItems.forEach(review => {
                const reviewUsername = review.querySelector('.review-header h4').textContent;
                const actionsDiv = review.querySelector('.review-actions');
                
                if (actionsDiv) {
                    const editBtn = actionsDiv.querySelector('.edit-review-btn');
                    const deleteBtn = actionsDiv.querySelector('.delete-review-btn');
                    
                    // Users can only edit their own reviews
                    if (editBtn) {
                        if (reviewUsername !== this.currentUsername) {
                            editBtn.style.display = 'none';
                        }
                    }
                    
                    // Users can delete their own reviews, admins and moderators can delete any review
                    if (deleteBtn) {
                        if (reviewUsername !== this.currentUsername && !['admin', 'moderator'].includes(this.currentUserRole)) {
                            deleteBtn.style.display = 'none';
                        }
                    }
                }
            });
        }
    }

    initFormEventListeners() {
        // Handle review form submit
        this.reviewForm.addEventListener('submit', (e) => {
            e.preventDefault();
            console.log('Form submit triggered');
            
            // Check if user can review this product before submitting
            if (!this.canReviewProduct && this.currentUserRole !== 'admin' && !this.isEditing) {
                showNotification('You can only review products you have purchased', 'error');
                return;
            }
            
            if (this.isEditing) {
                this.submitEditReview();
            } else {
                this.submitNewReview();
            }
        });
    }

    initReviewListEventListeners() {
        // Handle edit and delete buttons on existing reviews
        if (this.reviewsList) {
            this.reviewsList.addEventListener('click', (e) => {
                // Edit button clicked
                if (e.target.classList.contains('edit-review-btn') || 
                    e.target.closest('.edit-review-btn')) {
                    const reviewElement = e.target.closest('.review');
                    const reviewId = reviewElement.dataset.reviewId;
                    this.startEditingReview(reviewId, reviewElement);
                }
                
                // Delete button clicked
                if (e.target.classList.contains('delete-review-btn') || 
                    e.target.closest('.delete-review-btn')) {
                    const reviewElement = e.target.closest('.review');
                    const reviewId = reviewElement.dataset.reviewId;
                    this.confirmDeleteReview(reviewId, reviewElement);
                }
            });
        }
    }

    setupCancelButton() {
        const submitBtn = this.reviewForm.querySelector('button[type="submit"]');
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-secondary cancel-edit-btn';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.style.display = 'none';
        cancelBtn.addEventListener('click', () => this.cancelEditing());
        submitBtn.parentNode.insertBefore(cancelBtn, submitBtn);
    }

    initializeRatingStars() {
        const ratingInputs = document.querySelectorAll('.rating-input input');
        const ratingLabels = document.querySelectorAll('.rating-input label');
        
        // Add hover effects to rating stars
        ratingLabels.forEach((label, index) => {
            label.addEventListener('mouseenter', () => {
                // Highlight current star and all stars before it
                for (let i = 0; i <= index; i++) {
                    ratingLabels[i].classList.add('hover');
                }
            });
            
            label.addEventListener('mouseleave', () => {
                // Remove hover effect when mouse leaves
                ratingLabels.forEach(label => label.classList.remove('hover'));
            });
        });
        
        // Add click handler to rating inputs
        ratingInputs.forEach((input, index) => {
            input.addEventListener('change', () => {
                // Reset all selected stars
                ratingLabels.forEach(label => label.classList.remove('selected'));
                
                // Highlight stars up to the selected one
                for (let i = 0; i <= index; i++) {
                    ratingLabels[4-i].classList.add('selected');
                }
            });
        });
    }

    submitNewReview() {
        // Ensure user is logged in
        if (!this.currentUsername) {
            showNotification('You must be logged in to write a review', 'error');
            return;
        }

        // check for review eligibility
        if (!this.canReviewProduct && this.currentUserRole !== 'admin') {
            showNotification('You can only review products you have purchased', 'error');
            return;
        }
        
        const formData = new FormData(this.reviewForm);
        const username = formData.get('username').trim();
        const rating = formData.get('rating');
        const comment = formData.get('comment').trim();
        
        // Validate form data
        if (!username || !rating || !comment) {
            showNotification('Please fill out all fields', 'error');
            return;
        }
        
        // Prepare data for API
        const data = {
            product_id: this.productId,
            username: username,
            rating: rating,
            comment: comment
        };
        
        // Submit review to API
        fetch('/api/reviews/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Error submitting review');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Add the new review to the list
                this.addReviewToList(data.review);
                // Reset form
                this.reviewForm.reset();
                // Reset star rating visual
                document.querySelectorAll('.rating-input label').forEach(label => {
                    label.classList.remove('selected');
                });
                // Remove "no reviews" message if it exists
                const noReviews = this.reviewsList.querySelector('.no-reviews');
                if (noReviews) {
                    noReviews.remove();
                }
                showNotification('Review added successfully!', 'success');
            } else {
                console.error('Error submitting review:', data.error);
                showNotification('Error: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error: ' + error.message, 'error');
        });
    }
    
    startEditingReview(reviewId, reviewElement) {
        // Ensure user has permission to edit this review
        const reviewUsername = reviewElement.querySelector('.review-header h4').textContent;
        if (reviewUsername !== this.currentUsername && !['admin'].includes(this.currentUserRole)) {
            showNotification('You do not have permission to edit this review', 'error');
            return;
        }
        
        // Store review ID being edited
        this.currentReviewId = reviewId;
        this.isEditing = true;

        // Get review data from the review element
        const username = reviewElement.querySelector('.review-header h4').textContent;
        const rating = reviewElement.querySelectorAll('.rating .fa-star').length || 
                      reviewElement.querySelector('.rating').textContent.split('★').length - 1;
        const comment = reviewElement.querySelector('.review-content p').textContent;

        // Store original form values to revert back if canceled
        this.storeOriginalFormValues();

        // Update form with review data
        const usernameInput = document.getElementById('username');
        const commentInput = document.getElementById('review-text') || document.getElementById('comment');
        const ratingInputs = document.querySelectorAll('.rating-input input');

        usernameInput.value = username;
        commentInput.value = comment;
        
        // Set the correct rating star
        for (let i = 0; i < ratingInputs.length; i++) {
            if (ratingInputs[i].value == rating) {
                ratingInputs[i].checked = true;
                break;
            }
        }

        // Update form appearance for edit mode
        this.updateFormForEditMode(true);

        // Scroll to form
        this.reviewForm.scrollIntoView({ behavior: 'smooth' });
    }

    storeOriginalFormValues() {
        const usernameInput = document.getElementById('username');
        const commentInput = document.getElementById('review-text') || document.getElementById('comment');
        const ratingInput = document.querySelector('.rating-input input:checked');

        this.originalFormValues = {
            username: usernameInput.value,
            comment: commentInput.value,
            rating: ratingInput ? ratingInput.value : null
        };
    }

    updateFormForEditMode(isEditing) {
        const submitBtn = this.reviewForm.querySelector('button[type="submit"]');
        const cancelBtn = this.reviewForm.querySelector('.cancel-edit-btn');
        const formTitle = this.reviewForm.closest('.add-review').querySelector('h3');

        if (isEditing) {
            submitBtn.textContent = 'Update Review';
            cancelBtn.style.display = 'inline-block';
            if (formTitle) formTitle.textContent = 'Edit Your Review';
            
            // Lock username field during edit mode (as it's determined by the server)
            const usernameInput = document.getElementById('username');
            usernameInput.setAttribute('readonly', 'readonly');
        } else {
            submitBtn.textContent = 'Submit Review';
            cancelBtn.style.display = 'none';
            if (formTitle) formTitle.textContent = 'Write a Review';
            
            // Update username field based on login status
            const usernameInput = document.getElementById('username');
            if (this.currentUsername) {
                usernameInput.value = this.currentUsername;
                usernameInput.setAttribute('readonly', 'readonly');
            } else {
                usernameInput.removeAttribute('readonly');
            }
        }
    }

    cancelEditing() {
        // Reset form to original values
        if (this.originalFormValues) {
            const usernameInput = document.getElementById('username');
            const commentInput = document.getElementById('review-text') || document.getElementById('comment');
            const ratingInputs = document.querySelectorAll('.rating-input input');

            usernameInput.value = this.originalFormValues.username;
            commentInput.value = this.originalFormValues.comment;
            
            if (this.originalFormValues.rating) {
                for (let i = 0; i < ratingInputs.length; i++) {
                    ratingInputs[i].checked = ratingInputs[i].value === this.originalFormValues.rating;
                }
            } else {
                // Clear all ratings
                ratingInputs.forEach(input => input.checked = false);
            }
        }

        // Reset edit mode
        this.isEditing = false;
        this.currentReviewId = null;
        this.originalFormValues = null;
        this.updateFormForEditMode(false);
    }

    submitEditReview() {
        const username = document.getElementById('username').value.trim();
        const commentInput = document.getElementById('review-text') || document.getElementById('comment');
        const comment = commentInput.value.trim();
        const ratingInput = document.querySelector('.rating-input input:checked');
        const rating = ratingInput ? ratingInput.value : null;
        const reviewId = this.currentReviewId;

        // Validate form
        if (!username || !comment || !rating) {
            showNotification('Please fill out all fields', 'error');
            return;
        }

        // Prepare data for API
        const data = {
            username: username, // Will be ignored server-side but included for compatibility
            comment: comment,
            rating: rating
        };

        // Send update to API
        fetch(`/api/reviews/${reviewId}/update/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Error updating review');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update the review in the UI
                this.updateReviewInUI(reviewId, data.review);
                // Reset form
                this.cancelEditing();
                // Reset form values
                this.reviewForm.reset();
                // Update username field with current user
                if (this.currentUsername) {
                    document.getElementById('username').value = this.currentUsername;
                }
                showNotification('Review updated successfully!', 'success');
            } else {
                console.error('Error updating review:', data.error);
                showNotification('Error: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error: ' + error.message, 'error');
        });
    }

    updateReviewInUI(reviewId, reviewData) {
        const reviewElement = document.querySelector(`.review[data-review-id="${reviewId}"]`);
        if (reviewElement) {

            const usernameElement = reviewElement.querySelector('.review-header h4');
            if (usernameElement) {
                usernameElement.textContent = reviewData.username;
            }

            // Update the rating stars
            const ratingElement = reviewElement.querySelector('.rating');
            if (ratingElement) {
                let starsHTML = '';
                for (let i = 1; i <= 5; i++) {
                    if (i <= reviewData.rating) {
                        starsHTML += '★';
                    } else {
                        starsHTML += '☆';
                    }
                }
                ratingElement.innerHTML = starsHTML;
            }

            // Update the review text
            const commentElement = reviewElement.querySelector('.review-content p');
            if (commentElement) {
                commentElement.textContent = reviewData.comment;
            }
        }
        
        // Update product rating if provided
        const productRating = document.querySelector('.product-rating');
        if (productRating && reviewData.product_rating) {
            this.updateProductRating(productRating, reviewData.product_rating);
        }
    }

    confirmDeleteReview(reviewId, reviewElement) {
        // Check permission to delete this review
        const reviewUsername = reviewElement.querySelector('.review-header h4').textContent;
        const canDelete = reviewUsername === this.currentUsername || ['admin', 'moderator'].includes(this.currentUserRole);
        
        if (!canDelete) {
            showNotification('You do not have permission to delete this review', 'error');
            return;
        }
        
        if (confirm('Are you sure you want to delete this review?')) {
            this.deleteReview(reviewId, reviewUsername);
        }
    }

    deleteReview(reviewId, username) {
        // Send delete request to API
        fetch(`/api/reviews/${reviewId}/delete/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ username: username })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Error deleting review');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Remove the review from the UI
                const reviewElement = document.querySelector(`.review[data-review-id="${reviewId}"]`);
                if (reviewElement) {
                    reviewElement.remove();
                    
                    // Check if there are no more reviews and add the "no reviews" message if needed
                    if (this.reviewsList.querySelectorAll('.review').length === 0) {
                        const noReviewsElement = document.createElement('div');
                        noReviewsElement.className = 'no-reviews';
                        noReviewsElement.innerHTML = '<p>This product hasn\'t been reviewed yet. Be the first to write a review!</p>';
                        this.reviewsList.appendChild(noReviewsElement);
                    }
                }
                showNotification('Review deleted successfully!', 'success');
            } else {
                console.error('Error deleting review:', data.error);
                showNotification('Error: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error: ' + error.message, 'error');
        });
    }
    
    addReviewToList(review) {
        // Create new review element
        const reviewElement = document.createElement('div');
        reviewElement.className = 'review';
        reviewElement.dataset.reviewId = review.id;
        
        // Format date
        const date = new Date(review.created_at);
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        
        // Generate stars HTML
        let starsHTML = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= review.rating) {
                starsHTML += '★';
            } else {
                starsHTML += '☆';
            }
        }
        
        // Determine if we should show edit/delete buttons based on permissions
        const isAuthor = review.username === this.currentUsername;
        const isAdmin = this.currentUserRole === 'admin';
        const isModerator = this.currentUserRole === 'moderator';
        
        const showEditBtn = isAuthor || isAdmin;
        const showDeleteBtn = isAuthor || isAdmin || isModerator;
        
        // Set review HTML
        reviewElement.innerHTML = `
            <div class="review-header">
                <h4>${review.username}</h4>
                <div class="rating">${starsHTML}</div>
                <span class="review-date">${dateStr}</span>
                ${(showEditBtn || showDeleteBtn) ? `
                <div class="review-actions">
                    ${showEditBtn ? `
                    <button class="edit-review-btn" title="Edit review">
                        <i class="fa-solid fa-edit"></i>
                    </button>
                    ` : ''}
                    ${showDeleteBtn ? `
                    <button class="delete-review-btn" title="Delete review">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                    ` : ''}
                </div>
                ` : ''}
            </div>
            <div class="review-content">
                <p>${review.comment}</p>
            </div>
        `;
        
        // Add to the top of the reviews list
        this.reviewsList.insertBefore(reviewElement, this.reviewsList.firstChild);
        
        // Update average rating if displayed
        if (review.product_rating) {
            const productRating = document.querySelector('.product-rating');
            if (productRating) {
                this.updateProductRating(productRating, review.product_rating);
            }
        }
    }
    
    updateProductRating(productRatingElement, newRating) {
        // Clear existing stars
        const existingStars = productRatingElement.querySelectorAll('i');
        existingStars.forEach(star => star.remove());
        
        // Get the rating span element
        const ratingSpan = productRatingElement.querySelector('span');
        
        // Generate new stars
        const fullStars = Math.floor(newRating);
        const hasHalfStar = newRating % 1 >= 0.5;
        
        // Add full stars
        for (let i = 0; i < fullStars; i++) {
            const starIcon = document.createElement('i');
            starIcon.className = 'fa-solid fa-star';
            productRatingElement.insertBefore(starIcon, ratingSpan);
        }
        
        // Add half star if needed
        if (hasHalfStar) {
            const halfStarIcon = document.createElement('i');
            halfStarIcon.className = 'fa-solid fa-star-half-alt';
            productRatingElement.insertBefore(halfStarIcon, ratingSpan);
        }
        
        // Update rating text
        if (ratingSpan) {
            ratingSpan.textContent = newRating.toFixed(1);
        }
    }
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize the Review System
const reviewSystem = new ReviewSystem();