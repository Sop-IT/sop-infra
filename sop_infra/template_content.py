from django.conf import settings

from netbox.plugins import PluginTemplateExtension

from sop_infra.models import SopInfra


ALLOWED_PANELS = ['meraki', 'classification', 'sizing']


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
        self.extensions = self.get_dashboard_config()


    def get_display_position(self, panel):

        position = self.settings.get('display_default')
        custom = self.settings.get('display_custom')

        if custom is None:
            return position

        if exists := custom.get(panel):
            return custom.get(panel)

        return position


    def get_html_panel(self, panel):

        return self.template_name.format(panel)


    def get_dashboard_config(self):

        extensions = []
        panels = self.settings.get('panels')

        if panels is None:
            return None

        for panel in panels:

            if panel not in ['meraki', 'classification', 'sizing']:
                print('WARNING:  only select panels between', ALLOWED_PANELS)
                continue

            display = self.get_display_position(panel)
            new_class = type(
                f'{panel}_SopInfra_dash_extension',
                (PluginTemplateExtension,), {
                    'model': self.model,
                    'what': self.get_html_panel(panel),
                    display: create_new_panel
                }
            )
            extensions.append(new_class)

        return extensions


    def push(self):
        return self.extensions


template_extensions = SopInfraDashboard().push()

