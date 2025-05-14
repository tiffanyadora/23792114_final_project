# store/views.py

import os
import json
import random
import requests
import logging
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.db import models, connection
from django.db.models import Q, Count, Max, F, Value, BooleanField, Prefetch
from django.db.models.functions import Concat
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import (
    Product, VisualContent, Category, Review, 
    Cart, CartItem, Order, OrderItem,
    User, Message, Conversation, Notification, NotificationSettings
)

from django.core.cache import cache
from django.conf import settings
import hashlib

# Setup logging
logger = logging.getLogger(__name__)

# OpenWeather API Key
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')

def home(request):
    category_name = request.GET.get('category', None)
    page = request.GET.get('page', 1)
    sort_by = request.GET.get('sort', 'recommended') # Default sort to recommended

    # Try to get categories from cache
    categories = cache.get('all_categories')
    
    if not categories:
        # Get all categories with associated images if not in cache
        categories = {}
        default_images = {
            "Apparel": "t-shirt.jpg",
            "Accessories": "cap.jpg",
            "Gifts": "keychain.jpg"
        }
        for category in Category.objects.all():
            categories[category.name] = default_images.get(category.name, "flag.jpg")
        
        # Cache categories for 1 hour (3600 seconds)
        cache.set('all_categories', categories, 3600)

    # Query products based on sort option
    if sort_by == 'recommended' and request.user.is_authenticated:
        from .product_features import get_recommended_products
        products = get_recommended_products(request.user, limit=100)
    elif sort_by == 'popular':
        from .product_features import get_popular_products
        products = get_popular_products(limit=100)
    elif sort_by == 'new':
        from .product_features import get_new_releases
        products = get_new_releases(limit=100)
    elif sort_by == 'rating':
        from .product_features import get_high_rated_products
        products = get_high_rated_products(limit=100)
    else:
        # Else, sort from newest products first
        products = Product.objects.filter(is_listed=True)
        if category_name:
            products = products.filter(category__name=category_name)
        products = products.order_by('-created_at')

    # If category filter is applied (again for non-recommended lists)
    if category_name and sort_by != 'recommended':
        products = products.filter(category__name=category_name)

    # Pagination (8 products per page)
    paginator = Paginator(products, 8)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    return render(request, 'index.html', {
        'categories': categories,
        'products': products_page,
        'selected_category': category_name,
        'sort_by': sort_by,
    })

