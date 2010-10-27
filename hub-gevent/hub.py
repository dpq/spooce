#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging, hmac, hashlib, uuid, random, new
import memcache, cookielib, sys, getopt,re
from ConfigParser import ConfigParser

import urllib2
from urllib import quote_plus as quote
from simplejson import dumps as tojson, loads as fromjson
from datetime import datetime, timedelta

from gevent import monkey; monkey.patch_socket()
from gevent.wsgi import WSGIServer
from gevent.coros import RLock

from werkzeug import Request, Response
from werkzeug.contrib.securecookie import SecureCookie

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Boolean, DateTime, Text, Integer
from sqlalchemy import Table, Column, MetaData, Index, desc, create_engine

import secret, default

Session, Terminal, Subscription = {}, {}, {}

locks = {}

def __Terminal_init__(self, tid, key = ""):
    self.tid = tid
    if key != "":
        domain = self.__class__.__name__.replace("terminal_", "")
        mac = hmac.new(secret.NameSecret[domain], None, hashlib.md5)
        mac.update(key)
        self.key = mac.digest().encode('base64').strip()
    else:
        self.key = ""
    self.last_seen = datetime.now()


def __Terminal_repr__(self):
    return "<Terminal('%s', '%s')>"%(self.tid, str(self.last_seen))


def __Subscription_init__(self, id_sub, id_pub, filter):
    self.subscriber = id_sub
    self.publisher = id_pub
    self.filter = filter


def __Subscription_repr__(self):
    return "<Subscription('%s'=>'%s' -- %s)>" % (self.publisher, self.subscriber, self.filter)


