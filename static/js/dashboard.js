/**
 * Javascript functionality for all dashboard types:
 * - Admin Dashboard
 * - Seller Dashboard
 * - Customer Service Dashboard
 * - Moderator Dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    // Tab Navigation
    initTabNavigation();
    
    // Search and Filtering Functionality
    initSearchFunctionality();
    initFilterDropdowns();
    
    // Order Management Functions
    initOrderView();
    initOrderActions();
    
    // Product Management Functions
    initProductActions();
    
    // User Management Functions
    initUserActions();
    
    // Review Management Functions
    initReviewActions();
    
    // Modal Functionality
    initModalControls();
});

/**
 * Initialize tab navigation across all dashboards
 */
function initTabNavigation() {
    const tabLinks = document.querySelectorAll('.nav-link');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);

            tabLinks.forEach(link => link.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('show', 'active'));

            this.classList.add('active');
            document.getElementById(targetId).classList.add('show', 'active');
        });
    });
}

/**
 * Initialize search functionality for all tables
 */
function initSearchFunctionality() {
    // User search
    const userSearch = document.getElementById('user-search');
    if (userSearch) {
        userSearch.addEventListener('input', function() {
            filterTableRows(this.value.toLowerCase(), '.users-table tbody tr');
        });
    }
    
    // Product search
    const productSearch = document.getElementById('product-search');
    if (productSearch) {
        productSearch.addEventListener('input', function() {
            filterTableRows(this.value.toLowerCase(), '.products-table tbody tr');
        });
    }
    
    // Order search
    const orderSearch = document.getElementById('order-search');
    if (orderSearch) {
        orderSearch.addEventListener('input', function() {
            filterTableRows(this.value.toLowerCase(), '.orders-table tbody tr');
        });
    }
    
    // Review search
    const reviewSearch = document.getElementById('review-search');
    if (reviewSearch) {
        reviewSearch.addEventListener('input', function() {
            filterTableRows(this.value.toLowerCase(), '.reviews-table tbody tr');
        });
    }
    
    // Seller search
    const sellerSearch = document.getElementById('seller-search');
    if (sellerSearch) {
        sellerSearch.addEventListener('input', function() {
            filterTableRows(this.value.toLowerCase(), '.sellers-table tbody tr');
        });
    }
}

/**
 * Filter table rows based on search text
 */
function filterTableRows(searchText, selector) {
    const rows = document.querySelectorAll(selector);
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchText) ? '' : 'none';
    });
}

/**
 * Initialize filter dropdowns for all tables
 */
