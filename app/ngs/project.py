from app import databases,app,db
from app.jobs.email import send_email
import ujson,copy,shutil
from os import name
from app.databases.user_models import User
from app.ngs.view import ViewSet,create_view_set_from_file,parse_extra_fields
import datetime,shlex
from sqlalchemy import text
from app.zegami.zegamiupload import create_new_set,update_collection,delete_collection
import os
from app.ngs.utils import create_bigbed_wid,get_temporary_folder,get_track_proxy,get_reverse_track_proxy
import pyBigWig
import requests
import string
import math
import random
from urllib.parse import urlparse
from app.ngs.genome import get_genomes
from functools import cmp_to_key
from app.ngs.track import validate_track_file_ucsc

from shutil import copyfile
from distutils.dir_util import copy_tree



project_base_columns=[
            {"id":"c1","field":"name","name":"Name","width":100,"datatype":"text","sortable":True,"filterable":True},
            {"id":"c2","field":"genome","name":"Genome","width":100,"datatype":"text","sortable":True,"filterable":True},
            {"id":"c3","field":"description","name":"Description","datatype":"text","width":250,"sortable":True,"filterable":True},
            {"id":"c4","field":"date_added","name":"Date","datatype":"date","width":100,"sortable":True,"filterable":True},
            {"id":"c6","field":"user","name":"User","datatype":"text","width":100,"sortable":True,"filterable":True}          
]

projects = {}


def get_projects_summary(user_id=None,limit=5,offset=0,filters={},
                         order_by=None,search_term="",is_administrator=False,
                         extra_fields="",main_only=False):
    #get projects that are public
    
    
    main_projects= []
    allowed=[]
    if user_id and not is_administrator:    
        sql = "SELECT value FROM permissions WHERE permission = 'view_project_type' AND user_id=%s"
        perms= databases["system"].execute_query(sql,(user_id,))
        for perm in perms:
            allowed.append(perm["value"])
    for name in app.config['MLV_PROJECTS']:
        proj = app.config['MLV_PROJECTS'][name]
        if proj.get("main_project"):
            if proj.get("is_public"):
                main_projects.append(name)
            else:
                if  user_id == None:
                    continue
                if is_administrator or name in allowed:
                    main_projects.append(name)
            
    main_projects= "('"+"','".join(main_projects)+"')"
    vars=()
    
    sql = ("SELECT projects.id AS id,projects.name AS name,description,to_char(date_made_public,'YYYY-MM-DD') AS date_made_public"
     ",status,users.first_name AS firstname ,users.last_name AS lastname,to_char(projects.date_added,'YYYY-MM-DD') AS date_added"
     ",projects.is_public AS is_public,projects.type AS type,genomes.label AS genome, projects.owner AS owner,genomes.small_icon"
     " AS genome_icon{} FROM projects INNER JOIN"
     " users ON projects.owner=users.id INNER JOIN genomes ON projects.genome = genomes.name").format(extra_fields)
   
    if user_id==None:
        sql+= " WHERE projects.is_public=True AND"
    else:
        sql+=" LEFT JOIN shared_objects on shared_objects.shared_with={} AND shared_objects.object_id=projects.id WHERE".format(user_id)
      
    sql+=" projects.is_deleted=False"
    if main_only:
        sql+=" AND projects.type IN {}".format(main_projects)  
    #permission filters
    if user_id != None and filters.get("perms"):
        if filters['perms'] == "shared":
            sql+= " AND shared_objects.shared_with={}".format(user_id)
        
        elif filters['perms']  == "mine":
            sql+= " AND projects.owner={}".format(user_id)
    
        elif filters['perms']=="public":
            sql+= " AND projects.is_public=True"
        
    if user_id !=None and not is_administrator:
            sql+=" AND (shared_objects.shared_with={} OR projects.owner={} OR projects.is_public=True)".format(user_id,user_id)
    if not is_administrator:
        sql+=" AND projects.owner!=1"    
    
    genome= filters.get("genome")
    if genome:
        sql+= " AND projects.genome=%s"
        vars+=(genome,)
        
    project_type=filters.get("type")
    
    if filters.get("is_deleted"):
        sql+=" AND projects.is_deleted=True"
    
    if filters.get("project_ids"):
        sql+=" AND projects.id = ANY(%s)"
        vars+=(filters.get("project_ids"),)
    
    if project_type:
        if isinstance(project_type,list):
            sql+= " AND projects.type = ANY(%s)"
        else:
            sql += " AND projects.type=%s"
        vars+=(project_type,)
        
    userid= filters.get("user_id")
    if userid:
        sql+=" AND users.id=%s"
        vars+=(userid,);  
    
    if search_term:
        vars  +=("%"+search_term+"%","%"+search_term+"%")
        sql+= " AND (projects.name ILIKE %s OR projects.description ILIKE %s)"
    
    if order_by:
        sql+=" ORDER BY {}".format(order_by)
    else:
        sql+=" ORDER BY projects.date_added DESC"
       
    sql += " LIMIT {} OFFSET {}".format(int(limit),int(offset))
        
    results = databases["system"].execute_query(sql,vars)
    
   
    
    info = app.config['MLV_PROJECTS']
    for res in results:
        res['type_label']=info[res['type']]["label"]
        res['large_icon']=info[res['type']]["large_icon"]
        res['is_mine']= (user_id==res['owner'])
        res['user']="{} {}".format(res['firstname'],res["lastname"])
    
    return results
        
         
