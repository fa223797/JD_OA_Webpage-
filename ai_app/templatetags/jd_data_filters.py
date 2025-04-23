from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    """获取字典中的值"""
    return dictionary.get(key, {})

@register.filter
def getattr(obj, attr):
    """获取对象的属性值"""
    try:
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return '' 