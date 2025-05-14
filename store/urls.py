from django.urls import path
from . import views
from . import api_views
from . import auth_views
from . import role_views
from . import subscription_api

urlpatterns = [
    path('', views.home, name='home'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/', views.product_detail, name='product_detail_legacy'), # This is legacy   
    path('search/', views.search, name='search'),

    # Product subscription endpoints
    path('api/product-subscription/subscribe/', subscription_api.subscribe_product, name='subscribe_product'),
    path('api/product-subscription/unsubscribe/', subscription_api.unsubscribe_product, name='unsubscribe_product'),
    path('api/product-subscription/<int:product_id>/check/', subscription_api.check_subscription, name='check_subscription'),
    path('api/subscriptions/', subscription_api.get_subscriptions, name='get_subscriptions'),
    
    # CRUD API endpoints - Products & Reviews
    path('api/products/add/', views.add_product_api, name='add_product_api'),
    path('api/products/<int:product_id>/update/', views.update_product_api, name='update_product_api'),
    path('api/products/<int:product_id>/delete/', views.delete_product_api, name='delete_product_api'),
    path('api/reviews/add/', views.add_review_api, name='add_review_api'),
    path('api/reviews/<int:review_id>/update/', views.update_review_api, name='update_review_api'),
    path('api/reviews/<int:review_id>/delete/', views.delete_review_api, name='delete_review_api'),
    path('api/reviews/can-review/<int:product_id>/', api_views.check_review_eligibility, name='check_review_eligibility'),
    
    # Product details API endpoints
    path('api/products/', api_views.api_products, name='api_products'),
    path('api/products/<str:product_id>/', api_views.api_product_detail, name='api_product_detail'),
    path('api/pokemon/<str:pokemon_name>/', api_views.api_pokemon_data, name='api_pokemon_data'),
    path('api/weather/<str:city_name>/', api_views.api_weather_data, name='api_weather_data'),

    # CRUD API endpoints - Cart
    path('api/cart/', views.get_cart, name='get_cart'),
    path('api/cart/add/', views.add_to_cart, name='add_to_cart'),
    path('api/cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('api/cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('api/checkout/', views.checkout, name='checkout'),

    # Authentication views
    path('register/', auth_views.register, name='register'),
    path('login/', auth_views.user_login, name='login'),
    path('logout/', auth_views.user_logout, name='logout'),
    path('terms/', auth_views.terms_view, name='terms'),
    
    # Password reset
    path('password-reset/', auth_views.password_reset_request, name='password_reset'),
    path('password-reset/sent/', auth_views.password_request_sent, name='password_request_sent'),
    path('password-reset/confirm/<str:token>/', auth_views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.password_reset_done, name='password_reset_done'),
    
    # Email verification
    path('verify-email/<str:token>/', auth_views.verify_email, name='verify_email'),
    path('email-verification-needed/', auth_views.email_verification_needed, name='email_verification_needed'),
    path('resend-verification-email/', auth_views.resend_verification_email, name='resend_verification_email'),
    
    # User profile
    path('profile/', auth_views.user_profile, name='profile'),
    path('check-username/', auth_views.check_username_availability, name='check_username'),
    path('check-email/', auth_views.check_email_availability, name='check_email'),
    
    # Role-based dashboards
    path('admin-tools/', role_views.admin_tools, name='admin_tools'),
    path('moderator-dashboard/', role_views.moderator_dashboard, name='moderator_dashboard'),
    path('customer-service-dashboard/', role_views.customer_service_dashboard, name='customer_service_dashboard'),
    path('seller-dashboard/', role_views.seller_dashboard, name='seller_dashboard'),

    # Order API endpoints
    path('my-orders/', role_views.user_orders, name='user_orders'),
    path('my-orders/order/<int:order_id>/', role_views.order_detail, name='order_detail'),

    # Role-based actions
    path('update-user-role/', role_views.update_user_role, name='update_user_role'),
    path('toggle-review-ban/', role_views.toggle_review_ban, name='toggle_review_ban'),
    path('toggle-product-listing/', role_views.toggle_product_listing, name='toggle_product_listing'),
    path('delete-review-by-moderator/', role_views.delete_review_by_moderator, name='delete_review_by_moderator'),
    path('api/orders/<int:order_id>/', views.get_order_details_api, name='get_order_details_api'),
    path('cancel-order/', role_views.cancel_order, name='cancel_order'),
    path('refund-order/', role_views.refund_order, name='refund_order'),
    path('assign-seller-role/', role_views.assign_seller_role, name='assign_seller_role'),
    path('fulfill-order/', role_views.fulfill_order, name='fulfill_order'),

    # For the notification API
    path('api/notifications/', api_views.get_notifications, name='get_notifications'),
    path('api/notifications/check/', api_views.check_notifications, name='check_notifications'),
    path('api/notifications/<int:notification_id>/mark-read/', api_views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', api_views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notification-settings/update/', api_views.update_notification_settings, name='update_notification_settings'),

    # For notification views
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),

    # Message URLs
    path('messages/', views.messages_view, name='messages'),
    path('messages/<int:conversation_id>/', views.conversation_view, name='conversation'),
    path('messages/new/', views.new_message_view, name='new_message'),

    # Message API endpoints
    path('api/users/search/', views.search_users_api, name='search_users_api'),
    
]