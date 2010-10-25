#!/usr/bin/python
# -*- coding: utf-8 -*-
from werkzeug import Request, Response
import logging, os, new, re, getopt, sys

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Boolean, DateTime, Integer
from sqlalchemy import Table, Column, MetaData, ForeignKey, Index, desc, create_engine
from simplejson import dumps as tojson, loads as fromjson

import hashlib, hmac, secret, gzip, cStringIO, StringIO, zlib

import secret, default

Session, Board, Window = {}, {}, {}


Config = ConfigParser()
Config.read("/etc/spooce/apps/infiniboard.cfg")

user, host, port, database = Config.get("MySQL", "user"), Config.get("MySQL", "host"), Config.get("MySQL", "port"), Config.get("MySQL", "database")

engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
    (user, secret.MySQL, host, port, database), pool_recycle=3600)
Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine)

Board = new.classobj("board", (Base, ), {
    "__tablename__": 'board',
    "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
    "__init__": __Package_init__,
    "__repr__": __Package_repr__,
    "id": Column(DateTime()),
    "uid": Column(Float()),
    "access": Column(Integer())
})

Window = new.classobj("window", (Base, ), {
    "__tablename__": 'window',
    "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
    "__init__": __Package_init__,
    "__repr__": __Package_repr__,
    "id": Column(DateTime()),
    "x": Column(Float()),
    "y": Column(Float()),
    "z": Column(Float()),
    "width": Column(Float()),
    "height": Column(Float()),
    "meta": Column(String()),
    "args": Column(String())
})

Base.metadata.create_all(engine)


import MySQLdb

from mod_python import apache, Session, Cookie
from urllib import urlopen, urlencode
from base64 import b64encode
from fpformat import fix
import time
import uuid

from infinipassword import dbPassword

#select id, st_x(st_pointN(st_exteriorring(geom), 1)) as x, st_y(st_pointN(st_exteriorring(geom), 1)) as y, st_distance(st_pointN(st_exteriorring(geom),1), st_pointN(st_exteriorring(geom),2)) as width, st_distance(st_pointN(st_exteriorring(geom),2), st_pointN(st_exteriorring(geom),3)) as height, z, active, type, opacity, contents_revision, geom_revision, active_revision, contents from app


# If a session hasn't shown any life signs this many seconds, mark it inactive (don't display it to other users)
sessionTimeout = 30

def currentRevision(instance):
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    cursor.execute("select max(id) from revision")
    row = cursor.fetchone()
    if row == None:
        return 0
    else:
        return row[0]

def sessionAppId(sessionId, instance):
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    cursor.execute("select id from app where type='session' and contents = %s", sessionId)
    row = cursor.fetchone()
    if row == None:
        return 0
    else:
        return row[0]

def sessionExists(sessionId, instance, activeOnly = False):
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    if activeOnly:
        cursor.execute("select count(*) from app where type='session' and contents = %s and active = 1", sessionId)
    else:
        cursor.execute("select count(*) from app where type='session' and contents = %s", sessionId)
    if cursor.fetchone()[0] == 0:
        return False
    else:
        return True

def hello(req):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    sessionId = str(uuid.uuid4())
    
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
        else:
            sessionList = sessionList.value.split(",")
            for x in sessionList[:]:
                revisionCookie = receivedCookies.get('rev_' + str(sessionAppId(x, instance)), None)
                expirationCookie = receivedCookies.get('exp_' + str(sessionAppId(x, instance)), None)
                if not (expirationCookie and revisionCookie):
                    sessionList.remove(x)
                elif (expirationCookie.value < time.time() + 364*24*60*60) or (not sessionExists(x, instance, True) and sessionExists(x, instance)):
                    sessionList.remove(x)
                    revisionCookie.expires, expirationCookie.expires = 0, 0
                    Cookie.add_cookie(req, expirationCookie)
                    Cookie.add_cookie(req, revisionCookie)
            if len(sessionList) > 0:
                sessionList = ','.join(sessionList) + "," + sessionId
            else:
                sessionList = sessionId
    else:
        sessionList = sessionId
    
    cRevision = currentRevision(instance) + 1
    cursor.execute("lock tables `revision` write, `app` write, `timeout` write")
    cursor.execute("insert into app (type, active, active_revision, contents) values ('session', 1, %s, %s)", (cRevision, sessionId))
    sAppId = cursor.lastrowid
    cursor.execute("insert into revision (app_id, type) values (%s, 'active')", sAppId)
    cursor.execute("insert into timeout (app_id, last_seen) values (%s, now())", sAppId)
    cursor.execute("unlock tables")
    cursor.close()
    conn.close()
    
    sessionsCookie = Cookie.SignedCookie('sessions', sessionList, cookieSecret)
    sessionsCookie.expires = time.time() + 365*24*60*60
    Cookie.add_cookie(req, sessionsCookie)
    
    revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
    expirationCookie = Cookie.Cookie('exp_' + str(sAppId), str(time.time() + 365*24*60*60))
    
    revisionCookie.expires, expirationCookie.expires = time.time() + 365*24*60*60, time.time() + 365*24*60*60
    
    Cookie.add_cookie(req, revisionCookie)
    Cookie.add_cookie(req, expirationCookie)
    
    return "{status: 'ok', sid:'%s', sappid:'%s'}"%(sessionId, sAppId)


