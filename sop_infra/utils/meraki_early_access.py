from meraki.api.appliance  import Appliance
import urllib 


class EarlyAccessAppliance(Appliance):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def updateUmbrellaExcludedDomains(self, networkId: str, domains:list[str], **kwargs):
        """
        **Specify one or more domain names to be excluded from being routed to Cisco Umbrella.**
        https://developer.cisco.com/meraki/api-v1/exclude-network-appliance-umbrella-domains/

        - networkId (string): network id
        - domains (list[string]) : domains to exclude
        """

        kwargs = locals()

        metadata = {
            "tags": ["appliance", "configure", "umbrella", "domains"],
            "operation": "updateUmbrellaExcludedDomains",
        }
        serial = urllib.parse.quote(str(networkId), safe="")
        resource = f"/networks/{networkId}/appliance/umbrella/excludeDomains"

        body_params = [
            "domains",
        ]
        payload = {k.strip(): v for k, v in kwargs.items() if k.strip() in body_params}

        if self._session._validate_kwargs:
            all_params = [] + body_params
            invalid = [k for k in kwargs if k.strip() not in all_params and k != "self"]
            if invalid and self._session._logger:
                self._session._logger.warning(f"updateUmbrellaExcludedDomains: ignoring unrecognized kwargs: {invalid}")
        # print(f"{resource} - {payload}")
        return self._session.put(metadata, resource, payload)
    

    def updateUmbrellaNetworkProtection(self, networkId: str, enabled: bool, **kwargs):
        """
        **Enable or disable umbrella protection for an MX network. When disabling, the umbrella property will be omitted from the response.**
        https://developer.cisco.com/meraki/api-v1/protection-network-appliance-umbrella/

        - networkId (string): network id
        - enabled (boolean) : enable or not
        """

        kwargs = locals()

        metadata = {
            "tags": ["appliance", "configure", "uplinks", "settings"],
            "operation": "updateUmbrellaNetworkProtection",
        }
        serial = urllib.parse.quote(str(networkId), safe="")
        resource = f"/networks/{networkId}/appliance/umbrella/protection"

        body_params = [
            "enabled",
        ]
        payload = {k.strip(): v for k, v in kwargs.items() if k.strip() in body_params}

        if self._session._validate_kwargs:
            all_params = [] + body_params
            invalid = [k for k in kwargs if k.strip() not in all_params and k != "self"]
            if invalid and self._session._logger:
                self._session._logger.warning(f"updateDeviceApplianceUplinksSettings: ignoring unrecognized kwargs: {invalid}")
        print(f"{kwargs} -  {resource} - {payload}")        
        return self._session.put(metadata, resource, payload)
    