from psycopg2.pool import ThreadedConnectionPool
import psycopg2,os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import AsIs
import psycopg2.extras


import os
from psycopg2._psycopg import connection

operands= {
             "equals":"=",
            "greater than":">",
            "less than":"<",
            "not equals":"!=",
            "=":"=",
            "between":"between"
    
}

def delete_genome_database(db_name):
    from app import app,databases
    #close all connections in order to drop databases
    databases[db_name].pool.closeall()

    #get a connection which can drop/create databases
    db_connection  = _get_connection(app,"postgres")
    conn = psycopg2.connect(db_connection)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    sql =  "DROP DATABASE IF EXISTS {}".format(tag);
    cursor.execute(sql)
    conn.commit()
    conn.close()
    del databases[db_name]
    




   

def create_genome_database(db_name):
    from app import app,databases
    #get a connection which can drop/create databases   
    db_connection  = _get_db_connection(app,"postgres")
    conn = psycopg2.connect(db_connection)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    #get the script
    file_name = os.path.join(app.root_path, 'databases', 'create_genome_db.sql')
    script = open(file_name).read().format(db_user=app.config['DB_USER'])
 
    sql ="CREATE DATABASE {} OWNER {}".format(db_name,app.config['DB_USER']);
    cursor.execute(sql)
    conn.commit()
    #get connection to create tables
    db_connection = _get_db_connection(app,db_name)
    db_conn = psycopg2.connect(db_connection)
    db_cursor=db_conn.cursor()
    db_cursor.execute(script)
    db_conn.commit()
    db_conn.close()
    conn.close()
    

        
    
def get_databases(databases,app,min_db_connections=1):
    try:
        #get the system database
        system_db_conn=_get_db_connection(app,app.config['SYSTEM_DATABASE'],True)
        databases["system"]=Database(system_db_conn,10,app)
        #now get th genome databases
        sql = "SELECT name,database,data,label,connections FROM genomes ORDER BY id"
        genomes= databases['system'].execute_query(sql)
        already={}
        for genome in genomes:
            already_conn = already.get(genome["database"])
            if already_conn:
                databases[genome["name"]]=already_conn
            else:
                db_conn= _get_db_connection(app,genome['database'])
            
                databases[genome['name']]=Database(db_conn,genome['connections'],app,min_db_connections)
                already[genome["database"]]=databases[genome["name"]]
            dgs= genome["data"].get("default_gene_set",1)
            sql = "SELECT description FROM gene_sets WHERE id=%s"
            res = databases[genome["name"]].execute_query(sql,(dgs,))
            dgs_desc= "No annotations"
            if len(res)>0:
                dgs_desc=res[0]["description"]
            app.config["GENOME_DATABASES"][genome["name"]]={
                "default_gene_set":dgs,
                "gene_description":dgs_desc,
                "label":genome["label"],
                "database":genome["database"]
            }
             
            fi = os.path.join(app.config["DATA_FOLDER"],genome["name"],"ens_to_ucsc.txt")
            if os.path.exists(fi):
                ens_to_ucsc={}
                with open(fi) as f:
                    for line in f:
                        arr =line.strip().split("\t")
                        ens_to_ucsc[arr[0]]=arr[1]
                app.config["GENOME_DATABASES"][genome["name"]]["ens_to_ucsc"]=ens_to_ucsc
                        
        #close the connection and re-open as this will cause problems with forking
        databases["system"].dispose()
        databases["system"]=Database(system_db_conn,10,app,min_db_connections)
        
            
        
    except:
        app.logger.exception("Unable to open databases")

def _get_db_connection(app,database,disable_ssl=False):
    c=app.config
    db_connection ="host='{}' dbname='{}' user='{}' password='{}'".format(
            c['DB_HOST'],
            database,
            c['DB_USER'],
            c['DB_PASS'] )
    #if disable_ssl:
    #     db_connection += " sslmode='disable'"
    return db_connection
    


def get_where_clause(filters,fields):
    '''Get all the views as a list of dictionaries orderd
        by id (ascending)
        Args:
            filters (list: Default is False -
                if True then only id,start,finish and chromosome will be
                returned 
            specific_views (Optional[list]): If given then only those in 
                the list will be given
                
        Returns:
            A list of dictionaries containing key (column name) to 
            value 
    '''

    vars = ()
  
    li = []
    for filter in filters:
        operand = operands.get(filter['operand'])
        if not operand:
            raise ValueError("operand {} not recognised".format(filter['operand']))
        field= fields.get(filter["field"])
        if not field:
            raise ValueError("field {} not recognised".format(filter['field']))
            
        if operand == "=" and isinstance(filter["value"],list):
            li.append(" {} = ANY(%s)".format(field))
        elif operand == "between":
            li.append(" {} >= %s AND {} <=%s ".format(field,field))
        else:  
            li.append(" {} {} %s ".format(field,operand))
        if operand == "between":
            vars= vars +(filter["value"][0],filter["value"][1])
        else:
            vars = vars +(filter["value"],)
    sql = " WHERE"+"AND".join(li)
    
    return sql,vars
    

