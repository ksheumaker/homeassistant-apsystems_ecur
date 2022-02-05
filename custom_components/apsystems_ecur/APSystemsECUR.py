#!/usr/bin/env python3

import asyncio
import socket
import binascii
import datetime
import json
import logging

_LOGGER = logging.getLogger(__name__)

from pprint import pprint

class APSystemsInvalidData(Exception):
    pass

class APSystemsInvalidInverter(Exception):
    pass


class APSystemsECUR:

    def __init__(self, ipaddr, port=8899, raw_ecu=None, raw_inverter=None):
        self.ipaddr = ipaddr
        self.port = port

        # what do we expect socket data to end in
        self.recv_suffix = b'END\n'

        # how long to wait on socket commands until we get our recv_suffix
        self.timeout = 5

        # how many times do we try the same command in a single update before failing
        self.cmd_attempts = 3

        # how big of a buffer to read at a time from the socket
        self.recv_size = 4096

        # how long to wait between socket open/closes
        self.socket_sleep_time = 2.0

        self.qs1_ids = [ "802", "801", "804", "806" ]
        self.yc600_ids = [ "406", "407", "408", "409" ]
        self.yc1000_ids = [ "501", "502", "503", "504" ]
        self.ds3_ids = [ "703", "704" ]

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

        self.socket_open = False

        self.errors = []

    async def async_read_from_socket(self):
        self.read_buffer = b''
        end_data = None

        data = await self.reader.readline()
        if data == b'':
            error = f"Got empty string from socket"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        size = len(data)
        end_data = data[size-4:]
        if end_data != self.recv_suffix:
            error = f"End suffix ({self.recv_suffix}) missing from ECU response end_data={end_data} data={data}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        self.read_buffer = data
        return self.read_buffer

    async def async_send_read_from_socket(self, cmd):
        current_attempt = 0
        while current_attempt < self.cmd_attempts:
            current_attempt += 1

            self.writer.write(cmd.encode('utf-8'))
            await self.writer.drain()

            try:
                return await asyncio.wait_for(self.async_read_from_socket(), 
                    timeout=self.timeout)
            except APSystemsInvalidData as err:
                _LOGGER.warning(f"Invalid data from ECU after issuing cmd={cmd.rstrip()} error={err}. Closing socket and trying again try {current_attempt} of {self.cmd_attempts}")
                await self.async_reopen_socket()
                pass
                
            except Exception as err:
                # if we get a timeout or invalid data we close the socket 
                # and try again
                _LOGGER.warning(f"Error from ECU after issuing cmd={cmd.rstrip()} error={err}. Closing socket and trying again try {current_attempt} of {self.cmd_attempts}")
                await self.async_reopen_socket()
                pass

        await self.async_close_socket()
        error = f"Incomplete data from ECU after {current_attempt} attempts, cmd='{cmd.rstrip()}' data={self.read_buffer}"
        self.errors.append(error)
        raise APSystemsInvalidData(error)

    async def async_close_socket(self):
        if self.socket_open:
            self.writer.close()
            await self.writer.wait_closed()
            self.socket_open = False

    async def async_reopen_socket(self):
        await self.async_close_socket()

        # sleep X seconds before re-opening the socket
        await asyncio.sleep(self.socket_sleep_time)

        return await self.async_open_socket()

    async def async_open_socket(self):
        _LOGGER.debug(f"Connecting to ECU on {self.ipaddr} {self.port}")
        self.reader, self.writer = await asyncio.open_connection(self.ipaddr, self.port)
        _LOGGER.debug(f"Connected to ECU {self.ipaddr} {self.port}")
        self.socket_open = True


    async def async_query_ecu(self):

        await self.async_open_socket()

        cmd = self.ecu_query
        self.ecu_raw_data = await self.async_send_read_from_socket(cmd)
        self.async_close_socket()

        self.process_ecu_data()

        if self.lifetime_energy == 0:
            await self.async_close_socket()
            error = f"ECU returned 0 for lifetime energy, raw data={self.ecu_raw_data}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        # the ECU likes the socket to be closed and re-opened between commands
        await self.async_reopen_socket()

        cmd = self.inverter_query_prefix + self.ecu_id + self.inverter_query_suffix
        self.inverter_raw_data = await self.async_send_read_from_socket(cmd)

        # the ECU likes the socket to be closed and re-opened between commands
        await self.async_reopen_socket()

        cmd = self.inverter_signal_prefix + self.ecu_id + self.inverter_signal_suffix
        self.inverter_raw_signal = await self.async_send_read_from_socket(cmd)

        await self.async_close_socket()

        data = self.process_inverter_data()
        data["ecu_id"] = self.ecu_id
        data["today_energy"] = self.today_energy
        data["lifetime_energy"] = self.lifetime_energy
        data["current_power"] = self.current_power
        data["qty_of_inverters"] = self.qty_of_inverters
        data["qty_of_online_inverters"] = self.qty_of_online_inverters

        return(data)
    
    def query_ecu(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ipaddr,self.port))

        sock.sendall(self.ecu_query.encode('utf-8'))
        self.ecu_raw_data = sock.recv(self.recv_size)

        self.process_ecu_data()

        cmd = self.inverter_query_prefix + self.ecu_id + self.inverter_query_suffix
        sock.sendall(cmd.encode('utf-8'))
        self.inverter_raw_data = sock.recv(self.recv_size)

        cmd = self.inverter_signal_prefix + self.ecu_id + self.inverter_signal_suffix
        sock.sendall(cmd.encode('utf-8'))
        self.inverter_raw_signal = sock.recv(self.recv_size)

        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

        data = self.process_inverter_data()

        data["ecu_id"] = self.ecu_id
        data["today_energy"] = self.today_energy
        data["lifetime_energy"] = self.lifetime_energy
        data["current_power"] = self.current_power


        return(data)
 
    def aps_int(self, codec, start):
        try:
            return int(binascii.b2a_hex(codec[(start):(start+2)]), 16)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to int location={start} data={debugdata}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)
 
    def aps_short(self, codec, start):
        try:
            return int(binascii.b2a_hex(codec[(start):(start+1)]), 8)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to short int location={start} data={debugdata}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

    def aps_double(self, codec, start):
        try:
            return int (binascii.b2a_hex(codec[(start):(start+4)]), 16)
        except ValueError as err:
            debugdata = binascii.b2a_hex(codec)
            error = f"Unable to convert binary to double location={start} data={debugdata}"
            self.errors.append(error)
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
            error = f"Error getting checksum int from '{cmd}' data={debugdata}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        if datalen != checksum:
            debugdata = binascii.b2a_hex(data)
            error = f"Checksum on '{cmd}' failed checksum={checksum} datalen={datalen} data={debugdata}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        start_str = self.aps_str(data, 0, 3)
        end_str = self.aps_str(data, len(data) - 4, 3)

        if start_str != 'APS':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect start signature '{start_str}' != APS data={debugdata}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        if end_str != 'END':
            debugdata = binascii.b2a_hex(data)
            error = f"Result on '{cmd}' incorrect end signature '{end_str}' != END data={debugdata}"
            self.errors.append(error)
            raise APSystemsInvalidData(error)

        return True

    def process_ecu_data(self, data=None):
        if not data:
            data = self.ecu_raw_data

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
        if not data:
            data = self.inverter_raw_data

        self.check_ecu_checksum(data, "Inverter data")

        output = {}

        timestamp = self.aps_timestamp(data, 19, 14)
        inverter_qty = self.aps_int(data, 17)

        self.last_update = timestamp
        output["timestamp"] = timestamp
        output["inverter_qty"] = inverter_qty
        output["inverters"] = {}

        # this is the start of the loop of inverters
        location = self.inverter_byte_start

        signal = self.process_signal_data()

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

            inv["signal"] = signal.get(inverter_uid, 0)

            # the first 3 digits determine the type of inverter
            inverter_type = inverter_uid[0:3]
            if inverter_type in self.yc600_ids:
                (channel_data, location) = self.process_yc600(data, location)
                inv.update(channel_data)    

            elif inverter_type in self.qs1_ids:
                (channel_data, location) = self.process_qs1(data, location)
                inv.update(channel_data)
            
            elif inverter_type in self.yc1000_ids:
                (channel_data, location) = self.process_yc1000(data, location)
                inv.update(channel_data)
                
            elif inverter_type in self.ds3_ids:
                (channel_data, location) = self.process_ds3(data, location)
                inv.update(channel_data)    

            else:
                error = f"Unsupported inverter type {inverter_type} please create GitHub issue."
                self.errors.append(error)
                raise APSystemsInvalidData(error)

            inverters[inverter_uid] = inv

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


