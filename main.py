#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

iSproggler


LICENSE

Copyright (c) 2005, David Nicolson
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.
  3. Neither the name of the author nor the names of its contributors
     may be used to endorse or promote products derived from this software
     without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT UNLESS REQUIRED BY
LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER OR CONTRIBUTOR
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

import sys
import os
import time
import codecs
import urllib
import urllib2
import re
import md5
import math
import cPickle
import commands
#import thread
import socket
import shutil
from struct import unpack

if sys.platform.startswith("win"):
    import win32api, win32con, win32process, win32file
    from win32gui import MessageBox

try:
    import log
except TypeError:
    import traceback
    MessageBox(0,"Windows is missing the APPDATA environment variable. Search for up to date information on how this can be created.\n\n[%s]" % "\n".join(traceback.format_tb(sys.exc_info()[2])),"iSproggler",1)
    sys.exit()
import itunes
import ipod
import mbid



_version_ = "1.1.0"
_build_ = 20080115
_threaded_ = False #TODO

local = {'debug': False,
         'seekprotection': True,
         'submitdown': False,
         'handshakedown': False,
         'typelibmajor': "",
         'typelibminor': "",
         'console': False,
         'exclude_dir': [],
         'exclude_genre': [],
         'exclude_artist': [],
         'socket': False,
         'httpdebug': False,
         'proxyhost': "",
         'proxyport': "",
         'proxyuser': "",
         'proxypass': "",
         'ipoddrivename': "",
         'dispatchmode': "",
         'batchsize': 50,
         'playlistname': u"Recently Played",
         'mbidsupport': True,
         'itunesenabled': True,
         'quitonitunesquit': False,
         'forceitunesdialog': False,
         'ignorepodcasts': True,
         'ignorevideopodcasts': True,
         'ignorevideos': True}