class Database(object):
    def __init__(self,db_connection,connection_number,app,min_db_connections=1):
        self.db_connection=db_connection
        self.min_connections=min_db_connections
        self.connection_number=connection_number
        self.pool=ThreadedConnectionPool(min_db_connections,connection_number,db_connection)
        self.app=app
        self.last_seen_process_id = os.getpid()
        self.needs_change=True
     
    def dispose(self):
        self.pool.closeall()
           
    def get_connection(self):
        if self.needs_change:
            current_pid = os.getpid()
            if not (current_pid == self.last_seen_process_id):
                self.last_seen_process_id = current_pid
                self.pool.closeall()
                self.pool=ThreadedConnectionPool(self.min_connections,self.connection_number,self.db_connection)
            self.needs_change=False
        return self.pool.getconn()
    
    def run_script(self,script):
        from app import app
        success=True
        conn=self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(script)
            conn.commit()
            self.pool.putconn(conn)
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(script))
            conn.rollback()
            self.pool.putconn(conn)
            success=False       
        return success
        
        
    def add_tracks(self,dicts,table):
        conn = self.get_connection()
        cursor =conn.cursor()
        for track in tracks:
            
            columns = track.keys()
            values = [track[column] for column in columns]  
            sql = "INSERT INTO tracks (%s) VALUES %s"
            cursor.execute(sql, (AsIs(','.join(columns)), tuple(values)))
        
        conn.commit()
        main_database.Database.run_script
        
    def execute_update(self,sql,vars=None):
        conn=self.get_connection()
        success=True
        try:
            cursor = conn.cursor()
            cursor.execute(sql,vars)
            conn.commit()
            self.pool.putconn(conn)
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
            success=False
        return success
    
    def value_exists(self,table,field,value):
        exists=False
        conn=self.get_connection()
        try:
            cursor = conn.cursor()
            sql= "SELECT * FROM %s WHERE %s = %s "
            vars= (AsIs(table),AsIs(field),value)
            cursor.execute(sql,vars)
            results = cursor.fetchall()
            self.pool.putconn(conn)
            if len(results)>0:
                exists=True
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
            
        return exists
    
    
    def delete_table(self, table):
        '''Deletes the table from the database
        table:
            Thr name of the table to delete 
        Returns:
            True - if the table was deleted, otherwise False.
        '''
        conn=self.get_connection()
        sql="DROP TABLE public.{}".format(table)
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            self.pool.putconn(conn)
            return True
        except Exception as e:  
            self.app.logger.exception("The table {}  could not be deleted using the SQL:\n{}".format(table,sql))
            conn.rollback()
            self.pool.putconn(conn)
            return False
    
    def remove_columns(self,table,columns):
        '''Deletes columns from the specified table
        
        Args:
            columns(list[str]): A list of column names to delete
                
        Returns:
            True - if the columns were deleted, otherwise False
        '''
        conn=self.get_connection()
        results=[]
        sql=""
        try:
            cursor = conn.cursor()
            for col in columns:
               
                sql= "ALTER TABLE public.{} DROP COLUMN {}".format(table,col)
                cursor.execute(sql)
            conn.commit()
            self.pool.putconn(conn)
            return True
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
            return False
           
    def add_columns(self,table,columns):
        '''Adds columns to to the specified table
        
        Args:
            columns: A list of dictionaries with 'name' and 'datatype' (text,integer or double)
                and optionally default (specifies default value). There is no check on the column
                name, so it has to be compatible with postgresql
                
        Returns:
            True - if the columns were added, otherwise False
        '''
        
        conn=self.get_connection()
        results=[]
        sql=""
        try:
            cursor = conn.cursor()
            for col in columns:
                if col['datatype']=="double":
                    col['datatype']="double precision"
                sql= "ALTER TABLE public.{} ADD COLUMN {} {}".format(table,col['name'],col['datatype'])
                if col.get("default"):
                    val = col.get("default")
                    if col['datatype']=="text":
                        val="'"+val+"'"
                    sql += " default " + val
                cursor.execute(sql)
            conn.commit()
            self.pool.putconn(conn)
            return True
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
            return False
            
        
        
    def execute_query(self,sql,vars=None):
        conn=self.get_connection()
        results=[]
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql,vars)
            results = cursor.fetchall()
            self.pool.putconn(conn)
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            self.pool.putconn(conn)
            
        return results
    
    def get_sql(self,sql,vars=None):
        conn=self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            result = cursor.mogrify(sql,vars)
            self.pool.putconn(conn)
            return result
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            self.pool.putconn(conn)
    
    
    def delete_by_id(self,table,ids):
        conn=self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            sql = "DELETE FROM %s WHERE id = ANY (%s)"
            cursor.execute(sql,(AsIs(table),ids))
            conn.commit()
            self.pool.putconn(conn)
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
            
    def execute_delete(self,sql,vars=None):
        
        conn=self.get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql,vars)
            conn.commit()
            self.pool.putconn(conn)
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
            return False
        return True
    
    
        
    
    def execute_insert(self,sql,vars=None,ret_id=True):
        if ret_id:
            sql+=" RETURNING id"
        conn=self.get_connection()
        new_id=-1
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql,vars)
            conn.commit()
            if ret_id:
                new_id = cursor.fetchone()[0]
            self.pool.putconn(conn)
           
        except Exception as e:  
            self.app.logger.exception("The SQL could not be run:\n{}".format(sql))
            conn.rollback()
            self.pool.putconn(conn)
        return new_id
       
        
        
    def get_tracks(self,track_ids=[],field="track_id",proxy=True):
        '''Get track info for all the supplies track ids
        Args:
            track_ids(list): A list of track_ids (or ids) to retreive
            field(Optional[str]): The field to query the databse (track_id
                by default)
            proxy(Optional[boolean]) If true (default) the the track's
              proxy url as defined in the config will be returned
        
        '''
        from app import app
        conn=self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sql = "SELECT id,track_id,url,type,short_label,color FROM tracks WHERE %s = ANY(%s)"
        cursor.execute(sql,(AsIs(field),track_ids))
        results=cursor.fetchall()
        self.pool.putconn(conn)
        if not results:
            return []
        t_p = app.config.get("TRACK_PROXIES") 
        if t_p and proxy:
            for item in results:
                for p in t_p:
                    item['url']=item['url'].replace(p,t_p[p])
        return results
        
    
    def insert_dicts_into_table(self,dicts,table):
        
        conn = self.get_connection()
        try:
            cursor =conn.cursor()
            for item in dicts:
                sql = "INSERT INTO {} (%s) VALUES %s".format(table)
                columns = item.keys()
                values = [item[column] for column in columns]  
                cursor.execute(sql, (AsIs(','.join(columns)), tuple(values)))
            conn.commit()
            cursor.close()
            self.pool.putconn(conn)
        except Exception as e:
            conn.rollback()
            self.pool.putconn(conn)
            raise
            
        
    
    def update_table_with_dicts(self,dicts,table):
        '''Updates the table with with the values in the supplied
        dictionaries (the keys being the column names) 
   
        Args:
            dicts (list[dict]): A list of dictionaries containing key(column name)
            to value (new value). Each dictionary should also contain an id key
            with the id of the row.
            
        Returns:
            True if the update was successful, otherwise False.
        '''
        conn = self.get_connection()
        sql=""
        complete =True
        try:
            cursor =conn.cursor()
            for item in dicts:
                id =item['id']
                del item['id']
                sql = "UPDATE {} SET (%s) = %s WHERE id= %s".format(table)
                columns = item.keys()
                values = [item[column] for column in columns]  
                cursor.execute(sql, (AsIs(','.join(columns)), tuple(values),id))
            conn.commit()
            cursor.close()
        except:
            self.app.logger.exception("update could not be run")
            conn.rollback()
            complete=False
        self.pool.putconn(conn)
        return complete
        
   
        
    def insert_dict_into_table(self,dic,table):
        conn = self.get_connection()
        try:
            cursor =conn.cursor()
       
            sql = "INSERT INTO {} (%s) VALUES %s RETURNING id".format(table)
            columns = dic.keys()
            values = [dic[column] for column in columns]  
            cursor.execute(sql, (AsIs(','.join(columns)), tuple(values)))
            conn.commit()
            new_id = cursor.fetchone()[0]
            cursor.close()
            self.pool.putconn(conn)
            return new_id
        except:
            self.app.logger.exception("update could not be run")
            self.pool.putconn(conn)
            return -1
            
        
        
        
        
        
   
   
        

        
    