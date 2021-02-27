from django import template
from matcher.models import MatchColor

register = template.Library()


@register.filter(name='is_green')
def is_green(color: MatchColor) -> bool:
    return color == MatchColor.GREEN


@register.filter(name='is_yellow')
def is_green(color: MatchColor) -> bool:
    return color == MatchColor.YELLOW


@register.filter(name='is_red')
def is_green(color: MatchColor) -> bool:
    return color == MatchColor.RED
