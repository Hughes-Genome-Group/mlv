from app import databases,app
from app.databases.main_database import get_where_clause
from pathlib import Path
from time import sleep
import json,os,csv,gzip,ujson,shutil,sys,subprocess
from _csv import reader
from app.ngs.gene import get_genes_in_view_set,GeneSet
from app.zegami.zegamiupload import get_tags,update_collection,create_new_set,delete_collection
from app.ngs.utils import get_track_proxy,get_temporary_folder



class ViewSet(object):
    def __init__(self,db,id):
        res = databases[db].execute_query("SELECT * FROM view_sets WHERE id=%s",(id,))
        if len(res)==0:
            app.logger.debug("Attempting to access not existant viewset {}".format(id))
            self.id=-1
        else:
            info=res[0]
            self.name = info['name']
            self.owner = info["owner"]
            self.id= id
            self.description=info['description']
            self.fields= info['fields']
            self.table_name= info['table_name']
            self.data=info['data']
            if not self.data:
                self.data={}
            self.db=db
    
    def add_wig_stats(self,wig_file,name="Peak",chunk_size=50000,offset=0):
        '''For each location in View set. stats about the given wig file
        will be added to the table: width, max height and area
        
        Args:
            wig_file(str): The location of the wig file from which to calculate
                the stats
            name(Optional(str)): The name(tag) to add to each label. Default is 'Peak'
                e.g Peak Width, Peak Max Height and Peak Area 
        
        '''
        import pyBigWig,time
      
        width_label=name+" Width"
        height_label=name+" Max Height"
        area_label=name+" Area"
        density_label=name+" Density"
        group_name = name+" Stats"
        
        info = self.add_columns([{"label":width_label,"datatype":"integer","columnGroup":group_name},
                                 {"label":height_label,"datatype":"double","columnGroup":group_name},
                                 {"label":density_label,"datatype":"double","columnGroup":group_name},
                                 {"label":area_label,"datatype":"double","columnGroup":group_name,"master_group_column":True}],group_name)
        
        width_field= info[width_label]
        height_field= info[height_label]
        area_field= info[area_label]
        density_field=info[density_label]
          
        bw=pyBigWig.open(wig_file)
        num =self.get_view_number()
        while offset<=num["count"]:
            sql = "SELECT id,chromosome,start,finish FROM {} ORDER BY id OFFSET {} LIMIT {}".format(self.table_name,offset,chunk_size)
            locations = databases[self.db].execute_query(sql)
      
            stats=[]
            for loc in locations:         
                width =loc['finish']-loc['start']
                try:
                    max_height=bw.stats(loc['chromosome'],loc['start'],loc['finish'],type="max",exact=True)[0]
                    if max_height==None:
                        max_height=0
                    av_height = bw.stats(loc['chromosome'],loc['start'],loc['finish'],exact=True)[0]
                    if av_height== None:
                        av_height=0
                    area= av_height*width
                except:
                    area=0
                    av_height=0
                    max_height=0
                stats.append({width_field:width,
                          density_field:int(av_height),
                          height_field:max_height,
                          area_field:area,
                          "id":loc['id']})   
            databases[self.db].update_table_with_dicts(stats,self.table_name)
            print (str(offset))
            offset+=chunk_size
            
        
    
       
    
    
    def create_icon(self,view_id=1,height=100,width=150):
        '''Creates (or replaces) an icon for the viewset based on the view supplied
        (or 1)
         Args:
           view_id (Optional[int]): The id view set (or 1 id not given)
        '''
        from app.ngs.thumbnail import ThumbnailSet
        ts = ThumbnailSet(self.db,height=height,width=width)
        ts.draw_view_set(self,gene_set=1,specific_views=[view_id],folder="icon")
        folder = self.get_folder("icon")
        original_location = os.path.join(folder,"tn"+str(view_id)+".png")
        new_location = os.path.join(folder,"icon.png")
        os.rename(original_location,new_location)
        self.data['icon_location']=os.path.join(folder,"tn"+str(view_id))
    
    
    def deepbind_model(self,models,length=500):
        from app.ngs.genome import Genome
        genome = Genome(self.db)
        folder = get_temporary_folder()
        id_file = os.path.join(folder,"temp.ids")
        out_id = open (id_file,"w")
        for model in models:
            out_id.write(model["id"]+"\n")
        out_id.close()
        sql = "SELECT id,chromosome,start,finish FROM {} ORDER BY id".format(self.table_name)
        locations = databases[self.db].execute_query(sql)
      
        seq_file = os.path.join(folder,"temp.seq")
        out_seq=open(seq_file,"w")
        margin=int(length/2)
        for loc in locations:
            midpoint= int((loc["finish"]-loc["start"])/2)+loc["start"]
            seq= genome.get_sequence(loc["chromosome"],midpoint-margin,midpoint+margin)
            out_seq.write(str(seq)+"\n")
            
        out_seq.close()
        out_file = os.path.join(folder,"scores.txt")
        command = "deepbind {} {} > {}".format(id_file,seq_file,out_file)
        os.system(command)
      
        columns=[]
        model_labels=[]    
        for model in models:
            model_label="{}({})".format(model["name"],model["id"])
            model_labels.append(model_label)
            columns.append({"label":model_label,"datatype":"double","columnGroup":"DeepBind"})
        
        info = self.data["field_information"].get("deepbind")
        if not info:
            info={}
            self.data["field_information"]["deepbind"]=info
            columns[0]["master_group_column"]=True
            
            
        l_to_f=self.add_columns(columns)
        for l in l_to_f:
            info[l]=l_to_f[l]
        self.update()
        
        first=True
        update_list=[]
        rec_id=1
        with open(out_file) as f:
            for line in f:
                if first:
                    first=False
                    continue
                arr=line.strip().split()
                rec= {"id":rec_id}
                for n,label in enumerate(model_labels):
                    rec[l_to_f[label]]=float(arr[n])
                update_list.append(rec)
                rec_id+=1
                    
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        shutil.rmtree(folder)
        
    def cluster_by_fields(self,fields,name,methods=["UMAP"]):
        import numpy,umap
        from sklearn.manifold import TSNE
        for field in fields:
            if not self.fields.get(field):
                return
        sql = "SELECT id,{} FROM {} ORDER BY id".format(",".join(fields),self.table_name)
        results = databases[self.db].execute_query(sql)
        folder= get_temporary_folder()
        data_file = os.path.join(folder,"data.txt")
        o= open(data_file,"w")
      
        for res in results:
            o.write(str(res[fields[0]]))
            for field in fields[1:]:
                o.write("\t"+str(res[field]))
            o.write("\n")
        o.close()
        data= numpy.loadtxt(data_file)
        
        return_info=[]
        
        for method in methods:
            if method=="UMAP":
                reducer=umap.UMAP()
                result = reducer.fit_transform(data)
            elif method=="tSNE":
                result = TSNE(n_components=2).fit_transform(data)
            
            columns=[]
            labels=[]
            for index in range(1,3):
                label = "{}{}_{}".format(method,index,name)
                columns.append({"label":label,"datatype":"double","columnGroup":name})
                labels.append(label)
                
            columns[0]["master_group_column"]=True
            l_to_f = self.add_columns(columns)
            field_order= []
            for label in labels:
                field_order.append(l_to_f[label])
            update_list=[]
            for rid,row in enumerate(result,start=1):
                update_list.append({"id":rid,field_order[0]:float(row[0]),field_order[1]:float(row[1])})
            
            databases[self.db].update_table_with_dicts(update_list,self.table_name)
            self.refresh_data()
            info = self.data["field_information"].get("cluster_by_fields")
            if not info:
                info={}
                self.data["field_information"]["cluster_by_fields"]=info
            
            info[name]=field_order
            self.update()
            return_info.append({"fields":field_order,"labels":labels,"method":method})
        
        return return_info      
                
    
    def add_genes(self,gene_set_id=None):
        '''Updates the view set with an extra column which contains
        all genes in the view
        Args:
            gene_set_id(Optional[int]): The id of the gene set,
                the default will be used if none given.
        '''
        gs = GeneSet(self.db)
        col_name = "Genes("+gs.name+")"
        info = self.add_columns([{"label":col_name,"datatype":"text"}])
        field_name = info[col_name]
        view_to_genes=get_genes_in_view_set(self,gene_set_id,simple=True,unique_only=True)
        update_list=[]
        for vid in view_to_genes:
            update_list.append({"id":vid,field_name:view_to_genes[vid]})
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        gi = self.data["field_information"].get("Genes")
        if not gi:
            gi={}
            self.data["field_information"]["Genes"]=gi
        gi[col_name]=field_name
        self.update()
        
    def add_ts_starts(self,geneset_id=None,overlap_column=False,go_levels=0):
        if self.data["field_information"].get("TSS"):
            self.remove_columns(self.data["field_information"]["TSS"].values())
        bed=os.path.join(self.get_folder(),"loc.bed.gz")
        if not os.path.exists(bed):
            self.create_bed_file()
        gs = GeneSet(self.db,geneset_id)
        ts = os.path.join(gs.get_folder(),"ts.bed.gz")
        command = "bedtools closest -d  -a {} -b {}".format(bed,ts)
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
        columns= [
            {"label":"TSS Distance","datatype":"integer","columnGroup":"Nearest TSS","master_group_column":True},
            {"label":"Gene ID","datatype":"text","columnGroup":"Nearest TSS"},
            {"label":"Gene Name","datatype":"text","columnGroup":"Nearest TSS"}
            ]
        if overlap_column:
            columns.append({"label":"Overlaps TSS","datatype":"text","columnGroup":"Nearest TSS"})
        if go_levels:
            for n in range(1,go_levels+1):
                column = {"label":"GO Level{}".format(n),"datatype":"text","columnGroup":"GO Mol. function"}
                if n==1:
                    column["master_group_column"]=True
                columns.append(column)
                
            
        update_list=[]
        name_to_field=self.add_columns(columns,"TSS")
        d_f=name_to_field["TSS Distance"]
        i_f=name_to_field["Gene ID"]
        n_f=name_to_field["Gene Name"]
        already =set()
        if go_levels:
            op = gzip.open(os.path.join(app.config["DATA_FOLDER"],"rs2go.json.gz"),"rt")
            rg2go = ujson.loads(op.read())
            op.close()
            op=open(os.path.join(app.config["DATA_FOLDER"],"go_mf_map.json"))
            go_map= ujson.loads(op.read())
            op.close()
                              
        for line in iter(process.stdout.readline,b''):
            arr=line.decode().split("\t")
            loc_id= int(arr[3])
            if (loc_id in already):
                continue
            already.add(loc_id)
            sign=1
            diff = int(arr[1])-int(arr[5])
            if arr[9]=="+": 
                if diff<0:
                    sign=-1
            else:
                if diff>0:
                    sign=-1
                    
                
            rec= {"id":loc_id,d_f:int(arr[10])*sign,i_f:arr[7],n_f:arr[8]}
            if overlap_column:             
                if rec[d_f]==0:
                    rec[name_to_field["Overlaps TSS"]]="TRUE"
                else:
                    rec[name_to_field["Overlaps TSS"]]="FALSE"
            if go_levels:
                li = rg2go.get(arr[7],[])
                if li:
                    for n in range(1,go_levels+1):
                        if n<=len(li):
                            rec[name_to_field["GO Level{}".format(n)]]=go_map.get(li[n-1])["name"]
                        
                        
                    
            update_list.append(rec)
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        return {"columns":name_to_field,"data":update_list}
    
    def get_tss_data(self):
        columns=[]
        data=[]
        fields = self.data["field_information"]["TSS"]
        sql = "SELECT id,{} from {}".format(",".join(fields.values()),self.table_name) 
        data = databases[self.db].execute_query(sql)
        for field in fields.values():
            col =self.fields[field]
            col["filterable"]=True
            col["sortable"]=True
            col["name"]=col["label"]
            col["field"]=field
            col["id"]=field
            columns.append(col)
        graphs = [{
            "type":"bar_chart",
            "param":fields["TSS Distance"],
            "title":"Distance From TSS",
            "bin_number":50,
            "location":{
                "x":0,
                "y":0,
                "height":4,
                "width":5
            },
            "id":"_tss_chart"
            
            
        }]
        return{
            "columns":columns,
            "data":data,
            "graphs":graphs
        }
        
    
    def get_annotation_data(self,ids):
        from app.ngs.project import get_project
        columns=[]
        fields=[]
        tracks=[]
        wigs=[]
        for aid in ids:
            i =self.data["annotation_information"][str(aid)]
            columns.append({
                "name":i["label"],
                "field":i["field"],
                "datatype":"text",
                "id":"annotation_{}".format(aid),
                "filterable":True,
                "sortable":True
            })
            tracks.append({
                "url":"/tracks/projects/{}/anno_{}.bed.gz".format(aid,aid),
                "short_label":i["label"],
                "featureHeight":12,
                "height":15,
                "color":"#5F9EA0",
                "track_id":"annotation_{}".format(aid),
                "allow_user_remove":True,
                "displayMode":"SQUISHED",
                "decode_function":"generic"
                
            })
            fields.append(i["field"])
            if i.get("type") and i["type"]!="annotation_set":
                p=get_project(aid)
                wig = p.get_main_wig_track()
                if wig:
                    wigs.append(wig)
        sql= "SELECT id,{} FROM {}".format(",".join(fields),self.table_name)
        res= databases[self.db].execute_query(sql)
        return {
            "columns":columns,
            "data":res,
            "tracks":tracks,
            "wigs":wigs
        }
            
              
  
    def add_annotations_intersect(self,ids):
        sql= "SELECT id,type,name,data->>'bed_file' AS bed FROM projects WHERE id = ANY(%s)"
        results =databases['system'].execute_query(sql,(ids,))
        files=[]
        columns=[]
        order_to_field={}
        for row in results:
            files.append(row['bed'])
            columns.append({"label":row['name'],"datatype":"text","columnGroup":"Annotations"})
        name_to_field=self.add_columns(columns,"Annotations")
        
        annotation_information=self.data.get("annotation_information")
        if not annotation_information:
            annotation_information={}
            self.data["annotation_information"]=annotation_information
        
        for index,row in enumerate(results,start=1):
            #delete prevoius column
            field = annotation_information.get(str(row['id']))
            if field:
                self.remove_columns([field["field"]])
            order_to_field[str(index)]=name_to_field[row['name']]
            annotation_information[row['id']]={
                "label":row["name"],
                "field":name_to_field[row['name']],
                "type":row["type"]
                
            }
        self.update()
        bed=self.get_bed_file()
        command = "bedtools intersect -wa -wb -a {} -b {}".format(bed," ".join(files))
        update_dict={}
        process = subprocess.Popen(command, stdout=subprocess.PIPE,shell=True)
        is_single = len(ids)==1
        for line in iter(process.stdout.readline,b''):
            arr=line.decode().strip().split("\t")
            loc_id= int(arr[3])
            if is_single:
                field =order_to_field["1"]
            else:
                field = order_to_field[arr[4]] 
            update_list=update_dict.get(loc_id)
            if not update_list:
                update_list=[]
                update_dict[loc_id]=update_list
            update_list.append(field)
            
        update_list=[]
        for loc_id in update_dict:
            di = {"id":loc_id}
            for field in update_dict[loc_id]:
                di[field]="TRUE"
            update_list.append(di)
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        for name in name_to_field:
            field=name_to_field[name]
            sql = "UPDATE {} SET {}='FALSE' WHERE {} IS NULL".format(self.table_name,field,field)
            databases[self.db].execute_update(sql)
       
            
    def clone(self,ids,name="",description=""):
        if not description:
            description = "Created from view set {}".format(self.id)
        table_name = create_table(name,[],self.db,owner=self.owner,description=description)
        new_id = int(table_name.split("_")[2])
        cols=[]
        for k,v in self.fields.items():
            cols.append({"name":k,"datatype":v["datatype"]})
        databases[self.db].add_columns(table_name,cols)
        sql = "UPDATE view_sets SET fields=%s WHERE id = %s"
        databases[self.db].execute_update(sql,(ujson.dumps(self.fields),new_id))
        sql= "SELECT * FROM {} WHERE id = ANY(%s)".format(self.table_name)
        records =databases[self.db].execute_query(sql,(ids,))
        for rec in records:
            del rec['id']
        databases[self.db].insert_dicts_into_table(records,table_name)
        vs = ViewSet(self.db,new_id)
        old_images = self.get_folder("thumbnails")
        new_images= vs.get_folder("thumbnails")
        li = os.listdir(old_images)
        if len(li)>0:
            for vid in ids:
                im_name= "tn{}.png".format(vid)
                im1= os.path.join(old_images,im_name)
                im2= os.path.join(new_images,im_name)
                shutil.copyfile(im1, im2)
            
        info = self.data.get("field_information")
        if info:
            vs.data["field_information"]=info
            vs.update()
        return vs
        
            
    def create_compound_column(self,columns,operator,name):
        for col in columns:
            if not self.fields.get(col):
                raise Exception("{} column not recognised".format(col))
        cols = ",".join(columns)
        sql = "SELECT id,{} from {}".format(cols,self.table_name)
        res =databases[self.db].execute_query(sql)
        new_col=[{"label":name,"datatype":"double"}]
        l_to_f=self.add_columns(new_col)
        field = l_to_f[name]
        update_list=[]
        update_list2=[]
        for r in res:
            v1= r[columns[0]]
            v2= r[columns[1]]
            if operator =="/":
                if v2 ==0:
                    v2=0.01
                res= v1/v2
            elif operator=="*":
                res=v1*v2
            elif operator=="-":
                res=v1-v2
            else:
                res=v1+v2
            
            update_list.append({"id":r["id"],field:res})
            update_list2.append({"id":r["id"],field:res})
                
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        
     
     
        return{
            "columns":[{
                "name":name,
                "field":field,
                "id":field,
                "datatype":"double",
                "filterable":True,
                "sortable":True
            }],
            "data":update_list2,
            "graphs":[{
                "type":"bar_chart",
                "param":field,
                "title":name
                
            }]
        }
            
            
        
        
         
    def add_annotations(self,ids):
        from app.ngs.annotation import get_annotations_in_view_set
        '''Updates the view set with extra columns for each annotation
        Each column will contain True or False depending on whether 
        the view region contains the annotation
        
        Args:
            ids: A list of annotation set ids
        
        '''
        #get the names
        id_to_name={}
        columns=[]
        results =databases[self.db].execute_query("SELECT id,name FROM annotation_sets WHERE id = ANY (%s)",(ids,))
        for res in results:
            id_to_name[res['id']]=res['name']
            columns.append({"label":res['name'],"datatype":"text","default":"False"})
            
        #add the columns
        name_to_field=self.add_columns(columns,"Annotations")
           
        
        #mapping of annotation_set id to field name in view set
        asid_to_field={}
        for asid in id_to_name:
            name = id_to_name[asid]
            asid_to_field[asid] = name_to_field[name]
              
        #get the annotations
        annots = get_annotations_in_view_set(self,ids,simple=True)
        update_list = []
        for vsid in annots:
            entry = {"id":vsid}
            for field in name_to_field.values():
                entry[field]="False"
            ls = annots[vsid]
            for item in ls:
                field = asid_to_field[item['annotation_set_id']]
                entry[field]="True"
            update_list.append(entry)
        #update the database  
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        
        anno= self.data.get('annotation_sets')
        
        if not anno:
            anno=ids
            self.data['annotation_sets']=anno
        else:
            self.data['annotation_sets']=self.data['annotation_sets']+anno
        self.update()
    
    
    def create_zegami_file(self,folder=None,name="data.tsv"):
        '''Creates a tab delimited text file suitiable for uploading
        to zegami
        
        Args:
            folder (Optional(str): The folder to write the text file to
                If none is specified then the folder will be zegami in the
                ViewSet's default folder
            name (Optional[str]): The name of the files (default is data.tsv)
        
        Returns:
            The full name of the file
        '''
        data = self.get_all_views()
        if not folder:
            folder = self.get_folder("zegami")
        out_file = os.path.join(folder,name)
        out = open(out_file,"w")
        out.write("id\tchromosome\tstart\tend\tImage Name")
        field_list=[]
        for key in self.fields:
            field_list.append({"field":key,"label":self.fields[key]["label"]})
        field_list = sorted(field_list,key = lambda x:x["label"])
        
    
        for item in field_list:     
            out.write("\t"+item["label"])
        
        out.write("\n")
        for item in data:
            out.write(str(item['id'])+"\t")
            out.write(item['chromosome']+"\t"+str(item['start'])+"\t"+str(item['finish'])+"\t")
            out.write("tn"+str(item['id'])+".png")
            for  field in field_list:
                i = item.get(field["field"],"")
                if i == None:
                    i=""
                out.write("\t"+str(i))
            out.write("\n")
        out.close()
        return out_file
    
    
    def create_atomic_set(self,set_name,label):
        zeg_id=os.path.split(self.data['zegami_url'])[1]
        set_file=self._create_zegami_set_file(set_name,label)
        return create_new_set(zeg_id,set_file,label)
                    
        
    def _create_zegami_set_file(self,set_name,label):
        folder= self.get_folder("zegami")
        json_file=open(os.path.join(folder,"data_{}.json".format(set_name)))
        mapping=ujson.loads(json_file.read())
        s= set()
        for i in mapping:
            s.add(mapping[i])
        zeg_file = os.path.join(folder,"data.tsv")
        set_file= os.path.join(folder,"data_for_"+set_name+".tsv")
        output_file = open(set_file,"w")
        first=True
        count=1
        written=0
        column_indexes=[];
        with open(zeg_file) as f:
            for line in f:
                if first:
                    arr = line.strip("\n").split("\t")
                    header_line=[]
                    for index,header in enumerate(arr):
                        if index<16:
                            column_indexes.append(index)
                            header_line.append(header)
                            continue
                        if header.startswith(label+"_"):
                            column_indexes.append(index)
                            header_line.append(header.replace("_"," "))
                    output_file.write("\t".join(header_line)+"\n")
                           
                    first= False
                    continue
                if count in s:
                    arr = line.strip("\n").split("\t")
                    line_to_write=[]
                    for index in column_indexes:
                        line_to_write.append(arr[index])
                    output_file.write("\t".join(line_to_write)+"\n")
                count+=1
        output_file.close()
        return set_file
        
    def get_data_for_set(self,set):
        info =self.data['field_information']['sets'][set]
        fields=[]
        for name in info:
            if name.endswith("_score"):
                fields.append(info[name])
                continue
            if name.endswith("_tags"):
                fields.append(info[name])
                continue
        sql = "SELECT id,{} FROM {}".format(",".join(fields),self.table_name)
        if set != "original":
            sql+=" WHERE {} = 'True'".format(info['is_set'])
        res= databases[self.db].execute_query(sql)
        id_to_rec={}
        for r in res:
            
            id_to_rec[r['id']]=r
            del r['id']
        return {"data":id_to_rec,"fields":info}    
                
                
    def create_grid_cluster(self,field1,field2,name,scale=[1,1]):
        from app.rasterfairy import rasterfairy
        import numpy as np
        sql= "SELECT id, {} AS f1,{} AS f2 FROM {}".format(field1,field2,self.table_name)
        res = databases[self.db].execute_query(sql)
        arr=[]
        for r in res:
            arr.append([r["f1"],r["f2"]])
        
         
         
        grid_xy= rasterfairy.transformPointCloud2D(np.array(arr))
        columns= [
            {"label":name+"_1","datatype":"integer"},
            {"label":name+"_2","datatype":"integer"}
        ]
        lab_to_names= self.add_columns(columns)
        nf1=  lab_to_names[name+"_1"]
        nf2 = lab_to_names[name+"_2"]
        for count,val in enumerate(grid_xy[0]):
            rec = res[count]
            del rec['f1']
            del rec['f2']
            rec[nf1]=val[0]
            rec[nf2]=val[1]
        databases[self.db].update_table_with_dicts(res,self.table_name)
           
        
        
            
    
    def create_new_tag_set(self,tag,parent,name):
        folder= self.get_folder("zegami")
        bed_location=os.path.join(folder,"data_{}.bed".format(name))
        info =self.data['field_information']['sets'][parent]
        
        field= info[parent+"_tags"]
        
        
        if tag == "all":
            if parent != "original":
                is_parent = info['is_set']
                sql = "SELECT id,chromosome,start,finish FROM {} WHERE {}='True' ORDER BY id".format(self.table_name,is_parent)
            else:
                 sql = "SELECT id,chromosome,start,finish FROM {} ORDER BY id".format(self.table_name)
            var =None
        else:
            sql = "SELECT id,chromosome,start,finish FROM {} WHERE {}=%s ORDER BY id".format(self.table_name,field)
            var = (tag,)
        results = databases[self.db].execute_query(sql,var)
        
        columns=[{"label":name,"datatype":"text"}]
        label_to_field=self.add_columns(columns)
        new_field= label_to_field[name]
        self.data['field_information']['sets'][name]={"is_set":new_field}
        self.update()
        bed_file=open(bed_location,"w")
        count=0
        bed_to_id={}
        update_list=[]
        for r in results:
            update_list.append({"id":r['id'],new_field:"True"})
            bed_file.write("{}\t{}\t{}\n".format(r['chromosome'],r['start'],r['finish']))
            bed_to_id[count]=r['id']
            count+=1
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        bed_file.close()
        json_file=open(os.path.join(folder,"data_{}.json".format(name)),"w")
        json_file.write(ujson.dumps(bed_to_id))
        json_file.close()
        return count,bed_location
    
    
    
    
    def add_tags_to_set(self,set_name,label,tags=None,zegami_url=None,p=None):
        '''Adds tags to the viewset -
        
        Args:
            set_name(str): The name of the set (original 
            label (str): The set label
            tags(dict): tag id to the tag value - if none tags will be imported from zegami
            zegami_url(string) - If not supplied 
            p (object): The project    
        Returns:
           The dictionary of tags

        '''
        zeg_id=None
        if set_name=="original":
            zeg_id=self.data["zegami_id"]
        elif zegami_url:
            zeg_id=os.path.split(zegami_url)[1]
        mapping = None
        if not tags:
            #get zegami tags
            tags = get_tags(zeg_id)
            #get all ids in the set
            sql = "SELECT id from {}".format(self.table_name)
            if set_name != "original":
                mapping= self._get_zegami_set_mapping(set_name)
                sql += " WHERE {} = 'True'".format(self.data['field_information']['sets'][set_name]["is_set"])
            res= databases[self.db].execute_query(sql)
            new_tags={}
            #convert the tags to proper ids
            for vid in tags['tags']:
                if mapping:
                    rid=int(mapping[vid])
                else:
                    rid=int(vid)+1
                new_tags[rid]=",".join(tags['tags'][vid])
            #any ids not present will be assigned untagged
            for r in res:
                tag=new_tags.get(r['id'])
                if not tag:
                    new_tags[r['id']]="untagged"
            tags=new_tags
                    
        #does the field exist
        field= self.data['field_information']['sets'][set_name].get(set_name+"_tags")
        if not field:  
            lab_to_field=self.add_columns([{"label":set_name+"_tags","datatype":"text"}])
            field= lab_to_field[set_name+"_tags"]
            self.data['field_information']['sets'][set_name][set_name+"_tags"]=field
        update_list=[]
        tag_dict={}
        for vid in tags:
            tag= tags[vid]
            tag_num=tag_dict.get(tag)
            if not tag_num:
                tag_dict[tag]=1
            else:
                tag_dict[tag]+=1
            update_list.append({"id":vid,field:tag})
        databases[self.db].update_table_with_dicts(update_list,self.table_name)
        self.update()
        #synch main zegami collection
        if zeg_id:
            self.synch_with_zegami(p)
        #Also update the set
        if set_name != "original":
            set_file= self._create_zegami_set_file(set_name,label)
            update_collection(zeg_id,set_file)
        return tag_dict
    
    
    
    def _get_zegami_set_mapping(self,set_name):
        folder=self.get_folder("zegami")
        file_name=os.path.join(folder,"data_{}.json".format(set_name))
        return ujson.loads(open(file_name).read())
              
    
        
                       
                    
    def synch_with_zegami(self):            
        file_name = self.create_zegami_file(name="data.tsv")
        zeg_id=self.data["zegami_id"]
        update_collection(zeg_id,file_name)        
        
    
    def update_zegami_file(self,set):
        '''Updates the zegami file with any tags that the user has added
        tags are 1 less than the id'''
        set_name = set['name']
        tag_col=self.data['field_information']['sets'][set_name][set_name+"_tags"]
       
           
        sql = "SELECT id,chromosome AS chr ,start,finish,{} as tags FROM {}".format(tag_col,self.table_name)
        if set_name != "original":
            is_set=self.data['field_information']['sets'][set_name]['is_set']
            sql += " WHERE {} = 'True'".format(is_set)
        sql += " ORDER BY id"
        results = databases[self.db].execute_query(sql)
        folder =self.get_folder("zegami")
        out_name = os.path.join(folder,set_name+"_data_tags.tsv")
        out_file=open(out_name,"w")
        out_file.write("id\tchromosome\tstart\tend\tTags\n")
        for r in results:
            if r['tags']=="untagged":
                r['tags']=""
            out_file.write("{}\t{}\t{}\t{}\t{}\n".format(r['id'],r['chr'],r['start'],r['finish'],r['tags']))
        out_file.close()
        
        return out_name
    
    def get_zegami_tag_number(self,zeg_id=None):
        '''Gets the number of (and type) of tags from zegami'''
        if not zeg_id:
            zeg_id = self.data.get("zegami_id")
        if not zeg_id:
            return None
        tags = get_tags(zeg_id)
        ret_data={}
        for tag in tags:
            u= tag["tag"]
            info=ret_data.get(u)
            if not info:
                ret_data[u]=1
            else:
                ret_data[u]+=1
            
        return ret_data
    
    def get_zegami_tags(self):
        tags= get_tags(self.data["zegami_id"])
        ids=[]
        id_to_tag={}
        for tag in tags:
            id =int(tag["key"])+1
            id_to_tag[id]=tag["tag"]
        sql = "SELECT id,chromosome,start,finish FROM {}".format(self.table_name)
        results = databases[self.db].execute_query(sql)
        for res in results:
            tag = id_to_tag.get(res[id])
            if not tag:
                tag=""
            res["tag"]=tag
        return results
             
    
    def create_zegami_collection(self,desc="",job=None,project=None,name=None,credentials=None):
        from app.zegami.zegamiupload import create_collection
        if not name:
            name= self.name
        tsv_file = self.create_zegami_file()
        desc= self.description+"\n"+desc
        url,zeg_id = create_collection(name,desc,tsv_file,"Image Name",
                                job=job,project=project,credentials=credentials)
        self.set_data("zegami_id",zeg_id)
        return url
    
    def upload_images_to_zegami(self,job=None,project=None,from_count=0,credentials=None):
        from app.zegami.zegamiupload import upload_images
        image_dir= self.get_folder("thumbnails")
        zeg_id=self.data["zegami_id"]
        upload_images(image_dir,zeg_id,job=job,project=project,from_count=from_count,credentials=credentials)
          

      
    def add_columns(self,columns,field_set=None):
        '''Adds (empty) columns to view set
        
        Args:
            columns: an array of column dictionaries which contain datatype (text,integer or double)
                and label
            field_set (:obj:`str`,optional): If supplied then information will be added to the correct set    
        Returns:
            A dictionary of column label to the column name in the table e.g. :obj:`{"my column 1":"field22",...}`
        Raises:
            ValueError if the columns argument is incorrect
        '''
        #whats the largest column number
        max=0
        for name in self.fields:
            num = int(name[5:])
            if num>max:
                max=num
        max+=1
        label_to_name={}
        update_cols={}
        #make the names of the columns
        for col in columns:
            if not col.get("label") or not col.get("datatype"):
                raise ValueError("column does not contain label or datatype")
            name = "field"+str(max)
            max+=1
            self.fields[name]=col
            update_cols[name]=col
            label_to_name[col['label']]=name
            #add name for the database add_columns methodfd
            col['name']=name
        #update the column names in the summary tablp.remove_columns(["field16"])e and add the actual columns
        #to the view set table
        sql = "UPDATE view_sets SET fields = fields::jsonb || %s  WHERE id=%s"
        databases[self.db].execute_update(sql,(ujson.dumps(update_cols),self.id))
        databases[self.db].add_columns(self.table_name,columns)
        if field_set:
            anno_fields=self.data['field_information'].get(field_set)
            if not anno_fields:
                anno_fields={}
                self.data['field_information'][field_set]=anno_fields
            for label in label_to_name:
                anno_fields[label]=label_to_name[label]
            self.update()    
        return label_to_name
    
    
    def remove_columns(self,column_names,are_labels=False):
        '''Removes the supplied columns, and all data they contain
        from the ViewSet
        Args:
            column_names(list[str]) The a list of the column (field) names
                e.g ["field1","field2"] or the field labels (in which case, are_labels
                should be True
            are_labels(boolean) Default is False. If True the the supplied list
                contains the column labels, not names (fields)     
        '''
        fields_to_delete=[]
        if are_labels:
            for name in self.fields:
                if self.fields[name] in column_names:
                    fields_to_delete.append(name)
                    del self.fields[name]
        else:
            for name in column_names:
                if self.fields.get(name):
                    fields_to_delete.append(name)
                    del self.fields[name]
        sql = "UPDATE view_sets SET fields = fields::jsonb {} WHERE id = {}"
        vars= ()
        tf=""         
        for field in fields_to_delete:
            tf+=" -%s"
            vars = vars + (field,)
        sql = sql.format(tf,self.id)  
       
        databases[self.db].execute_update(sql,vars)
        databases[self.db].remove_columns(self.table_name,fields_to_delete)
               
    def get_label_to_field(self):
        lab_to_field={
            "chromosome":"chromosome",
            "start":"start",
            "end":"finish"
        }
        for field in self.fields:
            lab_to_field[self.fields[field]["label"]]=field
        return lab_to_field
        
    def get_all_views(self,location_only=False,specific_views=None,filters= None):
        '''Get all the views as a list of dictionaries orderd
        by id (ascending)
        Args:
            location_only (Optional[boolean]): Default is False -
                if True then only id,start,finish and chromosome will be
                returned 
            specific_views (Optional[list]): If given then only those in 
                the list will be given
                
        Returns:
            A list of dictionaries containing key (column name) to 
            value 
        '''
        vars=None
     
        select="*"
        if location_only:
            select = "id,chromosome,start,finish"
        sql = "SELECT {} FROM {}".format(select,self.table_name)
        if specific_views:
            sv= ",".join(list(map(str,specific_views)))
            specific_views =" WHERE id IN({sv})".format(sv=sv)
            sql+= specific_views
       
        if filters:
            where,vars= get_where_clause(filters,self.get_label_to_field())
            sql+=where
            
            
                
                         
            
        sql+=" ORDER BY id"
        return databases[self.db].execute_query(sql,vars)
    
    def get_views(self,chromosome,start,finish):
        sql = "SELECT * FROM {} WHERE chromosome=%s AND finish>%s AND start<%s".format(self.table_name)
        return databases[self.db].execute_query(sql,(chromosome,start,finish))
        
    def get_folder(self,subfolder=None):
        '''Get the folder associated with this project. One will be created if it
        does not exist.
        Args:
            subfolder(str): 
        
        '''
        folder = os.path.join(app.config['DATA_FOLDER'],self.db,"view_sets",str(self.id))
        if subfolder:
            folder=os.path.join(folder,subfolder)
        if not os.path.exists(folder):
            os.makedirs(folder)
        return folder
    
    def get_url(self,external=False):
        url = "/"+self.db+"/view_set/"+str(self.id)
        if external:
            url="http://"+app.config['HOST_NAME']+url
        return url
        
    
    def get_view_number(self):
        sql = "SELECT count(*) FROM {}".format(self.table_name)
        return databases[self.db].execute_query(sql)[0]
    
    def get_data_simple(self,filters=None):
        tracks=None
        views=self.get_all_views(filters=filters)
        if self.data.get("track_config"):
            tracks = self.data.get("track_config")
        else:
            tracks=self.data.get("tracks")
            if not tracks and self.data["primary_track"].get("short_label"):
                tracks={}
                tracks[self.data['primary_track']['short_label']]=self.data['primary_track']
                for track in self.data['secondary_tracks']:
                    tracks[track['short_label']]=track
            if tracks:
                for track in list(tracks.values()):
                    track['url']=get_track_proxy(track['url'])

        return {
            "view_data":views,
            "tracks":tracks,
            "fields":self.fields,
            "data":self.data    
    }
        
    
        
        
    def get_filtered_data(self,filters):
       
        allowed_fields={}
        for field in self.fields:
            allowed_fields[field]=field
        allowed_fields["chromosome"]="chromosome"
        where_clause,vars= get_where_clause(filters,allowed_fields)
            
        sql = "SELECT chromosome, start, finish,id FROM {} {} ORDER BY start".format(self.table_name,where_clause)
        res = databases[self.db].execute_query(sql,vars)
        return res
        
    
    def get_data_for_table(self):
        from app.ngs.annotation import get_all_annotation_sets
        views=self.get_all_views()
        primary_track_ids=set()
        
        for view in views:
            primary_track_ids.add(view['track_id'])
        secondary_tracks = self.data.get("secondary_tracks",[])
        track_to_color={}
        track_ids=list(primary_track_ids)
        for item in secondary_tracks:  
            track_ids.append(item['id'])
            track_to_color[item['id']]=item['color']
        tracks=databases[self.db].get_tracks(track_ids,"id")
        #replace with custom colors or use default
        primary_track_color=None
        pt= self.data.get("primary_track")
        
        if pt:
            primary_track_color=pt.get("color")
            
        for track in tracks:
            if track['id'] in primary_track_ids:
               if primary_track_color:
                   track['color']=primary_track_color
            else:
                cc =track_to_color.get(track['id'],track["color"])
                track['color']=cc
        #info about annotation sets used
        annotation_data= get_all_annotation_sets(self.db,self.data.get("annotation_sets"))
        
        return {
            "view_data":views,
            "tracks":tracks,
            "fields":self.fields,
            "data":self.data,
            "annotation_data":annotation_data
            
        }
    
    def update_fields(self):
        sql = "UPDATE view_sets SET fields=%s WHERE id=%s "
        vars=(ujson.dumps(self.fields),self.id)
        databases[self.db].execute_update(sql,vars)
       
    def update(self):
        '''Updates the 'data' dictionary of the view set i.e.
         writes it to the database
        '''
        sql= "UPDATE view_sets SET data=%s WHERE id = %s"
        vars= (json.dumps(self.data),self.id)
        databases[self.db].execute_update(sql,vars)
        
    def update_column_metadata(self):
        '''Updates the 'data' dictionary of the view set i.e.
         writes it to the database
        Args:
            subfolder(str): 
        '''
        sql= "UPDATE view_sets SET fields=%s WHERE id = %s"
        vars= (json.dumps(self.fields),self.id)
        databases[self.db].execute_update(sql,vars)
        
    
    def set_data(self,param,value):
        '''Updates the 'data' dictionary of the view set in
           the database.
        Args:
            param(str): The name of paramater (dictionary key)
            value: the parameter's value
            
        '''
        sql = "SELECT data from view_sets WHERE id = %s"
        results = databases[self.db].execute_query(sql,(self.id,))
        data = results[0]['data']
        data[param]=value
        
        sql= "UPDATE view_sets SET data=%s WHERE id = %s"
        vars= (json.dumps(data),self.id)
        databases[self.db].execute_update(sql,vars)
        self.data=data
        
    def refresh_data(self):
        sql = "SELECT data from view_sets WHERE id = %s"
        results = databases[self.db].execute_query(sql,(self.id,))
        data = results[0]['data']
        self.data=data
        
     
    def get_bed_file(self):
        bed_file=os.path.join(self.get_folder(),"loc.bed.gz")
        if not os.path.exists(bed_file):
            self.create_bed_file()
        return bed_file
    
    def create_bed_file(self,chunksize=50000):
        '''Creates a 4 column gzipped file (the fourth column being
        the id of the entry. The file is called loc.bed.gz in the
        default viewset folder.Also creates a tabix index in the same
        folder   
        '''
        
        folder =self.get_folder()
        file_loc=os.path.join(folder,"loc.bed")
        out_file=open(file_loc,"w")
        offset=0
        num =self.get_view_number()
        while offset<=num["count"]:
            sql = "SELECT id,chromosome AS c,start AS s,finish AS f FROM {} ORDER BY chromosome,start,finish OFFSET {} LIMIT {}".format(self.table_name,offset,chunksize)
            rows = databases[self.db].execute_query(sql)
            for row in rows:
                out_file.write("{}\t{}\t{}\t{}\n".format(row["c"],row['s'],row['f'],row['id']))
            offset+=chunksize
        out_file.close()
        print("creating tabix")
        os.system("bgzip {}".format(file_loc))
        os.system("tabix -p bed {}".format(file_loc+".gz"))
        if (not os.path.exists(file_loc+".gz")):
            print ("tabix not created")
        return file_loc+".gz"
    
    
    
    def create_basic_bed_file(self,without_ids=False,selected_ids=None,
                              chunksize=400000,order_by_ids=False,fields=None):
        '''creates a basic bed file (ordered by chromosome,start,finish)
        Args:
            without_ids(Optional[bool]): Default is false, if True,
                then only 3 columns will be written
            selected_ids(Optional[list]: a list of ids to include in the bed file
        '''
        where_clause=""
        vars=None
        if selected_ids:
            where_clause= "WHERE id=ANY(%s)"
            vars=(selected_ids,)
        
        offset=0    
        num =self.get_view_number()
        folder =self.get_folder()
        file_loc=os.path.join(folder,"temp.bed")
        out_file=open(file_loc,"w")
        order_by= "id" #"chromosome COLLATE {} ,start,finish".format('"C"')
        if order_by_ids:
            order_by = "id"
        f_select=""
        if fields:
            f_select=","+",".join(fields)
        while offset<=num["count"]:
            sql = "SELECT id,chromosome AS c,start AS s,finish AS f{} FROM {} {} ORDER BY {} OFFSET {} LIMIT {}"\
                .format(f_select,self.table_name,where_clause,order_by,offset,chunksize)
            rows = databases[self.db].execute_query(sql,vars)
            for row in rows:
                if without_ids:
                    out_file.write("{}\t{}\t{}".format(row["c"],row['s'],row['f']))
                else:   
                    out_file.write("{}\t{}\t{}\t{}".format(row["c"],row['s'],row['f'],row['id']))
                if fields:
                    f_arr=[]
                    for field in fields:
                        f_arr.append(str(row[field]))
                    out_file.write("\t"+"\t".join(f_arr))
                out_file.write("\n")
            offset+=chunksize
        out_file.close()
        new_file = os.path.join(folder,"loc.bed")
        
        if order_by_ids:
            os.system("mv {} {}".format(file_loc,new_file))
        else:
            os.environ["LC_COLLATE"]="C"
            os.system ("sort -k1,1 -k2,2n {} > {}".format(file_loc,new_file))
            os.remove(file_loc)
        return new_file
        
       
    def delete(self,hard = False):
        '''Deletes the View Set
        Args:
            hard(Optional[bool]): Default is false, whereby the
               viewset is only tagged which hides it from view
               If true, then the set will be completety deleted
               along with all associated files 
        '''
        sql = "UPDATE view_sets SET is_deleted=TRUE WHERE id=%s"
        databases[self.db].execute_update(sql,(self.id,))
        if not hard:
            return
        #delete all files
        folder = self.get_folder()
        shutil.rmtree(folder)
        #delete entry
        databases[self.db].delete_by_id("view_sets",[self.id])
        #delete table
        databases[self.db].delete_table(self.table_name)
        
        zid=self.data.get("zegami_id")
        if zid:
            delete_collection(zid)
        


