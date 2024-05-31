from django import template

register = template.Library()

@register.filter(name='get_day')
def get_day(programs, day):
    return programs[day.lower()]