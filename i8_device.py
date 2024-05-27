#!/usr/bin/env python3

# Copyright (C) 2021-2023  Malik Irain
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

import os
import logging
import shutil

from pathlib import Path
from sys import argv, exit
from time import sleep

from threading import Event
from watchdog.observers import Observer
from watchdog.events import FileCreatedEvent, PatternMatchingEventHandler


from config import LOG_DIR, FILES_TO_SEND_DIR, FILES_SENT_DIR
from econect.formats import NeoCayenneLPP
from econect.protocol.I8TL import DataSender

logger = logging.getLogger('i8-utils')

def setup_watchdog(ds):
	def on_created(event):
		logger.info(f'[I8-D] File {event.src_path} to send.')
		ds.notify_file_to_send(event.src_path)
		try:
			shutil.move(event.src_path, FILES_SENT_DIR)
		except:
			logger.warning("[I8-D] File {event.src_path} can not be moved: already present in destination folder")
			try:
				os.remove(event.src_path)
			except FileNotFoundError:
				logger.error(f'[I8-D] Removing {event.src_path} failed: file already removed"')


	patterns = ["*"]
	ignore_patterns = None
	ignore_directories = True
	case_sensitive = False
	my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
	my_event_handler.on_created = on_created



	go_recursively = True
	observer = Observer()
	logger.info(f'[I8-D] Monitoring {FILES_TO_SEND_DIR} for files to send')
	observer.schedule(my_event_handler, FILES_TO_SEND_DIR, recursive=go_recursively)
	observer.start()

	for file in os.listdir(FILES_TO_SEND_DIR):
		filename = os.path.join(FILES_TO_SEND_DIR, file)
		event = FileCreatedEvent(filename)
		on_created(event)

	return observer

if __name__ == "__main__":
	devfile       = "/dev/ttyUSB0"
	bauds         = 230400

	if len(argv) > 1:
		devfile = argv[1]
 
	ds = DataSender(path=devfile, speed=bauds, del_dir=True, self_stop=False, qos_info=False, log_dir=LOG_DIR, response_timeout=1, retries=3)
	obs = setup_watchdog(ds)

	try:
		while True:
			Event().wait()

	except KeyboardInterrupt:

		pass
	finally:
		obs.stop()
		obs.join()
		ds.stop()
