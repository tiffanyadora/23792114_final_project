from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Product, Category

@receiver(post_save, sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    """Invalidate product cache when a product is updated"""
    cache.delete(f'product_detail_{instance.id}')

@receiver(post_delete, sender=Product)
def invalidate_product_cache_on_delete(sender, instance, **kwargs):
    """Invalidate product cache when a product is deleted"""
    cache.delete(f'product_detail_{instance.id}')

@receiver([post_save, post_delete], sender=Category)
def invalidate_categories_cache(sender, instance, **kwargs):
    """Invalidate categories cache when a category is updated or deleted"""
    cache.delete('all_categories')