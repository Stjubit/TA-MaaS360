from maas360_account_validation import account_validation
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


class MaaS360ExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):  # noqa: N802,N803
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):  # noqa: N802,N803
        account_validation(
            self.payload.get("api_root_host"),
            self.payload.get("billing_id"),
            self.payload.get("platform_id"),
            self.payload.get("app_id"),
            self.payload.get("app_version"),
            self.payload.get("app_access_key"),
            self.payload.get("username"),
            self.payload.get("password"),
            self.getSessionKey(),
            self.payload.get("verify"),
        )
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):  # noqa: N802,N803
        account_validation(
            self.payload.get("api_root_host"),
            self.payload.get("billing_id"),
            self.payload.get("platform_id"),
            self.payload.get("app_id"),
            self.payload.get("app_version"),
            self.payload.get("app_access_key"),
            self.payload.get("username"),
            self.payload.get("password"),
            self.getSessionKey(),
            self.payload.get("verify"),
        )
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):  # noqa: N802,N803
        AdminExternalHandler.handleRemove(self, confInfo)
