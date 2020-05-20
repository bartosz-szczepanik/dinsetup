from datetime import datetime, timedelta
from typing import List, Tuple

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication

from emkaprotocol.emkaProtocol import EmkaProtocol, Packet, Commands

class SerialReceiver(QObject):

    def __init__(self, connection, lock):
        super().__init__()
        self.buffer = b''
        self.msg_buffer = []
        self.log_buffer = []
        self.connection = connection
        self.protocol = EmkaProtocol()
        self.lock = lock
        self.quit = False
        self.fragment_timeout = 10

    @pyqtSlot()
    def recievingLoop(self):
        packets = []
        while True:
            try:
                packets += self.__getPacketsFromSocket()
                packets, messages = get_messages_from_packets(packets)
                self.__removeOldFragments(packets)
                if len(messages):
                    self.__receivingHandler(messages)
                QApplication.processEvents()
                if self.quit:
                    break
            except Exception as e:
                pass

    def __getPacketsFromSocket(self):
        in_bytes = self.connection.read(self.connection.in_waiting or 1)
        if in_bytes:
            self.buffer += in_bytes
        self.buffer, packets = self.protocol.get_packet_from_buffer(self.buffer)
        return packets

    def __receivingHandler(self, packets: List[Tuple[int, int, str]]):
        for packet in packets:
            if packet[0] == Commands.CMD_LOG.value:
                self.log_buffer.append(packet)
            else:
                with self.lock:
                    self.msg_buffer.append(packet)

    def __removeOldFragments(self, packets: List[Packet]):
        local_time = datetime.now()
        for frame in packets:
            if local_time - frame.timestamp > timedelta(seconds=self.fragment_timeout):
                packets.remove(frame)

    def abort(self):
        self.quit = True

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
