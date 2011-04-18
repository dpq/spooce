#!/usr/bin/python
# -*- coding=utf-8 -*-

from threading import RLock
from urllib2 import urlopen
from urllib import unquote
from os import system
import MySQLdb

class Textserver:
    def __init__(self):
        self.lock = RLock()
        self.possible = {
            "action" : ["read","write","writeurl","writetxt"],
            "strid" : "Aa_lat1.",
            "url" : "URL", # put your additional data into value
            "value" : ["http://site.my/.../img.png", "There can be some text string."],
            "msgid" : 0
        }
        self.__conn = MySQLdb.connect(host="localhost", db="sptxtsrv", user="textserv", passwd="-58.db.9AD.t9")
        self.__cursor = self.__conn.cursor()

    def __del__(self):
        self.__cursor.close()
        self.__conn.close()

    # Main in run to create an app instance, quit is run to destroy it.
    def main(self, appid = "textserv", arg = {}):
        self.appid = appid
#        system("mkdir -p %s" % self.__db)
#        # 23, textserver.py! Is the folder have a good name?
#        # 24, textserver.py TODO: check mkdir errors, check folder name

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
        return "textserver"

    def versioncode(self):
        return "1"

    def maintainer(self):
        return "Wera Barinova"

    def filepath(self):
        return "/home/wera/apps.bck/py/textserver.py"

    def mx(self, message):
        # 56, textserver.py: add read/write permissions!!
        if not self.valid(message):
            message["dst"] = message["src"]
            message["src"] = self.appid
            kernel.sendMessage(message)
            return
        act = message.pop("action")
        if act == "read":
            read = self.readTextFromDb(message["strid"])
            if read == None:
                message["value"] = ""
                message["status"] = 1
                message["errmsg"] = "Error reading from db. Incorrect id? (%s)" % message["strid"]
            else:
                message["value"] = read
                message["status"] = 0
        elif act == "write" or act == "writetxt":
            if not self.putTextToDb(message["strid"], message["value"]):
                message["status"] = 1
                message["errmsg"] = "Error writing to db, Sorry, check your request! :( %s )" % (message["strid"])
            else:
                message["status"] = 0
        elif act == "writeurl":
            try:
                r = urlopen(message["url"], message["value"]) # maybe do something with the value?
                txt = r.read()
                print "URL txt", txt
                putres = self.putTextToDb(message["strid"], txt)
                r.close()
                message["status"] = 0
            except:
                message["status"] = 1
                message["errmsg"] = "Error opening url."
            if not putres:
                message["status"] = 1
                message["errmsg"] = "Error writing to db"
        message["dst"] = message["src"]
        message["src"] = self.appid
        kernel.sendMessage(message)

    def valid(self, message): # add more validation
        result = "ok"
        if not message.has_key("action") or message["action"] not in self.possible["action"]:
            message["errmsg"] = "Incorrect action '%s'. Possible variants: %s" % (message["action"], "/".join(self.possible["action"]))
            message["status"] = 2
            return False
        if not message.has_key("strid") or not self.validTitle(message["strid"]):
            message["errmsg"] = "Incorrect or missing strid '%s'. Use digits, latin letters, '.' and '_'" % message["strid"]
            message["status"] = 3
            return False
        if message["action"] == "write" or message["action"] == "writetext": # write...
            if not message.has_key("value"):
                message["value"] = "None"
            else:
                if len(message["value"]) > 9990:
                    message["status"] = 9
                    message["errmsg"] = "Too long text. Try to use file server to store it."
                else:
                    res = {}
                    message["value"] = message["value"].replace("\n", "\\n").replace("\r", "\\r").replace('\"', '\u0022')
                    exec ('y = u"%s"' % message["value"]) in res
                    message["value"] = res["y"]
        if message["action"] == "writeurl":
            if not message.has_key("url"):
                message["errmsg"] = "No URL specified"
                message["status"] = 4
                return False
        return True

    def validTitle(self, strid): # Aa_lat1.
        result = True
        for l in strid:
            if ((l < "a" or l > "z") and
                (l < "A" or l > "Z") and
                (l < "0" or l > "9") and
                (l not in "._-")):
                result = False
                break
        return result

    def readTextFromDb(self, title):
#        try:
        if 1:
            self.__cursor.execute("select value from texts where strid=%s", title)
        result = self.__cursor.fetchone();
        if result == None or len(result) == 0:
            return None
        else:
            return result[0]
#        except:
#            return None

    def putTextToDb(self, title, text):
        try:
            readtxt = self.readTextFromDb(title)
            if readtxt == None:
                self.__cursor.execute("insert into texts set strid=%s, value=%s", (title, unquote(text).encode("utf-8")))
            else:
                self.__cursor.execute("update texts set value=%s where strid=%s", (unquote(text).encode("utf-8"), title))
            print "Done writing"
        except:
            return False
        kernel.sendMessage({"strid" : title, "value" : text, "src" : self.appid})
        return True

opt.package["textserver"]["1"] = Textserver
