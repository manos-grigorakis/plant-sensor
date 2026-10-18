class SoilMoisture:
    def __init__(self, air_value, water_value, soil_moisture):
        self.air_value = air_value
        self.water_value = water_value
        self.soil_moisture = soil_moisture

        self._validate_sensor_calibration()

        self.intervals = (self.air_value - self.water_value) / 3

    def read_moisture(self) -> float:
        """Read the sensor's ADC value and convert it to a moisture percentage"""
        moisture = self.soil_moisture.read_u16()
        return self._calculate_moisture_percentage(moisture)

    def classify_moisture(self) -> dict:
        """Classify soil moisture based on predefined percentage thresholds

        :return: Dictionary containing the moisture status and percentage
        """
        percentage = self.read_moisture()

        if percentage >= 66.67:
            status = 'VERY_WET'
        elif percentage >= 33.33:
            status = 'WET'
        else:
            status = 'DRY'

        return {
            'status': status,
            'moisture_percentage': round(percentage, 2)
        }

    def _validate_sensor_calibration(self) -> None:
        """Validate the air and water calibration values

        :raises ValueError: If the value are missing or the air value is not greater that the water value
        """
        if self.air_value is None or self.water_value is None:
            raise ValueError("Calibration values required")

        if self.air_value <= self.water_value:
            raise ValueError("Air value must be greater than water value")
    
    def _calculate_moisture_percentage(self, moisture) -> float:
        """Convert a raw ADC reading into a calibrated moisture percentage

        :param moisture: Raw ADC reading
        :return: Calibrated moisture percentage (between 0 and 100)
        """
        percentage = (self.air_value - moisture) / (self.air_value - self.water_value) * 100
        return max(0, min(100, percentage))