function initFilterDropdowns() {
    // Role filter for user management
    const roleFilter = document.getElementById('role-filter');
    if (roleFilter) {
        roleFilter.addEventListener('change', function() {
            const selectedRole = this.value.toLowerCase();
            const rows = document.querySelectorAll('.users-table tbody tr');
            
            rows.forEach(row => {
                const role = row.querySelector('td:nth-child(6)').textContent.toLowerCase();
                row.style.display = (selectedRole === '' || role === selectedRole) ? '' : 'none';
            });
        });
    }
    
    // Order filter
    const orderFilter = document.getElementById('order-filter');
    if (orderFilter) {
        orderFilter.addEventListener('change', function() {
            const selected = this.value.toLowerCase();
            const tbody = document.querySelector('.orders-table tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            if (selected === 'date') {
                rows.sort((a, b) => {
                    const dateA = new Date(a.querySelector('td:nth-child(4)').textContent.trim());
                    const dateB = new Date(b.querySelector('td:nth-child(4)').textContent.trim());
                    return dateB - dateA; // newest first
                });
            } else if (selected === 'item') {
                rows.sort((a, b) => {
                    const itemA = a.querySelector('td:nth-child(3)').textContent.trim().toLowerCase();
                    const itemB = b.querySelector('td:nth-child(3)').textContent.trim().toLowerCase();
                    return itemA.localeCompare(itemB);
                });
            }

            rows.forEach(row => row.style.display = '');

            if (['fulfilled', 'cancelled', 'pending'].includes(selected)) {
                rows.forEach(row => {
                    const statusCol = row.querySelector('td:nth-child(6)');
                    if (statusCol) {
                        const status = statusCol.textContent.toLowerCase().trim();
                        row.style.display = status.includes(selected) ? '' : 'none';
                    }
                });
            }

            // Re-attach sorted (or filtered) rows
            rows.forEach(row => tbody.appendChild(row));
        });
    }
    
    // Category filter
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            const selectedCategory = this.value.toLowerCase();
            const rows = document.querySelectorAll('.products-table tbody tr');
            
            rows.forEach(row => {
                const category = row.querySelector('td:nth-child(4)').textContent.toLowerCase();
                row.style.display = (selectedCategory === '' || category.includes(selectedCategory)) ? '' : 'none';
            });
        });
    }
    
    // Rating filter
    const ratingFilter = document.getElementById('rating-filter');
    if (ratingFilter) {
        ratingFilter.addEventListener('change', function() {
            const selectedRating = parseInt(this.value);
            const rows = document.querySelectorAll('.reviews-table tbody tr');
            
            rows.forEach(row => {
                const stars = row.querySelectorAll('.fa-solid.fa-star').length;
                row.style.display = (isNaN(selectedRating) || stars === selectedRating) ? '' : 'none';
            });
        });
    }
    
    // Product status filter
    const productStatusFilter = document.getElementById('product-status-filter');
    if (productStatusFilter) {
        productStatusFilter.addEventListener('change', function() {
            const selectedStatus = this.value;
            const rows = document.querySelectorAll('.product-row');
            
            rows.forEach(row => {
                const status = row.getAttribute('data-status');
                row.style.display = (selectedStatus === '' || status === selectedStatus) ? '' : 'none';
            });
        });
    }
    
    // User status filter
    const userStatusFilter = document.getElementById('user-status-filter');
    if (userStatusFilter) {
        userStatusFilter.addEventListener('change', function() {
            const selectedStatus = this.value;
            const rows = document.querySelectorAll('.user-row');
            
            rows.forEach(row => {
                const status = row.getAttribute('data-status');
                row.style.display = (selectedStatus === '' || status === selectedStatus) ? '' : 'none';
            });
        });
    }
}

/**
 * Initialize order view functionality
 */
function initOrderView() {
    const viewOrderButtons = document.querySelectorAll('.view-order-btn');
    if (viewOrderButtons.length === 0) return;

    viewOrderButtons.forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.dataset.orderId;
            const modal = document.getElementById('order-details-modal');
            const content = document.getElementById('order-details-content');
            
            // Get the seller ID if it exists (for Seller Dashboard)
            const sellerId = typeof window.sellerId !== 'undefined' ? window.sellerId : null;

            fetch(`/api/orders/${orderId}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Filter items based on seller ID if provided
                        const items = sellerId 
                            ? data.order.items.filter(item => item.seller_id == sellerId)
                            : data.order.items;
                        
                        // Format the date
                        const createdAt = new Date(data.order.created_at);
                        const formattedDate = createdAt.toLocaleString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                        });

                        content.innerHTML = `
                            <div class="order-details">
                                <h4>Order #${data.order.id}</h4>
                                <p><strong>Username:</strong> ${data.order.username}</p>
                                <p><strong>Customer Name:</strong> ${data.order.full_name}</p>
                                <p><strong>Email:</strong> ${data.order.email}</p>
                                <p><strong>Shipping Address:</strong> ${data.order.shipping_address}</p>
                                <p><strong>Order Date & Time:</strong> ${formattedDate}</p>
                                <br>
                                <h3>${sellerId ? 'Your' : 'All'} Items in This Order:</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background-color: #f4f4f4; text-align: left;">
                                            <th style="padding: 12px; border-bottom: 2px solid #ddd;">Product</th>
                                            <th style="padding: 12px; border-bottom: 2px solid #ddd;">Size</th>
                                            <th style="padding: 12px; border-bottom: 2px solid #ddd;">Quantity</th>
                                            <th style="padding: 12px; border-bottom: 2px solid #ddd;">Price</th>
                                            <th style="padding: 12px; border-bottom: 2px solid #ddd;">Subtotal</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${items.map(item => `
                                            <tr style="border-bottom: 1px solid #eee;">
                                                <td style="padding: 10px;">${item.product_name}</td>
                                                <td style="padding: 10px;">${item.size ? item.size : '-'}</td>
                                                <td style="padding: 10px;">${item.quantity}</td>
                                                <td style="padding: 10px;">$${parseFloat(item.price).toFixed(2)}</td>
                                                <td style="padding: 10px;">$${parseFloat(item.subtotal).toFixed(2)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                                <br>
                                <h4 style="text-align: right;">
                                    Total: $${parseFloat(data.order.total_amount).toFixed(2)}
                                </h4>
                                <p><strong>Order Status:</strong> ${data.order.status_display}</p>
                                <p><strong>Payment Status:</strong> ${data.order.payment_display}</p>
                                <p><strong>Payment Method:</strong> ${data.order.method_display}</p>
                            </div>
                        `;
                    } else {
                        content.innerHTML = '<p>Error loading order details</p>';
                    }
                    modal.style.display = 'block';
                })
                .catch(error => {
                    content.innerHTML = '<p>Error loading order details</p>';
                    modal.style.display = 'block';
                    console.error('Error fetching order details:', error);
                });
        });
    });
}

