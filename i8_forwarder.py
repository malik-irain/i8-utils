#!/usr/bin/env python3

# Copyright (C) 2021  Malik Irain
# This file is part of econect-i8-utils.
#
# econect-i8-utils is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# econect-i8-utils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with econect-i8-utils.  If not, see <http://www.gnu.org/licenses/>.


import mmap
import os
from sys import argv
from typing import cast

import requests
import time
import base64
import json


from config import LOG_DIR, SERVER_URL
from econect.protocol.I8TL import DataReceiver

if __name__ == '__main__':
	devfile : str = "/dev/ttyUSB1"
	bauds   : int = 230400

	broker  : str = ""
	port    : int = 0

	
	if len(argv) > 1:
		devfile = argv[1]
	if len(argv) > 2:
		file_to_send = argv[2]
	
	dr : DataReceiver = DataReceiver(path=devfile, speed=bauds, self_stop=True, del_dir=True, log_dir=LOG_DIR, thread_inactive_time_limit=60)
	
	
	try:
		while True:
			filename = dr.get_data_filename()
			node_addr = filename.split('/')[-1].split('-')[1]
			
			with open(filename, 'rb') as file:
				with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mm:
					done = False
					data = {
						'node'    :  node_addr,
						'content' :  base64.b64encode(cast(bytes, mm)).decode("utf-8")
					}
					while not done:
						try:
							# OLD Version
							# r = requests.post(SERVER_URL, 
							# 	data=cast(bytes,mm), 
							# 	headers={"Content-Type": "application/octet-stream"},
							# 	timeout=5)

							# NEW Version
							# r = requests.post(SERVER_URL, 
							#  	data=json.dumps(data), 
							#  	headers={"Content-Type": "application/json"},
							#  	timeout=5)
							# print(f'[{r.status_code}] {r.content.decode("utf-8")}')
							done = True
						except requests.exceptions.RequestException as re:
							print(f"Couldn't send {filename} to {SERVER_URL}")
							print(re)
							time.sleep(10)
			os.remove(filename)
	except KeyboardInterrupt:
		exit(0)