class Hub(object):
    def __init__(self):
        self.mc = {}
        self.hubid = ""
        self.repos = []
        self.wardens = []


    def __domain(self, req):
        return req.host.split(":")[0].replace('.', '_')


    def __tid(self, req):
        try:
            domain = self.__domain(req)
            if not req.args.has_key('tid'):
                return None
            res = req.args['tid'].split()
            if len(res) != 2:
                return None
            digest, tid = res
            mac = hmac.new(secret.SessionSecret[domain], None, hashlib.sha1)
            mac.update(tid)
            if mac.digest().encode('base64').strip() == digest:
                return tid
            else:
                return None
        except:
            logging.error("__tid failure", exc_info=1)
            logging.error("The TID in question is: " + req.args['tid'])
            return None


    def __connect(self, req):
        try:
            domain = self.__domain(req)
            session = Session[domain]()
            if req.args.has_key('tid') and req.args.has_key('key'):
                if not re.compile("^[0-9a-z]+$").match(req.args['tid']):
                    session.close()
                    return [tojson({'status': 3, 'errmsg': 'Invalid TID supplied.'})]
                tid, key = req.args['tid'], req.args['key']
                mac = hmac.new(secret.NameSecret[domain], None, hashlib.md5)
                mac.update(key)
                if session.query(Terminal[domain]).filter_by(tid=tid).count() == 0:
                    session.add(Terminal[domain](tid, key))
                    session.commit()
                    session.close()
                elif session.query(Terminal[domain]).filter_by(tid=tid).one().key != mac.digest().encode('base64').strip():
                    session.close()
                    return [tojson({'status': 2, 'errmsg': 'Authentication error.'})]
            else:
                while True:
                    tid = uuid.uuid4().hex
                    print "TID generated: %s" % tid.encode('utf8')
                    if session.query(Terminal[domain]).filter_by(tid=tid).count() == 0:
                        session.add(Terminal[domain](tid))
                        session.commit()
                        session.close()
                        break
            print 'Continuing terminal initialization: %s' % tid.encode('utf8')
            self.mc.set("%s_inbox" % tid.encode('utf8'), "[]")
            self.mc.set("%s_last_seen" % tid.encode('utf8'), str(datetime.now()))
            locks[tid.encode('utf8')] = RLock()
            mac = hmac.new(secret.SessionSecret[domain], None, hashlib.sha1)
            mac.update(tid)
            self.__push(domain, {"event": "connect", "tid": "/%s" % tid, "src": "/%s" % self.hubid})
            return [tojson({'status': 0,
                'tid': quote("%s %s" % (mac.digest().encode('base64').strip(), tid)),
                'hubid': '/%s' % self.hubid,
                'repo': self.repos[random.randrange(len(self.repos))],
                'warden': self.wardens[random.randrange(len(self.wardens))],
                'calibration': {'interval': 2000}})]
        except:
            logging.error("__connect failure", exc_info=1)
            return [tojson({'status': 1, 'errmsg': 'An error has occured. Please contact tech support.'})]


    def __disconnect(self, req):
        try:
            domain = self.__domain(req)
            session = Session[domain]()
            tid = self.__tid(req)
            if not tid:
                return [tojson({'status': 2, 'errmsg': 'Authentication error.'})]
            locks[tid.encode('utf8')].acquire()
            self.mc.delete("%s_inbox" % tid.encode('utf8'))
            self.mc.delete("%s_last_seen" % tid.encode('utf8'))
            locks[tid.encode('utf8')].release()
            del locks[tid.encode('utf8')]
            if session.query(Terminal[domain]).filter_by(tid=tid).one().key == "" or (req.args.has_key("release") and req.args["release"] == 1):
                session.delete(session.query(Terminal[domain]).filter_by(tid=tid).one())
            session.commit()
            session.close()
            self.__push(domain, {"event": "disconnect", "tid": "/%s" % tid, "src": "/%s" % self.hubid})
            return [tojson({'status': 0})]
        except:
            logging.error("__disconnect failure", exc_info=1)
            return [tojson({'status': 1, 'errmsg': 'An error has occured. Please contact tech support.'})]


    def __mx(self, req):
        try:
            domain = self.__domain(req)
            session = Session[domain]()
            tid = self.__tid(req)
            if not tid or session.query(Terminal[domain]).filter_by(tid=tid).count() != 1:
                return [tojson({'status': 2, 'errmsg': 'Authentication error.'})]
            terminal = session.query(Terminal[domain]).filter_by(tid=tid).one()
            terminal.last_seen = datetime.now()
            session.commit()
            session.close()
            locks[tid.encode('utf8')].acquire()
            self.mc.set("%s_last_seen" % tid.encode('utf8'), str(datetime.now()))
            locks[tid.encode('utf8')].release()
            incoming, outgoing = [], []
            if req.values.has_key('messages'):
                try:
                    incoming = fromjson(req.values['messages'])
                    if type(incoming) != list:
                        logging.error("mx: incoming messages object not a list")
                        logging.info(req.values['messages'])
                        incoming = []
                except:
                    logging.error("mx: could not parse incoming messages", exc_info=1)
            else:
                logging.error("mx: no incoming messages object. This is a spec violation.")
            for msg in incoming:
                if not msg.has_key("src"):
                    logging.error("mx: message doesn't have a source field.")
                    logging.info(tojson(msg))
                    continue
                if msg.has_key("uid"):
                    uid = urllib2.urlopen(self.wardens[random.randrange(len(self.wardens))] + "auth", urlencode({"uid": uid})).read()
                    if uid == "":
                        del msg["uid"]
                    else:
                        msg["uid"] = uid
                if msg.has_key("dst") and msg["dst"] == "/%s" % self.hubid:
                    response = {"src": "/%s" % self.hubid, "dst": msg["src"]}
                    filter = ""
                    if msg.has_key("filter"):
                        filter = tojson(msg["filter"])
                    if msg.has_key("msgid"):
                        response.update({"msgid": msg["msgid"]})
                    if msg["action"] == "subscribe":
                        response.update({"status": self.__subscribe(domain, msg["sub"], msg["pub"], filter)})
                    elif msg["action"] == "unsubscribe":
                        response.update({"status": self.__unsubscribe(domain, msg["sub"], msg["pub"], filter)})
                    response.update({"sub": msg["sub"]})
                    response.update({"pub": msg["pub"]})
                    response.update({"action": msg["action"]})
                    outgoing.append(response)
                elif msg.has_key("dst"):
                    print "sending", tojson(msg)
                    try:
                        self.__push(domain, msg, msg["dst"].split("/")[1])
                    except:
                        logging.error("mx: could not push; malformed destination address?", exc_info=1)
                else:
                    print "broadcasting", tojson(msg)
                    self.__push(domain, msg)
            outgoing += self.__pull(tid)
            print "pulling", tojson(outgoing)
            return [tojson(outgoing)]
        except:
            print "LOCKS", locks.keys()
            logging.error("__mx failure", exc_info=1)
            return ['[]']


    def __push(self, domain, message, tid=None):
        if tid:
            locks[tid.encode('utf8')].acquire()
            try:
                messages = self.mc.get("%s_inbox" % tid.encode('utf8'))
            except:
                logging.error("__push memcached failure", exc_info=1)
            if messages:
                messages = fromjson(messages)
                messages.append(message)
                self.mc.set("%s_inbox" % tid.encode('utf8'), tojson(messages))
                print "Pushed to", "%s_inbox" % tid.encode('utf8')
            else:
                logging.error("Malformed inbox, not pushing (%s_inbox)" % tid.encode('utf8'))
                logging.info("Inbox is %s " % str(messages))
            locks[tid.encode('utf8')].release()
        else:
            session = Session[domain]()
            dstlist, filterlist = [], []
            for dst, filter in session.query(Subscription[domain].subscriber, Subscription[domain].filter).filter_by(publisher=message["src"]).all():
                dstlist.append(dst)
                filterlist.append(filter)
            session.close()
            for i in range(0, len(dstlist)):
                dst = dstlist[i]
                filter = filterlist[i]
                if filter != "":
                    match = True
                    filter = fromjson(filter)
                    for f in filter:
                        if filter.has_key(f) and message[f] != filter[f]:
                            match = False
                            break
                    if not match:
                        continue
                    message.update({"dst": dst})
                    tid = message["dst"].split("/")[1]
                    self.__push(domain, message, tid)


    def __pull(self, tid):
        res = []
        messages = None
        locks[tid.encode('utf8')].acquire()
        try:
            messages = self.mc.get("%s_inbox" % tid.encode('utf8'))
        except:
            logging.error("__pull failure", exc_info=1)
        if messages:
            self.mc.set("%s_inbox" % tid.encode('utf8'), "[]")
            res = fromjson(messages)
        else:
            res = []
            logging.error("Malformed inbox, not pulling (%s_inbox)" % tid.encode('utf8'))
        locks[tid.encode('utf8')].release()
        return res


    def __subscribe(self, domain, sub, pub, filter=""):
        session = Session[domain]()
        try:
            if session.query(Subscription[domain]).filter_by(subscriber=sub, publisher=pub, filter=filter).count() > 0:
                session.close()
                return
            session.add(Subscription[domain](sub, pub, filter))
            session.commit()
            session.close()
            return 0
        except:
            logging.error("__subscribe failure", exc_info=1)
            session.close()
            return 1


    def __unsubscribe(self, domain, sub, pub, filter):
        session = Session[domain]()
        try:
            if filter == "":
                if session.query(Subscription[domain]).filter_by(subscriber=sub, publisher=pub).count() == 0:
                    session.close()
                    return
                session.delete(session.query(Subscription[domain]).filter_by(subscriber=sub, publisher=pub))
            else:
                if session.query(Subscription[domain]).filter_by(subscriber=sub, publisher=pub, filter=filter).count() == 0:
                    session.close()
                    return
                session.delete(session.query(Subscription[domain]).filter_by(subscriber=sub, publisher=pub, filter=filter).one())
            session.commit()
            session.close()
            return 0
        except:
            logging.error("__unsubscribe failure", exc_info=1)
            session.close()
            return 1


    def __call__(self, env, start_response):
        req = Request(env)
        resp = Response(status=200, content_type="text/plain")
        if req.path == '/connect':
            resp.response = self.__connect(req)
            return resp(env, start_response)
        elif req.path == '/disconnect':
            resp.response = self.__disconnect(req)
            return resp(env, start_response)
        elif req.path == '/mx':
            resp.response = self.__mx(req)
            return resp(env, start_response)
        elif req.path == '/fx':
            resp.response = self.__fx(req)
            return resp(env, start_response)
        else:
            resp.status_code = 404
            resp.response = [""]
            return resp(env, start_response)


