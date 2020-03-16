from . import meths
from app import databases
from app.ngs.view import ViewSet,get_all_default_sets
from app.ngs.gene import get_genes
from app.ngs.annotation import get_all_columns,get_all_annotation_sets
import ujson
from flask import request

#If no arguments passed will just get the genes for this region
@meths.route("/<genome>/get_annotations/<chr>/<start>/<end>",methods=['GET',"POST"])
def get_annotations(genome,chr,start,end):
    #work out which features
    start = int(start)
    end = int(end)
    db=databases[genome]
    genes = get_genes(genome,chr,start,end)
    args = request.json
    annotations=None
    if args.get("types"):
        annotations=get_annotations_by_type(genome,args.get("types"),chr,start,end)
    
    return ujson.dumps({"genes":genes,"annotations":annotations})

@meths.route("/get_annotation_set_columns",methods=['GET',"POST"])
def get_track_annotaton_set_columns():
    return ujson.dumps(get_all_columns())

@meths.route("/<genome>/get_annotation_sets",methods=['GET',"POST"])
def get_annotation_sets(genome):
    return ujson.dumps(get_all_annotation_sets(genome))
    

def get_annotations_by_type(genome,types,chr,start,end):
    sql = "SELECT chromosome,start,finish,type,annotations.id AS anno_id,annotation_sets.id AS set_id,annotations.name as name FROM annotations INNER JOIN annotation_sets ON annotation_set_id=annotation_sets.id AND type = ANY(%s) WHERE chromosome=%s AND finish>%s AND start<%s ORDER BY start" 
    annotations=databases[genome].execute_query(sql,(types,chr,start,end))
    return annotations

def get_annotation_sets(genome):
    sql = "SELECT * FROM annotation_sets"
    return databases[genome].execute_query(sql)
    
    