def create_project(db,name,type,description="",data={},
                   user_id=0,status = "new",returning_object=False,is_public=False):
    sql = "INSERT into projects (name,type,description,data,owner,status,genome,is_public) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
    id = databases["system"].execute_insert(sql,(name,type,description,ujson.dumps(data),user_id,status,db,is_public))
    if returning_object:
        return get_project(id)
    else:
        return id

class GenericObject(object):
    def __init__(self,id=None,res=None):
        if not res:
            sql = "SELECT * FROM {} WHERE id=%s".format(type)
            res=databases["system"].execute_query(sql,(id,))[0]
        else:
            id =res['id']
        self.id=id
        self.db=res['genome']
        self.description=res['description']
        self.data=res['data']
        self.name=res['name']
        self.type=res.get('type')
        self.is_public=res['is_public']
        self.owner=res['owner']
        self.status= res['status']
        self.date_added=res['date_added'].strftime("%Y-%m-%d")
        self.parent=res['parent']
    
    def has_edit_permission(self,user):
        if not user.is_authenticated:
            return False
        if not self.has_type_permission(user):
            return False
        if user.id == self.owner or user.administrator:
            return True
        else:
            perm=self
            if self.parent:
                perm=get_project(self.parent)
            sql = "SELECT id FROM shared_objects WHERE object_id={} AND level='edit' AND shared_with={}".format(perm.id,user.id)
            results= databases['system'].execute_query(sql)
            return len(results)>0
    
    
    def get_data(self):
        self.data["genome"]=self.db
        return self.data
    
    
    def execute_action(self,method,user,args={}):
        from app.jobs.celery_tasks import execute_action_async
        meth_info = self.methods.get(method)
        ret_obj={"success":True}
        if not meth_info:
            ret_obj["msg"]="Method does not exist"
            ret_obj["success"]=False
        elif meth_info["permission"]=="view" and not self.has_view_permission(user):
            ret_obj["msg"]="You do not have permission"
            ret_obj["success"]=False
        elif meth_info["permission"]=="edit" and not self.has_edit_permission(user):
            ret_obj["msg"]="You do not have permission"
            ret_obj["success"]=False
        elif meth_info["permission"]=="allow_anonymous":
            if self.owner !=1 and not self.has_edit_permission(user):
                ret_obj["msg"]="You do not have permission"
                ret_obj["success"]=False
            
            
        if not ret_obj["success"]:
            return ret_obj
        
        permission = meth_info.get("needs_permission")
        if permission:
            if not user.has_permission(permission):
                return {
                    "success":False,
                    "msg":"You need an adminstrator to give you permission"
                }
                
                
        run_flag = meth_info.get("running_flag")
        
        #this should be updated straight away and removed
        project_data = args.get("project_data")
        if project_data:
            for k in project_data:
                self.data[k]=project_data[k]
            if project_data.get("genome"):
                self.update({"genome":project_data["genome"]})
            else:
                self.update()
            del args["project_data"]
        if meth_info.get("user_required"):
            args["user"]=user
        if run_flag:
            self.set_data(run_flag[0],run_flag[1])  
        if meth_info.get("async") and app.config["USE_CELERY"]:
            execute_action_async.delay(self.id,method,args)
            ret_obj["success"]=True
        else:
            try:
                meth= getattr(self,method)
                data =meth(**args)
                ret_obj["success"]=True
                ret_obj["data"]=data
            except Exception as e:
                ret_obj["msg"]="There was a problem"
                ret_obj["success"]=False
                app.logger.exception("error")
            
        return ret_obj
    
    def get_permissions(self,user):
        '''Checks whether the supplied user has permission to view or edit the object
        Args:
            user (current_user): The current user
        Returns:
            Either 'view', 'edit' , 'view_no_log_in' (a non authenticated user
            and a public project' or None (no permissions)
        '''
        perm=self
        if self.parent:
            perm=get_project(self.parent)
        if not perm.has_type_permission(user):
            return None
        if not user.is_authenticated:
            if perm.is_public:
                return "view_no_log_in"
            else:
                return None
        else:
            if user.id== perm.owner or user.administrator:
                return "edit"
            
            else:
                sql = "SELECT level FROM shared_objects WHERE object_id={} and shared_with={}".format(perm.id,user.id)
                results= databases['system'].execute_query(sql)
                if len(results)==0:
                    if perm.is_public:
                        return "view"
                    else:
                        return None
                else:
                    return results[0]["level"]
    
    def has_type_permission(self,user):
        info = app.config["MLV_PROJECTS"][self.type]
        if info.get("is_public"):
            return True
        if not user.is_authenticated:
            return False
        if not user.administrator:
            sql = "SELECT id from permissions WHERE permission='view_project_type' AND value=%s AND user_id=%s"
            res= databases["system"].execute_query(sql,(self.type,user.id))
            if len(res)==0:
                return False
                
        return True 
    
    def has_view_permission(self,user):
        perm=self
        if self.parent:
            perm=get_project(self.parent)
    
        #Is this project type public
        if not perm.has_type_permission(user):
            return False
        
        if perm.is_public:
            return True
        if not user.is_authenticated:
            return False
        if user.id == perm.owner or user.administrator:
            return True
        #is the object shared with the user
        sql = "SELECT id FROM shared_objects WHERE object_id={} AND shared_with={}".format(self.id,user.id)
        results= databases['system'].execute_query(sql)
        return len(results)>0
    
    def get_shared_with(self):
        sql =("SELECT shared_with as uid,first_name,last_name,level FROM shared_objects"
             " INNER JOIN users on shared_with=users.id WHERE object_id={}").format(self.id)
        results = db.engine.execute(sql)
        ret_list=[]
        for res in results:
            ret_list.append({"uid":res.uid,"last_name":res.last_name,"first_name":res.first_name,"level":res.level})
        return ret_list
    
    def change_permission_type(self,type,uid):
        sql = "UPDATE shared_objects SET level=%s WHERE object_id=%s AND shared_with=%s"
        databases["system"].execute_update(sql,(type,self.id,uid))
        return ({"success":True})
        
    
    def share_with(self,user_id):
        sql = ("INSERT into shared_objects (owner,shared_with,object_id)"
               "VALUES(%s,%s,%s)")
        new_id = databases["system"].execute_insert(sql,(self.owner,user_id,self.id))
        return new_id !=-1
     
        
    def unshare_with(self,user_id):
        sql = "SELECT id FROM shared_objects WHERE shared_with=%s AND object_id=%s"
        pid = databases["system"].execute_query(sql,(user_id,self.id))
        if len(pid) !=0:
            databases["system"].delete_by_id("shared_objects",[pid[0]['id']])
            
    def unshare_all(self):
        sql= "DELETE from shared_objects WHERE object_id={}".format(self.id)
        databases["system"].execute_update(sql)       
            
    def get_url(self,external=False):
        url = "/projects/"+self.type+"/"+str(self.id)
        if external:
            host_name= None
            p_h_n = app.config.get("PROJECT_SPECIFIC_HOST_NAME")
            if p_h_n:
                host_name = p_h_n.get(self.type)
            if not host_name: 
                host_name=app.config['HOST_NAME']
            
            url="http://"+host_name+url
        return url
        
    def get_folder(self,subfolder=None,create=True):
        '''Get the folder associated with this project. One will be created if it
        does not exist.
        Args:
            subfolder(str): 
        
        '''
        folder = os.path.join(app.config['DATA_FOLDER'],self.db,"projects",str(self.id))
        if subfolder:
            folder=os.path.join(folder,subfolder)
        if not os.path.exists(folder) and create:
            os.makedirs(folder)
        return folder
    
    def delete_folder(self):
        folder = os.path.join(app.config['DATA_FOLDER'],self.db,"projects",str(self.id))
        if os.path.exists(folder):
            shutil.rmtree(folder)
        folder =os.path.join(app.config["TRACKS_FOLDER"],"projects",str(self.id))
        if os.path.exists(folder):
            shutil.rmtree(folder)
            
        
     
    def make_public(self):
        now = datetime.datetime.now()
        sql = "UPDATE projects SET is_public=True,date_made_public=%s WHERE id=%s"
        databases["system"].execute_update(sql,(now,self.id))
        
    def delete(self,hard=False):
        if not hard:
            sql= "UPDATE projects SET is_deleted=True WHERE id=%s"
            return databases["system"].execute_update(sql,(self.id,))
        else:
            self.delete_folder()
            self.unshare_all()
            sql="DELETE FROM projects WHERE id ={}".format(self.id)
            databases["system"].execute_update(sql)
    
            
            
    
    def update(self,fields=None):
        '''Updates the database with the projects data
        Args:
           fields(Optional[dict]): A dictionary where keys
           correspond to column names and the values to 
           be updated
        '''
        if not fields:
            sql ="UPDATE projects SET data=%s WHERE id =%s"
            vars=(ujson.dumps(self.data),self.id)
            databases["system"].execute_update(sql,vars)
        else:
            fields['id']=self.id
            fields['data']=ujson.dumps(self.data)
            databases["system"].update_table_with_dicts([fields],"projects")
    
    
    def set_data(self,param,value):
        '''Updates the 'data' dictionary of the view set in
        the database.
        Args:
            param(str): The name of parameter (dictionary key)
            value: the parameter's value
        '''
        sql = "SELECT data from projects WHERE id = %s"
        results = databases["system"].execute_query(sql,(self.id,))
        data = results[0]['data']
        data[param]=value
            
        sql= "UPDATE projects SET data=%s WHERE id = %s"
        vars= (ujson.dumps(data),self.id)
        databases["system"].execute_update(sql,vars)
        self.data=data
    
    
    def update_field(self,param):
        item =self.data.get(param[0])
        if len(param)>1:
            for p in param[1:]:
                item = item.get(p)
        path= ",".join(param)
        sql = "UPDATE projects SET data = jsonb_set(data,'{{{}}}','{}') WHERE id = {}".format(path,ujson.dumps(item),self.id)
        print (sql)
        
    
    def refresh_data(self):
        sql = "SELECT data from projects WHERE id =%s"
        results = databases["system"].execute_query(sql,(self.id,))
        self.data = results[0]['data']
        
    
    def create_compound_column(self,stages=[],name="",final_trans="none",history={}):
        vs = ViewSet(self.db,self.get_viewset_id())
        data= vs.create_compound_column(name,stages,final_trans)
        history["status"]="complete"
        history["tracks"]=[]
        f= data["columns"][0]["field"]
        history["fields"]=[f]
        history["id"]=f
        history["graphs"]=[data["graphs"][0]["id"]]
        self.add_to_history(history)
        data["history"]=history
        return data
    
    
    def delete_columns(self,columns=[]):
        vs = ViewSet(self.db,self.get_viewset_id())
        vs.remove_columns(columns)
        self.refresh_data()
       
        new_graphs=[]
        for g in self.data["graph_config"]:
            param= g.get("param")
            
            if param :
                contains_field=False
                if isinstance(param, list):
                    for p in param:
                        if p in columns:
                            contains_field=True
                            break
                    else:
                        if param in columns:
                            contains_field=True
                if contains_field:
                    continue
               
            new_graphs.append(g)
        if len(self.data["graph_config"]) != len(new_graphs):
            self.data["graph_config"]=new_graphs
            self.update()
            
        
        history=self.data.get("history")
        if history:
            new_history=[]
            for h in history:
                if h["id"] in columns:
                    continue
                new_history.append(h)
            
            self.set_data("history",new_history)
        return self.data["history"]
    
    #need a subclass for the following
    def add_tagging_column(self):
        vs = ViewSet(self.db,self.get_viewset_id())
        l_to_f=vs.add_columns(
            [{"label":"Tags","datatype":"text"}],
            "current_tags"   
        )
        field = l_to_f["Tags"]
        if not self.data.get("graph_config"):
            self.data["graph_config"]=[]
        self.data["graph_config"].append({
                "type":"row_chart",
                "title":"Tags",
                "param":field,
                "id":"current_tags"
            })
        self.update()
    
    
    def add_gene_track(self,tracks):
         if self.db != "other":
                tracks.append(
                    {
                        "format": "feature",
                        "url": "/meths/{}/get_genes".format(self.db),
                        "displayMode": "EXPANDED",
                        "discrete":True,
                        "short_label": "Ref Genes",
                        "height": 30,
                        "color": "#000000",
                        "track_id": "ref_genes",
                        "type": "custom_annotation"
                        
                    }   
                )
        
    
    def update_tags(self,tags={},tag_color_scheme={}):
        vs = ViewSet(self.db,self.get_viewset_id())
        ctf = vs.data["field_information"]["current_tags"]["Tags"]
        update_list=[]
        for id in tags:
            update_list.append({"id":id,ctf:tags[id]})
        sql =  "UPDATE {} SET {}=NULL".format(vs.table_name,ctf)
        databases[self.db].execute_update(sql)
        databases[self.db].update_table_with_dicts(update_list,vs.table_name)
        self.set_data("tag_color_scheme",tag_color_scheme)
        
    
    def get_chrom_file(self):
        '''Returns the location of the chromosome file (tab limited chr name,size.
        A file will be created from the project's original_wig if one does not exist
        '''
        if self.db != "other":
            return os.path.join(app.config["DATA_FOLDER"],self.db,"custom.chrom.sizes")
    
    
    
    def get_tracks_folder(self,create=True):
        folder = os.path.join(app.config['TRACKS_FOLDER'],"projects",str(self.id))
        if not os.path.exists(folder) and create:
            os.makedirs(folder)
        return folder
    
    def get_main_wig_track(self):
        return None
    
    def get_viewset_id(self):
        return self.data.get("viewset_id")
    
    def get_viewset(self,filters=None,offset=None,limit=None):
        
       
        vs=ViewSet(self.db,self.get_viewset_id())
        if (offset or offset==0) and limit:
            off_lim=[int(offset),int(limit)]
          
            if offset==0:
                
                return {
                    "views":vs.get_all_views(filters=filters,offset=off_lim),
                    "field_information":vs.data["field_information"],
                    "fields":vs.fields,
                    "sprite_sheets":vs.data.get("sprite_sheets"),
                    "annotation_information":vs.data.get("annotation_information"),
                    "base_image_url":"/data/{}/view_sets/{}/thumbnails/tn".format(self.db,vs.id),
                    "total":  vs.get_view_number()["count"]
                }
            else:
                return vs.get_all_views(filters=filters,offset=off_lim)
        
                
                
                
                
        else:
            return {
                "views":vs.get_all_views(filters=filters),
                "field_information":vs.data["field_information"],
                "fields":vs.fields,
                "sprite_sheets":vs.data.get("sprite_sheets"),
                "annotation_information":vs.data.get("annotation_information"),
                "base_image_url":"/data/{}/view_sets/{}/thumbnails/tn".format(self.db,vs.id)
            }
    
    def add_intersections(self,ids,ec):
        vs = ViewSet(self.db,self.get_viewset_id())
       
        if ec:
            data= vs.add_annotation_fields(ids[0],ec)
        else:
            data= vs.add_annotations_intersect(ids)
            
        self.refresh_data()
        self.data["graph_config"]+=data["graphs"]
        self.data["browser_config"]["state"]+=data["tracks"]
        self.update()
        tracks=[]
        graphs=[]
        for t in data["tracks"]:
            tracks.append(t["track_id"])
        for g in data["graphs"]:
            graphs.append(g["id"])
            
        return {
            "graphs":graphs,
            "tracks":tracks,
            "fields":data["fields"]
            
        }
        
        
    def cluster_by_fields(self,fields,name,methods,dimensions):
        vs = ViewSet(self.db,self.get_viewset_id())
        info = vs.cluster_by_fields(fields,name,methods,dimensions)
        self.refresh_data()
        graphs=[]
        fds=[]
        for cols in info:
            gid= cols["method"]+"_"+random_string(5)
            self.data["graph_config"].append({
                    "type":"wgl_scatter_plot",
                    "title":name + " " + cols["method"],
                    "param":[cols["fields"][0],cols["fields"][1]],
                    "id":gid,
                    "axis":{
                        "x_label":cols["labels"][0],
                        "y_label":cols["labels"][1]
                    },
                    "location":{
                        "x":0,
                        "y":0,
                        "height":4,
                        "width":6
                    }
                
            })
            graphs.append(gid)
            for f in cols["fields"]:
                fds.append(f)
                
        field_names=[]
        for f in fields:
            field_names.append(vs.fields[f]["label"])
        
        gid= "abc_"+random_string(5)
        graphs.append(gid)
        self.data["graph_config"].append({
            "type":"average_bar_chart",
            "title":name+" Fields",
            "param":fields,
            "labels":field_names,
            "id":gid,
            "location":{
                "x":0,
                "y":0,
                "height":2,
                "width":4
            }
        })
     
        self.update()
        return {
            "graphs":graphs,
            "tarcks":[],
            "fields":fds
            
        }          
        
        
    
    def add_annotation_intersections(self,ids=[],extra_columns=None):
        from app.jobs.jobs import AnnotationIntersectionJob
        j= AnnotationIntersectionJob(inputs={"project_id":self.id,"ids":ids,"extra_columns":extra_columns},
                                     user_id=self.owner,
                                     genome=self.db)
        j.send()
        return j.job.id
    

    def find_tss_distances(self,go_levels=0):
        from app.jobs.jobs import FindTSSDistancesJob
        go_levels=int(go_levels)
        j= FindTSSDistancesJob(inputs={"project_id":self.id,"go_levels":go_levels},user_id=self.owner,genome=self.db)
        self.set_data("find_tss_distances_job_id",j.job.id)
        self.set_data("find_tss_distances_job_status","running")
        j.send()
        return j.job.id
    
    
    def add_remove_item(self,item={},type="graph",action="add",history=None):     
        self.refresh_data()
        store = self.data["graph_config"]
        id_name="id"
        if type =="track":
            store=self.data["browser_config"]["state"]
            id_name="track_id"
       
        if action=="add":
            store.append(item)
            self.update()
            if history:
                self.add_to_history(history)              
        else:
            index =-1
            for i,graph in enumerate(store):
                if item[id_name]==graph[id_name]:
                    index=i
                    break
            if index !=-1:
                del store[index]
            if history:
                index=-1
                for i,hi in enumerate(self.data["history"]):
                     if hi["id"]==history:
                        index=i
                        break
                if index != -1:   
                    del self.data["history"][index]
                
            self.update()
        
                     
    
    

    
    def get_fields(self):
        vsid=self.get_viewset_id()
        
        if vsid:
            ret_list=[]
            vs = ViewSet(self.db,vsid)
            for field in vs.fields:
                item =vs.fields[field]
                item["name"]=item["label"]
                del item["label"]
                item["field"]=field
                ret_list.append(item)
            return ret_list
        else:
            return []
    
    def delete_tss_distances(self):
        vs = ViewSet(self.db,self.get_viewset_id())
        fields = vs.data["field_information"].get("TSS").values()
        vs.remove_columns(fields)
        del vs.data["field_information"]["TSS"]
        vs.update()
        new_charts=[]
        for chart in self.data["graph_config"]:
            if chart['id'].startswith("_tss"):
                continue
            new_charts.append(chart)
        self.data["graph_config"]=new_charts
        del self.data["find_tss_distances_job_id"]
        del self.data["find_tss_distances_job_status"]
        self.update()
        
    
    def get_tss_distances(self):
        vs = ViewSet(self.db,self.get_viewset_id())
        return vs.get_tss_data()
        
     
    def remove_annotation_intersections(self,ids):
        vs = ViewSet(self.db,self.get_viewset_id())
        info = vs.data["annotation_information"]
        for aid in ids:
            anno = info.get(str(aid))
            if not anno:
                continue
            del vs.data["field_information"]["Annotations"][anno["label"]]
            del vs.data["annotation_information"][aid]
            vs.remove_columns([anno['field']])        
        vs.update() 
            
            
            
    def remove_items(self,ids=[]):
        vs = ViewSet(self.db,self.get_viewset_id())
        vs.remove_items(ids)
        self.create_anno_bed_file(force=True)
       
        
        
               
    def create_anno_bed_file(self,force=False):
        vs = ViewSet(self.db,self.get_viewset_id())
        vbf = vs.get_bed_file(force)
        pbf = os.path.join(self.get_tracks_folder(),"anno_{}.bed.gz".format(self.id))
        copyfile(vbf,pbf)
        copyfile(vbf+".tbi",pbf+".tbi")
        self.set_data("bed_file",pbf)


    def create_subset_from_parent(self,ids=[],parent_id=None):
        try:
            p = get_project(parent_id)
            user= db.session.query(User).filter_by(id=self.owner).one()
            if not p.has_view_permission(user):
                raise Exception("User does not have permission on parent to create subset")
            #copy data
            self.data=p.data
            self.data["creating_subset"]=True
            self.update({"parent":parent_id})
            
            #copy viewset
            vs = ViewSet(p.db,p.get_viewset_id())
            new_vs = vs.clone(ids,"cloned from "+p.name)
            self.set_data("viewset_id",new_vs.id)
            
            #copy any specific files
            self.copy_files(p,new_vs)
            self.set_data("creating_subset",False)
        except Exception as e:
            app.logger.exception("Creating subset #{} from parent#{}".format(self.id,parent_id))
            self.set_data("subset_creation_failed",True)
        
    
    def copy_files(self,parent,new_vs):
        pass
    
    def get_annotation_intersections(self,ids=[]):
        vs =ViewSet(self.db,self.get_viewset_id())
        return vs.get_annotation_data(ids)
        
    def make_ucsc_images(self,margins=1000,image_width=500,session_url=""):
        from app.jobs.jobs import UCSCImagesJob
            
        inputs={
            "margins":margins,
            "image_width":image_width,
            "session_url":session_url,
            "project_id":self.id
            
        }
        j=UCSCImagesJob(genome=self.db,user_id=self.owner,inputs=inputs)
        self.set_data("creating_images_job_id",j.job.id)
        self.set_data("creating_images_job_status","running")
        j.send()
        
        return j.job.id
    
    def make_mlv_images(self,tracks=[],margins=1000,image_width=500):
        from app.jobs.jobs import MLVImagesJob
            
        inputs={
            "margins":margins,
            "image_width":image_width,
            "tracks":tracks,
            "project_id":self.id
            
        }
        j=MLVImagesJob(genome=self.db,user_id=self.owner,inputs=inputs)
        self.set_data("creating_images_job_id",j.job.id)
        self.set_data("creating_images_job_status","running")
        j.send()
        
        return j.job.id
        
    def upload_zegami_collection(self,project="",password="",username=""):
        from app.jobs.jobs import CreateZegamiCollectionJob
        from app.zegami.zegamiupload import get_client
        client =get_client({
            "project":project,
            "username":username,
            "password":password
        })
        if not client:
            return {"log_in_failed":True}
        inputs={
            "project":project,
            "username":username,
            "project_id":self.id
        }
        j=CreateZegamiCollectionJob(genome=self.db,user_id=self.owner,inputs=inputs)
        j.send(password)
        return {}

    def add_bw_stats(self,url,name):
        #copy wigfile
        file_name = os.path.split(url)[1]
        folder = os.path.join(app.config['TRACKS_FOLDER'],"projects",str(self.id))
        if not os.path.exists(folder):
            os.makedirs(folder)
        local_file = os.path.join(folder,file_name)
        url = shlex.quote(url)                 
        command = "curl {} -o {}".format(url,local_file)
        os.system(command)
        self.refresh_data()
        tid= random_string(5)
        self.data["browser_config"]["state"].append({
                "url":local_file.replace("/data",""),
                "track_id":tid,
                "discrete":True,
                "height":100,
                "color":"#808080",
                "scale":"dynamic",
                "short_label":name,
                "type":"bigwig",
                "allow_user_remove":True,
                "format":"wig"
        })
        self.update()
        vs =ViewSet(self.db,self.get_viewset_id())
        fields= vs.add_wig_stats(local_file,name)
        
        return {
            "fields":fields,
            "track":tid
        }
    
    def add_to_history(self,info):
        self.refresh_data()
        h= self.data.get("history",[])
        if not info.get("id"):
            hid= random_string(5)  
            info["id"]= hid
        h.append(info)
        self.set_data("history",h)
        return info["id"]
        
     
    def get_history(self,hid):
        for h in self.data["history"]:
            if h["id"]==hid:
                return h
     
    def delete_history_item(self,history_id=""):
        h= self.get_history(history_id)
        if h.get("tracks") and len(h.get("tracks"))>0:
            new_tracks=[]
            for t in self.data["browser_config"]["state"]:
                if t["track_id"] not in h["tracks"]:
                    new_tracks.append(t) 
            self.data["browser_config"]["state"]=new_tracks
        if h.get("graphs"):
            new_graphs=[]
            for g in self.data["graph_config"]:
                if g["id"] not in h["graphs"]:
                    new_graphs.append(g)
            self.data["graph_config"]=new_graphs
        self.update()
        if h.get("fields") and len(h.get("fields"))>0:
             self.delete_columns(h.get("fields"))
        index=-1
        self.refresh_data() 
        for i,hi in enumerate(self.data["history"]):
            if hi["id"]==history_id:
                index=i
                break
        del self.data["history"][index]
        self.update()
        
      
    def get_bw_stats_data(self,job_id=0):
        from app.jobs.jobs import get_job
        j=get_job(job_id)
        wig_names=j.get_input_parameter("wig_names")
        vs= ViewSet(self.db,self.get_viewset_id())
        data=vs.get_wig_stats_data(wig_names)
        wig_files=[]
        for track in self.data["browser_config"]["state"]:
            if track['track_id'] in wig_names:
                wig_files.append(track)
        data["tracks"]=wig_files
        return data
    
    
    def get_cluster_data(self,job_id=0):
        from app.jobs.jobs import get_job
        j=get_job(job_id)
        name=j.get_input_parameter("name")
        methods=j.get_input_parameter("methods")
        vs= ViewSet(self.db,self.get_viewset_id())
        data=vs.get_cluster_data(name,methods)
        graph_ids=[]
        graphs=[]
        field_graph= name+"_fields"
        for method in methods:
            graph_ids.append(name+"_"+method)
        for graph in self.data["graph_config"]:
            if graph['id'] in graph_ids:
                graphs.append(graph)
            if graph["id"]==field_graph:
                graphs.append(graph)
        data["graphs"]=graphs
        return data
        
     
     
    def initiate_job(self,job=None,inputs={}):   
        from app.jobs.jobs import job_types
        j_class= job_types[job]
        inputs["project_id"]=self.id
        j= j_class(genome=self.db,user_id=self.owner,inputs=inputs)
        history={"status":"running"}
        self.add_to_history(history)
        j.label_history(history)
        self.update()
        j.send()
        return history
    
    
    def check_job_finished(self,job_id=0,user=None):
        from app.jobs.jobs import get_job
        j= get_job(job_id)
        history = self.get_history(j.get_output_parameter("history_id"))
        if j.has_permission(user):
            status = j.check_status()
            if status=="complete":
                history = self.get_history(j.get_output_parameter("history_id"))
                vs= ViewSet(self.db,self.get_viewset_id())
                c_d={"data":[],"columns":[]}
                if len(history["fields"])>0:
                    c_d = vs.get_columns_and_data(history["fields"])
                graphs=[]
                tracks=[]
                for g in self.data["graph_config"]:
                    if g["id"] in history["graphs"]:
                        graphs.append(g)
                for t in self.data["browser_config"]["state"]:
                    if t["track_id"] in history["tracks"]:
                        tracks.append(t)
                    
                return {
                    "status":"complete",
                    "columns":c_d["columns"],
                    "data":c_d["data"],
                    "tracks":tracks,
                    "graphs":graphs,
                    "history":history
                    
                }   
                
            else:
                return {"status":status,"history":history}
            
        
    def send_peak_stats_job(self,wig_locations=[],wig_names=[]):
        from app.jobs.jobs import PeakStatsJob
        for wl in wig_locations:
            res = validate_track_file_ucsc(wl)
            if not res["valid"]:
                raise Exception("BigWig not valid")
        inputs={
            "wig_locations":wig_locations,
            "wig_names":wig_names,
            "project_id":self.id
        }
        j= PeakStatsJob(genome=self.db,user_id=self.owner,inputs=inputs)
        j.send()
        jid= j.job.id
        self.set_data("peak_stats_job_status","running")
        self.set_data("peak_stats_job_id",jid)
        return jid
    
    def send_cluster_by_fields_job(self,fields=[],name="",methods=["UMAP"],dimensions=2):
        from app.jobs.jobs import ClusterByFieldsJob
        inputs={
            "project_id":self.id,
            "name":name,
            "fields":fields,
            "methods":methods,
            "dimensions":dimensions
        }
        j= ClusterByFieldsJob(genome=self.db,user_id=self.owner,inputs=inputs)
        j.send()
        jid= j.job.id
        self.set_data("cluster_by_fields_job_status","running")
        self.set_data("cluster_by_fields_job_id",jid)
        return jid
    
        
        
