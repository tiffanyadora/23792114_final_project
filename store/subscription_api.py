from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.shortcuts import get_object_or_404
from .models import Product, ProductSubscription
from .product_features import subscribe_to_product, unsubscribe_from_product
import json
import logging

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    View to guarantee that the CSRF cookie is set.
    """
    return JsonResponse({'success': True})

@login_required
@csrf_protect
@require_POST
def subscribe_product(request):
    """Subscribe to product notifications"""
    try:
        # Log the request for debugging
        logger.debug(f"Subscribe request: {request.body}")
        logger.debug(f"Headers: {request.headers}")
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from request body")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
            
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing product_id'
            }, status=400)
            
        notify_price = data.get('notify_price', True)
        notify_restock = data.get('notify_restock', True)
        
        logger.debug(f"Looking up product with ID: {product_id}")
        product = get_object_or_404(Product, id=product_id)
        
        # Check if already subscribed
        existing = ProductSubscription.objects.filter(
            user=request.user, 
            product=product
        ).first()
        
        if existing:
            return JsonResponse({
                'success': True,
                'action': 'already_subscribed',  
                'message': 'Already subscribed to this product'
            })
            
        subscription = subscribe_to_product(
            user=request.user,
            product=product,
            notify_price=notify_price,
            notify_restock=notify_restock
        )
        
        logger.debug(f"User {request.user.username} subscribed to product {product.name}")
        
        return JsonResponse({
            'success': True,
            'action': 'subscribed',
            'message': 'Subscribed to product notifications',
            'is_subscribed': True
        })
    except Exception as e:
        logger.exception(f"Error in subscribe_product: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@csrf_protect
@require_POST
def unsubscribe_product(request):
    """Unsubscribe from product notifications"""
    try:
        # Log the request for debugging
        logger.debug(f"Unsubscribe request: {request.body}")
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
            
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing product_id'
            }, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check if subscription exists
        subscription = ProductSubscription.objects.filter(
            user=request.user,
            product=product
        ).first()
        
        if not subscription:
            return JsonResponse({
                'success': True,
                'action': 'not_subscribed',
                'message': 'Not subscribed to this product'
            })
        
        unsubscribe_from_product(request.user, product)
        
        logger.debug(f"User {request.user.username} unsubscribed from product {product.name}")
        
        return JsonResponse({
            'success': True,
            'action': 'unsubscribed',
            'message': 'Unsubscribed from product notifications',
            'is_subscribed': False
        })
    except Exception as e:
        logger.exception(f"Error in unsubscribe_product: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@require_GET
@ensure_csrf_cookie
def check_subscription(request, product_id):
    """Check if user is subscribed to product"""
    if not request.user.is_authenticated:
        # Return an empty response if not logged in
        return JsonResponse({'success': False, 'is_subscribed': []}, status=200)

    try:
        product = get_object_or_404(Product, id=product_id)
        
        is_subscribed = ProductSubscription.objects.filter(
            user=request.user,
            product=product
        ).exists()
        
        return JsonResponse({
            'success': True,
            'is_subscribed': is_subscribed
        })
    except Exception as e:
        logger.exception(f"Error in check_subscription: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@ensure_csrf_cookie
def get_subscriptions(request):
    """Get user's product subscriptions"""
    try:
        subscriptions = ProductSubscription.objects.filter(
            user=request.user
        ).select_related('product')
        
        subscription_data = [{
            'id': sub.id,
            'product_id': sub.product.id,
            'product_name': sub.product.name,
            'product_price': str(sub.product.price),
            'notify_price_change': sub.notify_price_change,
            'notify_restock': sub.notify_restock,
            'created_at': sub.created_at.isoformat()
        } for sub in subscriptions]
        
        return JsonResponse({
            'success': True,
            'subscriptions': subscription_data
        })
    except Exception as e:
        logger.exception(f"Error in get_subscriptions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)