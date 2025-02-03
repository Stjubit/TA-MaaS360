import json
import ta_helper

from maas360_handler import Maas360Handler
from maas360_utils import get_static_url_parameters

from splunklib import modularinput as smi
from splunktaucclib.rest_handler.error import RestError
from solnlib import log


def validate_input(definition: smi.ValidationDefinition):
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


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        session_key = inputs.metadata["session_key"]
        normalized_input_name = input_name.split("/")[-1]

        # initialize logger
        logger = ta_helper.initalize_logger(
            "device-input",
            normalized_input_name,
            "ta_maas360_settings",
            session_key,
        )
        log.modular_input_start(logger, normalized_input_name)

        # fetch account information
        maas360_account = ta_helper.get_account_details(
            logger, session_key, "ta_maas360_account", input_item["maas360_account"]
        )

        # fetch input configuration
        device_status = input_item["device_status"]
        platform = input_item["platform"]
        managed_status = input_item["managed_status"]
        plc_compliance = input_item["plc_compliance"]
        rule_compliance = input_item["rule_compliance"]
        app_compliance = input_item["app_compliance"]
        pswd_compliance = input_item["pswd_compliance"]

        # initialize MaaS360 handler
        maas360_handler = Maas360Handler(
            logger,
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

        # initialize KVStore checkpointer
        kv_checkpoint = ta_helper.initialize_checkpointer(
            logger, inputs.metadata["server_uri"], session_key
        )

        # fetch last reported after timestamp from checkpoint
        last_reported_after = kv_checkpoint.get(normalized_input_name)

        # set last reported after timestamp to 0 on first run to fetch all devices
        if last_reported_after is None:
            logger.info("First run of MaaS360 device input: fetching ALL devices!")
            last_reported_after = 0
        else:
            logger.info(
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
            logger.debug(
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
                logger.critical(
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
                        event = smi.Event(
                            data=json.dumps(device),
                            time=last_reported_time,
                            index=input_item["index"],
                            source=normalized_input_name,
                            sourcetype="ibm:maas360:device",
                            done=True,
                            unbroken=True,
                        )
                        event_writer.write_event(event)

                    # set last reported after timestamp to last reported timestamp of last device retrieved
                    next_last_reported_after = device_data["devices"]["device"][-1][
                        "lastReportedInEpochms"
                    ]
            else:
                logger.critical(
                    "Received unexpected API response. Check the input and account configuration! Response: {}".format(
                        device_data
                    )
                )
                return

        # update checkpoint with new last reported after timestamp
        logger.info(
            "Saving new last reported after timestamp in checkpoint: {}".format(
                next_last_reported_after
            )
        )
        kv_checkpoint.update(normalized_input_name, next_last_reported_after)

        logger.info("Done fetching MaaS360 devices!")
