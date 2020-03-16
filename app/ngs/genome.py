from app import databases,app
from app.ngs.gene import create_gene_set_from_remote_file,GeneSet
import os,requests,ujson

def get_genomes(not_other=False):
    sql = "SELECT name,label FROM genomes"
    if not_other:
        sql+=" WHERE name != 'other'"
    return databases["system"].execute_query(sql)



def create_genome(name,label,database="",icon=None,connections=5):
    from app.databases.main_database import _get_db_connection,Database
    if not icon:
        icon ="/static/icons/dna_icon.png"
    sql = "INSERT INTO genomes (name,label,database,small_icon,data,connections) VALUES(%s,%s,%s,%s,%s,%s)"
    databases["system"].execute_insert(sql,(name,label,database,icon,ujson.dumps({}),connections))
    #already has connection (need one to enter gene info)
    already_connection=False
    for n in app.config["GENOME_DATABASES"]:
        if app.config["GENOME_DATABASES"][n]["database"]==database:
            databases[name]=databases[n]
            already_connection=True
            break
    if not already_connection:
        db_conn=_get_db_connection(app,database)
        databases[name]=Database(db_conn,5,app,0)
        
    
    genome_dir = os.path.join(app.config["DATA_FOLDER"],name)
    if not os.path.exists(genome_dir):
        os.mkdir(genome_dir)
    remote_chrom_file= "http://hgdownload.cse.ucsc.edu/goldenPath/{}/bigZips/{}.chrom.sizes".format(name,name)
    resp = requests.head(remote_chrom_file)
    if resp.status_code==200:
        local_chrom_file = os.path.join(genome_dir,"custom.chrom.sizes".format(name))
        os.system("wget -O {} {}".format(local_chrom_file,remote_chrom_file))
        gene_file="http://hgdownload.soe.ucsc.edu/goldenPath/{}/database/refGene.txt.gz".format(name)
        create_gene_set_from_remote_file(name,gene_file,"UCSC RefGene",make_default=True)
        gs = GeneSet(name)
        gs.create_ts_file()
    


def get_chromosome_file(genome):
    return  os.path.join(app.config["DATA_FOLDER"],genome,"custom.chrom.sizes")


class Genome(object):
    def __init__(self,db):
        from pyfaidx import Faidx
        fa = os.path.join(app.config["DATA_FOLDER"],db,db+".fa")
        self.fasta=  Faidx(fa) 
    
    def get_sequence(self,chr,start,end):
        return self.fasta.fetch(chr,start,end)
    
    def destroy(self):
        self.fasta.close()
    
    