/**
 * Initialize order action buttons (fulfill, cancel, refund)
 */
function initOrderActions() {
    // Fulfill order
    const fulfillButtons = document.querySelectorAll('.fulfill-order-btn');
    if (fulfillButtons.length > 0) {
        fulfillButtons.forEach(button => {
            button.addEventListener('click', function() {
                const orderId = this.dataset.orderId;
                
                if (confirm('Are you sure you want to fulfill this order?')) {
                    performOrderAction(orderId, 'fulfill-order', 'fulfilled');
                }
            });
        });
    }
    
    // Cancel order
    const cancelButtons = document.querySelectorAll('.cancel-order-btn');
    if (cancelButtons.length > 0) {
        cancelButtons.forEach(button => {
            button.addEventListener('click', function() {
                const orderId = this.dataset.orderId;
                
                if (confirm('Are you sure you want to cancel this order?')) {
                    performOrderAction(orderId, 'cancel-order', 'cancelled');
                }
            });
        });
    }
    
    // Refund order
    const refundButtons = document.querySelectorAll('.refund-order-btn');
    if (refundButtons.length > 0) {
        refundButtons.forEach(button => {
            button.addEventListener('click', function() {
                const orderId = this.dataset.orderId;
                
                if (confirm('Are you sure you want to refund this order?')) {
                    performOrderAction(orderId, 'refund-order', 'refunded');
                }
            });
        });
    }
}

/**
 * Perform an order action (fulfill, cancel, refund)
 */
