#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import codecs
import re
import gc
import urllib
import traceback

import log
import times

if sys.platform.startswith("win"):
    import win32api
    from win32com.client import CastTo
    from win32gui import MessageBox

if __name__ == "__main__":
    log._debug_ = True
    import main

log = log.Log()


class iPod:
    def __init__(self,ignorepodcasts=True,ignorevideopodcasts=True,ignorevideos=True):
        self.ignorepodcasts = ignorepodcasts
        self.ignorevideopodcasts = ignorevideopodcasts
        self.ignorevideos = ignorevideos
        if sys.platform.startswith("win"):
            #self.mypath = os.getenv("USERPROFILE") + "\\Application Data\\iSproggler\\"
            self.mypath = os.path.join(os.getenv("APPDATA"),"iSproggler")
        elif sys.platform == "darwin":
            self.mypath = os.path.expanduser("~") + "/.iSproggler/"
        try:
            os.remove(os.path.join(self.mypath,"iTunes Music Library.xml"))
            log.debug("Deleted old multiple plays XML")
        except:
            pass

    def _gettracks(self,xmlfile):
        if not os.path.exists(xmlfile):
        	log.warning("XML library file does not exist")
        	return None
        try:
            xml = codecs.open(xmlfile,"rb","utf-8","replace").read()
        except (IOError, EOFError, UnicodeDecodeError), err:
            log.error("An error occurred trying to open the XML file: %s [%s]" % (xmlfile,err))
            log.error("\n".join(traceback.format_tb(sys.exc_info()[2])))
            return None
        matches = re.findall("(?xms)Tracks</key>.*?<dict>(.*)<key>Playlists(.*?)</plist>", xml)
        del xml
        songsxml = matches[0][0]
        #playlists = matches[0][1]
        del matches
        return songsxml
    
    def _songlist(self,songsxml):
        library = {}
        allsongs = re.findall("(?xms)<dict>(.*?)</dict>", songsxml)
        for song in allsongs:
            songinfo = re.findall("(?xms)<key>(.*?)</key>(.*?/.*?>)", song)
            #songid = int(songinfo[0][1])
            songid = None
            for attr in songinfo:
                if attr[0] == "Persistent ID":
                    songid = attr[1][8:-9]
            if songid is None:
                log.debug("Persistent ID not found in _songlist: "+repr(songinfo))
                songid = int(songinfo[0][1][9:-10])
            library[songid] = {}
            for field in songinfo:
                if field[1] == "<true/>":
                    library[songid][field[0]] = True
                elif field[1] == "<false/>":
                    library[songid][field[0]] = False
                else:
                    try:
                        library[songid][field[0]] = re.findall("(?xms)<.*?>(.*?)</.*?>",field[1])[0]
                    except IndexError:
                        log.warning("Unable to parse field: %s" % repr(field))
        del allsongs
        return library

    def _formatlocation(self,location):
        location = location.encode("utf-8").replace(":","%3A")
        location = urllib.url2pathname(location).replace("&#38;","&")
        if location.startswith("file://"):
            location = location[16:]
        elif location.startswith("file:\\\\"):
            location = location[17:]
        return unicode(location,"utf-8")

    def _parsesongs(self,library):
        ipodsongs = []
        for song in library:
            try:
                library[song]['Play Date UTC']

                try:
                    if times.isotounix(library[song]['Play Date UTC']) > times.isotounix(self.templastsong['time'],(self.templastsong['duration']+10)):
                        librarysong = library[song]
                        tempsong = {}
                        try:
                            tempsong['name'] = librarysong['Name'].replace("&#38;","&").replace("&#62;","<").replace("&#60;",">")

                        except KeyError:
                            continue
                        try:
                            tempsong['album'] = librarysong['Album'].replace("&#38;","&").replace("&#62;","<").replace("&#60;",">")

                        except KeyError:
                            log.debug("No album key found for the song \"%s\"" % tempsong['name'])
                            tempsong['album'] = ""
                        try:
                            librarysong['Podcast']
                            if self.ignorepodcasts:
                                log.verb("\"%s\" disqualified because it is a podcast" % tempsong['name'])
                                continue
                            try:
                                librarysong['Has Video']
                                if self.ignorevideopodcasts:
                                    log.verb("\"%s\" disqualified because it is a video podcast" % tempsong['name'])
                                    continue
                            except KeyError:
                                pass
                        except KeyError:
                            pass
                        try:
                            librarysong['Has Video']
                            if self.ignorevideos:
                                log.verb("\"%s\" disqualified because it is a video" % tempsong['name'])
                                continue
                        except KeyError:
                            pass
                        try:
                            tempsong['location'] = self._formatlocation(librarysong['Location'])
                        except KeyError:
                            log.warning("No location available for \"%s\" [%s]" % (tempsong['name'],repr(librarysong)))
                            tempsong['location'] = None
                        try:
                            try:
                                tempsong['id'] = librarysong['Persistent ID']
                            except KeyError:
                                log.debug("Persistent ID not found in _parsesongs: "+repr(librarysong))
                                tempsong['id'] = librarysong['Track ID']
                            tempsong['artist'] = librarysong['Artist'].replace("&#38;","&").replace("&#62;","<").replace("&#60;",">")

                            tempsong['duration'] = int(librarysong['Total Time']) / 1000
                            tempsong['playcount'] = int(librarysong['Play Count'])
                            #tempsong['time'] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(int(time.mktime(time.strptime(str(librarysong['Play Date UTC']),"%Y-%m-%dT%H:%M:%SZ")))-int(tempsong['duration'])))
                            tempsong['time'] = times.isotoiso(librarysong['Play Date UTC'],-tempsong['duration'])
                        except KeyError, err:
                            log.error("%s field not found for the song \"%s\", voiding song" % (err,tempsong['name']))
                            continue
                        try:
                            tempsong['genre'] = librarysong['Genre']
                        except:
                            tempsong['genre'] = ""
                        tempsong['mbid'] = None
                        #disqualify any song played more than four weeks ago
                        if times.isotounix(library[song]['Play Date UTC']) < time.mktime(time.gmtime()) - (28 * 24 * 60 * 60):
                            log.warning("\"%s\" by %s disqualified as it is played more than four weeks ago [%s UTC]" % (tempsong['name'],tempsong['artist'],tempsong['time']))
                            continue

                        #exclude rules
                        if len(self.local['exclude_dir']) > 0:
                            for path in self.local['exclude_dir']:
                                if tempsong['location'].startswith(path):
                                    log.verb("\"%s\" by %s will not be submitted as it resides in an excluded path [%s]" % (tempsong['name'], tempsong['artist'],path))
                                    continue
                        if len(self.local['exclude_artist']) > 0:
                            for artist in self.local['exclude_artist']:
                                if tempsong['artist'] == artist:
                                    log.verb("\"%s\" by %s will not be submitted as it an excluded artist [%s]" % (tempsong['name'], tempsong['artist'],artist))
                                    continue
                        if len(self.local['exclude_genre']) > 0:
                            for genre in self.local['exclude_genre']:
                                if tempsong['genre'] == genre:
                                    log.verb("\"%s\" by %s will not be submitted as it an excluded genre [%s]" % (tempsong['name'], tempsong['artist'],genre))
                                    continue

                        ipodsongs.append(tempsong)
                except Exception, err:
                    log.error("\n".join(traceback.format_tb(sys.exc_info()[2])))
                    log.error("An error occurred reading the parsed XML file: %s: %s" % (sys.exc_info()[0],err))
            except:
                #unplayed songs
                pass
        return ipodsongs

    def retrievesongs(self,xmlfile):
        log.verb("Looking for songs in Library played after \"%s\" at %s UTC" % (self.templastsong['name'],self.templastsong['time']))

        starttime = time.time()
        
        songsxml = self._gettracks(xmlfile)
        if songsxml is None:
        	return None
        library = self._songlist(songsxml)
        del songsxml

        totaltime = time.time() - starttime     
        log.debug("XML file parsed in %f seconds" % totaltime)
        starttime = time.time()
        
        ipodsongs = self._parsesongs(library)
        del library
        
        totaltime = time.time() - starttime     
        log.debug("Library checked in %f seconds" % totaltime)

        if gc.isenabled():
            log.debug("Garbage collection enabled")
        gc.collect()

        return ipodsongs
    
    def _adjusttimes(self,songs):
        """Adjusts timestamps to make room for multiple iPod plays."""
        log.verb("iPod songs before time adjustment:")
        for song in songs:
            log.verb("%s UTC (%s)\t%s\t%s" % (song['time'],song['duration'],song['playcount'],song['name']))
        timestamp = self.firstipod
        last_ipod = songs[-1]['time']
        for song in songs:
            #print song['time'], times.isotounix(timestamp), "(",times.isotounix(song['time']),times.isotounix(timestamp), ")"
            if times.isotounix(song['time']) < times.isotounix(timestamp):
                timestamp = song['time']
                log.verb("Earlier timestamp found, possibly due to many plays of a single song")
        #log.verb("First iPod-played song: %s UTC, target first song: %s UTC" % (self.firstipod,timestamp))
        newsongs = []
        first = True
        for song in songs:
            if first:
                #use the earliest possible timestamp
                song['time'] = timestamp
                first = False
            else:
                #now start adding the duration of the previous song 
                timestamp = times.isotoiso(timestamp,lastsong['duration'])
                song['time'] = timestamp
            lastsong = song
            if times.isotounix(song['time']) < times.isotounix(self.lastitunes):
                log.warning("\"%s\" by %s has a calculated play date before the last submission, not queueing [last submission: %s UTC, time: %s UTC]" % (song['name'],song['artist'],self.lastitunes,song['time']))
                continue
            if times.isotounix(song['time']) > int(time.mktime(time.gmtime())):
                log.warning("\"%s\" by %s has a calculated play date in the future, not queueing [current time: %s UTC, time: %s UTC]" % (song['name'],song['artist'],time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime()),song['time']))
                continue
            newsongs.append(song)
        
        log.verb("Original last played epoch: %s Adjusted last played epoch: %s" % (last_ipod,newsongs[-1]['time']))
        #newsongs[-1]['time'] = songs[-1]['time']
        newsongs[-1]['time'] = last_ipod
                
        log.verb("iPod songs after time adjustment:")
        for song in newsongs:
            log.verb("%s UTC (%s)\t%s\t%s" % (song['time'],song['duration'],song['playcount'],song['name']))
        return newsongs
    
    def checkmultiple(self,ipodsongs,multiplexml=None):
        log.verb("Checking for multiple iPod plays for %d song%s" % (len(ipodsongs),self._pluralise(len(ipodsongs))))
        if multiplexml is None:
            songsxml = self._gettracks(os.path.join(self.mypath,"iTunes Music Library.xml"))
        else:
            songsxml = self._gettracks(multiplexml)
        if songsxml is None:
            log.warning("XML file was copied but failed to be opened, multiple plays will be not be available")
            return ipodsongs
        library = self._songlist(songsxml)
        del songsxml
        songs = []
        multiple = False
        multiplecount = 0

        #if ipodsongs[0]['name'] != library[ipodsongs[0]['id']]['Name']:
        #    log.warning("ID mismatch, catching on multiple iPod plays")
        #    return False

        for ipodsong in ipodsongs:
            try:
                preupdatesong = library[ipodsong['id']]
            except KeyError:
                log.warning("\"%s\" by %s [%s] not found in XML file" % (ipodsong['name'],ipodsong['artist'],ipodsong['id']))
                songs.append(ipodsong)
                continue
            try:
                preupdateplay = int(preupdatesong['Play Count'])
            except KeyError:
                #log.warning("\"%s\" by %s [%s] unable to be checked for multiple plays, no original play count found" % (ipodsong['name'],ipodsong['artist'],ipodsong['id']))
                #songs.append(ipodsong)
                #continue
                preupdateplay = 0
            
            postupdateplay = int(ipodsong['playcount'])
            
            log.verb("Pre: %s Post: %s Name: \"%s\" [%s]" % (preupdateplay,postupdateplay,ipodsong['name'],ipodsong['id']))
            log.debug("Pre song: %s" % repr(preupdatesong))
            log.debug("Post song: %s" % repr(ipodsong))
            
            if preupdateplay > postupdateplay:
                log.warning("Play count is lower after iPod update for \"%s\" [before: %d, after: %d]" % (ipodsong['name'],preupdateplay,postupdateplay))
                songs.append(ipodsong)
                continue
            if preupdateplay != postupdateplay:
                songs.append(ipodsong)
                playcountdiff = postupdateplay - preupdateplay
                #normalise the earliest timestamp, subtract to the earliest possible timestamp
                multiplesongcount = 0
                for i in range(1,playcountdiff):
                    multiplesongcount += 1
                    multiple = True
                    multiplecount += 1
                    log.verb("Adding a play count for \"%s\" (%d)" % (ipodsong['name'],i+1))
                    #here we replicate playcounts to avoid duplicate songs in cache
                    tempsong = ipodsong.copy()
                    tempsong['playcount'] = int(ipodsong['playcount']) - i
                    tempsong['time'] = times.isotoiso(tempsong['time'],-(tempsong['duration'] * multiplesongcount))
                    songs.insert(0,tempsong)
            else:
                songs.append(ipodsong)

        del library

        try:
            os.remove(os.path.join(self.mypath,"iTunes Music Library.xml"))
        except:
            pass
 
        if multiple:
            log.verb("%d extra play%s added to submission queue" % (multiplecount,self._pluralise(multiplecount)))
            return self._adjusttimes(songs)
        else:
            log.verb("No songs played more than once found")
            return ipodsongs

    def processipodsongs(self, rawsongs):
        ipodsongs = []
        
        for rawsong in rawsongs:
            if rawsong['artist'] == "":
                log.verb("\"%s\" by %s disqualified because no artist is available" % (rawsong['name'],rawsong['artist']))
                continue
            #if rawsong['duration'] < 30:
            #    log.verb("\"%s\" by %s disqualified because the duration is less than 30 seconds" % (rawsong['name'],rawsong['artist']))
            #    continue
            if rawsong['genre'] == "Podcast" and self.ignorepodcasts:
                log.verb("\"%s\" by %s disqualified because it is a podcast" % (rawsong['name'],rawsong['artist']))
                continue
            #if rawsong['id'] == self.templastsong['id']:
            #    log.verb("\"%s\" by %s being skipped as we're looking for songs after it" % (rawsong['name'],rawsong['artist']))
            #    continue
            #if rawsong['id'] == self.tempplayingsong['id']:
            #    log.verb("\"%s\" by %s disqualified because of overflow in the playing song" % (rawsong['name'],rawsong['artist']))
            #    continue                
            else:
                ipodsongs.append(rawsong.copy())

        return self._sortdictlist(ipodsongs)

    def _sortdictlist(self,songs):
        sorted = map(lambda x, key="time": (x['time'], x), songs)
        sorted.sort()
        return map(lambda (key, x): x, sorted)

    def _shuffleindex(self,songs):
        """Returns the index where shuffle songs meet regular songs."""
        lasttime = None
        index = 0
        first = True
        
        if songs[::-1][0]['time'] != songs[::-1][1]['time']:
            log.debug("No two play dates the same -- no iPod shuffle songs")
            return None
        for song in songs[::-1]:
            #last two played songs have the same timestamp
            if song['time'] != lasttime and index > 0:
                #support for updates spanning to timestamps
                if first:
                    #ignore the first batch of identical timestamps
                    log.verb("First instance of unique timestamps: [%d: %s UTC]" % (index, lasttime))
                    first = False
                    lasttime = song['time']
                    continue
                if song['time'] != lasttime:
                    #on second series of identical timestamps recognise shuffle
                    log.verb("Final instance of unique timestamps: [%d: %s UTC]" % (index, lasttime))
                    return index
                lasttime = song['time']
                index += 1
            lasttime = song['time']
            index += 1
            #if song['time'] != lasttime and index > 0:
            #    return index
            #lasttime = song['time']
            #index += 1
        return len(songs)
    
    def _addduration(self,songs):
        """Adds duration to make duplicate original iTunes timestamps."""
        newsongs = []
        for song in songs:
            #song['time'] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(int(time.mktime(time.strptime(str(song['time']),"%Y-%m-%d %H:%M:%S")) + song['duration'])))
            song['time'] = times.isotoiso(song['time'],song['duration'])
            newsongs.append(song)
        return newsongs
    
    def shufflecheck(self,songs):
        """Subtracts recursively the duration of the shuffle songs."""
        if len(songs) == 1:
            return songs
        sortedsongs = self._sortdictlist(songs)
        index = self._shuffleindex(self._addduration(sortedsongs))
        if index is not None:
            log.verb("Found %d iPod shuffle played songs" % index)
            newsongs = []
            recduration = 0
            
            for song in songs[::-1][0:index]:
                recduration += song['duration']
                #song['time'] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(int(time.mktime(time.strptime(str(song['time']),"%Y-%m-%d %H:%M:%S")) - recduration)))
                song['time'] = times.isotoiso(song['time'],-recduration)
                log.debug("iPod shuffle: \"%s\" [%s] %s UTC" % (song['name'],song['duration'],song['time']))
                if times.isotounix(song['time']) < times.isotounix(self.templastsong['time']):
                    log.warning("\"%s\" by %s has a calculated play date before last date in iTunes, not queueing" % (song['name'],song['artist']))
                    continue
                newsongs.append(song)
            for song in songs[::-1][index:]:
                #song['time'] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(int(time.mktime(time.strptime(str(song['time']),"%Y-%m-%d %H:%M:%S")) - song['duration'])))
                song['time'] = times.isotoiso(song['time'],-song['duration'])
                log.debug("iPod: \"%s\" [%s] %s UTC" % (song['name'],song['duration'],song['time']))
                newsongs.append(song)
            return newsongs
        return songs
        
    def _pluralise(self,integer):
        if integer == 1:
            return ""
        else:
            return "s"

    def checkipod(self,lastsong,prefs,local,multiplexml=None):
        """Checks the Library for songs played after the last played iSproggler song."""
        self.local = local
        self.templastsong = lastsong.copy()
        
        try:
            rawsongs = self.retrievesongs(prefs['xmlfile'])
        except Exception, err:
            log.error("\n".join(traceback.format_tb(sys.exc_info()[2])))
            log.error("An error occurred retrieving iPod songs from the XML file: %s: %s" % (sys.exc_info()[0],err))
            return None

        try:
            if rawsongs is None:
                return None
            ipodsongs = self.processipodsongs(rawsongs)
        except Exception, err:
            log.error("An error occurred processing iPod songs: %s: %s" % (sys.exc_info()[0],err))
            log.error("\n".join(traceback.format_tb(sys.exc_info()[2])))
            return None

        if len(ipodsongs) < 1 or ipodsongs is None:
            log.verb("Found no songs in Library played after %s UTC" % (self.templastsong['time']))
            return None

        try:
            ipodsongs = self.shufflecheck(ipodsongs)
        except Exception, err:
            log.error("\n".join(traceback.format_tb(sys.exc_info()[2])))
            log.error("An error occurred checking iPod shuffle songs: %s: %s" % (sys.exc_info()[0],err))

        if prefs['ipodmultiple']:
            self.lastitunes = self.templastsong['time']
            self.lastitunesname = self.templastsong['name']
            self.firstipod = ipodsongs[0]['time']
            self.firstipodname = ipodsongs[0]['name']
            self.playinggap = times.isotounix(self.firstipod) - times.isotounix(self.lastitunes)
            log.verb("Last iTunes play: %s UTC \"%s\"" % (self.lastitunes, self.lastitunesname))
            log.verb("Last iTunes play duration: %s " % (self.templastsong['duration']))
            log.verb("Playing gap: %s" % (times.isotounix(self.firstipod) - (times.isotounix(self.lastitunes) + self.templastsong['duration'])))
            log.verb("First iPod play: %s UTC \"%s\"" % (self.firstipod, self.firstipodname))
            try:
                ipodsongs = self.checkmultiple(ipodsongs,multiplexml)
            except Exception, err:
                log.error("\n".join(traceback.format_tb(sys.exc_info()[2])))
                log.error("An error occurred processing multiple iPod songs: %s: %s" % (sys.exc_info()[0],err))

        log.debug("Found %d iPod song%s" % (len(ipodsongs),self._pluralise(len(ipodsongs))))
        if len(ipodsongs) > 0:
            return ipodsongs
        else:
            log.verb("Found 0 iPod songs after disqualifications")
            return None

    def _enumplaylist(self,tracks):
        ipodsongs = []
        for track in tracks:
            song = {}
            try:
                song['duration'] = int(track.Duration)
                song['time'] = time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(int(time.mktime(time.strptime(str(track.PlayedDate),"%m/%d/%y %H:%M:%S")))-int(song['duration'])))
            except ValueError:
                #song in playlist without played date
                #MessageBox(0,"A song was found without a played date in the Smart Playlist.\n\nPlease set it up with a condition Last Played in the last 2 weeks.","iSproggler",1)
                log.warning("The song \"%s\" does not have a played date, the Smart Playlist needs a Last Played condition" % track.Name)
                continue
            except AttributeError:
                log.warning("Required attributes: Duration, PlayedDate not available -- discarding track [%s]" % repr(dir(track)))
                continue
                
            if times.isotounix(song['time']) > times.isotounix(self.lastsong['time'],+10):
                #required fields
                song['name'] = track.Name
                song['playcount'] = int(track.PlayedCount)
                song['id'] = int(track.TrackDatabaseID)
                
                #optional fields
                try:
                    song['artist'] = track.Artist
                except AttributeError:
                    song['artist'] = ""
                
                #disqualify any song played more than four weeks ago
                if times.isotounix(song['time']) < time.mktime(time.gmtime()) - (28 * 24 * 60 * 60):
                    log.warning("\"%s\" by %s disqualified as it is played more than four weeks ago [%s UTC]" % (song['name'],song['artist'],song['time']))
                    continue
                
                if song['artist'] == "":
                    log.verb("\"%s\" disqualified because no artist is available" % song['name'])
                    continue

                try:
                    song['album'] = track.Album
                except AttributeError:
                    song['album'] = ""
                try:
                    song['genre'] = track.Genre
                except AttributeError:
                    song['genre'] = ""
                
                #try:
                #    song['location'] = CastTo(track,"IITFileOrCDTrack").Location
                #except:
                #    song['location'] = None
                #    log.warning("No location available for \"%s\"" % song['name'])
                song['location'] = None

                if song['duration'] < 30:
                    log.verb("\"%s\" by %s disqualified because the duration is less than 30 seconds" % (song['name'],song['artist']))
                    continue
                    
                #exclude rules
                if len(self.local['exclude_artist']) > 0:
                    for artist in self.local['exclude_artist']:
                        if song['artist'] == artist:
                            log.verb("\"%s\" by %s will not be submitted as it an excluded artist [%s]" % (song['name'], song['artist'],artist))
                            continue
                if len(self.local['exclude_genre']) > 0:
                    for genre in self.local['exclude_genre']:
                        if song['genre'] == genre:
                            log.verb("\"%s\" by %s will not be submitted as it an excluded genre [%s]" % (song['name'], song['artist'],genre))
                            continue
                    
                try:
                    if song['genre'] == "Podcast" or win32com.client.CastTo(track,"IITFileOrCDTrack").Podcast:
                        if self.ignorepodcasts:
                            log.verb("\"%s\" disqualified because it is a podcast" % song['name'])
                            continue
                except:
                    #log.warning("Failed to cast to IITFileOrCDTrack, unable to check for Podcast")
                    pass

                song['mbid'] = None

                ipodsongs.append(song.copy())

        self.playlisttracks = ipodsongs
        
        if len(ipodsongs) > 0:
            return True
        else:
            return None
        
    def manual(self,lastsong,iTunes,local):
        self.local = local
        ipodplaylist = local['playlistname']
        self.lastsong = lastsong.copy()
        log.verb("Looking for playlist \"%s\" in iPod sources" % ipodplaylist)
        for source in iTunes.Sources._NewEnum():
            if source.Kind == 2:
                log.verb("iPod source found: %s" % source.Name)
                try:
                    playlist = source.Playlists.ItemByName(ipodplaylist)
                except AttributeError:
                    log.warning("Playlist \"%s\" not found on %s" % (ipodplaylist,source.Name))
                    continue
                try:
                    tracks = playlist.Tracks
                except AttributeError:
                    MessageBox(0,"The Smart Playlist \"%s\" was not found on any iPod sources" % (ipodplaylist),"iSproggler",1)
                    log.warning("Playlist object \"%s\" not found on %s" % (ipodplaylist,source.Name))
                    continue                
                log.verb("iPod playlist found: %s" % ipodplaylist)
                log.verb("Looking for songs in playlist played after \"%s\" at %s UTC" % (self.lastsong['name'],self.lastsong['time']))
                if self._enumplaylist(tracks) is not None:
                    return self._sortdictlist(self.playlisttracks)
                else:
                    log.verb("No iPod played songs found in playlist \"%s\" on %s" % (ipodplaylist,source.Name))
        return None


