from app import databases,app
import ujson,os,gzip
import shutil
from app.ngs.utils import get_temporary_folder




class GeneSet(object):
    '''A class representing a gene set
    '''
    def __init__(self,genome,id=None):
        '''
        
        '''
        db=databases[genome]
        if id == None:
            id=1
            sql = "SELECT data->'default_gene_set' AS gs FROM genomes WHERE name=%s"
            res = databases["system"].execute_query(sql,(genome,))
            if res[0]['gs']:
                id = res[0]['gs']
                
        sql = "SELECT * FROM gene_sets WHERE id=%s"
        gs = db.execute_query(sql,(id,))[0]
        self.description =gs['description']
        self.name= gs['name']
        self.id=id
        self.db=genome
        self.data = gs['data']
        
    def get_folder(self,subfolder=None):
        '''Get the folder associated with this project. One will be created if it
        does not exist.
        Args:
            subfolder(str): 
        
        '''
        folder = os.path.join(app.config['DATA_FOLDER'],self.db,"genes",str(self.id))
        if subfolder:
            folder=os.path.join(folder,subfolder)
        if not os.path.exists(folder):
            os.makedirs(folder)
        return folder
        
    def create_ts_file(self):
        sql = "SELECT chrom,tx_start,tx_end,strand,name,name2 FROM {} ORDER BY chrom,tx_start ".format("gene_set_"+str(self.id)) 
        rows = databases[self.db].execute_query(sql)
        folder = self.get_folder()
        file_loc=os.path.join(folder,"ts.bed")
        out_file=open(file_loc,"w")
        for row in rows:
            if row["strand"]=="+":
                start =row["tx_start"]
                end = start+1
            else:
                end = row["tx_end"]
                start=end-1
            out_file.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(
                    row['chrom'],start,end,
                    row['name'],row["name2"],row['strand']
                ))
        out_file.close()
        sorted_bed = os.path.join(folder,"sorted.bed")
        os.system("sort -k1,1 -k2,2n {} > {}".format(file_loc,sorted_bed))
        os.system("rm {}".format(file_loc))
        os.system("mv {} {}".format(sorted_bed,file_loc))
        os.system("bgzip -f {}".format(file_loc))
        os.system("tabix -p bed {}".format(file_loc+".gz"))
        
            
        
        
        
        
        
    

def create_gene_set_from_remote_file(genome,remote_location,name,description="",make_default=False):
     
    f_name= os.path.split(remote_location)[1]
    folder = get_temporary_folder()
    file_name=os.path.join(folder,f_name)
    command = "wget '{}' -O {}".format(remote_location,file_name)
    data={"remote"}
    os.system(command)
    create_gene_set(genome,name,file_name,description,make_default)
    shutil.rmtree(folder)
      

def create_gene_set(genome,name,gene_file,description="",make_default=False):
    db = databases[genome]
    sql = "INSERT INTO gene_sets (name,description) VALUES (%s,%s)"
    new_id=db.execute_insert(sql,(name,description))
    table_name = "gene_set_"+ str(new_id)
    sql = "UPDATE gene_sets SET table_name=%s WHERE id=%s"
    db.execute_update(sql,(table_name,new_id))
    if make_default:
        sql="UPDATE genomes SET data = jsonb_set(data, '{{default_gene_set}}', '{}') WHERE name = %s".format(new_id)
        databases["system"].execute_update(sql,(genome,))
    file_name = os.path.join(app.root_path, 'databases', 'create_gene_set.sql')
    script = open(file_name).read().format(db_user=app.config['DB_USER'],table_name=table_name)
    db.run_script(script)
    data=[]
    if gene_file.endswith(".gz"):
        f=gzip.open(gene_file,mode='rt')
    else:
        f=open(gene_file)
        
    with f:
        for line in f:
            line = line.strip()
            arr = line.split("\t")
            exon_starts=arr[9][:-1].split(",")
            exon_starts=list(map(lambda x:str(x),exon_starts))
            exon_starts=ujson.dumps(exon_starts)
            exon_ends=arr[10][:-1].split(",")
            exon_ends=list(map(lambda x:str(x),exon_ends))
            exon_ends=ujson.dumps(exon_ends)
            exon_frames=arr[15][:-1].split(",")
            exon_frames=list(map(lambda x:str(x),exon_frames))
            exon_frames=ujson.dumps(exon_frames)
            
            row={
                "name":arr[1],
                "chrom":arr[2],
                "strand":arr[3],
                "tx_start":int(arr[4]),
                "tx_end":int(arr[5]),
                "cd_start":int(arr[6]),
                "cd_end":int(arr[7]),
                "exon_count":int(arr[8]),
                "exon_starts":exon_starts,
                "exon_ends":exon_ends,
                "score":int(arr[11]),
                "name2":arr[12],
                "cds_start_stat":arr[13],
                "cds_end_stat":arr[14],
                "exon_frames":exon_frames                 
            }
            data.append(row)
            if len(data) % 5000 ==0:
                db.insert_dicts_into_table(data,table_name)
                data=[]
    if len(data) != 0 :
        db.insert_dicts_into_table(data,table_name)
        
    file_name = os.path.join(app.root_path, 'databases', 'create_gene_index.sql')
    script = open(file_name).read().format(table_name=table_name)
    db.run_script(script)
    
    return new_id
    

