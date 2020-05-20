from .emkaProtocol import Commands, ENDIANNESS
from .connection import Connection, ConnParams
from typing import Tuple, List
from datetime import datetime, timedelta
import serial.tools.list_ports
import struct


def split_byte_string(s, n):
    """Split string or bytestring s into chunks of maximum length n."""
    while len(s) > n:
        k = n
        yield s[:k]
        s = s[k:]
    yield s


class AbstractCommunicationEngine:

    def __init__(self, params={ConnParams.PORT: "/dev/ttyACM0", ConnParams.BAUD: 115200, ConnParams.TIMEOUT: 1}):
        self.link = None
        self.rec_buffer = []
        self.log_buffer = []

    def __del__(self):
        self.clean()

    def clean(self):
        try:
            self.link.connection.close()
            self.link.close_receiving_loop()
        except AttributeError as e:
            pass

    def receiving_handler(self, packets: List[Tuple[int, int, str]]):
        # print(packets)
        for packet in packets:
            #print(packet)
            if packet[0] == Commands.CMD_LOG.value:
                self.log_buffer.append(packet)
            else:
                self.rec_buffer.append(packet)

    def log_handler(self, cmd):
        pass

    def wait_for_response(self, id, timeout=10):
        start = datetime.now()
        while datetime.now() - start <= timedelta(seconds=timeout):
            for packet in self.rec_buffer:
                if packet[1] == id:
                    self.rec_buffer.remove(packet)
                    return packet
        print(self.rec_buffer)
        raise TimeoutError("Packet timeout", id)

    def get_log_line(self):
        tmp = None
        if not self.link.__isRecThreadWorking():
            raise Exception("no receiver for log")
        try:
            tmp = self.log_buffer[0]
            self.log_buffer = self.log_buffer[1:]

        except IndexError:
            pass
        return tmp

    def send_and_wait_for_response(self, cmd, param):
        if not self.link.__isRecThreadWorking():
            self.link.__initReceivingLoop(self.receiving_handler)
        if not self.link.__isRecThreadWorking():
            raise Exception("nie da się uruchomić receivera")
        packets = self.link.send_packet(cmd.value, param)
        id = packets[0][1]
        response = self.wait_for_response(id)
        return response

    def getFW(self):
        return self.send_and_wait_for_response(Commands.CMD_MODEM_FIRMWARE_VERSION, bytearray.fromhex('00'))

    def getICCID(self):
        return self.send_and_wait_for_response(Commands.CMD_MODEM_AT, b"AT+ICCID")

    def getVersion(self):
        ret = self.send_and_wait_for_response(Commands.CMD_VERSION, b'?')
        version = ret[2].split(b'\0', 1)[0]
        other = ret[2][len(version):]
        serial, model, hwver = struct.unpack("!Ihhx", other)
        return version, serial, model, hwver

    def getConfig(self):
        ret = self.send_and_wait_for_response(Commands.CMD_CONFIG, b'?')
        return ret[2]

    def setDebugLevel(self, level: int):

        self.link.send_packet(Commands.CMD_DEBUGLEVEL.value, level.to_bytes(4, ENDIANNESS))
        #ret = self.send_and_wait_for_response(Commands.CMD_DEBUGLEVEL,
        #                                      level.to_bytes(4, ENDIANNESS))

        #if int.from_bytes(ret[2], ENDIANNESS) == level:
        #    return 0
        return 0

    def setSerial(self, serial):
        ret = self.send_and_wait_for_response(Commands.CMD_SET_SERIAL,
                                              serial.to_bytes(4, ENDIANNESS))

        if int.from_bytes(ret[2], ENDIANNESS) == serial:
            return 0
        return 1

    def clearMemory(self, addr: int, size: int):
        data = addr.to_bytes(4, ENDIANNESS) + size.to_bytes(4, ENDIANNESS)
        ret = self.send_and_wait_for_response(Commands.CMD_MEMORY_ERASE, data)
        return ret[2]

    def sendAUTH(self, password):
        length = len(password)
        data = length.to_bytes(1, ENDIANNESS) + password
        ret = self.send_and_wait_for_response(Commands.CMD_PASSWORD_AUTH, data)
        status = int.from_bytes(ret[2], byteorder=ENDIANNESS)
        return status

    def writeMemory(self, addr: int, data: bytes, progress_callback=None):
        size = len(data)
        nr = 0
        bpcount = 0
        total_chunks = len(data) // 512 + 1 if len(data) % 512 != 0 else 0
        for i, chunk in enumerate(split_byte_string(data, 512)):
            if progress_callback:
                progress_callback(i, total_chunks, datetime.now())
            chunk_addres = addr + i * 512
            chunk_data = chunk_addres.to_bytes(4, ENDIANNESS) + chunk
            ret = self.send_and_wait_for_response(Commands.CMD_MEMORY_WRITE, chunk_data)
            bpcount += 1
        return ret

    def readMemory(self, addr, size, progress_callback=None):
        ret_data = b''
        bpcount = 0
        total_chunks = size // 512 + 1 if size % 512 != 0 else 0
        for i, chunk_addr in enumerate(range(addr, addr + size, 512)):
            if progress_callback:
                progress_callback(i, total_chunks, datetime.now())
            chunk_size = (size - i * 512) if (size - i * 512 < 512) else 512
            data = chunk_addr.to_bytes(4, ENDIANNESS) + chunk_size.to_bytes(4, ENDIANNESS)
            ret = self.send_and_wait_for_response(Commands.CMD_MEMORY_READ, data)
            ret_data += ret[2]
            bpcount += 1
            # sleep(1)
        return ret_data

    def restart(self):
        tmp = 0
        data = tmp.to_bytes(4, ENDIANNESS)
        ret = self.send_and_wait_for_response(Commands.CMD_RESTART, data)

    def writeConfig(self, data):
        packets = self.send_and_wait_for_response(Commands.CMD_CONFIG, data)
        #packets = self.link.send_packet(Commands.CMD_CONFIG.value, data)
        #sleep(4)

    def readConfig(self):
        ret = self.send_and_wait_for_response(Commands.CMD_CONFIG, b'?')
        return ret[2]

    def getMainStatus(self):
        ret = self.send_and_wait_for_response(Commands.CMD_MAIN_STATUS, b'?')
        status = ret[2]

        '''
        unsigned char 			GSMlevel;
        unsigned int  			IP;
        unsigned char			GSMNetworkStatus;
        int						GSMStatus;
        int						GPRSStatus;
        char					operator[16];
        char					IMEI[16];
        unsigned char			ModemType;
        unsigned char			PowerSupply;
        struct _SocketStatus	sockets[6];
        unsigned char 			PINState;
        unsigned char			Technology;
        unsigned int			uptime;
        unsigned int			restartcount;
        unsigned int			uart_write[UARTsCount];
        unsigned int			uart_read[UARTsCount];
        unsigned int			uart_error[UARTsCount];
        unsigned int			radio_write;
        unsigned int			radio_read;
        unsigned int			radio_totalwrite;
        unsigned int			radio_totalread;
        // ArtM
        unsigned int			gsm_cellID;
        unsigned int 			gsm_earfcn;	// dla LTE
        int						gsm_dbm;
        char					gsm_MMC[4];
        char					gsm_MNC[4];
        char					gsm_phyCellID[12];
        int 					gsm_rsrp;
        int						gsm_sq;
        char					gsm_iccid[20];

        unsigned int 			radioState;
        int 					radio_RSSI;
        unsigned char 			FOTAState;
        '''

        # data = struct.unpack("BIBii16s16sBBIIIHIIQQBB11IiccciicIiB", status)
        return status  # data

    def sendATCommand(self, command, resp, timeout):
        pass

    def sendResetModem(self):
        pass

    def sendStartTestCommand(test, apn):
        pass

    def clearLog(self):
        pass

    def getTestStatus(self, data):
        pass

    def sendWMBUSdata(self, data):
        ret = self.send_and_wait_for_response(Commands.CMD_SEND_WMBUS, data)
        status = int.from_bytes(ret[2], byteorder='big')
        return status

    def getLogInfo(self, retval):
        pass

    def getLogData(self, min, count, retval):
        pass

    def getLogDataByDate(self, starttime, stoptime, retval):
        pass

    def sendWMBUSCarrier(self, set):
        pass

    def getModemFirmwareVersion(self, version):
        pass

    def sendPM9(self, set):
        pass

    def sendRadioRestart(self):
        pass

    def sendFOTA(self, host, user, password, path, file, timeout):
        pass

    def write_pin_required(self, req):
        pass


class SerialCommunicationEngine(AbstractCommunicationEngine):

    def __init__(self, params={ConnParams.PORT: "/dev/ttyACM0", ConnParams.BAUD: 115200, ConnParams.TIMEOUT: 1}):
        super(SerialCommunicationEngine, self).__init__()
        params = self.searchForCom(params)
        self.link = Connection(params)
        self.link.init_receiving_loop(self.receiving_handler)

    def searchForCom(self, params):
        for tmp in serial.tools.list_ports.comports():
            if tmp.location == params[ConnParams.PORT]:
                params[ConnParams.PORT] = tmp.device
                return params
        return params