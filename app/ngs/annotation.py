from app import databases,app
from app.ngs.utils import get_temporary_folder
import os,gzip,ujson,shutil

columns=[
     {"field":"name","name":"Name","type":"text"},
     {"field":"type","name":"Type","type":"text"},
     {"field":"date_added","name":"Date Added","type":"date"},
     {"field":"description","name":"Description","type":"text"},     
]


def get_all_annotation_sets(genome,ids=None):
    '''Retrieves information about all the annotation sets  
        Args:
            genome (str): The genome name
            ids (list[int]): Limit the annotation set those with ids in 
                the list. Optional default None (all sets returned)
        Returns:   
            A list of dictionaries containing id,name,type,date added
            and description for each annotation set
        
    '''
    
    sql = "SELECT id,name,type,date_added,description from annotation_sets"
    vars = None
    if ids:
        sql+=" WHERE id = ANY(%s)"
        vars=ids
    results =databases[genome].execute_query(sql,(vars,))
    for item in results:
        item['date_added']=item['date_added'].strftime("%Y-%m-%d")
    return results
    


def get_annotations_in_view_set(view_set,annotation_sets,simple=False,
                                margin=None,specific_views=None):
    '''Gets all annotations which overlap with each view    
        Args:
            genome (str): The genome name
            view_set (int): The id of the view_set
            annotation_sets (list[int]): A list annotation set ids
            simple (Optional[boolean]): Defaults to False. If True
                just the id of the views and viewset will be returned.
            specific_views (Optional[list]): A list of view ids, only
                these will be processed (Default is none - all views returned)
        Returns:
             A Dictionary with the view set id as key pointing
             to a list of annotations present in the set.
        
    '''
    db=databases[view_set.db]
    vs="view_set_"+str(view_set.id)
    annotation_sets = map(str,annotation_sets)
    ids = ",".join(annotation_sets)
    select =vs+".id as vsid ,annotation_set_id"
    if not simple:
        select+=(",annotations.chromosome as chromosome,annotations.start as start,"
                 "annotations.finish as finish,annotations.name as name")
    m_m=""
    p_m=""
    if margin:
        m_m="-"+str(margin)
        p_m="+"+str(margin)
       
    sql =("SELECT {select} FROM {vs} INNER JOIN annotations"
          " ON  {vs}.chromosome=annotations.chromosome AND"
          " {vs}.finish{p_m} > annotations.start AND {vs}.start{m_m} < annotations.finish"
          " AND annotation_set_id IN ({ids})").format(select=select,vs =vs,ids=ids,m_m=m_m,p_m=p_m)
    
    
    if specific_views:
         sv= ",".join(list(map(str,specific_views)))
         specific_views =" AND {vs}.id IN({sv})".format(vs=vs,sv=sv)
         sql += specific_views
        
    
    print (sql)
    results = db.execute_query(sql)
    annotations={}
    for res in results:
        info =annotations.get(res['vsid'])
        if not info:
            info=[]
            annotations[res['vsid']]=info
        info.append(res)
    return annotations

def create_annotation_set_from_bed(genome,bed_file,type,name,description="",data={}):
    db =databases[genome]
    
    sql = "INSERT INTO annotation_sets (name,description,type,data) VALUES (%s,%s,%s,%s)"
    set_id =db.execute_insert(sql,(name,description,type,ujson.dumps(data)))
    items=[]
    first=True
    include_name=True
    offset=0
    if bed_file.endswith(".gz"):
        f= gzip.open(bed_file,mode="rt")
    else:
        f= open(bed_file)
    with f:
        for line in f:
            arr =line.strip().split("\t")
            if first:
                if not arr[0].startswith("chr"):
                    offset=1
                first=False
                if len(arr)==3:include_name=False
                    
            item={
                "chromosome":arr[offset],
                "start":int(arr[offset+1]),
                "finish":int(arr[offset+2]),
                "annotation_set_id":set_id             
            }
            if include_name:
                item['name']=arr[offset+3]
            
            items.append(item)
            if len(items) % 5000 ==0:
                db.insert_dicts_into_table(items,"annotations")
                items=[] 
    if len(items)!=0:
        db.insert_dicts_into_table(items,"annotations")
    return AnnotationSet(genome,set_id)

def create_from_remote_file(genome,remote_location,name,type,description=""):
    
    f_name= os.path.split(remote_location)[1]
    folder = get_temporary_folder()
    file_name=os.path.join(folder,f_name)
    command = "wget '{}' -O {}".format(remote_location,file_name)
    data={"remote"}
    os.system(command)
    create_annotation_set_from_bed(genome,file_name,type,name,description,data)
    shutil.rmtree(folder)
    
    
    

def get_all_columns():
    return columns
        
def get_all_annotations(genome,chr,start,end,type=None,set_ids=None):
    '''Gets all annotations which overlap with each view
       
    Args:
        genome (str): The genome name
        start (int): The start of the region
        end (int): The end of the region
        type (Optional(str)): Defaults to None. If a value is supplied,
            then only annotations of that type will be returned.
        set_ids (Optional(list(int))): Defaults to None. Only annotations
            corresponding tp the set ids in the list will be returned
    Returns:
        A list of dictionaries containing all the annotations present
        in the speicified region
    '''
    
    db = databases[genome]
    sql = "SELECT * FROM annotations WHERE chromosome=%s AND finish>%s AND start<%s"
    args = (chr,start,end)
    if type:
        sql+=" AND type= ANY(%s) "
        args=args+type
        
    if set_ids:
        sql+= " AND annotation_set_id=ANY(%s)"
        args=args+(set_ids,)
    sql += " ORDER BY start"
    results = db.execute_query(sql,args)
    return results
  

           
        
            
class AnnotationSet(object):
    def __init__(self,db,id):
        info = databases[db].execute_query("SELECT * FROM annotation_sets WHERE id=%s",(id,))[0]
        self.name = info['name']
        self.id= id
        self.description=info['description']
            