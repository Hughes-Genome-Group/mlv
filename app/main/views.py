from . import main
from flask import Blueprint, redirect, render_template,request,safe_join,send_from_directory
from flask import request, url_for,flash
from flask_user import current_user, login_required, roles_accepted
from app import db,app,databases
from app.databases.user_models import UserProfileForm,User
from app.decorators import admin_required,permission_required,logged_in_required
from app.ngs.project import GenericObject,get_project,get_main_project_types
from app.ngs.genome import get_genomes
from flask_cors import cross_origin

import ujson


#***********GENERAL PAGES**********************
@main.route('/')
def home_page():

    return render_template(app.config["HOME_PAGE"])

@main.route("projects/<project_type>/home")
def project_home_page(project_type):
    not_allow_other = app.config["MLV_PROJECTS"][project_type].get("not_allow_other")
        
          
    return render_template("{}/home.html".format(project_type),
                           project_type=project_type,
                           genomes=get_genomes(not_allow_other))



'''calls to static module files are rerouted
to the module's static folder - can do this at the server level 
e.g with nginx:-
location ~  /(.*)/static/(.*) {
    alias /<app_root>/modules/$1/static/$2;
}'''
@main.route("<project>/static/<path:path>")
def test_url(project,path):
   f= safe_join("modules",project,"static",path)
   return send_from_directory(app.root_path,f)
   
   
 


    
@main.route("projects/<type>/<int:project_id>")
def project_page(type,project_id):
    p = get_project(project_id)
    if not  p.has_view_permission(current_user):
        return refuse_permission()
    template,args = p.get_template(request.args)
    all_args={
        "project_id":project_id,
        "project_name":p.name, 
        "project_type":type,
        "description":p.description     
    }
    all_args.update(args)
    return render_template(template,**all_args)
   
@main.route("projects")
def projects():
    return render_template("projects/projects.html")



#***********JOBS*************************


@main.route("jobs/jobs_panel")
@admin_required
def jobs_panel():
    return render_template('admin/view_jobs.html')


@main.route("admin/users_panel")
@admin_required
def users_panel():
    return render_template('admin/view_users.html')


@main.route("jobs/my_jobs")
@logged_in_required
def my_jobs():
    return render_template('admin/view_jobs.html',my_jobs=True)



@main.route("general/get_info")
def get_general_info():
    return ujson.dumps({
         "genomes":get_genomes(),
         "projects":get_main_project_types()
    })
   
   
@main.route("general/get_jobs_projects")
@logged_in_required
def get_jobs_projects():
    sql = "SELECT COUNT(status) FILTER(WHERE status='failed') AS failed, COUNT(status) FILTER(WHERE status<>'failed') AS running FROM jobs WHERE user_id={} AND status <> 'complete'".format(current_user.id)
    job_info = databases["system"].execute_query(sql)[0]
    sql = "SELECT COUNT(*) AS num FROM projects WHERE owner={} AND is_deleted=false AND type = ANY (%s)".format(current_user.id)
    projects=databases['system'].execute_query(sql,(app.config["MLV_MAIN_PROJECTS"],))[0]['num']
    return ujson.dumps({"projects":projects,"jobs":{"running":job_info['running'],"failed":job_info['failed']}})
    
@main.route("browser_view/<int:project_id>/<int:view_id>")
@cross_origin()
def browser_view(project_id,view_id):
    return render_template("pages/genome_browser.html",project_id=project_id,view_id=view_id)






#********Helper Methods***********************************
def refuse_permission():
    if not current_user.is_authenticated:
        flash("You need to be logged in and have permission","error")
        return redirect(url_for('user.login', next=request.url))
    else:
        flash("You do not have permission for " +request.url ,"error")
        return redirect(url_for('main.home_page'))