def main():
    global Session, Terminal, Subscription
    configfile, port, log = default.config, default.port, default.log
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

    for section in ["Global", "MemCache"]:
        if not Config.has_section(section):
            print "Malformed configuration file: missing section %s" % section
            sys.exit(1)

    if Config.has_option('Global', 'port'):
        port = Config.get('Global', 'port')
    if Config.has_option('Global', 'log'):
        log = Config.get('Global', 'log')

    if not Config.has_option('Global', 'repos') or Config.get('Global', 'repos') == "":
        print "No repositories specified; the system is not functional"
        sys.exit(1)

    if not Config.has_option('Global', 'wardens') or Config.get('Global', 'wardens') == "":
        print "No wardens specified; the system is not functional"
        sys.exit(1)

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

    for domain in secret.MySQL.keys():
        if not Config.has_section(domain):
            print "Malformed configuration file: missing section %s" % domain
            sys.exit(1)
        
        params = {"host": "", "user": "", "database": "", "port": ""}
        for param in params:
            if not Config.has_option(domain, param):
                print "Malformed configuration file: mission option %s in section %s" % (param, domain)
                sys.exit(1)
            params[param] = Config.get(domain, param)
 
        try:
            engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
                (params["user"], secret.MySQL[domain], params["host"], params["port"], params["database"]), pool_recycle=3600)
            Base[domain] = declarative_base(bind=engine)
            Session[domain] = sessionmaker(bind=engine)
        
            Terminal[domain] = new.classobj("terminal_%s" % domain, (Base[domain], ), {
                "__tablename__": 'terminal',
                "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
                "__init__": __Terminal_init__,
                "__repr__": __Terminal_repr__,
                "tid": Column(String(32), primary_key=True, autoincrement=False),
                "last_seen": Column(DateTime),
                "key": Column(String(24))
            })
        
            Subscription[domain] = new.classobj("subscription_%s" % domain, (Base[domain], ), {
                "__tablename__": 'subscription',
                "__table_args__":  {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
                "__init__": __Subscription_init__,
                "__repr__": __Subscription_repr__,
                "id": Column(Integer, primary_key=True),
                "subscriber": Column(String(128)),
                "publisher": Column(String(128)),
                "filter": Column(String(1024))
            })


            Index("index_subscription_%s" % domain, Subscription[domain].publisher)

            Base[domain].metadata.create_all(engine)
        except:
            print "Failed to establish connection to the database for domain %s " % domain
            print "Check the log file for details"
            logging.error("DB connection failure", exc_info=1)
            sys.exit(1)

    params = {"host": "", "port": ""}
    for param in params:
        if not Config.has_option("MemCache", param):
            print "Malformed configuration file: mission option %s in section MemCache" % param
            sys.exit(1)
        params[param] = Config.get("MemCache", param)
    
    try:
        MemCache = memcache.Client(["%s:%s" % (params["host"], params["port"])], debug=0)
    except:
        print "Failed to establish connection to the memcache daemon"
        print "Check the log file for details"
        logging.error("MemCache daemon connection failure", exc_info=1)
        sys.exit(1)
            
    logging.info("Generating a random hub ID.")
    HubID = uuid.uuid4().hex

    hub = Hub()

    repos = Config.get('Global', 'repos').split(",")
    for repo in repos:
        if len(repo) > 0:
            hub.repos.append(repo)

    if len(hub.repos) == 0:
        print "No repositories specified; the system is not functional"
        sys.exit(1)

    wardens = Config.get('Global', 'wardens').split(",")
    for warden in wardens:
        if len(repo) > 0:
            hub.wardens.append(warden)

    if len(hub.wardens) == 0:
        print "No repositories specified; the system is not functional"
        sys.exit(1)


    hub.mc = MemCache
    hub.mc.set("%s_inbox" % HubID.encode('utf8'), "[]")
    hub.mc.set("%s_last_seen" % HubID.encode('utf8'), str(datetime.now()))
    hub.hubid = HubID
    locks[HubID.encode('utf8')] = RLock()
    print "HUBID", HubID.encode('utf8')

    for domain in secret.MySQL.keys():
        session = Session[domain]()
        session.add(Terminal[domain](hub.hubid))
        session.commit()
        session.close()

    server = WSGIServer(("0.0.0.0", int(port)), hub)
    try:
        logging.info("Server running on port %s. Ctrl+C to quit" % port)
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        logging.info("Server stopped")


if __name__ == "__main__":
    main()
