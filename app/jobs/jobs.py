from app import db,app,databases
from app.databases.user_models import UserJob,User
from datetime import datetime,timedelta
from app.ngs.utils import get_temporary_folder
from app.zegami.zegamiupload import update_collection,delete_collection
from app.jobs.celery_tasks import process_job
from sqlalchemy import text
from app.ngs.project import get_project,random_string
from app.ngs.view import ViewSet
import traceback,requests,os,shutil
from app.ngs.thumbnail import create_thumbnails_from_ucsc,create_thumbnails_from_mlv
from app.jobs.email import send_email


job_types={}


class BaseJob(object):
    ''' 
    Attributes:
        job(UserJob): The sql Alchemy object that is based on this job
    '''
    def __init__(self,job=None,user_id=0,inputs={},genome="other",type=None):
        if type == None and job==None:
            raise ValueError("A job can not be constructed with type 'None'")
        self.user_name=None
        if job:
            self.job = job
        else:
            self.job = UserJob(user_id=user_id,inputs=inputs,status="new",outputs={},genome=genome,type=type)
            db.session.add(self.job)
            db.session.commit() 

    def get_id(self):
        return self.job.id

    def send(self):
        pass
    
    def resend(self):
        self.send()
    
    def check_status(self):
        return self.job.status
    
    def process(self):
        pass
    
    
    def kill(self):
        self.failed("killed by user")
    
    def failed(self,msg):
        self.job.outputs=dict(self.job.outputs)
        self.job.outputs['error']=msg
        self.job.status="failed"
        self.job.finished_on=datetime.now()
        db.session.commit()
    
    def delete(self):
        db.session.delete(self.job)
        db.session.commit()
        
        
    def complete(self):
        self.job.finished_on=datetime.now()
        self.job.status="complete"
        db.session.commit()
        
        
    
    def get_user_name(self):
        if not self.user_name:
            user = db.session.query(User).filter_by(id=self.job.user_id).one()
            return "{} {}".format(user.first_name,user.last_name)
            
    
    def has_permission(self,user):
        if not user.is_authenticated:
            return False
        if user.administrator:
            return True
        return self.job.user_id ==user.id
    
        
    def get_info(self):
        return {
            "inputs":self.job.inputs,
            "outputs":self.job.outputs
        }
        
    def set_input_parameter(self,param,value):
        self.job.inputs=dict(self.job.inputs)
        self.job.inputs[param]=value
        db.session.commit()
        
    def set_output_parameter(self,param,value):
        self.job.outputs=dict(self.job.outputs)
        self.job.outputs[param]=value
        db.session.commit()
        
    def get_input_parameter(self,param):
        return self.job.inputs.get(param)
    
    def get_output_parameter(self,param):
        return self.job.inputs.get(param)
    
    def set_status(self,value):
        self.job.status=value
        db.session.commit()
        
        


class LocalJob(BaseJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other",type=""):
        if (job):
            super().__init__(job=job)
        else:   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type=type)
    
    def send(self,args=None):
        self.set_status("queued")
        
        if app.config['USE_CELERY']:
            if (self.job.inputs.get("slow_queue")):
                process_job.apply_async(args=(self.job.id,args),queue="slow_queue")
            else:                
                process_job.delay(self.job.id,args)
        else:
            if not args:
                self.process()
            else:
                self.process(args)
            

class AnnotationIntersectionJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="annotation_intersection_job")
            
    def label_history(self,history):
        self.set_input_parameter("history_id",history["id"])
        history["label"] = "Calculate Intersections"
        history["job_id"]=self.job.id
        info=[]
        ids = self.job.inputs["ids"]
        sql = "SELECT name FROM projects WHERE id = ANY(%s)"
        res= databases["system"].execute_query(sql,(ids,))
        names=[]
        for r in res:
            names.append(r["name"])
        history["info"]="Calculated intsersections with:\n"+", ".join(names)
        
    def process(self):
        try:
            #do they contain tabix index bed files
            for pid in self.job.inputs["ids"]:
                p=get_project(pid)
                if not p.data.get("bed_file"):
                    p.create_anno_bed_file()
            p= get_project(self.job.inputs["project_id"])
            data = p.add_intersections(self.job.inputs["ids"],self.job.inputs.get("extra_columns"))
            hid= self.get_input_parameter("history_id")
            p.refresh_data()
            history=p.get_history(hid)
            if history:
                history["tracks"]=data["tracks"]
                history["fields"]=data["fields"]
                history["graphs"]=data["graphs"]
                history["status"]="complete"        
            p.update()      
            self.complete()
        except Exception as e:
            app.logger.exception("Cannot process Annotation IntersectionJob # {}".format(self.job.id))
            p.refresh_data()
            hid= self.get_input_parameter("history_id")
            history=p.get_history(hid)             
            history["status"]="failed"
            p.update();
            self.failed(traceback.format_exc())


