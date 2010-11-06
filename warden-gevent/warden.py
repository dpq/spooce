#!/usr/bin/python
# -*- coding: utf-8 -*-
from gevent import monkey; monkey.patch_socket()
from gevent.wsgi import WSGIServer

from werkzeug import Request, Response
import logging, os, getopt, sys, new, hmac, hashlib
from urllib import quote_plus as quote, urlencode
from uuid import uuid4
from ConfigParser import ConfigParser

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Boolean, DateTime, Text, Integer
from sqlalchemy import Table, Column, MetaData, Index, desc, create_engine
from urllib2 import urlopen
import secret, default
from geventmemcache.client import Memcache
from werkzeug import Local, LocalManager

import smtplib
from email.mime.text import MIMEText

local = Local()
local_manager = LocalManager([local])
Session = local('Session')
User = local('User')
MethodEmail = local('MethodEmail')
local.Session = []
local.User = []
local.MethodEmail = []

configfile = ""

def __User_init__(self):
    pass

def __User_repr__(self):
    return "<User('%d')>"%(self.uid)

def __MethodEmail_init__(self, uid, email, password):
    self.uid = uid
    self.email = email
    self.password = password

def __MethodEmail_repr__(self):
    return "<MethodEmail(%d => %s)>" % (self.uid, self.email)

def makeUser(base):
    return new.classobj("user", (base, ), {
        "__tablename__": 'user',
        "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
        "__init__": __User_init__,
        "__repr__": __User_repr__,
        "uid": Column(Integer, primary_key=True)
    })

def makeMethodEmail(base):
    return new.classobj("method_email", (base, ), {
        "__tablename__": 'method_email',
        "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
        "__init__": __MethodEmail_init__,
        "__repr__": __MethodEmail_repr__,
        "email": Column(String(255), primary_key=True, autoincrement=False),
        "password": Column(String(40)),
        "uid": Column(Integer)
    })


# Ported from Recipe 3.9 in Secure Programming Cookbook for C and C++ by
# John Viega and Matt Messier (O'Reilly 2003)

from string import *

rfc822_specials = '()<>@,;:\\"[]'

def isValidAddress(addr):
    if addr.count('@') != 1:
        return 0
    if not min(map(lambda x, y : len(x) < y, addr.split('@'), [64, 255])):
        return 0
    
    # First we validate the name portion (name@domain)
    c = 0
    while c < len(addr):
        if addr[c] == '"' and (not c or addr[c - 1] == '.' or addr[c - 1] == '"'):
            c = c + 1
            while c < len(addr):
                if addr[c] == '"': break
                if addr[c] == '\\' and addr[c + 1] == ' ':
                    c = c + 2
                    continue
                if ord(addr[c]) < 32 or ord(addr[c]) >= 127: return 0
                c = c + 1
            else: return 0
            if addr[c] == '@': break
            if addr[c] != '.': return 0
            c = c + 1
            continue
        if addr[c] == '@': break
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127: return 0
        if addr[c] in rfc822_specials: return 0
        c = c + 1
    if not c or addr[c - 1] == '.': return 0

    # Next we validate the domain portion (name@domain)
    domain = c = c + 1
    if domain >= len(addr): return 0
    count = 0
    while c < len(addr):
        if addr[c] == '.':
            if c == domain or addr[c - 1] == '.': return 0
            count = count + 1
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127: return 0
        if addr[c] in rfc822_specials: return 0
        c = c + 1

    return count >= 1


