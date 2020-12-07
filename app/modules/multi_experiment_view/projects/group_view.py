from app.ngs.project import GenericObject,projects,get_project,get_projects_summary,get_projects,create_project
from app import databases,app
import os,ujson,random,string


class GroupView(GenericObject):
    def get_template(self,args):
        return "group_view/page.html",{}
    
    def get_group_info(self,gid=0):
        p=get_project(int(gid))
        return {
            "clusters":p.data["clusters"],
            "experiments":p.data["experiments"]
        }
    
    
    
    def get_gene_suggest(self,term="",eid=0):
        var=()
        if eid==0:
            li=[]
            di={}
            for e in self.data["experiments"]:
                li.append(e["id"])
                di[e["id"]]=e["name"]
            sql="SELECT name AS label,id AS value FROM mev_experiment_fields WHERE  "+\
                "experiment=ANY(%s) AND name ILIKE %s ESCAPE '' ORDER BY label LIMIT 20"
            res = databases["system"].execute_query(sql,(li,"%"+term+"%"))
            for r in res:
                r["label"]="{}({})".format(r["label"],d[r["value"]])
                 
        else:
            sql = "SELECT name AS label ,id AS value FROM mev_experiment_fields WHERE experiment=%s AND name ILIKE %s ESCAPE '' ORDER BY label LIMIT 20"
            res= databases["system"].execute_query(sql,(eid,"%"+term+"%"))
        return res
        
    def get_gene_info(self,gene_list=[],exp_id=0):
        sql = "SELECT name,id  FROM mev_experiment_fields WHERE experiment =%s AND name=ANY(%s) ORDER BY name"
        return databases["system"].execute_query(sql,(exp_id,gene_list))
        
    def get_similar_genes(self, names=[]):
         p= get_project(self.data["group_id"])
         return p.get_similar_genes(names)
          
        
   
   
    def get_gene_data(self,cluster=0,group=0,type="",experiment=0,gene_ids=[]):
        p = get_project(self.data["group_id"])
        cluster=int(cluster)
        gene_data= p.get_gene_data(gene_ids,cluster,type);
        return gene_data
    
    def get_feature_set(self,feature_set_id=0):
         g= get_project(self.data["group_id"])
         fs = get_project(feature_set_id)
         return g.get_feature_data(fs.data["feature_ids"])
     
    
       
        
    def get_individual_gene_data(self,gene_id=0,group=0,type="residuals"):
        p = get_project(int(group))
        return p.get_individual_gene_data(gene_id,type)
        
        
   
    def save_view(self,data={}):
        path = os.path.join(self.get_folder(),"current_view.json")
        o = open(path,"w")
        o.write(ujson.dumps(data))
        o.close()
        self.set_data("current_view",path)
        
    
    def get_all_groups(self):
        filters={
              "type":["experiment_group"]
        }
        groups= get_projects_summary(user_id=self.owner,filters=filters,limit=100,extra_fields=",projects.data AS data")
        for group in groups:
            group["cluster_number"]=len(group["data"]["clusters"])
            group["experiments"]=group["data"]["experiments"]
            del group["data"]
        return groups
    
    def set_group(self,group_id=0):
        group_id=int(group_id)
        p=get_project(group_id)
        self.set_data("group_id",group_id)
        self.set_data("group_name",p.name)
        return True
        
    def get_experiment_data(self,id=0):
        id = int(id)
        
          
    
    def get_sample_data(self,ids=[],feature_data=None,user=None):
        
        fields={}
        field_names=[]
        if ids:
            projects=get_projects(ids)
            for p in projects:
                if (user and not p.has_view_permission(user)):
                    continue
                fields[p.id]={
                    "name":p.name,
                    "field":p.data["field"],
                    "datatype":p.data["datatype"],
                    "colors":p.data.get("colors"),
                    "graph":p.data.get("graph"),
                    "delimiter":p.data.get("delimiter"),
                    "id":p.id    
                }       
                field_names.append(p.data["field"])
               
            sql = "SELECT id,{} FROM mev_samples".format(",".join(field_names))
            
        else:
            sql = "SELECT id FROM mev_samples"    
        data= databases["system"].execute_query(sql)
        
        
        if feature_data:
              p = get_project(self.data["group_id"])
              
              f,d= p.get_features(feature_data,len(data))
              for fid in f:
                  fields[fid]=f[fid]
              for item in data:
                  new_data= d.get(item["id"])
                  if new_data:
                      for key in new_data:
                          item[key]=new_data[key]
      
            
        
        return {
            "fields":fields,
            "data":data      
        }
            
    
    def clone_view(self,data={},new_view=0,user=None):
        nv= get_project(new_view)
        if user and not nv.has_edit_permission(user):
            raise Exception()
        else:
            nv.data["group_id"]=self.data["group_id"]
            nv.data["group_name"]=self.data["group_name"]
            path = os.path.join(nv.get_folder(),"current_view.json")
            o = open(path,"w")
            o.write(ujson.dumps(data))
            o.close()
            nv.data["current_view"]=path
            nv.update()
            
            
        return {
            "url":"https://"+app.config["HOST_NAME"]+"/projects/group_view/"+str(new_view)
        }
        
                    
    def add_sample_data(self,name="",description="",datatype="",genome="other",data=[],user=None,is_public=False):
        if user:
            if not user.is_authenticated or not user.has_permission("mev_upload_sample_data"):
                return {"permission_denied":True}
        if not user:
            u_id=0
        else:
            u_id=user.id
        
        p = create_project(genome,name,"mev_sample_field",description,user_id=u_id,is_public=is_public,returning_object=True)
       
        dt = "text"
        if datatype=="continuous":
            dt="double"
        field= "".join(random.choice(string.ascii_lowercase) for _ in range(5))
        columns= [{"name":field,"datatype":dt}]
        databases["system"].add_columns("mev_samples",columns)
        
        graph = "row_chart"
        if dt == "double":
            graph="bar_chart"
        p.data={
            "datatype":dt,
            "field":field,
            "graph":graph
            
        }
        
        p.update()
        did= app.config["MEV_SAMPLE_ID"]
        sql = "SELECT id,{} FROM mev_samples WHERE {}=ANY(%s)".format(did,did)
        res = databases["system"].execute_query(sql,(list(data.keys()),))
        update_list=[]
        for item in res:
            val=  data.get(item[did])
            if dt=="double":
                try:
                    val= float(val)
                except:
                    continue
            update_list.append({"id":item["id"],field:val})    
         
        databases["system"].update_table_with_dicts(update_list,"mev_samples")
        
        return {"id":p.id}
        
        
        
            
            
            
    
    def get_data(self):
    
        clusters=None
        experiments=None
        sample_groups={}
        eg = self.data.get("group_id")
        if eg:
            p= get_project(self.data["group_id"])
            clusters=p.data["clusters"]
            experiments=p.data["experiments"]
            sample_groups=p.get_sample_groups()
        
        sample_fields=[]
        col_names=[]
        
        current_view_file =self.data.get("current_view")
        #current_view_file=None
        default_id = app.config.get("MEV_SAMPLE_ID")
        if current_view_file:
            current_view=ujson.loads(open(current_view_file).read())
            
        else:
            current_view={
                "sample_data_ids":app.config.get("MEV_DEFAULT_SAMPLE_FIELDS",[]),
                "default_sample_data":True,
                
            }
        
        current_view["default_id"]=default_id
             
        sql = "SELECT id,{}  FROM mev_samples".format(default_id)
        samples=databases["system"].execute_query(sql)
        
        
      
        return{
            "current_view":current_view,
            "samples":samples,
            "clusters":clusters,
            "experiments":experiments,
            "group_id":self.data.get("group_id"),
            "group_name":self.data.get("group_name"),
            "sample_groups":sample_groups,
          
            
        }
        
    
    def get_view(self):
        p=get_project(self.data["experiment_group"])
        self.data[""]

GroupView.methods={
    "get_group_info":{
        "permission":"view"
        
    },
    "get_gene_suggest":{
        "permission":"view"
    },
    "get_gene_info":{
        "permission":"view"
    },
    
    "get_individual_gene_data":{
        "permission":"view"
    },
    "get_all_groups":{
        "permission":"edit"
    },
    "set_group":{
        "permission":"edit"
    },
    "save_view":{
        "permission":"edit"
    },
     "get_gene_data":{
        "permission":"view"
    },
     "get_similar_genes":{
         "permission":"view"
    },
     "get_sample_data":{
         "permission":"view",
         "user_required":True
    },
     "add_sample_data":{
        "permission":"view",
        "user_required":True
    },
     
     "clone_view":{
         "permission":"view",
         "user_required":True
     },
     "get_feature_set":{
         "permission":"view"
    }
    
}
projects["group_view"]=GroupView