#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from urllib2 import urlopen
from datetime import datetime, timedelta
from xml.dom.minidom import parse
from ConfigParser import ConfigParser

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import DateTime, Float
from sqlalchemy import Table, Column, MetaData, Index, create_engine, desc

import new

URLmi = "http://www.sec.noaa.gov/ftpdir/lists/ace/"
URLhr = "http://www.sec.noaa.gov/ftpdir/lists/ace2/"

fileMagneticField = "ace_mag_1m.txt"
fileSolarWind = "ace_swepam_1m.txt"
fileLocation = "_ace_loc_1h.txt"

Config = ConfigParser()
Config.read("/etc/spooce/apps/subsolar.cfg")

user, host, port, database = Config.get("MySQL", "user"), Config.get("MySQL", "host"), Config.get("MySQL", "port"), Config.get("MySQL", "database")

secret_MySQL = "subsolarpass"


def __InstrumentMAG_init__(self, dt, b_x, b_y, b_z, b_t, gsm_lat, gsm_lon):
    self.dt = dt
    self.b_x = b_x
    self.b_y = b_y
    self.b_z = b_z
    self.b_t = b_t
    self.gsm_lat = gsm_lat
    self.gsm_lon = gsm_lon

def __InstrumentMAG_repr__(self):
    print "MAG @ %s :: %s %f %f %f" % (str(self.dt), self.b_x, self.b_y, self.b_z)

def __InstrumentSWEPAM_init__(self, dt, eta, p_density, v_bulk):
    self.dt = dt
    self.eta = eta
    self.p_density = p_density
    self.v_bulk = v_bulk

def __InstrumentSWEPAM_repr__(self):
    print "SWEPAM @ %s :: %f %f" % (str(self.dt), self.p_density, self.v_bulk)

def __Location_init__(self, dt, x, y, z):
    self.dt = dt
    self.x = x
    self.y = y
    self.z = z

def __Location_repr__(self):
    print "Location @ %s :: %s %f %f %f" % (str(self.dt), self.x, self.y, self.z)


print "mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" % (user, secret_MySQL, host, port, database)

engine = create_engine("mysql+mysqldb://%s:%s@%s:%s/%s?charset=utf8&use_unicode=0" %
    (user, secret_MySQL, host, port, database), pool_recycle=3600)
Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine)

InstrumentMAG = new.classobj("ace_mag", (Base, ), {
    "__tablename__": 'ace_mag',
    "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
    "__init__": __InstrumentMAG_init__,
    "__repr__": __InstrumentMAG_repr__,
    "dt": Column(DateTime(), primary_key=True),
    "b_x": Column(Float()),
    "b_y": Column(Float()),
    "b_z": Column(Float()),
    "b_t": Column(Float()),
    "gsm_lat": Column(Float()),
    "gsm_lon": Column(Float())
})

InstrumentSWEPAM = new.classobj("ace_mag", (Base, ), {
    "__tablename__": 'ace_swepam',
    "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
    "__init__": __InstrumentSWEPAM_init__,
    "__repr__": __InstrumentSWEPAM_repr__,
    "dt": Column(DateTime(), primary_key=True),
    "eta": Column(DateTime()),
    "p_density": Column(Float()),
    "v_bulk": Column(Float()),
    "ion_temp": Column(Float())
})

Location =  new.classobj("ace_coord", (Base, ), {
    "__tablename__": 'ace_coord',
    "__table_args__": {'mysql_engine':'InnoDB', 'mysql_charset':'utf8'},
    "__init__": __Location_init__,
    "__repr__": __Location_repr__,
    "dt": Column(DateTime(), primary_key=True),
    "x": Column(Float()),
    "y": Column(Float()),
    "z": Column(Float())
})

Base.metadata.create_all(engine)


RE = 6356

