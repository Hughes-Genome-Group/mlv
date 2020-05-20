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
def process_job(job_id,args=None):
    from app.jobs.jobs import get_job
    job = get_job(job_id)
    if not args:
        job.process()
    else:
        job.process(args)






     
