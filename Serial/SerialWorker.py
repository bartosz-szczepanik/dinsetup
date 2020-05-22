import struct
import sys
import traceback
from datetime import datetime, timedelta
from re import sub
from threading import Lock
from time import sleep
from typing import List

import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication
from serial import Serial
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

from Serial.SerialReceiver import SerialReceiver
from emkaprotocol.communicationEngine import split_byte_string
from emkaprotocol.crc_RFC1331 import crc
from emkaprotocol.emkaProtocol import Commands, ENDIANNESS, Packet, EmkaProtocol


class SerialWorker(QObject):

    recabortsig = pyqtSignal()
    labelchangesig = pyqtSignal(str, str)
    progressupdatesig = pyqtSignal(int)
    imagechangesig = pyqtSignal(str)

    def __init__(self, usbport, filelock, iccidpinfile=None, fw2data=None, fw3data=None, configdata = None):
        super().__init__()
        self.lock = Lock()
        self.filelock = filelock
        self.pinset = False

        self.protocol = EmkaProtocol()
        self.usbport = usbport
        self.comport = "NOTFOUND"
        self.iccidpinfile = iccidpinfile
        self.fw2data = fw2data
        self.fw3data = fw3data
        self.configdata = configdata

        self.sn = ""
        self.version = ""
        self.pin = ""
        self.iccid = ""

        self.connection = Serial()
        self.connection.bytesize = 8
        self.connection.baudrate = 115200
        self.connection.timeout = 10

        self.receiverthread = QThread()
        self.receiverworker = SerialReceiver(self.connection, self.lock)
        self.receiverthread.started.connect(self.receiverworker.recievingLoop)
        self.receiverworker.moveToThread(self.receiverthread)
        self.recabortsig.connect(self.receiverworker.abort)


        #self.sig_msg = pyqtSignal(str)
    def resetVisual(self):
        self.labelchangesig.emit("AUTH", "")
        self.labelchangesig.emit("SN", "SN: ")
        self.labelchangesig.emit("ICCID", "ICCID: ")
        self.labelchangesig.emit("PIN", "PIN: ")
        self.labelchangesig.emit("FW", "FW: ")
        self.labelchangesig.emit("AT", "AT: ")
        self.labelchangesig.emit("STATUS", "")
        self.imagechangesig.emit("DINDC")
        self.progressupdatesig.emit(0)


    @pyqtSlot()
    def serialSetupLoop(self):
        QApplication.processEvents()
        while True:
            try:
                self.imagechangesig.emit("DINDC")
                self.__findComport()
                self.connection.port = self.comport
                sleep(5)
                with self.connection:
                    self.imagechangesig.emit("DINCN")
                    self.__getDataFromDin()
                #   self.__getConfig()
                    self.__setPin()
                    self.__updateFw()
                QApplication.processEvents()
                self.resetVisual()
            except Exception as e:
                self.resetVisual()
                print("-"*60)
                print(e)
                traceback.print_exc(file=sys.stdout)
                print("-"*60)

    def __getDataFromDin(self):
        self.__getVersion()
        self.__sendAuthentication(b"Pysense2020!")
        self.pgecode = self.__buildPgeCode()

    def __getVersion(self):
        ret = None
        while not ret:
            ret = self.__sendAndWait(Commands.CMD_VERSION, b'?')
        version = ret[2].split(b'\0', 1)[0]
        other = ret[2][len(version):]
        serial, model, hwver = struct.unpack("!x4shh", other)
        self.sn = str(int.from_bytes(serial, "little")).rjust(8, '0')
        self.labelchangesig.emit("SN", "SN: " + self.sn)
        self.version = version[1:10].decode()
        self.labelchangesig.emit("FW", "FW: " + self.version)

    def __sendAuthentication(self, password):
        length = len(password)
        data = length.to_bytes(1, ENDIANNESS) + password
        ret = None
        while not ret or int.from_bytes(ret[2], byteorder=ENDIANNESS) != 0:
            ret = self.__sendAndWait(Commands.CMD_PASSWORD_AUTH, data)
        status = int.from_bytes(ret[2], byteorder=ENDIANNESS)
        if status == 0:
            self.labelchangesig.emit("AUTH", "AUTHENTICATION OK")
        else:
            self.labelchangesig.emit("AUTH", "AUTHENTICATION FAILED")

    def __buildPgeCode(self):
        code = "91041"
        code += self.sn
        code += "20"
        addition = 0
        for i in self.sn:
            addition += int(i)
        lastdigit = addition % 10
        code += str(lastdigit)
        return code

    def __sendAndWait(self, cmd, param, progress_callback=False, timeout=10):
        if not self.__isRecThreadWorking():
            self.__initReceivingLoop()
        if not self.__isRecThreadWorking():
            raise Exception("nie da się uruchomić receivera")
        packets = self.__sendPacket(cmd.value, param, progress_callback)
        id = packets[0][1]
        response = self.__waitForResponse(id, timeout)
        return response

    def __sendPacket(self, cmd, param, progress_callback):
        packets = self.protocol.build_message(cmd, param)
        for packet in packets:
            self.connection.write(packet.__bytes__())
            if progress_callback:
                self.progressupdatesig.emit(int(((packets.index(packet)+1)/len(packets))*100))
            sleep(0.1)
        trash, messages = getMsgFromPackets(packets)
        return messages

    def __waitForResponse(self, id, timeout=10):
        start = datetime.now()
        while datetime.now() - start <= timedelta(seconds=timeout):
            with self.lock:
                for packet in self.receiverworker.msg_buffer:
                    if packet[1] == id:
                        self.receiverworker.msg_buffer.remove(packet)
                        return packet
        #print(self.rec_buffer)
        print("----- PACKET RESPONSE TIMED OUT -----")
        return None

    def __initReceivingLoop(self):
        self.receiverthread.start()

    def __isRecThreadWorking(self):
        if self.receiverthread.isRunning():
            return True
        return False

    def __setPin(self):
        self.imagechangesig.emit("DINPIN")
        config = bytearray(self.configdata)
        self.__getIccid()
        self.__findPin()
        if self.pin:
            duplicate = False
            with self.filelock:
                f = open("../pgecodeiccidpin.txt", "a+")
                f.seek(0)
                tmp = f.readlines()
                content = [x.split(",") for x in tmp]
                for row in content:
                    if row[1] == self.iccid:
                        duplicate = True
                if not duplicate:
                    f.write(self.pgecode + "," + self.iccid + "," + self.pin + "\n")
                    f.flush()
                f.close()

            config[668:676] = self.pin.ljust(8, "\x00").encode()
            config[3] = crc(0, config[5:]).to_bytes(byteorder=ENDIANNESS, length=2)[0]
            config[4] = crc(0, config[5:]).to_bytes(byteorder=ENDIANNESS, length=2)[1]

            if self.__checkAtPin():
                self.pinset = False
                self.__setAtPin()
            else:
                self.pinset = True
            self.__setConfig(config)

    def __getIccid(self, retries = 0):
        retries = retries
        ret = None
        while (not ret or len(ret[2]) <= 4) and retries < 4:
            retries += 1
            self.labelchangesig.emit("STATUS", "Retrieving ICCID, try:{}/4".format(retries))
            ret = self.__sendAndWait(Commands.CMD_MODEM_AT, b'AT+ICCID', False, 20)
            sleep(3)
        try:
            self.iccid = ret[2].decode().split(":")[1][7:20]
        except:
            self.iccid = "FAILED"
        self.labelchangesig.emit("ICCID", "ICCID: "+ self.iccid)

    def __findPin(self):
        self.pin = None
        for row_num in range(self.iccidpinfile.nrows):
            row_value = self.iccidpinfile.row_values(row_num)
            if str(int(row_value[0])) == self.iccid:
                self.pin = str(row_value[1]).rjust(4, "0")
                self.labelchangesig.emit("PIN", "PIN: " + self.pin)
                break

    def __setConfig(self, config):
        ret = None
        while not ret:
            ret = self.__sendAndWait(Commands.CMD_CONFIG, config, True)

    def __getConfig(self):
        ret = None
        while not ret:
            ret = self.__sendAndWait(Commands.CMD_CONFIG, b"?", True)
        open("RzeszowConfig.bin","wb").write(ret[2])

    def __setAtPin(self, retries=0):
        retries = retries
        command = "AT+CPIN="+self.pin
        response = "ATCPIN{}OK".format(self.pin)
        ret = None
        while (not ret or len(ret[2]) <= 4 or sub('\W+', '', ret[2].decode()).find(response) == -1) and retries < 4:
            retries += 1
            try:
                self.labelchangesig.emit("STATUS", command + " {}/4".format(retries) + "Last response: " + sub('\W+', '', ret[2].decode()))
            except:
                self.labelchangesig.emit("STATUS", command + " {}/4".format(retries))

            ret = self.__sendAndWait(Commands.CMD_MODEM_AT, command.encode(), False, 20)
            sleep(3)
        self.labelchangesig.emit("AT", ret[2].decode())

    def __checkAtPin(self, retries=0):
        retries = retries
        ret = ""

        while (not ret or len(ret[2]) <= 4) and retries < 4:
            retries += 1
            try:
                self.labelchangesig.emit("STATUS", "ATCPIN? {}/4 last response: {}".format(retries, sub('\W+', '', ret[2].decode())))
            except:
                self.labelchangesig.emit("STATUS", "ATCPIN? {}/4".format(retries))
            ret = self.__sendAndWait(Commands.CMD_MODEM_AT, b"AT+CPIN?")
            sleep(3)
        try:
            ret = sub('\W+','', ret[2].decode())
        except:
            ret = "FAILED"

        if ret.find("READY")!=-1:
            self.labelchangesig.emit("AT", "AT:READY")
            return False
        elif ret.find("SIMPIN")!=-1:
            self.labelchangesig.emit("AT", "AT:SIMPIN")
            return True
        elif ret == "FAILED":
            self.labelchangesig.emit("AT", "AT:FAILED")
        else:
            self.labelchangesig.emit("AT", "AT: " + sub('\W+', '', ret[2].decode()))
            return True

    def __findComport(self):
        for tmp in serial.tools.list_ports.comports():
            if tmp.location == self.usbport:
                self.comport = tmp.device

    def __updateFw(self):
        if self.version != '3.71.1679' and self.version != '2.71.1679':
            self.imagechangesig.emit("DINFW")
            doagain = True
            retries = 0

            if self.version[0] == 3:
                fwtouse = self.fw3data
            else:
                fwtouse = self.fw2data

            while doagain and retries < 2:
                self.__clearMemory(0, 241664)
                self.__writeMemory(0, fwtouse)
                check = self.__readMemory(0, len(fwtouse))
                if check == fwtouse:
                    self.resetDin()
                    break
                retries += 1
        elif self.pinset:
            self.labelchangesig.emit("STATUS", "Updated")
            self.imagechangesig.emit("DINFIN")
            while self.connection.is_open:
                self.connection.write(b"\x00")
                sleep(3)


    def __clearMemory(self, addr: int, size: int):
        self.labelchangesig.emit("STATUS", "Clearing memory...")
        data = addr.to_bytes(4, ENDIANNESS) + size.to_bytes(4, ENDIANNESS)
        ret = self.__sendAndWait(Commands.CMD_MEMORY_ERASE, data)
        return ret[2]

    def __writeMemory(self, addr: int, data: bytes):
        bpcount = 0
        self.labelchangesig.emit("STATUS", "Writing fw to flash...")
        total_chunks = len(data) // 512 + 1 if len(data) % 512 != 0 else 0
        for i, chunk in enumerate(split_byte_string(data, 512)):
            self.progressupdatesig.emit(int(((i+1)/total_chunks)*100))
            chunk_addres = addr + i * 512
            chunk_data = chunk_addres.to_bytes(4, ENDIANNESS) + chunk
            ret = self.__sendAndWait(Commands.CMD_MEMORY_WRITE, chunk_data)
            bpcount += 1
        return ret

    def __readMemory(self, addr, size):
        ret_data = b''
        bpcount = 0
        total_chunks = size // 512 + 1 if size % 512 != 0 else 0
        self.labelchangesig.emit("STATUS", "Reading from flash...")
        for i, chunk_addr in enumerate(range(addr, addr + size, 512)):
            self.progressupdatesig.emit(int(((i+1)/total_chunks)*100))
            chunk_size = (size - i * 512) if (size - i * 512 < 512) else 512
            data = chunk_addr.to_bytes(4, ENDIANNESS) + chunk_size.to_bytes(4, ENDIANNESS)
            ret = self.__sendAndWait(Commands.CMD_MEMORY_READ, data)
            ret_data += ret[2]
            bpcount += 1
        return ret_data


def getMsgFromPackets(packets: List[Packet]):
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
