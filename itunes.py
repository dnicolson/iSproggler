#!/usr/bin/env python
# -*- coding: utf-8 -*-

#C:\Python24\python C:\Python24\Lib\trace.py --ignore-dir=C:\Python24\ -t Z:\isproggler\itunes.py

import sys
import os

try:
    import pythoncom
    import win32com.client
    import win32api, win32con, win32process
    import gc
except ImportError:
    import commands

import log
log = log.Log()

if __name__ == "__main__":
    log._debug_ = True

class iTunesConnection:
    def __init__(self, dispatchmode="", quitonitunes=False, forceitunesdialog=False, major=1, minor=7):
        self.track = None
        self.song = {}
        self.templastsong = {}
        self.tempplayingsong = {}
        self.connected = False
        self.eventhandler = False
        self.quitdelay = 0
        self.dispatchmode = dispatchmode
        self.quitonitunes = quitonitunes
        self.forceitunesdialog = forceitunesdialog
        self.major = major
        self.minor = minor
        self.connectfailed = False
        
        self.xml_file = None
    
    def pumpevents(self):
        if self.eventhandler:
            pythoncom.PumpWaitingMessages()
            if self.Events.quit:
                if self.forceitunesdialog:
                    log.verb("Killing iTunes...")
                    self.killitunes()
                self.connected = False
                self.eventhandler = False
                self.Events.quit = False
                self.quitdelay = 3
                self.cleanup()
                if self.quitonitunes:
                    log.verb("Exiting...")
                    sys.exit()

    def killitunes(self):
        processes = win32process.EnumProcesses()
        for pid in processes:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
            except:
                pass
                #log.warning("Exception raised in win32api.OpenProcess(): [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))
            try:
                exe = win32process.GetModuleFileNameEx(handle, 0)
                if os.path.split(exe)[1].lower() == "itunes.exe":
                    handle = win32api.OpenProcess(1, False, pid)
                    win32api.TerminateProcess(handle, -1)
                    win32api.CloseHandle(handle)
                    log.verb("iTunes killed")
                    return
            except:
                log.warning("Exception raised quitting iTunes: [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))

    def cleanup(self):
        log.verb("Cleaning up iTunes connection...")
        try:
            pythoncom.CoUninitialize()
            pythoncom.CoFreeUnusedLibraries()
        except:
            log.warning("Exception raised cleaning up COM: [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))
        try:
            log.verb("Ref count [self.iTunes: %d, self.Events: %d]" % (sys.getrefcount(self.iTunes),sys.getrefcount(self.Events)))
            del self.Events
            del self.iTunes
            gc.collect()
        except:
            log.debug("Exception raised deleting COM objects: [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))

        log.verb("InterfaceCount: %s" % pythoncom._GetInterfaceCount())
        log.verb("GatewayCount: %s" % pythoncom._GetGatewayCount())

    def _dispatch(self,mode):
        if mode == "Dispatch":
            self.iTunes = win32com.client.Dispatch("iTunes.Application")
        elif mode == "dynamic.Dispatch":
            self.iTunes = win32com.client.dynamic.Dispatch("iTunes.Application")
        elif mode == "EnsureModule/Dispatch":
            win32com.client.gencache.EnsureModule('{9E93C96F-CF0D-43F6-8BA8-B807A3370712}', 0, self.major, self.minor)
            self.iTunes = win32com.client.Dispatch("iTunes.Application")
        elif mode == "EnsureDispatch":
            self.iTunes = win32com.client.gencache.EnsureDispatch("iTunes.Application")
        elif mode == "EnsureModule/EnsureDispatch":
            win32com.client.gencache.EnsureModule('{9E93C96F-CF0D-43F6-8BA8-B807A3370712}', 0, self.major, self.minor)
            self.iTunes = win32com.client.gencache.EnsureDispatch("iTunes.Application")
        else:
            raise TypeError, "Invalid _dispatch mode '%s'" % mode

    def createobject(self):
        win32com.client.gencache.is_readonly = False
        
        #for user defined dispatch
        if self.dispatchmode != "":
            log.verb("Trying _dispatch with mode '%s'" % self.dispatchmode)
            try:
                self._dispatch(self.dispatchmode)
                log.verb("iTunes connection initialised")
                if self.registerevents():
                    log.verb("Registered for iTunes Events")
                    try:
                        self.xml_file = self.iTunes.LibraryXMLPath
                        log.verb("iTunes Library file: %s" % self.xml_file)
                    except:
                        self.xml_file = None
                    return True
            except Exception, err:
                log.warning("Failed to create iTunes object using _dispatch '%s': [%s: %s]" % (self.dispatchmode,sys.exc_info()[0],err))
                self.cleanup()

        modes = ["Dispatch",
                 "dynamic.Dispatch",
                 "EnsureModule/Dispatch",
                 "EnsureDispatch",
                 "EnsureModule/EnsureDispatch"]
    
        for mode in modes:
            try:
                log.debug("Trying _dispatch with mode '%s'" % mode)
                self._dispatch(mode)
                log.verb("iTunes connection initialised")
                if self.registerevents():
                    log.verb("Registered for iTunes Events")
                    try:
                        self.xml_file = self.iTunes.LibraryXMLPath
                        log.verb("iTunes Library file: %s" % self.xml_file)
                    except:
                        self.xml_file = None
                    return True
                else:
                    #log.warning("Failed to register event handler using _dispatch '%s'" % mode)
                    song = {}
                    try:
                        track = self.iTunes.CurrentTrack
                        #required fields
                        song['name'] = track.Name
                        song['duration'] = int(track.Duration)
                        song['position'] = int(self.iTunes.PlayerPosition)
                        song['playcount'] = int(track.PlayedCount)
                        song['id'] = int(track.TrackDatabaseID)
                        #optional fields
                        song['artist'] = track.Artist
                        song['album'] = track.Album
                        song['genre'] = track.Genre
                    except Exception, err:
                        log.debug("iTunes test poll attempt failed: %s [%s: %s]" % (repr(song),sys.exc_info()[0],err))
                        continue
                    log.verb("iTunes test polling attempt after event handler failure: %s" % repr(song))
                    if len(song) > 0:
                        log.verb("Continuing without iTunes Events")
                        return True
            except Exception, err:
                log.error("Failed to create iTunes object using _dispatch '%s': [%s: %s]" % (mode,sys.exc_info()[0],err))
                self.cleanup()

        return False

    def registerevents(self):
        try:
            self.Events = win32com.client.WithEvents(self.iTunes, iTunesEvents)
            self.eventhandler = True
            return True
        except Exception, err:
            #log.warning("Failed to register event handler: [%s: %s]" % (sys.exc_info()[0],err))
            self.eventhandler = False
            self.Events = None
            return False

        #try:
        #    self.iTunes = win32com.client.DispatchWithEvents("iTunes.Application", iTunesEvents)
        #    self.Events = self.iTunes
        #    return True
        #except Exception, err:
        #    log.warning("Failed to register event handler: [%s: %s]" % (sys.exc_info()[0],err))

        self.Events = iTunesEvents()
        return False

    def connect(self):
        #we can't connect to iTunes' existing COM server as it isn't listed in the Running Object Table
        #try:
        if self.itunesrunning():
            pythoncom.CoInitialize()
            if self.createobject():
                self.connected = True
                return True
            else:
                log.error("iTunes object failed to be created, run the iTunes installer again")
                self.connectfailed = True
                self.connected = False
                return False
        else:
            log.verb("iTunes doesn't appear to be running, retrying later")
            self.connected = False
            self.eventhandler = False
            return False
        #except Exception, err:
        #    log.error("Failed to initialise iTunes communication: [%s: %s]" % (sys.exc_info()[0],err))
        #    self.connected = False
        #    pass
            
    def reinitialise(self):
        self.connected = False
        self.eventhandler = False
        self.cleanup()

    def itunesrunning(self):
        processes = win32process.EnumProcesses()
        for pid in processes:
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
            except:
                #log.warning("Exception raised in win32api.OpenProcess(): [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))
                continue
            try:
                exe = win32process.GetModuleFileNameEx(handle, 0)
                if os.path.split(exe)[1].lower() == "itunes.exe":
                    return True
            except:
                try:
                    pass #log.warning("Failed to get process name for PID: %d [%s]" % (pid,repr(handle)))
                except:
                    log.warning("Exception raised in win32process.GetModuleFileNameEx() try block: [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))
                #log.warning("Exception raised in win32process.GetModuleFileNameEx(): [%s: %s]" % (sys.exc_info()[0], sys.exc_info()[1]))
        return False

    def getsong(self):
        """Retrieves song information from iTunes."""
        try:
            log.debug("Ref count [self.iTunes: %d, self.Events: %d]" % (sys.getrefcount(self.iTunes),sys.getrefcount(self.Events)))
        except:
            pass
        if sys.platform.startswith("win"):
            try:
                #delay poll attempts after quitting to prevent reopening iTunes
                if self.quitdelay > 0:
                    log.debug("Delaying %d poll attempt" % self.quitdelay)
                    self.quitdelay -= 1
                    return
                if not self.connected:
                    if not self.connect() and self.connectfailed:
                        return {0: "not_connected"}
                if self.eventhandler:
                    if self.Events.suspended:
                        log.debug("iTunes activity suspended, returning with None")
                        return None
                track = self.iTunes.CurrentTrack
                try:
                    #required fields
                    self.song['name'] = track.Name
                    self.song['duration'] = int(track.Duration)
                    self.song['position'] = int(self.iTunes.PlayerPosition)
                    self.song['playcount'] = int(track.PlayedCount)
                    self.song['id'] = int(track.TrackDatabaseID)
                    #optional fields
                    self.song['artist'] = track.Artist
                    self.song['album'] = track.Album
                    self.song['genre'] = track.Genre
                    try:
                        self.song['location'] = win32com.client.CastTo(track,"IITFileOrCDTrack").Location
                    except:
                        #log.warning("Failed to cast to IITFileOrCDTrack, unable to get file location")
                        self.song['location'] = None
                    self.song['mbid'] = None
                except AttributeError:
                    return None
                try:
                    if track.Genre == "Podcast" or win32com.client.CastTo(track,"IITFileOrCDTrack").Podcast:
                        #self.song['duration'] = -1
                        self.song['genre'] = "Podcast"
                except:
                    #log.warning("Failed to cast to IITFileOrCDTrack, unable to check for podcast")
                    pass
                #iTunes Music Store previews
                if track.Kind == 3 and self.song['duration'] != 0:
                    self.song['duration'] = -2
                #videos, this will fail for videos in the Library and not Videos
                try:
                    if win32com.client.CastTo(track.Playlist,"IITUserPlaylist").SpecialKind == 5:
                        self.song['duration'] = -3
                except:
                    pass
            except pythoncom.com_error, err:
                if err[1].startswith("Invalid class string"):
                    log.error("Failure initialising connection with iTunes")
                    self.reinitialise()
                    return None
                if err[1].startswith("The object invoked has disconnected from its clients"):
                    log.verb("Re-initialising iTunes connection")
                    self.reinitialise()
                    return None
                if err[1].startswith("The RPC server is unavailable"):
                    log.verb("Re-initialising iTunes connection")
                    self.reinitialise()
                    return None
                if err[1].startswith("The server threw an exception"):
                    log.verb("Re-initialising iTunes connection")
                    self.reinitialise()
                    return None
                if err[1].startswith("Call was rejected"):
                    log.verb("Connection failure to iTunes, a modal dialog is probably displayed")
                    return None
                if err[1].startswith("Server execution failed"):
                    log.verb("iTunes appears to be busy")
                    return None
                log.error("COM error: %s" % err)
                self.reinitialise()
                return None

            return self.song
            
        elif sys.platform == "darwin":
            applescript = """tell application "iTunes"
                                set this_name to the name of current track
                                set this_artist to the artist of current track
                                set this_album to the album of current track
                                set this_duration to the duration of current track
                                set this_position to player position
                                set this_playcount to the played count of current track
                                set this_id to the database ID of current track
                                set this_location to the location of current track
                                set this_location to POSIX path of this_location
                                set this_genre to genre of current track
                            end tell
                            return this_name & tab & this_artist & tab & this_album & tab & this_duration & tab & this_position & tab & this_playcount & tab & this_id & tab & this_location & tab & this_genre"""
    
            osa_output = unicode(commands.getoutput("osascript -e '%s'" % applescript),"utf-8")
            try:
                self.song['name'], self.song['artist'], self.song['album'], \
                self.song['duration'], self.song['position'], \
                self.song['playcount'], self.song['id'], self.song['location'], self.song['genre'] \
                    = osa_output.split('\t')
                self.song['mbid'] = None

                self.song['id'] = int(self.song['id'])
                self.song['playcount'] = int(self.song['playcount'])
                self.song['position'] = int(self.song['position'])
                self.song['duration'] = int(float(self.song['duration']))

            except ValueError:
                return None

            return self.song
        else:
            return None

class iTunesEvents:
    def __init__(self):
        self.suspended = False
        self.quit = False
        self.playing = False
        self.stopped = False
        self.suspendedreason = ""

    def OnAboutToPromptUserToQuitEvent(self):
        log.verb("iTunes Event: About to quit")
        log.verb("Ignore warning dialog in iTunes if displayed")
        self.quit = True

    def OnQuittingEvent(self):
        log.verb("iTunes Event: Quitting")
        self.quit = True

    def OnCOMCallsDisabledEvent(self,code):
        if code == 0:
            reason = "COM interface is being disabled for some other reason"
        elif code == 1:
            reason = "COM interface is being disabled because a modal dialog is being displayed"
        elif code == 2:
            #reason = "COM interface is being disabled because iTunes is quitting"
            self.quit = True
            return
        else:
            reason = "Reason unavailable"
        if not self.quit:
            log.verb("iTunes Event: Connection suspended [%s: %s]" % (code, reason))
        self.suspended = True
        self.suspendedreason = reason

    def OnCOMCallsEnabledEvent(self):
        if not self.quit:
            log.verb("iTunes Event: Connection resumed")
        self.suspended = False

    def OnPlayerPlayEvent(self,track):
        try:
            track = win32com.client.CastTo(track, "IITTrack")
            log.verb("iTunes Event: \"%s\" playing" % track.Name)
        except Exception, err:
            pass
            #log.warning("Failed to cast to IITTrack for OnPlayerPlayEvent: %s" % err) 
        self.playing = True
        self.stopped = False

    def OnPlayerStopEvent(self,track):
        try:
            track = win32com.client.CastTo(track, "IITTrack")
            log.verb("iTunes Event: \"%s\" stopped" % track.Name)
        except Exception, err:
            pass
            #log.warning("Failed to cast to IITTrack for OnPlayerStopEvent: %s" % err)
        self.stopped = True
        self.playing = False
    
    def OnPlayerPlayingTrackChangedEvent(self,track):
        try:
            track = win32com.client.CastTo(track, "IITTrack")
            log.verb("iTunes Event: Song information changed for \"%s\"" % track.Name)
        except Exception, err:
            pass
            #log.warning("Failed to cast to IITTrack for OnPlayerPlayingTrackChangedEvent: %s" % err)


if __name__ == "__main__":
    import time
    itunes = iTunesConnection()
    if sys.platform.startswith("win"):
        itunes.connect()

    try:
        while 1:
            print itunes.getsong()
            for i in range(10):
                if sys.platform.startswith("win"):
                    itunes.pumpevents()
                time.sleep(1)
    except KeyboardInterrupt:
        print "Interrupt"
        itunes.cleanup()