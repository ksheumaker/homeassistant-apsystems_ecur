#!/usr/bin/env python3

import socket
import binascii
import datetime
import json
import logging
import time

_LOGGER = logging.getLogger(__name__)

from pprint import pprint

class APSystemsInvalidData(Exception):
    pass

class APSystemsInvalidInverter(Exception):
    pass


class APSystemsSocket:

    def __init__(self, ipaddr, port=8899, raw_ecu=None, raw_inverter=None):
        self.ipaddr = ipaddr
        self.port = port

        # what do we expect socket data to end in
        self.recv_suffix = b'END\n'

        # how long to wait on socket commands until we get our recv_suffix
        self.timeout = 10

        # how many times do we try the same command in a single update before failing
        self.cmd_attempts = 3

        # how big of a buffer to read at a time from the socket
        self.recv_size = 4096

        # how long to wait between socket open/closes
        self.socket_sleep_time = 5

        # should we close and re-open the socket between each command
        self.reopen_socket = False

        self.qs1_ids = [ "80" ]
        self.yc600_ids = [ "40" ]
        self.yc1000_ids = [ "50" ]
        self.ds3_ids = [ "70" ]
        self.all_ids = [ "40", "50", "70", "80" ]

        self.cmd_suffix = "END\n"
        self.ecu_query = "APS1100160001" + self.cmd_suffix
        self.inverter_query_prefix = "APS1100280002"
        self.inverter_query_suffix = self.cmd_suffix

        self.inverter_signal_prefix = "APS1100280030"
        self.inverter_signal_suffix = self.cmd_suffix

        self.inverter_byte_start = 26

        self.ecu_id = None
        self.qty_of_inverters = 0
        self.qty_of_online_inverters = 0
        self.lifetime_energy = 0
        self.current_power = 0
        self.today_energy = 0
        self.inverters = {}
        self.firmware = None
        self.timezone = None
        self.last_update = None
        self.vsl = 0
        self.tsl = 0

        self.ecu_raw_data = raw_ecu
        self.inverter_raw_data = raw_inverter
        self.inverter_raw_signal = None
        self.read_buffer = b''
        self.reader = None
        self.writer = None
        self.socket = None
        self.socket_open = False
        self.errors = []

    def read_from_socket(self):
        self.read_buffer = b''
        self.sock.settimeout(self.timeout)
        while self.read_buffer.find(self.recv_suffix) == -1:
            self.read_buffer += self.sock.recv(self.recv_size)
        return self.read_buffer

    def send_read_from_socket(self, cmd):
        try:
            self.sock.settimeout(self.timeout)
            self.sock.sendall(cmd.encode('utf-8'))
            time.sleep(self.socket_sleep_time)
            return self.read_from_socket()
        except Exception as err:
            self.close_socket()
            raise

    def close_socket(self):
        try:
            if self.socket_open:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.settimeout(self.timeout)
                data = self.sock.recv(self.recv_size) #flush incoming/outgoing data after shutdown request before actually closing the socket
                self.sock.close()
                self.socket_open = False
        except Exception as err:
            raise
            
    def open_socket(self):
        self.socket_open = False
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ipaddr, self.port))
            self.socket_open = True
        except Exception as err:
            raise

    def query_ecu(self):
        self.open_socket()
        cmd = self.ecu_query
        self.ecu_raw_data = self.send_read_from_socket(cmd)
        self.close_socket()
        try:
            self.process_ecu_data()
        except APSystemsInvalidData as err:
            raise
        if self.lifetime_energy == 0:
            error = f"ECU returned 0 for lifetime energy, raw data={self.ecu_raw_data}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        # Some ECUs likes the socket to be closed and re-opened between commands
        self.open_socket()
        cmd = self.inverter_query_prefix + self.ecu_id + self.inverter_query_suffix
        self.inverter_raw_data = self.send_read_from_socket(cmd)
        self.close_socket()
        
        # Some ECUs likes the socket to be closed and re-opened between commands
        self.open_socket()
        cmd = self.inverter_signal_prefix + self.ecu_id + self.inverter_signal_suffix
        self.inverter_raw_signal = self.send_read_from_socket(cmd)

        self.close_socket()

        data = self.process_inverter_data()
        data["ecu_id"] = self.ecu_id
        data["today_energy"] = self.today_energy
        data["lifetime_energy"] = self.lifetime_energy
        data["current_power"] = self.current_power
        data["qty_of_inverters"] = self.qty_of_inverters
        data["qty_of_online_inverters"] = self.qty_of_online_inverters
        return(data)
 
    def aps_int(self, codec, start):
        try:
            return int(binascii.b2a_hex(codec[(start):(start+2)]), 16)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to int location={start} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)
 
    def aps_short(self, codec, start):
        try:
            return int(binascii.b2a_hex(codec[(start):(start+1)]), 8)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to short int location={start} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

    def aps_double(self, codec, start):
        try:
            return int (binascii.b2a_hex(codec[(start):(start+4)]), 16)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to double location={start} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)
    
    def aps_bool(self, codec, start):
        return bool(binascii.b2a_hex(codec[(start):(start+2)]))
    
    def aps_uid(self, codec, start):
        return str(binascii.b2a_hex(codec[(start):(start+12)]))[2:14]
    
    def aps_str(self, codec, start, amount):
        return str(codec[start:(start+amount)])[2:(amount+2)]
    
    def aps_timestamp(self, codec, start, amount):
        timestr=str(binascii.b2a_hex(codec[start:(start+amount)]))[2:(amount+2)]
        return timestr[0:4]+"-"+timestr[4:6]+"-"+timestr[6:8]+" "+timestr[8:10]+":"+timestr[10:12]+":"+timestr[12:14]

    def check_ecu_checksum(self, data, cmd):
        datalen = len(data) - 1
        try:
            checksum = int(data[5:9])
        except ValueError as err:
            debugdata = binascii.b2a_hex(data)
            error = f"could not extract checksum int from '{cmd}' data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        if datalen != checksum:
            debugdata = binascii.b2a_hex(data)
            error = f"Checksum on '{cmd}' failed checksum={checksum} datalen={datalen} data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        start_str = self.aps_str(data, 0, 3)
        end_str = self.aps_str(data, len(data) - 4, 3)

        if start_str != 'APS':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect start signature '{start_str}' != APS data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        if end_str != 'END':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect end signature '{end_str}' != END data={debugdata}"
            self.add_error(error)
            raise APSystemsInvalidData(error)

        return True

    def process_ecu_data(self, data=None):
        if not data:
            data = self.ecu_raw_data
        #_LOGGER.warning(binascii.b2a_hex(data))
        self.check_ecu_checksum(data, "ECU Query")
        self.ecu_id = self.aps_str(data, 13, 12)
        self.qty_of_inverters = self.aps_int(data, 46)
        self.qty_of_online_inverters = self.aps_int(data, 48)
        self.vsl = int(self.aps_str(data, 52, 3))
        self.firmware = self.aps_str(data, 55, self.vsl)
        self.tsl = int(self.aps_str(data, 55 + self.vsl, 3))
        self.timezone = self.aps_str(data, 58 + self.vsl, self.tsl)
        self.lifetime_energy = self.aps_double(data, 27) / 10
        self.today_energy = self.aps_double(data, 35) / 100
        self.current_power = self.aps_double(data, 31)

    def process_signal_data(self, data=None):
        signal_data = {}
        if not data:
            data = self.inverter_raw_signal
        #_LOGGER.warning(binascii.b2a_hex(data))
        self.check_ecu_checksum(data, "Signal Query")
        if not self.qty_of_inverters:
            return signal_data
        location = 15
        for i in range(0, self.qty_of_inverters):
            uid = self.aps_uid(data, location)
            location += 6
            strength = data[location]
            location += 1
            strength = int((strength / 255) * 100)
            signal_data[uid] = strength
        return signal_data

    def process_inverter_data(self, data=None):

        output = {}
        
        if self.inverter_raw_data != '' and (self.aps_str(self.inverter_raw_data,9,4)) == '0002':
            data = self.inverter_raw_data
            #_LOGGER.warning(binascii.b2a_hex(data)) # for debug purposes only. Uncomment only the first # at the beginning
            self.check_ecu_checksum(data, "Inverter data")
            istr = ''
            cnt1 = 0
            cnt2 = 26
            if self.aps_str(data, 14, 2) == '00':
                timestamp = self.aps_timestamp(data, 19, 14)
                inverter_qty = self.aps_int(data, 17) 
                self.last_update = timestamp
                output["timestamp"] = timestamp
                output["inverter_qty"] = inverter_qty
                output["inverters"] = {}
                signal = self.process_signal_data()
                inverters = {}
                
                while cnt1 < inverter_qty:
                    inv={}
                    if self.aps_str(data, 15, 2) == '01':
                        inverter_uid = self.aps_uid(data, cnt2)
                        inv["uid"] = inverter_uid
                        inv["online"] = self.aps_bool(data, cnt2 + 6)
                        istr = self.aps_str(data, cnt2 + 7, 2)
                        inv["signal"] = signal.get(inverter_uid, 0)
                        if istr == '01':
                            power = []
                            voltages = []
                            inv["frequency"] = self.aps_int(data, cnt2 + 9) / 10
                            inv["temperature"] = self.aps_int(data, cnt2 + 11) - 100
                            power.append(self.aps_int(data, cnt2 + 13))
                            voltages.append(self.aps_int(data, cnt2 + 15))
                            power.append(self.aps_int(data, cnt2 + 17))
                            voltages.append(self.aps_int(data, cnt2 + 19))
                            output = {
                            "model" : "YC600/DS3",
                            "channel_qty" : 2,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(output)
                            cnt2 = cnt2 + 21
                        elif istr == '02':
                            power = []
                            voltages = []
                            inv["frequency"] = self.aps_int(data, cnt2 + 9) / 10
                            inv["temperature"] = self.aps_int(data, cnt2 + 11) - 100
                            power.append(self.aps_int(data, cnt2 + 13))
                            voltages.append(self.aps_int(data, cnt2 + 15))
                            power.append(self.aps_int(data, cnt2 + 17))
                            voltages.append(self.aps_int(data, cnt2 + 19))
                            power.append(self.aps_int(data, cnt2 + 21))
                            voltages.append(self.aps_int(data, cnt2 + 23))
                            power.append(self.aps_int(data, cnt2 + 25))
                            output = {
                            "model" : "YC1000",
                            "channel_qty" : 4,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(output)
                            cnt2 = cnt2 + 27
                        elif istr == '03':
                            power = []
                            voltages = []
                            inv["frequency"] = self.aps_int(data, cnt2 + 9) / 10
                            inv["temperature"] = self.aps_int(data, cnt2 + 11) - 100
                            power.append(self.aps_int(data, cnt2 + 13))
                            voltages.append(self.aps_int(data, cnt2 + 15))
                            power.append(self.aps_int(data, cnt2 + 17))
                            power.append(self.aps_int(data, cnt2 + 19))
                            power.append(self.aps_int(data, cnt2 + 21))
                            output = {
                            "model" : "QS1",
                            "channel_qty" : 4,
                            "power" : power,
                            "voltage" : voltages
                            }
                            inv.update(output)
                            cnt2 = cnt2 + 9
                        else:
                            cnt2 = cnt2 + 9
                        inverters[inverter_uid] = inv
                    cnt1 = cnt1 + 1
                self.inverters = inverters
                output["inverters"] = inverters
                return (output)
    
    def process_yc1000(self, data, location):

        power = []
        voltages = []
        power.append(self.aps_int(data, location))
        location += 2
        voltages.append(self.aps_int(data, location))
        location += 2
        power.append(self.aps_int(data, location))
        location += 2
        voltages.append(self.aps_int(data, location))
        location += 2
        power.append(self.aps_int(data, location))
        location += 2
        voltages.append(self.aps_int(data, location))
        location += 2
        power.append(self.aps_int(data, location))
        location += 2
        output = {
            "model" : "YC1000",
            "channel_qty" : 4,
            "power" : power,
            "voltage" : voltages
        }
        return (output, location)

    
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
    
    def process_ds3(self, data, location):
        power = []
        voltages = []
        for i in range(0, 2):
            power.append(self.aps_int(data, location))
            location += 2
            voltages.append(self.aps_int(data, location))
            location += 2
        output = {
            "model" : "DS3",
            "channel_qty" : 2,
            "power" : power,
            "voltage" : voltages,
        }
        return (output, location)

    def add_error(self, error):
        timestamp = datetime.datetime.now()
        self.errors.append(f"[{timestamp}] {error}")

    def dump_data(self):
        return {
            "ecu_id" : self.ecu_id,
            "qty_of_inverters" : self.qty_of_inverters,
            "qty_of_online_inverters" : self.qty_of_online_inverters,
            "lifetime_energy" : self.lifetime_energy,
            "current_power" : self.current_power,
            "today_energy" : self.today_energy,
            "firmware" : self.firmware,
            "timezone" : self.timezone,
            "lastupdate" : self.last_update,
            "ecu_raw_data" : str(binascii.b2a_hex(self.ecu_raw_data)),
            "inverter_raw_data" : str(binascii.b2a_hex(self.inverter_raw_data)),
            "inverter_raw_signal" : str(binascii.b2a_hex(self.inverter_raw_signal)),
            "errors" : self.errors,
            "inverters" : self.inverters
        }
