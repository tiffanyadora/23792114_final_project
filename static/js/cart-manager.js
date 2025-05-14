// For all cart-related functionality which are loading, adding, update, clearing (checkout)

class CartManager {
    constructor() {
        this.cartItems = [];
        this.cartTotal = 0;
        this.isLoggedIn = document.body.classList.contains('logged-in') || 
            document.querySelectorAll('a[href*="logout"]').length > 0;
        this.loadCart();
        this.setupEventListeners();
    }

    async loadCart() {
        try {
            const response = await fetch('/api/cart/');
            const data = await response.json();
            this.cartItems = data.items;
            this.cartTotal = data.total;
            this.updateCartUI();
        } catch (error) {
            console.error('Error loading cart:', error);
        }
    }

    async addToCart(productId, quantity = 1, size = null) {
        try {
            const response = await fetch('/api/cart/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity,
                    size: size
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.loadCart(); // Refresh cart data
                showNotification('Item added to cart!');
                return true;
            } else {
                showNotification('Error: ' + data.error, 'error');
                return false;
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            showNotification('Error adding to cart', 'error');
            return false;
        }
    }

    async updateCartItem(itemId, quantity) {
        try {
            const response = await fetch(`/api/cart/update/${itemId}/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    quantity: quantity
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.loadCart(); // Refresh cart data
                return true;
            } else {
                showNotification('Error: ' + data.error, 'error');
                return false;
            }
        } catch (error) {
            console.error('Error updating cart item:', error);
            showNotification('Error updating cart', 'error');
            return false;
        }
    }

    async removeFromCart(itemId) {
        try {
            const response = await fetch(`/api/cart/remove/${itemId}/`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            if (data.success) {
                this.loadCart(); // Refresh cart data
                showNotification('Item removed from cart');
                return true;
            } else {
                showNotification('Error: ' + data.error, 'error');
                return false;
            }
        } catch (error) {
            console.error('Error removing from cart:', error);
            showNotification('Error removing item', 'error');
            return false;
        }
    }

    async checkout(customerData) {
        try {
            const response = await fetch('/api/checkout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(customerData)
            });
            
            const data = await response.json();
            if (data.success) {
                this.loadCart(); // Refresh cart
                return {
                    success: true,
                    orderId: data.order_id
                };
            } else {
                showNotification('Error: ' + data.error, 'error');
                return {
                    success: false,
                    error: data.error
                };
            }
        } catch (error) {
            console.error('Error during checkout:', error);
            showNotification('Error processing checkout', 'error');
            return {
                success: false,
                error: 'Network error'
            };
        }
    }

    updateCartUI() {
        // Update cart count in header
        const cartCountElement = document.getElementById('cart-count');
        if (cartCountElement) {
            const itemCount = this.cartItems.reduce((sum, item) => sum + item.quantity, 0);
            cartCountElement.textContent = itemCount;
        }

        // Update cart dropdown or cart page if they exist
        this.updateCartDropdown();
        this.updateCartPage();
        this.updateCheckoutModal();
    }

    updateCartDropdown() {
        const cartDropdown = document.getElementById('cart-dropdown');
        if (!cartDropdown) return;
    
        const cartItemsList = cartDropdown.querySelector('.cart-items');
        const cartTotalElement = cartDropdown.querySelector('.cart-total-amount');
    
        if (cartItemsList) {
            // Clear current items
            cartItemsList.innerHTML = '';
            
            if (this.cartItems.length === 0) {
                cartItemsList.innerHTML = '<li class="empty-cart">Your cart is empty</li>';
                
                // Hide checkout button if cart is empty
                const checkoutBtn = cartDropdown.querySelector('.checkout-btn');
                if (checkoutBtn) {
                    checkoutBtn.style.display = 'none';
                }
            } else {
                // Show checkout button if cart has items
                const checkoutBtn = cartDropdown.querySelector('.checkout-btn');
                if (checkoutBtn) {
                    checkoutBtn.style.display = 'block';
                }
                
                // Add each item to the dropdown
                this.cartItems.forEach(item => {
                    const itemElement = document.createElement('li');
                    itemElement.className = 'cart-item';
                    
                    // Check if we can add more of this item based on stock
                    const canIncreaseQty = item.stock_quantity && item.quantity < item.stock_quantity;
                    
                    itemElement.innerHTML = `
                        <div class="item-info">
                            <span class="item-name">${item.name}</span>
                            <span class="item-price">$${item.price.toFixed(2)}</span>
                            ${item.size ? `<span class="item-size">Size: ${item.size}</span>` : ''}
                        </div>
                        <div class="item-quantity">
                            <button class="quantity-btn cart-minus" data-item-id="${item.id}" ${item.quantity <= 1 ? 'disabled' : ''}>-</button>
                            <span>${item.quantity}</span>
                            <button class="quantity-btn cart-plus" data-item-id="${item.id}" ${!canIncreaseQty ? 'disabled' : ''}>+</button>
                            <button class="remove-item" data-item-id="${item.id}">×</button>
                        </div>
                    `;
                    cartItemsList.appendChild(itemElement);
                    
                    // Add event listeners to quantity buttons
                    const minusBtn = itemElement.querySelector('.cart-minus');
                    const plusBtn = itemElement.querySelector('.cart-plus');
                    const removeBtn = itemElement.querySelector('.remove-item');
                    
                    minusBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const itemId = minusBtn.dataset.itemId;
                        const currentQty = item.quantity;
                        if (currentQty > 1) {
                            this.updateCartItem(itemId, currentQty - 1);
                        }
                    });
                    
                    plusBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const itemId = plusBtn.dataset.itemId;
                        // Only allow increasing if we have enough stock
                        if (item.stock_quantity && item.quantity < item.stock_quantity) {
                            this.updateCartItem(itemId, item.quantity + 1);
                        } else if (item.stock_quantity) {
                            showNotification(`Maximum available quantity is ${item.stock_quantity}`, 'warning');
                        }
                    });
                    
                    removeBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const itemId = removeBtn.dataset.itemId;
                        this.removeFromCart(itemId);
                    });
                });
            }
        }
    
        if (cartTotalElement) {
            cartTotalElement.textContent = `$${this.cartTotal.toFixed(2)}`;
        }
    }

    updateCartPage() {
        const cartPage = document.getElementById('cart-page');
        if (!cartPage) return;
    
        const cartTableBody = document.getElementById('cart-items-table');
        const cartTotalElement = document.getElementById('cart-total');
    
        if (cartTableBody) {
            // Clear current items
            cartTableBody.innerHTML = '';
            
            if (this.cartItems.length === 0) {
                cartTableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="empty-cart">Your cart is empty</td>
                    </tr>
                `;
            } else {
                // Add each item to the table
                this.cartItems.forEach(item => {
                    const row = document.createElement('tr');
                    
                    // Check if we can add more of this item based on stock
                    const canIncreaseQty = item.stock_quantity && item.quantity < item.stock_quantity;
                    
                    row.innerHTML = `
                        <td>
                            <div class="product-info">
                                <img src="/static/images/${item.image}" alt="${item.name}" class="thumbnail">
                                <div>
                                    <h3>${item.name}</h3>
                                    ${item.size ? `<p>Size: ${item.size}</p>` : ''}
                                    ${item.stock_quantity ? `<p class="stock-info">${item.stock_quantity} in stock</p>` : ''}
                                </div>
                            </div>
                        </td>
                        <td>$${item.price.toFixed(2)}</td>
                        <td>
                            <div class="quantity-control">
                                <button class="quantity-btn minus" data-item-id="${item.id}" ${item.quantity <= 1 ? 'disabled' : ''}>-</button>
                                <input type="number" value="${item.quantity}" min="1" ${item.stock_quantity ? `max="${item.stock_quantity}"` : ''} class="quantity-input" data-item-id="${item.id}">
                                <button class="quantity-btn plus" data-item-id="${item.id}" ${!canIncreaseQty ? 'disabled' : ''}>+</button>
                            </div>
                        </td>
                        <td>$${(item.price * item.quantity).toFixed(2)}</td>
                        <td>
                            <button class="remove-item" data-item-id="${item.id}">Remove</button>
                        </td>
                    `;
                    cartTableBody.appendChild(row);
                    
                    // Event listeners for quantity controls
                    const minusBtn = row.querySelector('.minus');
                    const plusBtn = row.querySelector('.plus');
                    const quantityInput = row.querySelector('.quantity-input');
                    const removeBtn = row.querySelector('.remove-item');
                    
                    minusBtn.addEventListener('click', () => {
                        const currentQty = parseInt(quantityInput.value);
                        if (currentQty > 1) {
                            this.updateCartItem(item.id, currentQty - 1);
                        }
                    });
                    
                    plusBtn.addEventListener('click', () => {
                        const currentQty = parseInt(quantityInput.value);
                        // Only allow increasing if we have enough stock
                        if (item.stock_quantity && currentQty < item.stock_quantity) {
                            this.updateCartItem(item.id, currentQty + 1);
                        } else if (item.stock_quantity) {
                            showNotification(`Maximum available quantity is ${item.stock_quantity}`, 'warning');
                        }
                    });
                    
                    quantityInput.addEventListener('change', () => {
                        let newQty = parseInt(quantityInput.value);
                        
                        if (isNaN(newQty) || newQty < 1) {
                            newQty = 1;
                            quantityInput.value = 1;
                        } else if (item.stock_quantity && newQty > item.stock_quantity) {
                            newQty = item.stock_quantity;
                            quantityInput.value = item.stock_quantity;
                            showNotification(`Maximum available quantity is ${item.stock_quantity}`, 'warning');
                        }
                        
                        this.updateCartItem(item.id, newQty);
                    });
                    
                    removeBtn.addEventListener('click', () => {
                        this.removeFromCart(item.id);
                    });
                });
            }
        }
    
        if (cartTotalElement) {
            cartTotalElement.textContent = `$${this.cartTotal.toFixed(2)}`;
        }
    }
    
    updateCheckoutModal() {
        const checkoutModal = document.getElementById('checkout-modal');
        if (!checkoutModal) return;
        
        // Check if user is logged in
        if (!this.isLoggedIn) {
            // Replace content with login prompt
            const modalContent = checkoutModal.querySelector('.modal-content');
            if (modalContent) {
                // Save the original form if we haven't saved it yet
                if (!this._originalCheckoutForm) {
                    this._originalCheckoutForm = modalContent.innerHTML;
                }
                
                modalContent.innerHTML = `
                    <span class="close-modal" id="close-checkout-modal">&times;</span>
                    <h3>Login Required</h3>
                    <div class="login-needed-message">
                        <p>You need to be logged in to complete your purchase.</p>
                        <div class="form-actions">
                            <a href="/login/?next=${encodeURIComponent(window.location.pathname)}" class="btn btn-primary">Login</a>
                            <button type="button" class="btn btn-secondary cancel-btn">Cancel</button>
                        </div>
                    </div>
                `;
                
                // Set up event listeners for the new buttons
                const closeModalBtn = modalContent.querySelector('.close-modal');
                const cancelBtn = modalContent.querySelector('.cancel-btn');
                
                if (closeModalBtn) {
                    closeModalBtn.addEventListener('click', () => this.closeCheckoutModal());
                }
                
                if (cancelBtn) {
                    cancelBtn.addEventListener('click', () => this.closeCheckoutModal());
                }
                
                return;
            }
        } else if (this._originalCheckoutForm) {
            // Restore the original checkout form if we're now logged in
            const modalContent = checkoutModal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.innerHTML = this._originalCheckoutForm;
                this._originalCheckoutForm = null;
                
                // Re-add event listeners to the restored form
                const checkoutForm = document.getElementById('checkout-form');
                const closeModalBtn = modalContent.querySelector('.close-modal');
                const cancelBtn = modalContent.querySelector('.cancel-btn');
                
                if (checkoutForm) {
                    checkoutForm.addEventListener('submit', this.handleCheckoutSubmit.bind(this));
                }
                
                if (closeModalBtn) {
                    closeModalBtn.addEventListener('click', () => this.closeCheckoutModal());
                }
                
                if (cancelBtn) {
                    cancelBtn.addEventListener('click', () => this.closeCheckoutModal());
                }
            }
        }
        
        // Normal checkout modal update
        const orderItems = document.getElementById('order-items');
        const orderTotal = document.getElementById('order-total-amount');
        
        if (!orderItems || !orderTotal) return;
        
        // Clear current items
        orderItems.innerHTML = '';
        
        // Add each item to the order summary
        this.cartItems.forEach(item => {
            const itemElement = document.createElement('li');
            itemElement.className = 'order-item';
            itemElement.innerHTML = `
                <div class="item-details">
                    <span class="item-name">${item.name}</span>
                    ${item.size ? `<span class="item-size">(Size: ${item.size})</span>` : ''}
                    <span class="item-quantity">x${item.quantity}</span>
                </div>
                <span class="item-price">$${(item.price * item.quantity).toFixed(2)}</span>
            `;
            orderItems.appendChild(itemElement);
        });
        
        // Update total amount
        orderTotal.textContent = `$${this.cartTotal.toFixed(2)}`;
    }
    
