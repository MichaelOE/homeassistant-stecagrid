import socket
import struct

from logging import getLogger

_LOGGER = getLogger(__name__)

### Constants
PowerOutput_MIN = 0.0
PowerOutput_MAX = 10000.0

### Variables
ReceiverAddress = b"\x01"
SenderAddress = b"\xc9"
ServiceCode = b"\x40"
AuthLevel = b"\x01"
DataLength = bytearray(b"\x00\x01")
# Identifier = b'\x29'

CRC_8_OFFSET = 0x55
CRC_16_OFFSET = 0x5555

# A list of 16 CRC-8 values
CRC8_Table = [
    0x00,
    0x8F,
    0x27,
    0xA8,
    0x4E,
    0xC1,
    0x69,
    0xE6,
    0x9C,
    0x13,
    0xBB,
    0x34,
    0xD2,
    0x5D,
    0xF5,
    0x7A,
]
# A list of 16 CRC-16 values
CRC16_Table = [
    0x0000,
    0xACAC,
    0xEC05,
    0x40A9,
    0x6D57,
    0xC1FB,
    0x8152,
    0x2DFE,
    0xDAAE,
    0x7602,
    0x36AB,
    0x9A07,
    0xB7F9,
    0x1B55,
    0x5BFC,
    0xF750,
]


