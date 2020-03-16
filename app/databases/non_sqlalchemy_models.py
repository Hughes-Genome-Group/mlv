from app import app,databases


class User(UserMixin):
    __tablename__ = "users"
    email=True
    first_name=True
    last_name=True
    dirty_records={}
    
    @property
    def confirmed_at(self):
        return self._confirmed_at
    
    @confirmed_at.setter
    def confirmed_at(self, value):
        
        if self._confirmed_at != value:
            self._confirmed_at=value
            di=  User.dirty_records.get(self.id)
            if not di:
                di ={}
                User.dirty_records[self.id]=di
            di["confirmed_at"]=value
    
    
    @property
    def password(self):
        return self._password
    
    @password.setter
    def password(self, value):
        
        if self._password != value:
            self._password=value
            di=  User.dirty_records.get(self.id)
            if not di:
                di ={}
                User.dirty_records[self.id]=di
            di["password"]=value
        
    
  
    def __init__(self,data):
        self.id= data['id']
        self.email = data["email"]
        self._confirmed_at = data["confirmed_at"]
        self._password =data["password"]
        self.active = data["is_active"]
        self.first_name = data["first_name"]
        self.last_name=data["last_name"]
        self.administrator= data["administrator"]
        
    def has_permission(self,permission):
        sql =  "SELECT value FROM permissions WHERE user_id=%s AND permission=%s"
        res = databases["system"].excute_query(sql,(self.id,permission))
        if len(res)==0:
            return None
        
        else:
            return res[0]["value"]
        
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
              
            results= database["system"].execute_query(sql)
            for res in results:
                ret_dict[res["object_id"]]=[res["uid"],res["ufn"],res["uln"],res["date_shared"]]
            return ret_dict
        
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
        
        sql = "SELECT permission FROM permissions WHERE user_id=%s AND permission = ANY(%s)"
        perms = databases["system"].execute_query(sql,(user.id,li))
        li=[]
        for p in perms:
            li.append(p["permission"])
        return li
    
    @staticmethod    
    def find_user_name(term,limit=10):
        term="%"+term+"%"
        ret_list=[]
        sql = ("SELECT id,firstname,lastname FROM users WHERE "
               "firstname ILIKE %s OR last_name ILIKE %s "
               "ORDER BY last_name LIMIT {}").format(limit)
        results =databases["system"].execute_query(sql,(term,term))
        for res in results:
            ret_list.append({
                "label":"{} {}".format(res["first_name"],res["last_name"]),
                "value":res["id"]
            })
            
        return ret_list
         
        
        
    
        



class MLVAdapter():
    """ This object is used to shield Flask-User from SQLAlchemy specific functions."""
    def __init__(self, db, UserClass, UserAuthClass=None, UserEmailClass=None, UserProfileClass=None, UserInvitationClass=None):
        self.db = db
        self.UserClass = UserClass                  # first_name, last_name, etc.
        self.UserAuthClass = UserAuthClass          # username, password, etc.
        self.UserEmailClass = UserEmailClass        # For multiple emails per user
        self.UserProfileClass = UserProfileClass    # Distinguish between v0.5 or v0.6 call
        self.UserInvitationClass = UserInvitationClass
     
     
     
    def get_object(self, ObjectClass, id):
        """ Retrieve one object specified by the primary key 'pk' """
        sql = "SELECT * FROM {} WHERE id=%s".format(ObjectClass.__tablename__)
        res = self.db.execute_query(sql,(id,))
        if len(res)==0:
            return None
        else:
            return ObjectClass(res[0])

    def find_all_objects(self, ObjectClass, **kwargs):
        """ Retrieve all objects matching the case sensitive filters in 'kwargs'. """

        # Convert each name/value pair in 'kwargs' into a filter
        where= []
        values = tuple()
        for field_name, field_value in kwargs.items():
            where.append("{} = %s".format(field_name))
            values+=(field_value,)
            # Make sure that ObjectClass has a 'field_name' property
        # Execute query
        sql = "SELECT * FROM {} WHERE {}".format(ObjectClass.__tablename__," AND ".join(where))
        res = self.db.execute_query(sql,values)
        objs=[]
        for r in res:
            objs.append(ObjectClass(r))
        return objs


    def find_first_object(self, ObjectClass, **kwargs):
        """ Retrieve the first object matching the case sensitive filters in 'kwargs'. """
        where= []
        values = tuple()
        for field_name, field_value in kwargs.items():
            where.append("{} = %s".format(field_name))
            values+=(field_value,)
            # Make sure that ObjectClass has a 'field_name' property
        # Execute query
        sql = "SELECT * FROM {} WHERE {} LIMIT 1".format(ObjectClass.__tablename__," AND ".join(where))
        res = self.db.execute_query(sql,values)
        if len(res)==0:
            return None
        return ObjectClass(res[0])
       

      

    def ifind_first_object(self, ObjectClass, **kwargs):
        """ Retrieve the first object matching the case insensitive filters in 'kwargs'. """
        where= []
        values = tuple()
        for field_name, field_value in kwargs.items():
            where.append("{} ILIKE %s".format(field_name))
            values+=(field_value,)
            # Make sure that ObjectClass has a 'field_name' property
        # Execute query
        sql = "SELECT * FROM {} WHERE {} LIMIT 1".format(ObjectClass.__tablename__," AND ".join(where))
        res = self.db.execute_query(sql,values)
        if len(res)==0:
            return None
        return ObjectClass(res[0])

       

    def add_object(self, ObjectClass, **kwargs):
        """ Add an object of class 'ObjectClass' with fields and values specified in '**kwargs'. """
        new_id = self.db.insert_dict_into_table(kwargs,ObjectClass.__tablename__)
        object=self.get_object(ObjectClass,new_id)
        return object

    def update_object(self, object, **kwargs):
        """ Update object 'object' with the fields and values specified in '**kwargs'. """
        for key,value in kwargs.items():
            if hasattr(object, key):
                setattr(object, key, value)
        
             

    def delete_object(self, object):
        self.db.delete_by_id(object.__tablename__,[object.id])
        if object.dirty_records.get(object.id):
            del object.dirty_records[object.id]

    def commit(self):
        update_list=[]
        for ob_id,di in self.UserClass.dirty_records.items():
                di['id']=ob_id
                update_list.append(di)
            
        self.db.update_table_with_dicts(update_list,self.UserClass.__tablename__)
        self.UserClass.dirty_records={}
    