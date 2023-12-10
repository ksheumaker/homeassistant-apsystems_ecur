[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![hacs_badge](https://img.shields.io/maintenance/yes/2023)](https://github.com/ksheumaker/homeassistant-apsystems_ecur)
[![hacs_badge](https://img.shields.io/github/v/release/ksheumaker/homeassistant-apsystems_ecur)](https://github.com/ksheumaker/homeassistant-apsystems_ecur)
[![hacs_badge](https://img.shields.io/github/v/release/ksheumaker/homeassistant-apsystems_ecur?include_prereleases&label=pre-release)](https://github.com/ksheumaker/homeassistant-apsystems_ecur)
[![Validate with Hassfest](https://github.com/ksheumaker/homeassistant-apsystems_ecur/actions/workflows/validate%20with%20Hassfest.yml/badge.svg)](https://github.com/ksheumaker/homeassistant-apsystems_ecur/actions/workflows/validate%20with%20Hassfest.yml)
![Home Assistant Dashboard](https://github.com/ksheumaker/homeassistant-apsystems_ecur/blob/main/dashboard.jpg)
# Home-Assistant APsystems ECU Integration
This is an integration for [Home-Assistant](http://home-assistant.io) that adds support for the [APsystems](http://www.apsystems.com) Energy Communication Unit (ECU) so that you are able to monitor your PV installation (inverters) in detail. It currently supports one ECU (one instance of the integration) but a work-around is available https://github.com/ksheumaker/homeassistant-apsystems_ecur/issues/142

Note: This integration was initially written for the older ECU-R (2160xxxxxxxx series) and is fully compatible with the ECU-B. For later ECU-R models (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) and ECU-C owners, usage of this integration results in ECU outage over time. From version 1.2.21 the integration will restart the ECU automatically. This can be monitored by the "binary_sensor.restart_ecu". Unfortunately this is a firmware issue which can't be solved by the integration.


## Background & acknowledgement
This integration queries the ECU with a set interval for new data. This was done without a public API, and by listening to and interpreting the protocol the APSystems ECU phone app (ECUapp) uses when setting up the PV array. This couldn't have been done without the hardwork of @checking12 and @HAEdwin on the home assistant forum, and all the other people from this forum (https://gathering.tweakers.net/forum/list_messages/2032302/1). Thanks goes out to @12christiaan and @ViperRNMC for providing an automated solution to restart the ECU-C and ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) models.

## Prerequisites
You own an APSystems ECU model ECU-B, ECU-R or ECU-C and any combination of YC600, YC1000/QT2, DS3/DS3D, DS3-H or QS1/QS1A inverter. If your inverter is not supported, please raise an issue. Your ECU is connected to your LAN, correctly configured (assigned a fixed IP address) and Home Assistant has free access to it. You also have HACS installed in Home Assistant.
Connection method (ethernet or WiFi) depends on your ECU model, follow the table below.
Connection | ECU Model | Automated Restart*
--- | --- | ---
Wireless (unplugged Ethernet required) | ECU-R (2160xxxxxxxx series) and ECU-B | No
Wireless | ECU-R (SunSpec logo/ECU-ID starting with 2162xxxxxxxx) | Yes
Wired | ECU-C | Yes

### Test your connection
Final step to the prerequisites is testing the connection between HomeAssistant and the ECU. Sometimes it is difficult to find the ECU among all the other nodes, especially if you have many IOT devices. In any case, look for Espressif Inc. or ESP because the WiFi interface is from this brand. Testing the connection can be done from the terminal using the Netcat command, follow the example below but use the correct (fixed) IP address of your ECU. If connected you'll see line 2, then type in the command APS1100160001END if you get a response (line 4) you are ready to install the integration. If not, power cycle your ECU wait for it to get started and try again.
```
[core-ssh .storage]$ nc -v 172.16.0.4 8899 <┘
172.16.0.4 (172.16.0.4:8899) open
APS1100160001END <┘
APS11009400012160000xxxxxxxz%10012ECU_R_1.2.22009Etc/GMT-8
```

## Pre-release/Beta program
If you're having trouble with the integration, consider joining the beta program. To do this, select HACS > Integrations > click on APSystems ECU-R > Select the three dots (overflow menu) in the top right corner > Redownload > switch on the "Show beta versions" switch. In HA you will now also see notifications when there is a beta release. You are always able to roll-back to an official release. Please provide us with feedback when using beta releases.

## Release notes
Release notes, assets and further details can be found [here](https://github.com/ksheumaker/homeassistant-apsystems_ecur/releases)

## Other languages
German: https://smart-home-assistant.de/ap-systems-ecu-b-einbinden
Feel free to participate by adding your language to the integration but remember to reload the page, labels might be invisible due to browser caching.

## Install Integration
This is not a Home Assistant Add-On, it's a custom component/integration. Install the integration using HACS by searching for "APSystems ECU-R". If you are unable to find the integration in HACS, select HACS in left pane. In the top pane you can find the overflow menu (three dots above eachother). Select Custom Repositories and add the URL: https://github.com/ksheumaker/homeassistant-apsystems_ecur below that select category Integration. Choose ADD-button and then click on the repository (with the wastebasket behind it). The homepage of the integration will open and in the lower right corner you will find the Download-button. Choose the version and click Download. Now restart Home Assistant by going to [Settings] > [System] and select [restart] in the upper right corner. After restart, next step will be the configuration.

## Configuration
Choose [Configuration] > [Devices & Services] > [+ Add Integration] and search for "APSystems PV solar ECU" which enables you to configure the integration settings. Provide the IP-address from the ECU (no leading zero's), and set the update interval (300 seconds is the recommended default).
_It's good to know that the ECU only contains new data once every 5 minutes so a smaller interval does not update info more often._ After selecting [Submit] the integration will setup the entities in around 12 seconds. Note: If the previous connection test was succesfull but you encounter the message "Can't find ECU at this IP-Address or life-time energy is zero" you will have to temporary apply this fix https://github.com/ksheumaker/homeassistant-apsystems_ecur/issues/113

## Data caching
The integration uses caching. The reason for this is that the ECU does not always respond to data requests. For example during maintenance tasks that take place on the ECU around 02.45-03.15 AM local time. In most cases a 'time out' occurs, these are suppressed in the homeassistant.log. Practice shows that it is then best to use the old data until the ECU responds again to the next query interval. 
![Integration data caching](https://github.com/ksheumaker/homeassistant-apsystems_ecur/blob/main/integration_cache.jpg)

*The integration uses the cache 5 times in a row, after which it is assumed that something else is going on, such as a stuck ECU. On the older ECU-R models (UID 2160xxxxx) and ECU-B this is not very common, on ECU-C and ECU-R (UID 2162xxxxx) models it is - the integration will restart your ECU automatically if this happens. If that fails the ECU Query Device switch will disable querying. Because an automated restart is not available on the older ECU model the switch will disable querying immediately. You can use an automation to send a notify if this happens.

## Using the ECU Query Device switch
Although you can query the ECU 24/7, it is an option to stop the query after sunset and start the query again at sunrise. This is especially useful if too many query errors occur after sunset or during ECU maintenance. If you prefer to temporary stop querying the ECU, you can create an automation that flips the switch. manually flipping the switch causes the cache to be used the next intervals until an automation flips the switch on again. 

## The temperature sensors
When the inverters are turned off at sundown the ECU returns zero for inverters temperature. Users prefer to keep them as null values instead of zero so the graphs are not being updated during the offline periods. In return, this causes a non-numeric error message for the gauge if you use that as a temperature indicator. In that case you can use this template part which converts the value to zero:
```
temperature_non_numeric_408xxxxxxxxx:
        value_template: "{{ states('sensor.inverter_408xxxxxxxxx_temperature')|float(0) }}"
        unit_of_measurement: "°C"
```

## Data exposed devices and entities (and how to create derived sensors)
The integration supports getting data from the PV array as a whole as well as each individual inverter in detail.
ECU and inverters will be exposed in Home Assistant. As a result the following sensors and switch can be used.

### ECU Sensors
* sensor.ecu_current_power - total amount of power (in W) being generated right now
* sensor.ecu_inverters - total number of configured inverters in the ECU
* sensor.ecu_inverters_online - total number of configured online inverters in the ECU 
* sensor.ecu_today_energy - total amount of energy (in kWh) generated today now
* sensor.ecu_lifetime_energy - total amount of energy (in kWh) generated from the lifetime of the array
* binary_sensor.ecu_restart - indicates a restart of the ECU
* binary_sensor.ecu_using_cached_data - indicates the usage of cached data

### Inverter Level Sensors (Array)
A new device will be created for each inverter called `Inverter_[UID]` where [UID] is the unique ID of the Inverter
* sensor.inverter_[UID]_frequency - the AC power frequency in Hz
* sensor.inverter_[UID]_voltage - the AC voltage in V
* sensor.inverter_[UID]_temperature - the temperature of the invertor in your local unit (C or F)
* sensor.inverter_[UID]_signal - the signal strength of the zigbee connection
* sensor.inverter_[UID]\_power_ch_[1-4] - the current power generation (in W) of each channel (model depentent) of the inverter

### Switch
* switch.ecu_query_device - switch will turn off after the user configured number of intervals if cached data is used.

### How to derive new sensors from excisting sensors
* Total power for each inverter: Settings > Devices and Services > Helpers (top of the screen) > +Create Helper > +/- Combine the state of several sensors
* Show the total_energy_yesterday: https://community.home-assistant.io/t/statistic-sensor-reset-clear-at-midnight-for-daily-min-max-temperature/501688/8

## TODO
Code cleanup - it probably needs some work
