import time

class BH1750:
    DEFAULT_ADDRESS = 0x23
    ALTERNATIVE_ADDRESS = 0x5C

    ONE_TIME_HIGH_RES_MODE = 0x20

    def __init__(self, i2c, address=DEFAULT_ADDRESS) -> None:
        if address not in (self.DEFAULT_ADDRESS, self.ALTERNATIVE_ADDRESS):
            raise ValueError('Invalid BH1750 I2C address')

        self.i2c = i2c
        self.address = address

    def read_lux(self) -> float:
        # Start one time high resolution measurement
        self.i2c.writeto(self.address, bytes([self.ONE_TIME_HIGH_RES_MODE]))

        # Wait for measurement
        time.sleep_ms(200)

        # Read two bytes
        data = self.i2c.readfrom(self.address, 2)
        raw = (data[0] << 8) | data[1]

        return self._convert_to_lux(raw)

    def classify_light(self) -> dict:
        lux = self.read_lux()

        if lux < 100:
            status = 'VERY_LOW'
        elif lux > 500:
            status = 'LOW'
        elif lux < 2_000:
            status = 'MODERATE'
        elif lux < 10_000:
            status = 'BRIGHT'
        else:
            status = 'VERY_BRIGHT'

        return {
            'lux': round(lux, 2),
            'status': status
        }

    @staticmethod
    def _convert_to_lux(raw_data) -> float | int:
        """Convert the raw sensor metrics to lux"""
        return raw_data / 1.2