class Warden(object):
    def __init__(self):
        self.mc = {}


    def __register(self, req):
        if not req.values.has_key("method"):
            return ["You must provide a registration method"]
        method = req.values["method"]
        if method == "email":
            return ["""<!DOCTYPE html>
            <html>
            <head>
                <title>Please enter the email address</title>
                <script type="text/javascript">
                var RecaptchaOptions = {theme: 'clean'};
                </script>
            </head>
            <body>
                <form action="/regemail1" method="post">
                    <span>Please enter the email address:</span><br/>
                    <input type="text" size="45" name="email" style="border: 1px solid black; width: 302px" /><br/>
                    <span>Please enter the two words below:</span><br/>
                    <script type="text/javascript" src="http://www.google.com/recaptcha/api/challenge?k=6LfzRL0SAAAAALYxeIddE1g7Eqq-UP-jYHYRBwS3"></script>
                    <noscript>
                        <iframe src="http://www.google.com/recaptcha/api/noscript?k=6LfzRL0SAAAAALYxeIddE1g7Eqq-UP-jYHYRBwS3" height="300" width="500" frameborder="0"></iframe><br/>
                        <textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
                        <input type="hidden" name="recaptcha_response_field" value="manual_challenge" />
                    </noscript>
                    <input type="submit" />
                </form>
            </body>
            </html>"""]
        else:
            return ["Method not supported"]


    def __addEmailAuth1(self, req):
        if not req.values.has_key("email"):
            return ["You must provide an email address"]
        email = req.values["email"]
        if not isValidAddress(email):
            return ["Invalid email address"]
        
        if not req.values.has_key("recaptcha_challenge_field") or not req.values.has_key("recaptcha_response_field"):
            return ["No CAPTCHA received"]
        
        rc = {}
        rc["privatekey"] = secret.RecaptchaKey
        rc["remoteip"] = req.remote_addr
        rc["challenge"] = req.values["recaptcha_challenge_field"]
        rc["response"] = req.values["recaptcha_response_field"]
        res = urlopen("http://www.google.com/recaptcha/api/verify", urlencode(rc)).read().split("\n")
        
        if res[0] == "false":
            return [res[1]]
        
        session = Session[0]()
        query = session.query(MethodEmail[0]).filter_by(email=email)
        uid = self.__uid(req)
        token = str(uuid4())
        if uid == None and query.count() == 0:
            # New user
            self.mc.set("tmptoken_" + token, "%s" % (email), 3600)
        elif query.count() == 1 and query.one().uid == uid and uid != None:
            # Setting a new password
            self.mc.set("tmptoken_" + token, "%s %s" % (email, uid), 3600)
        elif query.count() == 0 and uid != None:
            # Adding a new email
            self.mc.set("tmptoken_" + token, "%s %s" % (email, uid), 3600)
        else:
            return ["Permission denied"]

        try:
            msg = MIMEText('<a href="%sregemail2?token=%s">Complete the registration process</a>' % (req.host_url, token), "html", "utf-8")
            msg['Subject'] = 'Spooce registration'
            msg['From'] = 'noreply@spooce.com'
            msg['To'] = email
            s = smtplib.SMTP()
            s.connect()
            s.sendmail('noreply@spooce.com', [email], msg.as_string())
            s.quit()
            session.close()
        except:
            logging.error("__addEmailAuth1 failure", exc_info=1)
            return ["Internal server error"]
        return ["Authentication email sent to the specified address."]
    

    def __addEmailAuth2(self, req):
        if not req.values.has_key("token"):
            return ["Access denied"]
        token = req.values["token"]
        try:
            token = self.mc.get("tmptoken_" + str(token))
        except:
            logging.error("__addEmailAuth2 failure", exc_info=1)
            return ["Internal server error"]
        
        if token is None:
            return ["Token does not exist or has expired"]
        
        page = """<!DOCTYPE html>
        <html>
        <head>
            <title>Please enter the password</title>
            <script type="text/javascript">
            function init() {
                document.getElementById("mode").onclick = function() {
                    var passwd = document.getElementById("password");
                    if (passwd.getAttribute("type") == "password") {
                        passwd.setAttribute("type", "text");
                    }
                    else {
                        passwd.setAttribute("type", "password");
                    }
                };
            }
            </script>
        </head>
        <body onload="init()">
            <form action="/regemail3" method="post">
                <span>Please enter the password:</span>
                <input type="hidden" name="token" value="__TOKEN__" />
                <br/>
                <input id="password" type="password" size="20" name="password" style="border: 1px solid black" />
                <br/>
                <input id="mode" type="checkbox" /><label for="mode">Show password</label>
                <br/>
                <input type="submit" />
            </form>
        </body>
        </html>
        """.replace("__TOKEN__", req.values["token"])
        return [page]


    def __addEmailAuth3(self, req):
        if not req.values.has_key("token") or not req.values.has_key("password"):
            return ["Access denied"]
        mac = hmac.new(secret.AuthSecret, None, hashlib.sha1)
        mac.update(req.values["password"].encode('utf8'))
        password = mac.digest().encode('base64').strip()
        try:
            token = self.mc.get("tmptoken_" + str(req.values["token"]))
        except:
            logging.error("__addEmailAuth3 failure", exc_info=1)
            return ["Internal server error"]

        if token is None:
            return ["Token does not exist or has expired"]

        token = token.split()
        self.mc.delete("tmptoken_" + str(req.values["token"]))
        if len(token) == 0:
            return ["Token empty"]
        elif len(token) == 1:
            email = token[0]
            session = Session[0]()
            u = User[0]()
            session.add(u)
            session.flush()
            uid = u.uid
            session.commit()
            session.close()
        else:
            email, uid = token[0], token[1]
            try:
                uid = int(uid)
            except:
                logging.error("__addEmailAuth3 failure", exc_info=1)
                return ["Invalid UID"]
        
        session = Session[0]()
        try:
            if session.query(MethodEmail[0]).filter_by(email=email).count() == 0:
                session.add(MethodEmail[0](uid, email, password))
                session.commit()
                session.close()
                return ["Email authentication added"]
            else:
                session.query(MethodEmail[0]).filter_by(email=email, uid=uid).one().password = password
                session.commit()
                session.close()
                return ["Email password changed"]
        except:
            logging.error("__addEmailAuth3 failure", exc_info=1)
            session.close()
            return ["Internal server error"]


    def __removeEmailAuth(self):
        if not req.values.has_key("email"):
            return ["You must provide an email address"]
        email = req.values["email"]
        if not isValidAddress(email):
            return ["Invalid email address"]
        
        uid = self.__uid(req)
        if uid == None:
            return ["Permission denied"]
        try:
            uid = int(uid)
        except:
            logging.error("__removeEmailAuth failure", exc_info=1)
            return ["Invalid UID"]
        session = Session[0]()
        query = session.query(MethodEmail[0]).filter_by(email=email,uid=uid)
        token = str(uuid4())
        if uid == None and query.count() == 0:
            # New user
            self.mc.set("tmptoken_" + token, "%s" % (email), 3600)
        elif query.count() == 1 and query.one().uid == uid and uid != None:
            # Setting a new password
            self.mc.set("tmptoken_" + token, "%s %s" % (email, uid), 3600)
        elif query.count() == 0 and uid != None:
            # Adding a new email
            self.mc.set("tmptoken_" + token, "%s %s" % (email, uid), 3600)
        else:
            return ["Permission denied"]


    def __authenticateByEmail(self, req):
        email, password = req.values["email"], req.values["password"].encode('utf8')
        session = Session[0]()
        mac = hmac.new(secret.AuthSecret, None, hashlib.sha1)
        mac.update(password)
        password = mac.digest().encode('base64').strip()
        query = session.query(MethodEmail[0]).filter_by(email=email, password=password)
        if query.count() != 1:
            session.close()
            return ""
        else:
            user = query.one()
            uid = str(user.uid)
            session.close()
            mac = hmac.new(secret.AuthSecret, None, hashlib.sha1)
            mac.update(uid)
            return quote("%s %s" % (mac.digest().encode('base64').strip(), uid))


    def __uid(self, req):
        try:
            if not req.values.has_key("uid"):
                return None
            res = req.args['uid'].split()
            if len(res) != 2:
                return None
            digest, uid = res
            mac = hmac.new(secret.AuthSecret, None, hashlib.sha1)
            mac.update(uid)
            if mac.digest().encode('base64').strip() == digest:
                return uid
            else:
                return None
        except:
            logging.error("__uid failure", exc_info=1)
            logging.error("The UID in question is: " + req.args['uid'])
            return None


    def __call__(self, env, start_response):
        req = Request(env)
        Config = ConfigParser()
        Config.read(configfile)
        params = {"host": "", "user": "", "database": "", "port": ""}
        for param in params:
            if not Config.has_option("MySQL", param):
                print "Malformed configuration file: mission option %s in section MySQL" % (param)
                sys.exit(1)
            params[param] = Config.get("MySQL", param)    
        engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
            (params["user"], secret.MySQL, params["host"], params["port"], params["database"]), pool_recycle=3600)
        Base = declarative_base(bind=engine)
        local.Session = []
        local.User = []
        local.MethodEmail = []
        local.Session.append(sessionmaker(bind=engine))
        local.User.append(makeUser(Base))
        local.MethodEmail.append(makeMethodEmail(Base))
        resp = Response(status=200)
        if req.path == '/register':
            resp.content_type = "text/html"
            resp.response = self.__register(req)
            return resp(env, start_response)
        elif req.path == '/regemail1':
            resp.content_type = "text/plain"
            resp.response = self.__addEmailAuth1(req)
            return resp(env, start_response)
        elif req.path == '/regemail2':
            resp.content_type = "text/html"
            resp.response = self.__addEmailAuth2(req)
            return resp(env, start_response)
        elif req.path == '/regemail3':
            resp.content_type = "text/plain"
            resp.response = self.__addEmailAuth3(req)
            return resp(env, start_response)
        elif req.path == '/auth' and req.values.has_key("email") and req.values.has_key("password"):
            resp.content_type = "text/plain"
            resp.response = [self.__authenticateByEmail(req)]
            return resp(env, start_response)
        elif req.path == '/auth' and req.values.has_key("uid"):
            resp.content_type = "text/plain"
            uid = self.__uid(req)
            if uid == None:
                uid = ""
            resp.response = [uid]
            return resp(env, start_response)
        else:
            resp.status_code = 404
            resp.response = [""]
            return resp(env, start_response)


