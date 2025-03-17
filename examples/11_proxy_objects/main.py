import argparse

import belay

parser = argparse.ArgumentParser()
parser.add_argument("--port", "-p", default="/dev/ttyUSB0")
args = parser.parse_args()

device = belay.Device(args.port)


@device.setup
def setup():
    class User:
        def __init__(self, name):
            self.name = name

        def greetings(self):
            return f"Hello {self.name}!"

    user = User("Bob Smith")


setup()

# Create a ProxyObject for the micropython object "user" that was defined in setup() .
# This is just a thin wrapper for calling belay.ProxyObject(device, "user") .
user = device.proxy("user")

user_name = user.name
print(f'We got the attribute "{user_name}".')
# We got the attribute "Bob Smith".

result = user.greetings()
print(f'We executed the method "greetings" and got the result: "{result}"')
# We executed the method "greetings" and got the result: "Hello Bob Smith!"
