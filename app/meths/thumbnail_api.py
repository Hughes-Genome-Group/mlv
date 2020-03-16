from . import meths
from app.ngs.thumbnail import ThumbnailSet,create_node_thumbnail
from app.ngs.utils import get_temporary_folder,get_reverse_track_proxy
from app.ngs.view import ViewSet
from flask import request,send_file
import os,ujson

@meths.route("/<db>/create_test_thumbnails",methods=['POST'])
def create_test_thumbnails(db):
    '''creates test thumbnails
    ''' 
    data = request.json
    tracks=data.get("tracks")
    #reverse the proxy
    for track in tracks:
        track['url']=get_reverse_track_proxy(track['url'])
    
    
    annotation_sets=data.get("annotations")
    gene_set=data.get("genes")
    if gene_set:
        gene_set=1
    height=int(data.get("height",100))
    width=int(data.get("width",200))
    margin =  int(data.get("margin",0))
    margin2 =  int(data.get("margin2",0))
    
    #not yet implemented
    region_length=int(data.get("region_length",0))
    region_length2= int(data.get("region_length2",0))
    half_rl=int(region_length/2)
    half_rl2=int(region_length2/2)
    
    
    locations=data.get("locations")
    double_view=data.get("double_view")
    if double_view:
        margin2=margin+10000
        
  
    
    tn_set = ThumbnailSet(db,tracks=tracks,annotation_sets=annotation_sets,
                          gene_set=gene_set,height=height,width=width)
    
    thumbnails=[]
    folder = get_temporary_folder()
    url_folder = folder.replace("/mlv","")
    count=1
    for loc in locations:
        tram_lines=[loc['start'],loc['end']]
        if region_length:
            middle = int((loc['end']-loc['start'])/2)+loc['start']
            st=middle-half_rl
            en=middle+half_rl
        else:
            st=  loc['start']-margin
            en = loc['end']+margin
        stub ="tn"+str(count)
        
        if not double_view:
            tn_set.draw_thumbnail(loc['chr'],st,en,
                              folder,stub,tram_lines=tram_lines)
        else:
            if region_length:
                 middle = int((loc['end']-loc['start'])/2)+loc['start']
                 st=middle-half_rl
                 en=middle+half_rl
                 st2=middle-half_rl2
                 en2=middle+half_rl2
            else:
                st=loc['start']-margin
                en=loc['end']+margin
                st2=loc['start']-margin2
                en2=loc['end']+margin2
            
            views=[
                  
                    {"chrom":loc['chr'],"start":st,"end":en,'tram_lines':tram_lines},
                    {"chrom":loc['chr'],"start":st2,"end":en2,'tram_lines':tram_lines}   
                ]
            tn_set.draw_composite_thumbnail(views,folder,stub)
            
        thumbnails.append(os.path.join("/data",url_folder,stub+".png"))
        count+=1
    return ujson.dumps(thumbnails)

@meths.route("/create_track_image",methods=['POST'])
def create_track_image():
    data= request.json
    type = data.get("type")
    if type not in ["png","svg","pdf"]:
        return None
    pos = data["position"]
    images=[{"loc":[pos["chr"],pos["start"],pos["end"]],"stub":"image"}]
    for track in data["tracks"]:
        url = track.get("url")
        if url and url.startswith("/"):
            track["url"]="https://lanceotron.molbiol.ox.ac.uk"+url
    config={
        "width":int(data["width"]),
        "height":data["height"],
        "type":type,
        "fixed_height_mode":True
        
    }
    folder = create_node_thumbnail(data["tracks"],images,config)
    folder = folder.replace("/mlv","")
    ret_image = folder+"/image."+type
    return ret_image
    


@meths.route("/<db>/create_thumbnail_preview",methods=['POST'])
def create_thumbnail_preview(db):
    data = request.json
    vs = ViewSet(db,data["viewset_id"])
    folder = get_temporary_folder()
    tn_det = data['thumbnail_details']
    vs.data['thumbnail_details']= tn_det
    vs.data["margin"]=tn_det['margin']
    vs.data["annotation_sets"]=data["annotations"]
    tn = ThumbnailSet(db,height=int(tn_det['height']),
                      width=int(tn_det['width']))
    ids = list(range(1,21))
    gene_set=0
    if data.get("genes") and vs.db != "other":
        gene_set=1
    tn.draw_view_set(vs,specific_views=ids,
                    folder=folder,
                    gene_set=gene_set)
    images=[]
    url_folder = folder.replace("mlv","")
    
    for i_id in ids:
        images.append("{}/tn{}.png".format(url_folder,i_id))
    return ujson.dumps({"images":images,"success":True})
    
