#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The only required part of this script is the setup tuple

# Change this to the root location
#root = "Z:\\iSproggler"
#root = "C:\\isproggler"

# The following extensions are required

"""http://starship.python.net/~skippy/win32/Downloads.html
http://www.py2exe.org/
http://www.wxpython.org/"""

deployment = True

from distutils.core import setup
import py2exe
import sys
import os
import shutil
import main
from initimages import initimages
import tarfile
import zipfile

root = os.path.split(sys.argv[0])[0]
print "Root: ",root

print "\nPackaging iSproggler version %s\n" % main._version_

sys.argv.append("py2exe")


os.mkdir(os.path.join(root,"build"))

def targzsource():
    shutil.copytree(root,os.path.join(os.path.split(root)[0],"iSproggler-src"))
    temproot = os.path.join(os.path.split(root)[0],"iSproggler-src")
    for filename in os.listdir(temproot):
        if filename.endswith(".pyc"):
            os.remove(os.path.join(temproot,filename))
    targz = tarfile.open(os.path.join(os.path.split(temproot)[0],"iSproggler"+main._version_+"-src.tar.gz"),"w:gz")
    targz.add(temproot,os.path.split(temproot)[1])
    targz.close()
    shutil.rmtree(temproot)

def movefiles():
    try:
        pass #shutil.rmtree("C:\\Python24\\Lib\\site-packages\\win32com\\gen_py")
    except:
        pass
    if not os.path.exists(os.path.join(root,"build")):
        os.makedirs(os.path.join(root,"build"))            
    #try:
    #    shutil.rmtree(os.path.join(root,"build\\data"))
    #except:
    #    pass
    #shutil.copytree(os.path.join(root,"data"),os.path.join(root,"build\\data"))
    shutil.copyfile(os.path.join(root,"local.py"),os.path.join(root,"build\\local.py"))
    #shutil.copyfile(os.path.join(root,"Read Me.rtf"),os.path.join(root,"build\\Read Me.rtf"))

def deldsstores():
    if ".DS_Store" in os.listdir(root):
        os.remove(os.path.join(root,".DS_Store"))
    if ".DS_Store" in os.listdir(os.path.join(root,"data")):
        os.remove(os.path.join(os.path.join(root,"data"),".DS_Store"))
    if ".DS_Store" in os.listdir(os.path.join(root,"build")):
        os.remove(os.path.join(os.path.join(root,"build"),".DS_Store"))

def prepareshell():
    """From http://starship.python.net/crew/theller/moin.cgi/WinShell"""
    # ModuleFinder can't handle runtime changes to __path__, but win32com uses them,
    # particularly for people who build from sources.  Hook this in.
    try:
        import modulefinder
        import win32com
        for p in win32com.__path__[1:]:
            modulefinder.AddPackagePath("win32com", p)
        for extra in ["win32com.shell","win32com.mapi"]:
            __import__(extra)
            m = sys.modules[extra]
            for p in m.__path__[1:]:
                modulefinder.AddPackagePath(extra, p)
    except ImportError:
        # no build path setup, no worries.
        pass

def upx():
    os.system("upx --best "+os.path.join(root,"build\\iSproggler.exe"))

def zipapp():
    temproot = os.path.join(os.path.split(root)[0],"iSproggler Build")
    shutil.copytree(os.path.join(root,"build"),temproot)
    zip = zipfile.ZipFile(os.path.join(os.path.split(root)[0],"iSproggler-"+main._version_+".zip"),"w",zipfile.ZIP_DEFLATED)
    zipinfo = zipfile.ZipInfo("iSproggler/")
    zip.writestr(zipinfo, "")
    for p in os.listdir(temproot):
        if os.path.isdir(os.path.join(temproot,p)):
            for dirpath in os.listdir(os.path.join(temproot,p)):
                zip.write(os.path.join(os.path.join(temproot,p),dirpath),"iSproggler/"+p+"/"+dirpath)
        else:
            zip.write(os.path.join(temproot,p),"iSproggler/"+p)
    zip.close()
    shutil.rmtree(temproot)

def createmsi():
    pass

print "Creating tape archive..."
targzsource()
print "Moving and deleting files..."
movefiles()
print "Deleting .DS_Store files..."
deldsstores()
print "Creating images..."
# Bug somewhere when calling this from setup?
#initimages(root)
#print "Preparing shell module..."
#prepareshell()
print


setup(
    options = {"py2exe": {"typelibs":
                          [('{9E93C96F-CF0D-43F6-8BA8-B807A3370712}', 0, 1, 9)],
                          "optimize": 2,
                          #"packages": ["encodings"],
                          "bundle_files": 1,
                          "dist_dir": os.path.join(root,"build"),
                          }},


    zipfile = None,             
    windows = [{"script": os.path.join(root,"main.py"),

                "dest_base" : "iSproggler",

                "icon_resources": [(1, root+"\\icon.ico")],

                "version": main._version_,

                "copyright": "David Nicolson",

                }]
)

os.remove(os.path.join(os.path.join(root,"build"),"w9xpopen.exe"))
print
if deployment:
    print "Compressing executable..."
    upx()
print "Creating ZIP archive..."
zipapp()

#if raw_input("Upload to server? [y/n]\n").tolower() == "y":
#   ftpupload()
    
