from django import template

register = template.Library()

@register.filter
def format_approvers(approvers):
    """Format a list of approvers for display."""
    if not approvers:
        return 'Not approved yet'

    # Join the approvers with commas, and handle the last one separately
    if len(approvers) > 1:
        return ', '.join(approvers[:-1]) + ' and ' + approvers[-1]
    return approvers[0]


@register.filter
def get_full_name(user):
    """Returns the full name of a user."""
    if user:
        return user.get_full_name()
    return ''