def bye(req, sid):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
        elif not sessionExists(sid, instance, True):
            return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
        elif sid not in sessionList.value:
            return "{status: 'error', errno:3, errmsg:'Something weird has happened.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    cRevision = currentRevision(instance) + 1
    sAppId = sessionAppId(sid, instance)
    cursor.execute("lock tables `revision` write, `app` write")
    cursor.execute("update app set active=0, active_revision=%s where contents=%s", (cRevision, sid))
    cursor.execute("insert into revision (app_id, type) values (%s, 'active')", sAppId)
    cursor.execute("unlock tables")
    cursor.close()
    conn.close()
    
    return "{status: 'ok'}"


def list(req, cx, cy, hw, hh, sid):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
        elif not sessionExists(sid, instance):
            return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
        elif sid not in sessionList.value:
            return "{status: 'error', errno:3, errmsg:'Something weird has happened.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    
    # Detect all goners (sessions that have been silent recently)
    cursor.execute("select app.id from timeout, app where app.type='session' and app.active=1 and timeout.app_id = app.id and timeout.last_seen < now() - %s", sessionTimeout)
    apps = cursor.fetchall()
    for x in apps:
        cRevision = currentRevision(instance) + 1
        cursor.execute("lock tables `revision` write, `app` write, `timeout` write")
        cursor.execute("update app set active = 0, active_revision = %s where id = %s", (cRevision, x[0]))
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("active", x[0]))
        cursor.execute("unlock tables")
    
    # This session has had gone away and is now coming back
    if sessionExists(sid, instance) and not sessionExists(sid, instance, True):
        sAppId = sessionAppId(sid, instance)
        cRevision = currentRevision(instance) + 1
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("update app set active = 1, active_revision = %s where id = %s", (cRevision, sAppId))
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("active", sAppId))
        cursor.execute("unlock tables")
    
    # Position of screen center, halfwidth and halfheight of the cache area
    cx, cy, hw, hh = int(cx), int(cy), int(hw), int(hh)
    
    # Top-left corner coordinates, width and height of the cache area
    cacheX, cacheY, cacheWidth, cacheHeight = cx - hw, cy - hh, hw*2, hh*2
    
    # Top-left corner coordinates, width and height of the visible area
    visX, visY, visWidth, visHeight = cx - hw/3, cy - hh/3, int(round(hw/1.5)), int(round(hh/1.5))
    
    cursor.execute("select id, type, x, y, z, width, height, opacity from app where IF(%s > x, %s, x) <= IF(%s < x+width, %s, x+width) AND IF(%s > y, %s, y) <= IF(%s < y+height, %s, y+height) and active=1 and id!=%s", (cacheX, cacheX, cacheX + cacheWidth, cacheX + cacheWidth, cacheY, cacheY, cacheY + cacheHeight, cacheY + cacheHeight, sessionAppId(sid, instance)))
    
    res = "[ "
    while True:
        row = cursor.fetchone()
        if row == None:
            break
        res += '{ id:"a_%s", type:"%s", x:%d, y:%d, z:%d, width:%d, height:%d, opacity: %.2f },'%(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
    
    cursor.execute("select x, y, width, height from app where id=%s", sessionAppId(sid, instance))
    row = cursor.fetchone()
    sAppId = sessionAppId(sid, instance)
    cRevision = currentRevision(instance) + 1
    if str(visX) != str(row[0]) or str(visY) != str(row[1]) or str(visWidth) != str(row[2]) or str(visHeight) != str(row[3]):
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("update app set x = %s, y = %s, width = %s, height = %s, geom_revision = %s where id = %s", (visX, visY, round(visWidth), round(visHeight), cRevision, sAppId))
        cursor.execute("insert into revision (app_id, type) values (%s, 'geom')", sAppId)
        cursor.execute("unlock tables")
    
    cursor.execute("update timeout set last_seen = now() where app_id = %s", sessionAppId(sid, instance))
    cursor.close()
    conn.close()
    
    revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
    revisionCookie.expires = time.time() + 365*24*60*60
    Cookie.add_cookie(req, revisionCookie)
    
    expirationCookie = Cookie.Cookie('exp_' + str(sAppId), str(time.time() + 365*24*60*60))
    expirationCookie.expires = time.time() + 365*24*60*60
    Cookie.add_cookie(req, expirationCookie)
    
    return "{status: 'ok', data: " + res[:-1] + "]}"


def checkin(req, cx, cy, hw, hh, sid):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    revision = receivedCookies.get('rev_' + str(sessionAppId(sid, instance)), None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
        if sid not in sessionList.value or revision == None:
            return "{status: 'error', errno:3, errmsg:'Something weird has happened.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    revision = int(revision.value)
    
    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    
    # Detect all goners (sessions that have been silent recently)
    cursor.execute("select app.id from timeout, app where app.type='session' and app.active=1 and timeout.app_id = app.id and timeout.last_seen < now() - %s", sessionTimeout)
    apps = cursor.fetchall()
    for x in apps:
        cRevision = currentRevision(instance) + 1
        cursor.execute("lock tables `revision` write, `app` write, `timeout` write")
        cursor.execute("update app set active = 0, active_revision = %s where id = %s", (cRevision, x[0]))
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("active", x[0]))
        cursor.execute("unlock tables")
    
    # This session has had gone away and is now coming back
    if sessionExists(sid, instance) and not sessionExists(sid, instance, True):
        sAppId = sessionAppId(sid, instance)
        cRevision = currentRevision(instance) + 1
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("update app set active = 1, active_revision = %s where id = %s", (cRevision, sAppId))
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("active", sAppId))
        cursor.execute("unlock tables")
    
    # Position of screen center, halfwidth and halfheight of the cache area
    cx, cy, hw, hh = int(cx), int(cy), int(hw), int(hh)
    
    # Top-left corner coordinates, width and height of the cache area
    cacheX, cacheY, cacheWidth, cacheHeight = cx - hw, cy - hh, hw*2, hh*2
    
    # Top-left corner coordinates, width and height of the visible area
    visX, visY, visWidth, visHeight = cx - hw/3, cy - hh/3, int(round(hw/1.5)), int(round(hh/1.5))
    
    cursor.execute("select id, type, x, y, z, width, height, active, geom_revision, contents_revision, active_revision, opacity from app where IF(%s > x, %s, x) <= IF(%s < x+width, %s, x+width) AND IF(%s > y, %s, y) <= IF(%s < y+height, %s, y+height) and id!=%s AND (geom_revision > %s OR contents_revision > %s OR active_revision > %s)", (cacheX, cacheX, cacheX + cacheWidth, cacheX + cacheWidth, cacheY, cacheY, cacheY + cacheHeight, cacheY + cacheHeight, sessionAppId(sid, instance), revision, revision, revision))
    
    res = "[ "
    
    for app in cursor.fetchall():
        res += "{id:'a_%d',"%app[0]
        # Geometry. We transmit app type because it will be needed if the app slides into someone's visible area
        if app[8] > revision:
            res += "type:'%s', geomUpdate:1, x:%d, y:%d, z:%d, width:%d, height:%d,opacity:%.2f,"%(app[1], app[2], app[3], app[4], app[5], app[6], app[11])
        # Contents
        if app[9] > revision:
            res += "contentsUpdate:1,"
        # Active status
        if app[10] > revision:
            if app[7] == 1:
                res += "activeUpdate:1, active:1, type:'%s', x:%d, y:%d, z:%d, width:%d, height:%d,"%(app[1], app[2], app[3], app[4], app[5], app[6])
            else:
                res += "activeUpdate:1, active:0,"
        res = res[:-1] + '},'
    
    if res != "[ ":
        revisionCookie = Cookie.Cookie('rev_' + str(sessionAppId(sid, instance)), str(currentRevision(instance)))
        revisionCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, revisionCookie)
        expirationCookie = Cookie.Cookie('exp_' + str(sessionAppId(sid, instance)), str(time.time() + 365*24*60*60))
        expirationCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, expirationCookie)
    
    res = res[:-1] + "]"
    
    cursor.execute("select x, y, width, height from app where id=%s", sessionAppId(sid, instance))
    row = cursor.fetchone()
    if str(visX) != str(row[0]) or str(visY) != str(row[1]) or str(visWidth) != str(row[2]) or str(visHeight) != str(row[3]):
        cRevision = currentRevision(instance) + 1
        sAppId = sessionAppId(sid, instance)
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("update app set x = %s, y = %s, width = %s, height = %s, geom_revision = %s where id = %s", (visX, visY, round(visWidth), round(visHeight), cRevision, sAppId))
        cursor.execute("insert into revision (app_id, type) values (%s, 'geom')", sAppId)
        cursor.execute("unlock tables")
        #return "%s %s; %s %s; %s %s; %s %s"%(str(visX), row[0], str(visY), row[1], str(visWidth), str(row[2]), str(visHeight), str(row[3]))
    
    cursor.execute("update timeout set last_seen = now() where app_id = %s", sessionAppId(sid, instance))
    cursor.close()
    conn.close()
    
    return "{status: 'ok', data: " + res + " }"

