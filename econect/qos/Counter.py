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

import time
from abc import ABC, abstractmethod
from typing import Any

class TrameCounter(ABC):
	__slots__ = ()

	@abstractmethod
	def inc_send(self):
		pass

	@abstractmethod
	def inc_retrans(self):
		pass

class FileTrameCounter(TrameCounter):
	__slots__ = ('_sent_trames_count', '_file')

	def __init__(self, filename : str):
		super().__init__()
		self._sent_trames_count = None
		self._file = open(filename, 'a', buffering=1)

	def _write_line(self, val : Any):
		self._file.write(f'{time.time_ns()},{val}\n')

	def inc_send(self):
		self._write_line('T')

	def inc_retrans(self):
		self._write_line('R')

	def __del__(self):
		self._file.close()



class DummyTrameCounter(TrameCounter):
	__slots__ = ()

	def __init__(self):
		super().__init__()

	def inc_send(self):
		pass

	def inc_retrans(self):
		pass
