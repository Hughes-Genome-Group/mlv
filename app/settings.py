# Settings common to all environments (development|staging|production)
# Place environment specific settings in env_settings.py
# An example file (env_settings_example.py) can be used as a starting point

import os
import importlib



# Application settings
APP_NAME = "MLV"
APP_SYSTEM_ERROR_SUBJECT_LINE = APP_NAME + " system error"

# Flask settings
CSRF_ENABLED = True

# Flask-SQLAlchemy settings
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask-User settings
USER_APP_NAME = APP_NAME
USER_ENABLE_CHANGE_PASSWORD = True  # Allow users to change their password
USER_ENABLE_CHANGE_USERNAME = False  # Allow users to change their username
 # Force users to confirm their email
USER_ENABLE_FORGOT_PASSWORD = True  # Allow users to reset their passwords
USER_ENABLE_EMAIL = True  # Register with Email
USER_ENABLE_REGISTRATION = True  # Allow new users to register
USER_ENABLE_RETYPE_PASSWORD = True  # Prompt for `retype password` in:
USER_ENABLE_USERNAME = False  # Register and Login with username
USER_AFTER_LOGIN_ENDPOINT = 'main.home_page'
USER_AFTER_LOGOUT_ENDPOINT = 'main.home_page'


USER_ENABLE_CONFIRM_EMAIL = True 
USER_SEND_REGISTERED_EMAIL = True
USER_ALLOW_LOGIN_WITHOUT_CONFIRMED_EMAIL=True
USER_ENABLE_MULTIPLE_EMAILS=True

#change to something more secure
SECRET_KEY="somerandomstring"

#Database settings
DB_HOST=os.getenv("DB_HOST") or "localhost"
DB_USER="mlv"
DB_PASS=os.getenv("DATABASE_PASS")
SYSTEM_DATABASE="mlv_user"
SQLALCHEMY_TRACK_MODIFICATIONS = False  

#Filled in from the gemome table
GENOME_DATABASES={
}

#Folders need to be mapped
DATA_FOLDER="/data/mlv/"
TEMP_FOLDER="/data/mlv/temp"
TRACKS_FOLDER="/data/tracks"

JS_VERSION="5.165"


#email settings
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_SSL = False
MAIL_USE_TLS = True
MAIL_USERNAME = 'mlv@gmail.com'
MAIL_PASSWORD = 'password'
MAIL_DEFAULT_SENDER = 'The MLV Team'

HELP_EMAIL_RECIPIENTS=["mlv@gmail.com"]

HOME_PAGE = "mlv_home.html"
APPLICATION_NAME="MultiLocusView"
APPLICATION_LOGO='/static/img/logo.png'

USER_PERMISSIONS={}

MLV_PROJECTS={ 
    "annotation_set":{
        "icon":"img/icons/peak_search_icon.png",
        "large_icon":"/static/img/icons/annotation_set_icon.png",
        "can_create":True,
        "is_public":True,
        "label":"Annotations",
        "import":"app.projects.annotation_set",
        "enter_genome":True,
        "description":"Upload a bed like file to create annotations. In projects, you can then find which features intersect with these annotations"      
     }  
}

MODULES=["multi_locus_view"]
MODULE_INFO={}

#celery settings
BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_RESULT_BACKEND = 'amqp'
USE_CELERY=True

ZEGAMI_SETTINGS={
    "API_URL":"https://zegami.com/api/",
    "OAUTH_URL":"https://zegami.com/oauth/token/"
    
}




