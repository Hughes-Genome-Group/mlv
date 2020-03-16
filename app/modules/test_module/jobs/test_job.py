from app.jobs.jobs import  LocalJob,job_types
from app import app
from app.ngs.project import get_project

class TestJob(LocalJob):
    def __init__(self,job=None,user_id=0,inputs=None,genome="other"):
        super().__init__(job,user_id,inputs,genome,type="test_job")
    
    def process(self):
        pid= self.job.inputs["project_id"]         
        p= get_project(pid)

        try:
            #do some long complicated stuff
            p.set_data("test_job_status","complete") 
            self.complete()
        except Exception as e:
            app.logger.exception("Job #{} failed")
            p.set_data("test_job_status","complete") 
            self.failed(traceback.format_exc())
            
job_types["test_job"]=TestJob

            