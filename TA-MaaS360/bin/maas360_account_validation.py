#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module validates MaaS360 account configuration being saved by the user
"""

import ta_maas360_declare  # noqa: F401 # isort: skip

import traceback
import requests
import maas360_utils
from maas360_handler import Maas360Handler

from splunktaucclib.rest_handler.error import RestError


def account_validation(
    api_root_host,
    billing_id,
    platform_id,
    app_id,
    app_version,
    app_access_key,
    username,
    password,
    session_key,
    verify="Yes",
):
    """
    This method verifies the credentials by making an API call
    """
    # first set up logger
    logger = maas360_utils.set_logger("account_validation")
    logger.info(
        "Verifying MaaS360 account credentials with billing ID {}".format(billing_id)
    )

    if not api_root_host or not billing_id or not platform_id or not app_id or not app_version or not app_access_key or not username or not password or not session_key or not verify:
        logger.critical("Invalid MaaS360 account configuration. You have to enter all required arguments!")
        raise RestError(
            400,
            "You have to provide all necessary arguments!"
        )
    
    # initialize MaaS360 handler
    maas360_handler = Maas360Handler(logger, api_root_host, billing_id, platform_id, app_id, app_version, app_access_key, username, password, verify)
    
    # try to authenticate
    auth_success = maas360_handler.auth()

    if auth_success is False:
        logger.critical("Unable to authenticate to MaaS360 API with provided account configuration.")
        raise RestError(400, "Unable to authenticate to MaaS360 API - please check the account configuration!")
