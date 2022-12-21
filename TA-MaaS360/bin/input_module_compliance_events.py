# encoding = utf-8

import datetime
import json
from maas360_handler import Maas360Handler
from splunktaucclib.rest_handler.error import RestError


CHECK_POINT_KEY = "maas360_compliance_events_input_checkpoint"


def validate_input(helper, definition):
    # fetch input configuration
    maas360_account = definition.parameters.get("maas360_account", None)

    # validate input
    if not maas360_account:
        raise RestError(400, "You have to provide all necessary arguments!")

    return True


def collect_events(helper, ew):
    # set up logging
    helper.set_log_level(helper.get_log_level())

    # fetch input configuration
    maas360_account = helper.get_arg("maas360_account")

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

    # fetch timestamp of last compliance event from checkpoint
    last_compliance_event_timestamp = helper.get_check_point(CHECK_POINT_KEY)

    # set last reported after timestamp to 0 on first run to fetch all compliance events
    if last_compliance_event_timestamp is None:
        helper.log_info(
            "First run of MaaS360 compliance events input: fetching ALL compliance events!"
        )
        last_compliance_event_timestamp = 0
    else:
        helper.log_info(
            "Fetching compliance events generated after {}".format(
                last_compliance_event_timestamp
            )
        )

    # initialize next last compliance event timestamp
    # this will be set to the timestamp of the last compliance event fetched
    next_last_compliance_event_timestamp = last_compliance_event_timestamp

    # initialize pagination and break condition
    page_number = 1
    page_size = 250
    num_indexed = 0
    checkpoint_reached = False

    while page_size != 0 and checkpoint_reached is False:
        # set up URL parameters for request with pagination
        url_parameters = {
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        helper.log_debug(
            "URL parameters provided to Compliance Events API: {}".format(
                url_parameters
            )
        )

        # send request to API
        compliance_events_response = maas360_handler.request(
            "GET",
            "/device-apis/devices/1.0/searchComplianceEvents/{}".format(
                maas360_handler.billing_id
            ),
            params=url_parameters,
        )

        # check status code
        if compliance_events_response.ok is False:
            helper.log_critical(
                "Unable to fetch MaaS360 compliance events from API. Received status code {}: {}".format(
                    compliance_events_response.status_code,
                    compliance_events_response.text,
                )
            )
            break

        # validate response data
        compliance_events_data = compliance_events_response.json()
        if (
            ("complianceEvents" in compliance_events_data)
            and ("pageSize" in compliance_events_data["complianceEvents"])
            and ("pageNumber" in compliance_events_data["complianceEvents"])
        ):
            # check if the page number returned is the same as the one we requested
            # because pagination works a little bit different in this API ...
            if compliance_events_data["complianceEvents"]["pageNumber"] < page_number:
                helper.log_info(
                    "Reached the end of the API data (page {})!".format(page_number)
                )
                break

            # modify pagination values
            page_size = compliance_events_data["complianceEvents"]["pageSize"]
            page_number = page_number + 1

            if page_size > 0 and page_size < 250:
                # page size has to be 25, 50, 100, 200 or 250
                page_size = 250

            if page_size > 0:
                # iterate over compliance events and write to index
                for compliance_event in compliance_events_data["complianceEvents"][
                    "complianceEvent"
                ]:
                    # parse timestamp of compliance event as UTC timestamp
                    event_timestamp = (
                        datetime.datetime.strptime(
                            compliance_event["actionExecutionTime"],
                            "%Y-%m-%dT%H:%M:%SZ",
                        )
                        .replace(tzinfo=datetime.timezone.utc)
                        .timestamp()
                    )

                    # update next timestamp checkpoint
                    if event_timestamp > next_last_compliance_event_timestamp:
                        next_last_compliance_event_timestamp = event_timestamp

                    # check if event has already been indexed
                    if last_compliance_event_timestamp >= event_timestamp:
                        checkpoint_reached = True
                        break

                    # if device id is in event, fetch security and compliance infos for device to enrich data
                    if "maas360DeviceID" in compliance_event:
                        maas360_device_id = compliance_event["maas360DeviceID"]

                        # send request to API
                        device_security_compliance_response = maas360_handler.request(
                            "GET",
                            "/device-apis/devices/1.0/mdSecurityCompliance/{}".format(
                                maas360_handler.billing_id
                            ),
                            params={"deviceId": maas360_device_id},
                        )

                        # check status code and validate response
                        if device_security_compliance_response.ok is False:
                            helper.log_warning(
                                "Unable to fetch MaaS360 security and compliance information from API. Received status code {}: {}".format(
                                    device_security_compliance_response.status_code,
                                    device_security_compliance_response.text,
                                )
                            )
                        else:
                            # validate reponse
                            compliance_attributes_data = (
                                device_security_compliance_response.json()
                            )
                            if (
                                ("securityCompliance" in compliance_attributes_data)
                                and (
                                    "complianceAttributes"
                                    in compliance_attributes_data["securityCompliance"]
                                )
                                and (
                                    "complianceAttribute"
                                    in compliance_attributes_data["securityCompliance"][
                                        "complianceAttributes"
                                    ]
                                )
                            ):
                                # add compliance attributes to compliance event
                                compliance_event[
                                    "complianceAttributes"
                                ] = compliance_attributes_data["securityCompliance"][
                                    "complianceAttributes"
                                ][
                                    "complianceAttribute"
                                ]

                    # prepare event and store it in index
                    event = helper.new_event(
                        data=json.dumps(compliance_event),
                        time=event_timestamp,
                        index=helper.get_output_index(),
                        source=helper.get_input_type(),
                        sourcetype=helper.get_sourcetype(),
                        done=True,
                        unbroken=True,
                    )
                    ew.write_event(event)
                    num_indexed = num_indexed + 1
        else:
            helper.log_critical(
                "Received unexpected API response. Check the input and account configuration! Response: {}".format(
                    compliance_events_data
                )
            )
            return

    # update checkpoint with new last reported after timestamp
    if next_last_compliance_event_timestamp != last_compliance_event_timestamp:
        helper.log_info(
            "Saving new last compliance event timestamp in checkpoint: {}".format(
                next_last_compliance_event_timestamp
            )
        )
        helper.save_check_point(CHECK_POINT_KEY, next_last_compliance_event_timestamp)

    helper.log_info(
        "Done fetching MaaS360 compliance events (indexed {} events)!".format(
            num_indexed
        )
    )
