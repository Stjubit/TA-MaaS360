import os
from solnlib.log import Logs
import logging

APP_NAME = __file__.split(os.path.sep)[-3]


def set_logger(log_type):
    """
    This function sets up a logger with configured log level.
    :return logger: logger object
    """
    Logs.set_context(namespace="ta_maas360", root_logger_log_file=log_type)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return logger


def get_static_url_parameters(
    device_status,
    platform,
    managed_status,
    plc_compliance,
    rule_compliance,
    app_compliance,
    pswd_compliance,
):
    """
    This function defines static URL parameters based on the
    input configuration
    """
    url_parameters = {}

    if device_status != "ALL":
        url_parameters["deviceStatus"] = device_status
    if platform != "ALL":
        url_parameters["platformName"] = platform
    if managed_status != "ALL":
        url_parameters["maas360ManagedStatus"] = managed_status
    if plc_compliance != "ALL":
        url_parameters["plcCompliance"] = plc_compliance
    if rule_compliance != "ALL":
        url_parameters["ruleCompliance"] = rule_compliance
    if app_compliance != "ALL":
        url_parameters["appCompliance"] = app_compliance
    if pswd_compliance != "ALL":
        url_parameters["pswdCompliance"] = pswd_compliance

    return url_parameters