def viewcontents(req, id_list, zoom):
    req.content_type = "text/html"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    if 1:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        id_list = id_list.replace("a_", "").split(",")
        format_strings = ','.join(['%s']*len(id_list))
        cursor.execute("select id, contents, type from app where id in (%s) and active=true"%format_strings, tuple(id_list))
        res = "[ "
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            id = "a_" + str(row[0])
            contents = row[1]
            if row[2] == "session":
                res += '{id:"%s", contents: ""},'%(id)
            elif row[2] == "image":
                serverId = row[0]%10
                if serverId == 0:
                    serverId = 10
                if contents.startswith("http://infiniboard.ru"):
                    contents = "http://dec1.sinp.msu.ru/~rumith/ib/image/" + contents.split("/")[-1]
                res += '{id:"%s", contents: "%s"},'%(id, contents.replace('\"', '\\"').replace('\n', '\\n').replace('\r', '\\r'))
                #.replace("http://infiniboard.ru", "http://dec1.sinp.msu.ru/~rumith/ib").replace("img", "image"))
            else:
                res += '{id:"%s", contents: "%s"},'%(id, contents.replace('\"', '\\"').replace('\n', '\\n').replace('\r', '\\r'))
        cursor.close()
        conn.close()
        return res[:-1] + "]"
