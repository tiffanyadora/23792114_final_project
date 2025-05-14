from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator, RegexValidator
from django.db.models import Q
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        email = self.normalize_email(email)
        username = username.lower()  # Store username as lowercase
        
        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )
        
        # Django handle the password hashing
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)
        
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('customer_service', 'Customer Service'),
        ('seller', 'Seller'),
        ('customer', 'Customer'),
    )
    
    username = models.CharField(
        max_length=150, 
        unique=True,
        validators=[
            MinLengthValidator(3, 'Username must be at least 3 characters long'),
        ]
    )
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    address = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    interest = models.TextField(blank=True, null=True)

    is_review_banned = models.BooleanField(default=False)
    
    # Account status and security fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    login_attempts = models.IntegerField(default=0)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    lockout_until = models.DateTimeField(null=True, blank=True)
    
    # Password reset tracking
    password_reset_attempts = models.IntegerField(default=0)
    last_password_reset_request = models.DateTimeField(null=True, blank=True)
    
    # Email verification token
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    verification_token_created = models.DateTimeField(null=True, blank=True)
    
    # Password reset token
    reset_password_token = models.CharField(max_length=100, blank=True, null=True)
    reset_password_token_created = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username
    
    def get_short_name(self):
        return self.first_name if self.first_name else self.username
    
    def add_login_attempt(self):
        """Increment login attempt counter and update timestamp"""
        self.login_attempts += 1
        self.last_login_attempt = timezone.now()
        
        # Lock account after 5 unsuccessful attempts
        if self.login_attempts >= 5:
            self.lockout_until = timezone.now() + timezone.timedelta(hours=1)
        
        self.save(update_fields=['login_attempts', 'last_login_attempt', 'lockout_until'])
    
    def reset_login_attempts(self):
        """Reset login attempts counter after successful login"""
        self.login_attempts = 0
        self.lockout_until = None
        self.save(update_fields=['login_attempts', 'lockout_until'])
    
    def is_locked_out(self):
        """Check if the account is locked out due to too many failed login attempts"""
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        return False
    
    def can_reset_password(self):
        """Check if the user can request a password reset"""
        if not self.last_password_reset_request:
            return True
            
        # Allow 3 password reset requests per hour
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        if self.last_password_reset_request < one_hour_ago:
            # Reset counter if the last request was more than an hour ago
            self.password_reset_attempts = 0
            self.save(update_fields=['password_reset_attempts'])
            return True
            
        # Check if the user has reached the limit
        return self.password_reset_attempts < 3
    
    def add_password_reset_attempt(self):
        """Track password reset attempts"""
        self.password_reset_attempts += 1
        self.last_password_reset_request = timezone.now()
        self.save(update_fields=['password_reset_attempts', 'last_password_reset_request'])
    
    def get_or_create_cart(self):
        """Get the user's current cart or create a new one"""
        # NOTE: This was previously defined but now make sure it references the correct model
        cart, created = Cart.objects.get_or_create(user=self, is_active=True)
        return cart
    
    def has_purchased_product(self, product_id):
        """
        Check if the user has purchased a specific product in any of their orders
        """
        # Check if user has ordered this product
        return OrderItem.objects.filter(
            order__user=self,
            product_id=product_id
        ).exists()
    
    def can_review_product(self, product_id):
        """
        Check if the user can review a specific product
        A user can review a product if they:
        1. Have purchased the product
        2. OR have admin role
        3. AND are not review banned
        """
        if self.is_review_banned:
            return False
            
        if self.role == 'admin':
            return True
            
        return self.has_purchased_product(product_id)


