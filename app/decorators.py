from functools import wraps
from flask import request, redirect, url_for,flash
from flask_login import current_user
from app import db
import ujson

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("You need to be logged in as an administrator for this page","error")
            return redirect(url_for('user.login', next=request.url))
        if not current_user.administrator:
            flash("you need Adiminisrative privelages for this page","error")
            return redirect(url_for('main.home_page') )
        return f(*args, **kwargs)
    return decorated_function



def admin_required_method(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if  current_user.is_authenticated and current_user.administrator:
           return f(*args, **kwargs)
        return ujson.dumps({"success":False,"msg":"Adminisrative Permissions Required"})
    return decorated_function

def logged_in_required_method(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if  current_user.is_authenticated:
           return f(*args, **kwargs)
        return ujson.dumps({"success":False,"msg":"Tou need to be logged in for this method"})
    return decorated_function

def logged_in_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if  current_user.is_authenticated:
           return f(*args, **kwargs)
        flash("You need to be logged in to view this page","error")
        return redirect(url_for('user.login', next=request.url))
        
    return decorated_function
          

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            msg=""
            if not current_user.is_authenticated:
                 flash("You need to be logged in and have permission","error")
                 return redirect(url_for('user.login', next=request.url))
            elif not current_user.administrator:
                if  not current_user.has_permission(permission):
                    flash("You do not have permission for " +request.url ,"error")
                    return redirect(url_for('main.home_page'))
            
            return f(*args,**kwargs)
         
        return decorated_function
    return decorator 









#decorator for methods that have genome(db) as first argument
#and return json dicrtionary containing success (boolean)
#and msg (string)
def permission_required_method(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            msg=""
            if not current_user.is_authenticated:
                msg = "Method requires login"
            elif not current_user.administrator:
               if  not current_user.has_permission(permission):
                   msg = "You do not have permission"
            if msg:
                return ujson.dumps({"success":False,"msg":msg})
            return f(*args,**kwargs)
         
        return decorated_function
    return decorator 
                
    