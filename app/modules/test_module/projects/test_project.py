from app.ngs.project import GenericObject,projects
from ..jobs.test_job import TestJob


class TestProject(GenericObject):
    def get_template(self,args):
        return "test_project/page.html",{}
    
    
    def initiate_job(self,data=""):
        inputs={
            "project_id":self.id,
            "data":data   
        }
        job = TestJob(user_id=self.owner,inputs=inputs,genome=self.db)
        job.send()
        
                
TestProject.methods={
    "inititiate_job":{
        "permission":"edit",
        "running_flag":["test_job_status","running"]
        
    }
    
    
}
projects["test_project"]=TestProject