# IBM MaaS360 Add-on for Splunk

This Splunk Technical Add-on adds two inputs for IBM MaaS360:

- **Devices** (excellent data source for A&I and other use cases)
- **Compliance Events** (enriched with security and compliance infos about affected devices)

## Setup & Configuration

### Where to install this add-on (Splunk Enterprise)

| Splunk platform instance type | Supported | Required    | Comments |
| ----------------------------- | --------- | --------    | -------- |
| Search Heads                  | Yes       | No          | Only install this add-on to a SH if you want to use data models |
| Indexers                      | Yes       | Conditional | I recommend to use Heavy Forwarders to collect data, but an Indexer can also be used. If you don't run the input on an indexer, don't install this TA to Indexers! |
| Heavy Forwarders              | Yes       | Conditional | It's recommended to run inputs on this instance! |
| Universal Forwarders          | No        | No          | |

> 📝 Single-instance (standalone) and Splunk Cloud deployments are supported as well!

> 🔨 You have to restart Splunkd on the Splunk instance that runs the inputs after you install this TA!

### IBM MaaS360 Configuration

The Add-on fetches data from the IBM MaaS360 **Web Services API**, which has to be enabled in the MaaS360 portal first. You can find more infos about that [here](https://www.ibm.com/docs/no/maas360?topic=web-services)!

#### Access Rights

The IBM MaaS360 user needs at least the following access rights (roles):

- **Device Input:** `Device View - Read-only`
- **Compliance Event Input:** `Manage Policies`

### Technical Add-on Configuration

The Setup of this TA is very straightforward. Here are the required steps:

- Install the TA on your Splunk instance(s) according to the table above
- 🔨 Restart Splunkd on the Splunk instance that will run the inputs
- Open the **IBM MaaS360 Add-on for Splunk** App

  ![Navigation Bar Entry](/screenshots/nav_bar.jpg "Navigation Bar Entry")

- Switch to **Configuration** and add a new **Account**

  ![Add Account UI](/screenshots/add_account.jpg "Add Account UI")

  - **(2)** | The **API Root Host** varies by MaaS360 instance on which the customer account exists
  - **(4) (5) (6) (7)** | You receive these infos after provisioning the MaaS360 app

- Switch to **Inputs** and create new inputs according to your needs.

  - **Device Input:**
    
    ![Device Input UI](/screenshots/device_input.jpg "Device Input UI")
    
    This input fetches all devices that match the filters defined in the input configuration and that have **last reported to MaaS360 since the last run** of this input!

    - **(3)** | Index in which the data should be stored
    - **(4)** | The MaaS360 account to use for the input (see the last step)
    - **(5)** | This filter can be used to only fetch devices that are *Active/Inactive*
    - **(6)** | Fetch devices based on their platform *(e.g. Windows/Android/...)*
    - **(7)** | Use the MaaS360 managed status to filter out devices *(e.g. Enrolled only)*
    - **(8) (9) (10) (11)** | Filter devices based on their compliances status *(OOC = Out of compliance)*
  
  - **Compliance Events Input:**

    ![Compliance Events Input UI](/screenshots/compliance_events_input.jpg "Compliance Events Input UI")

    This input fetches all compliance events **reported since the last run** of the input and adds **Security & Compliance** infos about the affected devices.

    - **(3)** | Index in which the data should be stored
    - **(4)** | The MaaS360 account to use for the input (see the last step)

    > 📝 The first run of this input may take a few minutes, because it fetches ALL compliance events.

- Verify that the input is working by searching for the data! If you don't see anything, have a look at the **Troubleshooting** section.

### CIM

This Add-on maps IBM MaaS360 **Device** data to the [Inventory](https://docs.splunk.com/Documentation/CIM/latest/User/ComputeInventory) (formerly labeled and documented as "Compute Inventory") data model.

💬 If you don't want to use the data model, you can ignore this section and don't have to install this Add-on to your search head(s).

All device events receive the event type `maas360_device`.
All events with this event type are tagged with `inventory`. You can use this tag to set up data model acceleration!

## Troubleshooting

The TA writes logs into `_internal`. You can use the following search for troubleshooting/monitoring purposes:

```
index="_internal" sourcetype="tamaas360:log"
```

Optionally, raise the Log Level on the App Configuration page:

 ![Logging UI](/screenshots/logging.jpg "Logging UI")

## How to dev

This project uses Docker Compose to spin up a full Splunk Enterprise development environment.

- Put your Splunk developer license in the root of this repository in a file called `splunk.lic`
- Create a file with the name `splunkbase.credentials` in the root of this repository and add working Splunkbase credentials in it *(hint: BugMeNot)*:

```
SPLUNKBASE_USERNAME=<username>
SPLUNKBASE_PASSWORD=<password>
```

- Start the Docker instance: `docker compose up [-d]`

That's it. You can now start configuring the add-on in Splunk Web and develop whatever you like.

**Hint:** The Splunk instance is pre-configured with an index called `mdm`. You can use it to store MaaS360 data.

### Linux File Permissions

Please make sure that files outside of the `bin/` and `appserver/controllers` directory do not have execute permissions and are not `.exe` files. Splunk recommends `644` for all app files outside of the `bin/` directory, `644` for scripts within the `bin/` directory that are invoked using an interpreter (e.g. `python my_script.py` or `sh my_script.sh`), and `755` for scripts within the `bin/` directory that are invoked directly (e.g. `./my_script.sh` or `./my_script`). Here's a snippet that ensures that file permissions are correct:

```
sudo find TA-MaaS360 -type d -exec chmod 755 {} +
sudo find TA-MaaS360 -type f -exec chmod 644 {} +
sudo find TA-MaaS360/TA-MaaS360/bin/ -type f -name "*.exe" -exec chmod 755 {} +
```

**More infos:** [Splunk AppInspect check criteria](https://dev.splunk.com/enterprise/reference/appinspect/appinspectcheck/)

## Additional Infos

This project is actually hosted in GitLab and synced to GitHub, but you can still contribute to this project in GitHub of course!