GenericObject.methods={
    "add_remove_item":{   
        "permission":"edit"   
    },
    "initiate_job":{   
        "permission":"edit"   
    },
    "check_job_finished":{   
        "permission":"edit",
        "user_required":True 
    },
    "delete_history_item":{
        "permission":"edit"
    }
}      
      
       
def get_project(id):
    '''Returns the project specified by the id. The preferred
    way of getting a project, rather than using a constructor
    Args:
        id(int): The id of the project
    Returns:
        An object, whose type depends on the project's type
    '''
    sql = "SELECT * FROM projects WHERE id=%s"
    res=databases["system"].execute_query(sql,(id,))
    if len(res)==0:
        return None
    res = res[0]
    class_type= _get_class(res["type"])
    return class_type(res=res)


def get_projects(ids):
    sql = "SELECT * FROM projects WHERE id=ANY(%s)"
    results=databases["system"].execute_query(sql,(ids,))
    
    projs=[]
    for res in results:
        projs.append(projects[res["type"]](res=res))
    return projs

def get_main_project_types():
    projs=[]
    for name in app.config['MLV_MAIN_PROJECTS']:
        projs.append({"name":name,"label":app.config['MLV_PROJECTS'][name]['label']});
    return projs
        
    

def get_project_data_type(db,type):
    return _get_class(type).get_project_data(db)
    
    
def get_project_columns_type(type):
    return project_base_columns


def _get_class(type):
    return projects[type]


def random_string(size=25,chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))  









