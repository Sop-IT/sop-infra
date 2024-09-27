from dcim.models import Site


def get_object_or_create(model, site: Site) -> object | None:
    '''
    get the model object or create it
    (for dcim/site extra models)
    '''
    if model is None:
        return None
    target = model.objects.filter(site=site)
    if target.exists():
        return target.first()
    target = model(site=site)
    target.save()
    return target
