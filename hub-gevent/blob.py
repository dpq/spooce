#!/usr/bin/python
# -*- coding: utf-8 -*-
from gevent import monkey; monkey.patch_socket()
from gevent.wsgi import WSGIServer
from ConfigParser import ConfigParser

from werkzeug import Request, Response
import logging, os, new, re, getopt, sys

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Boolean, DateTime, Text, Integer
from sqlalchemy import Table, Column, MetaData, ForeignKey, Index, desc, create_engine
from simplejson import dumps as tojson, loads as fromjson
from werkzeug import Local, LocalManager

import magic, default, secret
local = Local()
local_manager = LocalManager([local])

configfile = ""
Session = local('Session')
FileEntry = local('FileEntry')
local.Session = []
local.FileEntry = []

def __FileEntry_init__(self, id, filename, filetype):
    self.id = id
    self.filename = filename
    self.filename = filetype


def __FileEntry_repr__(self):
    print "File %s %s %s" % (self.id, self.filename, self.filetype)

def makeFileEntry(base):
    return new.classobj("fileentry", (base,), {
        "__tablename__": 'fileentry',
        "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
        "__init__": __FileEntry_init__,
        "__repr__": __FileEntry_repr__,
        "id": Column(String(32), primary_key=True),
        "filename": Column(String(128)),
        "filetype": Column(String(32)),
    })


class Blob(object):
    def __init__(self):
        pass

    def __upload(self, req):
        if "fileid" not in req.values:
            return ["FileID not specified"]
        try:
            session = Session[0]()
            if session.query(FileEntry[0]).filter_by(id=req.values["fileid"]).count() == 1:
                if len(req.files) != 1 or "file" not in req.files:
                    session.close()
                    return ["Accepts exactly one file"]
                file = req.files["file"]
                file.save(os.path.join(path, req.values["fileid"]))
                mime = magic.Magic(mime=True)
                filetype = mime.from_file(os.path.join(path, req.values["fileid"]))
                filename = file.filename
                session.add(FileEntry[0](req.values["fileid"], filename, filetype))
                session.commit()
                session.close()
                return ["File uploaded"]
            else:
                session.close()
                return ["Unauthorized request"]
        except:
            logging.error("__upload failure", exc_info=1)
            session.close()
            return ["An unknown error has occured"]
    
    def __download(self, req):
        if "fileid" not in req.values:
            return 404, "", "text/plain", [""]
        session = Session[0]()
        try:
            fileid = req.values["fileid"]
            force = False
            if "force" in req.values:
                force = True
            lang, appcode, versioncode = req.path.split("/")[2:5]
            if session.query(FileEntry[0]).filter_by(id=fileid).count() == 1:
                res = session.query(FileEntry[0]).filter_by(lang=lang, appcode=appcode, versioncode=versioncode).one()
                filename, filetype = res.filename, res.filetype
                session.close()
                body = open(os.path.join(path, fileid), "rb").read()
                if force:
                    filetype = "application/octet-stream"
                return 200, filename, filetype, [body]
        except:
            logging.error("__download failure", exc_info=1)
        session.close()
        return 404, "", "text/plain", [""]

    def __call__(self, env, start_response):
        Config = ConfigParser()
        Config.read(configfile)
        params = {"host": "", "user": "", "database": "", "port": ""}
        for param in params:
            if not Config.has_option("BlobStore", param):
                print "Malformed configuration file: mission option %s in section %s" % (param, "BlobStore")
                sys.exit(1)
            params[param] = Config.get("BlobStore", param)
        req = Request(env)
        resp = Response(status=200, content_type="text/plain")
        engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
            (params["user"], secret.BlobSecret, params["host"], params["port"], params["database"]), pool_recycle=3600)
        Base = declarative_base(bind=engine)
        local.Session = []
        local.FileEntry = []
        Session.append(sessionmaker(bind=engine))
        FileEntry.append(makeFileEntry(Base))
        if req.path.startswith('/fx'):
            if req.method == "GET":
                resp.status_code, filename, resp.content_type, resp.response = self.__download(req)
                if resp.content_type == "application/octet-stream":
                    resp.headers["Content-Disposition"] = "attachment; filename=%s" % filename
                return resp(env, start_response)
            elif req.method == "POST":
                resp.content_type="text/plain"
                resp.response = self.__upload(req)
                return resp(env, start_response)
        else:
            resp.status_code = 404
            resp.content_type="text/plain"
            resp.response = ""
            return resp(env, start_response)


def main():
    global configfile
    configfile, port, log = default.config, default.fxport, default.fxlog
    Base = {}

    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:", ["config="])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(1)

    for option, value in opts:
        if option in ("-c", "--config"):
            configfile = value

    Config = ConfigParser()
    Config.read(configfile)

    for section in ["FileSystem", "Global"]:
        if not Config.has_section(section):
            print "Malformed configuration file"
            sys.exit()

    if Config.has_option('Global', 'fxport'):
        port = Config.get('Global', 'fxport')
    if Config.has_option('Global', 'fxlog'):
        log = Config.get('Global', 'fxlog')

    logging.basicConfig(filename=log,
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)


    if not Config.has_section("BlobStore"):
        print "Malformed configuration file: missing section BlobStore"
        sys.exit(1)
    
    params = {"host": "", "user": "", "database": "", "port": ""}
    for param in params:
        if not Config.has_option("BlobStore", param):
            print "Malformed configuration file: mission option %s in section %s" % (param, "BlobStore")
            sys.exit(1)
        params[param] = Config.get("BlobStore", param)

    try:
        engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
            (params["user"], secret.BlobSecret, params["host"], params["port"], params["database"]), pool_recycle=3600)
        Base = declarative_base(bind=engine)
        Session.append(sessionmaker(bind=engine))
        FileEntry.append(makeFileEntry(Base))
        Base.metadata.create_all(engine)
    except:
        print "Failed to establish connection to the database"
        print "Check the log file for details"
        logging.error("DB connection failure", exc_info=1)
        sys.exit(1)

    server = WSGIServer(("0.0.0.0", int(port)), Blob())
    try:
        logging.info("Server running on port %s. Ctrl+C to quit" % port)
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        logging.info("Server stopped")


if __name__ == "__main__":
    main()