class SubSolar:
    def main(self, appid, args):
        self.appid = appid
        self.subsolarPictureFormat = """<?xml version="1.0" encoding="utf-8" ?>
<picture title="" fontcolor="#804600" width="375" height="340" bgcolor="#ffffff">
<grid title="%s" bgcolor="#ffffff" fgcolor="#ccccee" fontcolor="#000090" width="100%" height="100%" top="0"
left="2%" offset="7%;7%">
<axis id="utc" title="UT (ACE)" column="UT" type="datetime" min="%s" max="%s"
steps="4" substeps="1" style="linear" direction="78%;0"> </axis>
 <axis title="R&lt;sub&gt;ss&lt;/sub&gt; [R&lt;sub&gt;E&lt;/sub&gt;]" column="" type="double" max="17" min="5"
steps="6" substeps="2" style="linear" direction="0;80%"> </axis>
 <graphic column="Rss" fgcolor="#a00000" style="solid" createSubscript="no" title="" width="1" />
</grid>
</picture>""" # Last hour /Last 24 hours ; min data, max data
        self.dtformat = "%Y-%m-%d_%H:%M:%S"

        kernel.sendMessage({
            "action" : "add",
            "rule": "* * * * *",
            "flag": "fetch",
            "src" : self.appid,
            "dst" : "/bin/cron"
        })
    
    def mx(self, message):
        if message["src"] == "/bin/cron" and message.has_key("flag") and message["flag"] == "fetch":
            self.getMeasurements()
            hourly, daily = self.drawCurrentChart()
            kernel.sendMessage({
                "src": self.appid,
                "dst": "/sci/qlookwrapper",
                "imgid": "SMDC_RSS_hourly",
                "data": hourly
            })
            kernel.sendMessage({
                "src": self.appid,
                "dst": "/sci/qlookwrapper",
                "imgid": "SMDC_RSS_daily",
                "data": daily
            })
            # The web client must include the image with ID SMDC_RSS
            # Gallery not included

    def getMeasurements(self):
        try:
            y, m = datetime.now().year, datetime.now().month
            print "%s%d%02d%s" % (URLhr, y, m, fileLocation)
            f = urlopen("%s%d%02d%s" % (URLhr, y, m, fileLocation)).read()
            self.saveLocation(f)
            print "%s%s" % (URLmi, fileMagneticField)
            f = urlopen("%s%s" % (URLmi, fileMagneticField)).read()
            self.saveMagneticField(f)
            print "%s%s" % (URLmi, fileSolarWind)
            f = urlopen("%s%s" % (URLmi, fileSolarWind)).read()
            self.saveSolarWind(f)
        except:
            logging.error("Error retrieving ACE measurement data. Check the log for details", exc_info=1)
            return
        
    def saveLocation(self, file):
        file = file.replace("\r", "\n").replace("\n\n", "\n").split("\n")[:-1]
        session = Session()
        for line in file[::-1]:
            line = line.split()
            if len(line) == 1:
                break
            dt = datetime.strptime("%s-%s-%sT%s:%s"%(line[0], line[1], line[2], line[3][0:2], line[3][2:4]), "%Y-%m-%dT%H:%M")
            query = session.query(Location).filter_by(dt=dt)
            if query.count() > 0:
                break
            session.add(Location(dt, line[6], line[7], line[8]))
        session.commit()
        session.close()
    
    def saveMagneticField(self, file):
        file = file.replace("\r", "\n").replace("\n\n", "\n").split("\n")[:-1]
        session = Session()
        for line in file[::-1]:
            line = line.split()
            if len(line) == 1:
                break
            dt = datetime.strptime("%s-%s-%sT%s:%s"%(line[0], line[1], line[2], line[3][0:2], line[3][2:4]), "%Y-%m-%dT%H:%M")
            query = session.query(InstrumentMAG).filter_by(dt=dt)
            if query.count() > 0:
                break
            session.add(InstrumentMAG(dt, line[7], line[8], line[9], line[10], line[11], line[12]))
        session.commit()
        session.close()
    
    def saveSolarWind(self, file):
        file = file.replace("\r", "\n").replace("\n\n", "\n").split("\n")[:-1]
        session = Session()
        for line in file[::-1]:
            line = line.split()
            if len(line) == 1:
                break
            print line
            dt = datetime.strptime("%s-%s-%sT%s:%s"%(line[0], line[1], line[2], line[3][0:2], line[3][2:4]), "%Y-%m-%dT%H:%M")
            query = session.query(InstrumentSWEPAM).filter_by(dt=dt)
            if query.count() > 0:
                break
            loc = session.query(Location).order_by(desc(Location.dt)).first()
            eta = dt + timedelta(seconds=loc.x*RE/float(line[7]))
            eta -= (timedelta(seconds=eta.second) + timedelta(microseconds=eta.microsecond))
            session.add(InstrumentSWEPAM(dt, eta, line[7], line[8]))
        session.commit()
        session.close()
    
    def calculateRss(self):
        session = Session()
        velocity, density, bz, pressure, rss = {}, {}, {}, {}, {}
        now = datetime.now()
        now -= (timedelta(seconds=now.second) + timedelta(microseconds=now.microsecond))
        for i in range(-30, 30):
            dt = now + timedelta(seconds=60*i)
            swquery = session.query(InstrumentSWEPAM).filter_by(eta=dt)
            for sw in swquery.all():
                if velocity.has_key(dt) and sw.p_density > 0 and sw.v_bulk > 0:
                    velocity[dt] = (velocity[dt]*density[dt] + sw.p_density*sw.velocity)/(density[dt] + sw.p_density)
                    density[dt] += sw.p_density
                elif not velocity.has_key(sw.dt) and not density.has_key(dt):
                    velocity[dt] = sw.v_bulk
                    density[dt] = sw.p_density
                mag = session.query(InstrumentMAG).filter_by(dt=sw.dt).one()
                bz[dt] = mag.bz
        session.close()
        for dt in velocity.keys():
            if velocity[dt] < 0 or density[dt] < 0 or bz < -999:
                continue
            # HACK. We don't actually know the pressure of alpha, we merely multiply the base pressure by 1.2
            p = 1.67*0.000001*n*v*v*1.2
            if p > 0:
                pressure[dt] = p
                rss[dt] = 8.6*(1 + 0.407*exp( -(abs(bz) - bz)*(abs(bz) - bz)/(200 * pow(p, 0.15))) * pow(p, -0.19))
        return rss # {dt : R}

    def drawCurrentCharts(self):
        rss = self.calculateRss()
        rss = map(lambda dt: dt.strftime(self.dtformat) + "\t" + str(rss[dt]), sorted(rss.keys()))
        #xml = parse("subsolarPictureFormat.xml")
        # TODO: find a good place for preparepicfiles local drive
        #self.subsolarPictureFormat = xml.toxml()
        min = min(rss.keys())
        max = max(rss.keys())
        minhour = datetime(min.year, min.month, min.day, min.hour)
        maxhour = minhour + timedelta(hours = 1)
        minday = datetime(min.year, min.month, min.day)
        maxday = minday + timedelta(days = 1)
        self.pictureFormatHourly = self.subsolarPictureFormat % ("Last hour", minhour.strftime(self.dtformat), maxhour.strftime(self.dtformat))
        self.pictureFormatDaily = self.subsolarPictureFormat % ("Last 24 hours", minday.strftime(self.dtformat), maxday.strftime(self.dtformat))
        # where to take more data for the beginning of the chart? There is only the last line
        rssHourly = rss
        rssDaily = rss
        return (
            self.pictureFormatHourly + "\n" + "="*52 + "\nUT Rss\n" + "\n".join(rssHourly),
            self.pictureFormatDaily + "\n" + "="*52 + "\nUT Rss\n" + "\n".join(rssDaily)
        )


if not opt.package.has_key("subsolar"):
    opt.package["subsolar"] = {}

opt.package["subsolar"]["1"] = SubSolar
