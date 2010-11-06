#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging, hmac, hashlib, new, getopt, sys
from ConfigParser import ConfigParser

from datetime import datetime, timedelta

import memcache

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Boolean, DateTime, Text, Integer
from sqlalchemy import Table, Column, MetaData, Index, desc, create_engine

import secret, default

# Add the following to the crontab
# m h  dom mon dow   command
# * * * * *  cd YOUR_WORKING_DIRECTORY; ./vacuum.py

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




def main():
    SessionMaker, Terminal, Subscription = {}, {}, {}
    configfile, ttl, log = default.config, int(default.ttl), default.vacuumlog
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

    if Config.has_option('Global', 'ttl'):
        ttl = int(Config.get('Global', 'ttl'))
    else:
        print "Time to live not specified in the config file, aborting."
        sys.exit(1)
    
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

    params = {"host": "", "port": ""}
    for param in params:
        if not Config.has_option("MemCache", param):
            print "Malformed configuration file: mission option %s in section MemCache" % param
            sys.exit(1)
        params[param] = Config.get("MemCache", param)

    try:
        mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    except:
        print "Failed to establish connection to the memcache daemon"
        print "Check the log file for details"
        logging.error("MemCache daemon connection failure", exc_info=1)
        sys.exit(1)

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
            SessionMaker[domain] = sessionmaker(bind=engine)
        
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
            session = SessionMaker[domain]()
            tids = {}
            for t in session.query(Terminal[domain]).filter(Terminal[domain].last_seen < datetime.now() - timedelta(seconds=ttl)).all():
                mc.delete("%s_inbox" % t.tid)
                mc.delete("%s_last_seen" % t.tid)
                tids[t.tid] = t.key
            
            for tid in tids.keys():
                session.query(Subscription[domain]).filter(Subscription[domain].subscriber.op('regexp')('^/%s' % tid)).delete('fetch')
                if tids[tid] == "":
                    session.query(Terminal[domain]).filter_by(tid=tid).delete('fetch')
            session.commit()
            session.close()
        except:
            print "Failed to establish connection to the database for domain %s " % domain
            print "Check the log file for details"
            logging.error("DB connection failure", exc_info=1)
            session.close()
            sys.exit(1)


if __name__ == "__main__":
    main()
