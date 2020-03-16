from . import meths
from app.decorators import permission_required_method,logged_in_required_method,admin_required_method
from app.ngs.project import create_project,get_project,get_project_data_type,get_project_columns_type
import ujson,copy
from flask_user import current_user
from flask import request
from app import db as user_db
from app import app,databases
from app.ngs.project import get_projects_summary,create_project,get_project
from app.ngs.utils import get_temporary_folder,save_file
from app.ngs.view import ViewSet
import os
from app.zegami.zegamiupload import get_tags
from _sqlite3 import complete_statement


#******************************************
#**GENERAL PROJECT METHODS*****************
#******************************************
@meths.route("/get_project_data/<int:id>")
def get_project_data(id): 
    p = get_project(id)
    perm = p.get_permissions(current_user)
    if not perm:
         return ujson.dumps({"success":False,"msg":"You do not have permission"})

    return ujson.dumps({
        "name":p.name,
        "type":p.type,
        "genome":p.db,
        "description":p.description,
        "data":p.get_data(),
        "permission":perm,
        "status":p.status,
        "id":p.id
    })
 

@meths.route("/execute_project_action/<int:project_id>",methods=["POST"])
def execute_project_action(project_id):
    try:
        data=request.json
        if data:
            arguments= data.get("args",{})
            method= data.get("method")
        #special case when files are inolved
        if len(request.files)>0:
            data = ujson.loads(request.form.get("data"))
           
            method=data.get("method")
            arguments=data.get("arguments",{})
            arguments["files"]={}
            for fid in request.files:
                f = request.files[fid]
                filepath = save_file(f)
                arguments["files"][fid]=filepath    
        p = get_project(project_id)
        return ujson.dumps(p.execute_action(method,current_user,arguments))
    except Exception as e:
        return ujson.dumps({"msg":"Cannot execute action","success":False})
        


    

@meths.route("/get_create_projects")
def get_create_projects():
    ret_proj={}
    perms={}
    li=[]
    non_public_allowed= set()
    if current_user.is_authenticated:       
        sql = "SELECT value FROM permissions WHERE permission='view_project_type' AND user_id=%s"
        res = databases["system"].execute_query(sql,(current_user.id,))
        for r in res:
            non_public_allowed.add(r['value'])
    
    for name in app.config['MLV_PROJECTS']:
        proj=app.config['MLV_PROJECTS'][name]
        
        if proj.get("can_create"):
            if proj.get("is_public"):
                ret_proj[name]=proj
            elif current_user.is_authenticated:
                if current_user.administrator or name in non_public_allowed:
                    ret_proj[name]=proj            
    return ujson.dumps({"projects":ret_proj})




            
@meths.route("/create_project/<type>",methods=["POST"])
def create_new_project(type):
    if not current_user.is_authenticated and not app.config["MLV_PROJECTS"][type].get("anonymous_creation"):
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    msg=""
    success=True
    project_id=-1
    try:
        permission= "create_project_type"
        if current_user.is_authenticated and not current_user.administrator and  not current_user.has_permission(permission,type):
            msg ="You do not have permission to create this project"
            success=False
        else:
            name = request.form.get("name")
            description = request.form.get("description")
            genome = request.form.get("genome")
            has_genome=True
            if app.config["MLV_PROJECTS"][type].get("enter_genome"):
                has_genome=genome
            else:
                genome="other"
            if not name or not description:
                msg="A name and description are required"
                success = False
            elif not has_genome:
                msg="A Genome is required"
                success = False
                
            else:
                user_id=1
                data={}
                is_public=False
                if current_user.is_authenticated:
                    user_id = current_user.id
                   
                else:
                    data["email"]= request.form.get("email")
                    is_public=True
                project_id=create_project(genome,name,
                               type,description,
                               user_id=user_id,is_public=is_public,data=data)
                
    except Exception as e:
        app.logger.exception("Cannot create project")
        success= False
        msg = "There was an error trying to create the project"

    return ujson.dumps({"success":success,"msg":msg,"project_id":project_id})
                 

         
        


@meths.route("/<db>/get_project_data_for_type/<type>")
def get_project_data_for_type(db,type):
    return ujson.dumps(get_project_data_type(db,type))


@meths.route("/get_project_columns_for_type/<type>")
def get_project_columns_for_type(type):
    return ujson.dumps(get_project_columns_type(type))


@meths.route("/get_project_information",methods=["POST"])
def get_project_information():
    params= request.json
    filters= params.get("filters")
    search_term = params.get("search_term")
    offset = params.get("offset")
    limit= params.get("limit")
    order_by=params.get("order_by")
    main_only=params.get("main_only")
    
    #always ask for one more to see if there are any more
    
    
    user_id=None
    is_administrator=False
    if current_user.is_authenticated:
        user_id= current_user.id
        if current_user.administrator:
            is_administrator=True
            
            
    projects = get_projects_summary(user_id,limit+1,offset,filters,
                                    order_by,search_term,is_administrator,
                                    main_only=main_only)
    more=False
    if len(projects)>limit:
        projects=projects[0:limit]
        more=True 
    return ujson.dumps({"projects":projects,"more":more}) 


