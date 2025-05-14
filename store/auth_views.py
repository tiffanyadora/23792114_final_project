from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.middleware.csrf import get_token
from .models import User, NotificationSettings
from .forms import (
    CustomUserCreationForm, 
    CustomAuthenticationForm, 
    CustomPasswordResetForm, 
    CustomSetPasswordForm,
    UserProfileForm,
    get_country_from_ip
)
import uuid
import os
import logging
import requests
import json
from datetime import timedelta
from django_countries import countries

# Setup logging
logger = logging.getLogger(__name__)

# API keys from environment variables
MAILJET_API_KEY = os.environ.get('MAILJET_API_KEY')
MAILJET_SECRET_KEY = os.environ.get('MAILJET_API_SECRET')
IPINFO_API_KEY = os.environ.get('IPINFO_API_KEY')

# Setup mailjet for email sending
try:
    from mailjet_rest import Client
    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
except ImportError:
    mailjet = None
    logger.warning("Mailjet library not installed")

# IP tracking for password reset attempts
ip_reset_attempts = {}

# Registration view
@csrf_protect
def register(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('home')
    
    country_list = [name for code, name in countries]
    
    # Get user's country from IP
    default_country = get_country_from_ip()
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Generate verification token
            verification_token = str(uuid.uuid4())
            user.verification_token = verification_token
            user.verification_token_created = timezone.now()

            # Save user
            user.save()
                        
            # Set first user as admin
            if User.objects.count() == 0:
                user.role = 'admin'
                user.is_staff = True
                user.is_superuser = True
                user.email_verified = True  # Skip email verification for first user
            else:
                user.role = 'customer'
                user.email_verified = False
            
            # Send verification email if not first user
            if User.objects.count() > 1:
                send_verification_email(user)
            
            # Log the user in
            login(request, user)
            
            if User.objects.count() == 1:
                messages.success(request, "You have been registered as the site administrator.")
            else:
                messages.success(request, "Registration successful! Please check your email to verify your account.")
            
            return redirect('email_verification_needed')
    else:
        form = CustomUserCreationForm(initial={'country': default_country})
    
    return render(request, 'authen/register.html', {
        'form': form,
        'countries': country_list,
        'default_country': default_country,
        'csrf_token': get_token(request),
    })

# Login view
@csrf_protect
def user_login(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('home')
    
    context = {
        'form': CustomAuthenticationForm(),
        'is_locked_out': False
    }
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        context['form'] = form
        
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # If username is actually an email, get the associated username
        if '@' in username:
            try:
                user = User.objects.get(email__iexact=username)
                username = user.username
            except User.DoesNotExist:
                messages.error(request, "Incorrect username or password")
                return render(request, 'authen/login.html', context)
        
        # Try to get the user
        try:
            user = User.objects.get(username__iexact=username)
            
            # Check if account is locked
            if user.is_locked_out():
                lockout_time = user.lockout_until
                current_time = timezone.now()
                remaining_minutes = int((lockout_time - current_time).total_seconds() / 60) + 1
                
                context.update({
                    'is_locked_out': True,
                    'remaining_minutes': remaining_minutes,
                    'username': username
                })
                
                messages.error(request, "Your account is temporarily locked due to too many failed login attempts")
                return render(request, 'authen/login.html', context)
            
            # Attempt authentication
            user_auth = authenticate(username=user.username, password=password)
            if user_auth is not None:
                login(request, user_auth)
                user.reset_login_attempts()
                next_page = request.GET.get('next', 'home')
                return redirect(next_page)
            else:
                # Authentication failed, increment login attempts
                user.add_login_attempt()
                
                if user.login_attempts >= 5:
                    context.update({
                        'is_locked_out': True,
                        'remaining_minutes': 60,
                        'username': username
                    })
                    messages.error(
                        request, 
                        "Your account has been temporarily locked due to too many failed login attempts"
                    )
                else:
                    remaining_attempts = 5 - user.login_attempts
                    messages.error(
                        request, 
                        f"Incorrect username or password. You have {remaining_attempts} attempt(s) remaining."
                    )
                    context['username'] = username
                    
        except User.DoesNotExist:
            # User doesn't exist, but don't reveal this information
            messages.error(request, "Incorrect username or password")
    
    return render(request, 'authen/login.html', context)

# Logout view
def user_logout(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

# Password reset request
@csrf_protect
def password_reset_request(request):
    """Handle password reset requests."""
    
    if request.user.is_authenticated:
        return redirect('home')
    
    context = {
        'form': CustomPasswordResetForm(),
        'ip_rate_limited': False,
        'account_rate_limited': False
    }
    
    # Check IP-based limits
    client_ip = get_client_ip(request)
    current_time = timezone.now()
    
    # Initialize IP tracking if not exists
    if client_ip not in ip_reset_attempts:
        ip_reset_attempts[client_ip] = {
            'count': 0,
            'first_attempt': current_time
        }
    
    # Reset IP counter if it's been more than an hour
    if (current_time - ip_reset_attempts[client_ip]['first_attempt']).total_seconds() > 3600:
        ip_reset_attempts[client_ip] = {
            'count': 0,
            'first_attempt': current_time
        }
    
    # Check if IP has reached limit
    if ip_reset_attempts[client_ip]['count'] >= 3:
        # Calculate remaining time for IP limit
        elapsed_seconds = (current_time - ip_reset_attempts[client_ip]['first_attempt']).total_seconds()
        remaining_minutes = int((3600 - elapsed_seconds) / 60) + 1
        
        context.update({
            'ip_rate_limited': True,
            'remaining_minutes': remaining_minutes
        })
        
        return render(request, 'authen/password_reset_request.html', context)
    
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        context['form'] = form
        
        if form.is_valid():
            identifier = form.cleaned_data['email']
            
            # Get users matching the identifier
            users = form.get_users(identifier)
            
            # Check if any user was found
            if users.exists():
                user = users.first()
                
                # Check if the user can request a password reset
                if not user.can_reset_password():
                    # Get time remaining until next reset is allowed
                    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
                    elapsed_seconds = (timezone.now() - user.last_password_reset_request).total_seconds()
                    remaining_minutes = int((3600 - elapsed_seconds) / 60) + 1
                    
                    context.update({
                        'account_rate_limited': True,
                        'remaining_minutes': remaining_minutes
                    })
                    
                    return render(request, 'authen/password_reset_request.html', context)
                
                # Track the reset attempt for the user
                user.add_password_reset_attempt()
                
                # Increment IP-based counter
                ip_reset_attempts[client_ip]['count'] += 1
                
                # Generate token
                token = str(uuid.uuid4())
                user.reset_password_token = token
                user.reset_password_token_created = timezone.now()
                user.save()
                
                # Send password reset email
                send_password_reset_email(user)
            
            # Always show success message for security (don't reveal if account exists)
            context['success_message'] = "If your email address is registered, you will receive instructions to reset your password."
            return render(request, 'authen/password_reset_request.html', context)
    
    return render(request, 'authen/password_reset_request.html', context)

# Password request sent
def password_request_sent(request):
    """Show page after password reset email is sent."""
    return render(request, 'authen/password_request_sent.html')

# Password reset done
def password_reset_done(request):
    """Show page after password reset is done."""
    return render(request, 'authen/password_request_done.html')

# Password reset confirmation
@csrf_protect
def password_reset_confirm(request, token):
    """Handle password reset confirmation."""
    try:
        user = User.objects.get(reset_password_token=token)
        
        # Check if token is expired (24 hours)
        if not user.reset_password_token_created or \
           user.reset_password_token_created < timezone.now() - timedelta(hours=24):
            messages.error(request, "The password reset link has expired. Please request a new one.")
            return redirect('password_reset')
        
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                
                # Clear the reset token
                user.reset_password_token = None
                user.reset_password_token_created = None
                user.reset_login_attempts()
                user.save()
                
                messages.success(request, "Your password has been changed successfully. You can now log in.")
                return redirect('password_reset_done')
        else:
            form = CustomSetPasswordForm(user)
        
        return render(request, 'authen/password_reset_confirm.html', {
            'form': form,
            'valid_token': True,
            'token': token
        })
    
    except User.DoesNotExist:
        messages.error(request, "The password reset link is invalid. Please request a new one.")
        return redirect('password_reset')

# Email verification
def verify_email(request, token):
    """Handle email verification."""
    try:
        user = User.objects.get(verification_token=token)
        
        # Check if token is expired (7 days)
        if user.verification_token_created < timezone.now() - timedelta(days=7):
            messages.error(request, "The verification link has expired. Please request a new one.")
            return redirect('email_verification_needed')
        
        # Mark email as verified
        user.email_verified = True
        user.verification_token = None
        user.verification_token_created = None
        user.save()
        
        messages.success(request, "Your email has been verified successfully!")
        return render(request, 'authen/verification_result.html')
    
    except User.DoesNotExist:
        messages.error(request, "The verification link is invalid.")
        return redirect('email_verification_needed')

# Email verification needed
def email_verification_needed(request):
    """Show page indicating email verification is needed."""
    if request.user.is_authenticated and request.user.email_verified:
        return redirect('home')
    
    return render(request, 'authen/email_verification_needed.html')

# Resend verification email
@login_required
def resend_verification_email(request):
    """Resend verification email to the user."""
    user = request.user
    
    if user.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('home')
    
    # Generate new token
    token = str(uuid.uuid4())
    user.verification_token = token
    user.verification_token_created = timezone.now()
    user.save()
    
    # Send verification email
    send_verification_email(user)
    
    messages.success(request, "A new verification email has been sent. Please check your inbox.")
    return redirect('email_verification_needed')

# User profile view
@login_required
def user_profile(request):
    """Display and update user profile and notification settings."""
    
    # Get or create notification settings for the user
    notification_settings, created = NotificationSettings.objects.get_or_create(user=request.user)
    
    # Handle both profile and notification settings updates
    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')
        
        if form_type == 'profile':
            # Handle profile form submission
            form = UserProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Your profile has been updated successfully.")
                return redirect('profile')
            # If form is invalid, we'll pass it to the template below
        
        elif form_type == 'notifications':
            # Handle notification settings form submission
            notification_settings.order_updates = request.POST.get('order_updates') == 'on'
            notification_settings.product_restock = request.POST.get('product_restock') == 'on'
            notification_settings.price_alerts = request.POST.get('price_alerts') == 'on'
            notification_settings.marketing_emails = request.POST.get('marketing_emails') == 'on'
            notification_settings.save()
            
            messages.success(request, "Notification settings updated successfully.")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    country_list = [name for code, name in countries]
    
    # Get user's country from IP for new users
    default_country = get_country_from_ip()

    # Determine which tab to show first (useful if there were form validation errors)
    active_tab = 'account'
    if request.method == 'POST' and request.POST.get('form_type') == 'notifications':
        active_tab = 'notifications'

    return render(request, 'authen/profile.html', {
        'form': form, 
        'countries': country_list, 
        'default_country': default_country,
        'notification_settings': notification_settings,
        'active_tab': active_tab
    })

# Terms view
def terms_view(request):
    """Display terms and conditions."""
    return render(request, 'authen/terms.html')

# Admin tools view
@login_required
def admin_tools(request):
    """Admin tools and user management."""
    # Check if user is an admin
    if request.user.role != 'admin':
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    
    users = User.objects.exclude(id=request.user.id).order_by('username')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        
        if user_id and new_role:
            try:
                user_to_update = User.objects.get(id=user_id)
                user_to_update.role = new_role
                
                # Update staff status based on role
                if new_role in ['admin', 'staff']:
                    user_to_update.is_staff = True
                else:
                    user_to_update.is_staff = False
                
                # Update superuser status for admins
                user_to_update.is_superuser = (new_role == 'admin')
                
                user_to_update.save()
                
                messages.success(request, f'User {user_to_update.username} role updated to {new_role}')
            except User.DoesNotExist:
                messages.error(request, 'User not found')
    
    return render(request, 'admin_tools.html', {
        'users': users
    })

@require_POST
def check_username_availability(request):
    """Check if username is available."""
    username = request.POST.get('username', '').lower()
    
    if not username:
        return JsonResponse({'available': False, 'message': 'Please enter a username'})
    
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters long'})
    
    exists = User.objects.filter(username__iexact=username).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Username is available' if not exists else 'Username is already taken'
    })

@require_POST  
def check_email_availability(request):
    """Check if email is available."""
    email = request.POST.get('email', '').lower()
    
    if not email:
        return JsonResponse({'available': False, 'message': 'Please enter a valid email', 'html': False})
    
    # Email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    import re
    if not re.match(email_regex, email):
        return JsonResponse({'available': False, 'message': 'Please enter a valid email address', 'html': False})
    
    exists = User.objects.filter(email__iexact=email).exists()
    
    if exists:
        # Separate the HTML and text parts
        return JsonResponse({
            'available': False,
            'message': 'An account with this email already exists.',
            'html': True,
            'link': {
                'text': 'Forgot password?',
                'url': '/password-reset/'
            }
        })
    
    return JsonResponse({'available': True, 'message': 'Email is available', 'html': False})

# Helper functions
def send_verification_email(user):
    """Send email verification email."""
    if not mailjet or not all([MAILJET_API_KEY, MAILJET_SECRET_KEY]):
        logger.error("Mailjet API keys not configured")
        return False
    
    verification_url = f"{settings.SITE_URL}/verify-email/{user.verification_token}/"
    email_body = f"""
    <h2>Welcome to {settings.SITE_NAME}!</h2>
    <p>Hello {user.first_name},</p>
    <p>Thank you for registering with WildcatWear. Please click the link below to verify your email address:</p>
    <p><a href="{verification_url}" style="background-color: #0056b3; color: white; padding: 10px 15px; 
    text-decoration: none; border-radius: 4px;">Verify Email</a></p>
    <p>If the button above doesn't work, copy and paste this URL into your browser:</p>
    <p>{verification_url}</p>
    <p>This link will expire in 7 days.</p>
    <p>Best regards,<br>The WildcatWear Team</p>
    """
    
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "wildcatwear.team@gmail.com",
                    "Name": "WildcatWear Support"
                },
                "To": [
                    {
                        "Email": user.email,
                        "Name": user.get_full_name()
                    }
                ],
                "Subject": "Welcome to WildcatWear - Verify Your Email",
                "HTMLPart": email_body
            }
        ]
    }
    
    try:
        result = mailjet.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False

