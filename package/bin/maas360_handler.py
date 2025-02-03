import requests

"""
MaaS360 Request Handler Class
"""


class Maas360Handler:
    def __init__(
        self,
        logger,
        api_root_host,
        billing_id,
        platform_id,
        app_id,
        app_version,
        app_access_key,
        username,
        password,
        verify=True,
    ):
        self.api_root_host = api_root_host
        self.billing_id = billing_id
        self.platform_id = platform_id
        self.app_id = app_id
        self.app_version = app_version
        self.app_access_key = app_access_key
        self.username = username
        self.password = password
        self.verify = verify
        self.logger = logger

        self.session = requests.Session()
        self.session.verify = verify == "Yes"
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "application/json"

    def auth(self) -> bool:
        self.logger.info("Authenticating MaaS360 API client")

        # construct auth data
        auth_data = {
            "authRequest": {
                "maaS360AdminAuth": {
                    "billingID": self.billing_id,
                    "platformID": self.platform_id,
                    "appID": self.app_id,
                    "appVersion": self.app_version,
                    "appAccessKey": self.app_access_key,
                    "userName": self.username,
                    "password": self.password,
                }
            }
        }

        # send auth request
        auth_response = self.request(
            "POST",
            "/auth-apis/auth/2.0/authenticate/customer/{}".format(self.billing_id),
            json=auth_data,
        )
        auth_response_data = auth_response.json()

        # validate response and set auth token in session
        auth_success = False
        if (
            auth_response.ok
            and ("authResponse" in auth_response_data)
            and ("authToken" in auth_response_data["authResponse"])
        ):
            self.session.headers["Authorization"] = 'MaaS token="{}"'.format(
                auth_response_data["authResponse"]["authToken"]
            )
            self.logger.info("Successfully authenticated MaaS360 API client")
            auth_success = True
        else:
            self.logger.critical(
                "Unable to authenticate MaaS360 API client. Please check the MaaS360 account configuration!"
            )
            self.logger.debug("Authentication Response: {}".format(auth_response_data))

        return auth_success

    def request(self, method, endpoint, **kwargs) -> requests.Response:
        # construct URL
        url = "https://{}{}".format(self.api_root_host, endpoint)

        # check if session has been authenticated already
        if ("Authorization" in self.session.headers) is False and (
            "auth-apis" in endpoint
        ) is False:
            # auth first
            self.auth()

        # send request
        api_response = self.session.request(method, url, **kwargs)

        # validate response (authentication)
        if api_response.status_code == 401:  # Forbidden
            # reauth and resend request
            self.logger.debug("Reauthenticating MaaS360 API client")
            self.auth()
            api_response = self.session.request(method, url, **kwargs)

        return api_response