def product_detail(request, product_id=None):
    """
    Product detail view with caching and prefetching.
    
    Optimizations:
    1. Reviews are prefetched with select_related to avoid N+1 queries
    2. Suggested products query uses prefetching for categories
    """
    # Use the request parameter if not explicitly provided
    if not product_id:
        product_id = request.GET.get('id')
    
    if not product_id:
        raise Http404("Product ID missing")
    
    # Create a cache key for this product
    cache_key = f'product_detail_{product_id}'
    
    # Try to get data from cache
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Use cached data if available
        product = cached_data.get('product')
        visuals = cached_data.get('visuals')
        product_features = cached_data.get('product_features')
        pokemon_data = cached_data.get('pokemon_data')
    else:
        # Get product by ID
        product = get_object_or_404(Product, id=product_id)
        
        # Get visuals for a product
        visuals = VisualContent.objects.filter(product=product)
        
        # Split features into a list
        product_features = product.get_features_list()
        
        # Get Pokemon data (server-side API call)
        pokemon_data = None
        if product.pokemon:
            try:
                pokemon_response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{product.pokemon.lower()}")
                if pokemon_response.status_code == 200:
                    pokemon_json = pokemon_response.json()
                    pokemon_data = {
                        'name': pokemon_json.get('name', '').capitalize(),
                        'sprite': pokemon_json.get('sprites', {}).get('front_default', ''),
                        'types': [t.get('type', {}).get('name', '').capitalize() for t in pokemon_json.get('types', [])],
                    }
            except Exception as e:
                logger.error(f"Error fetching Pokemon data: {str(e)}")
        
        # Cache the data for 30 minutes (1800 seconds)
        cache.set(cache_key, {
            'product': product,
            'visuals': visuals,
            'product_features': product_features, 
            'pokemon_data': pokemon_data
        }, 1800)

    # Track user interest if authenticated
    if request.user.is_authenticated:
        from .product_features import track_product_view
        track_product_view(request.user, product)

    
    # ORM Query: Get reviews for this product
    # Equivalent SQL Query:
    # SELECT * FROM store_review WHERE product_id = %s ORDER BY created_at DESC

    # Get reviews with prefetching to avoid N+1 queries
    # This isn't cached because reviews change frequently and are user-specific
    reviews = Review.objects.filter(product_id=product_id)\
                           .select_related('user')\
                           .order_by('-created_at')
    
    # ORM Query: Get all products except current
    # Equivalent SQL Query:
    # SELECT * FROM store_product WHERE id != %s

    # Recommendation products features with prefetching:
    # Get products efficiently with prefetch_related
    all_products = Product.objects.exclude(id=product_id)\
                           .select_related('category', 'user')\
                           .filter(is_listed=True)

    # Recommendation products features:
    suggested_products = []

    # 1. First try to find products with similar names
    if product.name:
        # Split the product name into words for matching
        name_words = product.name.lower().split()
        
        # Create a Q object for name matching
        name_q = Q()
        
        # Add each word from the name to our query
        for word in name_words:
            if len(word) > 3:  # Only match on words with more than 3 characters to avoid common words
                name_q |= Q(name__icontains=word)
        
        # Find products with similar names
        name_matches = all_products.filter(name_q)[:3]
        suggested_products.extend(name_matches)
    
    # Keep track of already suggested product IDs to avoid duplicates
    suggested_ids = [p.id for p in suggested_products]

    # 2. If we need more products, look for products in the same category
    if len(suggested_products) < 4:
        category_matches = all_products.filter(category=product.category).exclude(
            id__in=suggested_ids
        )[:4-len(suggested_products)]
        suggested_products.extend(category_matches)
        # Update our list of suggested IDs
        suggested_ids = [p.id for p in suggested_products]
        
    # 3. If we still need more, look for products with similar Pokemon
    if len(suggested_products) < 4 and product.pokemon:
        # Find products with the same Pokemon type
        pokemon_matches = all_products.filter(
            pokemon__icontains=product.pokemon
        ).exclude(
            id__in=suggested_ids
        )[:4-len(suggested_products)]
        
        suggested_products.extend(pokemon_matches)
        # Update our list of suggested IDs
        suggested_ids = [p.id for p in suggested_products]

    # If we still don't have 4 products, fill with random products
    if len(suggested_products) < 4:
        remaining_products = all_products.exclude(
            id__in=suggested_ids
        )
        
        # If we have remaining products, randomly select what we need
        if remaining_products.exists():
            # Convert queryset to list for random sampling
            remaining_list = list(remaining_products)
            # Calculate how many more products we need
            needed = 4 - len(suggested_products)
            # Randomly sample the needed number of products
            random_picks = random.sample(remaining_list, min(needed, len(remaining_list)))
            suggested_products.extend(random_picks)
    
    #  At most 4 suggested products
    suggested_products = suggested_products[:4]

    # Split features into a list
    product_features = product.get_features_list()

    # Get Pokemon data (server-side API call)
    pokemon_data = None
    if product.pokemon:
        try:
            pokemon_response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{product.pokemon.lower()}")
            if pokemon_response.status_code == 200:
                pokemon_json = pokemon_response.json()
                pokemon_data = {
                    'name': pokemon_json.get('name', '').capitalize(),
                    'sprite': pokemon_json.get('sprites', {}).get('front_default', ''),
                    'types': [t.get('type', {}).get('name', '').capitalize() for t in pokemon_json.get('types', [])],
                }
        except Exception as e:
            logger.error(f"Error fetching Pokemon data: {str(e)}")

    user_context = {}
    if request.user.is_authenticated:
        user_context = {
            'is_authenticated': True,
            'username': request.user.username,
            'user_role': request.user.role,
            'is_review_banned': request.user.is_review_banned
        }
    else:
        user_context = {
            'is_authenticated': False,
            'username': '',
            'user_role': 'guest',
            'is_review_banned': False
        }

    return render(request, 'store.html', {
        'product': product,
        'visuals': visuals,
        'suggested_products': suggested_products,
        'product_features': product_features,
        'pokemon_data': pokemon_data,
        'reviews': reviews,
        'user_context': user_context,
    })


