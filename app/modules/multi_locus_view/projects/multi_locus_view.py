from app import app
from app.ngs.project import GenericObject,projects
from app.ngs.view import ViewSet,create_view_set_from_file,parse_extra_fields
from app.jobs.jobs import delete_job 
import os,shutil

class MultiLocusView(GenericObject):
    def __init__(self,res):
        super().__init__(res=res)
        
    def get_template(self,args):
        return "multi_locus_view/mlv.html",{}
          
    def copy_files(self,parent,new_vs):
        bed_file = new_vs.create_bed_file()
        index = bed_file+".tbi"
        folder = self.get_tracks_folder()
        f_name="anno_{}.bed.gz".format(self.id)
        new_bed=os.path.join(folder,f_name)
        new_index=os.path.join(folder,f_name+".tbi")
        shutil.copyfile(bed_file,new_bed)
        shutil.copyfile(index,new_index) 
        tracks = self.data["browser_config"]["state"]
        for track in tracks:
            if track["track_id"] == "regions":
                track["url"]= new_bed.replace("/data","")
        self.data["bed_file"]=new_bed
        
        self.update()
    
    def upload_file(self,has_headers=False,files=[],fields={},delimiter="\t"):
        try:
            self.update({"status":"Uploading File"})
            extra_fields= parse_extra_fields(fields)
       
            vs = create_view_set_from_file(self.db,files["upload_file"],"Peak Analysis "+self.name,
                                  description="Peak Analysis "+self.name,
                                  has_headers=has_headers,
                                  extra_fields=extra_fields,
                                  delimiter=delimiter,
                                  owner=self.owner,
                                  no_track_id=True,
                                  parse_headers=False,
                                  create_icon=False)
        
        
            bed_file = vs.create_bed_file()
            index = bed_file+".tbi"
            folder = self.get_tracks_folder()
            f_name="anno_{}.bed.gz".format(self.id)
            new_bed=os.path.join(folder,f_name)
            new_index=os.path.join(folder,f_name+".tbi")
            shutil.copyfile(bed_file,new_bed)
            shutil.copyfile(index,new_index)
            tracks=[
                { 
                    "url":"/tracks/projects/{}/{}".format(self.id,f_name),
                    "short_label":"Feature",
                    "track_id":"regions",
                    "featureHeight":12,
                    "format":"feature",
                    "height":30,
                    "type":"mlv_feature_track"
                }

            ]
            self.add_gene_track(tracks)         
            self.data["browser_config"]={"state":tracks,"feature_track":{"track_id":"regions"}}
            self.data["uploading_file"]=False
            self.data["viewset_id"]=vs.id
            self.data["bed_file"]=new_bed
            self.update({"status":"complete"})
            self.add_tagging_column()
            
            
        except Exception as e:
            app.logger.exception("unable to upload file for {}".format(self.id))
            self.data["uploading_file"]=False
            self.update({"status":"Failed Upload"})
          
    
    def delete(self,hard=False):
        if not hard:
            return super().delete()
            
        vs_id= self.data.get("viewset_id")
        if vs_id:
            vs = ViewSet(self.db,vs_id)
            if vs.id !=-1:
                vs.delete(True)
        info= self.data.get("zegami_upload_job")
        if info:
            delete_job(info["job_id"])
            
        info = self.data.get("ucsc_images")
        if info:
            delete_job(info["job_id"])
               
        super().delete(True)
    
MultiLocusView.methods={
    "upload_file":{
        "permission":"edit",
        "running_flag":["uploading_file",True],
        "async":True
    },
    "get_viewset":{
        "permission":"view"
    },
    "add_annotation_intersections":{
        "permission":"edit"
    },
    "remove_annotation_intersections":{
        "permission":"edit"
    },
    "get_annotation_intersections":{
        "permission":"view"
    },
    "make_ucsc_images":{
        "permission":"edit",
        "permission_required":"ucsc_create_images"
    },
    "upload_zegami_collection":{
        "permission":"edit"
    },
    "create_compound_column":{
        "permission":"edit"
    },
    "delete_columns":{
        "permission":"edit"
    },
    "make_mlv_images":{
        "permission":"edit"
    },
    "create_subset_from_parent":{
        "permission":"edit",
        "running_flag":["creating_subset",True],
        "async":True
    },
    "update_tags":{
        "permission":"edit"
    },
        "find_tss_distances":{
        "permission":"edit"
    },
    "get_tss_distances":{
        "permission":"edit"
    },
    "send_peak_stats_job":{
        "permission":"edit"
    },
    "send_cluster_by_fields_job":{
        "permission":"edit"
    }
}


projects["multi_locus_view"]=MultiLocusView