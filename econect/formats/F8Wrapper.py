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

from os.path import basename
from struct import pack
from typing import Any


class F8Wrapper:

	PREAMBLE = 0xF8
	__slots__ = ('_name', '_mode', '_file', '_header', '_i', )

	def __init__(self, filename : str, mode : str):
		self._name = filename
		self._i = 0
		self._mode = mode

		filename = basename(filename)

		self._header = pack('BB', F8Wrapper.PREAMBLE, len(filename)) + bytes(filename, 'utf-8')
		self._file = open(self._name, self._mode)

	def __enter__(self) -> 'F8Wrapper':
		return self

	def __exit__(self, type : Any, value : Any, traceback : Any):
		self.close()

	def read(self, bytes_to_read : int = -1) -> bytes:
		ret = bytes()
		if bytes_to_read < 0:
			if bytes_to_read != -1:
				raise ValueError("read length must be non-negative or -1")

			ret = self._header[self._i:] + self._file.read(bytes_to_read)
			self._i = len(self._header)

		elif self._i < len(self._header):
				ret += self._header[self._i: self._i + bytes_to_read]
				self._i += len(ret)
				bytes_to_read -= len(ret)

		ret += self._file.read(bytes_to_read)
		return ret

	def close(self):
		self._file.close()