class Product(models.Model):
    """
    Product model for storing product information
    """
    # Indexes were added for name and is_listed fields since they are used alot in filtering
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    feature = models.TextField(blank=True, null=True)
    rating = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    pokemon = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    keywords = models.TextField(blank=True, null=True, help_text="Comma-separated keywords for the product")
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='products',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return self.name
        
    def to_json(self):
        """Convert product to JSON serializable dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'feature': self.feature,
            'rating': float(self.rating),
            'price': float(self.price),
            'category': self.category.name,
            'pokemon': self.pokemon,
            'location': self.location,
            'keywords': self.keywords,
            'quantity': self.quantity,
            'image': self.get_primary_image_name()
        }
        
    def get_primary_image_name(self):
        """Get the primary image filename for this product"""
        visual = self.visuals.first()
        if visual:
            return f"{visual.short_name}.{visual.file_type}"
        return "default.jpg"
    
    def get_features_list(self):
        """Split the feature string into a list of features"""
        if not self.feature:
            return []
        return [f.strip() for f in self.feature.split(',')]
    
    def get_keywords_list(self):
        """Split the keywords string into a list of keywords"""
        if not self.keywords:
            return []
        return [k.strip().lower() for k in self.keywords.split(',')]
    
    @classmethod
    def search(cls, query=None, category=None, min_price=None, max_price=None, min_rating=None):
        """
        Search products with filters
        """

        # Start with is_listed=True filter
        products = cls.objects.filter(is_listed=True)

        # Filter by query (search in name and description)
        if query:
            products = products.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query)
            )
        
        # Apply other filters
        if category:
            products = products.filter(category__name=category)
        
        if min_price is not None:
            products = products.filter(price__gte=min_price)
        
        if max_price is not None:
            products = products.filter(price__lte=max_price)
        
        if min_rating is not None:
            products = products.filter(rating__gte=min_rating)
        
        return products
        
    @classmethod
    def suggest_similar(cls, query):
        """
        Find similar products based on name similarity when no exact matches found
        Returns products with partial word matches sorted by relevance
        """
        if not query:
            return cls.objects.none()
        
        # Break query into words for better matching
        query_words = query.lower().split()
        
        # Build a complex query to find products with similar names
        name_q = Q()
        
        # Match each word in the query
        for word in query_words:
            if len(word) > 2:  # Only match on words with more than 2 characters
                name_q |= Q(name__icontains=word)
        
        # Find products with similar names
        similar_products = cls.objects.filter(name_q, is_listed=True)
        
        # If no matches found by name words, try fuzzy matching using trigrams
        if not similar_products.exists() and len(query) > 3:
            # Find products where at least part of the name matches
            for i in range(len(query) - 2):
                trigram = query[i:i+3].lower()
                if len(trigram) == 3:
                    similar_products |= cls.objects.filter(name__icontains=trigram)
        
        # Sort by relevance - products whose names start with the query should appear first
        result_list = list(similar_products)
        result_list.sort(key=lambda p: (not p.name.lower().startswith(query.lower()), p.name))
        
        # Return top suggestions (limit to avoid overwhelming the user)
        return result_list[:8]

class VisualContent(models.Model):
    """
    VisualContent model for storing product images and other visual content
    """
    name = models.CharField(max_length=255)
    description = models.TextField()
    short_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    css_class = models.CharField(max_length=50, default='product-image')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='visuals')
    
    def __str__(self):
        return f"{self.name} ({self.product.name})"
        
    def get_html(self, css_override=None):
        """Return an HTML <img> tag for the visual content"""
        css_class = css_override if css_override else self.css_class
        return f'<img class="{css_class}" alt="{self.description}" src="/static/images/{self.short_name}.{self.file_type}">'
    
    def to_json(self):
        """Convert visual content to JSON serializable dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'short_name': self.short_name,
            'file_type': self.file_type,
            'css_class': self.css_class,
            'product_id': self.product.id,
            'img_url': f"/static/images/{self.short_name}.{self.file_type}"
        }


class ProductSubscription(models.Model):
    """
    Model for users subscribing to product updates (price changes, restock)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_subscriptions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='subscribers')
    notify_price_change = models.BooleanField(default=True)
    notify_restock = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.username} subscribed to {self.product.name}"

class ProductInterest(models.Model):
    """
    Track user interests based on product views with keywords
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_interests')
    keyword = models.CharField(max_length=100)
    view_count = models.PositiveIntegerField(default=1)
    last_viewed = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'keyword')
    
    def __str__(self):
        return f"{self.user.username} - {self.keyword} ({self.view_count} views)"

class ProductView(models.Model):
    """
    Track product views for recommendations
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_views')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"

class Review(models.Model):
    """
    Review model for product reviews
    """
    # Index was added for product field to make fetching a product's reviews more efficient
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    username = models.CharField(max_length=100)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username}"
    
    def to_json(self):
        """Convert review to JSON serializable format"""
        return {
            'id': self.id,
            'product_id': self.product.id,
            'user_id': self.user.id,
            'username': self.user.username,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat(),
            'product_rating': self.product.rating
        }
    
    def save(self, *args, **kwargs):
        # Ensure username matches user's username
        if self.user:
            self.username = self.user.username
        super().save(*args, **kwargs)

class Cart(models.Model):
    """
    Cart model for storing user shopping carts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)  # Add link to User
    session_id = models.CharField(max_length=255, blank=True, null=True)  # Keep for anonymous users
    is_active = models.BooleanField(default=True)  # Flag for active/inactive cart
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.user:
            return f"Cart {self.id} - {self.user.username}"
        return f"Cart {self.id} - {self.session_id}"
    
    @property
    def total_price(self):
        """Calculate total price of items in cart"""
        return sum(item.subtotal for item in self.items.all())
    
    @classmethod
    def get_or_create_cart(cls, user=None, session_id=None):
        """Get an active cart for a user or session, or create a new one"""
        if user:
            cart, created = cls.objects.get_or_create(
                user=user, 
                is_active=True,
                defaults={'session_id': session_id}
            )
        elif session_id:
            cart, created = cls.objects.get_or_create(
                session_id=session_id,
                user__isnull=True,  # Ensure no user is associated
                is_active=True
            )
        else:
            # Neither user nor session_id provided
            return None
        
        return cart
    
    def transfer_from_session(self, session_id):
        """Transfer items from a session cart to this user cart"""
        if not self.user:
            return False
            
        # Find the session cart
        session_cart = Cart.objects.filter(
            session_id=session_id,
            user__isnull=True,
            is_active=True
        ).first()
        
        if not session_cart:
            return False
            
        # Transfer items
        for item in session_cart.items.all():
            # Check if the same product already exists in the user's cart
            existing_item = self.items.filter(
                product=item.product,
                size=item.size
            ).first()
            
            if existing_item:
                # Update quantity if item already exists
                existing_item.quantity += item.quantity
                existing_item.save()
            else:
                # Create new item in user's cart
                CartItem.objects.create(
                    cart=self,
                    product=item.product,
                    quantity=item.quantity,
                    size=item.size
                )
                
        # Deactivate the session cart
        session_cart.is_active = False
        session_cart.save()
        
        return True

