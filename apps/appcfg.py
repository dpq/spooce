#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib, urllib2, getopt, sys

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "a:v:l:k:", ["lang=", "appcode=", "versioncode=", "key="])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(1)
    
    appcode, versioncode, lang, key = "", "", "", ""
    for option, value in opts:
        if option in ("-a", "--appcode"):
            appcode = value
        if option in ("-v", "--versioncode"):
            versioncode = value
        if option in ("-l", "--lang"):
            lang = value
        if option in ("-k", "--key"):
            key = value
    
    if len(args) != 1:
        print "Only one file is allowed in a package"
        sys.exit()
    
    try:
        f = open(args[0]).read()
    except:
        print "Error reading the file"
        sys.exit()
    
    try:
        data = urllib.urlencode({"lang": lang, "appcode": appcode, "versioncode": versioncode, "key": key, "body": f})
        res = urllib2.urlopen("http://213.131.1.119/pkg/upload", data)
        print res.read()
    except:
        print "Error uploading the file"


if __name__ == "__main__":
    main()