def _determine_fields(file_name):
    extra_fields={}
    offset=3
    track_id_position=0
    with open(file_name) as csvfile:
        reader = csv.reader(csvfile,delimiter="\t")
        for row in reader:
            if reader.line_num==1:
                for n,header in enumerate(row[offset:],start=1):
                    if header=="track_id":
                        track_id_position=n
                        continue
                    extra_fields[n]={"name":"field"+str(n),"label":header,"datatype":"integer","order":n,"parser":int}
                continue
            for n,value in enumerate(row[offset:],start=1):
                if n==track_id_position:
                    continue
                if extra_fields[n]['datatype']=='text':
                    continue
                try:
                    int(value)
                except:
                    try:
                        float(value)
                        extra_fields[n]['datatype']="double precision"
                        extra_fields[n]['parser']=float
                    except:
                        extra_fields[n]['datatype']="text"
                        extra_fields[n]['parser']=str
                        
            if reader.line_num==10:
                break
   
    return extra_fields,track_id_position
   
    

def _create_location_index(table_name,db):
    file_name = os.path.join(app.root_path, 'databases', 'create_location_index.sql')
    script = open(file_name).read().format(table_name=table_name)
    databases[db].run_script(script)


def get_all_sets(genome):
    sql = "SELECT id,name,description,date_added FROM view_sets WHERE is_deleted=FALSE"
    results = databases[genome].execute_query(sql)
    for item in results:
        item['date_added']=item['date_added'].strftime("%m/%d/%Y")
    return results

