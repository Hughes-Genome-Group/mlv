from app.ngs.project import GenericObject,projects,get_project,get_projects,get_projects_summary
from app import databases,app
from random import randint
import os,ujson,random,string





class DataView(GenericObject):
    def get_template(self,args):
        return "data_view/page.html",{}
    
    
    def get_data(self):
        p=get_project(self.data["exp_id"])
        info= p.get_h5_sample_data()
        self.data["sample_ids"]=info["sample_ids"]
        self.data["sample_index_to_id"]=info["sample_index_to_id"]
        return self.data
        
    
    def get_experiment_data(self,field_ids=[]):
        p=get_project(self.data["exp_id"])
        return p.get_h5_data(field_ids)
    
    def get_sample_data(self,ids=[],user=None):
        
        fields=[]
        field_names=[]
        e=get_project(self.data["exp_id"])
            
        idr = e.data["h5_sample_data"]["field"]
        
        if ids:
            projects=get_projects(ids)
            for p in projects:
                if (user and not p.has_view_permission(user)):
                    continue
                fields.append({
                    "name":p.name,
                    "field":p.data["field"],
                    "datatype":p.data["datatype"],
                    "colors":p.data.get("colors"),
                    "graph":p.data.get("graph"),
                    "sortable":True,
                    "filterable":True,
                    "delimiter":p.data.get("delimiter"),
                    "columnGroup":"Sample Data",
                    "id":p.id    
                })       
                field_names.append(p.data["field"])
               
            sql = "SELECT {} as id,{} FROM mev_samples".format(idr,",".join(field_names))
            
        else:
            sql = "SELECT id FROM mev_samples"    
        data= databases["system"].execute_query(sql)
        
        
     
      
            
        
        return {
            "fields":fields,
            "data":data      
        }
    
    
    def save_view(self,data={}):
        self.data["current_view"]=data
        self.update()
        return True
    
    def get_all_experiments(self):
     
        filters={
              "type":["experiment"]
        }
        exps= get_projects_summary(user_id=self.owner,filters=filters,limit=100,extra_fields=",projects.data AS data")
        return exps
    
    def get_experiment_columns(self,id=1):
        e = get_project(id)
        return e.get_columns(include_sample_columns=True)
    
    
    def get_random_ids(self,table,number):
        sql = "SELECT id FROM {}".format(table)
        res = databases["system"].execute_query(sql)
        arr=[]
        for r in res:
            arr.append(r["id"])
        chosen_ids=[]
        for n in range(0,number):
            left = len(arr)
            if left==0:
                break
            index= randint(0,left)
            chosen_ids.append(arr[index])
            del arr[index]
        return chosen_ids
            
        
        
    
    def build_experiment_query(self,query_type="",fields=[],experiment=0,data={},sample_fields=[]):
        vars=tuple()
        where_clause=""
        e= get_project(experiment)
        table =e.data["table"]
        if query_type=="subset":
            rows=self.get_random_ids(table,data["count"])    
            where_clause= "WHERE {}.id=ANY(%s)".format(table)
            vars= vars+(rows,)
        elif query_type== "query":
            sql = "SELECT * FROM mev_experiment_fields WHERE id=%s"
            res= databases["system"].execute_query(sql,(data["query"]["field"],))
            field= res[0]["field"]
            operand=data["query"]["operand"]
            if operand not in ["=","<",">","!="]:
                raise Exception("operand not found")
            if data["query"]["value"] in ["null","NULL","Null"]:
                n=""
                if operand=="!=":
                    n="NOT"
                where_clause = "WHERE {} IS {} NULL".format(field,n)
            else:
                where_clause="WHERE {}{}%s".format(field,operand)
                vars = vars+(data["query"]["value"],)
        
            
       
        columns= e.get_columns(ids=fields,include_field_names=True)
        field_list=["{}.id AS id".format(table)]
        groups = set()
        for col in columns:
            t_field= col["field"].replace("[","").replace("]","")
            field_list.append("{} AS {}".format(col["field"],t_field))
            col["field"]=t_field
            col["columnGroup"]=col["group"]
            if not col["group"] in groups:
                groups.add(col["group"])
                col["master_group_column"]=True
            del col["group"]
            col["sortable"]=True
            col["filterable"]=True
            
        join_clause=""
        if len(sample_fields)!=0:
            for s in sample_fields:
                col = app.config["MEV_SAMPLE_COLUMNS"].get(s)
                if col:
                    field_list.append("mev_samples.{} AS {}".format(col["field"],col["field"]))    
                    c= col.copy()       
                    
                    c["columnGroup"]=c["group"]
                    del c["group"]
                    c["sortable"]=True
                    c["filterable"]=True
                    columns.append(c)
                    
            join_clause="INNER JOIN mev_samples ON sample = mev_samples.id"
        sql = "SELECT {} FROM {} {} {}".format(",".join(field_list),table,join_clause,where_clause)
        sql_string = databases["system"].get_sql(sql,vars)
        
        
        
        q_file_name = os.path.join(self.get_folder(),"defualt_query.sql")
        ou = open(q_file_name,"w")
        ou.write(sql_string.decode("utf-8"))
        ou.close()
        
        c_file_name = os.path.join(self.get_folder(),"default_columns.json")
        ou = open(c_file_name,"w")
        ou.write(ujson.dumps(columns))
        ou.close()
        
        count_sql = "SELECT COUNT(*) AS num FROM {} {} {}".format(table,join_clause,where_clause)
        res = databases["system"].execute_query(count_sql,vars)
        count =res[0]["num"]
        view_data={
            "query":q_file_name,
            "columns":c_file_name,
            "exp_name":e.name,
            "exp_id":e.id,
            "size":count
            
        }
        self.set_data("view_data",view_data)
        
        #res = databases["system"].execute_query(sql,vars)
        return True
    
    
    def add_tagging_column(self,name=""):
        tagging_columns =  self.data.get("tagging_columns")
        rs = "".join(random.choice(string.ascii_uppercase) for _ in range(4))
        if not tagging_columns:
            tagging_columns=[]
        tagging_column={
            "name":name,
            "field":rs,
            "datatype":"text",
            "sortable":True,
            "filterble":True,
            "columnGroup":"Tags"
            
        }
        if len(tagging_columns)==0:
            tagging_column["master_group_column"]=True
        tagging_columns.append(tagging_column)
        path =os.path.join(self.get_folder(),rs+".json")
        o = open(path,"w")
        o.write(ujson.dumps({}))
        o.close()
        
        self.set_data("tagging_columns",tagging_columns)
        return {"columns":[tagging_column]}    
            
        
    def update_tagging_column(self,field="",column="",ids=[],value=None):
        for tag in self.data["tagging_columns"]:
            if field==tag["field"]:
                fi = os.path.join(self.get_folder(),field+".json")
                data = ujson.loads(open(fi).read())
                if not value:
                    for id in ids:
                        i=str(id)
                        if data.get(i):
                            del data[i]
                else:
                    for id in ids:
                        data[str(id)]=value
            ou =open(fi,"w")
            ou.write(ujson.dumps(data))
            ou.close()
    
    
    
    def get_gene_suggest(self,term="",eid=0):
        sql = "SELECT name AS label ,id AS value FROM mev_experiment_fields WHERE experiment=%s AND name ILIKE %s ESCAPE '' LIMIT 20"
        res= databases["system"].execute_query(sql,(eid,"%"+term+"%"))
        return res
    
    def get_where_clause(self):
          q_file_name = os.path.join(self.get_folder(),"defualt_query.sql")
          arr= open(q_file_name).read().split("WHERE")
          if len(arr)==1:
              return ""
          else:
              return arr[1]
    
    def get_gene_data(self,gene_ids=[]):
        sql = "SELECT * FROM mev_experiment_fields WHERE id=ANY(%s)"
        gene_info = databases["system"].execute_query(sql,(gene_ids,))
        data={}
        columns=[]
        where_clause = self.get_where_clause()
        if where_clause:
            where_clause+=" AND "
        for gene in gene_info:
            field="d{}".format(gene["id"])
            columns.append({
                "id":gene["id"],
                "field":field,
                "name":gene["name"],
                "datatype":gene["datatype"],
                "sortable":True,
                "filterable":True
            })  
            sql = "SELECT id,{} AS {} FROM exp{}_default WHERE {} {} IS NOT NULL  ".format(gene["field"],field,self.data["view_data"]["exp_id"],where_clause,gene["field"])
            res= databases["system"].execute_query(sql)
            for r in res:
                d= data.get(r["id"])
                if not d:
                    d={}
                    data[r["id"]]=d
                d[field]=r[field]
        return {
            "data":data,
            "columns":columns      
        }
                           
    def get_h5_view(self):
           return {
            "data":res,
            "size":self.data["view_data"]["size"],
            "columns":columns,
            "graphs":graphs,
            "static_graphs":static_graphs,
            "tag_data":tag_data
        }
        
             
      
    def get_view(self,offset=0,limit=None):
        view_data = self.data.get("view_data")
        i = open(view_data["query"])
        sql = i.read()
        i.close()
        static_graphs=None
        columns=None
        graphs=[]
        tag_data={}
        if limit:
            extra= " WHERE {}.id> "
            if "WHERE" in sql:
                extra =  " AND {}.id>"
                
            table = "exp"+str(view_data["exp_id"])+"_default"
            extra= extra.format(table)
            sql = sql + " {}{} ORDER BY id LIMIT {}".format(extra,int(offset),int(limit))
        res = databases["system"].execute_query(sql)
        if limit == None or offset==0:
            i=open(view_data["columns"])
            columns = ujson.loads(i.read())
            tcs = self.data.get("tagging_columns")
            if tcs:
                columns=columns+tcs
                for tc in tcs:
                    fi = os.path.join(self.get_folder(),tc["field"]+".json")
                    data = ujson.loads(open(fi).read())
                    tag_data[tc["field"]]=data
                    
            i.close()
            
            p=get_project(self.data["view_data"]["exp_id"])
            graphs=self.data.get("graphs",[])
            if p.data.get("static_graphs"):
           
                static_graphs={
                "data":ujson.loads(open(p.data["static_graphs"]).read()),
                "link":"/data/{}/projects/{}/images/sg".format(p.db,p.id)       
                }
        return {
            "data":res,
            "size":self.data["view_data"]["size"],
            "columns":columns,
            "graphs":graphs,
            "static_graphs":static_graphs,
            "tag_data":tag_data
        }
        
    def get_gene_info(self,gene_list=[],exp_id=0):
        sql = "SELECT name,id  FROM mev_experiment_fields WHERE experiment =%s AND name=ANY(%s)"
        return databases["system"].execute_query(sql,(exp_id,gene_list))       
        
    
DataView.methods={
    "get_all_experiments":{
        "permission":"edit"
        
    },
    "save_view":{
        "permission":"edit"
        
    },
    "get_experiment_columns":{
        "permission":"edit"
    },
    "build_experiment_query":{
        "permission":"edit"
    },
    "get_view":{
        "permission":"view"
    },
    "get_gene_info":{
        "permission":"view"
    },
    "add_tagging_column":{
        "permission":"edit"
    },
    "update_tagging_column":{
        "permission":"edit"
    },
     "get_gene_suggest":{
        "permission":"view"
    },
    "get_gene_data":{
        "permission":"view"
    },
    "get_experiment_data":{
        "permission":"view"
    },
    "get_sample_data":{
         "permission":"view",
         "user_required":True
    },
  
  
    
}
        
                

projects["data_view"]=DataView