#   except:
#       cursor.close()
#       conn.close()
#       return "[ ]"

from urllib import FancyURLopener

class Crawler(FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11'

def downloadcontents(req, id):
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    
    instance = req.hostname.split(".")[0]

    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    if 1:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        cursor.execute("select id, contents, type from app where id=%s and active=true", id.replace("a_", ""))
        row = cursor.fetchone()
        if row == None:
            return ""
        req.headers_out["Content-type"] = "application/force-download"
        if row[2] == "image":
            crawler = Crawler()
            req.headers_out["Content-Disposition"] = "attachment; filename=%s.%s"%(id, row[1].split(".")[-1])
            req.write(crawler.open(row[1]).read())
            cursor.close()
            conn.close()
            return
        elif row[2] == "text":
            req.headers_out["Content-Disposition"] = "attachment; filename=%s.txt"%id
            req.write(row[1])
            cursor.close()
            conn.close()
            return
        elif row[3] == "session":
            req.headers_out["Content-Disposition"] = "attachment; filename=%s.txt"%id
            req.write("Not implemented")
            cursor.close()
            conn.close()
            return
        else:
            cursor.close()
            conn.close()
            return ""
    #except:
    #       cursor.close()
    #       conn.close()
    #       return ""

from urllib import unquote_plus
from base64 import b64encode
from os import chdir, path, system
from subprocess import Popen, PIPE

def export(req, cx, cy, hw, hh, z, sid, format="html", ie = "0"):
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"

    chdir("/home/rumith/infiniboard-demo/export.tmp")
    if path.isfile(sid + "." + format) or path.isfile(sid + ".html"):
        return

    conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
    cursor = conn.cursor()
    
    # Position of screen center, halfwidth and halfheight of the cache area
    cx, cy, hw, hh, = int(cx), int(cy), int(hw), int(hh)
    
    # Top-left corner coordinates, width and height of the cache area
    cacheX, cacheY, cacheWidth, cacheHeight = cx - hw, cy - hh, hw*2, hh*2
    
    # Top-left corner coordinates, width and height of the visible area
    visX, visY, visWidth, visHeight = cx - hw/3, cy - hh/3, int(round(hw/1.5)), int(round(hh/1.5))
    
    cursor.execute("select id, type, x, y, z, width, height, contents from app where IF(%s > x, %s, x) <= IF(%s < x+width, %s, x+width) AND IF(%s > y, %s, y) <= IF(%s < y+height, %s, y+height) and active=1 and id!=%s", (cacheX, cacheX, cacheX + cacheWidth, cacheX + cacheWidth, cacheY, cacheY, cacheY + cacheHeight, cacheY + cacheHeight, sessionAppId(sid, instance)))
    #cursor.execute("select id, type, x, y, z, width, height, contents from app where IF(%s > x, %s, x) <= IF(%s < x+width, %s, x+width) AND IF(%s > y, %s, y) <= IF(%s < y+height, %s, y+height) and active=1 and id!=%s", (visX, visX, visX + visWidth, visX + visWidth, visY, visY, visY + visHeight, visY + visHeight, sessionAppId(sid, instance)))
    
    res = "<div id='board' style='width:100%%;height:100%%; font-size:%d'>\n"%int(z)
    while True:
        row = cursor.fetchone()
        if row == None:
            break
        x = row[2] - cx + hw/3
        y = row[3] - cy + hh/3
        if row[1] == "text":
            res += '<div id="a_%s" class="app" style="left: %sem; top: %sem; z-index:%s; width: %sem; height: %sem"><pre>%s</pre></div>\n'%(row[0],  x, y, row[4], row[5], row[6], row[7])
        elif row[1] == "image":
                res += '<div id="a_%s" class="app" style="background: transparent; left: %sem; top: %sem; z-index:%s; width: %sem; height: %sem"><img style="width:100%%;height:100%%" src="%s" alt="" /></div>\n'%(row[0], x, y, row[4], row[5], row[6], row[7])
        elif row[1] == "session":
            pass

    res += '\n</div>\n'
    req.headers_out["Content-type"] = "application/force-download"
    exportHTML = "<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8' /><title>Export file</title><style type='text/css'>%s</style></head><body>\n%s</body></html>"%(open("/home/rumith/infiniboard-demo/" + req.hostname + "_style/base.css").read().replace(":hover", "disabled_hover"), res)
    req.headers_out["Content-type"] = "application/force-download"
    
    if format == "html":
        # TODO zip this stuff
        req.headers_out["Content-Disposition"] = "attachment; filename=export.html"
        req.write(exportHTML)
        return
    
    file = open(sid + ".html", "w")
    file.write(exportHTML)
    file.close()
    try:
        system("DISPLAY=:0.0 unoconv -f %s %s.html"%(format, sid))
        req.headers_out["Content-Disposition"] = "attachment; filename=export.%s"%format
        #req.content_type = "text/html"
        req.write(open(sid + "." + format).read())
        system("rm %s.%s"%(sid, format))
        system("rm %s.html"%sid)
        return
    except:
        req.headers_out["Content-Disposition"] = "attachment; filename=error.txt"
        req.write("An error has occured: couldn't convert file to the specified format.")
        system("rm %s.html"%sid)
        return

"""if ie == "1":
                pass
            else:
                url = row[7]
                filetype = url.split(".")[-1]
                b64header = "data:image/%s;base64,"%filetype
                try:
                    b64body = b64encode(urlopen(url).read())
                except:
                    continue"""
# res += '<div id="a_%s" class="app" style="background: transparent; left: %sem; top: %sem; z-index:%s; width: %sem; height: %sem"><img style="width:100%%;height:100%%" src="%s%s" alt="" /></div>\n'%(row[0], x, y, row[4], row[5], row[6], b64header, b64body)

def search(req, query):
    req.content_type = "text/html"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    if query == "":
        return "{status: 'ok', list:''}"
    
    try:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        cursor.execute("select id from app where contents like %s and active=1 and type='text'", "%" + query + "%")
        res = ""
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            res += str(row[0]) + ','
        res = res[:-1]
        return "{status: 'ok', list:'%s'}"%res
    except Exception, (ErrorNumber, ErrorMessage):
        cursor.close()
        conn.close()
        return "{status: 'error', errno: %d, errmsg: \"%s\"}"%(ErrorNumber, ErrorMessage)

def createapp(req, x, y, z, width, height, apptype, sid):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    try:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        
        cRevision = currentRevision(instance) + 1
        sAppId = sessionAppId(sid, instance)
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("insert into app (x, y, z, width, height, type, active, active_revision) values (%s, %s, %s, %s, %s, %s, 1, %s)", (x, y, z, width, height, apptype, cRevision))
        appId = cursor.lastrowid
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("active", appId))
        revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
        revisionCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, revisionCookie)
        cursor.execute("unlock tables")
        cursor.close()
        conn.close()
        return "{status: 'ok', id: 'a_%d'}"%appId
    except Exception, (ErrorNumber, ErrorMessage):
        cursor.close()
        conn.close()
        return "{status: 'error', errno: %d, errmsg: \"%s\"}"%(ErrorNumber, ErrorMessage)

