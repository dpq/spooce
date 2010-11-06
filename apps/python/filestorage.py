#!/usr/bin/python
# -*- coding=utf-8 -*-

from threading import RLock
from urllib2 import urlopen
from urllib import unquote
from os import system
from uuid import uuid4

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import DateTime, Float, String, Integer
from sqlalchemy import Table, Column, MetaData, Index, create_engine, desc

from ConfigParser import ConfigParser
import new

Config = ConfigParser()
Config.read("/etc/spooce/apps/filestorage.cfg")

user, secret_MySQL = Config.get("MySQL", "user"), Config.get("MySQL", "passwd")
host, port, database = Config.get("MySQL", "host"), Config.get("MySQL", "port"), Config.get("MySQL", "database")
path = Config.get("FileSystem", "directory")


def __FileEntry_init__(self, id, filename, filetype):
    self.id = id
    self.filename = filename
    self.filetype = filetype
    

def __FileEntry_repr__(self):
    print "File %s %s %s" % (self.id, self.filename, self.filetype)


print "mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" % (user, secret_MySQL, host, port, database)

engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
    (user, secret_MySQL, host, port, database), pool_recycle=3600)
Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine)

FileEntry = new.classobj("fileentry", (Base, ), {
    "__tablename__": 'fileentry',
    "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
    "__init__": __FileEntry_init__,
    "__repr__": __FileEntry_repr__,
    "id": Column(String(32), primary_key=True),
    "filename": Column(String(128)),
    "filetype": Column(String(32)),
})


class FileStorage:
    def __init__(self):
        self.appid = ""
    
    def main(self, appid, args):
        self.appid = appid
    
    def mx(self, message):
        res = {}
        res["src"] = message["dst"]
        res["dst"] = message["src"]
        if message.has_key("msgid"):
            res["msgid"] = message["msgid"]
        if message["action"] == "upload":
            fileid = self.__fileid()
            message["fileid"] = fileid
        else:
            message["status"] = 1
            message["errmsg"] = "Unknown action"
            kernel.sendMessage(res)
    
    def __fileid(self):
        session = Session()
        fileid = uuid.uuid4().hex
        session.add(Filename(fileid, "", ""))
        session.commit()
        session.close()
        return fileid


opt.package["filestorage"]["1"] = FileStorage