def send_password_reset_email(user):
    """Send password reset email."""
    if not mailjet or not all([MAILJET_API_KEY, MAILJET_SECRET_KEY]):
        logger.error("Mailjet API keys not configured")
        return False
    
    reset_url = f"{settings.SITE_URL}/password-reset/confirm/{user.reset_password_token}/"
    email_body = f"""
    <h2>Password Reset Request</h2>
    <p>Hello {user.first_name},</p>
    <p>You requested a password reset for your WildcatWear account. Click the link below to set a new password:</p>
    <p><a href="{reset_url}" style="background-color: #0056b3; color: white; padding: 10px 15px; 
    text-decoration: none; border-radius: 4px;">Reset Password</a></p>
    <p>If the button above doesn't work, copy and paste this URL into your browser:</p>
    <p>{reset_url}</p>
    <p>This link will expire in 24 hours.</p>
    <p>If you didn't request this reset, you can ignore this email.</p>
    <p>Best regards,<br>The WildcatWear Team</p>
    """
    
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "wildcatwear.team@gmail.com",
                    "Name": "WildcatWear Support"
                },
                "To": [
                    {
                        "Email": user.email,
                        "Name": user.get_full_name()
                    }
                ],
                "Subject": "WildcatWear - Password Reset Request",
                "HTMLPart": email_body
            }
        ]
    }
    
    try:
        result = mailjet.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        return False

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip