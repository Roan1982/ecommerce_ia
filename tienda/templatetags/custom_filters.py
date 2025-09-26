from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Obtiene un valor de un diccionario usando una clave variable.
    Uso: {{ dictionary|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

@register.filter
def div(value, arg):
    """
    Divide el valor por el argumento.
    Uso: {{ value|div:arg }}
    """
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0