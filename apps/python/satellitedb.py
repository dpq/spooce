#!/usr/bin/python
# -*- coding=utf-8 -*-

from mymath import goodPrecisionFloToStr as goodPrecision
from xml.dom.minidom import parseString
from datetime import datetime, timedelta
from math import log10, pow, ceil, floor
from string import rjust, ljust
from threading import RLock
from urllib2 import urlopen
from urllib import unquote
from copy import deepcopy
from mymath import sss
from os import system
import MySQLdb
import Image

today = datetime.now()
today = datetime(today.year, today.month, today.day)
tonight = today + timedelta(days=1)
dtFormat = "%Y-%m-%d %H:%M:%S"
Qlookdt = "%Y-%m-%d_%H:%M:%S"
SATIDLEN = 4
INSTRIDLEN = 6
CHANIDLEN = 8

class Satellitedb:
    def __init__(self):
        self.lock = RLock()
        self.possible = {
            "action" : [
                "list",    # Satellites list
                "info",    # Short overview of the message["restrictions"]["satelliteSet"][0]; TODO: COMBINE with long OW!
                "desc",    # Channels structured list; restrictions are used
                "data",    # Countrates and other physical data (spectra?); restrictions are used
                "graphic", # Pass the result of the request to qlook ( OR TO FILE STORAGE THROUGH THE IMAGE CLIENT
                "file",    # Pass the result of the request to file storage
#               "write" # TODO: delete or understand, how should it work -- "write" action
            ],
            # These are supported now. Empty list is no restriction, i.e. "any instrument", for example
            "uid" : None, # None => SELECT Public only
            "satellites" : [],
            "instrumens" : [],
            "channels" : [], # names. For example, you can specify "skl" and I hope, more than one satellite will produce you some data ;)
            "particles" : [], #[("parttype", minEnergy, maxEnergy), ...]
            "dt_record" : [(today.strftime(dtFormat), tonight.strftime(dtFormat))],
            # this one and some more fields are "coordinates" and used for selecting data, not metadata
            "microsec" : [], # in the future this field will be supported by db and we will no need to save it saparately
            "lat" : []
            # there can be placed all coordinates, wich are supported by current version of python-magnetosphere
            # CHECK if COORD FIELD EXISTS
            # CHECK if WE HAVE AT LEAST ONE TLE FOR THIS satellite
        }
        self.__dbh = "localhost"
        self.__dbu = "satellitedb"
        self.__dbp = "g78JH_FEk30"
        self.__dbn = "satellitedb"

    def main(self, appid = "satellitedb", arg = {}):
        self.appid = appid

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
        return "satellitedb"

    def versioncode(self):
        return "1"

    def maintainer(self):
        return "Wera Barinova"

    def filepath(self):
        return "/home/wera/spooce/apps/python/satellitedb.py"

    def mx(self, message):
        print "HAS IS MSGID FIRST?", message.has_key("msgid")
        if not self.valid(message):
            message["dst"] = message["src"]
            message["src"] = self.appid
            kernel.sendMessage(message)
#            return message
        message["status"] = 0
        action = message.pop("action")
        result = {}
        rowCount = 1
        lenLine = 1
        header = ""
        if action == "list":
            result = map(lambda sat: (sat[1], sat[1]), self.getSatellist())
        if action == "info": # Only display name now; TODO: add more satellite info to db, like carrier, author, etc.
            result = self.getSatellinfo(message["satellites"][0])
        if action == "desc":
            channels = self.__convertToChannelHierarchy(self.getChannels(message)) # deletes restrictions from the message
            result = self.__createChannelsDescriptions(channels)
        if action in ["data", "graphic"]:
            result, boundaries, channels = self.getData(message["restrictions"]) # ["dt"] + channamesList, {dt : (tuple, of, data, for, channels) }
            if action == "graphic":
                message["dt_record"] = boundaries[2:]
                message["counters"] = boundaries[:2]
                message["channels"] = channels
                header = self.createHeader(message)
