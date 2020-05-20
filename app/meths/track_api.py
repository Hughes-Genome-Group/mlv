from . import meths
from app.ngs.track import get_all_tracks,get_all_columns,get_inputs,validate_track,add_track,validate_track_file_ucsc
import ujson
from flask import request
from app.decorators import logged_in_required_method


@meths.route("/<genome>/get_tracks",methods=['GET',"POST"])
def get_tracks(genome):
    return ujson.dumps(get_all_tracks(genome))


@meths.route("/validate_track_url",methods=["GET",'POST'])
@logged_in_required_method
def validate_track_url():
    url = request.form.get("url")
    multi = request.form.get("multi")
    if multi:
        urls =  url.split(",")
        for u in url:
            r=validate_track_file_uscs
    result= validate_track_file_ucsc(url,50)
    return ujson.dumps(result)


@meths.route("/get_track_columns",methods=['GET',"POST"])
def get_track_columns():
    return ujson.dumps(get_all_columns())

@meths.route("/get_track_inputs",methods=['GET',"POST"])
def get_track_inputs():
    return ujson.dumps(get_inputs())

@meths.route("/<genome>/add_new_track",methods=['GET',"POST"])
def add_new_track(genome):
    data = request.json
    errors= validate_track(genome,data)
    if len(errors)==0:
        id = add_track(genome,data)
        return ujson.dumps({"success":True,"data":data})
    else:
        return ujson.dumps({"success":False,"errors":errors})
