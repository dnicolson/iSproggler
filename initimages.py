#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys

def initimages(root):
    current = os.path.join(root,"data")

    imports = """from wx import ImageFromStream, BitmapFromImage
from wx import EmptyIcon
import cStringIO"""
    imagesdef = """def images(imagename):
    stream = cStringIO.StringIO(imagesdict[imagename])
    image = ImageFromStream(stream)
    bitmap = BitmapFromImage(image)
    if imagename.endswith(".ico"):
        icon = EmptyIcon()
        icon.CopyFromBitmap(bitmap)
        return icon
    return bitmap"""

    datafiles = os.listdir(current)
    try:
        datafiles.remove(".DS_Store")
    except:
        pass

    imgfile = open(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])),"images.py"),"w")
    imgfile.write("#!/usr/bin/env python\n\n")
    imgfile.write(imports+"\n\n")
    imgfile.write("imagesdict = {\n")

    for data in datafiles:
        filedata = open(os.path.join(current,data)).read()
        filehex = ['"']
        for byte in filedata:
            hexbyte = hex(ord(byte))
            if len(hexbyte) == 3:
                hexbyte = hexbyte[0]+hexbyte[1]+"0"+hexbyte[2]
            filehex.append(hexbyte.replace("0x","\\x"))
        filehex.append('"')
    
        imgfile.write("'"+data+"':\n")

        buffer = ""
        linelen = 0
        for byte in filehex:
            if linelen > 72:
                imgfile.write(buffer+"\\\n")
                buffer = ""
                linelen = 0
            buffer += byte
            linelen += len(byte)
        imgfile.write(buffer)
        if datafiles[-1] != data:
            imgfile.write(",\n\n")
    imgfile.write("}\n\n")

    imgfile.write("\n")
    imgfile.write(imagesdef)
    imgfile.close()

if __name__ == "__main__":
    initimages(sys.argv[1])
