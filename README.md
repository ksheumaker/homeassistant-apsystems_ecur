# Home-Assistant APsystems ECU-R and ECU-B Integration
This is a custom component for [Home-Assistant](http://home-assistant.io) that adds support for the [APsystems](http://www.apsystems.com) Energy Communication Unit (ECU) so that you are able to monitor your PV installation (inverters) in detail.

Note: For later ECU-R models (SunSpec logo/ECU-ID starting with 2162xxxxxx) and ECU-C owners this integration is not suitable resulting in ECU outage over time!


## Background & acknowledgement
This integration queries the ECU with a set interval for new data. This was done without a public API, and by listening to and interpreting the protocol the APSystems ECU phone app (ECUapp) uses when setting up the PV array.

This couldn't have been done without the hardwork of @checking12 and @HAEdwin on the home assistant forum, and all the other people from this forum (https://gathering.tweakers.net/forum/list_messages/2032302/1)

## Prerequisites
You own an APSystems ECU and any combination of YC600, YC1000, DS3 or QS1/QS1A inverter.
This component only works if the ECU is attached to your network by Wifi. To enable and configure WiFi on the ECU, use the ECUapp (downloadable via Appstore or Google Play) and temporarily enable the ECU's accesspoint by pressing the button on the side of the ECU. Then connect your phone's WiFi to the ECU's accesspoint to enable the ECUapp to connect and configure the ECU. Although there's no need to also attach the ECU by ethernet cable (for the ECU-B LAN ports are disabled), feel free to do so if you like but alway connect this integration to the ECU's WiFi enabled IP-Address.

## Beta program
If you're having trouble with the integration, consider joining the beta program. To do this, select HACS > Integrations > click on APSystems ECU-R > Select the three dots (overflow menu) in the top right corner > Redownload > switch on the "Show beta versions" switch. In HA you will now also see notifications when there is a beta release. You are always able to roll-back to an official release. Please provide us with feedback when using beta releases.

## Release notes
Release notes, assets and further details can be found [here](https://github.com/ksheumaker/homeassistant-apsystems_ecur/releases)

## Setup
Install the custom component using HACS by searching for "APSystems ECU-R". If you are unable to find the integration in HACS, select HACS in left pane, select Integrations. In the top pane right from the word Integrations you can find the menu (three dots above eachother). Select Custom Repositories and add the URL: https://github.com/ksheumaker/homeassistant-apsystems_ecur below that select category Integration.

## Configuration
choose [Configuration] > [Devices & Services] > [+ Add Integration] and search for search for "APSystems PV solar ECU" which enables you to configure the integration settings. Provide the WIFI IP-address from the ECU, and set the update interval (300 seconds is the default).
_Warning_ the ECU device isn't the most powerful querying it more frequently could lead to stability issues with the ECU and require a power cycle.

Although you can query the ECU 24/7, it is an option to stop the query after sunset and start the query again at sunrise. You can do this by adding automations and by triggering the ECU Query Device switch entity.  

Reason for this are the maintenance tasks that take place on the ECU around 02.45-03.15 AM local time. During this period the ECU does not provide data which results in error messages in the log if the integration tries to query for data. During maintenance, the ECU is checking whether all data to the EMA website has been updated, clearing cached data and the ECU is looking for software updates, updating the ECU firmware when applicable. Besides the log entries no harm is done if you query the ECU 24/7.

## Data exposed devices and entities
The integration supports getting data from the PV array as a whole as well as each individual inverter in detail.
ECU and inverters will be exposed in Home Assistant. As a result the following sensors and switch can be used.

### ECU Sensors
* sensor.ecu_current_power - total amount of power (in W) being generated right now
* sensor.ecu_inverters - total number of configured inverters in the ECU
* sensor.ecu_inverters_online - total number of configured online inverters in the ECU 
* sensor.ecu_today_energy - total amount of energy (in kWh) generated today now
* sensor.ecu_lifetime_energy - total amount of energy (in kWh) generated from the lifetime of the array

### Inverter Level Sensors (Array)
A new device will be created for each inverter called `Inverter_[UID]` where [UID] is the unique ID of the Inverter
* sensor.inverter_[UID]_frequency - the AC power frequency in Hz
* sensor.inverter_[UID]_voltage - the AC voltage in V
* sensor.inverter_[UID]_temperature - the temperature of the invertor in your local unit (C or F)
* sensor.inverter_[UID]_signal - the signal strength of the zigbee connection
* sensor.inverter_[UID]\_power_ch_[1-4] - the current power generation (in W) of each channel of the invertor - number of channels will depend on inverter model
* binary_sensor.ecu_using_cached_data - indicates the usage of cached data

### Switch
* switch.ecu_query_device - switch will turn off in the sixth step using cached data

## TODO
Code cleanup - it probably needs some work
