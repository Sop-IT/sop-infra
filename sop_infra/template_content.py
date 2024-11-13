from netbox.plugins import PluginTemplateExtension


class SiteInfraRefreshContent(PluginTemplateExtension):

    models = ['dcim.site']

    def list_buttons(self):

        def get_extra_context():
            extra_context:dict = {}
            return extra_context

        return self.render('sop_infra/tools/refresh.html', get_extra_context())


template_extensions = [SiteInfraRefreshContent,]