def search(request):
    query = request.GET.get('query', '').strip()
    category = request.GET.get('category', None)
    min_price = request.GET.get('min_price', None)
    max_price = request.GET.get('max_price', None)
    min_rating = request.GET.get('min_rating', None)
    page = request.GET.get('page', 1)

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

    if not query and not category and not min_price and not max_price and not min_rating:
        return render(request, 'search.html', {
            'results': [],
            'query': None,
            'categories': Category.objects.all()
        })

    # Perform product search with filters + is_listed=True
    results = Product.search(query, category, min_price, max_price, min_rating).filter(is_listed=True)

    # If no results, suggest similar listed products
    suggestions = []
    if query and not results.exists():
        suggestions = Product.suggest_similar(query)

    # Pagination - 8 products per page
    paginator = Paginator(results, 8)

    try:
        results_page = paginator.page(page)
    except PageNotAnInteger:
        results_page = paginator.page(1)
    except EmptyPage:
        results_page = paginator.page(paginator.num_pages)

    return render(request, 'search.html', {
        'results': results_page,
        'query': query,
        'suggestions': suggestions,
        'categories': Category.objects.all(),
        'category': category,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating
    })


@csrf_exempt
def add_product_api(request):
    if request.method == 'POST':
        try:
            # Reset both sequences before creating new records
            with connection.cursor() as cursor:
                cursor.execute("SELECT setval(pg_get_serial_sequence('store_product', 'id'), (SELECT COALESCE(MAX(id), 0) FROM store_product), true)")
                cursor.execute("SELECT setval(pg_get_serial_sequence('store_visualcontent', 'id'), (SELECT COALESCE(MAX(id), 0) FROM store_visualcontent), true)")
            
            data = json.loads(request.body)
            
            # Get or create category
            category, _ = Category.objects.get_or_create(name=data.get('category'))
            
            # ORM Query: Create new product
            # Equivalent SQL Query:
            # INSERT INTO store_product (name, description, feature, rating, price, category_id, pokemon, location, quantity, created_at, updated_at)
            # VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            product = Product.objects.create(
                name=data.get('name'),
                description=data.get('description'),
                feature=data.get('features'),
                rating=float(data.get('rating', 0)),
                price=float(data.get('price', 0)),
                category=category,
                pokemon=data.get('pokemon', ''),
                location=data.get('location', ''),
                quantity=int(data.get('quantity', 0)),
                user=request.user if request.user.is_authenticated else None
            )
            
            # Add visual content
            image_name = data.get('imageName', '').split('.')
            
            # ORM Query: Create new visual content
            # Equivalent SQL Query:
            # INSERT INTO store_visualcontent (name, description, short_name, file_type, css_class, product_id)
            # VALUES (%s, %s, %s, %s, %s, %s)
            VisualContent.objects.create(
                name=data.get('name'),
                description=data.get('description'),
                short_name=image_name[0],
                file_type=image_name[1] if len(image_name) > 1 else 'jpg',
                css_class='product-image',
                product=product
            )
            
            return JsonResponse({'success': True, 'product_id': product.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def update_product_api(request, product_id):
    if request.method == 'PUT':
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # Store original values to check for changes
            original_price = product.price
            original_quantity = product.quantity
            
            data = json.loads(request.body)
            
            # Update category if provided
            if 'category' in data:
                category, _ = Category.objects.get_or_create(name=data['category'])
                product.category = category
            
            # Update other fields if provided
            for field in ['name', 'description', 'feature', 'pokemon', 'location']:
                if field in data:
                    setattr(product, field, data[field])
            
            # Update numeric fields with validation
            new_price = None
            if 'price' in data:
                new_price = float(data['price'])
                product.price = new_price
            
            if 'rating' in data:
                product.rating = min(5.0, max(0.0, float(data['rating'])))

            new_quantity = None
            if 'quantity' in data:
                new_quantity = max(0, int(data['quantity']))
                product.quantity = new_quantity
            
            # ORM Query: Save the updated product
            # Equivalent SQL Query:
            # UPDATE store_product SET name=%s, description=%s, ... WHERE id=%s
            product.save()

            # Invalidate product cache
            cache.delete(f'product_detail_{product_id}')
            
            # Trigger notifications for price changes and restocks
            from .product_features import notify_price_change, notify_restock

            if 'imageName' in data:
                image_name = data['imageName'].split('.')
                
                # Find existing visual or create a new one
                visual = VisualContent.objects.filter(product=product).first()
                if visual:
                    visual.name = product.name
                    visual.description = product.description
                    visual.short_name = image_name[0]
                    visual.file_type = image_name[1] if len(image_name) > 1 else 'jpg'
                    visual.save()
                else:
                    # Create new visual if none exists
                    VisualContent.objects.create(
                        name=product.name,
                        description=product.description,
                        short_name=image_name[0],
                        file_type=image_name[1] if len(image_name) > 1 else 'jpg',
                        css_class='product-image',
                        product=product
                    )
            
            # Check for price change
            if new_price is not None and original_price != new_price:
                notify_price_change(product, original_price, new_price)
                
            # Check for restock (from 0 to positive quantity)
            if new_quantity is not None and original_quantity == 0 and new_quantity > 0:
                notify_restock(product)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def delete_product_api(request, product_id):
    if request.method == 'DELETE':
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # ORM Query: Delete product (cascades to visuals due to relationship)
            # Equivalent SQL Query:
            # DELETE FROM store_product WHERE id=%s
            product.delete()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def add_review_api(request):
    """Add a new review to a product"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'You must be logged in to write a review'
        }, status=403)
    
    # Check if user is review banned
    if request.user.is_review_banned:
        return JsonResponse({
            'success': False, 
            'error': 'Your review privileges have been suspended'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({
                'success': False, 
                'error': 'Product ID is required'
            }, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check if user can review this product (purchased it or admin)
        if not request.user.can_review_product(product_id):
            return JsonResponse({
                'success': False,
                'error': 'You can only review products you have purchased'
            }, status=403)
        
        # Validate required fields
        required_fields = ['rating', 'comment']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False, 
                    'error': f'{field.capitalize()} is required'
                }, status=400)
        
        # Create new review
        review = Review.objects.create(
            product=product,
            user=request.user,  # Use the authenticated user
            username=request.user.username,  # Set username from user object
            rating=int(data.get('rating')),
            comment=data.get('comment')
        )
        
        # Update product rating
        avg_rating = Review.objects.filter(product=product).aggregate(models.Avg('rating'))['rating__avg']
        if avg_rating:
            product.rating = avg_rating
            product.save()
        
        logger.info(f"Review added by {request.user.username} for product {product.id}")
        
        return JsonResponse({
            'success': True, 
            'review': review.to_json(),
            'product_avg_rating': product.rating
        })
    
    except Exception as e:
        logger.error(f"Error adding review: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@csrf_exempt
def update_review_api(request, review_id):
    """Update an existing review"""
    if request.method != 'PUT':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'You must be logged in to update a review'
        }, status=403)
    
    try:
        review = get_object_or_404(Review, id=review_id)
        
        # Check permissions: user must own the review or be admin/moderator
        if review.user != request.user and request.user.role not in ['admin', 'moderator']:
            logger.warning(f"Unauthorized attempt to update review by {request.user.username}")
            return JsonResponse({
                'success': False, 
                'error': 'You do not have permission to update this review'
            }, status=403)
        
        data = json.loads(request.body)
        
        # Update review fields
        if 'rating' in data:
            review.rating = int(data.get('rating'))
        
        if 'comment' in data:
            review.comment = data.get('comment')
        
        # Save the updated review
        review.save()
        
        # Update product rating
        product = review.product
        avg_rating = Review.objects.filter(product=product).aggregate(models.Avg('rating'))['rating__avg']
        if avg_rating:
            product.rating = avg_rating
            product.save()
        
        logger.info(f"Review {review_id} updated by {request.user.username}")
        
        return JsonResponse({
            'success': True, 
            'review': review.to_json(),
            'product_avg_rating': product.rating
        })
    
    except Exception as e:
        logger.error(f"Error updating review: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
def delete_review_api(request, review_id):
    """Delete a review"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False, 
            'error': 'You must be logged in to delete a review'
        }, status=403)
    
    try:
        review = get_object_or_404(Review, id=review_id)
        
        # Check permissions: user must own the review or be admin/moderator
        if review.user != request.user and request.user.role not in ['admin', 'moderator']:
            logger.warning(f"Unauthorized attempt to delete review by {request.user.username}")
            return JsonResponse({
                'success': False, 
                'error': 'You do not have permission to delete this review'
            }, status=403)
        
        # Get product before deleting review for rating update
        product = review.product
        
        # Delete the review
        review.delete()
        
        # Update product rating
        avg_rating = Review.objects.filter(product=product).aggregate(models.Avg('rating'))['rating__avg']
        if avg_rating:
            product.rating = avg_rating
        else:
            # If no reviews left, set rating to 0
            product.rating = 0
        product.save()
        
        logger.info(f"Review {review_id} deleted by {request.user.username}")
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        logger.error(f"Error deleting review: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
def _get_cart(session_id):
    """
    Get or create a cart for the given session ID
    
    # ORM Query:
    cart, created = Cart.objects.get_or_create(session_id=session_id)
    
    # Equivalent SQL:
    # SELECT * FROM store_cart WHERE session_id = %s LIMIT 1;
    # If not found:
    # INSERT INTO store_cart (session_id, created_at, updated_at) VALUES (%s, NOW(), NOW());
    """
    cart, created = Cart.objects.get_or_create(session_id=session_id)
    if created:
        logger.info(f"Created new cart for session {session_id}")
    return cart

@csrf_exempt
def get_cart(request):
    """Get the current cart items for a session"""
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    cart = _get_cart(session_id)
    
    # ORM Query: Get all cart items with product details
    # Equivalent SQL Query:
    # SELECT ci.*, p.name, p.price 
    # FROM store_cartitem ci
    # JOIN store_product p ON ci.product_id = p.id
    # WHERE ci.cart_id = %s;
    cart_items = []
    for item in cart.items.all():
        product = item.product
        cart_items.append({
            'id': item.id,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'quantity': item.quantity,
            'size': item.size,
            'subtotal': float(item.subtotal),
            'image': product.get_primary_image_name(),
            'stock_quantity': product.quantity
        })
    
    return JsonResponse({
        'cart_id': cart.id,
        'total': float(cart.total_price),
        'items': cart_items
    })

@csrf_exempt
def add_to_cart(request):
    """Add an item to the cart"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        size = data.get('size')
        
        # Validate product exists
        product = get_object_or_404(Product, id=product_id)

         # Check if product is in stock
        if product.quantity <= 0:
            return JsonResponse({
                'success': False, 
                'error': 'This product is out of stock'
            }, status=400)
        
        # Check if requested quantity is available
        if quantity > product.quantity:
            return JsonResponse({
                'success': False, 
                'error': f'Only {product.quantity} items available in stock'
            }, status=400)
        
        # Get or create cart
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        
        cart = _get_cart(session_id)
        
        # ORM Query: Get cart item if exists in cart
        # Equivalent SQL Query:
        # SELECT * FROM store_cartitem 
        # WHERE cart_id = %s AND product_id = %s AND (size = %s OR (size IS NULL AND %s IS NULL));
        existing_item = cart.items.filter(
            product=product,
            size=size
        ).first()
        
        if existing_item:
            # Check if total quantity after update will exceed stock
            if existing_item.quantity + quantity > product.quantity:
                return JsonResponse({
                    'success': False, 
                    'error': f'Cannot add {quantity} more items. Only {product.quantity - existing_item.quantity} more available'
                }, status=400)
            
            # ORM Query: Update cart item quantity
            # Equivalent SQL Query:
            # UPDATE store_cartitem SET quantity = quantity + %s WHERE id = %s;
            existing_item.quantity += quantity
            existing_item.save()
            logger.info(f"Updated cart item quantity: {existing_item.id}")
            item = existing_item
        else:
            # ORM Query: Create new cart item
            # Equivalent SQL Query:
            # INSERT INTO store_cartitem (cart_id, product_id, quantity, size, created_at) 
            # VALUES (%s, %s, %s, %s, NOW());
            item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                size=size
            )
            logger.info(f"Added new item to cart: {item.id}")
        
        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'cart_total': float(cart.total_price)
        })
    
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    if request.method != 'PUT':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        # ORM Query: Get cart item
        # Equivalent SQL Query:
        # SELECT * FROM store_cartitem WHERE id = %s;
        item = get_object_or_404(CartItem, id=item_id)
        product = item.product
        
        # Verify session owns this cart item
        session_id = request.session.session_key
        if item.cart.session_id != session_id:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        if quantity <= 0:
            # Delete item if quantity is 0 or less
            # ORM Query: Delete cart item
            # Equivalent SQL Query:
            # DELETE FROM store_cartitem WHERE id = %s;
            item.delete()
            logger.info(f"Deleted cart item: {item_id}")
        else:
            # Check if requested quantity is available in stock
            if quantity > product.quantity:
                return JsonResponse({
                    'success': False, 
                    'error': f'Only {product.quantity} items available in stock'
                }, status=400)
            
            # ORM Query: Update cart item quantity
            # Equivalent SQL Query:
            # UPDATE store_cartitem SET quantity = %s WHERE id = %s;
            item.quantity = quantity
            item.save()
            logger.info(f"Updated cart item quantity: {item_id}")
        
        cart = item.cart
        return JsonResponse({
            'success': True,
            'cart_total': float(cart.total_price)
        })
    
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
def remove_from_cart(request, item_id):
    """Remove an item from the cart"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # ORM Query: Get cart item
        # Equivalent SQL Query:
        # SELECT * FROM store_cartitem WHERE id = %s;
        item = get_object_or_404(CartItem, id=item_id)
        
        # Verify session owns this cart item
        session_id = request.session.session_key
        if item.cart.session_id != session_id:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        cart = item.cart
        
        # ORM Query: Delete cart item
        # Equivalent SQL Query:
        # DELETE FROM store_cartitem WHERE id = %s;
        item.delete()
        logger.info(f"Removed item from cart: {item_id}")
        
        return JsonResponse({
            'success': True,
            'cart_total': float(cart.total_price)
        })
    
    except Exception as e:
        logger.error(f"Error removing from cart: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
def checkout(request):
    """Process checkout and create an order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = request.session.session_key
        
        # Get the cart
        cart = _get_cart(session_id)
        
        # Verify cart has items
        if not cart.items.exists():
            return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)
        
        # Check stock levels before proceeding
        insufficient_stock = []
        for cart_item in cart.items.all():
            product = cart_item.product
            if cart_item.quantity > product.quantity:
                insufficient_stock.append({
                    'product_name': product.name,
                    'requested': cart_item.quantity,
                    'available': product.quantity
                })
        
        if insufficient_stock:
            return JsonResponse({
                'success': False, 
                'error': 'Some items have insufficient stock',
                'items': insufficient_stock
            }, status=400)
        
        # Create order
        # ORM Query: Create order
        # Equivalent SQL Query:
        # INSERT INTO store_order (session_id, full_name, email, shipping_address, total_amount, status, ..., created_at, updated_at) 
        # VALUES (%s, %s, %s, %s, %s, ... 'pending', NOW(), NOW());
        order = Order.objects.create(
            user=request.user,
            session_id=session_id,
            full_name=data.get('full_name'),
            email=data.get('email'),
            shipping_address=data.get('shipping_address'),
            total_amount=cart.total_price,
            payment_method=data.get('payment_method'),
            status='pending'
        )
        
        # Create order items for each cart item
        # ORM Query: Get all cart items
        # Equivalent SQL Query:
        # SELECT * FROM store_cartitem WHERE cart_id = %s;
        for cart_item in cart.items.all():
            # ORM Query: Create order item
            # Equivalent SQL Query:
            # INSERT INTO store_orderitem (order_id, product_name, product_id, price, quantity, size) 
            # VALUES (%s, %s, %s, %s, %s, %s);
            OrderItem.objects.create(
                order=order,
                product_name=cart_item.product.name,
                product=cart_item.product,
                price=cart_item.product.price,
                quantity=cart_item.quantity,
                size=cart_item.size
            )

            # Update product quantity
            # ORM Query: Decrease product quantity
            # Equivalent SQL Query:
            # UPDATE store_product SET quantity = quantity - %s WHERE id = %s;
            product.quantity = F('quantity') - cart_item.quantity
            product.save()
            
            # Refresh from database to get the actual value after F() operation
            product.refresh_from_db()
            logger.info(f"Updated product {product.id} quantity to {product.quantity}")
        
        # Clear the cart
        # ORM Query: Delete all cart items
        # Equivalent SQL Query:
        # DELETE FROM store_cartitem WHERE cart_id = %s;
        cart.items.all().delete()
        logger.info(f"Created order {order.id} and cleared cart")
        
        return JsonResponse({
            'success': True,
            'order_id': order.id
        })
    
    except Exception as e:
        logger.error(f"Error processing checkout: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def get_order_details_api(request, order_id):
    """
    API endpoint to get order details with prefetching for better performance.
    
    Optimizations:
    1. Order query uses select_related for user data
    2. Order items are prefetched with product data to avoid N+1 queries
    """
    try:
        # Get the requesting user
        user = request.user
        
        # Get the order with prefetched data
        order = Order.objects.select_related('user').prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product', 'product__user'))
        ).get(id=order_id)
        
        # Check if user has permission to view this order
        is_staff = user.role in ['admin', 'moderator', 'customer_service']

        # A user can view an order if they are the buyer or if they are a seller of any items in the order
        is_buyer = order.user == user
        # We avoid the N+1 query by using the prefetched items
        is_seller = any(item.product and item.product.user == user for item in order.items.all())
        
        if not (is_buyer or is_seller or is_staff):
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to view this order'
            }, status=403)
        
        # Get order items - with our prefetch, this does not trigger additional queries
        items = []
        for item in order.items.all():
            # Add seller ID to each item for filtering on the client side
            seller_id = item.product.user.id if item.product and item.product.user else None
            
            items.append({
                'id': item.id,
                'product_name': item.product_name,
                'product_id': item.product.id if item.product else None,
                'seller_id': seller_id,
                'price': float(item.price),
                'quantity': item.quantity,
                'size': item.size,
                'subtotal': float(item.price * item.quantity)
            })
        
        # Format order data
        order_data = {
            'id': order.id,
            'full_name': order.full_name,
            'email': order.email,
            'shipping_address': order.shipping_address,
            'total_amount': float(order.total_amount),
            'status': order.status,
            'payment_info': order.payment_info,
            'payment_method': order.payment_method,
            'status_display': order.get_status_display(),
            'payment_display': order.get_payment_info_display(),
            'method_display': order.get_payment_method_display(),
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': items,
            'username': order.user.username if order.user else None
        }
        
        return JsonResponse({
            'success': True,
            'order': order_data
        })
        
    except Exception as e:
        logger.error(f"Error getting order details: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def messages_view(request):
    """Display user conversations and messages"""
    user = request.user
    
    # Get all conversations for user
    conversations = Conversation.get_conversations_for_user(user)
    
    # Data to conversations
    conversation_data = []
    for conversation in conversations:
        # Get the other participant
        other_participant = conversation.participants.exclude(id=user.id).first()
        
        # Get unread messages count
        unread_count = Message.objects.filter(
            sender=other_participant,
            recipient=user,
            is_read=False,
            conversation=conversation
        ).count()
        
        # Add data to list
        conversation_data.append({
            'conversation': conversation,
            'other_user': other_participant,
            'unread_count': unread_count,
            'last_message': conversation.last_message,
        })
    
    # Sort conversations by last_message date
    conversation_data.sort(key=lambda x: x['conversation'].updated_at, reverse=True)
    
    return render(request, 'inbox.html', {
        'conversations': conversation_data
    })

@login_required
def conversation_view(request, conversation_id):
    """View conversation messages"""
    user = request.user

    # Get all conversations for user
    conversations = Conversation.get_conversations_for_user(user)
    
    # Get current conversation
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Check if user is a participant
    if not conversation.participants.filter(id=user.id).exists():
        request.session['notification'] = {
            'type': 'error',
            'message': 'You do not have permission to view this conversation'
        }
        return redirect('messages')

    # Get other participant
    other_user = conversation.participants.exclude(id=user.id).first()
    
    # Get messages
    messages = Message.objects.filter(conversation=conversation).order_by('created_at')
    
    # Mark all messages from other user as read
    Message.objects.filter(conversation=conversation, sender=other_user, recipient=user, is_read=False).update(is_read=True)
    
    # Handle new message submission
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if content:
            # Create new message
            message = Message.objects.create(
                sender=user,
                recipient=other_user,
                content=content,
                conversation=conversation
            )
            
            # Update conversation last message
            conversation.update_last_message(message)
            
            # Create notification for recipient
            Notification.create_notification(
                user=other_user,
                message=f"New message from {user.get_full_name() or user.username}",
                notification_type='info',
                link=f"/messages/{conversation.id}/"
            )
            
            # Redirect to avoid resubmission
            return redirect('conversation', conversation_id=conversation.id)
    
    return render(request, 'conversation.html', {
        'conversation': conversation,
        'other_user': other_user,
        'messages': messages
    })

@login_required
def new_message_view(request):
    """Create a new message/conversation"""
    user = request.user
    
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        content = request.POST.get('content', '').strip()
        
        if not recipient_id or not content:
            request.session['notification'] = {
                'type': 'error',
                'message': 'Recipient and message content are required'
            }
            return redirect('new_message')
        
        try:
            # Get recipient
            recipient = User.objects.get(id=recipient_id)
            
            # Get or create conversation
            conversation = Conversation.get_or_create_conversation(user, recipient)
            
            # Create message using direct create with the FK field
            message = Message.objects.create(
                sender=user,
                recipient=recipient,
                content=content,
                conversation=conversation
            )
            
            # Update conversation last message
            conversation.update_last_message(message)
            
            # Create notification for recipient
            Notification.create_notification(
                user=recipient,
                message=f"New message from {user.get_full_name() or user.username}",
                notification_type='info',
                link=f"/messages/{conversation.id}/"
            )
            
            # Redirect to conversation
            request.session['notification'] = {
                'type': 'success',
                'message': 'Message sent successfully'
            }
            return redirect('conversation', conversation_id=conversation.id)
            
        except User.DoesNotExist:
            request.session['notification'] = {
                'type': 'error',
                'message': 'Recipient not found'
            }
            return redirect('new_message')
    
    # Get potential recipients (all users except current user)
    recipients = User.objects.exclude(id=user.id).order_by('username')
    
    # Check if recipient_id is provided in query params
    recipient_id = request.GET.get('recipient')
    selected_recipient = None
    
    if recipient_id:
        try:
            selected_recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            pass
    
    return render(request, 'new_message.html', {
        'recipients': recipients,
        'selected_recipient': selected_recipient
    })

@login_required
def search_users_api(request):
    """API endpoint to search users"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({
            'success': True,
            'users': []
        })
    
    # Search users by username or name
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).order_by('username')[:10]
    
    # Format results
    user_data = []
    for user in users:
        user_data.append({
            'id': user.id,
            'username': user.username,
            'name': user.get_full_name(),
            'role': user.get_role_display()
        })
    
    return JsonResponse({
        'success': True,
        'users': user_data
})

@login_required
def mark_all_read_view(request):
    """View for marking all notifications as read and redirecting back"""
    # Mark all user's unread notifications as read
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    # Add notification to session for display on the next page
    request.session['notification'] = {
        'type': 'success',
        'message': 'All notifications marked as read'
    }
    
    # Redirect back to the previous page or notifications page
    # Get the 'next' parameter from the URL or default to the notifications page
    next_url = request.GET.get('next', 'messages')
    return redirect(next_url)