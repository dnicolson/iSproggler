#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import commands


class AudionConnection:
    def __init__(self):
        self.track = None
        self.song = {}
        self.templastsong = {}
        self.tempplayingsong = {}

    def pumpevents(self):
        pass
    
    def cleanup(self):
        pass

    def getsong(self):
        """Retrieves song information from Audion."""
        applescript = """tell application "Audion 3"
                            set control_window to front control window

                            set this_name to track title of control_window
                            set this_artist to track artist of control_window
                            set this_album to track album of control_window
                            set this_name to track title of control_window
                            set this_name to track title of control_window
                            set this_name to track title of control_window
                            
                            set this_duration to 300 --fix
                            set this_position to elapsed seconds of control_window
                            set this_playcount to 0 --fix
                            set this_id to 0 --fix
                            set this_location to "file://localhost/" --fix
                            --set this_location to POSIX path of this_location --fix
                        end tell
                        return this_name & tab & this_artist & tab & this_album & tab & this_duration & tab & this_position & tab & this_playcount & tab & this_id & tab & this_location"""

        osa_output = unicode(commands.getoutput("osascript -e '%s'" % applescript),"utf-8")
        try:
            self.song['name'], self.song['artist'], self.song['album'], \
            self.song['duration'], self.song['position'], \
            self.song['playcount'], self.song['id'], self.song['location'] \
                = osa_output.split('\t')
            self.song['mbid'] = None

            self.song['id'] = int(self.song['id'])
            self.song['playcount'] = int(self.song['playcount'])
            self.song['position'] = int(self.song['position'])
            self.song['duration'] = int(self.song['duration'])

        except ValueError:
            return None

        return self.song

class DummyClass:
    def __init__(self):
        pass
        
    def checkipod(self,lastsong,prefs):
        return None


if __name__ == "__main__":
    import time
    itunes = AudionConnection()

    while 1:
        print itunes.getsong()
        for i in range(3):
            time.sleep(1)