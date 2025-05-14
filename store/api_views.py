import os
import logging
import requests
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from .models import Product, VisualContent, Product, Notification, NotificationSettings

logger = logging.getLogger(__name__)
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')

def api_products(request):
    """
    Fetch all products with optimized query using select_related for category
    and prefetch_related for visuals to avoid N+1 queries.
    """
    try:
        products = Product.objects.filter(is_listed=True)\
                         .select_related('category', 'user')\
                         .prefetch_related('visuals')[:100]
        return JsonResponse({
            'success': True,
            'products': [p.to_json() for p in products]
        })
    except Exception as e:
        logger.error(f"Failed to fetch products: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def api_product_detail(request, product_id):
    """Fetch product detail by ID"""
    try:
        # Use Django's get_object_or_404
        product = get_object_or_404(Product, id=product_id)
        
        # Get visual content using filter rather than a custom method
        visuals = VisualContent.objects.filter(product=product)
        
        # Prepare the response data
        response_data = {
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'rating': float(product.rating),
                'quantity': int(product.quantity),
                'category': product.category.name if product.category else None,
                'feature': product.feature,
                'pokemon': product.pokemon,
                'location': product.location,
            },
            'visuals': [{
                'id': v.id,
                'name': v.name,
                'description': v.description,
                'short_name': v.short_name,
                'file_type': v.file_type
            } for v in visuals]
        }
        
        # Fetch pokemon data if available
        if product.pokemon:
            try:
                pokemon_data = _fetch_pokemon(product.pokemon)
                if pokemon_data.get('success'):
                    response_data['pokemon'] = pokemon_data
            except Exception as e:
                logger.error(f"Failed to fetch Pokemon data: {e}")
                # Don't fail the whole request if Pokemon data fails
        
        # Fetch weather data if available
        if product.location:
            try:
                weather_data = _fetch_weather(product.location)
                if weather_data.get('success'):
                    response_data['weather'] = weather_data
            except Exception as e:
                logger.error(f"Failed to fetch Weather data: {e}")
                # Don't fail the whole request if Weather data fails
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Failed to fetch product {product_id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def api_pokemon_data(request, pokemon_name):
    """Fetch Pokemon data"""
    try:
        return JsonResponse(_fetch_pokemon(pokemon_name))
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)
    except Exception as e:
        logger.error(f"Pokemon API error: {e}")
        return JsonResponse({'success': False, 'error': 'Pokemon data error'}, status=500)

def api_weather_data(request, city_name):
    """Fetch weather data"""
    try:
        return JsonResponse(_fetch_weather(city_name))
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=404)
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return JsonResponse({'success': False, 'error': 'Weather data error'}, status=500)

# --- Helper functions ---

def _fetch_pokemon(name):
    """Helper to get Pokemon data"""
    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
    resp = requests.get(url, timeout=5)
    
    if resp.status_code == 404:
        raise ValueError(f"Pokemon '{name}' not found")
    resp.raise_for_status()
    
    data = resp.json()
    return {
        'success': True,
        'name': data.get('name', '').capitalize(),
        'sprite': data.get('sprites', {}).get('front_default', ''),
        'types': [t['type']['name'].capitalize() for t in data.get('types', [])],
        'height': data.get('height', 0),
        'weight': data.get('weight', 0),
        'stats': {s['stat']['name']: s['base_stat'] for s in data.get('stats', [])}
    }

def _fetch_weather(city):
    """Helper to get weather data"""
    if not OPENWEATHER_API_KEY:
        raise EnvironmentError("OpenWeather API key not configured")

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    resp = requests.get(url, timeout=5)

    if resp.status_code == 404:
        raise ValueError(f"City '{city}' not found")
    resp.raise_for_status()

    data = resp.json()
    temp_c = data['main']['temp']
    temp_f = temp_c * 9 / 5 + 32

    return {
        'success': True,
        'city': data.get('name', city),
        'temperature_celsius': temp_c,
        'temperature_fahrenheit': temp_f,
        'condition': data['weather'][0]['main'],
        'description': data['weather'][0]['description'],
        'icon': data['weather'][0]['icon'],
        'icon_url': f"https://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",
        'humidity': data['main']['humidity'],
        'wind_speed': data['wind']['speed'],
        'timestamp': data['dt']
    }

