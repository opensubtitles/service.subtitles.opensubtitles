# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import urllib
import struct
import xbmcvfs
import xmlrpclib

__scriptname__ = sys.modules[ "__main__" ].__scriptname__

BASE_URL_XMLRPC = u"http://api.opensubtitles.org/xml-rpc"


class OSDBServer:

  def __init__( self, *args, **kwargs ):
    self.server = xmlrpclib.Server( BASE_URL_XMLRPC, verbose=0 )
    login = self.server.LogIn("", "", "en", __scriptname__.replace(" ","_"))    
    self.osdb_token  = login[ "token" ]

  def mergesubtitles( self ):
    self.subtitles_list = []
    if( len ( self.subtitles_hash_list ) > 0 ):
      for item in self.subtitles_hash_list:
        if item["format"].find( "srt" ) == 0 or item["format"].find( "sub" ) == 0:
          self.subtitles_list.append( item )

    if( len ( self.subtitles_list ) > 0 ):
      self.subtitles_list.sort(key=lambda x: [not x['sync'],x['language']])

  def searchsubtitles( self, srch_string, languages, hash_search, _hash = "000000000", size = "000000000"):
    msg                      = ""
    searchlist               = []
    self.subtitles_hash_list = []
    
    try:
      if ( self.osdb_token ) :
        if hash_search:
          searchlist.append({'sublanguageid':','.join(languages), 'moviehash':_hash, 'moviebytesize':str( size ) })
        searchlist.append({'sublanguageid':','.join(languages), 'query':srch_string })
        search = self.server.SearchSubtitles( self.osdb_token, searchlist )
        if search["data"]:
          for item in search["data"]:
            self.subtitles_hash_list.append({'filename'      : item["SubFileName"],
                                             'link'          : item["ZipDownloadLink"],
                                             'language'      : item["LanguageName"],
                                             'ID'            : item["IDSubtitleFile"],
                                             'rating'        : "%.1d" % float(item["SubRating"]),
                                             'format'        : item["SubFormat"],
                                             'sync'          : str(item["MatchedBy"]) == "moviehash",
                                             'hearing_imp'   : int(item["SubHearingImpaired"]) != 0
                                             })
            
    except:
      msg = "Error Searching For Subs"
    
    self.mergesubtitles()
    return self.subtitles_list, msg

  def download(self, ID, dest):
     try:
       import zlib, base64
       down_id=[ID,]
       result = self.server.DownloadSubtitles(self.osdb_token, down_id)
       if result["data"]:
         local_file = open(dest, "w" + "b")
         d = zlib.decompressobj(16+zlib.MAX_WBITS)
         data = d.decompress(base64.b64decode(result["data"][0]["data"]))
         local_file.write(data)
         local_file.close()
         log( __name__,"Download Using XMLRPC")
         return True
       return False
     except:
       return False

def log(module, msg):
  xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG ) 

def hashFile(file_path):
    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)
    f = xbmcvfs.File(file_path)
    
    filesize = f.size()
    hash = filesize
    
    if filesize < 65536 * 2:
        return "SizeError"
    
    buffer = f.read(65536)
    f.seek(max(0,filesize-65536),0)
    buffer += f.read(65536)
    f.close()
    for x in range((65536/bytesize)*2):
        size = x*bytesize
        (l_value,)= struct.unpack(longlongformat, buffer[size:size+bytesize])
        hash += l_value
        hash = hash & 0xFFFFFFFFFFFFFFFF
    
    returnHash = "%016x" % hash
    return filesize,returnHash


def OpensubtitlesHashRar(firsrarfile):
    f = xbmcvfs.File(firsrarfile)
    a=f.read(4)
    if a!='Rar!':
        raise Exception('ERROR: This is not rar file.')
    seek=0
    for i in range(4):
        f.seek(max(0,seek),0)
        a=f.read(100)        
        type,flag,size=struct.unpack( '<BHH', a[2:2+5]) 
        if 0x74==type:
            if 0x30!=struct.unpack( '<B', a[25:25+1])[0]:
                raise Exception('Bad compression method! Work only for "store".')            
            s_partiizebodystart=seek+size
            s_partiizebody,s_unpacksize=struct.unpack( '<II', a[7:7+2*4])
            if (flag & 0x0100):
                s_unpacksize=(unpack( '<I', a[36:36+4])[0] <<32 )+s_unpacksize
                log( __name__ , 'Hash untested for files biger that 2gb. May work or may generate bad hash.')
            lastrarfile=getlastsplit(firsrarfile,(s_unpacksize-1)/s_partiizebody)
            hash=addfilehash(firsrarfile,s_unpacksize,s_partiizebodystart)
            hash=addfilehash(lastrarfile,hash,(s_unpacksize%s_partiizebody)+s_partiizebodystart-65536)
            f.close()
            return (s_unpacksize,"%016x" % hash )
        seek+=size
    raise Exception('ERROR: Not Body part in rar file.')

