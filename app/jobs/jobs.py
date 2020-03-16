from app import db,app,databases
from app.databases.user_models import UserJob,User
from datetime import datetime,timedelta
from app.ngs.utils import get_temporary_folder
from app.zegami.zegamiupload import update_collection,delete_collection
from app.jobs.celery_tasks import process_job
from sqlalchemy import text
from app.ngs.project import get_project
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
    def process(self):
        try:
            #do they contain tabix index bed files
            for pid in self.job.inputs["ids"]:
                p=get_project(pid)
                if not p.data.get("bed_file"):
                    p.create_anno_bed_file()
            p= get_project(self.job.inputs["project_id"])
            vs = ViewSet(self.job.genome,p.get_viewset_id())
            vs.add_annotations_intersect(self.job.inputs["ids"])
            self.complete()
        except Exception as e:
            app.logger.exception("Cannot process AnnotationIntersectionJob # {}".format(self.job.id))
            self.failed(traceback.format_exc())


class PeakStatsJob(LocalJob):
        def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
            if (job):
                super().__init__(job=job)
            else:   
                super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="peak_stats_job")
                
        def process(self):
            p=get_project(self.job.inputs["project_id"])
            try:
                
                for n,wl in enumerate(self.job.inputs["wig_locations"]):
                    name = self.job.inputs["wig_names"][n]
                    self.set_status("Processing "+name)
                    p.add_bw_stats(wl,name)
                p.set_data("peak_stats_job_status","complete")
                self.complete()
            except Exception as e:
                app.logger.exception("Cannot process PeakStatsJob # {}".format(self.job.id))
                p.set_data("peak_stats_job_status","failed")
                self.failed(traceback.format_exc())
            
class ClusterByFieldsJob(LocalJob):
        def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
            if (job):
                super().__init__(job=job)
            else:   
                super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="cluster_by_fields_job")
                
        def process(self):
            p=get_project(self.job.inputs["project_id"])
            vs = ViewSet(p.db,p.get_viewset_id())
            try:
                name = self.job.inputs["name"]
                info = vs.cluster_by_fields(self.job.inputs["fields"],name,self.job.inputs["methods"])
                p.refresh_data()
                for cols in info:
                    p.data["graph_config"].append({
                            "type":"wgl_scatter_plot",
                            "title":name + " " + cols["method"],
                            "param":[cols["fields"][0],cols["fields"][1]],
                            "id":name,
                            "axis":{
                                "x_label":cols["labels"][0],
                                "y_label":cols["labels"][1]
                            },
                            "location":{
                                "x":0,
                                "y":0,
                                "height":2,
                                "width":3
                            }
                        
                        })
                p.data["cluster_by_fields_job_status"]="complete"
                p.update()          
                self.complete()
            except Exception as e:
                app.logger.exception("Cannot process ClusterByFieldsJob # {}".format(self.job.id))
                p.set_data("cluster_by_fields_job_status","failed")
                self.failed(traceback.format_exc())               
            
        

class FindTSSDistancesJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="find_tss_distances_job")
            
    def process(self):
        try:
            p =get_project(self.job.inputs["project_id"])
            vs =ViewSet(p.db,p.get_viewset_id())
            vs.add_ts_starts(overlap_column=True)
            p.set_data("find_tss_distances_job_status","complete")
            self.complete()
            
        except Exception as e:
            app.logger.exception("Cannot process AnnotationIntersectionJob # {}".format(self.job.id))
            p.set_data("find_tss_distances_job_status","failed")
            self.failed(traceback.format_exc())

class MLVImagesJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:
            inputs["slow_queue"]=True
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="mlv_images_job")
            
    def process(self):
        try:
            
           
            p= get_project(self.job.inputs["project_id"])       
            vs = ViewSet(p.db,p.get_viewset_id())
            
            create_thumbnails_from_mlv(self.job.inputs["tracks"],vs,
                                        image_width=self.job.inputs["image_width"],
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
            p= get_project(self.job.inputs["project_id"])
            app.logger.exception("Error in creating mlv images # {}".format(self.job.id))
            p.set_data("creating_images_job_status","failed") 
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
            
            
            
class GreatOntologyJob(LocalJob):
    def __init__(self,job=None,inputs=None,user_id=0,genome="other"):
        if (job):
            super().__init__(job=job)
        else:   
            super().__init__(inputs=inputs,genome=genome,user_id=user_id,type="great_ontology_job")
    
    def process(self):
        import ujson
        if not self.job.genome in ["hg19","hg38","mm10","mm9"]:
            raise Exception("Genome not supported")
        p= get_project(self.job.inputs["project_id"])
        tf= p.get_tracks_folder()
        vs = ViewSet(p.db,p.get_viewset_id())
        bed = vs.get_bed_file()
        '''
        tn = os.path.join(tf,"temp.bed.gz")
        shutil.copy(bed,tn)
        bed_url= "http://{}/tracks/projects/{}/temp.bed.gz".format(app.config["HOST_NAME"],p.id)
        
        params={
            "requestSpecies":p.db,
            "requestName":p.name,
            "requestSender":"MLV",
            "outputType":"batch",
            "requestURL":bed_url
        }
        response = requests.get("http://bejerano.stanford.edu/great/public/cgi-bin/greatStart.php",params=params)
        f= get_temporary_folder()
        self.set_output_parameter("results_folder",f)
        op = os.path.join(f,"results.txt")
        o = open(op,"w")
        o.write(response.text)
        o.close()
        '''
        results = {}
        a = ujson.loads(open("/home/sergeant/mlv_dev/node/mf.json").read())
        with open("/data/mlv/temp/faYNVuHIE0fbhAyIOOYM/results.txt") as f:
            for line in f:
                arr = line.split("\t")
                if arr[0] =="GO Molecular Function":
                    prob = float(arr[5])
                    if prob>100:
                        continue
                    ids = arr[22].split(",")
                    for vid in ids:
                        vid = int(vid)
                        info = results.get(vid)
                        if not info:
                            info={1:"",2:"",3:"",4:"",5:""}
                            results[vid]=info
                        go_info= a.get(arr[1])
                        if go_info:
                            l = go_info["level"]
                            if l<6 and l>0:
                                if not info[l]:
                                    info[l]=go_info["name"]
                                else:
                                    info[l]+=(","+go_info["name"])
        print(results[2347])           
        
        
        
        
         
    
    
job_types["great_ontology_job"]=GreatOntologyJob     
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
    if user:
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
  

    
    

    

