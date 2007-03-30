#!/usr/bin/env python
# -*- coding: utf-8 -*-

#TODO: everything

import codecs
import os
import sys
import md5
import re
import string
import cPickle
import traceback
try:
    import win32api, win32con, win32process
except:
    pass

class Control:
    def __init__(self):
        self.platform = ""
        self.path = ""
        self.getdirectory()
        self.version01()

    def getdirectory(self):
        if sys.platform.startswith("win"):
            self.platform = "Windows"
            self.path = os.getenv("USERPROFILE") + "\\Application Data\\iSproggler\\"
        elif sys.platform == "darwin":
            self.platform = "Mac OS X"
            self.path = os.path.expanduser("~") + "/.iSproggler/"
        if not os.path.exists(self.path):
            try:
                os.mkdir(self.path)
            except OSError:
                print "Unable to create the %s directory, check your permissions." % (self.path)
            return False
    
    def writeprefs(self,prefs):
        try:
            try:
                prefsfile = open(os.path.join(self.path,"iSproggler Prefs.pkl"),"wb")
                cPickle.dump(prefs,prefsfile)
                prefsfile.close()
            except (IOError, EOFError):
                print "Unable to write to prefs file in %s, check your permissions." % (self.path)
        except cPickle.UnpicklingError:
            print "Unable to write to prefs file, pickling error."
    
    def readprefs(self):
        try:
            try:
                prefsfile = open(os.path.join(self.path,"iSproggler Prefs.pkl"),"rb")
                prefs = cPickle.load(prefsfile)
                prefsfile.close()
                return prefs
            except (IOError, EOFError):
                print "Unable to read to prefs file in %s, check your permissions." % (self.path)
        except IOError, err:
            print "Unable to open prefs: %s" % err

    def readcache(self):
        try:
            cache = open(os.path.join(self.path,"iSproggler Cache.pkl"),"rb")
            cachedlist = cPickle.load(cache)
            cache.close()
            return cachedlist
        except (IOError, EOFError):
            print "Error opening cache, it might not exist."
            return None
            
    def writecache(self,filedata):
        try:
            picklefile = open(os.path.join(self.path,"iSproggler Cache.pkl"),"wb")
            cPickle.dump(filedata,picklefile)
            picklefile.close()
        except Exception, err:
            print "Error writing cache, check permissions. [%s]" % err

    def clearcache(self):
        try:
            cache = open(os.path.join(self.path,"iSproggler Cache.pkl"),"wb")
            cPickle.dump([],cache)
            cache.close()
            return True
        except (IOError, EOFError):
            print "Error clearing cache, it might not exist."
            return False

    def firstrun(self):
        print "This appears to be the first time you've run iSproggler."
        print "Please enter the following information..."
        
        self.setup()
        
        if self.platform == "Windows":
            print "If you would like iSproggler to start at login (recommended), place a shortcut of iSproggler.exe in %s\n" % (os.getenv("USERPROFILE")+"\\Start Menu\\Programs\\Startup\\\n")
            print "You can now run iSproggler.exe, it's recommended to keep both iSproggler.exe and iSprogglerCP.exe in C:\\Program Files\\iSproggler\\\n"
            print "iSprogglerCP.exe can be used at anytime to check the logs, cache or change preferences."

    def setup(self):
        username = raw_input("\nEnter your Last.fm username:\n")
        password = raw_input("\nEnter your Last.fm password:\n")
        loglevel = raw_input("\nChoose logging level [ERR/VERB/INFO]:\nERR - Only file or login errors are logged\nVERB - Default: handshakes, submissions and caching is included\nINFO - Responses from the submission server are also included\n")
        loglevel = string.upper(loglevel)
        if loglevel != "ERR" and loglevel != "VERB" and loglevel != "INFO":
            print "Not a valid option, VERB chosen by default."
            loglevel = "VERB"
        ipodchoice = raw_input("\nEnable iPod submissions? [y/n]\n")
        ipodchoice = string.lower(ipodchoice)
        if ipodchoice == "y":       
            pathchoice = None
            if self.platform == "Mac OS X":
                defaultxmlpath = os.path.expanduser("~") + "/Music/iTunes/iTunes Music Library.xml"
            else:
                defaultxmlpath = "%s\\My Documents\\My Music\\iTunes\\iTunes Music Library.xml" % os.getenv("USERPROFILE")
            if os.path.exists(defaultxmlpath):
                print "Default XML location exists: %s" % defaultxmlpath
                pathchoice = raw_input("\nIs this your XML file? [y/n]\n")
                pathchoice = string.lower(pathchoice)
            if pathchoice == "y":
                xmlfile = defaultxmlpath
            else:
                if pathchoice == None:
                    print "Could not find the XML in the default location: %s" % defaultxmlpath
                xmlfile = raw_input("\nEnter the path to your iTunes Music Library.xml file:\n")
        else:
            xmlfile = None
        self.writeprefs({"username": username, "password": md5.md5(password).hexdigest(), "loglevel": loglevel, "xmlfile": xmlfile})
        print "Preferences saved"

    def killisproggler(self):
        processes = win32process.EnumProcesses()
        for pid in processes:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
                exe = win32process.GetModuleFileNameEx(handle, 0)
                if os.path.split(exe)[1] == "iSproggler.exe":
                    PROCESS_TERMINATE = 1
                    handle = win32api.OpenProcess(PROCESS_TERMINATE, False, pid)
                    win32api.TerminateProcess(handle, -1)
                    win32api.CloseHandle(handle)
                    return True
            except:
                pass
        return False

    def isprogglerrunning(self):
        processes = win32process.EnumProcesses()
        for pid in processes:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
                exe = win32process.GetModuleFileNameEx(handle, 0)
                if os.path.split(exe)[1] == "iSproggler.exe":
                    return True
            except:
                pass
        return False

    def showmenu(self):
        print "Make a choice:\n"
        print "1. View/edit your preferences"
        print "2. View the cache"
        print "3. Clear the cache"
        print "4. Clear selected songs from cache"
        print "5. Check for uptodate messages"
        print "6. View last log messages"
        print "7. Quit iSproggler"
        print "8. Return\n"
        
        choice = raw_input()
        print ""
        if choice == "1":
            prefs = self.readprefs()
            print "Username: %s\nPassword (encrypted): %s\nLogging level: %s" % (prefs['username'],prefs['password'],prefs['loglevel'])
            try:
                print "XML file location: %s" % prefs['xmlfile']
            except KeyError:
                print "XML file location: None"
                prefs['xmllocation'] = None
            choice1 = raw_input("\nEdit this? [y/n]\n")
            choice1 = string.lower(choice1)
            if choice1 == "y":
                self.setup()
            else:
                pass
            print ""
        elif choice == "2":
            cache = self.readcache()
            if cache != None:
                print "There are %d songs cached for submission\n" % len(cache)
                if len(cache) != 0:
                    print "|Name                            |Artist                  |Play Date (UTC)    |"
                    print "|================================|========================|===================|"
                    for song in cache:
                        line = "|%s|%s|%s|" % (string.ljust(song['name'][:32],32),string.ljust(song['artist'][:24],24),song['time'])
                        print line.encode("utf-8")
            print ""
        elif choice == "3":
            cache = self.readcache()
            if len(cache) == 0:
                print "Cache is empty\n"
            else:
                if len(cache) == 1:
                    cache_s = ""
                else:
                    cache_s = "s"
                answer = raw_input("Are you sure you want to clear all %d song%s from the cache? [y/n]\n" % (len(cache),cache_s))
                answer = string.lower(answer)
                if answer == "y":
                    if self.clearcache():
                        if len(cache) == 1:
                            song_s = "s"
                        else:
                            song_s = ""
                        print "%d song%s cleared from the cache\n" % (len(cache), song_s)
                else:
                    pass
        elif choice == "4":
            cache = self.readcache()
            if cache != None:
                print "There are %d songs cached for submission\n" % len(cache)
                if len(cache) != 0:
                    print "#  |Name                          |Artist                 |Play Date (UTC)    |"
                    print "===|==============================|=======================|===================|"
                    #findsong = []
                    id = 1
                    for song in cache:
                        #findsong.append(id,song['id'],song['playcount'])
                        line = "%s|%s|%s|%s|" % (string.ljust(str(id),3),string.ljust(song['name'][:30],30),string.ljust(song['artist'][:23],23),song['time'])
                        print line.encode("utf-8")
                        id += 1
                    answer = raw_input("Choose a number to remove (anything but 1-%d will not remove anything)\n" % len(cache))
                    try:
                        if int(answer) > 0 and int(answer) <= len(cache):
                            id = 1
                            newcache = []
                            for song in cache:
                                if id == int(answer):
                                    pass
                                else:
                                    newcache.append(song)
                                id += 1
                            self.writecache(newcache)
                            print "Song removed"
                    except Exception, err:
                        print Exception, err
            print ""

        elif choice == "5":
            file = open(os.path.join(self.path,"iSproggler.log"),"rb")
            loglines = file.readlines()
            linematches = []
            for line in loglines:
                if re.search("New plug-in version available:",line):
                    linematches.append(line)
            print "Matched %d lines" % len(linematches)
            for line in linematches[-10:]:
                print line,
            print ""
        elif choice == "6":
            file = open(os.path.join(self.path,"iSproggler.log"),"rb")
            loglines = file.readlines()
            linematches = []
            for line in loglines[-10:]:
                print line,
            print ""
        elif choice == "7":
            try:
                if self.killisproggler():
                    print "Killing iSproggler..."
            except Exception:
                print "Failed to locate iSproggler.exe to terminate"
            if self.isprogglerrunning():
                print "iSproggler failed to quit, please use the Task Manager instead"
            else:
                print "iSproggler is no longer or not running"
            print ""
        elif choice == "8":
            sys.exit()
        else:
            print "%s is not a valid option" % choice
            self.showmenu()

    def version01(self):
        songhdelete = False
        cachedelete = False
        try:
            historyfile = open(os.path.join(self.path,"iSproggler Song History.pkl"),"rb")
            songhistory = cPickle.load(historyfile)
            historyfile.close()
            for songh in songhistory:
                if songh['time'].count("+") > 0:
                    songhdelete = True
            if songhdelete:
                historyfile = open(os.path.join(self.path,"iSproggler Song History.pkl"),"wb")
                cPickle.dump([],historyfile)
                historyfile.close()
                print "iSproggler 0.1 song history file cleared"
                
            cachefile = open(os.path.join(self.path,"iSproggler Cache.pkl"),"rb")
            cache = cPickle.load(cachefile)
            cachefile.close()
            for cachesong in cache:
                if cachesong['time'].count("+") > 0:
                    cachedelete = True
            if cachedelete:
                cachefile = open(os.path.join(self.path,"iSproggler Cache.pkl"),"wb")
                cPickle.dump([],cachefile)
                cachefile.close()
                print "iSproggler 0.1 cache file cleared"
        except:
            pass
            
if __name__ == "__main__":

    control = Control()
    try:
        prefsfile = open(os.path.join(sproggler.path,"iSproggler Prefs.pkl"),"rb")
    except IOError:
        control.firstrun()
        sys.exit()
    while 1:
        control.showmenu()
