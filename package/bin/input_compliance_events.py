import json
import ta_helper
import datetime

from maas360_handler import Maas360Handler

from splunklib import modularinput as smi
from splunktaucclib.rest_handler.error import RestError
from solnlib import log


def validate_input(definition: smi.ValidationDefinition):
    # fetch input configuration
    maas360_account = definition.parameters.get("maas360_account", None)

    # validate input
    if not maas360_account:
        raise RestError(400, "You have to provide all necessary arguments!")

    return True


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        session_key = inputs.metadata["session_key"]
        normalized_input_name = input_name.split("/")[-1]

        # initialize logger
        logger = ta_helper.initalize_logger(
            "compliance-input",
            normalized_input_name,
            "ta_maas360_settings",
            session_key,
        )
        log.modular_input_start(logger, normalized_input_name)

        # fetch account information
        maas360_account = ta_helper.get_account_details(
            logger, session_key, "ta_maas360_account", input_item["maas360_account"]
        )

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

        last_compliance_event_timestamp = kv_checkpoint.get(normalized_input_name)

        # set last reported after timestamp to 0 on first run to fetch all compliance events
        if last_compliance_event_timestamp is None:
            logger.info(
                "First run of MaaS360 compliance events input: fetching ALL compliance events!"
            )
            last_compliance_event_timestamp = 0
        else:
            logger.info(
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
            logger.debug(
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
                logger.critical(
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
                if (
                    compliance_events_data["complianceEvents"]["pageNumber"]
                    < page_number
                ):
                    logger.info(
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
                                logger.warning(
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
                                        in compliance_attributes_data[
                                            "securityCompliance"
                                        ]
                                    )
                                    and (
                                        "complianceAttribute"
                                        in compliance_attributes_data[
                                            "securityCompliance"
                                        ]["complianceAttributes"]
                                    )
                                ):
                                    # add compliance attributes to compliance event
                                    compliance_event["complianceAttributes"] = (
                                        compliance_attributes_data[
                                            "securityCompliance"
                                        ]["complianceAttributes"]["complianceAttribute"]
                                    )

                        # prepare event and store it in index
                        event = smi.Event(
                            data=json.dumps(compliance_event),
                            time=event_timestamp,
                            index=input_item["index"],
                            source=normalized_input_name,
                            sourcetype="ibm:maas360:compliance",
                            done=True,
                            unbroken=True,
                        )
                        event_writer.write_event(event)
                        num_indexed = num_indexed + 1
            else:
                logger.critical(
                    "Received unexpected API response. Check the input and account configuration! Response: {}".format(
                        compliance_events_data
                    )
                )
                return

        # update checkpoint with new last reported after timestamp
        if next_last_compliance_event_timestamp != last_compliance_event_timestamp:
            logger.info(
                "Saving new last compliance event timestamp in checkpoint: {}".format(
                    next_last_compliance_event_timestamp
                )
            )
            kv_checkpoint.update(
                normalized_input_name, next_last_compliance_event_timestamp
            )

        logger.info(
            "Done fetching MaaS360 compliance events (indexed {} events)!".format(
                num_indexed
            )
        )
