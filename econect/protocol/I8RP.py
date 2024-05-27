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
from struct import pack
from typing import Optional, Union

from digi.xbee.devices import XBee16BitAddress, XBee64BitAddress, XBeeDevice
from digi.xbee.exception import TimeoutException

import econect.protocol.I8TL as I8TL

'''
	I8RP : Resolution Protocol for IEEE 802.14.5
	
	 0              
	 0 1 2 3 4 5 6 7
	+-+-+-+-+-+-+-+-+
	|  0xF  | Ignor.|
	+-+-+-+-+-+-+-+-+

	This protocol allows to exchange IEEE 802.14.5 64 bit addresses
	between an end device and its coordinator.

	The end device will simply send a I8RP trame to its coordinator,
	by using it's known 16 bit address (0x0000), which will respond
	with an another I8RP, thus giving its 64 bit address.

	The 64 bit address is not included in I8RP trames but are available
	at the MAC Layer, which gives us this information.


	The trame is composed of a 4 bit Protocol ID (0xF) helping to
	identify layer 3 protocols and of 4 reserved bits which should be 
	set to 0.


'''

logger = logging.getLogger('i8-utils')



class I8RP_Trame:
	'''
	A class to represent I8RP Trames.
	
	It allows to easily create the trames and to send and receive them
	in a binary format.
	'''

	__slots__ = ('_protocol_id')


	def __init__(self):
		self._protocol_id = I8TL.Protocol_ID.I8RP

	def __eq__(self, other : object) -> bool:
		'''
		Equality operator. Two I8RP trames are always equals.
		'''
		if not isinstance(other, I8RP_Trame):
			return NotImplemented
		return self._protocol_id.value == other._protocol_id.value

	def to_bytes(self) -> bytes:
		'''
		Converts an I8RP trame to its bytes representation
		'''
		res_byte_array = pack('B', self._protocol_id.value) 
		return res_byte_array

	@staticmethod
	def from_bytes(byte_array : bytes) -> 'I8RP_Trame':
		'''
		Converts a bytes representation into an I8RP Trame
		'''
		i8rp_trame = I8RP_Trame.__new__(I8RP_Trame)

		i8rp_trame._protocol_id = I8TL.Protocol_ID(byte_array[0])	
		return i8rp_trame

	def send(self, device : XBeeDevice, destination_addr : Union[XBee64BitAddress, XBee16BitAddress] = XBee16BitAddress.from_hex_string("0000"), retries : int = 1, timeout : int = 3) -> Optional[XBee64BitAddress]:
		'''
		Sends an I8RP Trame to `destination_addr` using `device` and waiting for a response
		if needed in `timeout` seconds.

		If an I8RP trame is received before running out of retries, the 64 bit address is extracted from the MAC Layer. Otherwise,
		`None` is returned.
		'''
		coord64BitAddr = None
		tries = 1

		while coord64BitAddr is None and tries <= retries:
			logger.info(f'[I8RP] Sending from: {device.get_64bit_addr()}. To: {destination_addr}.')
			I8TL.i8tl_send_trame(device, destination_addr, self.to_bytes())

			#If you use a 64 bit address, it's not a request, so no need to wait for response!
			if isinstance(destination_addr, XBee64BitAddress):
				break
			try:
				raw_response = device.read_data(timeout)
				if raw_response is not None and (raw_response.data[0] & I8TL.Protocol_ID.I8RP.value) == I8TL.Protocol_ID.I8RP.value:				
					coord64BitAddr = raw_response.remote_device.get_64bit_addr()
					logger.info(f'[I8RP] Received response with address: {coord64BitAddr}.')
			
			except TimeoutException:
				logger.warning(f"[I8RP] Response timeout")
			tries+=1

		return coord64BitAddr