def closeapp(req, id, sid):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    try:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        sAppId = sessionAppId(sid, instance)
        cRevision = currentRevision(instance) + 1
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("active", id.replace("a_", "")))
        cursor.execute("update app set active=0, active_revision=%s where id=%s and active=1", (cRevision, id.replace("a_", "")))
        revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
        revisionCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, revisionCookie)
        cursor.execute("unlock tables")
        cursor.close()
        conn.close()
        return "{status: 'ok'}"
    except Exception, (ErrorNumber, ErrorMessage):
        cursor.close()
        conn.close()
        return "{status: 'error', errno: %d, errmsg: \"%s\"}"%(ErrorNumber, ErrorMessage)


def updateinfo(req, id, x, y, z, width, height, opacity, sid):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
        
    try:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        cRevision = currentRevision(instance) + 1
        sAppId = sessionAppId(sid, instance)
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("geom", id.replace("a_", "")))
        cursor.execute("update app set x=%s, y=%s, z=%s, width=%s, height=%s, opacity=%s, geom_revision=%s where id=%s and active=1", (x, y, z, width, height, opacity, cRevision, id.replace("a_", "")))
        revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
        revisionCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, revisionCookie)
        cursor.execute("unlock tables")
        cursor.close()
        conn.close()
        return "{status: 'ok', id:'%s'}"%id
    except Exception, (ErrorNumber, ErrorMessage):
        cursor.close()
        conn.close()
        return "{status: 'error', id:'%s', errno: %d, errmsg: \"%s\"}"%(id, ErrorNumber, ErrorMessage)

