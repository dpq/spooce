#!/usr/bin/python

from threading import Thread, currentThread, RLock, Timer
from urllib2 import urlopen
from urllib import urlencode#, quote_plus, unquote
import simplejson as json
from copy import deepcopy
from string import rjust
from sys import stdout
import logging as log
import sys, imp
from time import sleep

class DictOfDicts(dict):
    def __missing__(self, key):
        return {}


class DictWithMissing(dict):
    OK = 0
    EMPTY_DST = 1
    BAD_DST = 2
    NO_SUCH_DST = 3
    MX_APP_ERROR = 5
    CALLBACK_MX_APP_ERROR = 6
    status = {
        0 : "Ok",
        1 : "No dst. Broadcasting must not be supported. Use hub's help instead.",
        2 : "Bad dst : %s",
        3 : "No such abonet : %s",
        5 : "Cannot call mx() of process %s, but process itself exists.", # abonent ne otvechaet ili vremenno nedostupen
        6 : "Cannot call 'callback' for the process %s"
    }
    def __missing__(self, key):
        return None

    def setStatus(self, stat):
        self["status"] = stat
        self["errmsg"] = self.status[stat]

    def dstApp(self, tid):
        try:
            return self["dst"].split("/" + tid + "/")[1]
        except:
            return None

    def goodDst(self, tid):
        try:
            return self["dst"] == "/" + tid + "/" + self.dstApp(tid)
        except:
            return False


Message = DictWithMissing


class Opt:
    def __init__(self):
        self.package = DictOfDicts()

    def install(self, meta, callback = None):
        result = True
        if not self.package.has_key(meta[0]):
            self.package[meta[0]] = {}
        if not self.package[meta[0]].has_key(meta[1]):
            src = kernel.getSource(meta)
            if src != None:
                try:
#                if 1:
                    module = imp.new_module(meta[0])
                    module.__dict__["kernel"] = kernel
                    module.__dict__["opt"] = opt
                    exec src in module.__dict__
                    sys.modules[meta[0]] = module
                except Exception as error:
                    log.error("Cannot build %s. Check the source code below\n%s" % (str(meta), src))
                    log.error(str(error))
                    result = False
            else:
                result = False
        else:
            log.info("%s has already been installed." % str(meta))
        try:
            callback()
        except:
            pass
        return result
            

opt = Opt()
from datetime import datetime


