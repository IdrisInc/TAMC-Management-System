# Create a file called 'custom_filters.py' in your Django app directory

from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg


