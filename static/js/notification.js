// For site-wide notifications and alerts

document.addEventListener('DOMContentLoaded', function() {
    // Initialize displayed notifications tracking if it doesn't exist
    if (!localStorage.getItem('displayedNotifications')) {
        localStorage.setItem('displayedNotifications', JSON.stringify([]));
    }
    
    // Check for notifications in session storage (for page redirects)
    const sessionNotification = sessionStorage.getItem('notification');
    if (sessionNotification) {
        try {
            const notification = JSON.parse(sessionNotification);
            showNotification(notification.message, notification.type);
            sessionStorage.removeItem('notification');
        } catch (e) {
            console.error('Error parsing notification:', e);
        }
    }
    
    // Function to show notification
    window.showNotification = function(message, type = 'success') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        // Create notification content
        const content = document.createElement('div');
        content.className = 'notification-content';
        
        // icon based on type
        let icon;
        switch (type) {
            case 'success':
                icon = '<i class="fa-solid fa-circle-check"></i>';
                break;
            case 'error':
                icon = '<i class="fa-solid fa-circle-exclamation"></i>';
                break;
            case 'warning':
                icon = '<i class="fa-solid fa-triangle-exclamation"></i>';
                break;
            case 'info':
                icon = '<i class="fa-solid fa-circle-info"></i>';
                break;
            default:
                icon = '<i class="fa-solid fa-bell"></i>';
        }
        
        content.innerHTML = `${icon}<p style="color: black;">${message}</p>`;
        
        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'notification-close';
        closeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        closeBtn.addEventListener('click', function() {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        
        // Assemble notification
        notification.appendChild(content);
        notification.appendChild(closeBtn);
        
        // Add to document
        document.body.appendChild(notification);
        
        // Show notification after a brief delay (for transition effect)
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);
    };
    
    // Check for notifications from server
    function checkNotifications() {
        // Get already displayed notification IDs from localStorage
        let displayedNotifications = JSON.parse(localStorage.getItem('displayedNotifications') || '[]');
        
        // Fetch notifications from endpoint
        fetch('/api/notifications/check/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update notification counter
                    updateNotificationCounter(data.unread_count);
                    
                    // Display only new notifications that haven't been shown before
                    if (data.notifications.length > 0) {
                        // Filter to only show notifications that haven't been displayed yet
                        const newNotifications = data.notifications.filter(
                            notification => !displayedNotifications.includes(notification.id)
                        );
                        
                        // Show toast notifications for new ones
                        newNotifications.forEach(notification => {
                            showNotification(notification.message, notification.type);
                            // Add to displayed list
                            displayedNotifications.push(notification.id);
                        });
                        
                        // Save updated list to localStorage
                        if (newNotifications.length > 0) {
                            localStorage.setItem('displayedNotifications', JSON.stringify(displayedNotifications));
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error checking notifications:', error);
            });
    }
    
    // Mark notification as read
    function markNotificationRead(notificationId) {
        fetch(`/api/notifications/${notificationId}/mark-read/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update notification counter
                updateNotificationCounter(data.unread_count);
                
                // Update displayed notifications tracking
                let displayedNotifications = JSON.parse(localStorage.getItem('displayedNotifications') || '[]');
                
                // Add this notification ID to displayed list if not already there
                if (!displayedNotifications.includes(parseInt(notificationId))) {
                    displayedNotifications.push(parseInt(notificationId));
                    localStorage.setItem('displayedNotifications', JSON.stringify(displayedNotifications));
                }
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }
    
    // Update notification counter in header
    function updateNotificationCounter(count) {
        const notificationBadge = document.getElementById('notification-badge');
        if (notificationBadge) {
            if (count > 0) {
                notificationBadge.textContent = count > 99 ? '99+' : count;
                notificationBadge.classList.add('show');
            } else {
                notificationBadge.classList.remove('show');
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
    
    // Check for notifications on page load (if user is logged in)
    const alertIcon = document.getElementById('alert-icon');
    if (alertIcon) {
        // Display notification modal when clicking the bell icon
        alertIcon.addEventListener('click', function(e) {
            e.preventDefault();
            
            const dropdown = document.getElementById('notifications-dropdown');
            if (dropdown) {
                dropdown.classList.toggle('show');
                
                // Load notifications into dropdown
                loadNotifications();
            }
        });
        
        // Initial notification check
        checkNotifications();
        
        // Check periodically (every 30 seconds)
        setInterval(checkNotifications, 30000);
    }
    
    // Load notifications for dropdown
    function loadNotifications() {
        const dropdown = document.getElementById('notifications-dropdown');
        if (!dropdown) return;
        
        const notificationsList = dropdown.querySelector('.notifications-list');
        if (notificationsList) {
            // Show loading spinner
            notificationsList.innerHTML = '<div class="notifications-loading"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading notifications...</p></div>';
            
            // Fetch notifications from endpoint
            fetch('/api/notifications/')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update list with notifications
                        if (data.notifications.length > 0) {
                            // Build notifications HTML
                            let notificationsHTML = '';
                            
                            data.notifications.forEach(notification => {
                                // Format date
                                const date = new Date(notification.created_at);
                                const formattedDate = date.toLocaleDateString('en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    year: 'numeric',
                                    hour: 'numeric',
                                    minute: 'numeric'
                                });
                                
                                // Get appropriate icon based on type
                                let icon;
                                switch (notification.type) {
                                    case 'success':
                                        icon = '<i class="fa-solid fa-circle-check"></i>';
                                        break;
                                    case 'error':
                                        icon = '<i class="fa-solid fa-circle-exclamation"></i>';
                                        break;
                                    case 'warning':
                                        icon = '<i class="fa-solid fa-triangle-exclamation"></i>';
                                        break;
                                    case 'info':
                                        icon = '<i class="fa-solid fa-circle-info"></i>';
                                        break;
                                    default:
                                        icon = '<i class="fa-solid fa-bell"></i>';
                                }
                                
                                // Build notification item
                                notificationsHTML += `
                                    <div class="notification-item ${notification.is_read ? 'read' : 'unread'}" data-notification-id="${notification.id}">
                                        <div class="notification-icon ${notification.type}">
                                            ${icon}
                                        </div>
                                        <div class="notification-content">
                                            <p class="notification-message" style="color: black;">${notification.message}</p>
                                            <p class="notification-date" style="color: black;">${formattedDate}</p>
                                        </div>
                                        ${notification.link ? `<a href="${notification.link}" class="notification-link" data-notification-link="${notification.link}"></a>` : ''}
                                    </div>
                                `;
                            });
                            
                            notificationsList.innerHTML = notificationsHTML;
                            
                            // Click event to mark as read
                            const notificationItems = notificationsList.querySelectorAll('.notification-item');
                            notificationItems.forEach(item => {
                                item.addEventListener('click', function() {
                                    const notificationId = this.getAttribute('data-notification-id');
                                    
                                    // Mark as read if unread
                                    if (this.classList.contains('unread')) {
                                        markNotificationRead(notificationId);
                                        this.classList.remove('unread');
                                        this.classList.add('read');
                                    }
                                    
                                    // If notification has a link, navigate to it
                                    const link = this.querySelector('.notification-link');
                                    if (link) {
                                        window.location.href = link.getAttribute('href');
                                    }
                                });
                            });
                        } else {
                            notificationsList.innerHTML = '<div class="no-notifications"><p>No notifications</p></div>';
                        }
                    } else {
                        notificationsList.innerHTML = '<div class="notifications-error"><p>Error loading notifications</p></div>';
                    }
                })
                .catch(error => {
                    console.error('Error loading notifications:', error);
                    notificationsList.innerHTML = '<div class="notifications-error"><p>Error loading notifications</p></div>';
                });
        }
    }
    
    // Mark all notifications as read
    const markAllReadLink = document.getElementById('mark-all-read');
    if (markAllReadLink) {
        markAllReadLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Call the API to mark all notifications as read
            fetch('/api/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update notification counter
                    updateNotificationCounter(0);
                    
                    // Mark all notification items as read visually
                    const notificationItems = document.querySelectorAll('.notification-item.unread');
                    notificationItems.forEach(item => {
                        item.classList.remove('unread');
                        item.classList.add('read');
                    });
                    
                    // Clear displayed notifications tracking since they're all read now
                    localStorage.setItem('displayedNotifications', JSON.stringify([]));
                    
                    // Show success notification
                    showNotification('All notifications marked as read', 'success');
                }
            })
            .catch(error => {
                console.error('Error marking all notifications as read:', error);
                showNotification('Error marking notifications as read', 'error');
            });
        });
    }
    
    // Close notifications dropdown when clicking outside
    document.addEventListener('click', function(e) {
        const dropdown = document.getElementById('notifications-dropdown');
        const alertIcon = document.getElementById('alert-icon');
        
        if (dropdown && dropdown.classList.contains('show') && !dropdown.contains(e.target) && e.target !== alertIcon && !alertIcon.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
});