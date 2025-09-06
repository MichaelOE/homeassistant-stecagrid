import asyncio
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
        self.current_power_output = 0
        self.current_timestamp: str = "yyyy-MM-dd HH:mm:ss"
        self.timestamp_status: str = False

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

    def formulaToFloat(self, bytesToConvert):
        """
        Convert 4 bytes (formula + 3 value bytes) to float.
        Formula byte is ignored here, only used to check 0x00.
        """
        if len(bytesToConvert) != 4:
            _LOGGER.warning("formulaToFloat: expected 4 bytes, got %d", len(bytesToConvert))
            return 0.0

        try:
            formula, b0, b1, b2 = bytesToConvert

            if formula == 0x00:  # value not available
                return None

            # Reconstruct 24-bit value into 32-bit float representation
            temp_int = ((b2 << 8 | b0) << 8 | b1) << 7
            temp_bytes = temp_int.to_bytes(4, byteorder='big', signed=False)

            power_output = struct.unpack(">f", temp_bytes)[0]

        except Exception as e:
            _LOGGER.error("Error parsing inverter data: %s", e)
            power_output = 0.0

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

    async def GetInverterTime(self):
        req = self.GenerateRequestTelegram(4)
        msg_response = await self.PollInverter(req)

        _LOGGER.debug("Data and time")
        year = self.formulaToSInt(msg_response[13:15])
        month = self.formulaToSInt(msg_response[17:19])
        day = self.formulaToSInt(msg_response[21:23])
        hour = self.formulaToSInt(msg_response[25:27])
        minute = self.formulaToSInt(msg_response[29:31])
        second = self.formulaToSInt(msg_response[33:35])
        _LOGGER.debug(
            f"Date in inverter {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        )
        self.current_timestamp = (
            f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        )
        self.timestamp_status = msg_response[39 : len(msg_response) - 4].decode(
            "utf-8"
        )
        # return f"{self.timestamp_status}, status: '{msg_response[39 : len(msg_response) - 4].decode('utf-8')}'"
        return self.current_timestamp

    async def GetACOutput(self):
        req = self.GenerateRequestTelegram(41)
        msg_response = await self.PollInverter(req)
        
        _LOGGER.debug("AC power")
        if msg_response[22] == 0x0B:
            power_output = self.formulaToFloat(msg_response[22:26])

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
        self.current_power_output = power_output
        return round(self.current_power_output, 1)
    
    async def GetDailyYield(self):
        req = self.GenerateRequestTelegram(60)
        msg_response = await self.PollInverter(req)

        _LOGGER.debug("daily yield from inverter")

        daily_yield = PowerOutput_MIN

        # Find the formula byte 0x09 for CurrentDayYield
        formula_index = msg_response.find(b'\x09')
        if formula_index != -1 and len(msg_response) >= formula_index + 4:
            yield_bytes = msg_response[formula_index : formula_index + 4]  # 4 bytes
            daily_yield = self.formulaToFloat(yield_bytes)

        else:
            _LOGGER.info("Ingen solproduktion")

        print("Daily Yield (Wh):", round(daily_yield, 1))

        self._previous_value = daily_yield
        self.current_power_output = daily_yield
        return round(daily_yield, 1)

    async def GetNominalPower(self):
        req = self.GenerateRequestTelegram(29)
        msg_response = await self.PollInverter(req)

        _LOGGER.debug("Nominal AC Power from inverter")

        try:
            formula_index = msg_response.find(b'\x0b', 15)  # find first 0x0B
            if formula_index == -1 or len(msg_response) < formula_index + 5:
                print("Panel power bytes not found")
                return 0.0

            power_bytes = msg_response[formula_index : formula_index + 4]  # 4 bytes after 0x0B
            power_output = self.formulaToFloat(power_bytes)
            # print("Panel Power (W):", round(power_output, 3))
            return round(power_output, 3)
        
        except Exception as e:
            _LOGGER.error("Fejl ved parsing af inverterdata i GetPanelOutput! - der er sikkert overskyet. error=%s", e)
            return PowerOutput_MIN

    async def GetPanelOutput(self):
        req = self.GenerateRequestTelegram(34)
        msg_response = await self.PollInverter(req)
        
        try:
            formula_index = msg_response.find(b'\x0b', 15)  # find first 0x0B
            if formula_index == -1 or len(msg_response) < formula_index + 5:
                print("Panel power bytes not found")
                return 0.0

            power_bytes = msg_response[formula_index : formula_index + 4]  # 4 bytes after 0x0B
            power_output = self.formulaToFloat(power_bytes)
            print("Panel Power (W):", round(power_output, 3))
            return round(power_output, 3)
        
        except Exception as e:
            _LOGGER.error("Fejl ved parsing af inverterdata i GetPanelOutput! - der er sikkert overskyet. error=%s", e)
            return PowerOutput_MIN

    async def GetPanelVoltage(self):
        req = self.GenerateRequestTelegram(35)
        msg_response = await self.PollInverter(req)
        
        try:
            formula_index = msg_response.find(b'\x05', 15)  # find first 0x0B
            if formula_index == -1 or len(msg_response) < formula_index + 5:
                print("Panel voltage bytes not found")
                return 0.0
            
            power_bytes = msg_response[formula_index : formula_index + 4]  # 4 bytes after 0x0B
            power_output = self.formulaToFloat(power_bytes)
            print("Panel voltage (V):", round(power_output, 3))
            return round(power_output, 3)
        
        except Exception as e:
            _LOGGER.error("Fejl ved parsing af inverterdata i GetPanelOutput! - der er sikkert overskyet. error=%s", e)
            return PowerOutput_MIN

    async def GetPanelCurrent(self):
        req = self.GenerateRequestTelegram(36)
        msg_response = await self.PollInverter(req)
        
        try:
            formula_index = msg_response.find(b'\x07', 15)  # find first 0x0B
            if formula_index == -1 or len(msg_response) < formula_index + 5:
                print("Panel Current bytes not found")
                return 0.0
            
            power_bytes = msg_response[formula_index : formula_index + 4]  # 4 bytes after 0x0B
            power_output = self.formulaToFloat(power_bytes)
            print("Panel Current (A):", round(power_output, 3))
            return round(power_output, 3)
        
        except Exception as e:
            _LOGGER.error("Fejl ved parsing af inverterdata i GetPanelOutput! - der er sikkert overskyet. error=%s", e)
            return PowerOutput_MIN
            
    def GenerateRequestTelegram(self, RequestIdentifier):
        ### Generate Dataframe
        DataFrame = bytearray(b"")
        DataFrame.extend(bytes([RequestIdentifier]))  # Add Identifier to frame
        DataFrameCRC = self.frameCRC(CRC_8_OFFSET, DataFrame)  # calculate dataframe CRC
        DataFrameLength = bytearray(struct.pack(">h", len(DataFrame)))
        DataFrame.append(DataFrameCRC)  # and append

        ### Generate Header
        HeaderBegin = bytearray(b"\x02\x01")
        HeaderLength = bytearray(b"\x00\x10")
        Header = bytearray(b"")
        Header.extend(HeaderBegin)
        Header.extend(HeaderLength)
        Header.extend(ReceiverAddress)
        Header.extend(SenderAddress)
        Header.append(self.RS485_CRC8_Block(CRC_8_OFFSET, Header))

        ### Concat to FrameData
        FrameData = bytearray(b"")
        FrameData.extend(ServiceCode)
        FrameData.extend(AuthLevel)
        FrameData.extend(DataFrameLength)
        FrameData.extend(DataFrame)

        Telegram = bytearray(b"")
        Telegram.extend(Header)
        Telegram.extend(FrameData)

        # res = RS485_CRC16_Block(CRC_16_OFFSET, Telegram + b'\x03')
        Telegram.extend(
            struct.pack(">H", self.RS485_CRC16_Block(CRC_16_OFFSET, Telegram + b"\x03"))
        )
        Telegram.extend(b"\x03")

        return Telegram

    async def PollInverter(self, requestMessage):
        try:
            reader, writer = await asyncio.open_connection(self._host, self._port)

            # Send request
            writer.write(requestMessage)
            await writer.drain()  # Ensure the message is sent
            # print(f"TX {len(requestMessage)} bytes '{requestMessage.hex()}'")

            # Receive response
            msg_response = await reader.read(1024)
            length = len(msg_response)
            _LOGGER.debug(f"Received {length} bytes '{str(msg_response)}'")

            # Close the connection
            writer.close()
            await writer.wait_closed()

            # return msg_response
            print(f"RX {length} bytes '{msg_response.hex()}'")
            # print(f"RX {length} bytes '{str(msg_response)}'")


        except Exception as e:
            _LOGGER.debug(
                f"No response from Steca inverter. ({self._errorcount}) " + str(e)
            )
            if self._errorcount > 5:
                _LOGGER.warning(
                    f"No response from Steca inverter. ({self._errorcount}) " + str(e)
                )
                self._previous_value = None

            self._errorcount += 1
            # return self._previous_value

        self._errorcount = 0

        try:
            if len(msg_response) < 11:
                _LOGGER.info(
                    "Steca response too short, probably incomplete message received from inverter"
                )
                return PowerOutput_MIN

            ResponseCode = msg_response[8]
            #ResponseValue = msg_response[11]

            if ResponseCode == 0x01:  # ServiceNotSupported
                _LOGGER.warning("Service Not Supported by inverter")
                return "Service Not Supported by inverter"

            return msg_response

        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug(
                f"Fejl ved parsing af inverterdata! - det er måske overskyet eller aften/nat (output = {power_output})"
            )
            return PowerOutput_MIN