def get_genes_in_view_set(view_set,gene_set_id=None,simple=False,
                          unique_only=False,use_tss=False,margin=None,
                          specific_views=None):
    '''Retrieves the genes present in view the set 
        Args:
            genome (str): The genome name
            view_set (int): The ViewSet Object
            gene_set_id (Optional[int]): The gene set to query against.
                If not present, the default gene set will be used
            simple (Optional[boolean]): Default is False. If true, then
                only the gene names will be returned
            use_tt (Optional[booles]): Default is False. If true, then
                the transcription start and stop (instead of the cds)
                will be used to find overlap with the view
            unique_only (Optional[boolean]): Default is False,
                If True only one splice varaint per gene will be returned
            include_margins (Optional[boolean[): If True (default false)
                then genes in the margins will also be reported,
            specific_views(Optional[list]): A list of view ids to retreive
                default is none (all views retreived)
            
        Returns:   
            A list of dictionaries containing id,name,type,date added
            and description for each annotation set       
    '''
    genome = view_set.db
    if not gene_set_id:
        gene_set_id=app.config['GENOME_DATABASES'][genome]['default_gene_set']
    db=databases[genome]
    
    distinct=""
    if unique_only:
        distinct = "DISTINCT ON (vid,name2)"
   
    vs = view_set.table_name
    if simple:
        select= vs+".id as vid,name2,tx_start,tx_end"
    else:
        select = ('cd_start AS "cdStart",cd_end AS "cdEnd",chrom AS chr,tx_start'
                  ' AS start,tx_end AS end,name AS id,name2 AS name,strand'
                  ' ,exon_starts,exon_ends')
        select = vs+".id as vid,"+select
    gs = "gene_set_"+str(gene_set_id)
    
    st_name = "cd_start"
    en_name = "cd_end"
    
    if use_tss:
        st_name= "tx_start"
        en_name = "tx_end"
    
    
    #any margins?
    m_m=""
    p_m=""
    if margin:
        m_m="-"+str(margin)
        p_m="+"+str(margin)
    
    
    sql =("SELECT {distinct} {select} FROM {vs} INNER JOIN {gs}"
          " ON  {vs}.chromosome={gs}.chrom AND"
          " {vs}.finish{p_m} > {gs}.{st_name} AND {vs}.start{m_m} < {gs}.{en_name}")\
          .format(distinct=distinct,select=select,vs =vs,gs=gs,
                  st_name=st_name,en_name=en_name,p_m=p_m,m_m=m_m)
          
    if specific_views:
        sv= ",".join(list(map(str,specific_views)))
        specific_views =" AND {vs}.id IN({sv})".format(vs=vs,sv=sv)
        sql += specific_views
    
    
    sql += " ORDER BY vid,name2, (tx_end-tx_start) DESC"
     
    results = db.execute_query(sql)
    view_to_gene ={}
    if simple:
        for res in results:
            gene =  view_to_gene.get(res['vid'])
            if not gene:
                gene= res['name2']
                view_to_gene[res['vid']]=gene
    
            else:
                view_to_gene[res['vid']]=gene+","+res['name2']
    
    else:
        for res in results:
            _process_gene(res)
            vid = res['vid']
            gene_list =  view_to_gene.get(vid)
            if not gene_list:
                gene_list=[]
                view_to_gene[vid]=gene_list
            gene_list.append(res)
        
        for v in view_to_gene:
            li =view_to_gene[v]
            
    return view_to_gene
        
    
    
def get_genes(genome,chr,start,end,gene_set_id=None,unique_only=False,sorted=False):
    '''Retrieves the genes present in the specified range
    
    Args:
        genome (str): The genome name
        chr (str): The name of the chromosome (e.g. 'chr12')
        strart (int): The start of the range
        end (int) The end of the range
        gene_set_id: (Optional[int]) The id of the geneset.
           If none supplied, the default gene set will be used
        unique_only(Optional[boolean]): If True only one splice variant will
           be returned 
            
    Returns:   
        
    '''
    lookup = app.config["GENOME_DATABASES"][genome].get("ens_to_ucsc")
    is_ens=False
    t_chr=chr
    if lookup:
        t_chr = lookup.get(chr)
        if t_chr:
            is_ens=True
        else:
            t_chr=chr
    if not gene_set_id:
        gene_set_id= app.config["GENOME_DATABASES"][genome]["default_gene_set"]
    db=databases[genome]
    
    distinct=""
    if unique_only:
        distinct = "DISTINCT ON (name2)"
    fields= 'cd_start AS "cdStart",cd_end AS "cdEnd",chrom AS chr,tx_start AS start,tx_end AS end,name AS id,name2 AS name,strand,exon_starts,exon_ends'
    sql = "SELECT {} {} FROM {} WHERE chrom=%s AND tx_end>%s AND tx_start<%s".format(distinct,fields,"gene_set_"+str(gene_set_id))
    if sorted:
        sql+=" ORDER BY tx_start,tx_end"
    genes = db.execute_query(sql,(t_chr,start,end))
    for gene in genes:
        _process_gene(gene,is_ens,chr)
   
  
    return genes
    
def _process_gene(gene,is_ens,chr):
    if is_ens:
        gene["chr"]=chr    
    exons=[]
    for a in range(0,len(gene['exon_starts'])):
        exons.append({"start":gene['exon_starts'][a],"end":gene['exon_ends'][a]})
    gene['exons']=exons
    del gene['exon_starts']
    del gene['exon_ends']