# product_features.py - Handle product interest tracking, subscriptions, and recommendations

from django.db.models import Count, Q, F
from django.utils import timezone
from .models import ProductView, ProductInterest, ProductSubscription, Product
import logging

logger = logging.getLogger(__name__)

def track_product_view(user, product):
    """Track product view and update user interests per page visit """
    if not user.is_authenticated:
        return
    
    # Record the view
    ProductView.objects.create(user=user, product=product)
    
    # Extract keywords from product
    keywords = product.get_keywords_list()

    if not keywords:
        keywords = extract_keywords(product)
    
    # If no admin-defined keywords, fall back to extracted keywords
    if not keywords:
        keywords = extract_keywords(product)
    
    # Update interests for each keyword
    for keyword in keywords:
        if not keyword or len(keyword) < 2:
            continue
            
        interest, created = ProductInterest.objects.get_or_create(
            user=user,
            keyword=keyword.lower()  # Normalize to lowercase
        )
        
        # Increment view count
        interest.view_count = F('view_count') + 1
        interest.save()
        interest.refresh_from_db()
        
        # If viewed 3+ times, this is now an interest
        if interest.view_count >= 3:
            logger.info(f"User {user.username} now has interest in '{keyword}'")

def extract_keywords(product):
    """Extract keywords from product for interest tracking"""
    keywords = []
    
    # Add category as keyword
    keywords.append(product.category.name.lower())
    
    # Extract words from product name
    name_words = product.name.lower().split()
    
    # Common words to exclude
    exclude_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    for word in name_words:
        if len(word) > 3 and word not in exclude_words:
            keywords.append(word)
    
    # Add pokemon as keyword if present
    if product.pokemon:
        keywords.append(product.pokemon.lower())
    
    return keywords

def get_recommended_products(user, limit=100):
    """Get recommended products based on user interests"""
    if not user.is_authenticated:
        # Return popular products for anonymous users
        return Product.objects.filter(is_listed=True).order_by('-rating', '-created_at')[:limit]
    
    # Start with an empty Q object
    q_objects = Q()
    
    # First check explicit interests from User model
    if user.interest:
        # Split the interest text field into keywords
        explicit_interests = [i.strip().lower() for i in user.interest.split(',') if i.strip()]
        for keyword in explicit_interests:
            q_objects |= Q(keywords__icontains=keyword)
    
    # Then get user's top interests from product views (with 3+ views)
    viewing_interests = ProductInterest.objects.filter(
        user=user,
        view_count__gte=3
    ).order_by('-view_count')[:5]
    
    # Add viewing interests to query
    for interest in viewing_interests:
        q_objects |= Q(keywords__icontains=interest.keyword)
    
    # If we have any interests (either explicit or from viewing history)
    if q_objects != Q():
        # Get recommended products
        recommended = Product.objects.filter(
            q_objects,
            is_listed=True
        ).exclude(
            # Exclude products the user already bought
            id__in=user.orders.filter(status='delivered').values_list('items__product_id', flat=True)
        ).distinct().order_by('-rating', '-created_at')[:limit]
    else:
        # If no interests found, return new releases
        recommended = Product.objects.filter(is_listed=True).order_by('-created_at')[:limit]
   
    # If we still don't have enough products, get some popular ones
    if recommended.count() < limit:
        existing_ids = set(recommended.values_list('id', flat=True))
        popular_products = Product.objects.filter(
            is_listed=True
        ).exclude(
            id__in=existing_ids
        ).order_by('-rating')[:limit-recommended.count()]
       
        # Combine the querysets
        recommended = list(recommended) + list(popular_products)
        
    return recommended

def get_popular_products(limit=8):
    """Get popular products based on order count"""
    return Product.objects.filter(
        is_listed=True
    ).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count', '-rating')[:limit]

def get_new_releases(limit=8):
    """Get new product releases"""
    one_month_ago = timezone.now() - timezone.timedelta(days=30)
    return Product.objects.filter(
        is_listed=True,
        created_at__gte=one_month_ago
    ).order_by('-created_at')[:limit]

def get_high_rated_products(limit=8):
    """Get highly rated products"""
    return Product.objects.filter(
        is_listed=True,
        rating__gte=4.0
    ).order_by('-rating', '-created_at')[:limit]

def subscribe_to_product(user, product, notify_price=True, notify_restock=True):
    """Subscribe user to product notifications"""
    subscription, created = ProductSubscription.objects.get_or_create(
        user=user,
        product=product,
        defaults={
            'notify_price_change': notify_price,
            'notify_restock': notify_restock
        }
    )
    
    if not created:
        subscription.notify_price_change = notify_price
        subscription.notify_restock = notify_restock
        subscription.save()
    
    return subscription

def unsubscribe_from_product(user, product):
    """Unsubscribe user from product notifications"""
    ProductSubscription.objects.filter(user=user, product=product).delete()

def notify_price_change(product, old_price, new_price):
    """Notify subscribers about price change"""
    from .models import Notification, NotificationSettings
    
    subscribers = ProductSubscription.objects.filter(
        product=product,
        notify_price_change=True
    ).select_related('user')
    
    for subscription in subscribers:
        user = subscription.user
        
        # Check user's notification settings
        settings = NotificationSettings.get_or_create_settings(user)
        if not settings.price_alerts:
            continue
        
        # Create notification
        if new_price < old_price:
            message = f"Price drop! {product.name} is now ${new_price} (was ${old_price})"
        else:
            message = f"Price change: {product.name} is now ${new_price} (was ${old_price})"
        
        Notification.create_notification(
            user=user,
            message=message,
            notification_type='info',
            link=f"/products/{product.id}/"
        )

def notify_restock(product):
    """Notify subscribers about product restock"""
    from .models import Notification, NotificationSettings
    
    subscribers = ProductSubscription.objects.filter(
        product=product,
        notify_restock=True
    ).select_related('user')
    
    for subscription in subscribers:
        user = subscription.user
        
        # Check user's notification settings
        settings = NotificationSettings.get_or_create_settings(user)
        if not settings.product_restock:
            continue
        
        # Create notification
        message = f"{product.name} is back in stock!"
        
        Notification.create_notification(
            user=user,
            message=message,
            notification_type='success',
            link=f"/products/{product.id}/"
        )