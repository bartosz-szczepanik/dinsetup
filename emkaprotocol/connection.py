from enum import Enum, auto
from .emkaProtocol import EmkaProtocol, Packet
from threading import Thread
from serial import Serial
from typing import List
import datetime


class ConnType(Enum):
    CON_SERIAL = auto()
    CON_TCP = auto()


class ConnParams(Enum):
    PORT = auto()
    BAUD = auto()
    ADRESS = auto()
    TIMEOUT = auto()


def get_messages_from_packets(packets: List[Packet]):
    messages = []
    multi_frame = {}
    for p in packets:
        if p.count == 1:
            messages.append((p.cmd, p.id, p.data))
            packets.remove(p)
        else:
            if p.id not in multi_frame.keys():
                multi_frame[p.id] = [p]
            else:
                multi_frame[p.id].append(p)
                if len(multi_frame[p.id]) == p.count:
                    message = b""
                    prev_frame_nr = 0
                    error = False
                    for frame in sorted(multi_frame[p.id], key=lambda fram: fram.frame_in_command):
                        if prev_frame_nr == frame.frame_in_command:
                            error = True
                            multi_frame[p.id].remove(frame)
                            break  # is it retransmission??
                        if prev_frame_nr != frame.frame_in_command - 1:
                            error = True
                            break  # we got a missing frame waiting for it to get here
                        message += frame.data
                        prev_frame_nr = frame.frame_in_command
                    if not error:
                        for frame in multi_frame[p.id]:
                            packets.remove(frame)
                        messages.append((p.cmd, p.id, message))
    return packets, messages


class Connection:
    """ class used to connect to emka thing """

    def __init__(self, params, conn_type=ConnType.CON_SERIAL, fragment_timeout=100):
        self.protocol = EmkaProtocol()
        self.conn_type = conn_type
        self.handler = None
        self.read_thread = None
        self.connection = None
        self.exit = False
        self.buffer = b''
        self.fragment_timeout = fragment_timeout

        connection_init_functions = {
            ConnType.CON_SERIAL: self.init_serial_connection
        }

        self.type = conn_type
        connection_init_functions[self.type](params)

    def init_serial_connection(self, params):
        #print(params[ConnParams.PORT] + " " + str(params[ConnParams.BAUD]) + " " + str(params[ConnParams.TIMEOUT]))
        self.connection = Serial(params[ConnParams.PORT], params[ConnParams.BAUD], timeout=params[ConnParams.TIMEOUT])
        if not self.connection.port:
            raise BrokenPipeError("Serial Port didn't open properly")

    def send_packet(self, cmd, param):

        packets = self.protocol.build_message(cmd, param)
        for packet in packets:
            self.connection.write(packet.__bytes__())
        restofpacketsnotusefoulinthiscase, messages = get_messages_from_packets(packets)
        return messages

    def get_packets_from_socket(self):
        in_bytes = self.connection.read(self.connection.in_waiting or 1)
        if in_bytes:
            self.buffer += in_bytes
        self.buffer, packets = self.protocol.get_packet_from_buffer(self.buffer)
        return packets

    def init_receiving_loop(self, handler):
        self.handler = handler
        if not self.read_thread:
            self.read_thread = Thread(target=self.receiving_loop)
            self.read_thread.start()

    def close_receiving_loop(self):
        self.exit = True

    def is_receiving_loop_working(self):
        if self.read_thread is not None:
            if self.read_thread.is_alive():
                return True
        return False

    def remove_old_fragments(self, packets: List[Packet]):
        local_time = datetime.datetime.now()
        for frame in packets:
            if local_time - frame.timestamp > datetime.timedelta(seconds=self.fragment_timeout):
                packets.remove(frame)

    def receiving_loop(self):
        packets = []
        while not self.exit:
            try:
                packets += self.get_packets_from_socket()
                packets, messages = get_messages_from_packets(packets)
                self.remove_old_fragments(packets)

                if len(messages):
                    self.handler(messages)
            except Exception:
                self.connection.close()
                raise Exception("nie ma socketa")