#                print "RESULT[0]", result[0]
#                result[0] = header + result[0].split("\n")[-1] + result[1]
#                print "RESULT[0]", result[0]
        if len(result) == 0:
            message["status"] = 12
            message["errmsg"] = "Error reading from db. Bad request?"
        message["dst"] = message["src"] #COMMENT FOR TEST
        message["src"] = self.appid #COMMENT FOR TEST
        if action == "graphic":
            message["partial"] = {"index" : 0, "length" : 2} # the second part must be sent by imageserver or by qlookwrapper?
            message["value"] = ""
            message["alt"] = "Wait tor image updating..."
#            print "Kernel.sendMessage('%s')" % message["alt"] #UNCOMMENT FOR TEST
            kernel.sendMessage(deepcopy(message))
            message["dst"] = "/sci/qlookwrapper"
            message["imgid"] = message["imgid"] # ??? TODO :(
            result[0] = header + "\n" + "="*52 + "\n" + result[0].split("\n")[-1] + "\n"
        if action == "data" or action == "graphic":
            message["value"] = result#, boundaries, channels # FOR DATA TESTING
            i, count = 0, len(result)
            for r in result[:1]:
                message["value"] = r
                if i != count - 1:
                    print "index :", i, "length :", count
                    message["partial"] = {"index" : i, "length" : count}
                else:
                    message["partial"] = ""
                    message.pop("partial")
                kernel.sendMessage(deepcopy(message))
                i += 1
        else:
            message["value"] = result
            kernel.sendMessage(message)