class StecaConnector:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._previous_value = PowerOutput_MIN
        self._errorcount = 0

    # A function that takes a current CRC value, a data buffer, and a data length as parameters
    def RS485_CRC8_Block(self, currentCrc, data):
        # Loop through the data buffer
        for value in data:
            # XOR in the data
            currentCrc ^= value
            # Perform the XORing for each nibble
            currentCrc = (currentCrc >> 4) ^ CRC8_Table[currentCrc & 0x0F]
            currentCrc = (currentCrc >> 4) ^ CRC8_Table[currentCrc & 0x0F]

        # Return the final CRC value
        return currentCrc

    # A function that takes a current CRC value, a data buffer, and a data length as parameters
    def RS485_CRC16_Block(self, currentCrc, data):
        # Loop through the data buffer
        for value in data:
            # XOR in the data
            currentCrc ^= value
            # Perform the XORing for each nibble
            currentCrc = (currentCrc >> 4) ^ CRC16_Table[currentCrc & 0x000F]
            currentCrc = (currentCrc >> 4) ^ CRC16_Table[currentCrc & 0x000F]

        # Return the final CRC value
        return currentCrc

    def frameCRC(self, CRCOffset, data):
        total = CRCOffset
        total = total + sum(data[0 : len(data)])
        # Return the final CRC value
        return total

    def formulaToFloat(self, threeBytesToConvert):
        try:
            temp = (
                (threeBytesToConvert[2] << 8 | threeBytesToConvert[0]) << 8
                | threeBytesToConvert[1]
            ) << 7
            power_output = struct.unpack(
                "!f", bytes.fromhex(str(hex(temp)).split("0x")[1])
            )[0]
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fejl ved parsing af inverterdata! - der er sikkert overskyet (output = ",
                power_output,
                ")",
            )
        return power_output

    def formulaToSInt(self, bytesToConvert):
        try:
            sint = int.from_bytes(bytesToConvert, byteorder="big", signed=True)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "Fejl ved parsing af data fra inverter i formulaToSInt! (output = ",
                sint,
                ")",
            )
        return sint

    def GetInverterTime(self):
        req = self.GenerateRequestTelegram(b"\x04")
        retVal = self.PollInverter(req)
        return retVal

    def GetPowerOutput(self):
        req = self.GenerateRequestTelegram(b"\x29")
        retVal = self.PollInverter(req)
        return retVal

    def GenerateRequestTelegram(self, RequestIdentifier):
        ### Generate Dataframe
        DataFrame = bytearray(b"")
        DataFrame.extend(RequestIdentifier)  # Add Identifier to frame
        DataFrameCRC = self.frameCRC(CRC_8_OFFSET, DataFrame)  # calculate dataframe CRC
        DataFrameLength = bytearray(struct.pack(">h", len(DataFrame)))
        DataFrame.append(DataFrameCRC)  # and append

        ### Concat to FrameData
        FrameData = bytearray(b"")
        FrameData.extend(ServiceCode)
        FrameData.extend(AuthLevel)
        FrameData.extend(DataFrameLength)
        FrameData.extend(DataFrame)

        ### Generate Header
        HeaderBegin = bytearray(b"\x02\x01")
        HeaderLength = bytearray(b"\x00\x10")
        Header = bytearray(b"")
        Header.extend(HeaderBegin)
        Header.extend(HeaderLength)
        Header.extend(ReceiverAddress)
        Header.extend(SenderAddress)
        Header.append(self.RS485_CRC8_Block(CRC_8_OFFSET, Header))

        Telegram = bytearray(b"")
        Telegram.extend(Header)
        Telegram.extend(FrameData)

        # res = RS485_CRC16_Block(CRC_16_OFFSET, Telegram + b'\x03')
        Telegram.extend(
            struct.pack(">H", self.RS485_CRC16_Block(CRC_16_OFFSET, Telegram + b"\x03"))
        )
        Telegram.extend(b"\x03")

        return Telegram

    def PollInverter(self, requestMessage):
        power_output = PowerOutput_MIN

        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(3)
            client.connect((self._host, self._port))
            client.send(requestMessage)

            msgResponse = client.recv(1024)
            # Get the length of the received data
            length = len(msgResponse)
            _LOGGER.debug(f"Received {len(msgResponse)} bytes '{str(msgResponse)}'")

        except Exception as e:
            # _LOGGER.warning("No response from Steca inverter. " +  str(e))
            if self._errorcount > 5:
                _LOGGER.warning(
                    f"No response from Steca inverter. ({self._errorcount}) " + str(e)
                )
                self._previous_value = None

            self._errorcount += 1
            return self._previous_value

        self._errorcount = 0

        try:
            if len(msgResponse) < 11:
                _LOGGER.info(
                    "Steca response too short, probably incomplete message received from inverter"
                )
                return PowerOutput_MIN

            ResponseCode = msgResponse[8]
            ResponseValue = msgResponse[11]

            if ResponseCode == 0x01:  # ServiceNotSupported
                _LOGGER.warning("Service Not Supported by inverter")
                return "Service Not Supported by inverter"
            elif ResponseValue == 0x29:  # Nominal AC power of inverter
                _LOGGER.debug("Nominal AC power of inverter")
                if msgResponse[22] == 0x0B:
                    power_output = self.formulaToFloat(msgResponse[23:26])

                    if (
                        power_output <= PowerOutput_MIN
                        or power_output > PowerOutput_MAX
                    ):  # Range check
                        _LOGGER.warning(
                            f"Unusual inverter power '{power_output}', probably wrong message received from inverter"  # noqa: G004
                        )
                        power_output = PowerOutput_MIN

                else:
                    _LOGGER.info("Ingen solproduktion")
                    power_output = PowerOutput_MIN

                self._previous_value = power_output
                return power_output

            elif ResponseValue == 0x04:  # Data and time
                _LOGGER.debug("Data and time")
                year = self.formulaToSInt(msgResponse[13:15])
                month = self.formulaToSInt(msgResponse[17:19])
                day = self.formulaToSInt(msgResponse[21:23])
                hour = self.formulaToSInt(msgResponse[25:27])
                minute = self.formulaToSInt(msgResponse[29:31])
                second = self.formulaToSInt(msgResponse[33:35])
                _LOGGER.debug(
                    f"Date in inverter {year}-{month}-{day} {hour}:{minute}:{second}"
                )
                return f"{year}-{month}-{day} {hour}:{minute}:{second}, status: '{msgResponse[39:len(msgResponse)-4].decode('utf-8')}'"

        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug(
                f"Fejl ved parsing af inverterdata! - det er måske overskyet eller aften/nat (output = {power_output})"
            )
            return PowerOutput_MIN