def main():
    global configfile
    configfile, port, log = default.config, default.port, default.log

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

    for section in ["Global", "MySQL"]:
        if not Config.has_section(section):
            print "Malformed configuration file"
            sys.exit()

    if Config.has_option('Global', 'port'):
        port = Config.get('Global', 'port')
    if Config.has_option('Global', 'log'):
        log = Config.get('Global', 'log')

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

    params = {"host": "", "user": "", "database": "", "port": ""}
    for param in params:
        if not Config.has_option("MySQL", param):
            print "Malformed configuration file: mission option %s in section MySQL" % (param)
            sys.exit(1)
        params[param] = Config.get("MySQL", param)
 
    try:
        engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
            (params["user"], secret.MySQL, params["host"], params["port"], params["database"]), pool_recycle=3600)
        Base = declarative_base(bind=engine)
        Session.append(sessionmaker(bind=engine))
        User.append(makeUser(Base))
        MethodEmail.append(makeMethodEmail(Base))
        Base.metadata.create_all(engine)
    except:
        print "Failed to establish connection to the database"
        print "Check the log file for details"
        logging.error("DB connection failure", exc_info=1)
        sys.exit(1)
    
    params = {"host": "", "port": ""}
    for param in params:
        if not Config.has_option("MemCache", param):
            print "Malformed configuration file: mission option %s in section self.mc" % param
            sys.exit(1)
        params[param] = Config.get("MemCache", param)
    
    try:
        #self.mc = memcache.Client(["%s:%s" % (params["host"], params["port"])], debug=0)
        mc = Memcache([((params["host"], int(params["port"])), 100)])
    except:
        print "Failed to establish connection to the memcache daemon"
        print "Check the log file for details"
        logging.error("self.mc daemon connection failure", exc_info=1)
        sys.exit(1)

    warden = Warden()
    warden.mc = mc
    server = WSGIServer(("0.0.0.0", int(port)), warden)
    try:
        logging.info("Server running on port %s. Ctrl+C to quit" % port)
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        logging.info("Server stopped")


if __name__ == "__main__":
    main()
