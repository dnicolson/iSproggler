#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import codecs
import sys
import os

if sys.platform.startswith("win"):
    #mypath = os.getenv("USERPROFILE") + "\\Application Data\\iSproggler\\"
    mypath = os.path.join(os.getenv("APPDATA"),"iSproggler")
elif sys.platform == "darwin":
    mypath = os.path.expanduser("~") + "/.iSproggler/"

_debug_ = False

class Log:
    def __init__(self,truncate=False):
        self.lastmessage = ""
        self.slastmessage = ""
        try:
            self.utcoffset = self.utcoffset()
        except:
            self.utcoffset = ""
        if truncate:
            self.truncate()

    def utcoffset(self):
        #ttime = time.altzone
        if time.localtime(time.time()).tm_isdst and time.daylight:
            ttime = time.altzone
        else:
            ttime = time.timezone
        
        if ttime > 0:
            sign = "-"
        else:
            sign = "+"
        ttime = abs(ttime)
        mins = 0
        hours = 0
        
        while ttime > 0:
            ttime -= 60
            mins += 1
            if mins == 60:
                hours += 1
                mins = 0

        if hours < 10:
            hours = "0"+str(hours)
        if mins < 10:
            mins = "0"+str(mins)
            
        return " "+sign+str(hours)+str(mins)
    
    def truncate(self):
        try:
            lines = codecs.open(os.path.join(mypath,"iSproggler.log"),"rb","utf-8").readlines()
            if len(lines) > 2000:
                writelines = lines[-500:]
                linesout = codecs.open(os.path.join(mypath,"iSproggler.log"),"wb","utf-8")
                linesout.write("".join(writelines))
        except:
            pass

    def _write(self, verbosity, message):
        #to avoid repeated messages
        if self.slastmessage == message and self.lastmessage == message:
            return
        currenttime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+self.utcoffset
        try:
            logfile = codecs.open(os.path.join(mypath,"iSproggler.log"),"a","utf-8")
        except Exception, err:
            print "Unable to open to log: [%s: %s]" % (sys.exc_info()[0],err)
            return
        try:
			try:
				logfile.write("%s [%s] %s\r\n" % (currenttime, verbosity, message))
				print "%s [%s] %s" % (currenttime, verbosity, message.encode("utf-8"))
			except Exception, err:
				print "Unable to write \"%s\" to log: [%s: %s]" % (message.encode("utf-8"),sys.exc_info()[0],err)
        except UnicodeDecodeError, err:
            logfile.write("%s [%s] [UnicodeDecodeError] %s\r\n" % (currenttime, verbosity, repr(message)))
        self.slastmessage = self.lastmessage
        self.lastmessage = message

    def error(self, message):
        self._write("ERR",message)
        
    def warning(self, message):
        self._write("WARN",message)
        
    def info(self, message):
        self._write("INFO",message)

    def verb(self, message):
        self._write("VERB",message)
    
    def debug(self, message):
        if _debug_:
            self._write("DEBUG",message)

if __name__ == "__main__":
    log = Log()
    log.error("Error")
    log.info("Info")
    log.verb("Verbose")
    log.debug("Debug")