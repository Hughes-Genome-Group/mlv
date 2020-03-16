from . import meths
from app import databases,app
from app.ngs.view import ViewSet,get_all_default_sets,create_view_set_from_file,get_all_sets
import json,ujson,os
from flask import request
from flask_user import current_user
from app.ngs.utils import save_file
from app.ngs.project import get_project

@meths.route("/<db>/get_view_set/<vs_id>")
def get_view_set(db,vs_id):
    vs_id = int (vs_id)
    vs = ViewSet(db,vs_id)
    return json.dumps(vs.get_all_views())


@meths.route("/<db>/get_all_view_sets")
def get_all_view_sets(db):
    data =get_all_sets(db)
    return ujson.dumps({"data":data})

@meths.route("/<db>/upload_view_set", methods=["POST"])
def upload_view_set(db):
    f= request.files['upload_file']
    filepath = save_file(f)
    data = ujson.loads(request.form.get("data"))
   
    #filepath= "C:\\mlv\\test_data\\temp\\test_capturec.txt"
    #data= ujson.loads(open("C:\\mlv\\test_data\\temp\\test_upload.json").read())
    fields = data.get('fields')
    extra_fields=None
    if fields:
        extra_fields={}
        for field in fields:
            pos=field['position']-2
            extra_fields[pos]=field
            if field['datatype']=="double":
                field['parser']=float
                field['datatype']="double precision"
            elif field['datatype']=='text':
                field['parser']=str
            elif field['datatype']=='integer':
                field['parser']=int
            field['order']=pos
            field['name']="field"+str(pos)
    app.logger.info("creating view set")        
    vs = create_view_set_from_file(db,filepath,data['name'],
                              track_name=data.get('track_name'),
                              primary_track=data.get('primary_track'),
                              secondary_tracks=data.get("secondary_tracks"),
                              description=data.get("description"),
                              has_headers=data.get("has_headers",True),
                              extra_fields=extra_fields,
                              track_id_position=data.get("track_id_position",0),
                              annotation_sets=data.get("annotation_sets",[]),
                              delimiter=data.get("delimiter","\t"),
                              margin=data.get("margin")
                          )
 
    url= vs.get_url(external=True)
    data_file = os.path.join(vs.get_folder(),"original_data.json")
    handle = open(data_file,"w")
    handle.write(ujson.dumps(data))
    handle.close();
    
    
    return ujson.dumps({"success":True,"url":url,"id":vs.id})
    
    
@meths.route("/<db>/create_thumbnails/<vs_id>",methods=["POST"])    
def create_thumbnails(db,vs_id):
    data = request.json
    max_y=None
    if data['primary_track']['scale']=="fixed":
        max_y=data['primary_track']['max_y']
    primary_color = data['primary_track']['color']
    vs = ViewSet(db,vs_id)
    vs.create_thumbnails(25,50,max_y=max_y,
                      primary_track_color=primary_color,
                      secondary_track=data.get('secondary_track'),
                      flanking_region=data.get("margin"),
                      preview =data.get("preview"),
                      limit= data.get("limit"))
    return ujson.dumps({"success":True})
    

@meths.route("/<db>/get_feature_set/<vs_id>/<chr>/<start>/<finish>")
def get_view_set_range(db,vs_id,chr,start,finish):
    vs_id = int (vs_id)
    start = int (start)
    finish = int (finish)
    vs = ViewSet(db,vs_id)
    return json.dumps(vs.get_views(chr,start,finish))


@meths.route("/<db>/get_view_set_full/<vs_id>",methods=["POST","GET"])
def get_view_set_full(db,vs_id):
    vs_id = int (vs_id)
    vs = ViewSet(db,vs_id)
    if request.args.get("simple"):
        data= request.json
        filters=None
        if data:
            filters=data.get("filters")
        view_data=vs.get_data_simple(filters=filters)
    else:
        view_data= vs.get_data_for_table()
    if request.args.get("project_id"):
        pid= int(request.args.get("project_id"))
        p=get_project(pid)
        perm = p.get_permissions(current_user)
        p.data["permission"]=perm
        view_data['project_data']=p.data
        
    return json.dumps(view_data)




@meths.route("/get_all_default_sets")
def get_all_defualt_view_sets():
    return json.dumps(get_all_default_sets())


@meths.route("/<db>/get_multi_feature_set/<fs_id>/<chr>/<start>/<finish>")
def get_multi_feature_set(db,fs_id,chr,start,finish):
    fs_id = int (fs_id)
    start = int(start)
    finish= int(finish)
    fs = ViewSet(db,fs_id)
    metadata = fs.get_metadata()
    data= fs.get_views(chr,start,finish)
    return json.dumps({"metadata":metadata,"data":data})
    
