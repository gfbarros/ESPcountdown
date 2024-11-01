import os
import board
from adafruit_ht16k33.segments import BigSeg7x4
import wifi
import socketpool
from adafruit_httpserver import (
    Server, Request, Response, POST, GET,
    REQUEST_HANDLED_RESPONSE_SENT,
    )
import adafruit_requests
import ssl
import time
import adafruit_ds3231
import json

i2c = board.I2C()
display = BigSeg7x4(i2c, address=0x70)
display.brightness = 0.2

# init ds3231
rtc = adafruit_ds3231.DS3231(i2c)

# init wifi & http server + requester
pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, debug=True)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

aio_username = os.getenv("AIO_USERNAME")
aio_key = os.getenv("AIO_KEY")
timezone = os.getenv("TIMEZONE")
STime_URL = f"https://io.adafruit.com/api/v2/{aio_username}/integrations/time/struct?x-aio-key={aio_key}"


# Grab time from the internet & set the rtc
print("-" * 40)
structime = requests.get(STime_URL)
print(structime.text)
print("-" * 40)


# set rtc with struct_time object
# circuitpython is based on python3.4 which has unordered dicts :(
td = json.loads(structime.text)
# print((td))
rtc.datetime = time.struct_time((td["year"], td["mon"], td["mday"], td["hour"], td["min"], td["sec"], td["wday"], td["yday"], td["isdst"]))

current = rtc.datetime
print('The current time is: {}/{}/{} {:02}:{:02}:{:02}'.format(current.tm_mon, current.tm_mday, current.tm_year, current.tm_hour, current.tm_min, current.tm_sec))
print("-" * 40)

#  prints MAC address to REPL
# print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])

#  prints IP address to REPL
# print("My IP address is", wifi.radio.ipv4_address)


# Set default countdown
# Get todays date
nowtime = time.mktime(rtc.datetime)
#print("now in epoch: ", nowtime)
# create struct_time for target date
targettime = time.mktime((2025, 4, 30, 23, 59, 59, 3, 120, 1))
remaining = targettime - nowtime
#print(remaining)
remaining //= 86400

# update display
display.fill(0)
display.print(remaining)

# set rtc alarm to midnight for the counter update
rtc.alarm1 = (time.struct_time((0, 0, 0, 0, 0, 1, 0, 0, -1)), "hourly")


FORM_HTML_TEMPLATE = """
<html lang="en">
    <head>
        <title>Update LEDs</title>
    </head>
    <body>
        <h2>Type in end date (integers only).</h2>
        <form action="/" method="post" enctype="text/plain">
            <label for "fyear"> end date:</label>
            <input type="text" id="fyear" name="fyear" value="2025"><br>
            <input type="text" id="fmonth" name="fmonth" value="04"><br>
            <input type="text" id="fday" name="fday" value="30"><br>
            <input type="submit" value="Submit">
        </form>
        {submitted_value}
    </body>
</html>
"""


@server.route("/", [GET, POST])
def form(request: Request):
    """
    Serve a form with the given enctype, and display back the submitted value.
    """
    enctype = request.query_params.get("enctype", "text/plain")

    if request.method == POST:
        posted_year = request.form_data.get("fyear")
        posted_month = request.form_data.get("fmonth")
        posted_day = request.form_data.get("fday")
        # Get todays date & convert
        nowtime = time.mktime(rtc.datetime)
        targettime = time.mktime((int(posted_year), int(posted_month), int(posted_day), 23, 59, 59, 3, 120, 1))
        remaining = targettime - nowtime
        remaining //= 86400
        print("in server ", remaining)

        # update display
        display.fill(0)
        display.print(remaining)

    return Response(
        request,
        FORM_HTML_TEMPLATE.format(
            enctype=enctype,
            submitted_value=(
                f"<h3>Submitted form. Time remaining: {remaining}</h3>"
                if request.method == POST
                else ""
            ),
        ),
        content_type="text/html",
    )

server.start(str(wifi.radio.ipv4_address))

while True:
    try:
        # read time from rtc.
        nowtime = time.mktime(rtc.datetime)

        # check if it's been 2 sec, update dot.
        if nowtime % 2 == 0:
            display.bottom_left_dot = True
        else:
            display.bottom_left_dot = False

        # Check for alarm, update countdown.
        if rtc.alarm1_status:
            print("Alarm firing")
            rtc.alarm1_status = False

            # Update remaining & display
            remaining = targettime - nowtime
            remaining //= 86400
            display.fill(0)
            display.print(remaining)

        # Process waiting server requests
        pool_result = server.poll()

        if pool_result == REQUEST_HANDLED_RESPONSE_SENT:
            pass
    except OSError as error:
        print(error)
        continue
