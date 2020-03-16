from app import app
import os
from werkzeug.utils import secure_filename
import string,random,requests
import shutil


def save_file(file,dir="temp"):
    folder = os.path.join(app.config['DATA_FOLDER'],dir)
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = secure_filename(file.filename)
    filepath = os.path.join(folder,filename)
    file.save(filepath)
    return filepath

def convert_to_indexed_bed(file_name):
    files_to_process = []
    if os.path.isdir(file_name):
        files= os.listdir(file_name)
        for f in files:
            if f.endswith(".bed"):
                f= os.path.join(file_name,f)
                files_to_process.append(f)
    else:
        files_to_process.append(file_name)
    for f in files_to_process:
        gz_file=f+".gz"
        os.system("sort -V -k1,1 -k2,2 {} | bgzip >  {}".format(f,gz_file))
        os.system("tabix -p bed {}".format(gz_file))

def convert_to_bed(folder):
    files=os.listdir(folder)
    for f in files:
        if f.endswith("bb"):
            f=os.path.join(folder,f)
            o =  f.split(".bb")[0]+".bed"
            os.system("bigBedToBed {} {}".format(f,o))
 
 
def download_and_convert_bigbed(url,chroms=None):
    '''Downloads the remote bigbed file to a temporary directory
    and converts it to bed format
    
    Args:
        url (str): The url of the remote bigbed file
                 
    Returns:   01
        The location of the bed file  
    '''
    import urllib.request
    import pyBigWig
    from app.jobs.jobs import save_file
    folder = get_temporary_folder()
    if not os.path.exists(folder):
        os.makedirs(folder)
    name = os.path.split(url)[1]
    temp_file = os.path.join(folder,name)
    temp_file=temp_file.replace(".bb",".bed")
    resp= requests.get(url.replace(".bb",".bed"))
    #bb = urllib.request.urlopen(url)
    with open(temp_file,"w") as output:
        output.write(resp.text)  
    new_file = temp_file#.replace(".bb",".bed")
    #os.system("bigBedToBed {} {}".format(temp_file,new_file))
    if chroms: 
        temp_bb = new_file.replace(".bed","_wid.bed")
        out_file = open(temp_bb,"w")
        with open(new_file) as bed:
            for id,line in enumerate(bed,start=1):
                line=line.strip()
                out_file.write(line+"\t"+str(id)+"\n")
        out_file.close()
        bb_file=temp_bb.replace("_wid.bed","_wid.bb")
        os.system("bedToBigBed  -type=bed4 {} {} {}".format(temp_bb,chroms,bb_file))
        fold=url.split("/")[-2]
        save_file(bb_file,fold)
            
    #os.remove(temp_file)
    return temp_file    



    
    



def create_bigbed_wid(bed_file,remote_folder,name,chrom_file,extra_columns=2):
    from app.jobs.jobs import save_file
    folder = os.path.split(bed_file)[0]
    temp_file= os.path.join(folder,"temp.bed")
    temp_out= open(temp_file,"w")
    
    temp_bb=os.path.join(folder,name)
    with open(bed_file) as bed:
        for id,line in enumerate(bed,start=1):
            line=line.strip()
            arr=line.split("\t")
            arr.insert(3,str(id))
            temp_out.write("\t".join(arr)+"\n")
    temp_out.close()
    os.system("bedToBigBed type=bed4+{} {} {} {}".format(extra_columns,temp_file,chrom_file,temp_bb,) )
    save_file(temp_bb,remote_folder)
    shutil.rmtree(folder)
            
    
            
def get_track_proxy(url):
    t_p = app.config.get("TRACK_PROXIES")
    if t_p:
        for p in t_p:
            url=url.replace(p,t_p[p])
    return url;

def get_reverse_track_proxy(url):
    tp = app.config.get("TRACK_PROXIES")
    if tp:
        for sub in tp:
            proxy=tp[sub]
            url=url.replace(proxy,sub)
    return url
        
def get_temporary_folder():
    '''Makes a temporary folder with a random name 
    Returns:
        The name of the temporary folder
    '''
    chars=string.ascii_uppercase + string.ascii_lowercase + string.digits
    name= ''.join(random.choice(chars) for _ in range(20))
    folder =os.path.join(app.config["TEMP_FOLDER"],name)
    os.makedirs(folder)
    return folder
    
    
    
