#!/usr/bin/env python3

from APSystemsECUR import APSystemsECUR
import time
import asyncio
from pprint import pprint

ecu_ip = "192.168.0.251"
sleep = 60

loop = asyncio.get_event_loop()
ecu = APSystemsECUR(ecu_ip)

while True:
    try:
        data = loop.run_until_complete(ecu.async_query_ecu())
        print(f"[OK] Timestamp: {data.get('timestamp')} Current Power: {data.get('current_power')}")
        pprint(data)
    except Exception as err:
        print(f"[ERROR] {err}")

    print(f"Sleeping for {sleep} sec")
    time.sleep(sleep)


