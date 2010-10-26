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
        kernel.sendMessage({
            "src": self.appid,
            "dst": "/std/image",
            "imgid": message["imgid"],
            "action": "write",
            "url": "http://dec1.sinp.msu.ru/~wera/imageserver/" + self.tmpdir + "/" + self.draw(message["data"], ttl)
        })

    def stepsMaxMin(max, min):
        if min <= 0:
            min = 0.0001
        if max <= 0:
            max = 10
        max = pow(10, ceil(log10(max)))
        min = pow(10, floor(log10(min)))
        steps = log10(max / min)
        return steps, max, min

    def newFile(self):
        return int(max(listdir())[:-4]) + 1

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

"""    def getMaxMin(Columns):
        horCol = []
        vertCol = []
        for i in range(len(Columns)):
            for elem in Columns[i]:
                if (elem != -99e+99):
                    if i != 0:
                        vertCol.append(elem)
                    else:
                        horCol.append(elem)
        horMax = max(horCol)
        horMin = min(horCol)
        vertMax = max(vertCol)
        vertMin = min(vertCol)
        return horMax, horMin, vertMax, vertMin

    def getElem(elemList, attrName, attrValue):
        for elem in elemList:
            if elem.getAttribute(attrName) == attrValue:
                return elem
        return None

    def getElems(elemList, attrName, attrValue):
        result = []
        for elem in elemList:
            if elem.getAttribute(attrName) == attrValue:
                result.append(elem)
        return result
        if (elem != 0) and (dt != 0):
            datelabel = getElem(domFile.getElementsByTagName("grid"), "id", "datelabel")
            datelabel.setAttribute("title", "Event: " + dt + " [YYMMDD]")
            elemlabel = getElem(domFile.getElementsByTagName("grid"), "id", "elemlabel")
            elemlabel.setAttribute("title", "Element: " + elem)
    """