def get_all_default_sets():
    all_sets=[]
    count=1
    for db in databases:
        sql = "SELECT id,name,description,date_added FROM feature_sets WHERE type='default'"
        results = databases[db].execute_query(sql)
        
        for item in results:
            item['genome']=db
            item['date_added']=item['date_added'].strftime("%m/%d/%Y")
            item['gid']=item['id']
            item['id']=count
            count+=1
            all_sets.append(item)
    return all_sets


def parse_extra_fields(fields):
    if len(fields)==3:
        return {}
  
    extra_fields={}
    for field in fields[3:]:
        pos=field['position']-3
        extra_fields[pos]=field
        if field['datatype']=="double":
            field['parser']=float
            field['datatype']="double"
        elif field['datatype']=='text':
            field['parser']=str
        elif field['datatype']=='integer':
            field['parser']=int
        field['order']=pos
        field['label']=field['name']
        field['name']="field"+str(pos)
    return extra_fields
    


def create_view_set_from_file(db,file_name,name,
                              track_name=None,
                              primary_track={},
                              secondary_tracks=None,
                              description="",
                              has_headers=True,
                              parse_headers=True,
                              extra_fields=None,
                              track_id_position=0,
                              annotation_sets=[],
                              delimiter="\t",
                              chromosomes=None,
                              margin=0,
                              owner=0,
                              thumbnail_details=None,
                              no_track_id=False,
                              create_icon=True):
    """
    Creates a view set from the supplied file. If the file contains headers with column
    names, then many parameters can be left as default and column names, datatype etc.
    can be calculated from the file.

    Args:
        db: The database (genome) to which the set will be added
        file_name: The path of the file containing the data.The first three
            columns should be chromosome, start, finish .Can be gzipped
            and does not have to contain headers
        track_name: If the views all have the same primary track then then
            this value should be given here. Default is None
        primary_track: An object containing information about the primary track.
            Default is an empty dictionary
        secondary_tracks: A list of dictionaries {"name":"track1","color":"blue",scale:"fixed","min_y":0,"max_y":1000}
        description: A string describing the view set. Default is an empty string
        has_headers: If true than the the first line of the file will be ignored
        parse_headers: If true (default) and extra_headers are not supplied, then
           extra columns will be calculated from the first line
        extra_fields: A dictionary describing the additional fields (i.e. not chromosome,
           start or end). e.g. {3:{"datatype":"integer","parser":int,"order":1,"name":"field1","label":"score"}}
        track_id_position: The column index (0 based), which contains the track names (if the primary
            track for each view differs)
        annotation_sets: A list of annotation set ids that will be displayed with each view
        delimiter: The delimiter used to separate columns. The default value is tab
        margin: The distance either side of the view that will also be displayed
        owner(Optional[int]): The user id who will own the view set (default 0)
        no_track_id(boolean) If false the track id field will be 0. default true
        
        
    Returns:
        A ViewSet object representing the newly created set

    """
    
    offset=3
    if track_name:
        track_id = databases[db].get_tracks([track_name])[0]['id']
    if not extra_fields and parse_headers:    
        extra_fields,track_id_position= _determine_fields(file_name)
    if not extra_fields:
        extra_fields={}
    fields={}
    
    for item in extra_fields.values():
        new_dict=dict(item)
        del new_dict['parser']
        del new_dict['name']
        fields[item['name']]=new_dict
    data={}
    data['primary_track']=primary_track
    #change secondary tracks from name to id
    if secondary_tracks:
        data["secondary_tracks"]=secondary_tracks
       
    data['annotations_sets']=annotation_sets
    data['field_information']={}
    data['margin']=margin
    data['thumbnail_details']=thumbnail_details      
    table_name = create_table(name,fields,db,owner,data,description)
    features=[]
    if file_name.endswith(".gz"):
        handle = gzip.open(file_name,"rt")
    else:
        handle =open(file_name)
   
  
    line_num=1
    with handle as csvfile:
        reader = csv.reader(csvfile,delimiter=delimiter) 
        for row in reader:
            if len(row)==0 or row[0].startswith("#"):
                continue
            if line_num==1 and has_headers:
                line_num+=1
                continue
            if chromosomes:
                length = chromosomes.get(row[0])
                if not length:
                    continue
                if int(row[2])>length:
                    continue
            line_num+=1
            if not track_name:
                if no_track_id:
                    track_id=1
                else:  
                    track_id = databases[db].get_tracks([row[track_id_position+2]])[0]['id']
            feature= {"track_id":track_id,
                             "chromosome":row[0],
                             "start":int(row[1]),
                             "finish":int(row[2])}
            for n,value in enumerate(row[offset:],start=1):
                #ignore the track id column
                if n==track_id_position:
                    continue
                field = extra_fields.get(n)
                #user doesn't want this field
                if not field:
                    continue
                
                try:
                    feature[field['name']]=field['parser'](value)
                except:
                    pass
                
            features.append(feature)
            if len(features) % 5000 ==0:
                databases[db].insert_dicts_into_table(features,table_name)
                features=[]
    if len(features) != 0:
        databases[db].insert_dicts_into_table(features,table_name)
        
    _create_location_index(table_name,db)
    vs = ViewSet(db,int(table_name.split("_")[2]))
    if create_icon:
        vs.create_icon(height=75,width=200)
    return vs
           
def create_table(name,fields,db,owner=0,data=None,description=""):
    sql = "INSERT INTO view_sets (name,fields,description,owner) VALUES (%s,%s,%s,%s)"
    new_id = databases[db].execute_insert(sql,(name,json.dumps(fields),description,owner))
    table_name = "view_set_"+str(new_id)
    sql = "UPDATE view_sets SET table_name=%s WHERE id=%s"
    databases[db].execute_update(sql,(table_name,new_id))
    if data:
        sql = "UPDATE view_sets SET data=%s WHERE id=%s"
        databases[db].execute_update(sql,(json.dumps(data),new_id))
    extra_columns=[]
    for field in fields:
        dt = fields[field]['datatype']
        if dt == "double":
            dt = "double precision"
        extra_columns.append("{} {}".format(field,dt))
    if len(extra_columns)==0:
        e_c=""
    else:
        e_c=",\n".join(extra_columns)+","
        
    file_name = os.path.join(app.root_path, 'databases', 'create_view_set.sql')
    script = open(file_name).read().format(db_user=app.config['DB_USER'],extra_columns=e_c,table_name=table_name)
    databases[db].run_script(script)
    return table_name      
                        
            

                
       
                
            
                
                
            
            
        
       
          
        
    
