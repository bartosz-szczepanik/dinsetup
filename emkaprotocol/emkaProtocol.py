import sys
from enum import Enum, auto
from .crc_RFC1331 import crc
from Crypto.Cipher import AES


import datetime
import random
start_stop_character = bytes([0x23])

MAX_FRAME_DATA_LENGTH = 528
COMMANDS_COUNT = 25
BLOCK_SIZE = 16

crc_len = 2
start_stop_character_len = 1
ENDIANNESS = sys.byteorder
header_length = 6


class Commands(Enum):
    CMD_LOG = auto()
    CMD_VERSION = auto()
    CMD_CONFIG = auto()
    CMD_DEBUGLEVEL = auto()
    CMD_MEMORY_ERASE = auto()
    CMD_MEMORY_WRITE = auto()
    CMD_MEMORY_READ = auto()
    CMD_RESTART = auto()
    CMD_MAIN_STATUS = auto()
    CMD_MODEM_AT = auto()
    CMD_TEST_STATUS = auto()
    CMD_TEST_START = auto()
    CMD_SET_SERIAL = auto()
    CMD_SEND_WMBUS = auto()
    CMD_EVENT_READ = auto()
    CMD_EVENT_CLEAR = auto()
    CMD_EVENT_STATUS = auto()
    CMD_EVENT_READDATE = auto()
    CMD_RADIO_CARRIER = auto()
    CMD_MODEM_RESET = auto()
    CMD_MODEM_FIRMWARE_VERSION = auto()
    CMD_RADIO_PM9 = auto()
    CMD_RADIO_RESERVED = auto()
    CMD_RADIO_RESTART = auto()
    CMD_MODEM_UPDATE_FIRMWARE = auto()
    CMD_PASSWORD_AUTH = 28





class Packet:
    cmd = 0
    id = 0
    count = 0
    frame_in_command = 0
    data = bytes()
    data_length = 0
    crc = bytes()
    is_encrypted = False

    def __init__(self, *args, **kwargs):
        self.timestamp = datetime.datetime.now()
        if args and kwargs:
            raise AttributeError("Creation only with one of two args or kwargs")
        if args:
            self.__deserialize__(*args)
        if kwargs:
            self.__init_by_parameters(**kwargs)

    def __init_by_parameters(self, cmd=0, fr_id=0, count=1, frame_in_command=1, data=bytes(), data_length=0, crc_dat=0):
        self.cmd = cmd
        self.id = fr_id
        self.count = count
        self.frame_in_command = frame_in_command
        self.data = data
        self.data_length = data_length
        self.crc = crc_dat

    def __deserialize__(self, data):
        self.cmd = int(data[1])
        self.id = int(data[2])
        self.frame_in_command = int(data[3])
        self.count = int(data[4])
        self.data_length = int.from_bytes(data[5:6], ENDIANNESS)
        self.data = data[7:(len(data)-3)]
        dat = data[len(data)-3:len(data)-1]
        self.crc = int.from_bytes(dat, ENDIANNESS)

    def __half_bytes__(self):
        return self.cmd.to_bytes(byteorder=ENDIANNESS, length=1) + \
               self.id.to_bytes(byteorder=ENDIANNESS, length=1) + \
               self.frame_in_command.to_bytes(byteorder=ENDIANNESS, length=1) + \
               self.count.to_bytes(byteorder=ENDIANNESS, length=1) + \
               self.data_length.to_bytes(byteorder=ENDIANNESS, length=2) + self.data

    def __bytes__(self):
        return start_stop_character + \
               self.__half_bytes__() + self.crc.to_bytes(byteorder=ENDIANNESS, length=2) + start_stop_character

    def __repr__(self):
        return str(self.__bytes__())

    def calculate_crc(self):
        return crc(0, self.__half_bytes__())

    def set_crc(self):
        try:
            self.crc = self.calculate_crc()
        except:
            pass
    def set_header(self, data):
        self.cmd = int(data[0])
        self.id = int(data[1])
        self.frame_in_command = int(data[2])
        self.count = int(data[3])
        self.data_length = int.from_bytes(data[4:], ENDIANNESS)

    def set_data(self, data):
        self.data = data


