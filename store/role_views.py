from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Avg
from django.utils import timezone
from .models import User, Product, Order, OrderItem, Review, Notification, Message, Conversation
from .permissions import admin_required
from .auth_middleware import RoleMiddleware
import logging
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)

def paginate_queryset(queryset, page_number, items_per_page=8):
    paginator = Paginator(queryset, items_per_page)
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)

@login_required
@admin_required
def admin_tools(request):
    """Admin tools dashboard with user management"""
    if request.user.role != 'admin':
        logger.warning(f"Unauthorized access attempt to admin tools by user {request.user.username}")
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get all users for management
    users = User.objects.exclude(id=request.user.id).order_by('username')
    
    # Get all products
    products = Product.objects.all().order_by('-created_at')
    
    # Get all orders
    orders = Order.objects.all().order_by('-created_at')
    
    # Get all reviews
    reviews = Review.objects.all().order_by('-created_at')
    
    # Get categories
    categories = Product.objects.values_list('category__name', flat=True).distinct()
    
    return render(request, 'admin_tools.html', {
        'users': users,
        'products': products,
        'orders': orders,
        'reviews': reviews,
        'categories': categories,
        'role_choices': User.ROLE_CHOICES
    })

@login_required
def moderator_dashboard(request):
    """Moderator dashboard for content management"""
    if request.user.role not in ['admin', 'moderator']:
        logger.warning(f"Unauthorized access attempt to moderator dashboard by user {request.user.username}")
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get reviews for moderation
    reviews = Review.objects.all().select_related('product', 'user').order_by('-created_at')
    
    # Get users who can be review-banned
    users_with_reviews = User.objects.filter(reviews__isnull=False).distinct()
    
    # Get products that can be unlisted
    listed_products = Product.objects.filter(is_listed=True)
    unlisted_products = Product.objects.filter(is_listed=False)
    
    # Apply filtering
    review_filter = request.GET.get('review_filter')
    if review_filter == 'low_rated':
        reviews = reviews.filter(rating__lte=2)
    elif review_filter == 'high_rated':
        reviews = reviews.filter(rating__gte=4)
    
    # Search functionality
    search_query = request.GET.get('search_query')
    if search_query:
        reviews = reviews.filter(
            Q(comment__icontains=search_query) | 
            Q(product__name__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    
    return render(request, 'moderator_dashboard.html', {
        'reviews': reviews,
        'users_with_reviews': users_with_reviews,
        'listed_products': listed_products,
        'unlisted_products': unlisted_products,
        'review_filter': review_filter,
        'search_query': search_query
    })

@login_required
def customer_service_dashboard(request):
    """Customer service dashboard for order management"""
    if request.user.role not in ['admin', 'customer_service']:
        logger.warning(f"Unauthorized access attempt to customer service dashboard by user {request.user.username}")
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get all orders
    orders = Order.objects.all().order_by('-created_at')
    
    # Get users that can be assigned as sellers
    potential_sellers = User.objects.filter(role='customer')
    
    # Get all products
    products = Product.objects.all().order_by('-created_at')

    return render(request, 'customer_service_dashboard.html', {
        'orders': orders,
        'potential_sellers': potential_sellers,
        'products': products
    })

@login_required
def seller_dashboard(request):
    """Seller dashboard for product and order management"""
    if request.user.role not in ['admin', 'seller']:
        logger.warning(f"Unauthorized access attempt to seller dashboard by user {request.user.username}")
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get categories
    categories = Product.objects.values_list('category__name', flat=True).distinct()
    
    # Get seller's products
    seller_products = Product.objects.filter(user=request.user)
    
    # Get orders for seller's products
    seller_orders = Order.objects.filter(
        items__product__user=request.user
    ).distinct().order_by('-created_at')
    
    # Add sorting
    sort_by = request.GET.get('sort', 'date')
    if sort_by == 'fulfilled':
        seller_orders = seller_orders.filter(status='fulfilled')
    elif sort_by == 'cancelled':
        seller_orders = seller_orders.filter(status='cancelled')
    elif sort_by == 'pending':
        seller_orders = seller_orders.filter(status='pending')
    elif sort_by == 'item':
        # Sort by product name
        seller_orders = seller_orders.order_by('items__product_name')
    
    # Get customers who bought seller's products for messaging
    customers = User.objects.filter(
        orders__items__product__user=request.user
    ).distinct()
    
    return render(request, 'seller_dashboard.html', {
        'categories': categories,
        'products': seller_products,
        'orders': seller_orders,
        'customers': customers,
        'sort_by': sort_by
    })

@login_required
def user_orders(request):
    """View for regular users to see their orders"""
    user = request.user
    
    # Get user's orders
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Separate current and past orders
    current_orders = orders.filter(status__in=['pending'])
    past_orders = orders.filter(status__in=['fulfilled', 'cancelled'])
    
    return render(request, 'user_orders.html', {
        'current_orders': current_orders,
        'past_orders': past_orders
    })

def add_order_template_properties(order):
    """
    Add properties to the order object needed by the template
    This is a helper function to avoid modifying your Order model directly
    """
    from datetime import timedelta
    
    # Subtotal calculation
    subtotal = sum(item.subtotal for item in order.items.all())
    order.subtotal = subtotal
    
    # Tax and shipping calculation
    order.tax = round(order.total_amount * Decimal('0.08'), 2)  # 8% tax
    order.shipping_cost = round(order.total_amount - subtotal - order.tax, 2)
    
    # Status-related dates
    if order.status == 'fulfilled':
        # we'll just estimate the delivery 5 days after last update
        order.estimated_delivery = order.updated_at + timedelta(days=5)
    elif order.status == 'pending':
        # we'll just estimate the delivery 7 days after order creation
        order.estimated_delivery = order.created_at + timedelta(days=7)
    
    # Helper for template conditions
    order.is_completed = order.status in ['fulfilled', 'cancelled']
    
    if not hasattr(order, 'get_status_display'):
        order.get_status_display = lambda: dict(Order.ORDER_STATUS).get(order.status, order.status)
    
@login_required
def order_detail(request, order_id):
    """
    Display detailed information about a specific order
    """
    # Get the order and verify it belongs to the current user
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Optional: Get customer service user for contact link
    try:
        customer_service_user = User.objects.get(is_staff=True, username='customer_service')
    except User.DoesNotExist:
        customer_service_user = None
    
    # Add properties needed by the template
    add_order_template_properties(order)
    
    context = {
        'order': order,
        'customer_service_user': customer_service_user,
    }
    
    return render(request, 'order_detail.html', context)

# Admin actions
@login_required
@require_POST
def update_user_role(request):
    """Update user role (admin only)"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    new_role = request.POST.get('role')
    
    if user_id and new_role in dict(User.ROLE_CHOICES):
        try:
            user = User.objects.get(id=user_id)
            user.role = new_role
            
            # Update staff status based on role
            if new_role in ['admin', 'moderator']:
                user.is_staff = True
            else:
                user.is_staff = False
            
            # Update superuser status for admins
            user.is_superuser = (new_role == 'admin')
            
            user.save()
            
            logger.info(f"User {user.username} role updated to {new_role} by {request.user.username}")
            return JsonResponse({'success': True, 'message': f'User role updated to {new_role}'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid parameters'}, status=400)

# Moderator actions
@login_required
@require_POST
def toggle_review_ban(request):
    """Toggle review ban for a user (moderator only)"""
    if request.user.role not in ['admin', 'moderator']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    
    try:
        user = User.objects.get(id=user_id)
        user.is_review_banned = not user.is_review_banned
        user.save()
        
        action = "banned" if user.is_review_banned else "unbanned"
        logger.info(f"User {user.username} review {action} by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'User review {action}',
            'is_banned': user.is_review_banned
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

@login_required
@require_POST
def toggle_review_ban(request):
    """Toggle review ban for a user (moderator/admin only)"""
    if request.user.role not in ['admin', 'moderator']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    
    try:
        user = User.objects.get(id=user_id)
        user.is_review_banned = not user.is_review_banned
        user.save()
        
        action = "banned from writing reviews" if user.is_review_banned else "review ban lifted"
        logger.info(f"User {user.username} {action} by {request.user.username}")
        
        # Create notification for the user
        Notification.create_notification(
            user=user,
            message=f"You have been {action} by a moderator",
            notification_type='warning' if user.is_review_banned else 'info'
        )
        
        messages.success(request, f"User {user.username} has been {action}")
        
        return JsonResponse({
            'success': True,
            'message': f'User {action}',
            'is_banned': user.is_review_banned
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

@login_required
@require_POST
def delete_review_by_moderator(request):
    """Delete a review (moderator/admin only))"""
    if request.user.role not in ['admin', 'moderator']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    review_id = request.POST.get('review_id')
    
    try:
        review = get_object_or_404(Review, id=review_id)
        product = review.product
        user = review.user
        
        # Record the review details for notifications before deleting
        product_name = product.name
        
        # Delete the review
        review.delete()
        
        # Update product rating
        avg_rating = Review.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg']
        if avg_rating:
            product.rating = avg_rating
        else:
            # If no reviews left, set rating to 0
            product.rating = 0
        product.save()
        
        # Create notification for the review author
        Notification.create_notification(
            user=user,
            message=f"Your review for {product_name} has been removed by a moderator",
            notification_type='warning'
        )
        
        logger.info(f"Review {review_id} deleted by moderator {request.user.username}")
        messages.success(request, "Review deleted successfully")
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error deleting review by moderator: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@login_required
@require_POST
def toggle_product_listing(request):
    """Toggle product listing status (moderator/CS/Sellers)"""
    if request.user.role not in ['admin', 'moderator', 'customer_service', 'seller']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    product_id = request.POST.get('product_id')
    
    try:
        product = Product.objects.get(id=product_id)
        product.is_listed = not product.is_listed
        product.save()
        
        action = "listed" if product.is_listed else "unlisted"
        logger.info(f"Product {product.name} {action} by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Product {action}',
            'is_listed': product.is_listed
        })
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)

# Customer Service actions
@login_required
@require_POST
def cancel_order(request):
    """Cancel an order (CS only)"""
    if request.user.role not in ['admin', 'customer_service', 'seller']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    order_id = request.POST.get('order_id')
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Check if seller can cancel
        if request.user.role == 'seller':
            if not order.items.filter(product__user=request.user).exists():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        if order.status in ['cancelled']:
            return JsonResponse({'success': False, 'error': 'Cannot cancel this order'}, status=400)
        
        order.status = 'cancelled'
        order.save()
        
        # Restore product quantities
        for item in order.items.all():
            if item.product:
                item.product.quantity += item.quantity
                item.product.save()
        
        # Notify user
        Notification.create_notification(
            user=order.user,
            message=f"Your order #{order.id} has been cancelled",
            notification_type='warning',
            link=f"/my-orders/order/{order.id}/"
        )
        
        logger.info(f"Order {order.id} cancelled by {request.user.username}")
        return JsonResponse({'success': True, 'message': 'Order cancelled'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)

@login_required
@require_POST
def refund_order(request):
    """Refund an order (CS only)"""
    if request.user.role not in ['admin', 'customer_service']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    order_id = request.POST.get('order_id')
    
    try:
        order = Order.objects.get(id=order_id)
        
        if order.payment_info == 'refunded':
            return JsonResponse({'success': False, 'error': 'Order is already refunded'}, status=400)
        
        order.payment_info = 'refunded'
        order.save()
        
        # Notify user
        Notification.create_notification(
            user=order.user,
            message=f"Your order #{order.id} has been refunded",
            notification_type='info',
            link=f"/my-orders/order/{order.id}/"
        )
        
        logger.info(f"Order {order.id} refunded by {request.user.username}")
        return JsonResponse({'success': True, 'message': 'Order refunded'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)

@login_required
@require_POST
def assign_seller_role(request):
    """Assign seller role to a user (CS only)"""
    if request.user.role not in ['admin', 'customer_service']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    user_id = request.POST.get('user_id')
    
    try:
        user = User.objects.get(id=user_id)
        
        if user.role != 'customer':
            return JsonResponse({'success': False, 'error': 'User is not a customer'}, status=400)
        
        user.role = 'seller'
        user.save()
        
        logger.info(f"User {user.username} assigned seller role by {request.user.username}")
        return JsonResponse({'success': True, 'message': 'User assigned as seller'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

# Seller actions
@login_required
@require_POST
def fulfill_order(request):
    """Fulfill an order (seller and admin only)"""
    if request.user.role not in ['admin', 'seller']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    order_id = request.POST.get('order_id')
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Check if seller owns products in this order (skip for admin)
        if request.user.role != 'admin' and not order.items.filter(product__user=request.user).exists():
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        if order.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Order cannot be fulfilled'}, status=400)
        
        order.status = 'fulfilled'
        order.payment_info = 'paid'
        order.save()
        
        # Notify user
        Notification.create_notification(
            user=order.user,
            message=f"Your order #{order.id} is fulfilled!",
            notification_type='info',
            link=f"/my-orders/order/{order.id}/"
        )
        
        logger.info(f"Order {order.id} fulfilled by seller {request.user.username}")
        return JsonResponse({'success': True, 'message': 'Order fulfilled'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)