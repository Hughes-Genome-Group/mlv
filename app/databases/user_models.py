

from flask_user import UserMixin
from flask_user.forms import RegisterForm
from flask_user.signals import user_registered
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, validators
from sqlalchemy import text,or_
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from app import app,db,databases

def get_permission(user_id,permission):
    sql = "SELECT value FROM permissions WHERE user_id=%s AND permission=%s"
    res = databases["system"].execute_query(sql,(user_id,permission))
    if len(res)==0:
        return None
    return res[0]["value"]

class DummyUser():
    def __init__(self,email,first_name,last_name):
        self.email= email
        self.first_name=first_name
        self.last_name=last_name

# Define the User data model. Make sure to add the flask_user.UserMixin !!
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    # User authentication information (required for Flask-User)
    email = db.Column(db.Unicode(255), nullable=False, server_default=u'', unique=True)
    confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False, server_default='')
    # reset_password_token = db.Column(db.String(100), nullable=False, server_default='')
    active = db.Column(db.Boolean(), nullable=False, server_default='0')

    # User information
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    first_name = db.Column(db.Unicode(50), nullable=False, server_default=u'')
    last_name = db.Column(db.Unicode(50), nullable=False, server_default=u'')
    institution = db.Column(db.Unicode(300), server_default=u'')
    administrator= db.Column(db.Boolean,default=False,nullable=False)
    
    
    
    def object_is_shared(self,genome,type,object_id):
        p = db.session.query(SharedObject.owner).filter_by(shared_with=self.id,type=type,genome=genome,object_id= object_id).first()
        if p:
            return p.owner
        return False
    
    
    def has_permission(self,permission,value=None):
        if self.administrator:
            return True
        if not value:
            p = db.session.query(Permission).filter_by(user_id=self.id,permission=permission).first()
            if p:
                return p.value
            return None
        else:
            p = db.session.query(Permission).filter_by(user_id=self.id,permission=permission,value=value).first()
            if p:
                return True
            return False
            
    def delete_user(self):
        sql = "SELECT id FROM projects WHERE owner= %s"
        res= databases["system"].execute_query(sql,(self.id,))
        for r in res:
            p=get_project(r["id"])
            p.delete(True)
        db.session.delete(self)
        db.session.commit()
           
     
       
    @staticmethod
    def get_all_shared_objects(genome,user_id,type,limit=5,offset=0,simple=True):
        '''Gets the id's of all object's that have been shared with
        the user
        Args:
            genome(str):The name of the genome(database)
            user_id(int): The id of the user
            type(str) The type of object : - project,viewset,plugin
            simple (Optional[boolean]):If True (default) only a list
                of project ids will be returned otherwise a dicationary
                of project ids to a list of sharer id,firstname,secondname
        
        Returns:
            Either  a list of project ids or a dictionary of ids to
            a list containing sharerid, firstname, lastname
        
        '''
        if simple:
            ids = db.session.query(SharedObject.object_id).filter_by(genome=genome,shared_with=user_id,type=type).all()
            li =[]
            for i in ids:
                li.append(i)
            return li
        else:
            ret_dict={}
            sql= ("SELECT date_shared,object_id,users.id AS uid,users.first_name AS ufn ,users.last_name uln"
                   " FROM shared_objects INNER JOIN users ON genome = '{}' AND  shared_with = {}"
                   " AND type = '{}' AND users.id = shared_objects.owner ORDER BY date_shared DESC"
                   " LIMIT {} OFFSET {}").format(genome,str(user_id),type,limit,offset)
              
            results= db.engine.execute(text(sql))
            for res in results:
                ret_dict[res.object_id]=[res.uid,res.ufn,res.uln,res.date_shared]
            return ret_dict   
         
    def add_all_create_permissions(self):
        for project in app.config["MLV_PROJECTS"]:
            p = app.config["MLV_PROJECTS"][project]
            if p.get("is_public") and p.get("can_create"):
                perm = Permission(user_id=self.id,permission="create_project_type",value=project)
                db.session.add(perm)
        db.session.commit()
        
    def add_create_permission(self,project_type):
        if not self. has_permission("create_project_type",project_type):
            perm = Permission(user_id=self.id,permission="create_project_type",value=project_type)
            db.session.add(perm)
            db.session.commit()
        
        
    @staticmethod
    def get_create_permissions(user,genome):
        '''Checks whether the user has create permissions
        for plugins.This is a static method as the user may be 
        an AnonymousUserMixin
        
        Args:
            user:the current user (can be AnonymousUserMixin)
            genome:the genome for which the permissions are to be checked
        
        Returns:
            a list of plugins for which the user has permission to create
            returns an empty list if the user has no permissions
        
        '''
        li=[]
        if not user.is_authenticated:
            return li
        for project in app.config['MLV_PROJECTS']:
            li.append("create_"+project+"_project")
        if user.administrator:
            return li
        perms = db.session.query(Permission.permission).filter(Permission.permission.in_(li),
                                            Permission.user_id==user.id,
                                           Permission.genome==genome)
        li=[]
        for p in perms:
            li.append(p.permission)
        return li
    
    @staticmethod
    def find_user_name(term,limit=10):
        term="%"+term+"%"
        ret_list=[]
        results =User.query.filter(or_(User.first_name.ilike(term),User.last_name.ilike(term))).\
                                   order_by(User.last_name).limit(limit).all()
        for res in results:
            ret_list.append({
                "label":res.first_name+" "+res.last_name,
                "value":res.id
            })
            
        return ret_list


@user_registered.connect_via(app)
def _after_registration_hook(sender,user,**extra):
    user.add_all_create_permissions()
    
    
def add_create_permissions(project_type):
       users = db.session.query(User).all()
       for user in users:
           if user.id>1:
               user.add_create_permission(project_type)
       
    


# Define the user permissions
class SharedObject(db.Model):
    __tablename__ = 'shared_objects'
    id = db.Column(db.Integer(), primary_key=True)
    shared_with = db.Column(db.Integer()) # for @roles_accepted()
    level = db.Column(db.String(200))
    object_id =db.Column(db.Integer())
    date_shared = db.Column(db.DateTime(),default=func.now())
  

    
# Define the user permissions
class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer()) # for @roles_accepted()
    permission=db.Column(db.String(200),nullable=False)
    value = db.Column(db.String(200),nullable=False)



class UserJob(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer(), primary_key=True)
    inputs=db.Column(JSON)
    user_id=db.Column(db.Integer(), db.ForeignKey('users.id'))
    outputs=db.Column(JSON)
    sent_on=db.Column(db.DateTime, server_default=db.func.now())
    finished_on=db.Column(db.DateTime)
    status=db.Column(db.String(200))
    genome=db.Column(db.String(100))
    is_deleted=db.Column(db.Boolean())
    type= db.Column(db.String(200))
    
  
# Define the User registration form
# It augments the Flask-User RegisterForm with additional fields
class MyRegisterForm(RegisterForm):
    first_name = StringField('First name', validators=[
        validators.DataRequired('First name is required')])
    last_name = StringField('Last name', validators=[
        validators.DataRequired('Last name is required')])
    institution = StringField("Institution",validators=[
        validators.DataRequired('Institution is required')])


# Define the User profile form
class UserProfileForm(FlaskForm):
    first_name = StringField('First name', validators=[
        validators.DataRequired('First name is required')])
    last_name = StringField('Last name', validators=[
        validators.DataRequired('Last name is required')])
    submit = SubmitField('Save')
