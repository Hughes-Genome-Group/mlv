import json,os,csv,gzip
from app import databases,app

class HeatMap(object):
    def __init__(self,db,id):
        info = databases[db].execute_query("SELECT * FROM heat_maps WHERE id=%s",(id,))[0]
        self.name = info['name']
        self.id= id
        self.table_name= info['table_name']
        self.display_properties=info['display_properties']
        self.metadata_id=info['heat_map_metadata_id']
        self.data=info['data']
        if not self.data:
            self.data={}
        self.db=db
        
    def get_metadata(self):
        mid = self.metadata_id
        if not mid:
            return None
        sql = "SELECT * FROM  category_metadata WHERE id=%s"
        vals = databases[self.db].execute_query(sql,(mid,))
        vals[0]['display_properties']=self.display_properties
        return vals[0]
    
    def get_data(self,chr,start,end):
        sql = "SELECT * FROM {} WHERE chromosome=%s AND finish>%s AND start<%s".format(self.table_name)
        return databases[self.db].execute_query(sql,(chr,start,end))
    


def create_heat_map(db,bedfile,name,metadata_id,display_properties,description="",owner=0):
  
    table_name = create_table(db,name,metadata_id,display_properties,description,owner)
    features=[]
       
    
    with gzip.open(bedfile,'rt') as f:
        reader = csv.reader(f,delimiter="\t")
        for line in reader:
            arr = line[3].split("_")
            feature={"chromosome":line[0],
                     "start":int(line[1]),
                      "finish":int(line[2]),
                      "key":arr[0],
                      "value":arr[1]
                      }
            features.append(feature)
            if len(features) % 5000 ==0:
                databases[db].insert_dicts_into_table(features,table_name)
                features=[] 
        if len(features) != 0:
            databases[db].insert_dicts_into_table(features,table_name)
    _create_location_index(table_name,db)
    
    return HeatMap(db,int(table_name.split("_")[2]))

def create_table(db,name,metadata_id,display_properties,description,owner):
    sql = "INSERT INTO heat_maps (name,heat_map_metadata_id,display_properties,description,owner) VALUES (%s,%s,%s,%s,%s)"
    new_id = databases[db].execute_insert(sql,(name,metadata_id,json.dumps(display_properties),description,owner))
    table_name = "heat_map_"+str(new_id)
    sql = "UPDATE heat_maps SET table_name=%s WHERE id=%s"
    databases[db].execute_update(sql,(table_name,new_id))
   
    
    file_name = os.path.join(app.root_path, 'databases', 'create_heat_map.sql')
    script = open(file_name).read().format(db_user=app.config['DB_USER'],table_name=table_name)
    databases[db].run_script(script)
    return table_name 

def create_heat_map_metadata(file_name,key_column_name,db):
    columns={}
    values=[]
    key_column = None
    with open(file_name,'r') as f:
        reader = csv.reader(f)
        for line in reader:
            if reader.line_num==1:
                for count,item in enumerate(line):
                    if item == key_column_name:
                        key_column="c"+str(count)
                    columns["c"+str(count)]=item
                continue
            v={}
            for count,item in enumerate(line):
                v["c"+str(count)]=item
            values.append(v)
    sql = "INSERT INTO category_metadata (name,columns,data,key_column) VALUES (%s,%s,%s,%s)"
    vals = ("Cell Types",json.dumps(columns),json.dumps(values),key_column)
    id = databases[db].execute_insert(sql,vals)
    return id

def _create_location_index(table_name,db):
    file_name = os.path.join(app.root_path, 'databases', 'create_location_index.sql')
    script = open(file_name).read().format(table_name=table_name)
    databases[db].run_script(script)

