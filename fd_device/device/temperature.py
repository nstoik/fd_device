"""Module to interface with the temperature sensors connected to the device."""


def temperature(sensor_name, sample_number=3, percision=2):
    """Get the temperature of a sensor."""

    temp_values = []
    for _ in range(sample_number):
        temp = _read_temperature(sensor_name)
        if temp != "U":
            temp_values.append(temp)

    if len(temp_values) > 0:
        return round(sum(temp_values) / len(temp_values), percision)

    else:
        return "U"


def _read_temperature(name):
    """Low level read the temperatures of a sensor."""
    w1_master_devices = "/sys/bus/w1/devices/w1_bus_master1/w1_master_slaves"

    # get connected sensors
    with open(w1_master_devices) as f:
        content = [line.rstrip("\n") for line in f]

    if name in content:
        # sensor is connected
        sensor_file = "/sys/bus/w1/devices/" + name + "/w1_slave"
        try:
            with open(sensor_file) as f:
                lines = f.readlines()

            temp_output = lines[1].find("t=")
            if temp_output != -1:
                temp_string = lines[1].strip()[temp_output + 2 :]
                temp_c = float(temp_string) / 1000.0
                return temp_c

        except IOError:
            return "U"

    # problem reading sensor
    return "U"


def get_connected_sensors(values=False):
    """Return all of the sensores connected to the device."""
    w1_master_devices = "/sys/bus/w1/devices/w1_bus_master1/w1_master_slaves"
    # get connected sensors
    with open(w1_master_devices) as f:
        content = [line.rstrip("\n") for line in f]

    if values:
        values = {}
        for sensor in content:
            temp = temperature(sensor, sample_number=2)
            values[sensor] = temp
        return values

    else:
        return content


if __name__ == "__main__":
    print(get_connected_sensors(values=True))
