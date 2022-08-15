def do_connect(ssid, pwd):
    import network

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("connecting to network...")
        sta_if.active(True)
        sta_if.connect(ssid, pwd)
        while not sta_if.isconnected():
            pass
    print("network config:", sta_if.ifconfig())


# Attempt to connect to WiFi network
do_connect("your wifi ssid", "your password")

import webrepl

webrepl.start()
