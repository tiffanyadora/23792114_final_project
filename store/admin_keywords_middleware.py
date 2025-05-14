# admin_keywords_middleware.py

from django.http import HttpResponseForbidden
import json
import logging

logger = logging.getLogger(__name__)

class AdminKeywordsMiddleware:
    """Middleware to ensure only admins can modify product keywords"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Continue with regular processing for most requests
        return self.get_response(request)
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view to check for keyword access"""
        # Only check PUT and POST requests to product APIs
        if request.method not in ['POST', 'PUT']:
            return None
            
        # Check if this is a product API endpoint
        if hasattr(view_func, '__name__') and view_func.__name__ in ['add_product_api', 'update_product_api']:
            try:
                # Ensure the user is not trying to set keywords unless they're an admin
                if not request.user.is_superuser:
                    # Parse the request body
                    try:
                        body = json.loads(request.body)
                    except json.JSONDecodeError:
                        # If not valid JSON, let the view handle it
                        return None
                        
                    # Check if keywords field is being set
                    if 'keywords' in body:
                        logger.warning(f"Non-admin user {request.user.username} attempted to modify product keywords")
                        return HttpResponseForbidden("Only administrators can set product keywords")
            except Exception as e:
                # Log the error but don't block the request
                logger.error(f"Error in AdminKeywordsMiddleware: {str(e)}")
                
        # Allow the request to continue
        return None