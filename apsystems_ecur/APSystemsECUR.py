#!/usr/bin/env python3

import socket
import binascii
import datetime
import json

from pprint import pprint

class APSystemsECUR:

    def __init__(self, ipaddr, port=8899, raw_ecu=None, raw_inverter=None):
        self.ipaddr = ipaddr
        self.port = port

        self.recv_size = 2048

        self.qs1_ids = [ "802", "801" ]
        self.yc600_ids = [ "406", "407", "408", "409" ]
        self.yc1000_ids = [ "501", "502", "503", "504" ]

        self.ecu_query = 'APS1100160001END'
        self.inverter_query_prefix = 'APS1100280002'
        self.inverter_query_suffix = 'END'
        self.inverter_byte_start = 26

        self.ecu_id = None
        self.qty_of_inverters = 0
        self.lifetime_energy = 0
        self.current_power = 0
        self.today_energy = 0
        self.inverters = []
        self.firmware = None
        self.timezone = None
        self.last_update = None

        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter

        self.last_inverter_data = None


    def dump(self):
        print(f"ECU : {self.ecu_id}")
        print(f"Firmware : {self.firmware}")
        print(f"TZ : {self.timezone}")
        print(f"Qty of inverters : {self.qty_of_inverters}")

    async def async_query_ecu(self):
        return self.query_ecu()


    def query_ecu(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ipaddr,self.port))

        sock.send(self.ecu_query.encode('utf-8'))
        self.ecu_raw_data = sock.recv(self.recv_size)

        self.process_ecu_data()

        cmd = self.inverter_query_prefix + self.ecu_id + self.inverter_query_suffix
        sock.send(cmd.encode('utf-8'))

        self.inverter_raw_data = sock.recv(self.recv_size)

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        data = self.process_inverter_data()

        data["ecu_id"] = self.ecu_id
        data["today_energy"] = self.today_energy
        data["lifetime_energy"] = self.lifetime_energy
        data["current_power"] = self.current_power

        self.last_inverter_data = data

        return(data)
 
    def aps_int(self, codec, start):
        return int(binascii.b2a_hex(codec[(start):(start+2)]), 16)

    def aps_double(self, codec, start):
        return int (binascii.b2a_hex(codec[(start):(start+4)]), 16)
    
    def aps_bool(self, codec, start):
        return bool(binascii.b2a_hex(codec[(start):(start+2)]))
    
    def aps_uid(self, codec, start):
        return str(binascii.b2a_hex(codec[(start):(start+12)]))[2:14]
    
    def aps_str(self, codec, start, amount):
        return str(codec[start:(start+amount)])[2:(amount+2)]
    
    def aps_timestamp(self, codec, start, amount):
        timestr=str(binascii.b2a_hex(codec[start:(start+amount)]))[2:(amount+2)]
        return timestr[0:4]+"-"+timestr[4:6]+"-"+timestr[6:8]+" "+timestr[8:10]+":"+timestr[10:12]+":"+timestr[12:14]

    def process_ecu_data(self, data=None):
        if not data:
            data = self.ecu_raw_data

        if len(data) < 16:
            raise Exception("ECU query didn't return minimum 16 bytes, no inverters active.")

        print(binascii.b2a_hex(data))
        self.ecu_id = self.aps_str(data, 13, 12)
        self.qty_of_inverters = self.aps_int(data, 46)
        self.firmware = self.aps_str(data, 55, 15)
        self.timezone = self.aps_str(data, 70, 9)
        self.lifetime_energy = self.aps_double(data, 27) / 10
        self.today_energy = self.aps_double(data, 35) / 100
        self.current_power = self.aps_double(data, 31)

    def process_inverter_data(self, data=None):
        if not data:
            data = self.inverter_raw_data

        output = {}

        timestamp = self.aps_timestamp(data, 19, 14)
        inverter_qty = self.aps_int(data, 17)

        self.last_update = timestamp
        output["timestamp"] = timestamp
        output["inverter_qty"] = inverter_qty
        output["inverters"] = {}

        # this is the start of the loop of inverters
        location = self.inverter_byte_start

        inverters = {}
        for i in range(0, inverter_qty):

            inv={}

            inverter_uid = self.aps_uid(data, location)
            inv["uid"] = inverter_uid
            location += 6

            inv["online"] = self.aps_bool(data, location)
            location += 1

            inv["unknown"] = self.aps_str(data, location, 2)
            location += 2

            inv["frequency"] = self.aps_int(data, location) / 10
            location += 2

            inv["temperature"] = self.aps_int(data, location) - 100
            location += 2

            # the first 3 digits determine the type of inverter
            inverter_type = inverter_uid[0:3]
            if inverter_type in self.yc600_ids:
                (channel_data, location) = self.process_yc600(data, location)
                inv.update(channel_data)    

            elif inverter_type in self.qs1_ids:
                (channel_data, location) = self.process_qs1(data, location)
                inv.update(channel_data)    

            else:
                raise Exception(f"Unsupported inverter type {inverter_type}")

            inverters[inverter_uid] = inv

        output["inverters"] = inverters
        return (output)

    def process_qs1(self, data, location):

        power = []
        voltages = []

        power.append(self.aps_int(data, location))
        location += 2

        voltage = self.aps_int(data, location)
        location += 2

        power.append(self.aps_int(data, location))
        location += 2

        power.append(self.aps_int(data, location))
        location += 2

        power.append(self.aps_int(data, location))
        location += 2

        voltages.append(voltage)

        output = {
            "model" : "QS1",
            "channel_qty" : 4,
            "power" : power,
            "voltage" : voltages
        }

        return (output, location)


    def process_yc600(self, data, location):
        power = []
        voltages = []

        for i in range(0, 2):
            power.append(self.aps_int(data, location))
            location += 2

            voltages.append(self.aps_int(data, location))
            location += 2

        output = {
            "model" : "YC600",
            "channel_qty" : 2,
            "power" : power,
            "voltage" : voltages,
        }

        return (output, location)


