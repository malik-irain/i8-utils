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

import logging
import time
from enum import Flag
from struct import pack
from typing import Final, Optional

from digi.xbee.devices import XBee64BitAddress, XBeeDevice
from digi.xbee.exception import TimeoutException

import econect.protocol.I8TL as I8TL

'''
	I8TP : Time Protocol for IEEE 802.14.5

	
	     0              
	     0 1 2 3 4 5 6 7
	    +-+-+-+-+-+-+-+-+
	RQ. |  0xA  |  REQ  |
	    +-+-+-+-+-+-+-+-+


	     0                   1                   2                   3                   4                   5                   6                   7  
	     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	RS. |  0xA  |  RES  |                                                 64-bit timestamp (Big Endian)                                                 |
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


	This protocol allows to exchange system time from network coordinator
	to end devices using Cristian's algorithm.

	To avoid usage of program with admin. rights it is recommanded *NOT TO USE*
	the `__set_time_on_linux` function but to use `i8tp_request_delta` thus not
	modifying system clock.

	The end device simply sends a request (Trame RQ.) to its coordinator
	using `i8tp_request_delta` and receive a `delta`. It represents the difference 
	between their clocks. `delta` should then be added to each time measure of devices
	to get an idea of server side time. 

	When receiving a request, the server responds with a response trame (Trame RS.)
	which contains the timestamp measured at reception.

'''




logger = logging.getLogger('i8-utils')


class I8TP_Trame:
	'''
	A class to represent I8TP Trames.
	
	It allows to easily create the trames and to send and receive them
	in a binary format.
	'''

	class I8TP_Type(Flag):
		'''
		Flag type to represent types of I8TP Trames
			- I8TP_TIME_REQ for requests
			- I8TP_TIME_RES for response
		'''
		I8TP_TIME_REQ =  I8TL.Protocol_ID.I8TP.value + 0b0000
		I8TP_TIME_RES =  I8TL.Protocol_ID.I8TP.value + 0b0001 
		
		def is_set(self, other : 'I8TP_Trame.I8TP_Type') -> bool:
			'''
			To easily check if a flag is set
			'''
			return (self & other) == other

	__slots__ = ('_options', '_time')

	
	def __init__(self, options: I8TP_Type=I8TP_Type.I8TP_TIME_REQ) -> None:
		'''
		I8TP Trames constructor. Options are set from the argument.
		Time is set if the trame is a request.
		'''
		self._options = options
		self._time = None
		if self.is_res:
			self._time = time.time_ns().to_bytes(8, 'big')



	def __eq__(self, other : object) -> bool :
		'''
		Equality operator. Two I8RP trames are equals when they're the same type
		(two REQ trames are always equals) and when their time are equals.
		'''
		if not isinstance(other, I8TP_Trame):
			return NotImplemented
		return self._options.value == other._options.value and self._time == other._time

	@property
	def time(self) -> Optional[int]:
		'''
			Returns the time of a response trame, if existing.
		'''
		if not self.is_res or self._time is None:
			return None
		return int.from_bytes(self._time, 'big')


	@property
	def is_req(self) -> bool:
		'''
		Checks if the trame is a request one
		'''
		return self._options.is_set(I8TP_Trame.I8TP_Type.I8TP_TIME_REQ)

	@property
	def is_res(self) -> bool:
		'''
		Checks if the trame is a response one
		'''
		return self._options.is_set(I8TP_Trame.I8TP_Type.I8TP_TIME_RES)
	

	def to_bytes(self) -> bytes:
		'''
		Converts an I8TP trame to its bytes representation
		'''
		res_byte_array = pack('B', self._options.value) 
		if  self.is_res and self._time is not None:
			res_byte_array += self._time
	
		return res_byte_array

	@staticmethod
	def from_bytes(byte_array : bytes) -> 'I8TP_Trame':
		'''
		Converts a bytes representation into an I8TP Trame
		'''
		i8tp_trame = I8TP_Trame.__new__(I8TP_Trame)
		i8tp_trame._options = I8TP_Trame.I8TP_Type(byte_array[0])


		if  i8tp_trame.is_res:
			i8tp_trame._time = byte_array[1:]

		return i8tp_trame

	@staticmethod
	def _set_time_on_linux(time_ns : float) -> bool:
		'''
		A method to set system clock at a given `time_ns` value on Linux,
		using librt's clock_settime.

		WARNING: root access is needed in order to set the clock. 
		'''
		# import ctypes
		# import ctypes.util

		# CLOCK_REALTIME : Final[int] = 0

		# class timespec(ctypes.Structure):
		# 	_fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

		# librt = ctypes.CDLL(ctypes.util.find_library("rt"))
		
		# ts = timespec()
		# ts.tv_sec = int(time_ns*10e-9)
		# ts.tv_nsec = int(time_ns - ts.tv_sec*10e9)

		# return librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts)) == 0
		
		import subprocess
		subprocess.check_call(['date', '+"%s.%N"', '-s', f'@{time_ns}'])

	
	def send(self, device : XBeeDevice, destination_addr : XBee64BitAddress, retries : int = 3, timeout : int = 3, coeff : float = 0.65) -> Optional[int]:
		'''
			Generate a request for the time of the system at `destination_addr` (generaly the coordinator) using 
			the device `device` to communicate, trying `retries` times and each time waiting for a response in `timeout` seconds.

			If an I8TP response trame is received before running out of retries and contains a valid time, this value is extracted
			and used alongside with the time it took to receive it (the rtt) to compute the `delta`. Otherwise, 0 is returned.

			To compute `delta` Cristian's algorithm with a higher coefficient is used. It should be rtt*0.5,
			but RTT is not symetrical, more time is spent on the server side, hence the higher coef. (0.65)
		
		'''
		time_after_send = 0
		server_time = -1
		rtt = -1
		tries = 1

		delta = 0

		while server_time == -1 and tries <= retries:

			#Produces "[I8TP] Sending request (try {tries}/{retries})" if the current trame is a request,
			#and "[I8TP] Sending response: {self.time}" otherwise.
			logger.info(f"[I8TP] Sending {'request (try ' + str(tries) + '/' + str(retries) + ')' if self.is_req else 'response: ' + str(self.time)}")
			time_before_send = time.time_ns()
			I8TL.i8tl_send_trame(device, destination_addr, self.to_bytes())
			if self.is_res:
				return None
			try:
				raw_response = device.read_data(timeout)
				time_after_send = time.time_ns()
				if raw_response is not None and (raw_response.data[0] & 0xF0) == I8TL.Protocol_ID.I8TP.value:	
					i8tp_response = I8TP_Trame.from_bytes(raw_response.data)
					if i8tp_response.time:
						server_time = i8tp_response.time 
					rtt = time_after_send - time_before_send
					logger.info(f'[I8TP] Received response with time: {server_time}. Took {rtt} ns.')
			except TimeoutException:
				logger.warning(f"[I8TP] Response timeout")
			tries+=1

		if server_time == -1:
			delta = 0
			logger.warning(f"[I8TP] No valid answer received. Delta is set to 0")
		else:
			delta = round(server_time + rtt*coeff) - time_after_send
			logger.info(f"[I8TP] Delta is {delta} ns")
		
		return delta