if __name__ == "__main__":
    ipod = iPod()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "manual":
            import itunes
            itunes = itunes.iTunesConnection()
            itunes.createobject()
            print ipod.manual({'name': u'Volte-Face','time': "2006-04-11 00:24:37"},"Recently Played",itunes.iTunes,main.local)
        if sys.argv[1] == "multiple":
            lastsong = {'album': u"Chunga's Revenge", 'name': u'Sharleena', 'artist': u'Frank Zappa', 'mbid': None, 'location': u"/Volumes/Fire/Music/iTunes/iTunes Music/Frank Zappa/Chunga's Revenge/10 Sharleena.mp3", 'duration': 244, 'position': 37, 'playcount': 1, 'id': 14652}
            #lastsong['time'] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.mktime(time.gmtime()) - 25 * 60 * 60))
            lastsong['time'] = '2007-03-29 06:32:45'
            
            ipod.checkipod(lastsong,{'xmlfile': "/Users/dave/Desktop/iTunes Music Library2.xml", 'ipodmultiple': True},main.local,"/Users/dave/Desktop/iTunes Music Library1.xml")
    else:
        lastsong = {'album': u"Chunga's Revenge", 'name': u'Sharleena', 'artist': u'Frank Zappa', 'mbid': None, 'location': u"/Volumes/Fire/Music/iTunes/iTunes Music/Frank Zappa/Chunga's Revenge/10 Sharleena.mp3", 'duration': 244, 'position': 37, 'playcount': 1, 'id': 14652, 'time': "2006-02-10 01:54:37"}#2005-12-03 07:54:37 UTC     --- 2005-12-04T02:01:30Z
        #playingsong = {'album': u'Second Life Syndrome', 'name': u'Volte-Face', 'artist': u'Riverside', 'mbid': None, 'location': u'/Volumes/Fire/Music/iTunes/iTunes Music/Riverside/Second Life Syndrome/02 Volte-Face.mp3', 'duration': 520, 'position': 419, 'playcount': 14, 'id': 14955, 'time': "2005-12-04 02:39:28"}#2005-12-04T02:48:08Z
        #xmlfile = "/Users/dave/Music/iTunes/iTunes Music Library.xml"
        xmlfile = "C:\\Documents and Settings\\Dave\\My Documents\\My Music\\iTunes\\iTunes Music Library.xml"
    
        import shutil
        #shutil.copyfile(xmlfile,"/Users/dave/.isproggler/iTunes Music Library.xml")
        shutil.copyfile(xmlfile,"C:\\Documents and Settings\\Dave\\Application Data\\iSproggler\\iTunes Music Library.xml")
        ipod.checkipod(lastsong,{'xmlfile': xmlfile, 'ipodmultiple': True})
