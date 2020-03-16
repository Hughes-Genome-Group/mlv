from app.jobs.jobs import  LocalJob,job_types
from app import app
from app.ngs.project import get_project
import requests,traceback

class BlastJob(LocalJob):
    def __init__(self,job=None,user_id=0,sequence=None,genome="other"):
        super().__init__(job,user_id=user_id,
                         inputs={"sequence":sequence},
                         genome=genome,
                         type="blast_job")
        
    def get_rid(self,text):
        r= text.split("\n")
        for line in r:
            if line.startswith('<input name="RID"'):
                rid = line[25:36]
                break
  
        return rid
        
    
    def send(self):
        try:
            data={
                "PROGRAM":"blastn",
                "CMD":"Put",
                "DATABASE":"nr",
                "QUERY":self.get_input_parameter("sequence"),
                "HITLIST_SIZE":5
    
            }
            resp = requests.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi",data=data)
            if resp.status_code != 200:
                self.failed(resp.text)
            else:
                self.set_output_parameter("rid",self.get_rid(resp.text))
                self.set_status("running")
                
        except Exception as e:
            app.logger.exception("Job #{} failed")
            self.failed(traceback.format_exc())
    
    def process(self):
        try:
            results = self.get_output_parameter("results")
            #do lots of processing
            self.complete()
        except Exception as e:
            app.logger.exception("Could not process blast job")
            self.failed(traceback.format_exc())
            
    
                
    def check_status(self):
        if self.job.status in ["processing","new","failed","complete"]:
            return self.job.status
        resp = requests.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Get&RID={}&FORMAT_TYPE=Text".format(self.job.outputs["rid"]))
        for line in resp.text.split("\n"):
            get_results=False
            line =line.strip()
            if line.startswith("Status="):
                status=line[7:]          
                if status== "FAILED":
                    self.failed(resp.text)
                if status=="READY":
                    get_results=True
                break
        if get_results:
            self.set_output_parameter("results",resp.text)
            self.set_status("processing")
            self.process()

            
       
      
            
job_types["blast_job"]=BlastJob



        