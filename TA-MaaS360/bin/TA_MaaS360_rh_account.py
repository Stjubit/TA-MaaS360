
import ta_maas360_declare

from maas360_account_validation import account_validation
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'api_root_host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Host()
    ),
    field.RestField(
        'billing_id',
        required=True,
        encrypted=False,
        validator=validator.Number(
            min_val=1,
            max_val=99999999999,
        )
    ),
    field.RestField(
        'platform_id',
        required=True,
        encrypted=False,
        default=3,
        validator=validator.Number(
            min_val=1,
            max_val=100,
        )
    ),
    field.RestField(
        'app_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'app_version',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'app_access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'verify',
        required=True,
        encrypted=False,
        default='Yes',
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_maas360_account',
    model,
    config_name="ta_maas360_account"
)


class MaaS360ExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
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

    def handleCreate(self, confInfo):
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

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=MaaS360ExternalHandler,
    )
