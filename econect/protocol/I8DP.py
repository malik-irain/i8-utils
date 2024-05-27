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
from enum import Flag
from functools import total_ordering
from struct import pack, unpack
from typing import Final, List, Optional

from digi.xbee.devices import XBee64BitAddress, XBeeDevice
from digi.xbee.exception import TimeoutException

import econect.protocol.I8TL as I8TL

'''
	I8DP : Datagram Protocol for IEEE 802.14.5

	                                                         6
	     0                   1                   2           7           
	     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 . . . . . 4 5 6 7 8 9
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	DAT.|  0x0  | FLAGS |       SEQ     |           Binary data         |
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

		FLAGS (from left to right):
			- BEGIN
			- IS ACK (cf. ACK. Trame)
			- NEEDS ACK
			- MORE FRAGMENTS

                                                                         6
	     0                   1                   2                       7
	     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 . . . . . . . . 2 3 4 5 6 7 8 9 
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	ACK.|  0x0  |0 1 0 0|       SEQ     |   ACK_SEQ 1   |       ...     |   ACK_SEQ n   |
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	     0                   1           
	     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	RST.|  0x0  |1 1 1 1|1 1 1 1 1 1 1 1|
	    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    
    This protocols allow to exchange unlimited amount of data 
    between two IEEE 802.14.5 devices.

    Data is first separated into chunks of `PAYLOAD_MAX_LEN` at most.
    It is recommanded to send a RST. trame first. Then chunks are sent
    in order in DAT. trames with:
    	- BEGIN flag set for the first trame and unset for the others
    	- MORE_FRAG flag set except for the last one
    	- NEEDS_ACK flag set each `BURST_MAX_LEN`, when seq number
    	  circle back to 0 or for the last trame
	
	If data has only one chunk, a single DAT. trame is sent, with BEGIN
	and NEEDS_ACKS flags set and MORE_FRAG flag unset.

	The recipient responds with a trame with IS_ACK flag set, each time 
	a trame with NEEDS_ACK set is received. The ACK trame is built using
	the same sequence number as the received trame and contains a list of
	previous non-acknowlegded trame (at most `BURST_MAX_LEN`).

'''

logger = logging.getLogger('i8-utils')

