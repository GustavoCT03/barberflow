from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene un valor de un diccionario por clave"""
    if dictionary is None:
        return None
    return dictionary.get(key, [])