from app import databases,app,db
from app.jobs.email import send_email
import ujson,copy,shutil
from os import name
from app.databases.user_models import User
from app.ngs.view import ViewSet,create_view_set_from_file,parse_extra_fields
import datetime
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
            url="http://"+app.config['HOST_NAME']+url
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
        
    
    def create_compound_column(self,field1="",field2="",operand="+",name=""):
        vs = ViewSet(self.db,self.get_viewset_id())
        return vs.create_compound_column([field1,field2],operand,name)
    
    
    def delete_columns(self,columns=[]):
        vs = ViewSet(self.db,self.get_viewset_id())
        for col in columns:
            if not vs.fields.get(col):
                raise Exception("{} column does not exist".format(col))
        vs.remove_columns(columns)
        
    
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
    
    def get_viewset(self,filters=None):
        vs=ViewSet(self.db,self.get_viewset_id())
        return {
            "views":vs.get_all_views(filters=filters),
            "field_information":vs.data["field_information"],
            "fields":vs.fields,
            "sprite_sheets":vs.data.get("sprite_sheets"),
            "annotation_information":vs.data.get("annotation_information"),
            "base_image_url":"/data/{}/view_sets/{}/thumbnails/tn".format(self.db,vs.id)
        }
    
    def add_annotation_intersections(self,ids=[]):
        from app.jobs.jobs import AnnotationIntersectionJob
        j= AnnotationIntersectionJob(inputs={"project_id":self.id,"ids":ids},
                                     user_id=self.owner,
                                     genome=self.db)
        j.send()
        return j.job.id
    

    def find_tss_distances(self):
        from app.jobs.jobs import FindTSSDistancesJob
        j= FindTSSDistancesJob(inputs={"project_id":self.id},user_id=self.owner,genome=self.db)
        self.set_data("find_tss_distances_job_id",j.job.id)
        self.set_data("find_tss_distances_job_status","running")
        j.send()
        return j.job.id
    
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
            
            
            
            
        
               
    def create_anno_bed_file(self):
        vs = ViewSet(self.db,self.get_viewset_id())
        vbf = vs.get_bed_file()
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
        command = "curl {} -o {}".format(url,local_file)
        os.system(command)
        self.data["browser_config"]["state"].append({
                "url":local_file.replace("/data",""),
                "track_id":name,
                "discrete":True,
                "height":150,
                "color":"#808080",
                "scale":"dynamic",
                "short_label":name,
                "type":"bigwig",
                "format":"wig"
        })
        self.update()
        vs =ViewSet(self.db,self.get_viewset_id())
        vs.add_wig_stats(local_file,name)
        
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
    
    def send_cluster_by_fields_job(self,fields=[],name="",methods=["UMAP"]):
        from app.jobs.jobs import ClusterByFieldsJob
        inputs={
            "project_id":self.id,
            "name":name,
            "fields":fields,
            "methods":methods
        }
        j= ClusterByFieldsJob(genome=self.db,user_id=self.owner,inputs=inputs)
        j.send()
        jid= j.job.id
        self.set_data("cluster_by_fields_job_status","running")
        self.set_data("cluster_by_fields_job_id",jid)
        return jid
    
        
        
        
      
       
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
    
    projects=[]
    for res in results:
        projects.append(projects[res["type"]](res))
    return projects

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