def search_api(request):
    """API endpoint for searching products with filters"""
    query = request.GET.get('query', '').strip()
    category = request.GET.get('category', None)
    min_price = request.GET.get('min_price', None)
    max_price = request.GET.get('max_price', None)
    min_rating = request.GET.get('min_rating', None)
    
    # Convert string parameters to appropriate types
    if min_price:
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = None
            
    if max_price:
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = None
            
    if min_rating:
        try:
            min_rating = float(min_rating)
        except ValueError:
            min_rating = None
    
    # Search products with filters
    results = Product.search(query, category, min_price, max_price, min_rating)
    
    # If no results, suggest similar products
    suggestions = []
    if query and not results.exists():
        suggestions = Product.suggest_similar(query)
    
    # Format the response
    results_data = [product.to_json() for product in results]
    suggestions_data = [product.to_json() for product in suggestions]
    
    return JsonResponse({
        'results': results_data,
        'suggestions': suggestions_data,
        'query': query
    })

@login_required
def get_notifications(request):
    """Get user notifications"""
    try:
        # Get notifications for user
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
        
        # Format notifications for JSON response
        notification_data = []
        for notification in notifications:
            notification_data.append({
                'id': notification.id,
                'message': notification.message,
                'type': notification.type,
                'link': notification.link,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat()
            })
        
        # Get unread count
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'notifications': notification_data,
            'unread_count': unread_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def check_notifications(request):
    """Check for new unread notifications"""
    if not request.user.is_authenticated:
        # Return an empty response if not logged in
        return JsonResponse({'success': False, 'notifications': [], 'unread_count': 0}, status=200)
    
    try:
        # Get unread notifications for user
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
        
        # Format notifications for JSON response
        notification_data = []
        for notification in notifications:
            notification_data.append({
                'id': notification.id,
                'message': notification.message,
                'type': notification.type,
                'link': notification.link,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat()
            })
        
        # Get unread count
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'notifications': notification_data,
            'unread_count': unread_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        # Get notification
        notification = Notification.objects.get(id=notification_id, user=request.user)
        
        # Mark as read
        notification.mark_as_read()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Notification not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    try:
        # Mark all notifications as read
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'unread_count': 0
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def update_notification_settings(request):
    """Update notification settings"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)
    
    try:
        # Get or create notification settings for user
        settings = NotificationSettings.get_or_create_settings(request.user)
        
        # Update settings
        settings.order_updates = request.POST.get('order_updates') == 'on'
        settings.product_restock = request.POST.get('product_restock') == 'on'
        settings.price_alerts = request.POST.get('price_alerts') == 'on'
        settings.marketing_emails = request.POST.get('marketing_emails') == 'on'
        settings.save()
        
        # Add success notification
        Notification.create_notification(
            user=request.user,
            message='Notification settings updated successfully',
            notification_type='success'
        )
        
        # Redirect back to profile page
        request.session['notification'] = {
            'type': 'success',
            'message': 'Notification settings updated successfully'
        }
        
        return JsonResponse({
            'success': True
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
@login_required
def check_review_eligibility(request, product_id):
    """
    Check if the current user is eligible to review a specific product
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'can_review': False,
            'reason': 'Authentication required'
        })
        
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user is review banned
    if request.user.is_review_banned:
        return JsonResponse({
            'success': True,
            'can_review': False,
            'reason': 'Your review privileges have been suspended'
        })
        
    # Check if user has purchased the product or is an admin
    can_review = request.user.can_review_product(product_id)
    
    reason = None
    if not can_review:
        reason = 'You can only review products you have purchased'
    
    return JsonResponse({
        'success': True,
        'can_review': can_review,
        'reason': reason
    })