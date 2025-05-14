from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from django.conf import settings

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require that a user is staff or admin"""
    
    def test_func(self):
        """Test if the user is staff or admin"""
        return self.request.user.is_authenticated and (
            self.request.user.role in ['staff', 'admin'] or 
            self.request.user.is_staff or 
            self.request.user.is_superuser
        )
    
    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission"""
        if self.request.user.is_authenticated:
            # User is authenticated but doesn't have permission
            raise PermissionDenied("You don't have permission to access this page")
        # User is not authenticated
        return redirect(f"{reverse('login')}?next={self.request.path}")

class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require that a user is admin"""
    
    def test_func(self):
        """Test if the user is admin"""
        return self.request.user.is_authenticated and (
            self.request.user.role == 'admin' or 
            self.request.user.is_superuser
        )
    
    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission"""
        if self.request.user.is_authenticated:
            # User is authenticated but doesn't have permission
            raise PermissionDenied("You don't have permission to access this page")
        # User is not authenticated
        return redirect(f"{reverse('login')}?next={self.request.path}")

class EmailVerifiedMixin(UserPassesTestMixin):
    """Mixin to require that a user has verified their email"""
    
    def test_func(self):
        """Test if the user has verified their email"""
        return self.request.user.is_authenticated and self.request.user.email_verified
    
    def handle_no_permission(self):
        """Redirect to email verification page if email not verified"""
        if self.request.user.is_authenticated:
            # User is authenticated but email not verified
            return redirect('email_verification_needed')
        # User is not authenticated
        return redirect(f"{reverse('login')}?next={self.request.path}")

def staff_required(view_func):
    """Decorator for function-based views that requires staff or admin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        
        if request.user.role in ['staff', 'admin'] or request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        raise PermissionDenied("You don't have permission to access this page")
    
    return _wrapped_view

def admin_required(view_func):
    """Decorator for function-based views that requires admin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        
        if request.user.role == 'admin' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        raise PermissionDenied("You don't have permission to access this page")
    
    return _wrapped_view

def email_verified_required(view_func):
    """Decorator for function-based views that requires email verification"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        
        if request.user.email_verified:
            return view_func(request, *args, **kwargs)
        
        return redirect('email_verification_needed')
    
    return _wrapped_view