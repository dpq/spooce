#!/usr/bin/python
import os
from spooce import kernel, opt

config = {
"hubURL" : "http://213.131.1.119/",
"tid"    : "testterminal",
"key"    : "mysecretkey",
"LocalRepo"   : os.getcwd() + "/"
}

apps = (
    (("helloworldapp", "1.0"), {"myarg": "myvalue"}),
)

kernel.init(config["hubURL"], config["tid"], config["key"], config["LocalRepo"])

print opt.package

for app in apps:
    kernel.run(app[0], app[1])

