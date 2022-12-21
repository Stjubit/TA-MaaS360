# encoding = utf-8

import json
from maas360_handler import Maas360Handler
from maas360_utils import get_static_url_parameters
from splunktaucclib.rest_handler.error import RestError


CHECK_POINT_KEY = "maas360_device_input_checkpoint"


def validate_input(helper, definition):
    # fetch input configuration
    maas360_account = definition.parameters.get("maas360_account", None)
    device_status = definition.parameters.get("device_status", None)
    platform = definition.parameters.get("platform", None)
    managed_status = definition.parameters.get("managed_status", None)
    plc_compliance = definition.parameters.get("plc_compliance", None)
    rule_compliance = definition.parameters.get("rule_compliance", None)
    app_compliance = definition.parameters.get("app_compliance", None)
    pswd_compliance = definition.parameters.get("pswd_compliance", None)

    # validate input
    if (
        not maas360_account
        or not device_status
        or not platform
        or not managed_status
        or not plc_compliance
        or not rule_compliance
        or not app_compliance
        or not pswd_compliance
    ):
        raise RestError(400, "You have to provide all necessary arguments!")

    return True


def collect_events(helper, ew):
    # set up logging
    helper.set_log_level(helper.get_log_level())

    # fetch input configuration
    maas360_account = helper.get_arg("maas360_account")
    device_status = helper.get_arg("device_status")
    platform = helper.get_arg("platform")
    managed_status = helper.get_arg("managed_status")
    plc_compliance = helper.get_arg("plc_compliance")
    rule_compliance = helper.get_arg("rule_compliance")
    app_compliance = helper.get_arg("app_compliance")
    pswd_compliance = helper.get_arg("pswd_compliance")

    # initialize MaaS360 handler
    maas360_handler = Maas360Handler(
        helper.logger,
        maas360_account["api_root_host"],
        maas360_account["billing_id"],
        maas360_account["platform_id"],
        maas360_account["app_id"],
        maas360_account["app_version"],
        maas360_account["app_access_key"],
        maas360_account["username"],
        maas360_account["password"],
        maas360_account["verify"],
    )

    # fetch last reported after timestamp from checkpoint
    last_reported_after = helper.get_check_point(CHECK_POINT_KEY)

    # set last reported after timestamp to 0 on first run to fetch all devices
    if last_reported_after is None:
        helper.log_info("First run of MaaS360 device input: fetching ALL devices!")
        last_reported_after = 0
    else:
        helper.log_info(
            "Fetching devices last reported after {}".format(last_reported_after)
        )

    # initialize next last reported after timestamp
    # this will be set to the last reported time of the last device fetched
    next_last_reported_after = last_reported_after

    # set up static URL parameters
    static_url_parameters = get_static_url_parameters(
        device_status,
        platform,
        managed_status,
        plc_compliance,
        rule_compliance,
        app_compliance,
        pswd_compliance,
    )

    # initialize pagination and sorting
    page_number = 1
    page_size = 250
    sort_attribute = "lastReported"
    sort_order = "asc"

    while page_size != 0:
        # set up URL parameters for request with pagination
        url_parameters = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "sortAttribute": sort_attribute,
            "sortOrder": sort_order,
            "lastReportedAfterInEpochms": last_reported_after,
        }

        # add static URL parameters
        url_parameters.update(static_url_parameters)
        helper.log_debug(
            "URL parameters provided to Device API: {}".format(url_parameters)
        )

        # send request to API
        device_response = maas360_handler.request(
            "GET",
            "/device-apis/devices/2.0/search/customer/{}".format(
                maas360_handler.billing_id
            ),
            params=url_parameters,
        )

        # check status code
        if device_response.ok is False:
            helper.log_critical(
                "Unable to fetch MaaS360 devices from API. Received status code {}: {}".format(
                    device_response.status_code, device_response.text
                )
            )
            break

        # validate response data
        device_data = device_response.json()
        if ("devices" in device_data) and ("pageSize" in device_data["devices"]):
            # modify pagination values
            page_size = device_data["devices"]["pageSize"]
            page_number = page_number + 1

            if page_size > 0 and page_size < 250:
                # page size has to be 25, 50, 100, 200 or 250
                page_size = 250

            if page_size > 0:
                # write devices to index
                for device in device_data["devices"]["device"]:
                    # calculate timestamp in seconds
                    last_reported_time = device["lastReportedInEpochms"] / 1000

                    # prepare event and store it in index
                    event = helper.new_event(
                        data=json.dumps(device),
                        time=last_reported_time,
                        index=helper.get_output_index(),
                        source=helper.get_input_type(),
                        sourcetype=helper.get_sourcetype(),
                        done=True,
                        unbroken=True,
                    )
                    ew.write_event(event)

                # set last reported after timestamp to last reported timestamp of last device retrieved
                next_last_reported_after = device_data["devices"]["device"][-1][
                    "lastReportedInEpochms"
                ]
        else:
            helper.log_critical(
                "Received unexpected API response. Check the input and account configuration! Response: {}".format(
                    device_data
                )
            )
            return

    # update checkpoint with new last reported after timestamp
    helper.log_info(
        "Saving new last reported after timestamp in checkpoint: {}".format(
            next_last_reported_after
        )
    )
    helper.save_check_point(CHECK_POINT_KEY, next_last_reported_after)

    helper.log_info("Done fetching MaaS360 devices!")