#        return message # UNCOMMENT FOR TESTING

    def valid(self, message): # add more validation
        if not message.has_key("action") or message["action"] not in self.possible["action"]:
            message["errmsg"] = "Incorrect action '%s'. Possible variants: %s" % (message["action"], "/".join(self.possible["action"]))
            message["status"] = 11
            return False
        return True

    def getSatellist(self):
        if self.testmode:
            return (("coronas-photon", "CORONAS-Photon"), ("tatyana2", "Tatyana-2"), ("meteorm", "Meteor-M#1"))
        print "select sysname from satellite;"
        self.__conn = MySQLdb.connect(host = self.__dbh, user = self.__dbu, passwd = self.__dbp, db = self.__dbn)
        self.__cursor = self.__conn.cursor()
        self.__cursor.execute("select id, sysname from satellite;")
        self.__cursor.close()
        self.__conn.close()
        # TODO: text server strings
        return self.__cursor.fetchall()

    def getSatellinfo(self, satName):
        print "select * from satellite where sysname='%s'" % satName
        self.__conn = MySQLdb.connect(host = self.__dbh, user = self.__dbu, passwd = self.__dbp, db = self.__dbn)
        self.__cursor = self.__conn.cursor()
        self.__cursor.execute("select * from satellite where sysname='%s'" % satName)
        self.__cursor.close()
        self.__conn.close()
        return self.__cursor.fetchall()

    def __createConditionFromSet(self, intervals, nameMin, nameMax=None):
        if nameMax == None:
            nameMax = nameMin
        result = "0"
        for i in intervals:
            if len(i) == 0 or (len(i) == 1 and i[0] == None) or (len(i) == 2 and i[0] == None and i[1] == None):
                continue
            if len(i) == 1 or i[0] == i[1]:
                result += " or %s='%s' " % (nameMin, i[0])
            else:
                if i[0] == None:
                    result += " or %s<='%s' " % (nameMax, str(i[1]))
                elif i[1] == None:
                    result += " or %s>='%s' " % (nameMin, str(i[0]))
                elif i[0] > i[1]:
                    result += " or (%s<='%s' or %s>='%s') " % (nameMin, str(i[1]), nameMax, str(i[0]))
                else:
                    result += " or (%s>='%s' and %s<='%s') " % (nameMin, str(i[0]), nameMax, str(i[1]))
        if result == "0":
            return "1"
        return result#And + " and (%s)" % resultOr

    def __createParticleSelect(self, particles):
        result = "0"
        for p in particles:
            result += " or (particle.name='%s' and (%s))" % (p[0], 
                self.__createConditionFromSet((p[1:3], ), "minEnergy", "maxEnergy"))
        if result == "0":
            result = "1"
        return result

    def getChannels(self, message):# [] EMPTY => SELECT ALL
        sqlRequest = "select satellite.sysname,satinstrument.name,channel.name, unit, geomfactor, comment, particle.name, minEnergy, maxEnergy, channel.idSatellite, idInstrument, channel.id from channel, satellite, particle, satinstrument"
        joinRestriction = " where channel.idSatellite=satellite.id and idParticle=particle.id and idInstrument=satinstrument.id and satinstrument.satid=satellite.id"
        sqlRequest += joinRestriction
        if message.has_key("uid") and message["uid"] != None and message["uid"] != '': # not all message["uid"] -> goto warden?
            spooceuser = message.pop("uid")
            pass
        else:
            sqlRequest += " and isprivate=0"
        for key in ["satellites", "instrumens", "channels", "particles"]:
            if not message.has_key(key):
                message[key] = [] # [] EMPTY => SELECT ALL, WITHOUT THIS FILTER
        sqlRequest += "  and (" + self.__createConditionFromSet(map(lambda elem : (elem,), message.pop("satellites")), "satellite.sysname")
        sqlRequest += ") and (" + self.__createConditionFromSet(map(lambda elem : (elem,), message.pop("instrumens")), "satinstrument.name")
        sqlRequest += ") and (" + self.__createConditionFromSet(map(lambda elem : (elem,), message.pop("channels")), "channel.name")
        sqlRequest += ") and (" + self.__createParticleSelect(message.pop("particles")) + ")"
        # (part, min, max); You can specify the same particle type more than once in different energy intervals
        self.__conn = MySQLdb.connect(host = self.__dbh, user = self.__dbu, passwd = self.__dbp, db = self.__dbn)
        self.__cursor = self.__conn.cursor()
        try:
            self.__cursor.execute(sqlRequest)
            print "EXECUTED SUCCESSFULLY"
            print sqlRequest
        except:
            print "CANNOT EXECUTE"
            print sqlRequest
            self.__cursor.close()
            self.__conn.close()
            return ()
        chans = self.__cursor.fetchall()
        self.__cursor.close()
        self.__conn.close()
        if len(chans) == 0 or chans[0] == None:
            print sqlRequest
            return ()
        return chans

    def __convertToChannelHierarchy(self, rowsOfChannels, isobject = False): # if is object = {"unit"...}, else string
        result = {}
        minE = maxE = geomfactor = isprivate = 0
        { "satName_instrName" : ( # COMMENT
                "channame", (("parttype", minE, maxE), ("anotherPart", None, maxE), "Unit", geomfactor, "comment", isprivate) # TODO: order of channels by channel id and quickly!
        )} # END OF COMMENT
        #   0         1         2        3       4          5       6        7    8    9       10     11
        #satName, instrName, chanName, unit, geomfactor, comment, ptclName, min, max, idsat, idinstr, id
        for chan in rowsOfChannels:
            satId = chan[9]
            instrId = chan[1]#0]
            id = chan[2] # one channel has more than one id!!
