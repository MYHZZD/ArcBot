import json
import os
from PIL import Image
import hashlib

path = "C:\\Users\\Administrator\\Desktop\\ArcBot\\data\\saying\\"
with open(
    path + "mappings.json",
    "r",
    encoding="utf8",
) as readfile:
    jsondata: str = readfile.read()
    mappings = json.loads(jsondata)
delkey=[]
for key in mappings:
    if key != "Plugin":
        Data = mappings[key]
        Data_2 = Data["Data"]
        group = Data_2["Group"]
        pid = Data_2["Picture ID"]

        try:
            img=Image.open(path + group + "\\" + pid)
        except IOError:
            print(group+"中"+pid+"不存在,可能是同一图片多次添加导致")  
            delkey.append(key)   
        else:
            img.close()

            img = Image.open(path + group + "\\" + pid)
            fmt = img.format
            img.close()
            print(path + group + "\\" + pid)
            print(fmt)
            with open(path + group + "\\" + pid, "rb") as prb:
                md5 = hashlib.md5(prb.read()).hexdigest()
            if fmt == "JPEG":
                fmt = "jpg"
            if fmt == "PNG":
                fmt = "png"
            if fmt == "GIF":
                fmt = "gif"
            newname = path + group + "\\" + md5.upper() + "." + fmt
            print(newname + "\n")

            
            os.rename(path + group + "\\" + pid, newname)
            Data_2["Picture ID"] = md5.upper() + "." + fmt
for dkey in delkey:
    del mappings[dkey]
        
with open(
    path + "mappings_new.json",
    "w",
    encoding="utf8",
) as writejson:
    json.dump(mappings, writejson, ensure_ascii=False)