from urllib import urlretrieve
from urllib2 import urlopen

def updatecontents(req):
    req.content_type = "text/json"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    id = req.form["id"].replace("a_", "")
    sid = req.form["sid"]
    contents = req.form["contents"]
    filetype = req.form["type"]
    
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    try:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        cRevision = currentRevision(instance) + 1
        sAppId = sessionAppId(sid, instance)
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("contents", id))
        if filetype == "text":
            value = contents
            cursor.execute("update app set contents=%s, contents_revision=%s where id=%s and active=1", (value, cRevision, id))
        elif filetype == "image":
            extension = contents.split(".")[-1]
            try:
                urlopen(contents)
                file = open("/home/rumith/infiniboard-demo/image/%s.%s"%(id, extension), "wb")
                crawler = Crawler()
                file.write(crawler.open(contents).read())
                file.close()
                value = "http://dec1.sinp.msu.ru/~rumith/ib/image/%s.%s"%(req.hostname,  id, extension)
                #value = "http://%s/img/%d/%s.%s"%(req.hostname, int(time.time()), id, extension)
            except:
                file = open("/home/rumith/infiniboard-demo/image/%s.png"%id, "wb")
                file.write(open("/home/rumith/infiniboard-demo/%s_style/notfound.gif"%req.hostname).read())
                file.close()
                value = "http://dec1.sinp.msu.ru/~rumith/ib/image/%s.png"%(req.hostname,  id)
                #value = "http://%s/img/%d/%s.png"%(req.hostname, int(time.time()), id)
            cursor.execute("update app set contents=%s, contents_revision=%s where id=%s and active=1", (value, cRevision, id))
        
        revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
        revisionCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, revisionCookie)
        cursor.execute("unlock tables")
        cursor.close()
        conn.close()
        return "{status: 'ok', contents: '%s'}"%value.replace('\"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace("\'", "\\'")
    except Exception, (ErrorNumber, ErrorMessage):
        cursor.close()
        conn.close()
        return "{status: 'error', id:'%s', errno: %d, errmsg: \"%s\"}"%(req.form["id"], ErrorNumber, ErrorMessage)

from os import getcwd

from subprocess import call

def uploadcontents(req):
    req.content_type = "text/html"
    req.headers_out.add('Cache-Control', "no-store, no-cache, must-revalidate")
    req.headers_out.add('Pragma', "no-cache")
    req.headers_out.add('Expires', "-1")
    instance = req.hostname.split(".")[0]
    
    id = req.form["id"].replace("a_", "")
    sid = req.form["sid"]
    zoom = req.form["zoom"]
    filetype = req.form["type"]
    extension = req.form["contents"].filename.split(".")[-1]
    contents = req.form["contents"].value
    cookieSecret = 't3rr4G3N'
    receivedCookies = Cookie.get_cookies(req, Cookie.SignedCookie, secret = cookieSecret)
    sessionList = receivedCookies.get('sessions', None)
    if sessionList:
        if type(sessionList) is not Cookie.SignedCookie:
            return "{status: 'error', errno:1, errmsg:'Permission denied.'}"
    else:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    registered = False
    for tmp in sessionList.value.split(","):
        if sessionExists(tmp, instance):
            registered = True
            break
    if not registered:
        return "{status: 'error', errno:2, errmsg:'You are not logged in.'}"
    
    if 1:
        conn = MySQLdb.connect(host = "localhost", user = instance, passwd = dbPassword[instance], db = instance)
        cursor = conn.cursor()
        cRevision = currentRevision(instance) + 1
        sAppId = sessionAppId(sid, instance)
        cursor.execute("lock tables `revision` write, `app` write")
        cursor.execute("insert into revision (type, app_id) values (%s, %s)", ("contents", id))
        if filetype == "text":
            value = contents.replace('\"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            cursor.execute("update app set contents=%s, contents_revision=%s where id=%s and active=1", (value, cRevision, id))
        elif filetype == "image":
            file = open("/home/rumith/infiniboard-demo/image/orig.%s.%s"%(id, extension), "wb")
            file.write(contents)
            file.close()
            previewSteps = [ "0.1", "0.15", "0.2", "0.3", "0.4", "0.5", "0.75", "1" ]
            sliceSteps = [ 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 90, 96 ]
            # TODO make previews and slices
            #for z in previewSteps:
            #   call(["/home/rumith/infiniboard/previewImage/preview", "/home/rumith/infiniboard/img/orig.%s.%s"%(id, extension), str(100*float(z)) + "%x" + str(100*float(z)) + "%", "/home/rumith/infiniboard/img/%s.%s.%s"%(z, id, extension) ])
            value = "http://dec1.sinp.msu.ru/~rumith/ib/image/orig.%s.%s"%(id, extension)
            #value = "http://%s/img/%d/orig.%s.%s"%('.'.join(req.hostname.split(".")[-2:]), int(time.time()), id, extension)
            cursor.execute("update app set contents=%s, contents_revision=%s where id=%s and active=1", (value, cRevision, id))
        revisionCookie = Cookie.Cookie('rev_' + str(sAppId), str(cRevision))
        revisionCookie.expires = time.time() + 365*24*60*60
        Cookie.add_cookie(req, revisionCookie)
        cursor.execute("unlock tables")
        cursor.close()
        conn.close()
        return "{status: 'ok', contents: '%s'}"%value.replace('\"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace("'", "\'")
    #except Exception, (ErrorNumber, ErrorMessage):
    #   cursor.close()
    #   conn.close()
    #   return "{status: 'error', id:'%s', errno: %d, errmsg: \"%s\"}"%(id, ErrorNumber, ErrorMessage)
