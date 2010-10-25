#!/usr/bin/python
# -*- coding=utf-8 -*-

from threading import RLock
from urllib2 import urlopen
from urllib import unquote
from os import system
import MySQLdb
import Image
from StringIO import StringIO

class Imageserver:
    def __init__(self):
        self.lock = RLock()
        self.possible = {
            "action" : ["read","write","writeurl","delete"],
            "imgid" : "Aa_lat1.", # TODO: change to imgid
            "url" : "URL", # put your additional data into value
            "value" : ["http://site.my/.../img.png", "There can be some text string."],
            "msgid" : 0
        }
        self.__conn = MySQLdb.connect(host = "localhost", user = "imagserv", passwd = "sTj_7l", db = "spimgsrv")
        self.__cursor = self.__conn.cursor()
        self.__folder = "/home/wera/spooce/db/imagefolder/"
        self.__url = "http://213.131.1.4/~wera/imageserver/"

    def __del__(self):
        self.__cursor.close()
        self.__conn.close()

    def main(self, appid = "imgserv", arg = {}):
        if arg.has_key("folder"):
            self.__folder = arg["folder"]
        if arg.has_key("url"):
            self.__url = arg["url"]
        self.appid = appid
        system("mkdir -p %s" % self.__folder)

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
        return "imageserver"

    def versioncode(self):
        return "1"

    def maintainer(self):
        return "Wera Barinova"

    def filepath(self):
        return "/home/wera/spooce/apps.bck/py/imageserver.py"

    def mx(self, message):
        if not self.valid(message):
            message["dst"] = message["src"]
            message["src"] = self.appid
            kernel.sendMessage(message)
            return
        message["status"] = 0
        act = message.pop("action")
        if act == "read":
            readimg = self.readImageUrlFromDb(message["imgid"])
            if readimg == None:
                message["url"] = ""
                message["status"] = 12
                message["errmsg"] = "Error reading from db. Incorrect id? (%s)" % message["imgid"]
            else:
                message["url"] = readimg
        elif act == "write" or act == "writeurl": # Save Image URL into db
            if not self.putImageUrlToDb(message["imgid"], message["url"]):
                message["status"] = 13
                message["errmsg"] = "Error writing to db. Incorrect id? (%s)" % message["imgid"]
        if message["status"] == 0:
            try:
                message["width"], message["height"] = self.getImgSizes(message["url"])
                if act == "write": # broadcast
                    kernel.sendMessage({
                        "imgid" : message["imgid"],
                        "url" : message["url"],
                        "src" : self.appid,
                        "width" : message["width"],
                        "height" : message["height"]
                    })
            except:
                message["status"] = 14
                message["errmsg"] = "Cannot get sizes for image from database. Incorrect link?"
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

    def validTitle(self, imgid): # Aa_lat1.
        result = True
        for l in imgid:
            if ((l < "a" or l > "z") and
                (l < "A" or l > "Z") and
                (l < "0" or l > "9") and
                (l not in "._-")):
                result = False
                break
        return result

    def readImageUrlFromDb(self, title):
        print "select url from imageurls where imgid='%s';" % title
        self.__cursor.execute("select url from imageurls where imgid='%s'" % title)
        url = self.__cursor.fetchone()
        if url == None:
            return None
        url = url[0]
        return url

    def getImgSizes(self, url):
        print "open", url
        r = urlopen(url)
        image = r.read()
        r.close()
        img = Image.open(StringIO(image))
        return img.size

    def putImageUrlToDb(self, title, imageurl):
        try:
            readim = self.readImageUrlFromDb(title)
            if readim == None:
                print "insert into imageurls set imgid='%s', url='%s';" % (title, imageurl)
                self.__cursor.execute("insert into imageurls set imgid='%s', url='%s'" % (title, imageurl))
            else:
                print "update imageurls set url='%s' where imgid='%s';" % (imageurl, title)
                self.__cursor.execute("update imageurls set url='%s' where imgid='%s'" % (imageurl, title))
            return True
        except:
            return False

opt.package["imageserver"]["1"] = Imageserver
