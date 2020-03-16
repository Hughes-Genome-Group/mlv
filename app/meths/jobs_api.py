from . import meths
from app.decorators import admin_required_method,logged_in_required_method
from app.jobs.jobs import get_all_jobs,get_job
import requests,ujson
from flask_login import current_user
from flask import request

     
@meths.route("/get_job_status/<id>",methods=['GET'])
@logged_in_required_method
def get_job_status(id):
    job =get_job(int(id))
    if not job.has_permission(current_user):
        return ujson.dumps({"success":False,"msg":"Permission denied"})
    return ujson.dumps({"success":True,"status":job.job.status})

@meths.route("/jobs/get_jobs",methods=['GET'])
@logged_in_required_method
def get_jobs():
    my_jobs=request.args.get("my_jobs")
    user=None
    if my_jobs:
        user=current_user.id
    if not my_jobs and not current_user.administrator:
        return ujson.dumps({"succes":False,"msg":"You do not have permission"})
    
    return ujson.dumps(get_all_jobs(user))



@meths.route("/jobs/get_job_info/<int:job_id>",methods=['GET'])
def get_job_info(job_id):
    j= get_job(job_id)
    return ujson.dumps(j.get_info())

@meths.route("/jobs/resend_job/<int:job_id>",methods=['GET'])
def resend_job(job_id):
    j=get_job(job_id)
    if j.has_permission(current_user):
        j.resend()
        return ujson.dumps({"status":j.job.status,
                            "info":{
                                "inputs":j.job.inputs,
                                "outputs":j.job.outputs
                            },
        "success":True})
    else:
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    
@meths.route("/jobs/kill_job/<int:job_id>",methods=['GET'])
def kill_job(job_id):
    j=get_job(job_id)
    if j.has_permission(current_user):
        j.kill()
        return ujson.dumps({"status":j.job.status,
                            "info":{
                                "inputs":j.job.inputs,
                                "outputs":j.job.outputs
                            },
                            "success":True})
    else:
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
    

@meths.route("/jobs/reprocess_job/<int:job_id>",methods=['GET'])
def reprocess_job(job_id):
    j=get_job(job_id)
    if j.has_permission(current_user):
        j.process()
        return ujson.dumps({"status":j.job.status,
                            "info":{
                                "inputs":j.job.inputs,
                                "outputs":j.job.outputs
                            },
                            "success":True})
    else:
        return ujson.dumps({"success":False,"msg":"You do not have permission"})

@meths.route("/jobs/check_job_status/<int:job_id>",methods=['GET'])
def check_job_status(job_id):
    j=get_job(job_id)
    if j.has_permission(current_user):
        j.check_status()
        return ujson.dumps({"status":j.job.status,
                            "info":{
                                "inputs":j.job.inputs,
                                "outputs":j.job.outputs
                            },
                            "success":True})
    else:
        return ujson.dumps({"success":False,"msg":"You do not have permission"})
         
    
    