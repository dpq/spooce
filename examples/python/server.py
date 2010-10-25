#!/usr/bin/python
import os
import spooce

config = {
"hubURL" : "http://213.131.1.119/",
"tid"    : "testterminal",
"key"    : "mysecretkey",
"LocalRepo"   : os.getcwd()
}

apps = (
    (("helloworldapp", "1.0"), {"myarg": "myvalue"}),
)

kernel = spooce.Kernel(config["hubURL"], config["tid"], config["key"], config["LocalRepo"])

for app in apps:
    kernel.run(app[0], app[1])
