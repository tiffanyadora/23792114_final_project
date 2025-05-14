from django import template

register = template.Library()

@register.filter
def get_html(visual):
    return visual.get_html()