#            tbl = satName + "_" + instrName
            if not result.has_key(satId):
                result[satId] = {"name" : chan[0], "instruments" : {}}
            if not result[satId]["instruments"].has_key(instrId):
                print "INSTRNAME =", chan[1]
                result[satId]["instruments"][instrId] = {"name" : chan[1], "channels" : {}}
            if not result[satId]["instruments"][instrId]["channels"].has_key(id):
                result[satId]["instruments"][instrId]["channels"][id] = {
                    "unit" : chan[3],
                    "geomfactor" : chan[4],
                    "comment" : chan[5],
                    "id" : str(chan[11]),
                    "particles" : []
                }
            else:
                result[satId]["instruments"][instrId]["channels"][id]["id"] += "_" + str(chan[11])
            result[satId]["instruments"][instrId]["channels"][id]["particles"].append(tuple(chan[6:9]))
        return result
        chanDescrObject = { # Playing the COMMENT role
            "unit" : "MeV",
            "geomfactor" : 0.87,
            "comment" : "Comment from database",
            "particles" : [("electron", 0.5, 1.2)]
        }
        {"satid" : {
            "name" : "SAT NAME",
            "instruments" : {
                "instrid" : {
                    "name" : "nununu",
                    "channels" : {
                        "id" : chanDescrObject
                    }
                },#, ...
            }
        }}#, "nextSatId" :......

    def __createChannelsDescriptions(self, chans):
        result = deepcopy(chans)
        for satid in chans:
            for i in chans[satid]["instruments"]:
                result[satid]["instruments"][i] = {"channels" : {}, "name" : chans[satid]["instruments"][i]["name"]}
                for id in chans[satid]["instruments"][i]["channels"]:
                    chanInfo = chans[satid]["instruments"][i]["channels"][id]
                    result[satid]["instruments"][i]["channels"][chanInfo.pop("id")] = self.chanDescToStr(chanInfo)
        # DEBUG PRINTING
        print "Create Channels Descriptions"
        for satid in result:
            print satid
            for i in result[satid]["instruments"]:
                print "\t", result[satid]["instruments"][i]["name"]
                for id in result[satid]["instruments"][i]["channels"]:
                    print "\t\t", id
        return result

    def __createReqs(self, chans):
        print "Creating requests from channels :", chans
        request = '''select sysname, satinstrument.name, channel.name, particle.name, minEnergy, maxEnergy, unit, comment
                     from satellite, satinstrument, channel, particle
                     where satellite.id=idSatellite and satinstrument.id=idInstrument and idParticle=particle.id
                        and (%s)''' % " or ".join(map(
                            lambda ids : " or ".join(map(
                                lambda id : "channel.id='%s'" % id,
                                ids.split("_"))),
                            chans))
        info = ()
        try:
            self.__conn = MySQLdb.connect(host = self.__dbh, user = self.__dbu, passwd = self.__dbp, db = self.__dbn)
            self.__cursor = self.__conn.cursor()
            self.__cursor.execute(request)
            info = self.__cursor.fetchall()
            self.__cursor.close()
            self.__conn.close()
        except:
            print ("ERROR IN EXECUTING:\n" + request)

        reqs = {} # reqs = {"tbl" : {"chan" : {"unit" : "", "comment" : "", "particles" : ""}}}
        for inf in info: # CREATE TBL-CHANNEL association and channel descriptions
            sat, instr, chan, part, minE, maxE, unit, comment = inf # geomfactor and orientation?
            tbl = "pysatel.`%s_%s`" % (sat, instr)
            if not reqs.has_key(tbl):
                reqs[tbl] = {}
            if not reqs[tbl].has_key(chan):
                reqs[tbl][chan] = { # channel name for tbl is unique because it is a name of the table column
                    "unit" : unit,
                    "comment" : comment,
                    "particles" : []
                }
            reqs[tbl][chan]["particles"].append((part, minE, maxE))
        requests = []
        for tbl in reqs: # CREATE REQUEST TRIPLETS
            sqlRequest = "select dt_record,"
            print "__createReqs : reqs[tbl] =", reqs[tbl]
            chans = dict(map(lambda c : ("`%s`" % c, self.chanDescToStr(reqs[tbl][c])), reqs[tbl]))
            print "__createReqs : chans =", chans
            minmaxrequest = sqlRequest.replace("dt_record,", "")
            minmaxrequest += "min(dt_record),%s,max(dt_record),%s" % (
                ",".join(map(lambda c : "min(%s)" % c, chans)),
                ",".join(map(lambda c : "max(%s)" % c, chans))
            )
            sqlRequest += ",".join(chans.keys())
