import os
import board
from adafruit_ht16k33.segments import BigSeg7x4
import wifi
import socketpool
from adafruit_httpserver import Server, Request, Response, POST, GET
import adafruit_requests
import ssl
from adafruit_datetime import datetime, date, time

i2c = board.I2C()
display = BigSeg7x4(i2c, address=0x70)
display.brightness = 0.2

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, debug=True)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

aio_username = os.getenv("AIO_USERNAME")
aio_key = os.getenv("AIO_KEY")
timezone = os.getenv("TIMEZONE")
TIME_URL = f"https://io.adafruit.com/api/v2/{aio_username}/integrations/time/strftime?x-aio-key={aio_key}"
TIME_URL += "&fmt=%25Y-%25m-%25d"
ISODATE_URL = "https://io.adafruit.com/api/v2/time/ISO-8601"

print("Fetching time from", ISODATE_URL)
response = requests.get(ISODATE_URL)
print("-" * 40)
print(response.text)
print("-" * 40)

#  prints MAC address to REPL
# print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])

#  prints IP address to REPL
# print("My IP address is", wifi.radio.ipv4_address)


FORM_HTML_TEMPLATE = """
<html lang="en">
    <head>
        <title>Update LEDs</title>
    </head>
    <body>
        <h2>Type in end date (integers only).</h2>
        <form action="/" method="post" enctype="text/plain">
            <label for "fdate"> ISOdate:</label>
            <input type="text" id="fdate" name="fdate" value="2025-04-30"><br>
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
        posted_value = request.form_data.get("fdate")
        # Get todays date & convert
        isodate_string = requests.get(TIME_URL)
        todaydate = datetime.fromisoformat(isodate_string.text)
        #targetdate = datetime(2025, 4, 30)
        targetdate = datetime.fromisoformat(posted_value)
        interval = targetdate - todaydate
        print(interval.days)

        # update display
        # posted_value = "0000"
        display.fill(0)
        display.print(interval.days)

    return Response(
        request,
        FORM_HTML_TEMPLATE.format(
            enctype=enctype,
            submitted_value=(
                f"<h3>Submitted form value: {posted_value}</h3>"
                if request.method == POST
                else ""
            ),
        ),
        content_type="text/html",
    )

server.serve_forever(str(wifi.radio.ipv4_address))