class PeakStatsJob(LocalJob):
        def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
            if (job):
                super().__init__(job=job)
            else:
                inputs["slow_queue"]=True   
                super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="peak_stats_job")
                
        def label_history(self,history):
            self.set_input_parameter("history_id",history["id"])
            history["label"] = "Add Peak Stats"
            history["job_id"]=self.job.id
            info=[]
            for n,wl in enumerate(self.job.inputs["wig_locations"]):
                name = self.job.inputs["wig_names"][n]
                info.append("{}: {}".format(name,wl))
            history["info"]="Area and max height of the signal for each BigWig file calculated at each location\n"
            history["info"]+="BigWig Files processed:\n"+"\n".join(info)
                  
        def process(self):
            p=get_project(self.job.inputs["project_id"])
            try:
                tracks=[]
                fields=[]
                for n,wl in enumerate(self.job.inputs["wig_locations"]):
                    name = self.job.inputs["wig_names"][n]
                    self.set_status("Processing "+name)
                    info = p.add_bw_stats(wl,name)
                    tracks.append(info["track"])
                    fields=fields+info["fields"]
                    
               
                hid= self.get_input_parameter("history_id")
                p.refresh_data()
                history=p.get_history(hid) 
                history["tracks"]=tracks
                history["fields"]=fields
                history["graphs"]=[]
                history["status"]="complete"        
                p.update()      
                self.complete()
                
            except Exception as e:
                app.logger.exception("Cannot process PeakStatsJob # {}".format(self.job.id))
                p.refresh_data()
                hid= self.get_input_parameter("history_id")
                history=p.get_history(hid)
               
                history["status"]="failed"
                p.update();
                self.failed(traceback.format_exc())
            
class ClusterByFieldsJob(LocalJob):
        def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
            if (job):
                super().__init__(job=job)
            else:
                inputs["slow_queue"]=True
                super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="cluster_by_fields_job")
                
        def label_history(self,history):
            self.set_input_parameter("history_id",history["id"])
            history["label"] = "Dimension Reduction "+self.job.inputs["name"]
            history["job_id"]=self.job.id
            info=""
            p =get_project(self.job.inputs["project_id"])
            vs = ViewSet(p.db,p.get_viewset_id())
            names=[]
            for f in self.job.inputs["fields"]:
                names.append(vs.fields[f]["label"])
            info+="Fields: "+", ".join(names)
            info+=" \nCluster Methods:"+", ".join(self.job.inputs["methods"])
            info+=" \nDimensions: "+str(self.job.inputs["dimensions"]) 
           
            history["info"]=info
            
            
                   
        def process(self):
            p=get_project(self.job.inputs["project_id"])
           
            try:
                name = self.job.inputs["name"]
                dimensions = self.job.inputs.get("dimensions",2)
                data= p.cluster_by_fields(self.job.inputs["fields"],name,self.job.inputs["methods"],dimensions)
                p.refresh_data()
                hid= self.get_input_parameter("history_id")
                history=p.get_history(hid) 
                history["tracks"]=[]
                history["fields"]=data["fields"]
                history["graphs"]=data["graphs"]
                history["status"]="complete"   
                p.update()
                self.complete()
                
            except Exception as e:
                app.logger.exception("Cannot process ClusterByFieldsJob # {}".format(self.job.id))
                p.refresh_data()
                hid= self.get_input_parameter("history_id")
                history=p.get_history(hid)
                history["status"]="failed"
                p.update();
                self.failed(traceback.format_exc())               
            
        

class FindTSSDistancesJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="find_tss_distances_job")
            
            
    def label_history(self,history):
            self.set_input_parameter("history_id",history["id"])
            history["label"] = "Add TSS Stats"
            history["job_id"]=self.job.id
            info = "Calculate distance from each TSS"  
            go =  self.inputs.get("go_levels",0)
            if go !=0:
                info+="\nAdd GO of nearest gene"
            history["info"]=info    
            
    def process(self):
        try:
            p =get_project(self.job.inputs["project_id"])
            vs =ViewSet(p.db,p.get_viewset_id())
            data= vs.add_ts_starts(overlap_column=True,go_levels=self.job.inputs.get("go_levels",0))
            p.refresh_data()
            p.data["graph_config"]+=data["graphs"]
            hid= self.get_input_parameter("history_id")
            history=p.get_history(hid) 
            history["tracks"]=[]
            history["fields"]=data["fields"]
            history["graphs"]=[]
            for g in data["graphs"]:
                history["graphs"].append(g["id"])
            history["status"]="complete"        
            p.update()      
            self.complete()
           
            
        except Exception as e:
            app.logger.exception("Cannot process AnnotationIntersectionJob # {}".format(self.job.id))
            p.refresh_data()
            hid= self.get_input_parameter("history_id")
            history=p.get_history(hid)
            history["status"]="failed"
            p.update();
            self.failed(traceback.format_exc())

class MLVImagesJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:
            inputs["slow_queue"]=True
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="mlv_images_job")
            
            
    def label_history(self,history):
        self.set_input_parameter("history_id",history["id"])
        history["label"] = "Create Images"
        history["job_id"]=self.job.id
        history["info"]="Creating Images for each location based on internal browser"
        history["images"]=True
            
    def process(self):
        try:
            
           
            p= get_project(self.job.inputs["project_id"])       
            vs = ViewSet(p.db,p.get_viewset_id())
            
            create_thumbnails_from_mlv(self.job.inputs["tracks"],vs,
                                        image_width=self.job.inputs["image_width"],
                                        margins=self.job.inputs.get("margins",0),
                                        job=self.job)
            
            p.refresh_data()
            p.set_data("has_images",True)
            hid= self.get_input_parameter("history_id")
            history=p.get_history(hid) 
            history["tracks"]=[]
            history["fields"]=[]
            history["graphs"]=[]
            history["status"]="complete"        
            p.update()
            #send email
            url = p.get_url(external=True)
            user = db.session.query(User).filter_by(id=self.job.user_id).one()
            send_email(user,"Images Created","ucsc_image_job_finished",url=url) 
            
            self.complete()
            
        except Exception as e:
            p= get_project(self.job.inputs["project_id"])
            hid= self.get_input_parameter("history_id")
            history=p.get_history(hid)
            history["status"]="failed"
            p.update();
            app.logger.exception("Error in creating mlv images # {}".format(self.job.id))
            
            self.failed(traceback.format_exc())
    
                 
            
class UCSCImagesJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:
            inputs["slow_queue"]=True   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="ucsc_images_job")
    def process(self):
        try:
            p= get_project(self.job.inputs["project_id"])
         
            vs = ViewSet(p.db,p.get_viewset_id())
            
            create_thumbnails_from_ucsc(self.job.inputs["session_url"],vs,
                                        pixels=self.job.inputs["image_width"],
                                        margins=self.job.inputs.get("margins",0),
                                        job=self.job)
            
           
            p.set_data("has_images",True)
            #send email
            url = p.get_url(external=True)
            user = db.session.query(User).filter_by(id=self.job.user_id).one()
            send_email(user,"Images Created","ucsc_image_job_finished",url=url)
            p.set_data("creating_images_job_status","complete") 
            self.complete()
            
        except Exception as e:
            app.logger.exception("Error in ucsc upload # {}".format(self.job.id))
            p.set_data("creating_images_job_status","failed") 
            self.failed(traceback.format_exc())
        
        
  
        

class CreateZegamiCollectionJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:
            inputs["slow_queue"]=True   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="zegami_upload_job")
    
    #don't want to store the password 
    def process(self,pword):
        try:
            p= get_project(self.job.inputs["project_id"])
            p.set_data("zegami_upload_job",{
                    "job_id":self.job.id,
                    "job_status":"running"
            })
            vs = ViewSet(p.db,p.get_viewset_id())
            credentials={
                "project":self.job.inputs["project"],
                "username":self.job.inputs["username"],
                "password":pword
                
            }
            
            url = vs.create_zegami_collection(name=p.name,job=self.job,credentials=credentials)
            p.set_data("zegami_url",url)
            vs.upload_images_to_zegami(job=self.job,credentials=credentials)
        
            #send email

            user = db.session.query(User).filter_by(id=self.job.user_id).one()
            send_email(user,"Zegami Collection Created","zegami_collection_created",url=url)
            
            self.complete()
            
        except Exception as e:
            app.logger.exception("Error in zegami upload # {}".format(self.job.id))
            p.set_data("zegami_upload_job",{
                "job_id":self.job.id,
                "job_status":"failed"
            })
            self.failed(traceback.format_exc())
            
    
  
job_types["annotation_intersection_job"]=AnnotationIntersectionJob
job_types["ucsc_images_job"]=UCSCImagesJob
job_types["mlv_images_job"]=MLVImagesJob
job_types["zegami_upload_job"]=CreateZegamiCollectionJob
job_types["find_tss_distances_job"]=FindTSSDistancesJob
job_types["peak_stats_job"]=PeakStatsJob
job_types["cluster_by_fields_job"]=ClusterByFieldsJob
            
def get_all_jobs(user=None):
    extra=""
    types = list(job_types.keys())
    if user or user==0:
        extra = "AND jobs.user_id={}".format(user)
    sql= ("SELECT jobs.id as id,to_char(sent_on, 'YYYY-MM-DD HH24:MI:SS') as sent_on , "
          "to_char(finished_on, 'YYYY-MM-DD HH24:MI:SS') as finished_on, CONCAT(first_name,' ',last_name) "
          "as user_name,status,type AS job_type,genome FROM jobs INNER JOIN users "
          "ON jobs.user_id=users.id WHERE type = ANY (%s) {} ORDER BY jobs.id DESC").format(extra)
    results=databases["system"].execute_query(sql,(types,))
    return results
    

def delete_job(id):
    job = db.session.query(UserJob).filter_by(id=id).first()
    if not job:
        app.logger.debug("Trying to delete non-existant job {}".format(id))
        return
    class_type= job_types[job.type]
    class_type(job).delete()
      
def get_job(id=None,job=None):
    if not job:
        job = UserJob.query.filter_by(id=id).one()
        db.session.commit()
    return job_types[job.type](job)
  

    
    

    