#            if fluxes:
#                sqlRequest += ", directionAngle, gFactor"
#                minmaxrequest += ", directionAngle, gFactor"
#                tbl += ",`%s_orient`,channel" # => gFactor from channel
            minmaxrequest += " from " + tbl
            sqlRequest += " from " + tbl
            tbl = tbl.replace("`", '').replace(".", "->")
            requests.append((sqlRequest, minmaxrequest, dict(map(lambda c : (tbl + c, chans[c]), chans))))
        return requests

    def getData(self, restrictions):
        # channel description is a dict of {"satname_satistr" : {"name" : chandesc}}
        # - result of getChannels() or chansFormFromSite()
        { # restrictions: dt_record and coordinates...
            "dt_record" : (), # several intervals or one - into tuple :)
            "lat" : (),
            "lt" : (),
            "l" : ()
        }
        if not restrictions.has_key("channels"):
            return "", 0, 0
        chans = restrictions.pop("channels")
        if len(chans) == 0:
            return "", 0, 0
        if restrictions.has_key("mode"):
            fluxes = restrictions.pop("mode") == "fluxes"
        result = {}
        # result = channamesTuple, {dt : (tuple, of, data, for, channels) }
        # channamesTuple : (("sat_instr", "channame"), ...)
        chanCount = 0
        rowCount = 0
        print "restrictions", restrictions
        print "chans", chans
        chanCount = len(chans)
        offset = 0
        chanLen = 10 # symbols per channel
        nones = map(lambda x : None, range(chanCount))
        minmaxes = [] # dt, chans limits
        if not restrictions.has_key("dt_record"):
            restrictions["dt_record"] = self.possible["dt_record"]
        whereCond = " where " + " and ".join(map(lambda r : "(%s)" %
            self.__createConditionFromSet(restrictions[r], "`%s`" % r) if r != "status" else "1",
            restrictions
        ))
        requests = self.__createReqs(chans)
        chans = {}
        # GET DATA FROM EACH SATELLITE,..
            # ...FROM EACH INSTRUMENT
        self.__conn = MySQLdb.connect(host = self.__dbh, user = self.__dbu, passwd = self.__dbp, db = self.__dbn)
        self.__cursor = self.__conn.cursor()
        for req in requests:# self.__createReqs(chans): DO NOT UNCOMMENT BEFORE CHANGING CURRENT GROUP OF CHANNELS
            sqlRequest, minMaxRequest, newChans = req
            print "sqlRequest = %s\nminMaxRequest = %s\nnewChans = %s" % (sqlRequest, minMaxRequest, str(newChans))
            for nc in newChans:
                chans[nc] = newChans[nc]
            # REQUEST EXECUTING
            sqlRequest += whereCond
            minMaxRequest += whereCond
            print "Next request :", sqlRequest 
            dt = datetime.now()
            try:
                self.__cursor.execute(sqlRequest)
            except:# Exception, e:
#                print e
                print "bad request :("
                return "", [], []
            all = self.__cursor.fetchall()
            rowCount = len(all)
            print rowCount, "row(s)", (datetime.now() - dt).seconds, "second(s)"
            for row in all: # dt, chan1, chan2...
                dt = row[0].strftime(Qlookdt)
                if not result.has_key(dt):
                    result[dt] = nones[:]
                for i in range(len(chans) - offset):
