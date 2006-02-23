#!/usr/bin/env python
# -*- coding: utf-8 -*-

#main.py/ipod.py

import time

def isotounix(timestamp, offset=0):
    # to handle times in the format "%Y-%m-%dT%H:%M:%SZ"
    timestamp = timestamp.replace("T"," ")[:19]
    temptime = time.strptime(str(timestamp),"%Y-%m-%d %H:%M:%S")
    #temptime = list(temptime)
    #temptime[8] = 0
    return int(time.mktime(temptime)) + offset

def tupletounix(tupletime, offset=0):
    #temptime = list(tupletime)
    #temptime[8] = 0
    return int(time.mktime(tupletime)) + offset

def isotoiso(timestamp, offset=0):
    return unixtoiso(isotounix(timestamp,offset))

def unixtoiso(timestamp, offset=0):
    timetuple = time.localtime(timestamp + offset)
    #timelist = list(timetuple)
    #timelist[8] = 0
    return time.strftime("%Y-%m-%d %H:%M:%S",timetuple)


if __name__ == "__main__":
    print time.daylight
    print time.timezone
    print time.tzname
    duration = 20
    print isotounix("2004-12-10 18:14:03")
    print unixtoiso(isotounix("2004-12-10 12:14:33",-(duration+5)))
    print isotoiso("2006-02-04 18:12:20")