@meths.route("/update_object/<int:id>",methods=['POST'])
@logged_in_required_method
def update_object(id):
    p=get_project(id)
    if not p.has_edit_permission(current_user):
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    data = request.json
    try:
        for key in data:
            p.set_data(key,data[key])
        return ujson.dumps({"success":True})
    except Exception as e:
        app.logger.exception("There was a problem updating the project {} with data {}".format(id,data))
        return ujson.dumps({"success":False,"msg":"There was an error"})


@meths.route("/delete_object/<int:id>",methods=['GET'])
@logged_in_required_method
def delete_object(id):
    success=True
    p = get_project(id)
    if not p.has_edit_permission(current_user):
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    try:
        p.delete()
    except Exception as e:
        app.logger.exception("There was an error deleting project# {}".format(id))
        success=False
    return ujson.dumps({"success":success})


@meths.route("/get_shared_details_for_object/<int:id>",methods=['GET'])
@logged_in_required_method
def get_share_details_for_object(id):
    p = get_project(id)
    if not p.has_edit_permission(current_user):
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    
    return ujson.dumps(p.get_shared_with())


@meths.route("/update_permission_type_for_object/<int:id>/<int:uid>/<level>",methods=['GET'])
@logged_in_required_method
def update_permission_type_for_object(id,uid,level):
    p = get_project(id)
    if not p.has_edit_permission(current_user):
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    
    return ujson.dumps(p.change_permission_type(level,uid))


@meths.route("/share_object_with/<int:object_id>/<int:user_id>",methods=['GET'])
@logged_in_required_method
def share_object_with(object_id,user_id):
    ret_val = {"success":True}
    try:
        p = get_project(object_id)
        if not p.has_edit_permission(current_user):
            return ujson.dumps({"success":False,"msg":"You do not have permission"})
        p.share_with(user_id)
    except Exception as e:
        app.logger.exception("Could not share object: object id:{},user_id{}".format(object_id,user_id))
        ret_val["success"]=False
    return ujson.dumps(ret_val)


@meths.route("/unshare_object_with/<int:object_id>/<int:user_id>",methods=['GET'])
@logged_in_required_method
def unshare_object_with(object_id,user_id):
    ret_val = {"success":True}
    try:
        p = get_project(object_id)
        if not p.has_edit_permission(current_user):
            return ujson.dumps({"success":False,"msg":"You do not have permission"})
        p.unshare_with(user_id)
    except Exception as e:
        app.logger.exception("Could not share object genome:{},object id:{},user_id{}".format(db,object_id,user_id))
        ret_val["success"]=False
    return ujson.dumps(ret_val) 


@meths.route("/make_object_public/<int:object_id>",methods=['GET'])
@logged_in_required_method
def make_object_public(object_id):
    ret_val = {"success":True}
    try:
        p = get_project(object_id)
        if not p.has_edit_permission(current_user):
            return ujson.dumps({"success":False,"msg":"You do not have permission"})
        p.make_public()
        ret_val["url"] = p.get_url(external=True)
    except Exception as e:
        app.logger.exception("Could not make project public - object id:{}".format(object_id))
        ret_val["success"]=False
        ret_val['message']="There was a problem making the project public"
    return ujson.dumps(ret_val) 
    


   

@meths.route("/get_track_details/<int:project_id>/<int:view_id>")
def get_track_details(project_id,view_id):
    p= get_project(project_id)
    vsid = p.get_viewset_id()
    sql = "SELECT chromosome AS chr, start, finish AS end FROM view_set_{} WHERE id =%s".format(vsid)
    res = databases[p.db].execute_query(sql,(view_id,))
    return ujson.dumps({
        "tracks":p.data["peak_tracks"],
        "position":res[0]
        
    })


@meths.route("/remove_deleted_projects")
@admin_required_method
def remove_deleted_projects():
    sql = "SELECT id FROM projects WHERE is_deleted=True ORDER BY id "
    res = databases['system'].execute_query(sql)
    for r in res:
        p=get_project(r['id'])
        p.delete(True)
    return ujson.dumps({"success":True})





@meths.route("/<db>/fix_tags_in_set/<int:project_id>",methods=['GET','POST'])
@logged_in_required_method
def fix_tags_in_set(db,project_id):
    set_name = request.form.get("set")
    tag_set = request.form.get("tags")
    if tag_set:
        tag_set=ujson.loads(tag_set)
    p = get_project(project_id)
    if not p.has_edit_permission(current_user):
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
        
    vs =ViewSet(db,p.data['viewset_id'])
    set_info=None
    for item in p.data['ml_peak_class']['sets']:
        if item['name']==set_name:
            set_info=item
            break
    tags =vs.add_tags_to_set(set_name,set_info['label'],
                             zegami_url=set_info.get('zegami_url'),
                             tags=tag_set,p=p)
    total=0
    for t in tags:
        total+=tags[t]
    
    set_info['tags_submitted']=True
    
    set_info['tags']=tags
    set_info['tags']['all']=set_info['size']

    tag_field=vs.data["field_information"]['sets'][set_name][set_name+"_tags"]
    p.update()
    return ujson.dumps({"success":True,"set":set_info,"tag_field":tag_field})





