from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])

@register.filter
def equals(value, arg):
    return value == arg

@register.filter
def get_nested(item, key):
    """Handles nested dict keys like 'space.room_type.name'"""
    keys = key.split('.')
    for k in keys:
        if isinstance(item, dict):
            item = item.get(k)
        else:
            item = getattr(item, k, None)
        if item is None:
            break
    return item

@register.filter
def nested_dictsort(value, arg):
    try:
        return sorted(value, key=lambda item: get_nested(item, arg))
    except Exception as e:
        return value  # fallback to unsorted if something goes wrong


@register.filter
def unique(value, field):
    seen = set()
    result = []
    for item in value:
        val = get_nested(item, field)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result
