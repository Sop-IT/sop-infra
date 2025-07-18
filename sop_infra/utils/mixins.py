import logging
from datetime import datetime, timedelta, timezone
from utilities.exceptions import AbortScript
from users.models import User, Group
from extras.choices import LogLevelChoices


class SopBaseScriptMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raiseError = False
        self.raiseWarning = False

    def checkIsStaff(self, username=None):
        if username is None:
            try:
                username = self.request.user.username # type: ignore
            except:
                pass
        if username is None:
            raise AbortScript("---- No username found !!  ----")
        realUsers = User.objects.filter(username__exact=username)
        if realUsers is None:
            raise AbortScript("Looks like you do not exist...")
        if len(realUsers) > 1:
            raise AbortScript("Looks like you are ubiquitious...")
        realUser = realUsers[0]
        if realUser.is_staff:
            return
        raise AbortScript("---- Permission denied !!  ----")

    def checkHasPerm(self, username, groupToCheck):
        realUsers = User.objects.filter(username__exact=username)
        if realUsers is None:
            raise AbortScript("Looks like you do not exist...")
        if len(realUsers) > 1:
            raise AbortScript("Looks like you are ubiquitious...")
        realUser = realUsers[0]
        if realUser.is_staff:
            return
        lookupGroup = Group.objects.filter(name__exact=groupToCheck)
        if lookupGroup is None:
            raise AbortScript(f"---- Group {groupToCheck} not found !!  ----")
        checkGroupMembership = realUser.groups.filter(name__exact=groupToCheck)
        # self.log_info(f"values : {checkGroupMembership.values()}")
        if not (len(checkGroupMembership.values()) == 1):
            raise AbortScript("---- Permission denied !!  ----")

    def checkHasGroups(self, username, groups: list[str]):
        realUsers = User.objects.filter(username__exact=username)
        if realUsers is None:
            raise AbortScript("Looks like you do not exist...")
        if len(realUsers) > 1:
            raise AbortScript("Looks like you are ubiquitious...")
        realUser = realUsers[0]
        if realUser.is_staff:
            return
        checkGroupMembership = realUser.groups.filter(name__in=groups)
        # self.log_info(f"values : {checkGroupMembership.values()}")
        if not (len(checkGroupMembership.values()) > 0):
            raise AbortScript(
                f"---- Permission denied  : user {username} is not in groups {groups} !!  ----"
            )


class JobRunnerLogMixin:
    """
    Stripped down reimplementation from Netbox Script logging
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # init log storage
        self.messages = []  # Primary script log
        self.raiseError = False
        self.raiseWarning = False

        # Initiate the log
        self.logger = logging.getLogger(f"{__name__}")

    #
    # Logging
    #
    def _log(self, message, obj=None, level=LogLevelChoices.LOG_INFO):
        """
        Log a message. Do not call this method directly; use one of the log_* wrappers below.
        """
        if level not in LogLevelChoices.values():
            raise ValueError(f"Invalid logging level: {level}")

        if message:
            # Record to the script's log
            self.messages.append(
                {
                    "time": datetime.now().isoformat(),
                    "status": level,
                    "message": str(message),
                    "obj": str(obj) if obj else None,
                    "url": obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else None,  # type: ignore
                }
            )
            # Record to the system log
            if obj:
                message = f"{obj}: {message}"
            self.logger.log(LogLevelChoices.SYSTEM_LEVELS[level], message)

    def debug(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_DEBUG)

    def success(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_SUCCESS)

    def info(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_INFO)

    def warning(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_WARNING)

    def failure(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_FAILURE)
        self.raiseError = True

    def log_debug(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_DEBUG)

    def log_success(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_SUCCESS)

    def log_info(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_INFO)

    def log_warning(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_WARNING)

    def log_failure(self, message=None, obj=None):
        self._log(message, obj, level=LogLevelChoices.LOG_FAILURE)
        self.raiseError = True

    def get_job_data(self):
        """
        Return a dictionary of data to attach to the script's Job.
        """
        return {
            "log": self.messages,
        }

