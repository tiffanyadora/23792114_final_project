from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
from django.contrib.admin.helpers import ActionForm
from django.forms import CharField, HiddenInput
from .models import Product, Category, User, Review
import os
import openai
import json
import logging

logger = logging.getLogger(__name__)

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'email_verified')
    list_filter = ('role', 'is_active', 'email_verified', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'country', 'address', 'interest')}),
        (_('Account status'), {'fields': ('is_active', 'email_verified', 'login_attempts', 'lockout_until')}),
        (_('Permissions'), {
            'fields': ('role', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
    )
    
    readonly_fields = ('created_at',)

class ProductAdminForm(ActionForm):
    # Hidden field to store the IDs of selected products
    selected_products = CharField(required=False, widget=HiddenInput())

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'rating', 'get_keywords_display', 'quantity', 'is_listed')
    search_fields = ('name', 'description', 'keywords')
    list_filter = ('category', 'is_listed')
    action_form = ProductAdminForm
    actions = ['generate_keywords']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'price', 'rating', 'category', 'quantity', 'is_listed', 'user')
        }),
        ('Features', {
            'fields': ('feature',),
        }),
        ('SEO & Discovery', {
            'fields': ('keywords',),
            'description': 'Keywords are used for product discovery and recommendations. Separate with commas. ADMIN ONLY.',
            'classes': ('collapse',),
        }),
        ('Additional Information', {
            'fields': ('pokemon', 'location'),
            'classes': ('collapse',),
        }),
    )
    
    def get_keywords_display(self, obj):
        """Format keywords for display in admin list view"""
        if not obj.keywords:
            return format_html('<span style="color: #999;">No keywords</span>')
        
        keywords = obj.get_keywords_list()
        return format_html(', '.join(f'<span style="background-color: #f0f0f0; padding: 2px 5px; border-radius: 3px; margin: 2px;">{k}</span>' for k in keywords))
    
    get_keywords_display.short_description = 'Keywords'
    
    def get_readonly_fields(self, request, obj=None):
        """Make keywords field read-only for non-admin users"""
        if not request.user.is_superuser:
            return ('keywords',)
        return ()
    
    def generate_keywords(self, request, queryset):
        """Admin action to generate keywords using OpenAI API"""
        if not request.user.is_superuser:
            self.message_user(
                request, 
                "Only admins can generate keywords.",
                level=messages.ERROR
            )
            return
            
        # Get OpenAI API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.message_user(
                request, 
                "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.",
                level=messages.ERROR
            )
            return
            
        # Initialize OpenAI client
        try:
            client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self.message_user(
                request, 
                f"Failed to initialize OpenAI client: {str(e)}",
                level=messages.ERROR
            )
            return
            
        # Process each product
        success_count = 0
        error_count = 0
        
        for product in queryset:
            try:
                # Prepare product data for the API
                product_data = {
                    'name': product.name,
                    'description': product.description,
                    'category': product.category.name if product.category else "",
                    'features': product.feature or "",
                }
                
                # Thee prompt
                prompt = f"""
                Generate 5-10 specific keywords (max 2-word each) for the following product, sorted by relevance. 
                The keywords should capture the product's main attributes, usage, and category.
                Format the output as a simple comma-separated list with no additional text.
                
                Product Name: {product_data['name']}
                Category: {product_data['category']}
                Description: {product_data['description']}
                Features: {product_data['features']}
                """
                
                # Call OpenAI API, we're using GPT-4o model
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a product categorization expert who generates relevant keywords for e-commerce products."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.2
                )
                
                # Extract and format the keywords
                keywords_text = response.choices[0].message.content.strip()
                
                # Clean up the keywords - remove line breaks, quotes, and extra spaces
                keywords_text = keywords_text.replace('\n', '').replace('"', '').replace("'", "")
                
                # Store the keywords
                product.keywords = keywords_text
                product.save()
                
                success_count += 1
                logger.info(f"Generated keywords for product {product.id}: {keywords_text}")
                
            except Exception as e:
                logger.error(f"Failed to generate keywords for product {product.id}: {str(e)}")
                error_count += 1
                
        # Show summary message
        if success_count > 0:
            self.message_user(
                request, 
                f"Successfully generated keywords for {success_count} products.",
                level=messages.SUCCESS
            )
            
        if error_count > 0:
            self.message_user(
                request, 
                f"Failed to generate keywords for {error_count} products. See logs for details.",
                level=messages.WARNING
            )
    
    generate_keywords.short_description = "Generate keywords using OpenAI"
    
admin.site.register(User, CustomUserAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Category)