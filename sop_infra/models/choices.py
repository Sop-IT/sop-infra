from django.utils.translation import gettext_lazy as _

from utilities.choices import ChoiceSet


__all__ = (
    "InfraBoolChoices",
    "InfraTypeChoices",
    "InfraTypeIndusChoices",
    "InfraHubOrderChoices",
    "InfraSdwanhaChoices",

    "SwitchPortModeChoices", 
    "SwitchPortAllowedVlansChoices",
    "SwitchPortBpduFilterChoices",

    "SopMerakiStpGuardChoices",
)


class InfraBoolChoices(ChoiceSet):

    CHOICES = (
        ("unknown", _("Unknown"), "gray"),
        ("true", _("True"), "green"),
        ("false", _("False"), "red"),
    )


class InfraTypeChoices(ChoiceSet):

    CHOICES = (
        ("box", _("Simple BOX server")),
        ("superb", _("Super Box")),
        ("sysclust", _("Full cluster")),
    )


class InfraTypeIndusChoices(ChoiceSet):

    CHOICES = (
        ("wrk", _("WRK - Workshop")),
        ("fac", _("FAC - Factory")),
    )


class InfraHubOrderChoices(ChoiceSet):

    CHOICES = (
        (
            "N_731271989494311779,L_3689011044769857831,N_731271989494316918,N_731271989494316919",
            "EQX-NET-COX-DDC",
        ),
        (
            "N_731271989494316918,N_731271989494316919,N_731271989494311779,L_3689011044769857831",
            "COX-DDC-EQX-NET",
        ),
        (
            "L_3689011044769857831,N_731271989494311779,N_731271989494316918,N_731271989494316919",
            "NET-EQX-COX-DDC",
        ),
        (
            "N_731271989494316919,N_731271989494316918,N_731271989494311779,L_3689011044769857831",
            "DDC-COX-EQX-NET",
        ),
    )


class InfraSdwanhaChoices(ChoiceSet):

    CHOICES = (
        ("-HA-", _("-HA-")),
        ("-NHA-", _("-NHA-")),
        ("-NO NETWORK-", _("-NO NETWORK-")),
        ("-SLAVE SITE-", _("-SLAVE SITE-")),
        ("-DC-", _("-DC-")),
    )


class SwitchPortModeChoices(ChoiceSet):

    CHOICES = (
        ("access", _("access")),
        ("trunk", _("trunk")),
    )


class SwitchPortAllowedVlansChoices(ChoiceSet):

    CHOICES = (
        ("it_vlans", _("it_vlans")),
        ("ot_vlans", _("ot_vlans")),
        ("lxc_vlans", _("lxc_vlans")),
    )


class SwitchPortBpduFilterChoices(ChoiceSet):

    CHOICES = (
        ("disabled", _("disabled")),
        ("root guard", _("root guard")),
        ("bpdu guard", _("bpdu guard")),
    )



class SopMerakiStpGuardChoices(ChoiceSet):

    CHOICES = (
        ("disabled", _("disabled")),
        ("root guard", _("root guard")),
        ("bpdu guard", _("bpdu guard")),
        ("loop guard", _("loop guard")),
    )
