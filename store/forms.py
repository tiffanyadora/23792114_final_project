from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import os
import re
import json
import requests
import secrets
import string
from django.utils import timezone
from django.contrib.auth.hashers import check_password


User = get_user_model()

def generate_token(length=32):
    """Generate a secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class PasswordValidator:
    """Validator for password complexity requirements"""
    
    @classmethod
    def validate(cls, password):
        # Check length
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        # Check for at least one number
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        return True, "Password is valid"

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users with additional fields and validation"""
    
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    country = forms.CharField(max_length=100, required=True)
    terms_accepted = forms.BooleanField(required=True, label="I accept the Terms and Conditions")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        
        # Make all fields required
        for field_name in self.fields:
            self.fields[field_name].required = True

            # Apply Bootstrap classes except for checkboxes
            field = self.fields[field_name]
            if not isinstance(field.widget, forms.CheckboxInput):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()
            
        # Add custom error messages
        self.fields['username'].error_messages.update({
            'unique': 'This username is already taken',
        })
    
    def clean_username(self):
        """Ensure Username is unique regardless of case"""
        username = self.cleaned_data.get('username', '').lower()
        
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        
        return username
    
    def clean_email(self):
        """Ensure Email is unique"""
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists. Please use the forgot password link.")
        
        return email
    
    def clean_password1(self):
        """Validate password requirements"""
        password = self.cleaned_data.get('password1')
        
        is_valid, message = PasswordValidator.validate(password)
        if not is_valid:
            raise ValidationError(message)
        
        return password
    
    def save(self, commit=True):
        """Save the user with additional fields"""
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.country = self.cleaned_data['country']
        
        # Set role based on whether this is the first user
        is_first_user = User.objects.count() == 0
        user.role = 'admin' if is_first_user else 'customer'
        user.is_staff = is_first_user
        user.is_superuser = is_first_user
        
        # Generate verification token
        user.verification_token = generate_token()
        user.verification_token_created = timezone.now()
        user.email_verified = False
        
        if commit:
            user.save()
        return user
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'country', 
                 'password1', 'password2', 'terms_accepted')

class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form that accepts both username and email"""
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'autofocus': True})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap form-control class to all fields
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()
        self.error_messages['invalid_login'] = "The credentials you entered are not valid. Please try again."

class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form that accepts both username and email"""
    email = forms.CharField(
        label="Username or Email",
        max_length=254
    )
    
    def clean_email(self):
        # This method actually handles either username or email
        identifier = self.cleaned_data.get('email')
        
        # Don't validate if the email/username exists to avoid leaking information
        # The get_users method will handle the actual lookup
        
        return identifier
    
    def get_users(self, identifier):
        """Return matching user by email or username"""
        # Check if identifier is an email
        if '@' in identifier:
            users = User.objects.filter(email__iexact=identifier, is_active=True)
        else:
            # Try to find by username
            users = User.objects.filter(username__iexact=identifier, is_active=True)
        
        return users

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'id': 'password',
            'class': 'form-control',
            'placeholder': 'Enter new password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'id': 'confirm_password',
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        is_valid, message = PasswordValidator.validate(password)
        if not is_valid:
            raise forms.ValidationError(message)
        return password
    

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information"""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username', 'country', 'address', 'interest')
        
    def clean_username(self):
        """Ensure username is unique regardless of case"""
        username = self.cleaned_data.get('username', '').lower()
        
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This username is already taken.")
        
        return username
    
    def clean_email(self):
        """Ensure email is unique"""
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email already exists.")
        
        return email

def get_country_from_ip():
    """Get user's country based on IP information"""
    try:
        # Call ipapi.co API to get user's country
        response = requests.get('https://ipapi.co/json/')
        if response.status_code == 200:
            data = response.json()
            return data.get('country_name', '')
    except Exception:
        pass
    
    return ''