@total_ordering
class I8DP_Trame:
	'''
	A class to represent I8DP Trames.
	
	It allows to easily create the trames and to send and receive them
	in a binary format.
	'''
	BURST_MAX_LEN   : int        =  8
	PAYLOAD_MAX_LEN : Final[int] = 85


	class I8DPIncompatibleOptionsException(Exception):
		'''
		An exception to throw when I8DP_Flags are not compatible witch each other.
		'''
		def __init__(self, options : 'I8DP_Trame.I8DP_Flags'):
			self.message = "Selected options are incompatible ({})".format(options)
			super().__init__(self.message)

	class I8DPExceededPayloadMaxLenException(Exception):
		'''
		An exception to throw when payload size is bigger than `PAYLOAD_MAX_LEN`.
		'''
		def __init__(self, count : int):
			self.message = "Data should contain at most {} bytes (got {})".format(I8DP_Trame.PAYLOAD_MAX_LEN, count)
			super().__init__(self.message)

	class SequenceGenerator:
		'''
			A class to count sequence numbers
			starting over when `LIMIT` is reached.
		'''
		LIMIT : int = 256
		
		__slots__  = ('__value')

		def __init__(self, value: int=255) -> None:
			self.__value = value
	
		def current(self) -> int:
			'''
			Returns the current value
			'''
			return self.__value

		
		def next(self) -> int:
			'''
			Increments the value and returns it.
			'''
			self.__value = (self.__value + 1)%I8DP_Trame.SequenceGenerator.LIMIT
			return self.__value


	class I8DP_Flags(Flag):
		'''
		Flags for I8DP Trame:
			- I8DP_NONE for all flags unset
			- I8DP_RST to cancel an ongoing transmission and reset the receiver state
			- I8DP_BEGIN to signal the first packet of a transmission
			- I8DP_IS_ACK when the trame is an ACK one
			- I8DP_NEEDS_ACK to signal the receiver an ACK is needed for this trame (and all the previous non ACKd ones)
			- I8DP_MORE_FRAG to signal the transmitted data was separated 
		'''
		I8DP_RST       = I8TL.Protocol_ID.I8DP.value + 0b1111
		I8DP_NONE      = I8TL.Protocol_ID.I8DP.value + 0b0000
		I8DP_BEGIN     = I8TL.Protocol_ID.I8DP.value + 0b1000
		I8DP_IS_ACK    = I8TL.Protocol_ID.I8DP.value + 0b0100
		I8DP_NEEDS_ACK = I8TL.Protocol_ID.I8DP.value + 0b0010
		I8DP_MORE_FRAG = I8TL.Protocol_ID.I8DP.value + 0b0001
		

		def is_set(self, other : 'I8DP_Trame.I8DP_Flags') -> bool:
			'''
			To easily check if a flag is set
			'''
			return (self & other) == other

	__slots__ = ('_options', '_seq', '_data', '_ackd_trames')

	__sequence : 'I8DP_Trame.SequenceGenerator' = SequenceGenerator()

	def __init__(self, options : 'I8DP_Trame.I8DP_Flags' = I8DP_Flags.I8DP_NONE, data: bytes = None, seq: int = None, ackd_trames : List[int] = []):
		'''
		I8DP Trames constructor. Flags are set from the argument.
		Some checks are performed to create semanticaly correct trames.
		
		If it's a data trame: IS_ACK Flag should not be set in `options`, 
		`seq` and `ackd_trames` should not be set and `data` should be.

		If it's an acknoledgement trame: IS_ACK Flag should be set in `options`,
		`data` should not be set, `seq` should be set to the same number as 
		the trame answered and 	`ackd_trames` should be set if some previous trames are not acknowledged.
		'''
		self._options = options
		self._data = None
		self._seq = -1

		#An ACK Trame can't contain any other options
		if self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK|I8DP_Trame.I8DP_Flags.I8DP_MORE_FRAG) or self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK|I8DP_Trame.I8DP_Flags.I8DP_NEEDS_ACK) :
			raise I8DP_Trame.I8DPIncompatibleOptionsException(self._options)

		#If it's an ACK, you should provide a seq number to acknowledge
		#and if needed a list of other trames to acknowledge (but not too long).
		if self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK):
			if seq is None:
				raise ValueError("sequence number must be provided when building an ack trame.")
			if len(ackd_trames) > I8DP_Trame.PAYLOAD_MAX_LEN:
				raise I8DP_Trame.I8DPExceededPayloadMaxLenException(len(ackd_trames))
			
			self._seq = seq
			self._ackd_trames = ackd_trames			
		else:
			#if it's not an ACK data must be provided and not be too long
			if data is None:
				raise ValueError("data must be provided when it is a data packet (I8DP_IS_ACK flag is not set in options)")
			if len(data) > I8DP_Trame.PAYLOAD_MAX_LEN:
				raise I8DP_Trame.I8DPExceededPayloadMaxLenException(len(data))

			#if you provide a sequence number, it's useless it's automaticaly generated
			if seq is not None:
				logger.warning(f"[I8DP] Building data trame with a seq number ({seq}). Ignoring the provided seq number.")

			self._seq = I8DP_Trame.__sequence.next()
			self._data = data
		



	def __eq__(self, other : object) -> bool:
		'''
		Equality operator. Two I8DP trames are equals when they have
		the same sequence number.
		
		TODO: It *SHOULD* really be different if data is different.
		For that, (some of) the following operations should also
		be rewritten, and the usage of this functions (directly or
		indirectly should be checked and modified if needed)
		'''
		if isinstance(other, I8DP_Trame):
			return  self._seq == other._seq #and self._data == other._data
		if isinstance(other, int):
			return self._seq == other
		return NotImplemented

	def __lt__(self, other : object) -> bool:
		if isinstance(other, I8DP_Trame):
			return  self._seq < other._seq 
		if isinstance(other, int):
			return self._seq < other
		return NotImplemented

	def __hash__(self) -> int:
		return hash(self._seq)

	def __repr__(self) -> str:
		return self.__str__()

	def __str__(self) -> str:
		return str(self._seq)

	@property
	def data(self) -> bytes:
		'''
		Returns data associated with the trame, or empty bytes() if no data.
		'''
		if self._data is not None:
			return self._data
		return bytes()
		
	@property
	def seq(self) -> int:
		'''
		Returns the sequence number
		'''
		return self._seq

	@property
	def begin(self):
		'''
		Checks if the trame has the BEGIN flag set
		'''
		return self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_BEGIN)
	
	@property
	def is_rst(self):
		'''
		Checks if the trame has all flag sets (RST Trame).
		'''
		return self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_RST) and self._seq == (I8DP_Trame.SequenceGenerator.LIMIT - 1)
	
	@property
	def is_ack(self) -> bool:
		'''
		Checks if the trame has the IS_ACK flag set
		'''
		return self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK)

	@property
	def needs_ack(self) -> bool:
		'''
		Checks if the trame has the NEEDS_ACK flag set
		'''
		return self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_NEEDS_ACK)


	@property
	def more_frag(self):
		'''
		Checks if the trame has the MORE_FRAG flag set
		'''
		return self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_MORE_FRAG)
	
	@property
	def ack_list(self) -> List[int]:
		'''
		Returns the sequence number of all ackownledged trames (or [] if no ack)
		'''
		return ([self._seq] if self.is_ack else []) + [*self._ackd_trames]
		

	def unset_begin(self) -> None:
		'''
		Unset the BEGIN Flag
		'''
		self._options = self._options & ~I8DP_Trame.I8DP_Flags.I8DP_BEGIN

	def set_needs_ack(self) -> None:
		'''
		Set the NEEDS_ACK Flag
		'''
		self._options = self._options | I8DP_Trame.I8DP_Flags.I8DP_NEEDS_ACK


	def send(self, device : XBeeDevice, destination_addr : XBee64BitAddress, timeout : int = 3) -> Optional['I8DP_Trame']:
		'''
		Sends an I8DP Trame to `destination_addr` using `device` and waiting for an acknowlegdment
		if needed in `timeout` seconds.


		If an I8DP trame is received while needed (the trame NEEDS_ACK flag is set), it is checked
		and return if valid, otherwise None is returned.
		'''
		ack_received = False

		I8TL.i8tl_send_trame(device, destination_addr, self.to_bytes())
		if self.needs_ack:
			try:
				raw_response = device.read_data(timeout)
				if raw_response is not None and (raw_response.data[0] & I8TL.Protocol_ID.I8DP.value) == I8TL.Protocol_ID.I8DP.value:				
					i8dp_ack = I8DP_Trame.from_bytes(raw_response.data)
					ack_received = ((self.seq == i8dp_ack.seq) and i8dp_ack.is_ack)		
			except TimeoutException:
				logger.warning("[I8DP] Response for ack timed out.")

			if ack_received:
				return i8dp_ack
		
		return None



	def to_bytes(self) -> bytes:
		'''
		Converts an I8DP trame to its bytes representation
		'''
		res_byte_array = pack('BB', self._options.value, self._seq) 
		if not self._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK):
			if self._data is not None:
				res_byte_array += self._data
		else:
			for ack_seq in self._ackd_trames:
				res_byte_array += pack('B', ack_seq)
	
		return res_byte_array

	@staticmethod
	def from_bytes(byte_array : bytes) -> 'I8DP_Trame':
		'''
		Converts a bytes representation into an I8DP Trame
		'''
		i8dp_trame = I8DP_Trame.__new__(I8DP_Trame)
		i8dp_trame._options = I8DP_Trame.I8DP_Flags(byte_array[0])
		i8dp_trame._seq = unpack('B', byte_array[1:2])[0]
		i8dp_trame._data = None
		if not i8dp_trame._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_RST):
			if not i8dp_trame._options.is_set(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK):
				i8dp_trame._data = byte_array[2:]
			else:
				i8dp_trame._ackd_trames = []
				for ack_seq in byte_array[2:]:
					i8dp_trame._ackd_trames.append(unpack('B', bytes([ack_seq]))[0])

		return i8dp_trame


	@staticmethod
	def rst_trame() -> 'I8DP_Trame':
		'''
		Simply create a reset trame.
		'''
		logger.info('[I8DP] Building reset trame')
		rst_trame = I8DP_Trame.__new__(I8DP_Trame)
		
		rst_trame._options = I8DP_Trame.I8DP_Flags.I8DP_RST
		rst_trame._seq = I8DP_Trame.SequenceGenerator.LIMIT - 1
		
		rst_trame._ackd_trames = []
		rst_trame._data = None
		return rst_trame


	@staticmethod
	def data_trame(data : bytes, begin : bool = True, need_ack : bool = True, more_fragments : bool = False) -> 'I8DP_Trame':
		'''
		Create an I8DP_Trame containing data, and optional flags.
		'''
		logger.info(f'[I8DP] Building data trame.')
		options = I8DP_Trame.I8DP_Flags.I8DP_NONE
		if need_ack:
			options |= I8DP_Trame.I8DP_Flags.I8DP_NEEDS_ACK
		if more_fragments:
			options |= I8DP_Trame.I8DP_Flags.I8DP_MORE_FRAG
		if begin:
			options |= I8DP_Trame.I8DP_Flags.I8DP_BEGIN


		return I8DP_Trame(options, data)
	
	@staticmethod
	def ack_trame(seq : int, ackd_trames : List[int]) -> 'I8DP_Trame':
		'''
		Create an acknowlegdment I8DP_Trame for a `seq` number and a 
		`ackd_trames` list of other trames to acknowledge.
		'''
		logger.info(f'[I8DP] Building ack trame for {[seq] + ackd_trames}')
		return I8DP_Trame(I8DP_Trame.I8DP_Flags.I8DP_IS_ACK, seq=seq, ackd_trames=ackd_trames)
