
from app import databases
import csv,requests,os
from urllib.parse import urlparse
import subprocess
columns=[
            {"field":"track_id","name":"Name","type":"text"},
            {"field":"url","name":"URL","type":"text"},
            {"field":"date_added","name":"Date Added","type":"date"},
            {"field":"short_label","name":"Short Label","type":"text"},
            {"field":"type","name":"Type","type":"text"}
        ]

allowed_types={
    "bigwig":"bigWig",
    "bed":"Bed" 
}



controls=[
    {"field":"track_id","name":"Name","type":"input"},
    {"field":"url","name":"URL","type":"input"},
    {"field":"short_label","name":"Short Label","type":"input"},
    {"field":"long_label","name":"Long Label","type":"text-area"},
    {"field":"type","name":"Type","type":"select","values":allowed_types},
    {"field":"color","name":"Color","type":"color-chooser"} 
]

def get_all_columns():
    return columns


def validate_track_file_ucsc(url,max_number=None):
    try:
        info= urlparse(url)
        if not info[0] or not info[1]:
            raise Exception()
        
        command = "bigWigInfo -chroms {}".format(url)
        process = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
        chroms= {}
    
        for line in iter(process.stdout.readline,b''):
            line=line.decode()
            if line.startswith("\t"):
                arr= line.strip().split(" ");
                chroms[arr[0]]=int(arr[2])
        if len(chroms)==0:
            return {"valid":False}
        if max_number and len(chroms)>max_number :       
            li = sorted (chroms,key=chroms.get,reverse=True)
            new_chroms={}
            for item in li[0:max_number]:
                new_chroms[item]=chroms[item]
        
            chroms=new_chroms
    
        chrom_list=sorted(chroms.keys())
        return {"valid":True,"chromosomes":chroms,"ordered":chrom_list}
    except Exception as e:
        return {"valid":False}
    

def validate_track_file(url):
    import pyBigWig
    try:
        bw = pyBigWig.open(url)   
        chroms = bw.chroms()
        li =sorted(chroms.keys())
        return {"valid":True,"chromosomes":chroms,"ordered":li}
    except:
        return {"valid":False}


def validate_track(db,data):
    errors={}
    url = data.get("url")
    if not url:
        errors['url']="URL is required"
    else:
        try:
            resp = requests.head(url)
            if resp.status_code != 200:
                errors['url']="URL cannot be found"
        except:
            errors['url']="The URL is incorrect"
    name = data.get("track_id")
    if not name:
        errors['track_id']="A name is required"
    else:
        exists=databases[db].value_exists("tracks","track_id",name)
        if exists:
            errors['track_id']="The track name is not uniqe"
    return errors
       
        
def get_or_create_track(db,url,name=None,short_label=None):
    '''If a track with the supplied url is not in the database,
    one will be added, with the file name (without the extension)
    as the track_id (name) if one is not supplied
       
    Args:
        db(str): The name of the database
        url(str): The url of a track
        name(Optional(str)): If the track does not exist then
           this will be the track_id 
        
    Returns:
        A dictionary containing information about the track
      
    '''
    sql = "SELECT * FROM tracks WHERE url=%s"
    results= databases[db].execute_query(sql,(url,))
    if len(results)>0:
        return results[0]
    
    track_filename=os.path.split(url)[1]
    last_fullstop =track_filename.rfind(".")
    track_name=track_filename[:last_fullstop]
    track_suffix=track_filename[:last_fullstop]
    track_type="bed"
    if track_suffix=="bw":
        track_type="bigWig"
        
    data= {"track_id":track_name,"url":url,"type":track_type}
    data =add_track(db,data)
    return data
    
def add_track_details(db,tracks):
    '''Given a config of tracks (each must have track id)
    The url,short and long labels will be added to the 
    list
    Args:
        tracks(list): A list of track dictionaries (each one must
           have track_id)
    '''
    id_to_track={}
    for track in tracks:  
        id_to_track[track['track_id']]=track
    info = databases[db].get_tracks(list(id_to_track.keys()),proxy=False)
    for item in info:
        track=id_to_track[item['track_id']]
        track['url']=item['url']
        track['short_label']=item['short_label']
    



        

def get_all_tracks(db):
    sql = "SELECT id,track_id ,url,type,date_added,short_label,color FROM tracks"
    tracks= databases[db].execute_query(sql)
    for track in tracks:
        track['date_added']= track['date_added'].strftime("%Y-%m-%d")
        
   
    return tracks
    
def get_inputs():
    return controls    

def add_track(db,data,check_exists=False):
    '''Adds a track to the specified database
    The url,short and long labels will be added to the 
    list
    Args:
        db(str): The name of the database
        data(dict): A track dictionaries (minimum track_id and url)
        check_exists(Optional[boolean]): If True (default False) -
           the track_id will be checked ro see if it is unique
           
    Returns:
        A dictionary of the track object which will include the newly
        assigned id or None if check_exists was True and the track_id
        already exists
    '''
    if check_exists:
         exists=databases[db].value_exists("tracks","track_id",data['track_id'])
         if exists:
             return None
    if not data.get("short_label"):
        data['short_label']=data['track_id']
    if not data.get("long_label"):
        data["long_label"]=data['short_label']
    id = databases[db].insert_dict_into_table(data,"tracks")
    data['id']=id
    return data


def add_tracks_from_file(file_name,db):
    tracks=[]
    with open(file_name) as csvfile:
        reader = csv.DictReader(csvfile,delimiter="\t")
        for row in reader:
            tracks.append(row)
    databases[db].insert_dicts_into_table(tracks,"tracks")
            


def add_tracks_from_hub(local_file,db):
    tracks=[]
    try:
         with open(local_file) as f:
            track={}
            for line in f:
                line=line.strip()
                if line.startswith("track"):
                    track['track_id']=line.split()[1]
                elif line.startswith("bigDataUrl"):
                    track['url']=line.split()[1]
                elif line.startswith("shortLabel"):
                    track['short_label']=line.split()[1]
                elif line.startswith("longLabel"):
                    track['long_label']=line.split()[1]
                elif line.startswith("type"):
                    track['type']=line.split()[1]
                elif line.startswith("color"):
                    track['color']=line.split()[1]
                elif not line:
                    if len(track)==6:
                        tracks.append(track)
                    track={}
            if len(track)==6:
                tracks.append(track)
    except:
        print ("exception")
        
    databases[db].insert_dicts_into_table(tracks,"tracks");
    
    
                


