[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![hacs_badge](https://img.shields.io/maintenance/yes/2022)](https://github.com/ksheumaker/homeassistant-apsystems_ecur)
[![hacs_badge](https://img.shields.io/github/v/release/ksheumaker/homeassistant-apsystems_ecur)](https://github.com/ksheumaker/homeassistant-apsystems_ecur)
[![hacs_badge](https://img.shields.io/github/v/release/ksheumaker/homeassistant-apsystems_ecur?include_prereleases&label=pre-release)](https://github.com/ksheumaker/homeassistant-apsystems_ecur)
![Home Assistant Dashboard](https://github.com/ksheumaker/homeassistant-apsystems_ecur/blob/main/dashboard.jpg)
# Home-Assistant APsystems ECU Integration
This is an integration for [Home-Assistant](http://home-assistant.io) that adds support for the [APsystems](http://www.apsystems.com) Energy Communication Unit (ECU) so that you are able to monitor your PV installation (inverters) in detail.

Note: This integration was initially written for the older ECU-R (2160xxxxxxxx series) and is fully compatible with the ECU-B. For later ECU-R models (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) and ECU-C owners, usage of this integration results in ECU outage over time. You can then use the automation which is described below to automatically reboot the ECU if it fails. Unfortunately this is a firmware issue which can't be solved by the integration.


## Background & acknowledgement
This integration queries the ECU with a set interval for new data. This was done without a public API, and by listening to and interpreting the protocol the APSystems ECU phone app (ECUapp) uses when setting up the PV array. This couldn't have been done without the hardwork of @checking12 and @HAEdwin on the home assistant forum, and all the other people from this forum (https://gathering.tweakers.net/forum/list_messages/2032302/1). Thanks goes out to @12christiaan for providing an automated solution to reboot the ECU-C and ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) models.

## Prerequisites
You own an APSystems ECU and any combination of YC600, YC1000, DS3 or QS1/QS1A inverter. Your ECU is connected to your LAN, correctly configured and Home Assistant has free access to it. You also have HACS installed in Home Assistant.
Connection method (ethernet or WiFi) depends on your ECU model, follow the table below.
Connection | ECU Model | Reboot Automation Needed
--- | --- | ---
Wireless | ECU-R (2160xxxxxxxx series) and ECU-B | No
Wired or Wireless | ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) | Yes
Wired | ECU-C | Yes

## Pre-release/Beta program
If you're having trouble with the integration, consider joining the beta program. To do this, select HACS > Integrations > click on APSystems ECU-R > Select the three dots (overflow menu) in the top right corner > Redownload > switch on the "Show beta versions" switch. In HA you will now also see notifications when there is a beta release. You are always able to roll-back to an official release. Please provide us with feedback when using beta releases.

## Release notes
Release notes, assets and further details can be found [here](https://github.com/ksheumaker/homeassistant-apsystems_ecur/releases)

## Installation resources in other languages
German: https://smart-home-assistant.de/ap-systems-ecu-b-einbinden

## Setup Integration
Install the integration using HACS by searching for "APSystems ECU-R". If you are unable to find the integration in HACS, select HACS in left pane, select Integrations. In the top pane right from the word Integrations you can find the menu (three dots above eachother). Select Custom Repositories and add the URL: https://github.com/ksheumaker/homeassistant-apsystems_ecur below that select category Integration. After the installation, restart Home Assistant by going to [Settings] > [System] and select [restart] in the upper right corner. After restart, next step will be the configuration.

## Configuration
Choose [Configuration] > [Devices & Services] > [+ Add Integration] and search for "APSystems PV solar ECU" which enables you to configure the integration settings. Provide the IP-address from the ECU (no leading zero's), and set the update interval (300 seconds is the recommended default).
_It's good to know that the ECU only contains new data once every 5 minutes so a smaller interval does not update info more often._ After selecting [Submit] the integration will setup the entities in around 12 seconds.

## Data caching
The integration uses caching. The reason for this is that the ECU does not always respond to data requests. For example during maintenance tasks that take place on the ECU around 02.45-03.15 AM local time. In most cases a 'time out' occurs, these are suppressed in the homeassistant.log. Practice shows that it is then best to use the old data until the ECU responds again to the next query. 
![APSystems ECU integration cache](https://github.com/ksheumaker/homeassistant-apsystems_ecur/blob/main/integration_cache.jpg)

The integration uses the cache 5 times in a row, after which it is assumed that something else is going on, such as a stuck ECU. On the older ECU-R models (UID 2160xxxxx) and ECU-B this is not very common, on ECU-C and ECU-R (UID 2162xxxxx) models it is. You can use the automation to automatically reboot the ECU.

## Reboot Automation
For ECU-C and ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) models the use of this integration causes the ECU to get stuck. This is an ECU firmware issue and can be solved by the automation provided by @12christiaan.

In automations.yaml
```
- id: '1661333377702'
  alias: Reboot ECU if unavailable readings
  description: ''
  trigger:
  - platform: state
    entity_id:
    - switch.ecu_query_device
    to: 'off'
  condition:
  - condition: and
    conditions:
    - condition: state
      entity_id: binary_sensor.ecu_using_cached_data
      state: 'on'
  action:
  - service: shell_command.reboot_ecu
    data: {}
  - delay:
      hours: 0
      minutes: 1
      seconds: 0
      milliseconds: 0
  - service: switch.turn_on
    data: {}
    target:
      entity_id: switch.ecu_query_device
  mode: single
```
In configuration.yaml (don't forget to fill in the ECU IP-Address):
```
shell_command:
  reboot_ecu: '/usr/bin/curl "http://<ip-address>/index.php/management/set_wlan_ap" -H "X-Requested-With: XMLHttpRequest" --data-raw "SSID=ECU-WIFI_local&channel=0&method=0&psk_wep=&psk_wpa=" --compressed --insecure'
```

## Using the ECU Query Device switch
Although you can query the ECU 24/7, it is an option to stop the query after sunset and start the query again at sunrise.
If you prefer to stop querying the ECU, you can create an automation that flips the switch. manually flipping the switch causes the cache to be used the next interval. The switch is automatically turned off if the cache had to be used five times in a row and queries are stopped. In this case there may be something wrong with the ECU, it must be restarted by automation or given powercycle manually.

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
* sensor.inverter_[UID]\_power_ch_[1-4] - the current power generation (in W) of each channel (model depentent) of the inverter
* binary_sensor.ecu_using_cached_data - indicates the usage of cached data

### Switch
* switch.ecu_query_device - switch will turn off in the fifth step using cached data

## TODO
Code cleanup - it probably needs some work