########################################################
#################OLD METHODS############################
#########################################################


@meths.route("/<db>/create_tag_set/<int:project_id>",methods=["POST"])
@permission_required_method("create_peak_search_project")
def create_tag_set(db,project_id):
    try:
        p= get_project(project_id)
        parent= request.form.get("parent")
        tag = request.form.get("tag")
        label= request.form.get("label")
        data =p.create_new_tag_set(tag,parent,label,current_user.id)
        return ujson.dumps({"success":True,"data":data})
    except Exception as e:
        app.logger.exception("cannot create tag set database:{}  project:{}".format(db,project_id))
        return ujson.dumps({"success":False,"msg":"Could not create set"})
        
    
    
@meths.route("/<db>/check_tag_set_clustering/<int:job_id>",methods=["POST"])
@permission_required_method("create_peak_search_project")
def check_tag_set_clustering(db,job_id):
    try:
        job = get_job(job_id)
        job.check_status()
        if job.job.status=="complete":
            si = job.job.inputs['set_info']
            project_id=si[0]
            set= si[1]
          
            p= get_project(project_id)
            vs_id= p.data['initial_peak_calls']['view_set_id']
            vs = ViewSet(db,vs_id)
            fields= vs.data['field_information']["sets"][set]
            sql ="SELECT id,{},{},{},{},{} from {} WHERE {}='True'".format(fields[set+"_tSNE1"],fields[set+"_tSNE2"],
                                                                   fields[set+"_PCA1"],fields[set+"_PCA2"],
                                                                   fields['is_set'],
                                                                   vs.table_name,fields['is_set'])
            results = databases[db].execute_query(sql)
            ret_dict={}
            for r in results:
                i= r['id']
                del r['id']
                ret_dict[i]=r
            
            set_info=None
            for item in p.data['ml_peak_class']['sets']:
                if item["name"]==set:
                    set_info=item      
            return ujson.dumps({"complete":True,"data":ret_dict,"fields":fields,"set":set_info})
        else:
            return ujson.dumps({"complete":False})    
    except Exception as e:
        app.logger.exception("cannot processs job".format(db,project_id))
        return ujson.dumps({"success":False,"msg":"Could not create set"}) 
    


@meths.route("/check_tag_set_classifying/<int:job_id>",methods=["POST"])
@permission_required_method("create_peak_search_project")
def check_tag_set_classifying(job_id):
    try:
        job = get_job(job_id)
        job.check_status()
        if job.job.status=="complete" or job.job.status=="failed":
            project_id= job.job.inputs['project_id']     
            set=job.job.inputs['set']  
            set_info=None
            p= get_project(project_id)
            for item in p.data['ml_peak_class']['sets']:
                if item['name']==set:
                    set_info=item
                           
            data=None
            if request.form.get("get_fields"):
                data = p.get_set_data(set)
            return ujson.dumps({"complete":True,"set":set_info,"field_data":data})
        else:         
            return ujson.dumps({"complete":False}) 
    except Exception as e:
        app.logger.exception("cannot processs job".format(db,project_id))
        return ujson.dumps({"success":False,"msg":"Could not create set"}) 






@meths.route("/<db>/create_new_zegami_set/<project_id>/<tag>/<parent>",methods=['GET'])
@permission_required_method("create_peak_search_project")
def create_new_zegami_set(db,project_id,tag,parent):
    p = Project(db,int(project_id))
    sets = p.data['ml_peak_class']['sets']
    vs = ViewSet(db,p.data['initial_peak_calls']['view_set_id'])
    name = "set_{}".format(len(sets))
    bed_file=vs.create_new_zegami_set(tag,name)
    
    num = len(sets)
    set_info={
        "name":name,
        "tags":{},
        "created_from":[parent,tag]
        
    }
    job_data={
                "bed_file":bed_file,
                "wig_file":p.data['local_wig_file'],
                "chromosome":p.data['parameter_search']['original_chromosome'],
                "view_set_id":vs.id,
                "ml_step":"False",
                "set_info":[p.id,name]
            }
    
    pcj = PeakClusteringJob(data=job_data,user_id=current_user.id,genome=db)
    set_info["clustering_job_id"]=pcj.job.id
    set_info["clustering_job"]="running"
    sets.append(set_info)
    p.update({"status":"Creating {}".format(name)})
    pcj.send()
    return ujson.dumps({"success":True,"job_id":pcj.job.id})



