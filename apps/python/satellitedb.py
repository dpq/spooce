#!/usr/bin/python
# -*- coding=utf-8 -*-

from threading import RLock
from urllib2 import urlopen
from urllib import unquote
from os import system
import MySQLdb
import Image
from StringIO import StringIO

class Satellitedb:
    def __init__(self):
        self.lock = RLock()
        self.possible = {
            "action" : ["list", "info","write"],
            "satName" : "" # the same names as in the list
        }
        self.__conn = MySQLdb.connect(host = "localhost", user = "satellitedb", passwd = "g78JH_FEk30", db = "satellitedb")
        self.__cursor = self.__conn.cursor()

    def __del__(self):
        self.__cursor.close()
        self.__conn.close()

    def main(self, appid = "satellitedb", arg = {}):
        self.appid = appid

    def depInfo(self):
        return {
            "depends" : [("baseapp", "1")],
            "conflicts"  : [],
            "upgrades" : [],
            "replaces" : [],
            "suggests" : [],
            "recommends" : []
        }

    def appcode(self):
        return "satellitedb"

    def versioncode(self):
        return "1"

    def maintainer(self):
        return "Wera Barinova"

    def filepath(self):
        return "/home/wera/spooce/apps.bck/small/satellitedb.py"

    def mx(self, message):
        if not self.valid(message):
            message["dst"] = message["src"]
            message["src"] = self.appid
            kernel.sendMessage(message)
            return
        message["status"] = 0
        action = message.pop("action")
        if action == "list":
            satArray = self.getSatellist()
            if satArray == None:
                message["value"] = ""
                message["status"] = 12
                message["errmsg"] = "Error reading from db. Incorrect id? (%s)" % message["imgid"]
            else:
                message["value"] = map(lambda sat: sat[0], satArray)
#        elif action == "write": # Save Image URL into db
#            if not self.putImageUrlToDb(message["imgid"], message["url"]):
#                message["status"] = 13
#                message["errmsg"] = "Error writing to db. Incorrect id? (%s)" % message["imgid"]
        message["dst"] = message["src"]
        message["src"] = self.appid
        kernel.sendMessage(message)

    def valid(self, message): # add more validation
        if not message.has_key("action") or message["action"] not in self.possible["action"]:
            message["errmsg"] = "Incorrect action '%s'. Possible variants: %s" % (message["action"], "/".join(self.possible["action"]))
            message["status"] = 11
            return False
        if not message.has_key("imgid") or not self.validTitle(message["imgid"]):
            message["errmsg"] = "Incorrect or missing imgid '%s'. Use digits, latin letters, '.' and '_'" % message["imgid"]
            message["status"] = 10
            return False
        if message["action"] == "write" or message["action"] == "writeurl":
            if not message.has_key("url"):
                message["errmsg"] = "No URL specified"
                message["status"] = 16
                return False
        return True

    def getSatellist(self):
        print "select sysname from satellite;"
        self.__cursor.execute("select sysname from satellite;")
        return self.__cursor.fetchall()

    def getSatChannels(self, satname, instrname=None, channame=None): # you can also use a sysname
        cursor.execute("select id from satellite where display='%s' or sysname='%s';" % (satname, satname))
        cond = "idSatellite='%i'" % cursor.fetchone()[0]
        if instrname != None:
            cursor.execute("select id from satinstrument where name='%s';" % (instrname, ))
            cond += " and idInstrument='%i'" % cursor.fetchone()[0]
        if channame != None:
            cond += " and name='%s'" % channame
        print "select * from channel where " + cond
        cursor.execute("select * from channel where " + cond)
        return cursor.fetchall()

opt.package["satellitedb"]["1"] = Satellitedb
