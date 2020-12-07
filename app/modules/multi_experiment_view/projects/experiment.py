from app.ngs.project import GenericObject,projects,create_project
from app import databases,app
import ujson,os,csv
from string import ascii_lowercase
import h5py
import numpy

import matplotlib.pyplot as plt
cat_colors=[
    "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf", "#999999", "#1CE6FF", "#FF34FF",
    "#FF4A46", "#008941", "#676FA6", "#A30059", "#FFDBE5", "#7A4900", "#0000A6", "#63FFAC", "#B79762",
    "#004D43", "#8FB0FF", "#997D87", "#5A0007", "#809693", "#FEFFE6", "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80"
    ]


class Experiment(GenericObject):
    
    def get_template(self,args):
        return "experiment/page.html",{}
    
    def get_data(self):
        data={
            "item_count":self.data.get("item_count"),
            "uploading_error":self.data.get("uploading_error"),
            "uploading_data":self.data.get("uploading_data")
            
        }
        templates=[]
        for item in app.config["MEV_EXPERIMENT_TEMPLATES"].values():
            templates.append({"id":item["id"],"name":item["name"]})
        data["templates"]=templates
        return data
    
    
    def get_h5_sample_data(self):
         f= h5py.File(self.data["h5_file"])
         loc = self.data["h5_sample_data"]["column"]
         
         return {
             "sample_ids":numpy.array(f[loc[0]][loc[1]]).tolist(),
             "sample_index_to_id":numpy.array(f[loc[0]]["__categories"][loc[1]]).tolist()
             
         }
           
            
    def get_col_name_to_field(self):
        sql = "SELECT name,field,datatype FROM mev_experiment_fields WHERE experiment=%s"
        data={}

        recs =databases["system"].execute_query(sql,(self.id,))
        for rec in recs:
            data[rec["name"]]=[rec["field"]]
            func = str
            if rec["datatype"] == "double":
                func =float
            elif rec["datatype"]=="integer":
                func=int
            data[rec["name"]].append(func)  
           
        return data


    #box_field = sample
    #group=antibodies
    #graph__field=meta12
    #cat_va;=1
    def create_box_plots(self,group="",graph_field=0,box_field=0,category=""):
      
        
        sql = "SELECT mev_experiment_fields.name AS name ,mev_experiment_fields.id AS id,mev_experiment_fields.field AS field "+\
              "FROM mev_experiment_fields INNER JOIN mev_field_to_group on field_id=mev_experiment_fields.id LEFT JOIN "+\
              "mev_field_groups ON group_id=mev_field_groups.id  WHERE mev_field_groups.name =%s AND mev_field_groups.experiment=%s"
        res= databases["system"].execute_query(sql,(group,self.id))
        group_fields=[]
        field_to_name={}
        for item in res:
            group_fields.append("{} AS f{}".format(item["field"],item["id"]))
            field_to_name["f{}".format(item["id"])]=item["name"]
                          
                          
        #graph field
        sql = "SELECT field,name,id FROM mev_experiment_fields WHERE id=%s OR id=%s"
        other_fields=databases["system"].execute_query(sql,(graph_field,box_field))
        for item in other_fields:
            if item["id"]==graph_field:
                gf_field=item["field"]
                gf_field_name= item["name"]
            else:
                bf_field=item["field"]
                bf_field_name=item["name"]
                
        sql = "SELECT {} AS category,COUNT(*) AS num FROM {} GROUP BY {} ORDER BY num DESC".format(gf_field,self.data["table"],gf_field)
        res =  databases["system"].execute_query(sql)
        group_categories=[]
        for r in res:
            group_categories.append(r["category"])
            
        sql = "SELECT {} AS category,COUNT(*) AS num FROM {} GROUP BY {} ORDER BY num DESC".format(bf_field,self.data["table"],bf_field)   
        res= databases["system"].execute_query(sql)
        box_categories=[]
        for r in res:
            box_categories.append(r["category"])
            
                
        count=1
        static_graph_table=[] 
        for category in group_categories:
            sql = "SELECT {},{} AS bf_field FROM {} WHERE {}=%s".format(",".join(group_fields),bf_field,self.data["table"],gf_field)
                
            data= databases["system"].execute_query(sql,(category,))
            plot_data={}
            
            for field in field_to_name:
                plot_data[field]={}
                for cat in box_categories:
                    plot_data[field][cat]=[]
                    
                              
            for item in data:
                for field in field_to_name:
                    plot_data[field][item["bf_field"]].append(item[field])
            data = None
            
            colors= cat_colors[0:len(box_categories)]
            dir = os.path.join(self.get_folder(),"images")
            if not os.path.exists(dir):
                os.mkdir(dir)
            
            
           
            for field in field_to_name:
                
                box_data=[]
                
                for cat in box_categories:
                    box_data.append(plot_data[field][cat])
                box =plt.boxplot(box_data,patch_artist=True,labels=box_categories,showfliers=False)
                for patch, color in zip(box['boxes'], colors):
                    patch.set_facecolor(color)
                plt.title(gf_field_name+" "+category+" "+field_to_name[field],fontsize=20)
                plt.xticks(rotation=45)
                plt.savefig(os.path.join(dir,"sg{}.png".format(count)))
                static_graph_table.append({
                    "id":count,
                    "cluster_field":gf_field_name,
                    "cluster_id":category,
                    "group":group,
                    "group_id":field_to_name[field],
                    "type":"box_plot",
                    "boxes":bf_field_name  
                })
                count+=1
                
                
                plt.clf() 
          
        path= os.path.join(self.get_folder(),"static_graphs.json")
        self.set_data("static_graphs",path)
        o = open(path,"w")
        o.write(ujson.dumps(static_graph_table))
        o.close()
           
                
        
               
            
    def create_scatter_plots(self,x_vals=[],y_vals=[],colors=[]):
        pass       
        

    def get_columns(self,ids=None,include_field_names=False,include_sample_columns=False):
        vars= (self.id,)
        field_name=""
        if include_field_names:
            field_name= ",field"
        sql = "SELECT mev_experiment_fields.name AS name ,mev_experiment_fields.id AS id,"+\
              "mev_field_groups.name as group,datatype{} FROM mev_experiment_fields LEFT  "+\
              "JOIN mev_field_to_group on field_id=mev_experiment_fields.id LEFT JOIN "+\
              "mev_field_groups ON group_id=mev_field_groups.id  WHERE mev_experiment_fields.experiment =%s"
        sql=sql.format(field_name)
        if ids:
            sql += " AND mev_experiment_fields.id=ANY(%s)"
            vars=vars+(ids,)
            
        res = databases["system"].execute_query(sql,vars)
        if include_sample_columns and not self.data.get("no_sample_ids"):
            res= res+list(app.config["MEV_SAMPLE_COLUMNS"].values())
        return res
    
    def insert_genes_from_hdf5_file(self,filename):
        import h5py
        columns=[]
        f= h5py.File(filename)
        names=f["var"]["_index"]
        for count,name in enumerate(names):
            columns.append({
               "name":name,
               "group":"genes",
               "datatype":"double",
               "data":{
                   "h5py_index":count
                } 
            })
        self.insert_columns(columns)
        
    def insert_genes(self,eids,eid_to_name):
        columns=[]
        for eid in eids:
            columns.append({
                "name":eid_to_name[eid],
                "group":"genes",
                "datatype":"double",
                "uni_id":eid
                
            })
        self.insert_columns(columns)
        
            
    
    def create_table(self):
        file_name = os.path.join(app.root_path,"modules","multi_experiment_view","jobs","create_data_table.sql")
        table_name= "exp{}_default".format(self.id)
        self.set_data("table",table_name)
        script = open (file_name).read().format(db_user=app.config['DB_USER'],table_name=table_name)
        databases["system"].run_script(script)
        
    
    
    def add_dimension_reduction(self,group,dimensions=2):
        import numpy,umap
        from sklearn.manifold import TSNE
        sql = "SELECT field_name FROM mev_field_groups WHERE name = %s AND experiment=%s"
        res =databases["system"].execute_query(sql,(group,self.id))
        sql ="SELECT id,{} as f FROM {} ORDER BY id".format(res[0]["field_name"],self.data["table"])
        res= databases["system"].execute_query(sql)
        data=[]
        for r in res:
            data.append(r["f"])
         
        reducer=umap.UMAP(n_components=dimensions)
        result_u = reducer.fit_transform(data)
        result_t = TSNE(n_components=dimensions).fit_transform(data)
        
        '''self.insert_columns([
            {"name":"tSNE1","datatype":"double","group":"Dimension Reduction"},
            {"name":"tSNE2","datatype":"double","group":"Dimension Reduction"},
            {"name":"UMAP1","datatype":"double","group":"Dimension Reduction"},
            {"name":"UMAP2","datatype":"double","group":"Dimension Reduction"}            
        ])'''
        
        n_to_f = self.get_col_name_to_field()
        update_list=[]
        for index,u in enumerate(result_u):
            t=result_t[index]
            update_list.append({
                "id":res[index]["id"],
                 n_to_f["tSNE1"][0]:float(t[0]),
                 n_to_f["tSNE2"][0]:float(t[1]),
                 n_to_f["UMAP1"][0]:float(u[0]),
                 n_to_f["UMAP2"][0]:float(u[1])   
                
            })
        databases["system"].update_table_with_dicts(update_list,self.data["table"])            
        
            
    
    def delete(self,hard=False):
        #get all views
        sql = "SELECT id FROM projects WHERE (data#>>'{view_data,exp_id}')::integer=%s AND type='data_view'"
        res= databases["system"].execute_query(sql,(self.id,))
        view_ids=[]
        for r in res:
            ids.append(r['id'])
        
        if not hard:
            super().delete()
            for i in view_ids:
                p=get_project(i)
                p.delete()
        else:
            sql = "SELECT id FROM mev_experiment_fields WHERE experiment=%s"
            res = databases["system"].execute_query(sql,(self.id,))
            ids=[]
            for r in res:
                ids.append(r["id"])
            sql = "DELETE FROM mev_field_to_group WHERE field_id = ANY(%s)"
            databases["system"].execute_delete(sql,(ids,))
            sql = "DELETE FROM mev_experiment_fields WHERE experiment=%s"
            databases["system"].execute_delete(sql,(self.id,))
            sql = "DELETE FROM mev_field_groups WHERE experiment=%s"
            databases["system"].execute_delete(sql,(self.id,))
            databases["system"].delete_table(self.data["table"])          
            super().delete(True)
            for i in view_ids:
                p=get_project(i)
                p.delete(True)
      
        
    def load_gene_data_from_hd5_file(self,filename,chunksize=1000):
        import h5py
        
        sql = "SELECT id FROM mev_field_groups WHERE name='genes' AND experiment=%s"
        gid = databases["system"].execute_query(sql,(self.id,))[0]["id"]
        sql = "SELECT field,data  FROM mev_experiment_fields INNER JOIN mev_field_to_group ON id=field_id AND group_id=%s"
        genes = databases["system"].execute_query(sql,(gid,))
        g_index={}
        for g in genes:
            g_index[g["data"]["h5py_index"]]=g["field"]
        table= self.data["table"]
        f= h5py.File(filename)
        indices = f['X']["indptr"]
        gene_data=f['X']["indices"]
        data = f['X']['data']
        size = f['X']["indptr"].size
        update_list=[]
        for i in range(0,size):
            
            start = indices[i]
            if i == (size-1):
                end=size
            else:
                end= indices[i+1]
            values = list(data[start:end])
            genes=list(gene_data[start:end])
            
            val_length= len(values)
            no_items= int(val_length/999)+1
            items=[]
            for p in range(0,no_items):
                items.append({"id":i+1})
            item_index=0
            for n in range(0,len(values)):
                try:
                    items[item_index][g_index[genes[n]]]=float(values[n])
                except Exception as e:
                    print(e)
                if len(items[item_index])==1000:
                    item_index+=1
            
            for item in items:
                if len(item)!=1:        
                    update_list.append(item)
            if (i+1)%chunksize==0:
                
                databases["system"].update_table_with_dicts(update_list,table)
                update_list=[]
                print(i+1)
                
        databases["system"].update_table_with_dicts(update_list,table)
        update_list=[]
   
   
   
    def get_h5_data(self,field_ids=[]):
        sql = "SELECT name,data,id,datatype FROM mev_experiment_fields WHERE experiment=%s AND id = ANY(%s)"
        res = databases["system"].execute_query(sql,(self.id,field_ids))
        columns=[]
        data={}
        already =set()
        f= h5py.File(self.data["h5_file"])
        
        for r in res:
            h5_data=r["data"].get("h5_data")
            gid= r["data"].get("h5_index")                      
            col= {
                "name":r["name"],
                "field":r["id"],
                "datatype":r["datatype"],
                "sortable":True,
                "filterable":True,
               
                
            }
            if h5_data == None and gid:
                col_name="_g"+str(gid)
                col["data_col"]=col_name
                col["columnGroup"]="Genes"
                col["gene_column"]=True
                js =os.path.join( self.data["gene_files"],str(gid)+".json")
                h= open(js)
                data[col_name]=ujson.loads(h.read())
                h.close()
        
            elif h5_data:
                col_name= h5_data["column"][0]+","+h5_data["column"][1]
                try:
                    col["index"]=h5_data["index"]
                except:
                    pass
                col["data_col"]=col_name
                col["columnGroup"]=h5_data.get("group")
                if not col_name in already:
                    col_vals = numpy.array(f[h5_data["column"][0]][h5_data["column"][1]]).tolist()
                data[col_name]=col_vals
                already.add(col_name)
                if h5_data.get("names"):
                    col["col_names"]=  numpy.array(f[h5_data["column"][0]]["__categories"][h5_data["column"][1]]).tolist()  
           
            columns.append(col)
           
        return {
            "columns":columns,
            "data":data     
        }
        
   
            
            
            
         
         
         
           
    def insert_columns(self,columns):
    
        table = "exp{}_default".format(self.id)
        col_list=[]
        col_names=[]
        groups={}
        for col in columns:
            col_info={
                "name":col["name"],
                "datatype":col["datatype"],
                "experiment":self.id,
                
            }
            col_info["data"]=ujson.dumps(col.get("data",{}))
            if col.get("uni_id"):
                col_info["uni_id"]=col.get("uni_id")
            
            
            if col.get("group"):
                col_names.append(col["name"])
                existing_type= groups.get(col["group"],col["datatype"])
                if existing_type != col["datatype"]:
                    raise  Exception("mixed groups")
                groups[col["group"]]=col["datatype"]
                col_info["group"]=col["group"]
            if col.get("description"):
                col_info["description"]=col["description"]
            col_list.append(col_info)
            
        #does group exists
        sql = "SELECT id,name,field_name FROM mev_field_groups WHERE experiment=%s"
        res = databases["system"].execute_query(sql,(self.id,))
        name_to_group={}
        group_field_index=3
        for r in res:
            if groups.get(r["name"]):
                name_to_group[r["name"]]=r
                sql = "SELECT COUNT (*) AS num FROM mev_experiment_fields INNER JOIN mev_field_to_group ON mev_experiment_fields.id = mev_field_to_group.field_id WHERE group_id=%s"
                count  = databases["system"].execute_query(sql,(r["id"],))[0]["num"]
                r["count"]=count+1
                del groups[r["name"]]
                
            group_field_index +=1
        for group in groups:
            group_f= ascii_lowercase[group_field_index]
            sql = "INSERT INTO  mev_field_groups (name,experiment,field_name) VALUES(%s,%s,%s)"
            fid = databases["system"].execute_insert(sql,(group,self.id,group_f))
            name_to_group[group]={
                "name":group,
                "id":fid,
                "field_name":group_f,
                "count":1        
            }
            c_type="text[]"
            dt = groups[group]
            if dt=="double":
                c_type="double precision[]"
            elif dt=="integer":
                c_type="integer[]"
            
            databases["system"].add_columns(table,[{"datatype":c_type,"name":group_f}])
            group_field_index+=1
         
       
        nf_dt_counts={}
        sql = "SELECT COUNT (*) AS num FROM mev_experiment_fields WHERE experiment=%s AND field LIKE 'a[%%'"
        nf_dt_counts["text"]= databases["system"].execute_query(sql,(self.id,))[0]["num"]+1
        sql = "SELECT COUNT (*) AS num FROM mev_experiment_fields WHERE experiment=%s AND field LIKE 'b[%%'"
        nf_dt_counts["integer"]= databases["system"].execute_query(sql,(self.id,))[0]["num"]+1
        sql = "SELECT COUNT (*) AS num FROM mev_experiment_fields WHERE experiment=%s AND field LIKE 'c[%%'"
        nf_dt_counts["double"]= databases["system"].execute_query(sql,(self.id,))[0]["num"]+1
        
        
        for col in col_list:
            if col.get("group"):
                gr = name_to_group[col.get("group")]
                col["field"]=gr["field_name"]+"["+str(gr["count"])+"]"
                gr["count"]=gr["count"]+1
            else:
                if col["datatype"]=="text":
                     col["field"]="a["+str(nf_dt_counts["text"])+"]"
                     nf_dt_counts["text"]+=1
                if col["datatype"]=="integer":
                     col["field"]="b["+str(nf_dt_counts["integer"])+"]"
                     nf_dt_counts["integer"]+=1
                if col["datatype"]=="double":
                     col["field"]="c["+str(nf_dt_counts["double"])+"]"
                     nf_dt_counts["double"]+=1
        col_name_to_gid={}    
        for col in col_list:
             gr = col.get("group")
             if gr:
                 col_name_to_gid[col["name"]]= name_to_group[gr]['id']
                 del col["group"]
                  
        databases["system"].insert_dicts_into_table(col_list,"mev_experiment_fields")
        
        sql = "SELECT id,name FROM mev_experiment_fields WHERE name=ANY(%s) AND experiment = %s"
        res = databases["system"].execute_query(sql,(col_names,self.id))
        col_name_to_id={}
        for r in res:
            col_name_to_id[r["name"]]=r["id"]
        update_list=[]
        for name in col_name_to_gid :
            update_list.append({"field_id":col_name_to_id[name],"group_id":col_name_to_gid[name]})
        
            
        databases["system"].insert_dicts_into_table(update_list,"mev_field_to_group")
        
    def upload_data_file(self,columns=[],files={},template="none",use_sample_ids=True):
        try:
            if not self.data.get("table"):
                self.create_table()
            if template!="none":
                t_info = app.config["MEV_EXPERIMENT_TEMPLATES"].get(template)
                path =os.path.join(app.root_path,"modules","multi_experiment_view",t_info["file"])
                c_rules= ujson.loads(open(path).read())
                new_cols=[]
                for col in columns:
                    n = col["name"]
                    new_col={"name":n}
                    for group in c_rules["groups"]:
                        if group["rule"]=="starts_with":
                            for v in group["values"]:
                                if n.startswith(v):
                                    new_col["group"]=group["name"]
                                    new_col["datatype"]=group["datatype"]
                                    break
                            if new_col.get("group"):                
                                break
                        elif group["rule"]=="exact_match":
                            if n in group["values"]:
                                new_col["group"]=group["name"]
                                new_col["datatype"]=group["datatype"]
                    if new_col.get("group"):
                        new_cols.append(new_col)
                    else:
                        col["datatype"]=col["type"]
                        new_cols.append(col)
            self.insert_columns(new_cols)
       
            name_to_field= self.get_col_name_to_field()
            count=0
            with open(files["upload_file"]) as f:
                reader = csv.DictReader(f,delimiter="\t")
                fields = reader.fieldnames
                update_list=[]
                count=0
                for row in reader:
                    count+=1
                    item={}
                    for name in fields:
                        info = name_to_field[name]
                        try:
                            item[info[0]]=info[1](row[name])
                        except:
                            pass
                        
                    update_list.append(item)
                    if len(update_list)==5000:
                        databases["system"].insert_dicts_into_table(update_list,self.data["table"])
                        update_list=[]
                       
                databases["system"].insert_dicts_into_table(update_list,self.data["table"])
            self.set_data("item_count",count)
            self.set_data("uploading_data",False)
            self.set_data("no_sample_ids",not use_sample_ids)
        except Exception as e:
            upload_file= files.get("upload_file")
            app.logger.exception("Cannot upload data exp id {}  file:{} ".format(self.id,upload_file))
            self.set_data("uploading_data",False)
            self.set_data("uploading_error",True)        
      
      
    def insert_data(self,datafile,chunk_size=10000,update=False):
        table = "exp{}_default".format(self.id)
        n_to_f =self.get_col_name_to_field()
        update_list=[]
        items={}
        count=0
     
        with open(datafile) as df:
            
            reader = csv.DictReader(df,delimiter="\t")
            fields = reader.fieldnames
            count=1
            for row in reader:
               
                
                item={}
                if update:
                    item["id"]=count
                    count+=1
                for field in fields:
                    info = n_to_f.get(field)
                    if not info:
                        continue
                    try:
                        item[info[0]]=info[1](row[field])
                    except:
                       pass
                
                
                update_list.append(item)
                    
                if len(update_list)==chunk_size:
                    if update:
                        databases["system"].update_table_with_dicts(table,update_list)
                    else:
                        databases["system"].insert_dicts_into_table(update_list,table)
                    update_list=[]
            if update:
                databases["system"].update_table_with_dicts(table,update_list)
            else:      
                databases["system"].insert_dicts_into_table(update_list,table)
            update_list=[]          
                         
        sql = "SELECT COUNT(*) AS num FROM {}".format(table)
        count = databases["system"].execute_query(sql)[0]["num"]
        self.set_data("item_count",count)


Experiment.methods={
    "upload_data_file":{
        "permission":"edit",
        "async":True,
        "running_flag":["uploading_data",True],
    }
}

projects["experiment"]=Experiment


def create_new_experiment(db,name,type,description=""):
    p = create_project(db,name,"experiment",description,returning_object=True)
    p.data["type"]=type
    file_name = os.path.join(app.root_path,"modules","multi_experiment_view","jobs","create_data_table.sql")
    table_name= "exp{}_default".format(p.id)
    p.data["table"]=table_name
    p.update()
        
    script = open (file_name).read().format(db_user=app.config['DB_USER'],table_name=table_name)
    databases["system"].run_script(script)
    return p



def insert_sample_data(name,label,datatype):
    details={
        "datatype":datatype,
        "field":name,
        "name":label,
        "experiment":0
        
    }
    databases["system"].insert_dict_into_table(details,"mev_experiment_fields")





