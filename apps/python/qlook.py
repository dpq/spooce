#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from xml.dom.minidom import parse
from os import system, chdir
from threading import Timer
import logging

class QlookWrapper:
    def main(self, appid, args):
        self.appid = appid
        dir = ""
        try:
            dir = args["tmpdir"]
            system("mkdir -p %s" % dir)
            system("touch %s/0.txt" % dir)
            chdir(dir)
            self.tmpdir = dir.split("/")[-1]
        except:
            logging.error("Cannot change the directory to %s" % dir)
        system("export DISPLAY=:1.0")

    def mx(self, message):
        if message.has_key("ttl"):
            ttl = message["ttl"]
        else:
            ttl = 60
        f = open("testqlook.tst", "wa")
        f.write(message["value"])
        print "QLOOK", message["value"]
        f.close()
#        kernel.sendMessage({
#            "src": self.appid,
#            "dst": "/std/image",
#            "imgid": message["imgid"],
#            "action": "write",
#            "url": "http://dec1.sinp.msu.ru/~wera/imageserver/" + self.tmpdir + "/" + self.draw(message["data"], ttl)
#        })

    def draw(self, data, ttl): # ttl : seconds
        fileName = newFile()
        f = open(fileName + ".xml", "w")
        f.write(data)
        f.close()
        system("qlook < %s > %s" % (fileName + ".xml", fileName + ".png"))
        Timer(ttl, self.__delete, [fileName + ".png"]).start()
        Timer(ttl, self.__delete, [fileName + ".xml"]).start()
        return fileName + ".png"

    def validate(self, data):
        return True

    def __delete(self, filename):
        system("rm " + filename)

opt.package["qlook"]["1"] = QlookWrapper