class Kernel:
    def __init__(self):
        pass

    def init(self, hubLocation, login, passwd, localrepository):
        self.dtstart = datetime.now()
        #logfile = datetime.now().strftime("logs/%Y%m%d%H%M.spooce.kernel.log")
        #log.basicConfig(filename = logfile, level = log.DEBUG)
        log.basicConfig(stream = stdout, level = log.DEBUG)
        log.info("Starting terminal...")
        self.localrepo = localrepository
        #self.apps = Apps("T3rm1nalS3(r3+", self.saveMsg)
        self.standalone = not self.connect(hubLocation, login, passwd)
        opt.instance = {"00000kernel1" : self}
        self.process = {0 : currentThread()}
        opt.pidlen = 5
        opt.pid = {rjust("0", opt.pidlen, "0") + "kernel1" : 0}
        if self.standalone:
            log.error("Terminal (id=%s): Cannot communicate with the hub. Standalone mode is ON" % self.__ID)
        log.info("Terminal is preparing for getting messages from applications...")
        self.__stopFlag = 0
        self.__messageQueue = []
        self.__mqlock = RLock()
        self.callbacks = {}
        self.mxdaemon()

    def connect(self, hubURL, id, key):
        """Connect to the hub, register my brennaia tushka and get repo and
        nameserver's urls."""
        # TODO: id, key are not set. What else?
        self.__ID = id
        self.__KEY = key
        self.__url = hubURL
        request = self.__url + "connect?tid=%s&key=%s" % (self.__ID, self.__KEY)
        result = {}
        self.messageCheckingTimer = 0.2
        try:
            r = urlopen(request)
            content = r.read()
            r.close()
            result = eval(content.replace(": null", ": None"))
            # TODO: use simplejson to decode
        except:
            log.error("Cannot connect to hub." + "GET " + request)
            return False
        log.info("Connecting result =")
        for r in result:
            log.info("\t" + str(r) + " : " + str(result[r]))
        if result["status"] != 0:
            log.error("Bad result status. Type='%s', Value='%s'" %
                ( str(type(result["status"])), str(result["status"]))
            )
            return False
        self.__hubID = result["hubid"]
        self.__KEY, self.__ID = result['tid'].split("+", 1)
        self.__repo = result["repo"].lstrip("/")
        self.__warden = result["warden"].lstrip("/")
        try:
            self.messageCheckingTimer = result["calibration"]["interval"] * 0.001
            log.info("Timer is set for %i miliseconds" % result["calibration"]["interval"])
        except:
            log.warning("Calibration error. Skipped")
        log.info("Terminal kernel (id=%s) started.\nHub id = %s, \nReady for a job." % (self.__ID, self.__hubID))
        self.connected = True
        return True
        # TODO: add warden

    def disconnect(self):
        if not self.connected:
            log.error("Already disconnected.")
            return
        self.connected = False
        self.__stopFlag = 1 # stop mxdaemon
        if self.standalone:
            log.info("Terminal (id=%s) has been stopped." % self.__ID)
            return
        request = self.__url + "disconnect?tid=" + self.__ID
        try:
            r = urlopen(request)
            content = r.read()
            r.close()
            # spooce.py, 321 TODO: delete self.apps.instance[blueprintId][meta]
        except:
            log.error("GET " + request)
            log.error("Unknown error occured while disconnecting.")
        log.info("Terminal (id=%s) has been stopped." % self.__ID)

    def run(self, meta, Args):
        print "Running...", meta
        if not opt.install(meta[:2]):
            return False
        print "opt.package", opt.package
        Args["appcode"] = meta[0]
        Args["versioncode"] = meta[1]
        pid = max(self.process.keys()) + 1
        if len(meta) > 2:
            appid = meta[2]
        else:
            appid = rjust(str(pid), opt.pidlen, "0") + Args["appcode"] + Args["versioncode"]
        Args["appid"] = appid
        opt.pid[appid] = pid
        opt.instance[appid] = opt.package[meta[0]][meta[1]]()
        t = Thread(target = opt.instance[appid].main, name = str(meta) + str(Args), args = (appid, Args, ))
        t.start()
        self.process = {pid : t}
        self.sendMessage({"event": "run", "appid": "/" + self.__ID + "/" + appid})
        return True

    def kill(self, meta):
        return

    def sendMessage(self, newMessage, callback = None): # from apps
        newMessage["src"] = self.correctMessageSrc(Message(newMessage))
        self.__mqlock.acquire()
        self.__messageQueue.append(newMessage)
        self.__mqlock.release()
        try:
            self.callbacks[newMessage["msgid"]] = callback
        except:
            pass

    def correctMessageSrc(self, message):
        return "/" + self.__ID + "/" + message["src"].strip("/").split("/", 1)[-1]
        """src = "/" + self.__ID
        if message["src"] == None or message["src"] == '/' or message["src"] == src:
            return src
        stripsrc = message["src"].strip("/").split("/", 1)
        if len(stripsrc) > 2:
            logging.error("bad src : " + message["src"])
            return src
        if stripsrc[0] != self.__ID:
            src += "/" + stripsrc[0] # + "/" + stripsrc[1]
        elif len(stripsrc) == 2:
            src += "/" + stripsrc[1]
        return src"""

    def correctMessageDst(message):
        return

    def mxdaemon(self): # spooce.py, 425 TODO: Upload and download is economy well enough? Any optimization?
        """ The queue of outgoing messages. The whole queue is uploaded to the server
         by the mx() call, which also retrieves the server response."""
        print "====TIME (minutes)====", (datetime.now() - self.dtstart).seconds/60.0
        log.info("Mxdaemon woke up")
        if self.__stopFlag:
            log.info("Mxdaemon quits.")
            return
        self.__mqlock.acquire()
        mq = self.__messageQueue # POST THIS
        self.__messageQueue = [] # make messageQueue empty
        self.__mqlock.release()

        if len(mq) > 1:
            log.info("%i messages in queue:" % len(mq))
        elif len(mq) == 1:
            log.info("%i message in queue:" % len(mq))
        for m in mq:
            print "Message :\n", printMsg(m)
        request = []
        localmsg = []
        while len(mq) > 0:
            m = Message(mq.pop())
