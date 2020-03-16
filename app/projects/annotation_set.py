from app.ngs.project import GenericObject,projects,create_project,get_project
from app.ngs.view import ViewSet
import os,csv,gzip
from app.ngs.utils import get_temporary_folder
from app import  app

class AnnotationSet(GenericObject):
    def __init__(self,res):
        super().__init__(res=res)
        
    @staticmethod
    def create(name,db,bed_file,user_id=0,description=""):
        anno= create_project(db,name,"annotation_set",description,
                       user_id=user_id,returning_object=True)
        gz_bed= os.path.join(app.config["TRACKS_FOLDER"],str(anno.id)+".bed.gz")
        os.system("sort  -k1,1 -k2,2n {} | bgzip >  {}".format(bed_file,gz_bed))
        os.system("tabix -p bed {}".format(gz_bed))
        anno.data["bed_file"]=gz_bed
        anno.update()
        return anno
        
    def create_from_project(self,project_id=None,ids=[],fields=[]):
        p=get_project(project_id)
        vs  = ViewSet(p.db,p.get_viewset_id())
        new_fields=[]
       
        for count,field in enumerate(fields,start=1):
            info = vs.fields.get(field)
            if not info:
                continue
            else:
                new_fields.append({"datatype":info["datatype"],
                                   "position":count,
                                   "name":info["label"]})
                
        bed  = vs.create_basic_bed_file(without_ids=True,selected_ids=ids,
                                        fields=fields)
        files={"upload_file":bed}
        print (bed)
        self.create_from_file(files,fields=new_fields,process_file=False)
        
        
        
    
    def create_from_file(self,files={},has_headers=False,fields=[],delimiter="\t",process_file=True):
        try:
            folder = get_temporary_folder()
            f= files["upload_file"]
            
            bed_file=f
            if process_file:
                new_bed= os.path.join(folder,"new_bed.bed")
                outfile= open(new_bed,"w")
                if f.endswith(".gz"):
                    handle = gzip.open(f,"rt")
                else:
                    handle=open(f)
                
                with handle as csvfile:
                    reader=csv.reader(csvfile,delimiter=delimiter)
                
                    for row in reader:
                        if reader.line_num==1 and has_headers:
                            continue                  
                        out_arr=row[0:3]
                        for field in fields:
                            out_arr.append(row[field["position"]-1])
                        outfile.write("\t".join(out_arr)+"\n")
            
                outfile.close()
                bed_file=new_bed
                #reorder the fields
                new_fields=[]
                for count,field in enumerate(fields[3:],start=1):
                    field["position"]=count
                    new_fields.append(field)
                fields=new_fields
            
                
            
            gz_bed= os.path.join(self.get_tracks_folder(),"anno_{}.bed.gz".format(self.id))
            os.system("sort  -k1,1 -k2,2n {} | bgzip >  {}".format(bed_file,gz_bed))
            os.system("tabix -p bed {}".format(gz_bed))
            
            self.set_data("fields",fields)
            self.set_data("bed_file",gz_bed)
            self.set_data("processing_file",False)
            self.update({"status":"complete"})
            
        except Exception as e:
            self.data["processing_file"]=False
            app.logger.exception("Unable to create annotataions from file {}".format(f))
            self.update({"status":"failed"})
            
        
           
        
    def delete(self,hard=False):

        super().delete(hard)
        

AnnotationSet.methods={
    "create_from_file":{
        "permission":"edit",
        "running_flag":["processing_file",True],
        "async":True
    },
    "create_from_project":{
        "permission":"edit",
        "running_flag":["processing_file",True],
        "async":True
    
    }
}

projects["annotation_set"]=AnnotationSet