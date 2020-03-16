from app import celery,app,db
from app.databases.user_models import UserJob
from app.ngs.view import ViewSet
import traceback
from app.ngs.project import get_project


@celery.task
def execute_action_async(project_id,method,args):
    try:
        p=get_project(project_id)
        meth= getattr(p,method)
        meth(**args)
    except Exception as e:
        app.logger.exception("Error")
 
 
 
@celery.task
def celery_test():
    from app import databases
    #db.session.query(UserJob).all()
    #db.session.close()
    sql = "SELECT * FROM projects WHERE id<10"
    databases["hg19"].execute_query(sql)
    print("execute_query")
    

@celery.task
def process_job(job_id,args=None):
    from app.jobs.jobs import get_job
    job = get_job(job_id)
    if not args:
        job.process()
    else:
        job.process(args)

@celery.task
def upload_to_zegami_after_tsne(parameter_job_id):

    from app.jobs.jobs import get_job
    param_job= get_job(parameter_job_id)
    try:
        status =  param_job.job.status
     
        if not status.startswith("Uploaded"):
            param_job.job.status="Uploading to Zegami"
            db.session.commit()
        proj = get_project(param_job.job.inputs['project_id'])
        vs= ViewSet(proj.db,proj.data.get("viewset_id"))
        
        
       
        proj.update({"status":"Uploading To Zegami"})
        orig_wig=proj.data['original_wigfile']
        user_name= param_job.get_user_name()
        desc= "User Name:{}\nOriginal Wig:{}\n".format(user_name,orig_wig)
        url = vs.create_zegami_collection(desc,param_job.job)
        proj.set_data('zegami_url',url)
        vs.upload_images_to_zegami(job=param_job.job)
        
        
        param_job.set_output_parameter('zegami_url',url)
        param_job.complete()
        #get fresh project
        proj =get_project(param_job.job.inputs['project_id'])
        proj.job_finished()

        
            
        
        
    except Exception as e:
        app.logger.exception("Failed to upload to zegami job_id:{}".format(parameter_job_id))
        param_job.job.outputs=dict(param_job.job.outputs)
        param_job.job.outputs['error']=traceback.format_exc()
        #set job and project as complete because it can still be viewed
        proj.data['peak_analysis_job_status']="complete"
        proj.update({"status":"Zegami Upload Failed"})
        param_job.complete()

        





     
