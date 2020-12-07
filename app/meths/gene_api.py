import ujson
from app.ngs.gene import get_genes as get_gene_region
from . import meths
from flask_cors import cross_origin
from app.ngs.genome import get_genomes as get_all_genomes
from app import app

@meths.route("/<db>/get_genes/<chr>/<start>/<finish>")
@cross_origin()
def get_genes(db,chr,start,finish):
    start = int (start)
    end = int(finish)
    return ujson.dumps(get_gene_region(db,chr,start,finish,sorted=True))

@meths.route("/<db>/get_all_annotation_sets")
def get_all_annotation_sets(db):
    return ujson.dumps(get_annotation_sets(db))


@meths.route("/get_genomes")
def get_genomes():
    return ujson.dumps(get_all_genomes())