class Scrobbler:
    def __init__(self):
        self.handshaked = False
        self.md5hash = ""
        self.interval = 1
        self.subinterval = 1
        self.subintervaltime = int(time.time())
        self.attempts = 0
        self.playingsong = None
        self.songpieces = []
        self.seeklimit = .18
        self.lastsong = self._readlastsong()
        self.failedsong = {}
        self.lastpollpos = 0
        self.setopener()
        self.manualipoderror = ""
        self.badstatsusline = 0

        self.songssubmitted = 0
        self.songsqueued = self._lencache()
        self.submissionattempts = 0
        self.successfullsubmissions = 0
        self.lastsubmitted = {}
        self.lastrawserverresponse = ""
        self.lastserverresponse = [True,"",0]
        self.pausesubmissions = False
        self.disablesubmissions = False

    def submissionstate(self,mode=None,b=None):
        """Gets or sets the submission state."""
        if b is not None:
            if b:
                b = True
            else:
                b = False
        #load the last submission state
        if mode is None:
            try:
                state = f._unpickle("iSproggler Submission State.pkl")
            except Exception, err:
                log.debug("Exception raised restoring submission state: [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))
                state = {}
            try:
                self.pausesubmissions = state['pausesubmissions']
            except KeyError:
                self.pausesubmissions = False
            try:
                self.disablesubmissions = state['disablesubmissions']
            except KeyError:
                self.disablesubmissions = False

        elif mode == "pause":
            self.pausesubmissions = b
            log.verb("Saving paused submission state: "+str(b))
            try:
                state = f._unpickle("iSproggler Submission State.pkl")
            except:
                state = {}
            state['pausesubmissions'] = b
            f._pickle("iSproggler Submission State.pkl",state)
        elif mode == "disable":
            self.disablesubmissions = b
            log.verb("Saving disabled submission state: "+str(b))
            try:
                state = f._unpickle("iSproggler Submission State.pkl")
            except:
                state = {}
            state['disablesubmissions'] = b
            f._pickle("iSproggler Submission State.pkl",state)

    def submittable(self):
        """Determines if song is submittable."""
        if main.delayedipodcheck > 0:
            log.debug("Not adding iTunes song to queue yet to preserve iPod stamp")
            return

        #if a song fails and is cached, give up
        if len(self.failedsong) != 0:
            if self.playingsong['id'] == self.failedsong['id'] and \
            self.playingsong['playcount'] == self.failedsong['playcount']:
                return False

        #same song is playing
        if len(self.lastsong) != 0:
            if self.playingsong['id'] == self.lastsong['id'] and \
            self.playingsong['playcount'] == self.lastsong['playcount']:
                return False

        #exclude rules
        if len(main.local['exclude_dir']) > 0:
            for path in main.local['exclude_dir']:
                if self.playingsong['location'].startswith(path):
                    self.failedsong = self.playingsong.copy()
                    log.verb("\"%s\" by %s will not be submitted as it resides in an excluded path [%s]" % (self.playingsong['name'], self.playingsong['artist'],path))
                    return False
        if len(main.local['exclude_artist']) > 0:
            for artist in main.local['exclude_artist']:
                if self.playingsong['artist'] == artist:
                    self.failedsong = self.playingsong.copy()
                    log.verb("\"%s\" by %s will not be submitted as it an excluded artist [%s]" % (self.playingsong['name'], self.playingsong['artist'],artist))
                    return False
        if len(main.local['exclude_genre']) > 0:
            for genre in main.local['exclude_genre']:
                if self.playingsong['genre'] == genre:
                    self.failedsong = self.playingsong.copy()
                    log.verb("\"%s\" by %s will not be submitted as it an excluded genre [%s]" % (self.playingsong['name'], self.playingsong['artist'],genre))
                    return False

        #additional submission rules
        if self.disablesubmissions:
            self.failedsong = self.playingsong.copy()
            log.verb("\"%s\" by %s will not be queued or submitted as submissions are disabled" % (self.playingsong['name'], self.playingsong['artist']))
            return False
        #if self.playingsong['duration'] == -1 and main.local['ignorepodcasts']:
        if self.playingsong['genre'] == "Podcast" and main.local['ignorepodcasts']:
            self.failedsong = self.playingsong.copy()
            log.verb("\"%s\" disqualified as it is a podcast" % self.playingsong['name'])
            return False
        if self.playingsong['duration'] == -2:
            self.failedsong = self.playingsong.copy()
            log.verb("\"%s\" disqualified as it is from the iTunes Music Store" % self.playingsong['name'])
            return False
        if self.playingsong['duration'] == -3:
            if main.local['ignorevideos']:
                self.failedsong = self.playingsong.copy()
                log.verb("\"%s\" disqualified as it is a video" % self.playingsong['name'])
                return False
        if self.playingsong['duration'] == 0:
            self.failedsong = self.playingsong.copy()
            log.verb("\"%s\" disqualified as it is a stream" % self.playingsong['name'])
            return False
        if self.playingsong['artist'] == "":
            self.failedsong = self.playingsong.copy()
            log.verb("\"%s\" disqualified as no artist is available" % self.playingsong['name'])
            return False
        if int(self.playingsong['duration']) < 30:
            if self.getMBID(self.playingsong) != None:
                log.verb("\"%s\" has a duration of less than 30 seconds but is accepted as it has an MBID" % self.playingsong['name'])
            else:
                self.failedsong = self.playingsong.copy()
                log.verb("\"%s\" disqualified as the duration is less than 30 seconds" % self.playingsong['name'])
                return False

        #pause check
        if self.playingsong['position'] == self.lastpollpos:
            log.debug("\"%s\" appears to be paused" % self.playingsong['name'])
            return False
        self.lastpollpos = self.playingsong['position']

        #main submission rules
        if int(self.playingsong['position']) >= 240 or \
        float(self.playingsong['position']) / float(self.playingsong['duration']) > .5:
            #if seekprotection is set return false if not enough of the song has played
            if math.floor(self.playingsong['duration'] * self.seeklimit) / 10 > 24:
                reqpieces = int(math.floor(480 * self.seeklimit)) / 10
            else:
                reqpieces = int(math.floor(self.playingsong['duration'] * self.seeklimit)) / 10
            if main.local['seekprotection'] and \
            len(self.songpieces) < reqpieces:
                #yes, this is crude
                log.debug("%s [(%s/%s), %f, (%d/%d)]" % (self.playingsong['name'], self.playingsong['position'], self.playingsong['duration'], float(self.playingsong['position'])/float(self.playingsong['duration']),len(self.songpieces),reqpieces))
                log.verb("Seeking/late playback, about %d seconds more needs to be played" % ((reqpieces - len(self.songpieces)) * 10))
                return False
            if len(self.lastsong) == 0:
                return True
            if self.playingsong['id'] != self.lastsong['id']:
                return True
            if self.playingsong['id'] == self.lastsong['id'] and \
            self.playingsong['playcount'] != self.lastsong['playcount']:
                return True
        return False

    def seekprotection(self):
        if main.local['seekprotection']:
            #if itunes.playing:
            if len(s.songpieces) > 0 and \
            s.songpieces[0]['id'] == s.playingsong['id'] and \
            s.songpieces[0]['playcount'] == s.playingsong['playcount']:
                s.songpieces.append(s.playingsong.copy())
            else:
                s.songpieces = []
                s.songpieces.append(s.playingsong.copy())

    def _parsehttp(self,response):
        parsed = []
        st = ""
        for char in response:
            st += char
            if char == "\n":
                parsed.append(st)
                st = ""
        return parsed

    def setopener(self):
        if main.local['proxyhost'] == "" or main.local['proxyport'] == "":
            if main.local['httpdebug']:
                opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))
                urllib2.install_opener(opener)
                log.verb("HTTP debug enabled")
            return
        if main.local['proxyuser'] == "" or main.local['proxypass'] == "":
            proxy_handler = urllib2.ProxyHandler({"http":"http://%(proxyhost)s:%(proxyport)s" % main.local})
            log.verb("Setting proxy without authorisation [%s:%s]" % (main.local['proxyhost'],main.local['proxyport']))
        else:
            proxy_handler = urllib2.ProxyHandler({"http":"http://%(proxyuser)s:%(proxypass)s@%(proxyhost)s:%(proxyport)s" % main.local})
            log.verb("Setting proxy with authorisation [%s:%s]" % (main.local['proxyhost'],main.local['proxyport']))

        if main.local['httpdebug']:
            opener = urllib2.build_opener(proxy_handler, urllib2.HTTPHandler(debuglevel=1))
            log.verb("HTTP debug enabled")
        else:
            opener = urllib2.build_opener(proxy_handler, urllib2.HTTPHandler)
        urllib2.install_opener(opener)

    def handshake(self):
        """Initialises connection with the server."""
        self.lastshakeattempt = int(time.time())

        if main.local['handshakedown']:
            return False
        log.info("Handshaking...")
        if type(main.prefs['username']) == type(u""):
            username = main.prefs['username'].encode("utf-8")
        else:
            username = main.prefs['username']
        url = "http://post.audioscrobbler.com/?" + \
            urllib.urlencode({
              "hs":"true",
              "p":"1.1",
              "c":"isp",
              "v":_version_,
              "u":username
            })

        log.debug("Handshake URL: %s" % url)

        try:
            if not main.local['socket']:
                response = urllib2.urlopen(url).readlines()
            else:
                log.verb("Using direct sockets")
                responseraw = None
                socket.setdefaulttimeout(60)
                request = url[30:]
                host = url[7:30]
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host,80))
                sock.send("GET %s HTTP/1.0\r\n" % request)
                sock.send("Host: %s\r\n" % host)
                sock.send("User-Agent: %s\r\n\r\n" % "iSproggler/"+_version_)
                try:
                    responseraw = sock.recv(1024)
                    if responseraw == "":
                        log.error("Received empty handshake response")
                        return False
                    headers, response = responseraw.split("\r\n\r\n")
                    response = self._parsehttp(response)
                except Exception, err:
                    log.error("Received bad handshake response [%s: %s] <%s>" % (sys.exc_info()[0],err,responseraw))
                    return False
        except Exception, err:
            self.lastserverresponse = [False,"Handshake connection failure",int(time.time())]
            log.error("Handshake connection failure: %s: %s" % (sys.exc_info()[0],err))
            log.info("Handshake server could be down, check Last.fm forums")
            if not main.local['socket']:
                if str(sys.exc_info()[0]) == "httplib.BadStatusLine":
                    self.badstatsusline += 1
                    if self.badstatsusline == 3:
                        log.warning("BadStatusLine server response, falling back on direct sockets")
                        main.local['socket'] = True
            return False

        if response[0].startswith("UPTODATE"):
            self.lastserverresponse = [True,"UPTODATE handshake response",int(time.time())]
            log.verb("UPTODATE response from server")
            try:
                self.md5hash = re.sub("\n$","",response[1])
                self.urlsubmit = re.sub("\n$","",response[2])
                log.debug("Submit URL: %s" % self.urlsubmit)
            except IndexError:
                log.error("Bad handshake response")
                return False
            self.handshaked = True
            return True
        if response[0].startswith("UPDATE"):
            self.lastserverresponse = [True,"UPDATE handshake response",int(time.time())]
            log.verb("UPDATE response from server")
            match = re.match("UPDATE\s+(.*)\n",response[0])
            log.verb("New plug-in version available: %s" % match.group(1))
            try:
                self.md5hash = re.sub("\n$","",response[1])
                self.urlsubmit = re.sub("\n$","",response[2])
                log.debug("Submit URL: %s" % self.urlsubmit)
            except IndexError:
                log.error("Bad handshake response")
                return False
            self.handshaked = True
            return True
        elif response[0].startswith("BADUSER"):
            self.lastserverresponse = [False,"BADUSER handshake response",int(time.time())]
            log.verb("BADUSER response from server")
            log.error("Bad username")
            self.handshaked = False
            return False        
        elif response[0].startswith("FAILED"):
            self.lastserverresponse = [False,"FAILED handshake response",int(time.time())]
            log.verb("FAILED response from server")
            match = re.match("FAILED\s+(.*)\n",response[0])
            log.error("Handshake failed: " + match.group(1))
            log.verb("Handshake URL: %s" % url)
            self.handshaked = False
            return False
        else:
            log.warning("Received bad handshake response: %s" % response[0])
            self.handshaked = False
            return False

    def submit(self,songs):
        """Takes one or more songs and submits them to Audioscrobbler."""
        if main.local['submitdown']:
            self.lastserverresponse = [False,"Debug: submitdown",int(time.time())]
            return False

        #this will immediately cache the song
        if self.pausesubmissions:
            log.verb("\"%s\" queued for submission as submissions are paused" % songs[0]['name'])
            self.songsqueued += 1
            return False

        self.submissionattempts += 1

        n = 0
        response = md5.md5(main.prefs['password']+self.md5hash).hexdigest()
        submission = "u="+urllib.quote(main.prefs['username'])+"&s="+response
        
        for song in songs:
            submission += "&"+"a["+str(n)+"]="+urllib.quote(song['artist'].encode("utf-8"))
            submission += "&"+"t["+str(n)+"]="+urllib.quote(song['name'].encode("utf-8"))
            if song['album'] != "":
                submission += "&"+"b["+str(n)+"]="+urllib.quote(song['album'].encode("utf-8"))
            else:
                submission += "&"+"b["+str(n)+"]="+""
            if song['mbid'] is not None:
                submission += "&"+"m["+str(n)+"]="+song['mbid']
            else:
                submission += "&"+"m["+str(n)+"]="+""
            submission += "&"+"l["+str(n)+"]="+str(song['duration'])
            submission += "&"+"i["+str(n)+"]="+urllib.quote(song['time'])
            n += 1
        
        try:
            log.verb("Last submitted song %s UTC" % self.lastsong['time'])
        except:
            pass        
        
        try:
            match = re.match("(.*)&a\[1\]",submission)
            log.debug("Submitting %s and others..." % match.group(1))
            log.info("Submitting %d songs..." % n)
        except AttributeError:
            log.debug("Submitting %s..." % submission)
            log.info("Submitting 1 song...")

        try:
            if not main.local['socket']:
                o = urllib2.urlopen(self.urlsubmit,submission)
                response = o.readlines()
            else:
                log.verb("Using direct sockets")
                responseraw = None
                socket.setdefaulttimeout(60)
                address, request = self.urlsubmit[7:].split('/')
                host, port = address.split(':')
                request = "/"+request
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))
                sock.send("POST %s HTTP/1.0\r\n" % request)
                sock.send("Host: %s\r\n" % host)
                sock.send("User-Agent: %s\r\n" % ("iSproggler/"+_version_))
                sock.send("Content-Length: %s\r\n" % len(submission))
                sock.send("Content-Type: application/x-www-form-urlencoded\r\n\r\n")
                sock.send("%s\r\n\r\n" % submission)
                try:
                    responseraw = sock.recv(1024)
                    if responseraw == "":
                        log.error("Received empty submission response")
                        return False
                    headers, response = responseraw.split("\r\n\r\n")
                    response = self._parsehttp(response)
                except Exception, err:
                    log.error("Received bad submission response [%s: %s] <%s>" % (sys.exc_info()[0],err,responseraw))
                    return False     
        except Exception, err:
            self.lastserverresponse = [False,"Submission connection failure",int(time.time())]
            log.error("Submission connection failure: %s: %s [%s]" % (sys.exc_info()[0],err,self.urlsubmit))
            log.info("Submission server could be down, check Last.fm forums")
            self.attempts += 1
            log.debug("Number of failed submission attempts: %d" % self.attempts)
            if self.attempts == 3:
                log.verb("Voiding current handshake due to three consecutive submission network errors")
                self.handshaked = False
                self.handshake()
                self.attempts = 0
            if not main.local['socket']:
                if str(sys.exc_info()[0]) == "httplib.BadStatusLine":
                    self.badstatsusline += 1
                    if self.badstatsusline == 3:
                        log.warning("BadStatusLine server response, falling back on direct sockets")
                        main.local['socket'] = True
                    try:
                        log.verb("Headers: "+repr(o.headers.dict))
                        log.verb("Message: "+o.msg)
                        log.verb("Code: "+str(o.code))
                    except:
                        pass
            #this better work
            self.subinterval *= 2
            self.subintervaltime = int(time.time()) + self.subinterval * 10
            if self.subintervaltime > int(time.time()) + 120 * 60:
                self.subintervaltime = int(time.time()) + 120 * 60
            log.debug("Retrying submission in %d seconds [%d]" % (self.subinterval * 10,self.subintervaltime))
            return False

        #reset amount of failed attempts
        self.attempts = 0
        self.lastrawserverresponse = response[0]

        if response[0].startswith("OK"):
            self.lastserverresponse = [True,"OK submission response",int(time.time())]
            log.verb("OK response from server")
            self.songssubmitted += len(songs)
            self.successfullsubmissions += 1
            self.lastsubmitted = songs[-1]
            if len(songs) > 1:
                listofsongs = ""
                for song in songs:
                    listofsongs += "\"%s\" by %s [%s UTC], " % (song['name'],song['artist'],song['time'])
                log.info("%s submitted" % listofsongs[0:-2])
            else:
                log.info("\"%s\" by %s [%s UTC] submitted" % (song['name'],song['artist'],song['time']))
            self.subinterval = 1
            log.debug("Setting submission interval to 1")
            return True
        elif response[0].startswith("BADAUTH"):
            self.lastserverresponse = [False,"BADAUTH submission response",int(time.time())]
            log.verb("BADAUTH response from server")
            log.error("Incorrect username or password")
            log.verb("Voiding current handshake due to submission authentication failure")
            self.handshaked = False
            self.handshake()
            self.subinterval *= 2
            self.subintervaltime = int(time.time()) + self.subinterval * 10
            if self.subintervaltime > int(time.time()) + 120 * 60:
                self.subintervaltime = int(time.time()) + 120 * 60
            log.debug("Retrying submission in %d seconds [%d]" % (self.subinterval * 10,self.subintervaltime))
            return False        
        elif response[0].startswith("FAILED"):
            self.lastserverresponse = [False,"FAILED submission response",int(time.time())]
            log.verb("FAILED response from server")
            match = re.match("FAILED\s+(.*)\n",response[0])
            log.verb("Submission failed: %s" % match.group(1))
            log.verb("POST string: %s" % submission)

            if "Plugin bug" in match.group(1):
                log.verb("Reducing submission size to bypass truncated proxy: [%d]" % main.local['batchsize'])
                main.local['batchsize'] = int(main.local['batchsize'] / 2)
                if main.local['batchsize'] <= 1:
                    main.local['batchsize'] = 1
                return False

            log.verb("Voiding current handshake due to submission failure")
           
            self.handshaked = False
            self.handshake()
            self.subinterval *= 2
            self.subintervaltime = int(time.time()) + self.subinterval * 10
            if self.subintervaltime > int(time.time()) + 120 * 60:
                self.subintervaltime = int(time.time()) + 120 * 60
            log.debug("Retrying submission in %d seconds [%d]" % (self.subinterval * 10,self.subintervaltime))
            return False
        else:
            log.warning("Received unrecognizable submission response: %s" % response[0])
            log.verb("Voiding current handshake due to submission failure")
            self.handshaked = False
            self.handshake()
            self.subinterval *= 2
            self.subintervaltime = int(time.time()) + self.subinterval * 10
            if self.subintervaltime > int(time.time()) + 120 * 60:
                self.subintervaltime = int(time.time()) + 120 * 60
            log.debug("Retrying submission in %d seconds [%d]" % (self.subinterval * 10,self.subintervaltime))
            return False
            
    def submitcache(self):
        if self.songsqueued > 0:
            if int(time.time()) >= self.subintervaltime:
                if self.chunkcheck(f.cacheread()):
                    log.debug("Resetting submission interval")
                    self.subinterval = 1
            else:
                try:
                    log.verb("Attempting submission at %s" % time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(self.subintervaltime)))
                except:
                    log.verb("Attempting resubmission later")
                log.debug("Submission interval: %d" % self.subinterval)
    
    def getMBID(self,song):
        """Finds a MusicBrainz track identifier embedded in an ID3v2 tag."""
        if not main.local['mbidsupport']:
            return None
        try:
            if song['location'] is None:
                return None
        except KeyError:
            return None

        try:
            log.debug("Reading ID3 tag...")
            tmbid = mbid.getMBID(song['location'])
            if tmbid is not None:
                log.verb("Found MBID %s for \"%s\"" % (tmbid,song['name']))
                return tmbid
        except Exception, err:
            log.error("An error occurred checking \"%s\" for an MBID [%s:%s]" % (song['name'],sys.exc_info()[0],err))
            return None

    def addsong(self):
        """Takes a playing song and feeds it to submit()."""
        self.playingsong['mbid'] = self.getMBID(self.playingsong)
        self.playingsong['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()-int(self.playingsong['position'])))
        if self.submit([self.playingsong.copy()]):
            log.verb("Submission successful")
        else:
            if f.cacheadd(self.playingsong.copy()):
                self.songsqueued += 1
            self.failedsong = self.playingsong.copy()

    def submitandclear(self,songstosubmit):
        """Takes cached songs, submits then clears cache."""
        if self.submit(songstosubmit):
            if f.cacheclear(songstosubmit):
                log.verb("Submission successful from cache")
                self.songsqueued = self._lencache()
            else:
                log.warning("Submission successful from cache, cache unable to be cleared")
        else:
            return False

    def addsongtocache(self):
        """Takes a playing song and caches it."""
        self.playingsong['mbid'] = self.getMBID(self.playingsong)
        self.playingsong['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()-int(self.playingsong['position'])))
        if f.cacheadd(self.playingsong.copy()):
            self.songsqueued += 1
        #song hasn't failed, but we don't want to keep checking it
        self.failedsong = self.playingsong.copy()

    def addsongipod(self,song):
        """Adds a song played when closed."""
        song['mbid'] = self.getMBID(song)
        if song['duration'] < 30:
            if song['mbid'] is None:
                log.verb("\"%s\" by %s disqualified because the duration is less than 30 seconds" % (song['name'],song['artist']))
                return
            else:
                log.verb("\"%s\" has a duration of less than 30 seconds but is accepted as it has an MBID" % song['name'])
        if f.cacheadd(song.copy()):
            self.songsqueued += 1

    def addsongipodmanual(self,song):
        """Adds a song played when closed."""
        if f.cacheadd(song.copy()):
            self.songsqueued += 1
    
    def _pluralise(self,integer):
        if integer == 1:
            return ""
        else:
            return "s"
    
    def checkipodsongs(self):
        """Checks to see if any songs have been played in iTunes without iSproggler."""
        #if not main.prefs['ipodsupport']:
        #    return
        
        if itunes.xml_file is not None:
            if itunes.xml_file != main.prefs['xmlfile']:
                log.warning("iTunes is using a different iTunes Music Library.xml than the default [default: %s, iTunes: %s]" % (main.prefs['xmlfile'],itunes.xml_file))
                main.prefs['xmlfile'] = itunes.xml_file
        if main.prefs['xmlfile'] == "":
            return
        if main.prefs['xmlfile'] is None:
            return
        if self.lastsong == {}:
            log.verb("Unable to check for iPod played songs until a song is played in iTunes")
            return
        if self.disablesubmissions:
            return
        log.verb("Using XML file: %s" % main.prefs['xmlfile'])
        if not os.path.exists(main.prefs['xmlfile']):
            if sys.platform.startswith("win"):
                MessageBox(0,"The iTunes Library files have been moved or deleted. iPod support has been disabled, enable it again and choose an active iTunes Music Library.xml file","iSproggler",1)
                main.prefs['ipodsupport'] = False
                main.prefs['ipodmultiple'] = False
                main.prefs['xmlfile'] = ""
                f._pickle("iSproggler Prefs.pkl",main.prefs)
                log.warning("iTunes Music Library.xml file not found")
                return
        if os.stat(main.prefs['xmlfile']).st_mtime < time.mktime(time.localtime())-24*60*60:
            secs_old = time.mktime(time.localtime()) - os.stat(main.prefs['xmlfile']).st_mtime
            log.warning("iTunes Music Library.xml file appears to be unused by iTunes (%d secs old)" % int(secs_old))

        if len(self.lastsong) > 0:
            ipodsongs = ipod.checkipod(self.lastsong.copy(),main.prefs,main.local)
            if ipodsongs is not None:
                for ipodsong in ipodsongs:
                    if ipodsong is not None:
                        self.addsongipod(ipodsong.copy())
                log.info("%d song%s played offline added to the submission queue" % (len(ipodsongs),self._pluralise(len(ipodsongs))))
                f.chronorder()
                f.updateipodepoch()
                if s.handshaked:
                    self.submitcache()

    def ipodmanual(self):
        if not itunes.connected:
            self.manualipoderror = "Unable to communicate with iTunes. If this is persistent iTunes is not installed properly and the iTunes installer must be run again. No playlists or music will be affected"
            log.verb("Unable to check for iPod songs because there is no iTunes connection")
            return False
        if itunes.eventhandler:
            if itunes.Events.suspended:
                self.manualipoderror = "Unable to check for iPod songs because the iTunes connection is suspended [%s]" % itunes.Events.suspendedreason
                log.verb("Unable to check for iPod songs because the iTunes connection is suspended")
                return False

        log.verb("Manually checking for iPod songs in playlist \"%s\"" % main.local['playlistname'])
        if len(self.lastsong) > 0:
            try:
                ipodsongs = ipod.manual(self.lastsong.copy(),itunes.iTunes,main.local)
            except Exception, err:
                if str(sys.exc_info()[0]) == "pythoncom.com_error":
                    self.manualipoderror = "An error occurred communicating with iTunes: %s" % err
                    return False
                else:
                    self.manualipoderror = "An error occurred manually checking for iPod songs: [%s:%s]" % (sys.exc_info()[0],err)
                    return False

            if ipodsongs is not None:
                for ipodsong in ipodsongs:
                    if ipodsong is not None:
                        self.addsongipodmanual(ipodsong.copy())
                log.info("%d song%s played offline added to the submission queue" % (len(ipodsongs),self._pluralise(len(ipodsongs))))
                f.chronorder()
                f.updateipodepoch()
                if s.handshaked:
                    self.submitcache()
            else:
                MessageBox(0,"No songs found in playlist \"%s\" after the last iTunes- or iPod-played song \"%s\" played at %s UTC, be sure to select Update iPod before playing songs in iTunes" % (main.local['playlistname'],s.lastsong['name'],s.lastsong['time']),"iSproggler",1)
                log.error("No songs found in playlist \"%s\" after the last iTunes- or iPod-played song \"%s\" played at %s UTC, be sure to select Update iPod before playing songs in iTunes" % (main.local['playlistname'],s.lastsong['name'],s.lastsong['time']))
                return False
        else:
            self.manualipoderror = "Unable to check for iPod-played songs until a song is played in iTunes"
            return False
        
        return True

    def chunkcheck(self,songstosubmit):
        """Checks to see whether cache needs to be chunked."""
        log.info("%d song%s queued for submission" % (len(songstosubmit),self._pluralise(len(songstosubmit))))
        if self.pausesubmissions:
            return
        success = True
        chunked = self._chunkcache(songstosubmit)
        if songstosubmit != chunked:
            for chunk in chunked:
                if self.submitandclear(chunk) is False:
                    log.verb("One chunk failed to submit, retrying later")
                    success = False
                    break
        else:
            if self.submitandclear(songstosubmit) is False:
                success = False
        return success

    def _chunkcache(self,songs):
        """Takes a list with dictionaries and returns them in smaller lists."""
        chunked = []
        index = -1
        maxlength = main.local['batchsize']
        
        if len(songs) > maxlength:
            counter = 0
            for item in songs:
                if counter == 0:
                    chunked.append([item])
                    index += 1
                else:
                    chunked[index].append(item)
                counter += 1
                if counter == maxlength:
                    counter = 0
            return chunked
        else:
            return songs

    def _readlastsong(self):
        try:
            songhistorypath = os.path.join(main.mypath,"iSproggler Song History.pkl")
            picklefile = open(songhistorypath,"rb")
            unpickleddata = cPickle.load(picklefile)
            picklefile.close()
            return unpickleddata[-1]
        except Exception, err:
            if main.ready():
                if os.path.exists(songhistorypath):
                    log.warning("Error reading song history: [%s]" % err)
            return {}

    def _lencache(self):
        try:
            cachepath = os.path.join(main.mypath,"iSproggler Cache.pkl")
            picklefile = open(cachepath,"rb")
            unpickleddata = cPickle.load(picklefile)
            picklefile.close()
            return len(unpickleddata)
        except Exception, err:
            if main.ready():
                if os.path.exists(cachepath):
                    log.warning("Error reading cache: [%s]" % err)
            return 0

class Files:
    def __init__(self):
        self.version01()

    def _pickle(self, filename, filedata):
        picklefile = open(os.path.join(main.mypath,filename),"wb")
        cPickle.dump(filedata,picklefile)
        picklefile.close()

    def _unpickle(self, filename):
        try:
            picklefile = open(os.path.join(main.mypath,filename),"rb")
            unpickleddata = cPickle.load(picklefile)
            picklefile.close()
            return unpickleddata
        except cPickle.UnpicklingError:
            log.error("Unpickling error reading %s" % filename)
            return []
            
    def cacheread(self):
        """Reads cache into a list of dictionaries."""
        try:
            return self._unpickle("iSproggler Cache.pkl")
        except (IOError, EOFError), err:
            log.error("File error reading cache %s" % err)
            return False

    def cachecheck(self):
        """Return true if cache is populated."""
        if os.path.isfile(os.path.join(main.mypath,"iSproggler Cache.pkl")):
            if len(self.cacheread()) > 0:
                return True
        return False
        
    def songhistoryread(self):
        """Returns a list of the last played (not necessarily submitted) songs."""
        try:
            return self._unpickle("iSproggler Song History.pkl")
        except (IOError, EOFError):
            return []

    def _writehistory(self,song):
        try:
            songhistory = self._unpickle("iSproggler Song History.pkl")
            songhistory.append(song)
            if len(songhistory) > 10:
                songhistory = songhistory[1:]
        except (IOError, EOFError):
            songhistory = [song]
            pass
        #have to break these up otherwise the list will never be written
        try:
            self._pickle("iSproggler Song History.pkl",songhistory)
        except (IOError, EOFError):
            pass

    def songhistorywrite(self, song):
        """Records played (not necessarily submitted) songs to compare with the iTunes Library."""
        song['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()-int(song['position'])))
        s.lastsong = song.copy()
        self._writehistory(song)
    
    def updateipodepoch(self):
        self._writehistory(s.lastsong)

    def cacheadd(self,song):
        song['position'] = 0
        try:
            cachedlist = self._unpickle("iSproggler Cache.pkl")
            #check if song already exists in cache
            try:
                cachedlist.index(song)
                log.warning("The song \"%s\" is already cached (play count: %d, play date (minus duration): %s UTC)" % (song['name'],song['playcount'],song['time']))
            except ValueError:
                cachedlist.append(song)
                s.lastsong = song.copy()
                log.info("Adding \"%s\" by %s to the submission queue [%s UTC]" % (song['name'],song['artist'],song['time']))
            self._pickle("iSproggler Cache.pkl",cachedlist)
            return True
        except (IOError, EOFError), err:
            try:
                log.verb("Creating cache file")
                log.info("Adding \"%s\" by %s to the submission queue [%s UTC]" % (song['name'],song['artist'],song['time']))
                self._pickle("iSproggler Cache.pkl",[song])
                return True
            except (IOError, EOFError), err:
                log.error("Unable to create cache file %s" % err)
                return False

    def cacheclear(self,songs):
        try:
            cachedlist = self._unpickle("iSproggler Cache.pkl")
            for song in songs:
                try:
                    cachedlist.remove(song)
                except ValueError:
                    log.warning("Tried to remove a song from the cache that wasn't there: \"%s\" by %s" % (song['name'],song['artist']))
            self._pickle("iSproggler Cache.pkl",cachedlist)
            return True
        except (IOError, EOFError), err:
            log.error("Unable to update cache file %s" % err)
    
    def _sortdictlist(self,songs):
        sorted = map(lambda x, key="time": (x['time'], x), songs)
        sorted.sort()
        return map(lambda (key, x): x, sorted)
        
    def chronorder(self):
        cache = self._unpickle("iSproggler Cache.pkl")
        self._pickle("iSproggler Cache.pkl",self._sortdictlist(cache))

    def version01(self):
        songhdelete = False
        cachedelete = False
        try:
            songhistory = self._unpickle("iSproggler Song History.pkl")
            for songh in songhistory:
                if songh['time'].count("+") > 0:
                    songhdelete = True
            if songhdelete:
                self._pickle("iSproggler Song History.pkl",[])
                log.verb("iSproggler 0.1 song history file cleared")
                
            cache = self._unpickle("iSproggler Cache.pkl")
            for cachesong in cache:
                if cachesong['time'].count("+") > 0:
                    cachedelete = True
            if cachedelete:
                self._pickle("iSproggler Cache.pkl",[])
                log.verb("iSproggler 0.1 cache file cleared")
        except:
            pass


class Main:
    def __init__(self):
        self.setmypath()
        self.prefs = {}
        self.ipodmounted = False
        self.ipodname = ""
        self.drivelist = []
        self.delayedipodcheck = 0
        self.updateonunmount = False
        if sys.platform.startswith("win"):
            if self.isrunning():
                sys.exit(1)
        self.plugincheck()
    
    def initalert(self,text):
        if sys.platform.startswith("win"):
            MessageBox(0,text,"iSproggler",1)
        else:
            print text
    
    def isrunning(self):
        """Checks to see if iSproggler is already running."""
        isprogglers = 0
        processes = win32process.EnumProcesses()
        for pid in processes:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
                exe = win32process.GetModuleFileNameEx(handle, 0)
                if os.path.split(exe)[1] == "iSproggler.exe" or \
                os.path.split(exe)[1] == "iSprogglerConsole.exe":
                    isprogglers += 1
            except:
                pass
        if isprogglers > 1:
            return True
        else:
            return False

    def timecheck(self):
        socket.setdefaulttimeout(12)
        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            sock.sendto("\x1b"+ 47 * "\0",("pool.ntp.org",123))
            data, address = sock.recvfrom(1024)
            t = unpack("!12I",data)[10]
            t -= 2208988800L

            ntp_t = time.localtime(t)
            local_t = time.localtime()
            diff = abs(time.mktime(ntp_t) - time.mktime(local_t))
            
            if diff > 600:
                log.warning("Check your system clock, time is %f seconds off [local: %s, ntp: %s]" % \
                    (diff,time.strftime("%Y-%m-%d %H:%M:%S",local_t)+" "+time.tzname[0],time.strftime("%Y-%m-%d %H:%M:%S",ntp_t)+" "+time.tzname[0]))
        except:
            pass

    def _plugininstalled(self,plugin):
        if os.path.exists(os.path.join("C:\\Program Files\\iTunes\\Plug-Ins\\",plugin)):
            return True
        if os.path.exists(os.path.join(os.path.join(os.getenv("USERPROFILE"),"\\Application Data\\Apple Computer\\iTunes\\iTunes Plug-ins\\"),plugin)):
            return True
        
        return False

    def iscrobblercheck(self):
        if not self._plugininstalled("iScrobbleWin.dll"):
            return False

        try:
            config = open(os.path.join(os.getenv("USERPROFILE"),"\\Application Data\\iScrobbler.ini"),"rb").readlines()
            metadict = {}
            for line in config[1:]:
                match = re.match("([a-z_]*)=(.*)\r",line)
                metadict[match.group(1)] = match.group(2)

            if metadict['enabled'] == "1":
                return True
        except:
            pass

        return False

    def jscrob2check(self):
        if not self._plugininstalled("jscrob2.dll"):
            return False

        try:
            import _winreg
            reg = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
            key = _winreg.OpenKey(reg, r"Software\jscrob2", _winreg.KEY_READ)
            enable = _winreg.QueryValueEx(key, "enable")[0]
            if enable == 1:
                return True
        except:
            pass

        return False

    def audioscrobblercheck(self):
        if not self._plugininstalled("audioscrobbler.dll"):
            return False

        try:
            import _winreg
            reg = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
            key = _winreg.OpenKey(reg, r"Software\Last.fm\Users", _winreg.KEY_READ)
            #user = _winreg.EnumKey(key, 0)
            user = _winreg.QueryValueEx(key, "CurrentUser")[0]
            key = _winreg.OpenKey(reg, r"Software\Last.fm\Users\%s" % user, _winreg.KEY_READ)
            enable = _winreg.QueryValueEx(key, "LogToProfile")[0]

            if enable == 1:
                return True
        except:
            pass

        return False

    def plugincheck(self):
        if sys.platform.startswith("win32"):
            if self.audioscrobblercheck():
                self.initalert("Audioscrobbler appears to be enabled for the current Audioscrobbler account.\n\nPlease deselect the 'Enable scrobbling' menu before playing songs in iTunes.")
            if self.iscrobblercheck():
                self.initalert("iScrobbler appears to be enabled.\n\nPlease disable it before playing songs in iTunes.")
            if self.jscrob2check():
                self.initalert("jscrob2 appears to be enabled.\n\nPlease disable it before playing songs in iTunes or updating your iPod.")

    def setmypath(self):
        if sys.platform.startswith("win"):
            #mypath = os.getenv("USERPROFILE") + "\\Application Data\\iSproggler\\"
            mypath = os.path.join(os.getenv("APPDATA"),"iSproggler")
        elif sys.platform == "darwin":
            mypath = os.path.expanduser("~") + "/.iSproggler/"
        else:
            self.initalert("Unsupported platform: %s." % sys.platform)
            sys.exit(1)
        if not os.path.exists(mypath):
            try:
                os.mkdir(mypath)
                self.mypath = mypath
            except OSError:
                self.initalert("Unable to create the %s directory, check your permissions." % mypath)
                sys.exit(1)
        else:
            self.mypath = mypath
        
    def setprefs(self):
        """Reads preferences."""
        defaultprefs = {'username': "",
                        'password': "",
                        'passlength': 8,
                        'ipodsupport': False,
                        'ipodmultiple': False,
                        'xmlfile': "",
                        'ipodmanual': False,
                        'itunesinstall': False}

        try:
            prefsfile = open(os.path.join(self.mypath,"iSproggler Prefs.pkl"),"rb")
            prefs = cPickle.load(prefsfile)
            prefsfile.close()
        except IOError:
            prefs = {}
        for pref in defaultprefs:
            try:
                prefs[pref]
            except:
                prefs[pref] = defaultprefs[pref]
        self.prefs = prefs

    def setlocal(self,local):
        #search the local.py in the iSproggler folder and not the one bundled with py2exe in later versions
        sys.path.insert(0,os.path.split(sys.argv[0])[0])
        try:
            os.remove(os.path.join(os.path.split(sys.argv[0])[0],"local.pyc"))
        except:
            pass
        try:
            from local import local as localadd
            localold = local.copy()
            local.update(localadd)
            if local != localold:
                for key in localold:
                    if localold[key] != local[key]:
                        log.verb("local.py value: '%s': %s" % (key, local[key]))
        except:
            self.initalert("Init Warning: Parse error in local.py file.")
        self.local = local

    def ready(self):
        if self.prefs['username'] == "" or self.prefs['password'] == "":
            return False
        return True    

    def cli(self):
        if main.local['console']:
            return True
        if len(sys.argv) > 1:
            if sys.argv[1] == "--gui":
                return False
            if sys.argv[1] == "--console":
                return True
        if not sys.platform.startswith("win"):
            return True
        return False

    def control(self):
        import control
        control = control.Control()
        control.showmenu()
        sys.exit()    

    def initialhandshake(self):
        socket.setdefaulttimeout(20)
        if s.handshake():
            s.handshaked = True
            log.info("Handshake success on launch")
        else:
            s.handshaked = False
            log.info("Handshake failure on launch")
        socket.setdefaulttimeout(60)

    def _drivelist(self):
        if sys.platform == "darwin":
            #workspace = NSWorkspace.sharedWorkspace()
            #drivelist = workspace.mountedLocalVolumePaths()
            drivelist = [unicode("/Volumes/"+drive,"utf-8") for drive in os.listdir("/Volumes/") \
                            if os.path.isdir("/Volumes/"+drive)]
        elif sys.platform.startswith("win"):
            drivelist = [drive for drive in win32api.GetLogicalDriveStrings()[:-1].split("\x00") \
                            if win32file.GetDriveType(drive) in [win32file.DRIVE_REMOVABLE]]
            drives = [drive+" "+repr(win32file.GetDriveType(drive)) for drive in win32api.GetLogicalDriveStrings()[:-1].split("\x00")]
            #log.debug("Drivelist: %s" % repr(drives))
            for drive in ["A:\\","B:\\","C:\\"]:
                try:
                    drivelist.remove(drive)
                except ValueError:
                    pass
        return drivelist
    
    def ipodcheck(self):
        if int(time.time()) > self.delayedipodcheck and \
        self.delayedipodcheck != 0:
            self.delayedipodcheck = 0
            s.checkipodsongs()
            
        if self.delayedipodcheck > 0:
            #log.verb("Not checking iPods until sync has finished [%s]" % int(time.time()) - self.delayedipodcheck)
            log.verb("Not checking iPods until sync has finished")
            return
            
        drives = self._drivelist()
        newdrives = []
        for drive in drives:
            if drive not in self.drivelist:
                newdrives.append(drive)
        self.drivelist = drives

        #only check predetermined iPod drive
        if main.local['ipoddrivename'] != "":
            if main.local['ipoddrivename'] in newdrives:
                newdrives = [main.local['ipoddrivename']]
        
        for drive in newdrives:
            #card readers and zip drives should fail here
            if sys.platform.startswith("win"):
                try:
                    volinfo = win32api.GetVolumeInformation(drive)
                except Exception, err:
                    log.warning("Not checking drive: %s %s" % (drive, err))
                    continue
            try:
                dirlist = os.listdir(drive)
                log.debug(repr(dirlist[:10]))
                #if dirlist == [] or dirlist == [u'.autodiskmounted']:
                #for Mac OS X
                if dirlist == [u'.autodiskmounted']:
                    #time.sleep(.1)
                    #dirlist = os.listdir(drive)
                    #we'll check again when it's ready
                    log.verb("Drive not ready yet")
                    self.drivelist.remove(drive)
            #except (WindowsError, OSError), err:
            except Exception, err:
                log.warning("Error checking drive %s: %s" % (drive,err))
                continue
            log.verb("Checking drive: %s" % drive)
            #if os.path.exists(os.path.join(drive,"iPod_Control")):
            check = 0
            for item in dirlist:
                if item.lower() == "itunes":
                    check += 1
                    continue
                if item.lower() == "mobile":
                    check += 1
                    continue
                if item.lower() == "lyrics":
                    check += 1
                    continue
            if check == 3:
                dirlist.append("iPod_Control")
                log.verb("Motorola phone found")
            if "iPod_Control" in dirlist:
                if not self.ipodmounted:
                    self.ipodmounted = True
                    self.ipodname = drive
                    log.verb("iPod volume mounted: %s" % drive)
                    self.updateonunmount = True
                    if self.prefs['ipodmultiple']:
                        try:
                            #if sys.platform.startswith("win"):
                                #shutil.copy(main.prefs['xmlfile'].encode("windows-1252"),os.path.join(self.mypath,"iTunes Music Library.xml"))
                            #   shutil.copy(main.prefs['xmlfile'].encode("mbcs"),os.path.join(self.mypath,"iTunes Music Library.xml"))
                            try:
                                shutil.copy(main.prefs['xmlfile'],os.path.join(self.mypath,"iTunes Music Library.xml"))
                            except:
                                if sys.platform.startswith("win"):
                                    shutil.copy(main.prefs['xmlfile'].encode("mbcs"),os.path.join(self.mypath,"iTunes Music Library.xml"))
                                else:
                                    log.error("Failed to copy XML file for multiple plays: [%s:%s]" % (sys.exc_info()[0],err))
                        except Exception, err:
                            log.error("Failed to copy XML file for multiple plays: [%s:%s]" % (sys.exc_info()[0],err))
                return

        if self.ipodname not in self.drivelist:
            if self.ipodmounted:
                self.ipodmounted = False
                self.ipodname = ""
                if main.prefs['ipodmanual']:
                    log.verb("Only checking for iPod played songs on selection of Update iPod")
                    return
                if self.updateonunmount:
                    log.verb("iPod volume unmounted, checking for iPod songs")
                    self.delayedipodcheck = int(time.time()) + 30
                else:
                    log.verb("iPod volume unmounted, already manually checked for iPod songs")

    def main(self):
        while 1:
            mtime = os.stat(self.mypath).st_mtime
            if mtime != self.lastmtime:
                log.debug("iTunes Library XML modified: %s" % time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(mtime)))
            self.lastmtime = mtime

            if self.ready():
                if s.pausesubmissions:
                    return
                if main.local['itunesenabled']:
                    self.core()
                for i in range(10):
                    if sys.platform.startswith("win"):
                        itunes.pumpevents()
                    if main.prefs['ipodsupport']:
                        self.ipodcheck()
                    time.sleep(1)

    def core(self):
        """The main routine."""
        if not main.local['itunesenabled']:
            return
        try:
            s.playingsong = itunes.getsong().copy()
            try:
                if s.playingsong[0] == "not_connected":
                    s.playingsong = None
                    if self.prefs['itunesinstall'] == False:
                        self.prefs['itunesinstall'] = True
                        MessageBox(0,"iTunes is not installed properly. Run the iTunes installer again and choose the 'Repair' option.","iSproggler",1)
            except KeyError:
                pass
            #this can be None if "not_connected" or due to a COM error
            if s.playingsong is None:
                return
            s.seekprotection()
            if s.handshaked:
                if s.submittable():
                    #we check the cache only when a song changes
                    if f.cachecheck():
                        log.verb("Cache not empty, adding playing song to cache instead of submitting")
                        s.addsongtocache()
                        s.submitcache()
                    else:
                        s.addsong()
                    f.songhistorywrite(s.playingsong.copy())
            elif s.submittable():
                #we check and cache iPod songs only on song changes
                s.addsongtocache()
                f.songhistorywrite(s.playingsong.copy())
        except AttributeError, err:
            #if nothing is playing in iTunes do nothing
            pass
        if not s.handshaked:
            if int(time.time()) - (s.lastshakeattempt) >= s.interval * 60:
                if s.handshake():
                    s.interval = 1
                else:
                    if s.interval == 64:
                        s.interval = 120
                    elif s.interval < 60:
                        s.interval *= 2
                    log.info("Handshake failure, retrying in %d minutes" % (s.interval))
        if s.handshaked:
            s.submitcache()


class LogBuffer:
    def __init__(self):
        pass

    def flush(self):
        sys.__stdout__.flush()

    def write(self,string):
        """To redirect httplib debug prints to STDERR so they are logged by py2exe."""
        string = string.strip()
        try:
            time.strptime(string[:10],"%Y-%m-%d")
            sys.__stdout__.write(string+"\n")
        except ValueError:
            if string != "":
                line = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())+log.utcoffset+" [STDERR] "+string+"\n"
                sys.stderr.write(line)


if __name__ == "__main__":
    main = Main()
    log = log.Log(True)

    main.setprefs()
    main.setlocal(local)
    main.lastmtime = os.stat(main.mypath).st_mtime
    _debug_ = main.local['debug']
    log._debug_ = _debug_

    s = Scrobbler()
    f = Files()
    mbid = mbid.MBID()

    if main.local['typelibmajor'] != "" and main.local['typelibminor'] != "":
        itunes = itunes.iTunesConnection(main.local['dispatchmode'], main.local['quitonitunesquit'], \
            main.local['forceitunesdialog'], int(main.local['typelibmajor']),int(main.local['typelibminor']))
    else:
        itunes = itunes.iTunesConnection(main.local['dispatchmode'], main.local['quitonitunesquit'], main.local['forceitunesdialog'])
    ipod = ipod.iPod(main.local['ignorepodcasts'],main.local['ignorevideopodcasts'],main.local['ignorevideos'])

    if not sys.argv[0].endswith(".exe") or main.local['httpdebug']:
        log.verb("Initialising LogBuffer() to redirect standard files")
        logbuffer = LogBuffer()
        sys.stdout = logbuffer

    if _build_ == 1:
        log.verb("Session started [%s]" % (_version_))
    elif _build_ < 0:
        log.verb("Session started [%s beta %s]" % (_version_,abs(_build_)))
    else:
        log.verb("Session started [%s build %s]" % (_version_,_build_))
    
    main.timecheck()

    if sys.platform.startswith("win"):
        s.submissionstate()

    if main.ready():
        main.initialhandshake()
    else:
        s.lastshakeattempt = int(time.time())

    if main.cli():
        main.main()
    else:
        log.verb("Starting system tray process")
        import gui
        gui._version_ = _version_
        gui._threaded_ = _threaded_
        gui.main = main
        gui.s = s
        gui.f = f
        gui.itunes = itunes

        #if _threaded_:
        #    thread.start_new_thread(main.main, ())
        
        app = gui.MyApp(0)
        app.MainLoop()
