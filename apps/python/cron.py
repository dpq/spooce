#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import time

# The actual Event class
class Event(object):
    def __init__(self, src, dst, flag, rule):
        rule = rule.split()
        crit = {}
        crit["mi"] = rule[0]
        crit["hr"] = rule[1]
        crit["dy"] = rule[2]
        crit["mn"] = rule[3]
        crit["dw"] = rule[4]
        self.criteria = {}
        for c in ["mi", "hr", "dy", "mn", "dw"]:
            self.criteria[c] = crit[c]
        print self.criteria
        # Set other info
        self.dst = dst
        self.src = src
        self.flag = flag
        self.rule = rule

    def matchone(self, t, field):
        print field, t, self.criteria[field]
        if self.criteria[field] == "*":
            return True
        elif self.criteria[field].startswith("/"):
            div = int(self.criteria[field][1:])
            if int(t)%div == 0:
                return True
            else:
                return False
        else:
            if int(t) == int(self.criteria[field]):
                return True
            else:
                return False
    
    def match(self, t):
        print t
        # Days are cumulative
        days = self.matchone(t.day, "dy") or self.matchone(t.weekday() + 1, "dw")
        print self.matchone(t.day, "dy")
        print self.matchone(t.weekday(), "dw")
        print days
        print self.matchone(t.minute, "mi")
        print self.matchone(t.hour, "hr")
        print self.matchone(t.month, "mn")
        return days and self.matchone(t.minute, "mi") and self.matchone(t.hour, "hr") and self.matchone(t.month, "mn")

    def check(self, t):
        if self.match(t):
            kernel.sendMessage({"src": self.src, "dst": self.dst, "flag": self.flag})



class Cron(object):
    def __init__(self):
        self.events = []
        self.id = ""

    def mx(self, message):
        if message.has_key("rule") and message.has_key("flag") and message.has_key("action"):
            if message["action"] == "add":
                self.addcron(message["src"], message["rule"], message["flag"])
            elif message["action"] == "remove":
                self.removecron(message["src"], message["rule"], message["flag"])

    def addcron(self, client, rule, flag):
        for e in self.events:
            if e.flag == flag and e.rule == rule and e.dst == client:
                print "%s %s %s exists" % (flag, rule, client)
                return
        self.events.append(Event(self.id, client, flag, rule))
        print "%s %s %s added" % (flag, rule, client)

    def removecron(self, client, rule, flag):
        for i in range(0, len(self.events)):
            e = self.events[i]
            if e.flag == flag and e.rule == rule and e.dst == client:
                del self.events[i]
                return
    

    def main(self, appid = "cron", args = None):
        self.id = appid
        while 1:
            print "Checking events!!!"
            for e in self.events:
                e.check(t)
            t = datetime(*datetime.now().timetuple()[:5])
            t += timedelta(minutes=1)
            while datetime.now() < t:
                sleeptime = (t - datetime.now()).seconds
                if sleeptime == 0:
                    sleeptime = 1
                print "sleeping for", sleeptime
                time.sleep(sleeptime)

opt.package["cron"]["1"] = Cron