def getlastsplit(firsrarfile,x):
    if firsrarfile[-3:]=='001':
        return firsrarfile[:-3]+('%03d' %(x+1))
    if firsrarfile[-11:-6]=='.part':
        return firsrarfile[0:-6]+('%02d' % (x+1))+firsrarfile[-4:]
    if firsrarfile[-10:-5]=='.part':
        return firsrarfile[0:-5]+('%1d' % (x+1))+firsrarfile[-4:]
    return firsrarfile[0:-2]+('%02d' %(x-1) )

def addfilehash(name,hash,seek):
    f = xbmcvfs.File(name)
    f.seek(max(0,seek),0)
    for i in range(8192):
        hash+=struct.unpack('<q', f.read(8))[0]
        hash =hash & 0xffffffffffffffff
    f.close()    
    return hash

######## Standard Search function ###########
# 'item' has everything thats needed for search parameters, look in script.subtitles.main/gui.py for detailed info
# below list might be incomplete
#
#    item['file_original_path']
#    item['year']
#    item['season']
#    item['episode']
#    item['tvshow']
#    item['title']
# anything needed for download can be saved here and later retreived in 'download_subtitles' function
#############################################

def Search( item ):
  ok = False
  hash_search = False
  if len(item['tvshow']) > 0:                                            # TvShow
    OS_search_string = ("%s S%.2dE%.2d" % (item['tvshow'],
                                           int(item['season']),
                                           int(item['episode']),)
                                          ).replace(" ","+")      
  else:
    if str(item['year']) == "":
      item['title'], item['year'] = xbmc.getCleanMovieTitle( item['title'] )

    OS_search_string = item['title'].replace(" ","+")
    
  log( __name__ , "Search String [ %s ]" % (OS_search_string,))     
 
  if item['temp'] : 
    hash_search = False
    file_size   = "000000000"
    SubHash     = "000000000000"
  else:
    try:
      if item['rar']:
        file_size, SubHash   = OpensubtitlesHashRar(item['file_original_path'])
      else:
        file_size, SubHash   = hashFile(item['file_original_path'])
      log( __name__ ,"xbmc module hash and size")
      hash_search = True
    except:  
      file_size   = ""
      SubHash     = ""
      hash_search = False
  
  if file_size != "" and SubHash != "":
    log( __name__ ,"File Size [%s]" % file_size )
    log( __name__ ,"File Hash [%s]" % SubHash)
  
  log( __name__ ,"Search by hash and name %s" % (os.path.basename( item['file_original_path'] ),))
  item['subtitles_list'], item['msg'] = OSDBServer().searchsubtitles( OS_search_string, item['3let_language'], hash_search, SubHash, file_size  )

# 2 below items need to be returned to main script
# item['subtitles_list'] list of all subtitles found, needs to include below items. see searchsubtitles above for more info
#                        "language"
#                        "filename"
#                        "rating"
# item['msg'] message notifying user of any errors

  return item

######## Standard Download function ###########
# as per search_subtitles explanation
#
# we need to return list of subtitles to main script, if list contains more than one subtitle file,
#  it needs to be sorted so that CD1 is first, CD2 second...
# list of subtitles can be:
#                           download url for subtitle(uncompressed),
#                           local file,
#                           network file(smb, nfs, afp),
#                           file in zip or rar archive(path/to/zip.zip/subtitle_file.srt)
###############################################
def Download(item):
  subtitle_list = []
  exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
  if item['stack']: ## we only want XMLRPC download if movie is not in stack, you can only retreive multiple subs in zip
    result = False
  else:
    subtitle = os.path.join(item['tmp_sub_dir'], item['subtitles_list'][item['pos']][ "filename" ])
    result = OSDBServer().download(item['subtitles_list'][item['pos']][ "ID" ], subtitle)
  if not result:
    log( __name__,"Download Using HTTP")
    zip = os.path.join( item['tmp_sub_dir'], "OpenSubtitles.zip")
    f = urllib.urlopen(item['subtitles_list'][item['pos']][ "link" ])
    with open(zip, "wb") as subFile:
      subFile.write(f.read())
    subFile.close()
    xbmc.sleep(500)
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip,item['tmp_sub_dir'],)).encode('utf-8'), True)
    for file in xbmcvfs.listdir(zip)[1]:
      file = os.path.join(item['tmp_sub_dir'], file)
      if (os.path.splitext( file )[1] in exts):
        subtitle_list.append(file)
  else:
    subtitle_list.append(subtitle)
    
  if xbmcvfs.exists(subtitle_list[0]):
    return subtitle_list
    
    