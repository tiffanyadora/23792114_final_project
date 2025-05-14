from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Global dictionary to store password reset attempts based on IP
# Format: {ip_address: {'count': 0, 'first_attempt': timestamp}}
ip_reset_attempts = {}

class PasswordResetRateLimitMiddleware:
    """
    Middleware to track and limit password reset requests by IP address
    This helps prevent brute force attacks and abuse of the password reset system
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process password reset requests
        if request.path == '/password-reset/' and request.method == 'POST':
            client_ip = self.get_client_ip(request)
            current_time = timezone.now()
            
            # Initialize IP tracking if not exists
            if client_ip not in ip_reset_attempts:
                ip_reset_attempts[client_ip] = {
                    'count': 0,
                    'first_attempt': current_time
                }
            
            # Reset IP counter if it's been more than an hour
            if (current_time - ip_reset_attempts[client_ip]['first_attempt']).total_seconds() > 3600:
                ip_reset_attempts[client_ip] = {
                    'count': 0,
                    'first_attempt': current_time
                }
            
            # Increment counter for this IP
            ip_reset_attempts[client_ip]['count'] += 1
            
            # Log excessive attempts
            if ip_reset_attempts[client_ip]['count'] > 3:
                logger.warning(
                    f"IP {client_ip} has exceeded password reset rate limit with "
                    f"{ip_reset_attempts[client_ip]['count']} attempts in the last hour."
                )
        
        # Clean up old IP entries every hour
        self.cleanup_ip_tracking()
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def cleanup_ip_tracking(self):
        """Clean up old IP entries to prevent memory leaks"""
        current_time = timezone.now()
        ips_to_remove = []
        
        for ip, data in ip_reset_attempts.items():
            # Remove entries older than 2 hours
            if (current_time - data['first_attempt']).total_seconds() > 7200:
                ips_to_remove.append(ip)
        
        for ip in ips_to_remove:
            del ip_reset_attempts[ip]

def get_password_reset_attempts_for_ip(ip_address):
    """
    Get the number of password reset attempts for an IP address
    This can be used in views to enforce rate limiting
    """
    if ip_address in ip_reset_attempts:
        current_time = timezone.now()
        data = ip_reset_attempts[ip_address]
        
        # Check if the tracking has expired
        if (current_time - data['first_attempt']).total_seconds() > 3600:
            return 0
        
        return data['count']
    
    return 0