import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib import messages
from django.conf import settings

from netbox.plugins import PluginTemplateExtension
from netbox.context import current_request
from dcim.models import Site

from sop_infra.models import SopInfra



#_________SITE_POST_SAVE


@receiver(post_save, sender=Site)
def create_or_update_sopinfra(sender, instance, created, **kwargs):
    '''
    when creating or updating a Site
    create or update its related SopInfra instance
    '''
    request = current_request.get()
    target = SopInfra.objects.filter(site=instance)

    # create
    if created and not target.exists():
        infra = SopInfra.objects.create(site=instance)
        infra.full_clean()
        infra.snapshot()
        infra.save()
        try:
            messages.success(request, f'Created {infra}')
        except:pass
        return

    # update
    infra = target.first()
    infra.snapshot()
    infra.full_clean()
    infra.save()
    try:
        messages.success(request, f'Updated {infra}')
    except:pass



#_________PANELS_CONFIGURATION


ALLOWED_PANELS = ['meraki', 'classification', 'sizing']
ALLOWED_POSITIONS = ['left_page', 'right_page']


def create_new_panel(self):

    def get_extra_context() -> dict:

        qs = SopInfra.objects.filter(site=self.context['object'])
        infra = qs.first() if qs.exists() else SopInfra

        return {'infra': infra, 'what': self.what}

    return self.render(f'sop_infra/panels/panel.html', get_extra_context())


class SopInfraDashboard:

    template_name = 'sop_infra/tab/{}.html'
    # model to display dashboard on
    model = 'dcim.site'

    def __init__(self):
        self.settings = settings.PLUGINS_CONFIG.get('sop_infra', {})
        self.extensions = self.get_display_extensions()


    def get_html_panel(self, panel):

        return self.template_name.format(panel)


    def get_display_position(self, panel, display):

        if exists := display.get(panel):

            if exists not in ALLOWED_POSITIONS:
                return None

            return exists

        return None


    def get_display_extensions(self):

        extensions = []
        _display = self.settings.get('display')

        # no configuration
        if _display is None:
            return

        # error handling
        if not isinstance(_display, dict):
            logging.error(f'Invalid syntax "{_display}", must be a dict.')
            return

        for panel in _display:

            if panel not in ALLOWED_PANELS:
                logging.error(f'Invalid panel "{panel}", valid display are:', ALLOWED_PANELS)
                continue

            # return the position of {panel:position}
            position = self.get_display_position(panel, _display)

            if position is None:
                logging.error(f'Invalid position "{position}", valid positions are:', ALLOWED_POSITIONS)
                continue

            # creates dynamically a template extension class
            new_class = type(
                f'{panel}_SopInfra_panel_extension',
                (PluginTemplateExtension,), {
                    'model': self.model,
                    'what': self.get_html_panel(panel),
                    position: create_new_panel
                }
            )
            extensions.append(new_class)


        return extensions


    def push(self):
        return self.extensions



template_extensions = SopInfraDashboard().push()