class EmkaProtocol:

    received = 0
    in_buffer = bytes()
    messages = []

    def __init__(self, key=bytes([0x7e, 0x15, 0x2b, 0x19, 0x22, 0xea, 0x8f, 0xb7,
                                  0xc6, 0x35, 0x22, 0x6a, 0x4a, 0x2f, 0x1f, 0x3c])):
        self.msg_id = random.randint(0, 255)
        self.key = key
        if key is not None:
            self.useAes = True

    def build_message(self, cmd: Commands, data: bytes):
        if self.msg_id >= 255:
            self.msg_id = 0
        self.msg_id += 1
        packets = []
        fragments = [data[i:i + MAX_FRAME_DATA_LENGTH] for i in range(0, len(data), MAX_FRAME_DATA_LENGTH)]
        for i, fragment in enumerate(fragments):
            packet = Packet(cmd=cmd, fr_id=self.msg_id, count=len(fragments),
                            frame_in_command=i+1, data=bytes(), data_length=0, crc_dat=0)  # pakiet z uzupełnionym headerem

            if self.useAes:
                initial_length = len(fragment)
                rest = len(fragment) % BLOCK_SIZE
                if rest != 0:
                    rest = BLOCK_SIZE - rest
                    fragment += b'\x00'*rest
                    #fragment += Random.new().read(rest)

                #iv = Random.new().read(BLOCK_SIZE)
                aes = AES.new(self.key, AES.MODE_ECB)#, iv)
                final_fragment = aes.encrypt(fragment)
                final_fragment = initial_length.to_bytes(2, byteorder=ENDIANNESS)+final_fragment
            else:
                final_fragment = fragment
            packet.data = final_fragment
            packet.data_length = len(final_fragment)
            packet.set_crc()
            packets.append(packet)
        return packets

    @staticmethod
    def decode_from_buffer(buffer):
        can_decode_packet = True
        decoded_packets = []
        while can_decode_packet:
            if len(buffer) < 9:
                break
            if bytes([buffer[0]]) != start_stop_character:
                buffer = buffer[1:]
                continue
            packet = Packet()
            packet.set_header(buffer[start_stop_character_len:header_length+start_stop_character_len])
            if len(buffer) < packet.data_length+header_length+crc_len+start_stop_character_len*2:
                break
            else:
                oldbuff = buffer
                lenbuf = len(buffer)
                buffer = buffer[start_stop_character_len:]
                buffer = buffer[header_length:]
                packet.data = buffer[:packet.data_length]
                buffer = buffer[packet.data_length:]
                packet.crc = int.from_bytes(buffer[:crc_len], ENDIANNESS)
                buffer = buffer[crc_len:]
                if bytes([buffer[0]]) != start_stop_character:
                    with open("dump", "wb") as file:
                        file.write(oldbuff)

                    raise ValueError("There is no stop character on the end of packet. \nPacket: {0}, buffer: {1} {2}".format(packet.data, oldbuff, lenbuf))
                buffer = buffer[start_stop_character_len:]
                decoded_packets.append(packet)

        return buffer, decoded_packets

    def decrypt_packets(self, packets):

        decrypted_packets = []
        for packet in packets:
            data = packet.data[2:]
            #iv = Random.new().read(BLOCK_SIZE)
            aes = AES.new(self.key, AES.MODE_ECB)#, iv)
            if len(data) % 16:
                # known bug with log decryption there is two bytes less than it should be
                data+=b"00"
            decrypted = aes.decrypt(data)
            decrypted = decrypted[:int.from_bytes(packet.data[:2], ENDIANNESS)]
            packet.data = decrypted
            packet.is_encrypted = False
            decrypted_packets.append(packet)
        return decrypted_packets

    def get_packet_from_buffer(self, buffer):
        buffer, packets = self.decode_from_buffer(buffer)
        if self.useAes:
            packets = self.decrypt_packets(packets)
        return buffer, packets
