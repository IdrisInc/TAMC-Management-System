from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



@register.filter
def in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter
def split_string(value, delimiter=','):
    """Splits a string by the given delimiter."""
    return value.split(delimiter) if value else []