function performOrderAction(orderId, endpoint, actionType) {
    fetch(`/${endpoint}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `order_id=${orderId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Order ${orderId} is successfully ${actionType}.`, 'success');
            location.reload();
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification(`Error ${actionType} order`, 'error');
        console.error(`Error ${actionType} order:`, error);
    });
}

/**
 * Initialize product actions (update stock, edit, delete, list/unlist)
 */
function initProductActions() {
    // Update stock
    const updateStockButtons = document.querySelectorAll('.update-stock-btn');
    if (updateStockButtons.length > 0) {
        updateStockButtons.forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.dataset.productId;
                const currentStock = this.dataset.currentStock;
                const modal = document.getElementById('update-stock-modal');
                
                if (modal) {
                    document.getElementById('stock-product-id').value = productId;
                    document.getElementById('new-stock').value = currentStock;
                    
                    modal.style.display = 'block';
                }
            });
        });
        
        // Handle stock update form submission
        const updateStockForm = document.getElementById('update-stock-form');
        if (updateStockForm) {
            updateStockForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const productId = document.getElementById('stock-product-id').value;
                const newStock = document.getElementById('new-stock').value;
                
                const updateData = { quantity: newStock };
                
                fetch(`/api/products/${productId}/update/`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(updateData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(`Stock for Product #${productId} has successfully been updated.`, 'success');
                        location.reload();
                    } else {
                        showNotification('Error: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Error updating stock', 'error');
                    console.error('Error updating stock:', error);
                });
            });
        }
    }
    
    // Edit product
    const editProductButtons = document.querySelectorAll('.edit-product-btn');
    if (editProductButtons.length > 0) {
        editProductButtons.forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.dataset.productId;
                if (!productId) {
                    console.error('Product ID not found on edit button');
                    return;
                }
                
                if (typeof window.openProductModal === 'function') {
                    window.openProductModal(true, productId);
                } else if (typeof openProductModal === 'function') {
                    openProductModal(true, productId);
                } else {
                    console.error('openProductModal function not found. Make sure admin-tools.js is loaded properly.');
                    // As a fallback, try to redirect to the product page for editing
                    window.location.href = `/products/${productId}/edit/`;
                }
            });
        });
    }
    
    // Delete product
    const deleteProductButtons = document.querySelectorAll('#delete-product-btn, .delete-product-btn');
    if (deleteProductButtons.length > 0) {
        deleteProductButtons.forEach(button => {
            button.addEventListener('click', function() {
                const productRow = this.closest('tr');
                const productIdCell = productRow.querySelector('td:first-child');
                const productId = this.dataset.productId || (productIdCell ? productIdCell.textContent.trim() : null);
                
                if (!productId) {
                    console.error('Product ID not found');
                    return;
                }
                
                if (confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
                    fetch(`/api/products/${productId}/delete/`, {
                        method: 'DELETE',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showNotification('Product deleted successfully!', 'success');
                            location.reload();
                        } else {
                            showNotification(`Error: ${data.error || 'Failed to delete product'}`, 'error');
                        }
                    })
                    .catch(error => {
                        showNotification('An error occurred during deletion', 'error');
                        console.error('Delete error:', error);
                    });
                }
            });
        });
    }
    
    // Toggle product listing (list/unlist)
    const listUnlistButtons = document.querySelectorAll('.list-product-btn, .unlist-product-btn');
    if (listUnlistButtons.length > 0) {
        listUnlistButtons.forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.dataset.productId;
                
                fetch('/toggle-product-listing/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: `product_id=${productId}`
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(`Product ${data.is_listed ? 'listed' : 'unlisted'} successfully`, 'success');
                        location.reload();
                    } else {
                        showNotification('Error: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Error updating product listing', 'error');
                    console.error('Error updating product listing:', error);
                });
            });
        });
    }
}

/**
 * Initialize user management actions
 */
function initUserActions() {
    // Edit user role
    const editUserButtons = document.querySelectorAll('.edit-user-btn');
    const editUserForm = document.getElementById('edit-user-form');
    
    if (editUserButtons.length > 0 && editUserForm) {
        // Open edit user modal
        editUserButtons.forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.getAttribute('data-user-id');
                const modal = document.getElementById('edit-user-modal');
                
                // Get user data from row
                const row = this.closest('tr');
                const username = row.querySelector('td:nth-child(2)').textContent;
                const role = row.querySelector('td:nth-child(6)').textContent.toLowerCase();
                
                // Populate form
                document.getElementById('user_id').value = userId;
                document.getElementById('username').value = username;
                
                // Set role dropdown value
                const roleSelect = document.getElementById('role');
                for (let i = 0; i < roleSelect.options.length; i++) {
                    if (roleSelect.options[i].textContent.toLowerCase() === role) {
                        roleSelect.selectedIndex = i;
                        break;
                    }
                }
                
                // Show modal
                modal.style.display = 'block';
            });
        });
        
        // Submit role update
        editUserForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const userId = document.getElementById('user_id').value;
            const newRole = document.getElementById('role').value;
            
            fetch('/update-user-role/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: `user_id=${userId}&role=${newRole}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(`User ${userId}'s role is changed to ${newRole}`, 'success');
                    location.reload();
                } else {
                    showNotification('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showNotification('Error updating user role', 'error');
                console.error('Error updating user role:', error);
            });
        });
    }
    
    // Assign seller role
    const assignSellerButtons = document.querySelectorAll('.assign-seller-btn');
    if (assignSellerButtons.length > 0) {
        assignSellerButtons.forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.dataset.userId;
                
                if (confirm('Are you sure you want to assign seller role to this user?')) {
                    fetch('/assign-seller-role/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: `user_id=${userId}`
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showNotification(`User ${userId} is assigned as seller.`, 'success');
                            location.reload();
                        } else {
                            showNotification('Error: ' + data.error, 'error');
                        }
                    })
                    .catch(error => {
                        showNotification('Error assigning seller role', 'error');
                        console.error('Error assigning seller role:', error);
                    });
                }
            });
        });
    }
}

/**
 * Initialize review management actions
 */
function initReviewActions() {
    // Delete review
    const deleteReviewButtons = document.querySelectorAll('.delete-review-btn');
    if (deleteReviewButtons.length > 0) {
        deleteReviewButtons.forEach(button => {
            button.addEventListener('click', function() {
                const reviewId = this.dataset.reviewId;
                
                if (confirm('Are you sure you want to delete this review?')) {
                    fetch('/delete-review-by-moderator/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: `review_id=${reviewId}`
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showNotification('Review deleted successfully', 'success');
                            location.reload();
                        } else {
                            showNotification('Error: ' + data.error, 'error');
                        }
                    })
                    .catch(error => {
                        showNotification('Error deleting review', 'error');
                        console.error('Error deleting review:', error);
                    });
                }
            });
        });
    }
    
    // Ban/unban user from writing reviews
    const banUnbanButtons = document.querySelectorAll('.ban-reviews-btn, .unban-reviews-btn');
    if (banUnbanButtons.length > 0) {
        banUnbanButtons.forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.dataset.userId;
                const action = this.classList.contains('ban-reviews-btn') ? 'ban' : 'unban';
                
                const confirmMessage = `Are you sure you want to ${action} this user from writing reviews?`;
                if (confirm(confirmMessage)) {
                    fetch('/toggle-review-ban/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: `user_id=${userId}`
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showNotification(`User ${action === 'ban' ? 'banned from' : 'allowed to write'} reviews`, 'success');
                            location.reload();
                        } else {
                            showNotification('Error: ' + data.error, 'error');
                        }
                    })
                    .catch(error => {
                        showNotification(`Error ${action}ning user`, 'error');
                        console.error(`Error ${action}ning user:`, error);
                    });
                }
            });
        });
    }
}

/**
 * Initialize modal controls
 */
function initModalControls() {
    // Close modals using close button and cancel button
    document.querySelectorAll('.close-modal, .cancel-btn').forEach(element => {
        element.addEventListener('click', function() {
            // Find and close all modals
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                modal.style.display = 'none';
            });
        });
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

/**
 * Show notification message
 */
function showNotification(message, type = 'success') {
    // Check if notification container exists, if not create it
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '9999';
        document.body.appendChild(notificationContainer);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    // Style notification
    notification.style.backgroundColor = type === 'success' ? '#4CAF50' : '#f44336';
    notification.style.color = 'white';
    notification.style.padding = '16px';
    notification.style.marginBottom = '10px';
    notification.style.borderRadius = '4px';
    notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    notification.style.display = 'flex';
    notification.style.justifyContent = 'space-between';
    notification.style.alignItems = 'center';
    notification.style.minWidth = '300px';
    notification.style.maxWidth = '500px';
    
    // Add close button functionality
    const closeButton = notification.querySelector('.notification-close');
    closeButton.style.backgroundColor = 'transparent';
    closeButton.style.border = 'none';
    closeButton.style.color = 'white';
    closeButton.style.cursor = 'pointer';
    closeButton.style.fontSize = '20px';
    closeButton.style.marginLeft = '10px';
    
    closeButton.addEventListener('click', function() {
        notificationContainer.removeChild(notification);
    });
    
    // Add notification to container
    notificationContainer.appendChild(notification);
    
    // Auto-remove notification after 5 seconds
    setTimeout(function() {
        if (notification.parentNode === notificationContainer) {
            notificationContainer.removeChild(notification);
        }
    }, 5000);
}

/**
 * Get CSRF token from cookies
 */
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

/**
 * Export modal for product editing
 * This function is used by edit product functionality.
 * It's meant to be imported from admin-tools.js if needed.
 */
function openProductModal(isEdit = false, productId = null) {
    // Ensure the product submission modal exists
    const modal = document.getElementById('product-submission-modal');
    if (!modal) {
        console.error('Product submission modal not found!');
        return;
    }
    
    const form = document.getElementById('product-submission-form');
    
    // Clear form fields
    if (form) {
        form.reset();
    }
    
    // Set the modal title based on whether we're adding or editing
    const modalTitle = modal.querySelector('h3');
    if (modalTitle) {
        modalTitle.textContent = isEdit ? 'Edit Product' : 'Add New Product';
    }
    
    if (isEdit && productId) {
        // Fetch product data
        fetch(`/api/products/${productId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Populate form with product data
                    const product = data.product;
                    if (form) {
                        form.elements['name'].value = product.name;
                        form.elements['category'].value = product.category;
                        form.elements['price'].value = product.price;
                        form.elements['rating'].value = product.rating;
                        form.elements['quantity'].value = product.quantity;
                        form.elements['description'].value = product.description;
                        form.elements['features'].value = product.features.join(', ');
                        form.elements['imageName'].value = product.image_name;
                        
                        // Set additional fields if they exist
                        if (product.pokemon && form.elements['pokemon']) {
                            form.elements['pokemon'].value = product.pokemon;
                        }
                        if (product.location && form.elements['location']) {
                            form.elements['location'].value = product.location;
                        }
                    }
                    
                    // Add hidden field for product ID if not already present
                    if (!form.elements['product_id']) {
                        const hiddenField = document.createElement('input');
                        hiddenField.type = 'hidden';
                        hiddenField.name = 'product_id';
                        hiddenField.value = productId;
                        form.appendChild(hiddenField);
                    } else {
                        form.elements['product_id'].value = productId;
                    }
                    
                    // Set form action
                    form.dataset.mode = 'edit';
                    
                    // Show modal
                    modal.style.display = 'block';
                } else {
                    showNotification('Error loading product data: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showNotification('Error loading product data', 'error');
                console.error('Error loading product data:', error);
            });
    } else {
        // Adding new product
        if (form) {
            // Remove product_id field if it exists
            const productIdField = form.elements['product_id'];
            if (productIdField) {
                productIdField.parentNode.removeChild(productIdField);
            }
            
            // Set form action
            form.dataset.mode = 'add';
        }
        
        // Show modal
        modal.style.display = 'block';
    }
}

