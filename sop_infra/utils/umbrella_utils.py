from dcim.models import Site, SiteGroup

class SopUmbrellaUtils:

    __parsed: bool = False
    __umbrella_api_keys: dict[str, str] = {}

    @classmethod
    def try_parse_configuration(cls):
        # parse all configuration.py informations
        from django.conf import settings

        infra_config = settings.PLUGINS_CONFIG.get("sop_infra")
        if infra_config is None:
            raise Exception("No sop_infra in .PLUGINS_CONFIG !")
        sopumbrella_config = infra_config.get("umbrella")
        if sopumbrella_config is None:
            raise Exception("No umbrella section in sop_infra PLUGINS_CONFIG key !")
        cls.__umbrella_api_keys = sopumbrella_config.get("api_keys")
        if cls.__umbrella_api_keys is None:
            raise Exception("No umbrella/api_keys plugin config key !")
        cls.__parsed = True

    @classmethod
    def get_legacy_api_key_for_dash_name(cls, name: str) -> dict[str,str]:
        return cls.get_api_key_for_dash_name(name, "LEGACY_DEVICES")
    
    @classmethod
    def get_ro_api_key_for_dash_name(cls, name: str) -> dict[str,str]:
        return cls.get_api_key_for_dash_name(name, "RO")

    @classmethod
    def get_rw_api_key_for_dash_name(cls, name: str) -> dict[str,str]:
        return cls.get_api_key_for_dash_name(name, "RW")

    @classmethod
    def get_api_key_for_dash_name(cls, name: str, type: str) -> dict[str,str]:
        if not cls.__parsed:
            cls.try_parse_configuration()
        keys: dict[str, str] = cls.__umbrella_api_keys.get(name)  # type: ignore
        if keys is None:
            raise Exception(f"No keys for dashboard '{name}'")
        return keys.get(type, "")

    @staticmethod
    def get_umbrella_excluded_domains(site:Site) -> list[str]:
        return SopUmbrellaUtils.get_umbrella_excluded_domains_group(site.group)

    @staticmethod
    def get_umbrella_excluded_domains_group(g:SiteGroup) -> list[str]:
        if g is None:
            return None
        cur=g.custom_field_data.get('umbrella_internal_domains') 
        par=None
        if g.parent is not None:
            par=SopUmbrellaUtils.get_umbrella_excluded_domains_group(g.parent)
        if cur is None and par is None:
            return None
        ret=[]
        if cur is not None:
            ret.extend(cur.split('\r\n'))
        if par is not None:
            ret.extend(par)
        return ret