#                    if fluxes:
#                        gFactor = chans[-2]
#                        directionAngle = chans[-1]
#                        result[row[0]][offset + i] = (row[i+1] * gFactor * cos(directionAngle))
#                    else:
                    if 1: # TODO: FLUXES
                        result[dt][offset + i] = row[i+1]
            # MIN-MAX REQUEST EXECUTING
            print "Min-max request :", minMaxRequest
            try:
                self.__cursor.execute(minMaxRequest)
            except:
                print "bad request :("
                return "", [], []
            mmrow = self.__cursor.fetchone()
            currchanlen = len(chans) - offset + 1
            if minmaxes == []:
                minmaxes = [
#                    mmrow[0],
                    min(mmrow[1:currchanlen]),
#                    mmrow[currchanlen],
                    max(mmrow[currchanlen + 1:])
                ]
            else:
                minmaxes = [
#                    min(minmaxes[0], mmrow[0]),
                    min(minmaxes[0], min(mmrow[1:currchanlen])),
#                    max(minmaxes[2], mmrow[currchanlen]),
                    max(minmaxes[1], max(mmrow[currchanlen + 1:]))
                ]
            offset = len(chans)
        self.__cursor.close()
        self.__conn.close()
        dtkeys = sorted(result.keys())
        minmaxes.append(dtkeys[0])
        minmaxes.append(dtkeys[-1])
        mmres = {"dt_record" : [dtkeys[0], dtkeys[1]]}

        chpaths = chans.keys()
        chans = dict(zip(
            range(len(chans)),
            map(lambda c : c.replace("`", "").replace('.', '->').replace('_', '->') + ', ' + chans[c], chpaths)
        ))
        # SLICE MESSAGE INTO PARTS: HEADER THAN DATA PARTS
        lenDT = len("YYYY-MM-DD hh:mm:ss ")
        res = ["\n".join(map(lambda c : str(c) + " " + chans[c], chans)) + "\n" + ljust("Datetime", lenDT, " ") + " ".join(map(lambda c : rjust(str(c), chanLen, " "), range(len(chans))))]
        print res
        rowCount = len(result)
#        lenLine = len("2010-11-05 12:08:07 ") + chanCount * chanLen
        lenLine = lenDT + chanCount * chanLen
        volumeLimit = 1024 * 50 # 50Kb ==> *1024 # 1 Mb
        linesPerMessage = volumeLimit / lenLine
        messageCount = rowCount / linesPerMessage
        if rowCount % linesPerMessage:
            messageCount += 1
        print "Stats:\nRows in result : %i\nBytes per message : %i\nBytes per line : %i\nLines per message : %i\nMessages : %i" % (rowCount, volumeLimit, lenLine, linesPerMessage, messageCount)
        for i in range(messageCount):
            subres = ""
            for dt in dtkeys[i * linesPerMessage : (i + 1) * linesPerMessage]:
#                subres += dt + " ".join(map(lambda v : rjust("%.2f" % v, chanLen, " ") if v != None else "      None", result[dt])) + "\n"
                subres += dt + " ".join(map(lambda v : rjust("%.2f" % v, chanLen, " ") if v != None else "  9.99e+99", result[dt])) + "\n"
            # print subres
            res.append(subres)
        return res, minmaxes, chans

#    def fluxes(channame, countrates, directionAngles):
#        # direction is provided by satName_orientation table
#    	self.__cursor.execute("select geomfactor from channel where name='%s'" % channame)
#    	gFactor = self.__cursor.fetchone()[0]
#    	return map(lambda c, d: c * gFactor * cos(d), countrates, directionAngles)

    def sssMinMaxLog(self, min, max):
        if min <= 0:
            min = 0.0001
        if max <= 0:
            max = 10
        max = pow(10, ceil(log10(max)))
        min = pow(10, floor(log10(min)))
        steps = log10(max / min)
        return steps, max, min
    
    def getMaxMin(Columns):
        horCol = []
        vertCol = []
        for i in range(len(Columns)):
            for elem in Columns[i]:
                if (elem != -99e+99):
                    if i != 0:
                        vertCol.append(elem)
                    else:
                        horCol.append(elem)
        horMax = max(horCol)
        horMin = min(horCol)
        vertMax = max(vertCol)
        vertMin = min(vertCol)
        return horMax, horMin, vertMax, vertMin

    def emptyGrid(self, dtLimits, chanLimits):
        gridStr = """<grid id='grid%s' title='' width='100%%' height='100%%' top='0' left='2%%' offset='7%%;7%%' fontsize='10' fontcolor='#000090' fgcolor='#ccccee' bgcolor='#ffffff' >
            <axis id='utc' title='UT' column='Datetime' type='datetime' steps='%s' substeps='%s'  min='%s' max='%s' style='linear' direction='78%%;0'> </axis>
            <axis title='Countrates' column='' type='double' min='0.01' max='1e+4' steps='6' substeps='10' style='log' direction='0;70%%'> </axis>
            </grid>"""
