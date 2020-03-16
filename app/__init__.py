# __init__.py is a special Python file that allows a directory to become
# a Python package so it can be accessed using the 'import' statement.

# __init__.py is a special Python file that allows a directory to become
# a Python package so it can be accessed using the 'import' statement.

from datetime import datetime
import os
import jinja2
from flask import Flask
from flask_mail import Mail
from flask_migrate import Migrate, MigrateCommand
from flask_sqlalchemy import SQLAlchemy
from flask_user import UserManager, SQLAlchemyAdapter
from flask_wtf.csrf import CSRFProtect
from app.databases.main_database import get_databases
import ujson
import logging
import importlib
from logging.handlers import RotatingFileHandler
from pathlib import Path

from celery import Celery
celery = Celery(__name__)

# Instantiate Flask extensions
db = SQLAlchemy()
csrf_protect = CSRFProtect()
mail = Mail()
migrate = Migrate()
databases={}
modules={}
app = Flask(__name__)


def create_app(config = None,extra_config_settings={},min_db_connections=1):
    """Create a Flask applicaction.
    """
    # Instantiate Flask
   

    # Load App Config settings
    # Load common settings from 'app/settings.py' file
    app.config.from_object('app.settings')
    # Load local settings from 'app/local_settings.py'
    if config:
        app.config.from_object("app."+config)
    # Load extra config settings from 'extra_config_settings' param
    app.config.update(extra_config_settings)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = 'postgresql://{}:{}@{}/{}'.format(app.config["DB_USER"],
                                                                              app.config["DB_PASS"],
                                                                              app.config["DB_HOST"],
                                                                              app.config["SYSTEM_DATABASE"])
    
    
    #get connections for the main databases (Non Flask-SQLAlchemy)
    get_databases(databases,app,min_db_connections)

    # Setup Flask-Extensions -- do this _after_ app config has been loaded
    #database.init_app(app)
    # Setup Flask-SQLAlchemy
    db.init_app(app)
    
    
    
    #work out modules
    root = app.root_path
    modules_folder = os.path.join(root,"modules")
    template_folders=[]
    for folder in app.config["MODULES"]:
        module_folder=os.path.join(modules_folder,folder)
        if os.path.isdir(module_folder):
            load_module(app,module_folder)
            template_folders.append(os.path.join(root,"modules",folder,"templates"))
    
    
    my_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader(template_folders),
    ])
    app.jinja_loader = my_loader
         
    app.config['MLV_MAIN_PROJECTS']=[]

    for p in app.config['MLV_PROJECTS']:
        im = app.config['MLV_PROJECTS'][p].get("import")
        #legacy
        if im:
            importlib.import_module(im)
        if app.config['MLV_PROJECTS'][p].get("main_project"):
            app.config['MLV_MAIN_PROJECTS'].append(p)
            
    
  
    #uplo
    celery.conf.update(app.config)
   
    # Setup Flask-Migrate
    #migrate.init_app(app, db)

    # Setup Flask-Mail
    mail.init_app(app)

    # Setup WTForms CSRFProtect
    csrf_protect.init_app(app)

    # Register blueprints
    from app.main import  main
    app.register_blueprint(main,url_prefix="/")
    
    from app.meths import meths
    app.register_blueprint(meths,url_prefix="/meths")
    csrf_protect.exempt(meths)

    # Define bootstrap_is_hidden_field for flask-bootstrap's bootstrap_wtf.html
    from wtforms.fields import HiddenField

    def is_hidden_field_filter(field):
        return isinstance(field, HiddenField)

    app.jinja_env.globals['bootstrap_is_hidden_field'] = is_hidden_field_filter
    


    
    load_loggers(app)

    # Setup Flask-User to handle user account related forms
    from .databases.user_models import MyRegisterForm,User

    db_adapter=SQLAlchemyAdapter(db,User)   # Setup the SQLAlchemy DB Adapter
    user_manager = UserManager(db_adapter, app,  # Init Flask-User and bind to app
                               register_form=MyRegisterForm  # using a custom register form with UserProfile fields
                               
    )

    return app



def load_module(app,module_folder):
    module_name=os.path.split(module_folder)[1]
    config_file = os.path.join(module_folder,"config.json")
    config = ujson.loads(open(config_file).read())
    for project in config["projects"]:
        app.config["MLV_PROJECTS"][project["name"]]=project
        import_path= "app.modules.{}.projects.{}".format(module_name,project["name"])
        importlib.import_module(import_path)
     
    jobs = config.get("jobs")
    if jobs:
        for job in jobs:
            import_path="app.modules.{}.jobs.{}".format(module_name,job["name"])
            importlib.import_module(import_path)
    
    permissions= config.get("permissions")
    if permissions:
        for key in permissions:
            app.config["USER_PERMISSIONS"][key]=permissions[key]
    app_config = config.get("config")
    if app_config:
        for key in app_config:
            app.config[key]=app_config[key]

def load_loggers(app):
    root = Path(app.root_path).parent
    log_file=os.path.join(str(root),"logs","log.txt")
    
    logHandler = RotatingFileHandler(log_file, maxBytes=200000, backupCount=1)
    
    # set the log handler level
    logHandler.setLevel(logging.INFO)
    logHandler.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)s:%(message)s"))

    # set the app logger level
    app.logger.setLevel(logging.INFO)

    app.logger.addHandler(logHandler)
    



@app.after_request
def after_request_function(response):
    db.session.close()
    return response