class CartItem(models.Model):
    """
    CartItem model for storing items in a cart
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True, null=True)  # For apparel
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Cart {self.cart.id}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this cart item"""
        return self.product.price * self.quantity

class Order(models.Model):
    """
    Order model for completed purchases
    """
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled')
    )

    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed')
    )

    PAYMENT_METHODS = (
    ('credit_card', 'Credit Card'),
    ('bank_transfer', 'Bank Transfer'),
    ('ewallet', 'E-Wallet'),
    ('cod', 'Cash on Delivery'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)  # Add link to User
    session_id = models.CharField(max_length=255, blank=True, null=True)  # Keep for anonymous users
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    shipping_address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='credit_card')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_info = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.user:
            return f"Order {self.id} - {self.user.username}"
        return f"Order {self.id} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        # If user is provided and user fields are empty, populate them
        if self.user and not self.full_name:
            self.full_name = self.user.get_full_name()
        if self.user and not self.email:
            self.email = self.user.email
        if self.user and not self.shipping_address and self.user.address:
            self.shipping_address = self.user.address
        if self.user and not self.shipping_address and self.user.address:
            self.shipping_address = self.user.address
        if not self.payment_method:
            self.payment_method = 'credit_card'
            
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """
    OrderItem model for items in an order
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255)  # Store name in case product is deleted
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of purchase
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True, null=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} in Order {self.order.id}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this order item"""
        return self.price * self.quantity

class Notification(models.Model):
    """
    Notification model for storing user notifications
    """
    TYPE_CHOICES = (
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
    
    @classmethod
    def create_notification(cls, user, message, notification_type='info', link=None):
        """
        Create a new notification for a user
        """
        return cls.objects.create(
            user=user,
            message=message,
            type=notification_type,
            link=link
        )
    
    @classmethod
    def create_bulk_notification(cls, users, message, notification_type='info', link=None):
        """
        Create notifications for multiple users
        """
        notifications = []
        for user in users:
            notifications.append(
                cls(
                    user=user,
                    message=message,
                    type=notification_type,
                    link=link
                )
            )
        return cls.objects.bulk_create(notifications)

class NotificationSettings(models.Model):
    """
    User notification preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    order_updates = models.BooleanField(default=True)
    product_restock = models.BooleanField(default=True)
    price_alerts = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Settings for {self.user.username}"
    
    @classmethod
    def get_or_create_settings(cls, user):
        """Get or create notification settings for a user"""
        settings, created = cls.objects.get_or_create(user=user)
        return settings
    
class Conversation(models.Model):
    """
    Model to track conversations between users
    """
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.ForeignKey('Message', null=True, blank=True, on_delete=models.SET_NULL, related_name='last_message_conversation')
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participants_str = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation between {participants_str}"
    
    def update_last_message(self, message):
        """Update last message reference"""
        self.last_message = message
        self.save()
    
    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        # Find conversations where both users are participants
        conversations = cls.objects.filter(participants=user1).filter(participants=user2)
        
        if conversations.exists():
            return conversations.first()
        else:
            # Create new conversation
            conversation = cls.objects.create()
            conversation.participants.add(user1, user2)
            conversation.save()
            return conversation
        
    @classmethod
    def get_conversations_for_user(cls, user):
        """Get all conversations for a user"""
        return cls.objects.filter(participants=user)
    
class Message(models.Model):
    """
    Message model for user-to-user messaging
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}: {self.subject}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.save()
    
    @classmethod
    def get_conversation(cls, user1, user2):
        """Get conversation between two users"""
        return cls.objects.filter(
            models.Q(sender=user1, recipient=user2) | 
            models.Q(sender=user2, recipient=user1)
        ).order_by('created_at')
    
    @classmethod
    def get_unread_count(cls, user):
        """Get count of unread messages for user"""
        return cls.objects.filter(recipient=user, is_read=False).count()