    setupEventListeners() {
        // Setup checkout button click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('checkout-btn')) {
                e.preventDefault();
                this.openCheckoutModal();
            }
        });
        
        // Setup checkout form submission
        const checkoutForm = document.getElementById('checkout-form');
        if (checkoutForm) {
            checkoutForm.addEventListener('submit', this.handleCheckoutSubmit.bind(this));
        }
        
        // Setup modal close buttons
        const closeModalButtons = document.querySelectorAll('.close-modal, .cancel-btn');
        closeModalButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.closeCheckoutModal();
            });
        });
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            const checkoutModal = document.getElementById('checkout-modal');
            if (checkoutModal && e.target === checkoutModal) {
                this.closeCheckoutModal();
            }
        });
        
        // Add event listener for the custom 'pageContentUpdated' event
        document.addEventListener('pageContentUpdated', () => {
            // Check if login status has changed
            const wasLoggedIn = this.isLoggedIn;
            this.isLoggedIn = document.body.classList.contains('logged-in') || 
                document.querySelectorAll('a[href*="logout"]').length > 0;
                
            // If login status changed, update the checkout modal
            if (wasLoggedIn !== this.isLoggedIn) {
                this.updateCheckoutModal();
            }
        });
    }
    
    handleCheckoutSubmit(e) {
        e.preventDefault();
        
        if (!this.isLoggedIn) {
            // If not logged in, show the login prompt instead
            this.updateCheckoutModal();
            return;
        }
        
        const formData = new FormData(e.target);
        const customerData = {
            full_name: formData.get('full_name'),
            email: formData.get('email'),
            shipping_address: formData.get('shipping_address'),
            payment_method: formData.get('payment_method')
        };
        
        this.checkout(customerData).then(result => {
            if (result.success) {
                this.closeCheckoutModal();
                showNotification(`Order #${result.orderId} placed successfully!`);
                this.loadCart(); // Refresh cart (should be empty now)
            }
        });
    }
    
    openCheckoutModal() {
        const modal = document.getElementById('checkout-modal');
        if (modal) {
            modal.style.display = 'block';
            this.updateCheckoutModal();
        }
    }
    
    closeCheckoutModal() {
        const modal = document.getElementById('checkout-modal');
        if (modal) {
            modal.style.display = 'none';
        }
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

// Initialize cart manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.cartManager = new CartManager();
    
    // Setup cart toggle in header if it exists
    const cartToggle = document.getElementById('cart-toggle');
    const cartDropdown = document.getElementById('cart-dropdown');
    
    if (cartToggle && cartDropdown) {
        cartToggle.addEventListener('click', (e) => {
            e.preventDefault();
            cartDropdown.classList.toggle('show');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!cartToggle.contains(e.target) && !cartDropdown.contains(e.target)) {
                cartDropdown.classList.remove('show');
            }
        });
    }
});