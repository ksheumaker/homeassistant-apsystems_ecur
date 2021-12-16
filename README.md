# homeassistant-apsystems_ecur
This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for the [APsystems](http://www.apsystems.com) ECU-R and ECU-B solar Energy Communication Unit. With this component you are able to monitor your PV installation (inverters) in detail.


## Background & acknowledgement
This integration queries the local ECU-R and ECU-B every 1 minute for new data. This was done without a public API, and by listening to and interpreting the protocol the APSystems ECU phone app (ECUapp) uses when setting up the PV array.

This couldn't have been done without the hardwork of @checking12 and @HAEdwin on the home assistant forum, and all the other people from this forum (https://gathering.tweakers.net/forum/list_messages/2032302/1)

## Prerequisites
You own an APSystems ECU-R or ECU-B and any combination of YC600, YC1000 or QS1/QS1A inverter.
This component only works if the ECU-R or ECU-B is attached to your network by Wifi. To enable and configure WiFi on the ECU, use the ECUapp (downloadable via Appstore or Google Play) and temporarily enable the ECU's accesspoint by pressing the button on the side of the ECU. Then connect your phone's WiFi to the ECU's accesspoint to enable the ECUapp to connect and configure the ECU.
Although there's no need to also attach the ECU-R by ethernet cable (for the ECU-B LAN ports are disabled), you are free to do so if you like.
```

Release notes
v1.0.0 First release
v1.0.1 Revised the readme, added support for YC1000 and added versioning to the manifest
v1.0.2 Added support for QS1A
v1.0.3 Added support for 2021.8.0 (including energy panel), fixed some issues with ECU_R_PRO
v1.0.4 Added optional scan_interval to config
v1.0.5 Fixed energy dashboard and added HACS setup option description in readme.md
v1.0.6 Replaces deprecated device_state_attributes for extra_state_attributes and mentioned the ECU-B because of compatibility with this component
```

## Setup
Option 1:
Easiest option, install the custom component using HACS by searching for "APSystems ECU-R"

Option 2:
Copy contents of the apsystems_ecur/ directory into your <HA-CONFIG>/custom_components/apsystems_ecur directory (```/config/custom_components``` on hassio)
Your directory structure should look like this:
```
   config/custom_components/apsystems_ecur/__init__.py
   config/custom_components/apsystems_ecur/APSystemsECUR.py
   config/custom_components/apsystems_ecur/binary_sensor.py
   config/custom_components/apsystems_ecur/const.py
   config/custom_components/apsystems_ecur/manifest.json
   config/custom_components/apsystems_ecur/sensor.py
   config/custom_components/apsystems_ecur/services.yaml
```

## Configuration
Add the following snippet into your ```configuration.yaml```  replace [IPADDR] with the WiFi connected IP address of your ECU-R or ECU-B device. By default the integration will query the ECU every 60 seconds, you can alter this by altering the scan interval configuration option.  

_Warning_ the ECU device isn't the most powerful querying it more frequently could lead to stability issues with the ECU and require a power cycle.

```

apsystems_ecur:
    host: [IPADDR]
    scan_interval: 60

```
Although you can query the ECU 24/7, it is good practice to stop the query an hour after sunset (apsystems_ecur.stop_query) and only start the query again at sunrise (apsystems_ecur.start_query). You can do this by adding automations. Reason for this are the maintenance tasks that take place on the ECU around 02.15 local time. During this period the ECU port is closed which results in error messages in the log if the integration tries to query for data. During maintenance, the ECU is checking whether all data to the EMA website has been updated, clearing cached data and the ECU is looking for software updates.

## Data available
The component supports getting data from the array as a whole as well as each individual invertor.

### Array Level Sensors
* sensor.ecu_current_power - total amount of power (in W) being generated right now
* sensor.ecu_today_energy - total amount of energy (in kWh) generated today now
* sensor.ecu_lifetime_energy - total amount of energy (in kWh) generated from the lifetime of the array

### Inverter Level Sensors
There will be this set of sensors for every inverter you have in your system, UID will be replaced by the UID of the inverter discovered

* sensor.inverter_[UID]_frequency - the AC power frequency in Hz
* sensor.inverter_[UID]_voltage - the AC voltage in V
* sensor.inverter_[UID]_temperature - the temperature of the invertor in your local unit (C or F)
* sensor.inverter_[UID]_signal - the signal strength of the zigbee connection
* sensor.inverter_[UID]_power_ch_[1-4] - the current power generation (in W) of each channel of the invertor - number of channels will depend on inverter model

## TODO
1. Code cleanup - it probably needs some work
