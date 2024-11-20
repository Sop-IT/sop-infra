from django import template


__all__ = (
    'field_verbose_name',
    'field_help_text',
)


register = template.Library()


@register.filter()
def field_verbose_name(instance, field_name):
    '''
    html filter to return field verbose_name
    usage: object|field_verbose_name:"field_name"
    '''
    try:
        return instance._meta.get_field(field_name).verbose_name
    except:
        return None


@register.filter()
def field_help_text(instance, field_name):
    '''
    html filter to return field help_text if exists
    usage: object|field_help_text:"field_name"
    '''
    try:
        return instance._meta.get_field(field_name).help_text
    except:
        return None


@register.filter()
def field_value(instance, field_name):
    '''
    html filter to return field value
    usage: object|field_value:"field_name"
    '''
    try:
        maybe_method = f'get_{field_name}_display'
        if hasattr(instance, maybe_method):
            return getattr(instance, maybe_method)()

        maybe_method = f'get_{field_name}'
        if hasattr(instance, maybe_method):
            return getattr(instance, maybe_method)()

        return getattr(instance, field_name)
    except:
        return None


@register.filter()
def field_exists(instance, field_name) -> bool:
    '''
    html filter to see if object exists
    usage: object|field_exists:"field_name"
    '''
    try:
        if hasattr(instance, field_name):
            if getattr(instance, field_name) is not None:
                return True

        return False
    except:
        return False


@register.filter()
def field_help_exists(instance, field_name) -> bool:
    '''
    html filter to see if object has help_text
    usage: object|field_help_exists:"field_name"
    '''
    try:
        field = instance._meta.get_field(field_name)
        text = field.help_text
        if text:
            return True
        return False
    except:
        return False