#            <axis title='%s' column='' type='double' min='%s' max='%s' steps='%s' substeps='%s' style='log' direction='0;80%'> </axis>
#        FluxesOrCR = "Countrates"
#        if restrictions.has_key("mode") and restrictions.pop("mode") == "fluxes":
#            FluxesOrCR = "Fluxes"
        dtMin = datetime.strptime(dtLimits[0], Qlookdt)
        dtMax = datetime.strptime(dtLimits[1], Qlookdt)
        sDt, ssDt, dtMin, dtMax = sss(dtMin, dtMax)
        dtStrMin, dtStrMax = dtMin.strftime(Qlookdt), dtMax.strftime(Qlookdt)
        self.gridId += 1
        return parseString(gridStr % (str(self.gridId), sDt, ssDt, dtStrMin, dtStrMax)).documentElement

    def createHeader(self, restrictions):
        MAX_GRAPHIC_PER_GRID = 5
        colors = ["38761d", "990000", "0b5394", "bf9000", "351c75", "741b47", "b45f06", "134f5c", "ff0000", "ff9900", "000000", "00ff00", "0000ff", "9900ff", "ff00ff", "76a5af", "ea9999"]
        #title = "title", "%s (%s)" % (satellite, instrument) # FROM satellites and instruments
        width, height = 800, 400 # FROM USER WINDOW
        picture = "<?xml version='1.0' encoding='utf-8' ?>\n<picture title='' width='%s' height='%s' fontsize='14' bgcolor='#ffffff' fontcolor='#000000'>\n</picture>"""
        header = parseString(picture % (str(width), str(height)))
        picture = header.documentElement
        # not more than 5 graphics per grid
        # Buttons: "Upload Format", "Save Format"
        # together:
        # countRates, L-shell

        self.gridId = 0
        grid = self.emptyGrid(restrictions["dt_record"], restrictions["counters"])
        chans = restrictions["channels"]
        count = 0
        for chan in chans:
            if count >= MAX_GRAPHIC_PER_GRID:
                count = 0
                picture.appendChild(grid)
                grid = self.emptyGrid(restrictions["dt_record"], restrictions["counters"])
            graphic = parseString('<graphic style="solid" width="1" />').documentElement
            graphic.setAttribute("column", str(chan))
            graphic.setAttribute("title", chans[chan].replace("<", "&lt;").replace(">", "&gt;"))
            graphic.setAttribute("fgcolor", "#" + colors[count])
            grid.appendChild(graphic)
            count += 1
        if count < MAX_GRAPHIC_PER_GRID:
            picture.appendChild(grid)
        return header.toxml().replace("</pic", "\n</pic")

    def addNewSatFromFile(self, pathToTelemetry):
        # for local use only :)
        satDescFile = open(pathToTelemetry)
        self.addNewSatellite(satDescFile.read())
        satDescFile.close()

    def addNewSatellite(self, satInfo): # TODO: add returns with errors
        # satInfo is a string containing python code. It must be PySatel compatible
        # channel table: chandescfields
        chandescfields = "name", "idSatellite", "idInstr", "isprivate", "geomfactor", "idParticle", "minEnergy", "maxEnergy", "unit", "comment"
        satmodule = {}
        exec satInfo in satmodule
        satname = satmodule["desc"]()["name"]
        self.__conn = MySQLdb.connect(host = self.__dbh, user = self.__dbu, passwd = self.__dbp, db = self.__dbn)
        self.__cursor = self.__conn.cursor()
        try:
            self.__cursor.execute("insert into satellite set sysname='%s';" % satname)
        except:
            print "Cannot insert satellite ", satname
        self.__cursor.execute("select id from satellite where sysname='%s';" % satname)
        satid = self.__cursor.fetchone()[0]
        for i in satmodule["instruments"]:
            try:
                self.__cursor.execute("insert into satinstrument set name='%s', satid='%s';" % (i, satid))
            except:
                print "Cannot insert instrument", i, "satid =", satid
            self.__cursor.execute("select id from satinstrument where name='%s' and satid='%s';" % (i, satid))
            instid = self.__cursor.fetchone()[0]
            for ch in satmodule["instruments"][i][1]:
                chdata = self.channelinfo(ch)
                chname, unit, geomfactor, comment, isprivate = chdata["name"], chdata["unit"], chdata["geomfactor"], chdata["comment"], chdata["isprivate"]
                for p in chdata["particles"]:
                    if p[0] != "":
                        self.__cursor.execute("select id from particle where name='%s';" % p[0])
                        try:
                            parttype = self.__cursor.fetchone()[0]
                        except:
                            print "No particle!", i, chname, p[0], "adding..."
                            self.__cursor.execute("insert into particle set name='%s'" % p[0])
                            self.__cursor.execute("select id from particle where name='%s';" % p[0])
                            parttype = self.__cursor.fetchone()[0]
                    else:
                        parttype = 0
                    min = p[1]
                    max = p[2]
                    try:
                        self.__cursor.execute("insert into channel(name,idSatellite,idInstrument,isprivate,geomfactor,idParticle,minEnergy,maxEnergy,unit,comment) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (chname, satid, instid, int(isprivate), geomfactor, parttype, min, max, unit, comment))
                        print chname, p, "added"
                    except:
                        print "insert into channel(name,idSatellite,idInstrument,isprivate,geomfactor,idParticle,minEnergy,maxEnergy,unit,comment) values (%s, %i, %i, %i, %f, %i, %s, %s, %s, %s)", (chname, satid, instid, isprivate, geomfactor, parttype, min, max, unit, comment)
            print i, "added successfully"
        self.__cursor.close()
        self.__conn.close()
        print "Done", pathToTelemetry

    def channelinfo(self, ch):
        # parsing channel from Pysate format; `isprivate` is optional, default == 0
        # ("channame", (("partType", minEnergy, maxEnergy), (... more ptcls), "phys Unit", geomfactor, "Comment", isprivate)
        # see 
        # if minEnergy == maxEnergy the channel has not energy interval and will be displayed as "protons 10 MeV"
        # if minEnergy
        chname = ch[0]
        chdata = list(ch[1])
        if type(chdata[0]) != tuple:
            chdata = [tuple(chdata[:3])] + chdata[3:]
        particles = []
        dat = chdata.pop(0)
        while type(dat) == tuple:
            particles.append(dat)
            dat = chdata.pop(0)
        unit = dat
        geomfactor = chdata.pop(0)
        comment = chdata.pop(0)
        isprivate = len(chdata) > 0 and chdata.pop()
        return {
            "name" : chname,
            "particles" : particles,
            "unit" : unit,
            "geomfactor" : geomfactor,
            "comment" : comment + ", ",
            "isprivate" : isprivate
        }

    def chanDescToStr(self, chanInfo): # chanInfo is a result of channelinfo or elem of getChannels's result
        result = ""
        for p in chanInfo["particles"]:
            if p[0] != "" and p[0] != None:
                result += p[0]
            if p[1] == None:
                if p[2] != None:
                    result += " < " + goodPrecision(p[2])
            elif p[2] == None:
                result += " > " + goodPrecision(p[1])
            else:
                result += " %s - %s" % (goodPrecision(p[1]), goodPrecision(p[2]))
#            if chanInfo.has_key("unit") and chanInfo["unit"] != None and chanInfo["unit"] != "":
            result += " " + chanInfo["unit"] + ", "
        return (result + chanInfo["comment"])

def getElem(elemList, attrName, attrValue):
    for elem in elemList:
        if elem.getAttribute(attrName) == attrValue:
            return elem
    return None

def getElems(elemList, attrName, attrValue):
    result = []
    for elem in elemList:
        if elem.getAttribute(attrName) == attrValue:
            result.append(elem)
    return result

try:
    opt.package["satellitedb"]["1"] = Satellitedb
except:
    print "NE ZABYT' VERNUT' INSTALLING!"
    print "NE ZABYT' VERNUT' message['src'] = self.appid, kernel.sendMessage and other mx"
