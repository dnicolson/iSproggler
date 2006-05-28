#!/usr/bin/env python

from sys import exc_info
import struct
import log

if __name__ == "__main__":
    log._debug_ = True

log = log.Log()

class MBID:
    def __init__(self):
        pass

    def _toSynchSafe(self,bytes):
        (s0, s1, s2, s3) = struct.unpack("!4b",bytes)
        return (s0 << 21) + (s1 << 14) + (s2 << 7) + s3
               
    def _toInteger(self,bytes):
        size = 0
        for n in struct.unpack("!4B",bytes):
            size = size * 256 + n
        return size

    def getMBID(self,location):
        try:
            mfile = open(location,"rb")
        except (IOError,EOFError), err:
            log.error("Failed to open music file: %s [%s]" % (location,err))
            return
    
        if mfile.read(3) != "ID3":
            log.debug("No ID3v2 tag found: %s" % location)
            return
        
        (v0, v1) = struct.unpack("!2b",mfile.read(2))
        if v0 == 2:
            log.debug("ID3v2.2.0 does not support MBIDs: %s" % location)
            return
        
        if v0 != 3 and v0 != 4:
            log.debug("Unsupported ID3 version: v2.%d.%d" % (v0,v1))
            return
        
        (flag,) = struct.unpack("!b",mfile.read(1))
        if flag & 0x00000040:
            log.debug("Extended header found")
            if v0 == 3:
                size_extended = self._toInteger(mfile.read(4))
            else:
                size_extended = self._toSynchSafe(mfile.read(4))
            log.debug("Extended header size: %d" % size_extended)
            mfile.seek(size_extended,1)
    
        (s0, s1, s2, s3) = struct.unpack("!4b",mfile.read(4))
        size = (s0 << 21) + (s1 << 14) + (s2 << 7) + s3
        log.debug("Tag size: %d" % size)
    
        while 1:
            if mfile.tell() > size or mfile.tell() > 1048576:
                break
            frame = mfile.read(4)
            if frame[0] == "\x00":
                break
            if v0 == 3:
                frame_size = self._toInteger(mfile.read(4))
            else:
                frame_size = self._toSynchSafe(mfile.read(4))

            mfile.seek(2,1)
            log.debug("Reading %d bytes from frame %s" % (frame_size,frame))

            if frame == "UFID":
                frame_data = mfile.read(frame_size)
                if frame_data.startswith("http://musicbrainz.org"):
                    mbid = frame_data[-36:]
                    return mbid
            else:
                mfile.seek(frame_size,1)
    
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print MBID().getMBID(sys.argv[1])
    else:
        import os
        for path in os.listdir("/Users/dave/Projects/Python/MBID Test/"):
            print MBID().getMBID(os.path.join("/Users/dave/Projects/Python/MBID Test/",path))
            print