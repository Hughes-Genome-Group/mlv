from . import meths
from flask import request
from flask_user import current_user
from app.databases.user_models import User
from app.decorators import logged_in_required_method,admin_required_method
from app import databases,app
import ujson,os
from app import mail,app
from flask_mail import Message
from werkzeug.utils import secure_filename

@meths.route("/users/user_autocorrect")
@logged_in_required_method
def username_autocorrect():
    term = request.args.get("term")
    names =User.find_user_name(term)
    return ujson.dumps(names)


@meths.route("/users/has_permission/<permission>")
def user_has_permission(permission):
    ret_object={"permission":False}
    if  current_user.is_authenticated:
        perm=current_user.has_permission(permission)
        info = app.config["USER_PERMISSIONS"].get(permission)
        if  info:
            
            if info["type"] == "number":
                if not perm:
                    perm= info["default"]
            if current_user.administrator:
                perm = info["admins"]
        ret_object["permission"]=perm  
        
    return ujson.dumps(ret_object)




@meths.route("/users/get_user_data")
@admin_required_method
def get_user_data():
    sql = "SELECT users.id as id, (first_name || ' ' || last_name) as name, institution, email, count(projects.id) as project_num FROM users LEFT JOIN projects ON projects.owner=users.id GROUP BY users.id ORDER BY project_num DESC"
    res = databases["system"].execute_query(sql)
    return ujson.dumps(res)
    
 
 
@meths.route("/users/get_all_user_permissions/<int:user_id>")
@admin_required_method
def get_all_user_permissions(user_id):
    sql = "SELECT id,permission,value FROM permissions WHERE user_id=%s"
    res = databases["system"].execute_query(sql,(user_id,))
    return ujson.dumps(res)


@meths.route("/users/add_user_permission/<int:user_id>",methods=["POST"])
@admin_required_method
def add_user_permission(user_id):
    perm = request.form.get("perm")
    val = request.form.get("val")
    sql = "INSERT INTO permissions (user_id,permission,value) VALUES (%s,%s,%s)"
    pid = databases["system"].execute_insert(sql,(user_id,perm,val))
    return ujson.dumps({"success":True,"id":pid})

@meths.route("/users/delete_user_permission/<int:perm_id>")
@admin_required_method
def delete_user_permission(perm_id):
    sql = "DELETE FROM permissions WHERE id=%s"
    databases["system"].execute_delete(sql,(perm_id,))
    return ujson.dumps({"success":True})

       
    
@meths.route("/send_help_email",methods=["POST"])
@logged_in_required_method
def send_help_email():
    user_name = current_user.first_name+" "+current_user.last_name
    data =request.json
    user_details ="user id:{}\tuser name:{}\tinstitution:{}\n\n".format(current_user.id,user_name,current_user.institution)
    url_details= "url:{}\n\n".format(data["url"])
    
    msg=Message()
    msg.body=user_details+url_details+data["text"]
    msg.subject=app.config["APPLICATION_NAME"]+":"+data["subject"]
    msg.recipients = app.config["HELP_EMAIL_RECIPIENTS"]
    mail.send(msg)
    
    return ujson.dumps({"success":True})

@meths.route("/get_help_text/<module>/<name>")
def get_help_text(module,name):
    response={}
    admin=False
    over_ride = request.args.get("overide_pref")
    
    if current_user.is_authenticated:
        if current_user.administrator:
            admin=True
        if not over_ride:
            pref = "not_show_{}_{}_help".format(module,name)
            sql = ("SELECT id FROM user_preferences WHERE user_id=%s"
                   " AND preference = %s")
            res = databases["system"].execute_query(sql,(current_user.id,pref))
            if len(res)>0:
                return ujson.dumps({"not_show":True})
            
    module=secure_filename(module)
    name=secure_filename(name)
    file_name =os.path.join(app.root_path,"modules",module,"templates","help",name+".txt") 
    response['text'] = open(file_name).read()
    response['admin']=admin
    if not over_ride:
        response['autoshow']=True
    return ujson.dumps(response)
            
@meths.route("/save_help_text/<module>/<name>",methods=["POST"])
@admin_required_method
def save_help_text(module,name):
    name = secure_filename(name) 
    text=request.form.get("text")
    if text:
        module=secure_filename(module)
        name=secure_filename(name)
        file_name =os.path.join(app.root_path,"modules",module,"templates","help",name+".txt")     
        handle= open(file_name,"w")
        handle.write(text)
        handle.close()
    return ujson.dumps({"success":True})



@meths.route("/not_show_help_text/<module>/<name>")
@logged_in_required_method
def not_show_help_text(module,name):
    sql = "INSERT into user_preferences (user_id,preference) VALUES (%s,%s)"
    pref= "not_show_{}_{}_help".format(module,name)
    databases["system"].execute_insert(sql,(current_user.id,pref))
    return ujson.dumps({"success":True})



        