#            if m["dst"] != None and m["dst"].strip("/").startswith(self.__ID):
#                localmsg.append(m)
#            else:
            request.append(m)
        for m in request:
            print "Message for hub :\n", printMsg(m)

        if not self.standalone:
            response = self.mx(request[:]) # add ttl and delete unnecessary messages
            while len(response) > 0:
                message = response.pop()
                try:
                    localmsg.append(Message(message))
                except:
                    log.error("Bad Message %s.\nNot an instance of the dict?" % str(message))

        # Sending messages to local applications
        rejected, rereq = [], []
        while len(localmsg) > 0:
            message = Message(localmsg.pop())
            debugcopy = deepcopy(message)
            if message.has_key("msgid") and self.callbacks.has_key(message["msgid"]):
                msgid = message.pop("msgid")
                try:
                    self.callbacks[msgid](message)
                except:
                    log.error("Message (%s) not send to callback. Skipped. Original:\n%s\n" % (str(msgid), str(debugcopy)))
                    message.setStatus(message.CALLBACK_MX_APP_ERROR)
            else:
#                if where == None:
#                    where = opt.package.keys()
#                else:
                if message.goodDst(self.__ID):
                    where = [message.dstApp(self.__ID)]
                    for dst in where:
                        skp = []
                        if not opt.instance.has_key(dst):
                            message.setStatus(message.NO_SUCH_DST)
                        else:
                            try:
#                            if 1:
                                opt.instance[dst].mx(message)
                            except:
                                skp = dst
                                log.error("Message not send to mx. Skipped. Original:\n%s\n" % str(debugcopy))
                                message.setStatus(message.MX_APP_ERROR)
                else:
                    message.setStatus(message.BAD_DST)
#            if message["status"] != 0:
#                message["dst"] = message["src"]
#                message["src"] = self.__ID
#                rejected.append(message)
#            elif message["rereq"] != None:
#                rereq.append(message)

        if len(rejected) > 0:
            print "rejected:"
            for m in rejected:
                printMsg(m)
        if len(rereq) > 0:
            print "rereq:"
            for m in rejected:
                printMsg(m)
        # Put rejected, accepted and responsed messages to the queue :
        # they will be send to the hub next time mxdaemon is woke up
#        self.__mqlock.acquire()
#        self.__messageQueue += rejected + rereq
#        self.__mqlock.release()

        log.info("Mxdaemon has slept")
#        sleep(0.1)
        Timer(self.messageCheckingTimer, self.mxdaemon).start()

    def mx(self, mq):
        """Initiate communication session with the hub; upload the message queue
        and download any messages already waiting in the inbox. Always returns
        a list; Empty list returned if hub accepted the request but its response
        was bad."""
        response = ""
        request = self.__url + "mx?tid=" + self.__KEY + "+" + self.__ID
        try:
            r = urlopen(request, urlencode({"messages" : json.dumps(mq)}))
            response = r.read()
            r.close()
            if response == None:
                log.info("POST request\n" + request + "\nmessages :\n" + json.dumps(mq))
                log.error("Hub response is None. Message queue returned to the Terminal")
                return mq
        except:
            log.info("POST request\n" + request + "\nmessages :\n" + json.dumps(mq))
            log.error("Cannot exchange messages with the hub.")
            return mq
        try:
            response = json.loads(response)
            if type(response) == dict:
                response = [response]
            response = list(response)
            print "RESPONSE:"
            for r in response:
                printMsg(r)
        except:
            log.error("Bad response from the hub :\n%s\n(must be [{}, {}...])" % response)
            return []
        return response

    def getSource(self, meta):
        appcode, versioncode = meta
        log.info("Downloading the source of %s, %s" % meta)
        content = ""
        if not self.standalone:
            request = self.__url + self.__repo + "%s/%s/%s" % (self.lang(), appcode, versioncode)
            try:
                r = urlopen(request)
                content = r.read()
                r.close()
            except:
                log.error("GET " + request)
                log.error("Cannot download the source of %s, %s (lang=%s)" % (appcode, versioncode, self.lang()))
        if len(content) > 0:
            return content.replace("\r", "\n").replace("\n\n", "\n")
#        try:
        if 1:
            log.info("Getting %s, %s from the file %s" % (appcode, versioncode, self.localrepo + appcode + ".py"))
            sourcefile = open(self.localrepo + appcode + ".py")
            content = sourcefile.read()
            sourcefile.close()
            return content.replace("\r", "\n").replace("\n\n", "\n")
#        except:
#            log.error("Cannot get from file " + self.localrepo + appcode + ".py")
        return None

    def lang(self):
        """ Since apps can be written in multiple languages, we need to filter
        out those that do not match our VM's language"""
        return "python"

def printMsg(message):
    for key in message:
        print "\t", key, ":", message[key]

kernel = Kernel()
