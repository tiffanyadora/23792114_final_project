# User role and access middleware

import re
import logging
from django.shortcuts import redirect
from django.urls import resolve, reverse

logger = logging.getLogger(__name__)

class RoleMiddleware:
    """
    Middleware to check user permissions based on role.
    Restricts access to certain pages based on user role.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URL patterns that require specific roles
        self.role_requirements = {
            r'^/admin-tools/': ['admin'],
            r'^/moderator-dashboard/': ['admin', 'moderator'],
            r'^/customer-service-dashboard/': ['admin', 'customer_service'],
            r'^/seller-dashboard/': ['admin', 'seller'],
            r'^/products/.*/edit/': ['admin', 'seller'],
            r'^/products/.*/delete/': ['admin', 'seller'],
            r'^/products/add/': ['admin', 'seller'],
            r'^/products/form/': ['admin', 'seller'],
            r'^/update-user-role/': ['admin'],
            r'^/toggle-review-ban/': ['admin', 'moderator'],
            r'^/toggle-product-listing/': ['admin', 'moderator', 'customer_service', 'seller'],
            r'^/cancel-order/': ['admin', 'customer_service', 'seller'],
            r'^/refund-order/': ['admin', 'customer_service'],
            r'^/assign-seller-role/': ['admin', 'customer_service'],
            r'^/fulfill-order/': ['admin', 'seller'],
        }
        
        # URL patterns that require authentication
        self.auth_required_urls = [
            r'^/profile/',
            r'^/orders/',
            r'^/messages/',
            r'^/notification-settings/',
            r'^/wishlist/',
        ]
    
    def __call__(self, request):
        # Skip middleware for static files and admin urls
        if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/admin/'):
            return self.get_response(request)
        
        # Check for role-specific URLs
        for pattern, allowed_roles in self.role_requirements.items():
            if re.match(pattern, request.path):
                # Check if user is authenticated
                if not request.user.is_authenticated:
                    # Store requested URL for redirect after login
                    request.session['next'] = request.path
                    # Add notification
                    request.session['notification'] = {
                        'type': 'error',
                        'message': 'Please log in to access this page.'
                    }
                    # Redirect to login
                    return redirect('login')
                
                # Check if user has required role
                if request.user.role not in allowed_roles:
                    # Log unauthorized access attempt
                    logger.warning(
                        f"Unauthorized access attempt: User {request.user.username} "
                        f"(role: {request.user.role}) tried to access {request.path}"
                    )
                    # Add notification
                    request.session['notification'] = {
                        'type': 'error',
                        'message': 'You do not have permission to access this page.'
                    }
                    # Redirect to home
                    return redirect('home')
        
        # Check for authentication-required URLs
        for pattern in self.auth_required_urls:
            if re.match(pattern, request.path):
                # Check if user is authenticated
                if not request.user.is_authenticated:
                    # Store requested URL for redirect after login
                    request.session['next'] = request.path
                    # Add notification
                    request.session['notification'] = {
                        'type': 'error',
                        'message': 'Please log in to access this page.'
                    }
                    # Redirect to login
                    return redirect('login')
        
        # Continue with request
        return self.get_response(request)

class EmailVerificationMiddleware:
    """
    Middleware to check if user's email is verified.
    Redirects to email verification page if email is not verified.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that require email verification
        self.verification_required_urls = [
            r'^/checkout/',
            r'^/orders/place/',
        ]
        
        # URLs that are exempt from verification check
        self.exempted_urls = [
            r'^/static/',
            r'^/media/',
            r'^/admin/',
            r'^/login/',
            r'^/logout/',
            r'^/register/',
            r'^/verify-email/',
            r'^/email-verification-needed/',
            r'^/resend-verification-email/',
            r'^/password-reset/',
        ]
    
    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Check if email is not verified
            if not request.user.email_verified:
                # Check if URL requires verification
                requires_verification = False
                
                # Check if current URL is in the verification required list
                for pattern in self.verification_required_urls:
                    if re.match(pattern, request.path):
                        requires_verification = True
                        break
                
                # Skip check for exempted URLs
                is_exempted = False
                for pattern in self.exempted_urls:
                    if re.match(pattern, request.path):
                        is_exempted = True
                        break
                
                # Redirect to verification page if necessary
                if requires_verification and not is_exempted:
                    # Add notification
                    request.session['notification'] = {
                        'type': 'warning',
                        'message': 'Please verify your email address to continue.'
                    }
                    # Redirect to verification needed page
                    return redirect('email_verification_needed')
        
        # Continue with request
        return self.get_response(request)