/**
 * Initialize product submission form
 */
function initProductSubmission() {
    const productSubmissionForm = document.getElementById('product-submission-form');
    const addProductBtn = document.getElementById('add-product-btn');
    
    if (addProductBtn) {
        addProductBtn.addEventListener('click', function() {
            openProductModal(false);
        });
    }
    
    if (productSubmissionForm) {
        productSubmissionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const isEdit = this.dataset.mode === 'edit';
            const endpoint = isEdit ? '/api/products/update/' : '/api/products/add/';
            const method = isEdit ? 'PUT' : 'POST';
            
            fetch(endpoint, {
                method: method,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(`Product ${isEdit ? 'updated' : 'added'} successfully!`, 'success');
                    location.reload();
                } else {
                    showNotification(`Error: ${data.error || `Failed to ${isEdit ? 'update' : 'add'} product`}`, 'error');
                }
            })
            .catch(error => {
                showNotification(`An error occurred while ${isEdit ? 'updating' : 'adding'} the product`, 'error');
                console.error(`Error ${isEdit ? 'updating' : 'adding'} product:`, error);
            });
        });
    }
}

// Make openProductModal available globally
window.openProductModal = openProductModal;

// Initialize product submission if form exists
document.addEventListener('DOMContentLoaded', function() {
    initProductSubmission();
});