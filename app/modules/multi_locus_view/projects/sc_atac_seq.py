from app import app,db
from string import ascii_letters
from app.ngs.project import GenericObject,projects
import os,ujson,gzip
import shlex
from app.ngs.utils import get_temporary_folder
from app.jobs.email import send_email
from app.databases.user_models import User


class ScATACSeq(GenericObject):
    def get_template(self,args):
        self.get_folder()
        return "sc_atac_seq/sc_atac_seq.html",{}
    
    
    def get_data(self):
        records=None
        data_path= os.path.join(self.get_folder(),"data.json")
        if os.path.exists(data_path):
            i = open(data_path)
            records=ujson.loads(i.read())
            i.close()
        return {
            "records":records,
            "fields":self.data.get("fields"),
            "experiments":self.data.get("experiments"),
            "graphs":self.data.get("graphs"),
            "heat_maps":self.data.get("heat_maps"),
            "browser":self.data.get("browser")
            
        
        }
    
    
    def get_heat_map_data(self,heat_map_id=""):
        info = self.data["heat_maps"].get(heat_map_id)
        o = open(os.path.join(self.get_folder(),info["file"]))
        return ujson.loads(o.read())
      
        
    
    
    def upload_heat_map(self,files=[],rows=[],columns=[],name=""):
        heat_maps=self.data.get("heat_maps")
        if  not heat_maps:
            heat_maps={}
            self.data["heat_maps"]=heat_maps
        heat_map_id=None
        for l in ascii_letters:
            if not heat_maps.get("h"+l):
                heat_map_id="h"+l
                heat_maps[heat_map_id]={"file":heat_map_id+".json","name":name}
                break
        fields=[]
        data={}
        for cell in columns:
            data[cell]={}
        self.update()
        for count,r in enumerate(rows,start=1):
            fields.append({
                "datatype":"double",
                "name":r,
                "field":"{}{}".format(heat_map_id,count)
                
                
            })
            
        with open(files["upload_file"]) as f:
            count=0
            for line in f:
                count+=1
                if count<3:
                    continue
                arr=line.strip().split()
                cell_id=columns[int(arr[0])-1]
                data[cell_id][heat_map_id+arr[1]]=float(arr[2])
        o =open(os.path.join(self.get_folder(),heat_map_id+".json"),"w")
        js= {
            "data":data,
            "fields":fields,
            "name":name,
            "id":heat_map_id   
        }
        o.write(ujson.dumps(js))
        o.close()
        return js
        
    def create_from_avocato_output(self,output_dir=""):
        self.set_data("remote_avacato_dir",output_dir)
        remote_file = os.path.join(output_dir,"cell","cell_all.csv")
        tf = get_temporary_folder()
        local_file = os.path.join(tf,"cell.csv")
        remote_file= shlex.quote(remote_file)
        os.system("wget {} -O {}".format(remote_file,local_file))
        line_num=0
        headers=[]
        #work put headers
        with open(local_file) as f:
            for line in f:
                arr=line.strip().split(",")
              
                if line_num==0:
                    for c,item in enumerate(arr,start=1):
                        headers.append({
                            "name":item,
                            "position":c
                            
                        })
                    line_num+=1
                    continue
                if line_num==1:
                    
                    for c,item in enumerate(arr):
                        type="text"
                        try:
                            int(item)
                            type="integer"
                        except:                            
                            try:
                                float(item)
                                type="double"                          
                            except:
                                pass
                        headers[c]["datatype"]=type
                    break
        self.add_data_file(has_headers=True,files={"upload_file":local_file},fields=headers,delimiter=",")
        user = db.session.query(User).filter_by(id=self.owner).one()
        send_email(user,"Job Finished","job_finished",url=self.get_url(external=True),type="Avacato Visualisation")
                
    def add_data_file(self,has_headers=False,files=[],fields={},delimiter="\t"):
        f_c= self.data.get("field_counter",1)
        #nothing yet added
        new=False
        if f_c==1:
            new =True
            data={}
            self.data["fields"]=[{"datatype":"text","name":"Cell ID","field":"id","sortable":True,"filterable":True}]
        else:
            i=open(os.path.join(self.get_folder(),"data.json"))
            data=ujson.loads(i.read())
            i.close()
        cols=[]
        order_to_field={}
        
        
        path =os.path.join(app.root_path,"modules","multi_locus_view","sc_atac_rules.json")
        c_rules= ujson.loads(open(path).read())
        col_groups={}
        name_to_field={}
        for group in c_rules["groups"]:
            col_groups[group["name"]]=[]
             
        
        for item in fields[1:]:   
            field= "f"+str(f_c)  
            item["field"]=field
            item["id"]=field
            item["filterable"]=True
            item["sortable"]=True
            name_to_field[item["name"]]=field
            
            n = item["name"]                   
            for group in c_rules["groups"]:
                if group["rule"]=="starts_with":
                    for v in group["values"]:
                        if n.startswith(v):
                            item["columnGroup"]=group["name"]
                            item["datatype"]=group["datatype"]
                            if len(col_groups[group["name"]])==0:
                                item["master_group_column"]=True
                            col_groups[group["name"]].append(field)
                            
                            break
                    if item.get("columnGroup"):                
                        break
                elif group["rule"]=="exact_match":
                    if n in group["values"]:
                        item["columnGroup"]=group["name"]
                        item["datatype"]=group["datatype"]
                        if len(col_groups[group["name"]])==0:
                            item["master_group_column"]=True
                        col_groups[group["name"]].append(field)
                        break
      
      
            
            meth= str
            if item["datatype"]=="integer":
                meth=int
            elif item["datatype"]=="double":
                meth=float
            order_to_field[item["position"]]=[field,meth]
            f_c+=1
            del item["position"]
            cols.append(item)
            
            
        first_line=True
        file_name = files["upload_file"]
        if file_name.endswith(".gz"):
            handle = gzip.open(file_name,"rt")
        else:
            handle =open(file_name)
        with handle as f:
            for line in f:
                if first_line and has_headers:
                    first_line=False
                    continue
                line=line.strip()
                arr=line.split(delimiter)
                cid = arr[0]
                if new:
                    record={}
                    data[cid]=record
                else:
                    record=data[cid]
                rdf={}
                for count,f in enumerate(arr[1:],start=2):
                    info = order_to_field[count]
                    try:
                        if record != "":
                            record[info[0]]=info[1](f)
                    except:
                        pass
                    
        o=open(os.path.join(self.get_folder(),"data.json"),"w")
        o.write(ujson.dumps(data))
        o.close()
        self.data["fields"]+=cols
        self.data["field_counter"]=f_c
        description_text=""
        graphs=[]
        if new:
            for item in c_rules["default_graphs"]:
                has_fields=True
                for name in item["depends_on"]:
                    if not name_to_field.get(name):
                        has_fields=False
                        break
                if not has_fields:
                    continue
                title= item["graph"]["title"]
                g_text= ujson.dumps(item["graph"])
                for name in item["depends_on"]:
                    g_text= g_text.replace("##"+name+"##",name_to_field[name])
                
                graphs.append(ujson.loads(g_text))
                description_text+="<b>"+title+"</b>"
                description_text+="<p>"+item["description"]+"</p>"
                
        if description_text != "":
            graphs.append({
                "type":"text_box_chart",
                "text":description_text,
                "title":"Description of Plots",
                "location":{"x":6,"y":8,"height":4,"width":4}
                
            })       
            
        self.data["graphs"]=graphs
        self.update()
        return {
            "records":data,
            "fields":cols,
            "graphs":graphs,
            "new":new
        }
        
        
    
    def add_data(self,file,exp_name):
        i=open(os.path.join(self.get_folder(),"data.json"))
        data=ujson.loads(i.read())
        i.close()
        
        f_c= self.data.get("field_counter")
        
        
        
        fields= [
            {"datatype":"double","name":exp_name+" tSNE1","field":"f"+str(f_c),"columnGroup":exp_name},
            {"datatype":"double","name":exp_name+" tSNE2","columnGroup":exp_name,"field":"f"+str(f_c+1)},
            {"datatype":"text","name":exp_name+" cluster","field":"f"+str(f_c+2),"columnGroup":exp_name,"master_group_column":True}
        
        ]
        t1= "f"+str(f_c)
        t2= "f"+str(f_c+1)
        t3= "f"+str(f_c+2)
        with open(file) as f:
            for line in f:
                line=line.strip()
                arr=line.split("\t")
                if arr[0]=="Cell_barcodes":
                    continue
                data[arr[0]][t1]=float(arr[1])
                data[arr[0]][t2]=float(arr[2])
                data[arr[0]][t3]=(arr[3])
                
        o=open(os.path.join(self.get_folder(),"data.json"),"w")
        o.write(ujson.dumps(data))
        o.close()
        graph= {
            "type":"wgl_scatter_plot",
            "title":exp_name,
            "axis":{"x_label":"tSNE1","y_label":"tSNE2"},
            "param":["f1","f2"],
            "color_by":{
                "column":{
                    "name":"Cluster",
                    "field":t3,
                    "datatype":"text"
                    
                    }
            }
            
        }
        self.data["fields"]=self.data["fields"]+fields
        self.data["graphs"].append(graph)
        self.data["field_counter"]+=3
        self.update()
        
         
        
    def add_bam_coverage_track(self, url=""):
         
        path =os.path.join(app.root_path,"modules","multi_locus_view","sc_atac_rules.json")
        c_rules= ujson.loads(open(path).read())
        bro = c_rules["browser"]
        bro["config"][0]["url"]="/meths/{}/get_genes".format(self.db)
       
        
        proxies = app.config["TRACK_PROXIES"]
        if proxies:
            for p in proxies:
                url=url.replace(p,proxies[p])
        bro["config"][1]["url"]=url
        self.set_data("browser",bro)
        return bro
        
    
    def create_from_file(self,file):
        data={}
        with open(file) as f:
            for line in f:
                line=line.strip()
                arr=line.split("\t")
                if arr[0]=="Cell_barcodes":
                    continue
                data[arr[0]]={"f1":float(arr[1]),"f2":float(arr[2]),"f3":(arr[3])}
        
        o=open(os.path.join(self.get_folder(),"data.json"),"w")
        o.write(ujson.dumps(data))
        o.close()
        
        fields= [
            {"datatype":"text","name":"BarCode","field":"id","width":300},
            {"datatype":"double","name":"Exp1 tSNE1","field":"f1","columnGroup":"Exp1"},
            {"datatype":"double","name":"Exp1 tSNE2","columnGroup":"Exp1","field":"f2"},
            {"datatype":"text","name":"Exp1 cluster","field":"f3","columnGroup":"Exp1","master_group_column":True}
        
        ]  
        self.set_data("fields",fields)
        self.set_data("experiments",["exp1"])
        self.set_data("graphs",[{
            "type":"wgl_scatter_plot",
            "title":"exp1",
            "axis":{"x_label":"tSNE1","y_label":"tSNE2"},
            "param":["f1","f2"],
            "color_by":{
                "column":{
                    "name":"Cluster",
                    "field":"f3",
                    "datatype":"text"
                    
                    }
            }
            
        }])
        self.set_data("field_counter",4)     


projects["sc_atac_seq"]=ScATACSeq
ScATACSeq.methods={
    "add_data_file":{
        "permission":"edit"
        
    },
    "upload_heat_map":{
        "permission":"edit"
        
    },
    "get_heat_map_data":{
        "permission":"view"
        
    },
    "add_bam_coverage_track":{
        "permission":"edit"
    }
    
}