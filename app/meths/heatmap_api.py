import ujson
from . import meths
from app.ngs.heatmap import HeatMap

@meths.route("/<db>/get_heatmap_metadata/<hm_id>")
def get_heatmap_metadata(db,hm_id):
    hm_id = int (hm_id)
    hm = HeatMap(db,hm_id)
    return ujson.dumps(hm.get_metadata())

@meths.route("/<db>/get_heatmap_data/<hm_id>/<chr>/<start>/<end>")
def get_heatmap_data(db,hm_id,chr,start,end):
    hm_id = int(hm_id)
    hm = HeatMap(db,hm_id)
    start=int(start)
    end=int(end)
    return ujson.dumps(hm.get_data(chr,start,end)) 