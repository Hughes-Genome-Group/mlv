from app import create_app,db,databases
import datetime,requests,json,os,gzip,csv,os
import click
import ujson
import requests
from pathlib import Path
from sqlalchemy import text
from app.jobs.jobs import get_job
from app.databases.user_models import UserJob
from app.jobs.jobs import get_all_jobs,delete_job,job_types
from app.ngs.project import get_project
from app.ngs.view import ViewSet
from app import databases,db
from app.databases.user_models import User

app=create_app(os.getenv("FLASK_CONFIG"),min_db_connections=0)


@app.cli.command()
@click.option("--db_name")
def create_new_genome_database(db_name="generic_gen"):
    from app.databases.man_database import create_genome_database
    create_genome_database(db_name)
    
    

@app.cli.command()
@click.option("--name")
@click.option("--label")
@click.option("--icon")
@click.option("--database")
@click.option("--connections")
def add_new_genome(name=None,label=None,icon=None,database="generic_genome",connections=5):
    from app.ngs.genome import create_genome
    #add genes
    connections = int(connections)
    create_genome(name.label,database,icon,connections)
   
    

@app.cli.command()
def find_orphan_viewsets():
    sql = "SELECT id,genome FROM projects"
    res= databases["system"].execute_query(sql)
    genomes={}
    for r in res:
        p =get_project(r["id"])
        vsid= p.get_viewset_id()
        if vsid:
            li = genomes.get(r["genome"])
            if not li:
                li=[]
                genomes[r["genome"]]=li
            li.append(vsid)
    
    for genome in genomes:
        print(genome)
        sql = "SELECT id FROM view_sets WHERE NOT (id = ANY (%s)) ORDER BY id"
        res = databases[genome].execute_query(sql,(genomes[genome],))
        for r in res:
            print(r['id'])
            
    
@app.cli.command()
@click.option("--type")
def delete_orphan_jobs(type=None):
    sql =("SELECT projects.id AS project_id, jobs.id AS job_id, jobs.type FROM jobs LEFT JOIN projects "
          "ON jobs.inputs->>'project_id'= projects.id::text WHERE jobs.inputs->>'project_id' IS NOT NULL "
          "AND projects.id IS NULL {} ORDER BY jobs.type")
    
    extra=""
    vars=None
    if type:
        extra= "AND jobs.type=%s"
        vars=(type,)
    sql=sql.format(extra)
    res = databases["system"].execute_query(sql,vars)
    for r in res:
        print(r['job_id'])
        delete_job(r["job_id"])




@app.cli.command()
@click.option("--port",default=5000)
def run_app(port=5000):
    app.run(port=port)


@app.cli.command()
@click.option("--queue",default=None)
@click.option("--threads",default=3)
def runcelery(queue=None,threads=3):
    from celery.bin.celery import main as celery_main
    #import any modules containing celery tasks or classes that have
    #not already been imported
    
   
    from app import celery,app
    from app.jobs import celery_tasks
   

  
    celery_args = ['celery', 'worker']
    if queue:
        celery_args.append('-Q%s'%queue)
    celery_args.append('--concurrency=%s'% str(threads))
    celery_main(celery_args)




@app.cli.command()   
def remove_deleted_projects():
    sql = "SELECT id FROM projects WHERE is_deleted=True ORDER BY id"
    res = databases['system'].execute_query(sql)
    for r in res:
        p=get_project(r['id'])
        p.delete(True)
        

@app.cli.command()
def test_email():
    from app.jobs.email import send_email
    from app.databases.user_models import User
    user =db.session.query(User).filter_by(id=2).one()
    send_email(user,"test","test_email",info="hello")


@app.cli.command()
def check_all_jobs():
    types = job_types.keys()
    jobs=db.session.query(UserJob).filter(UserJob.status.notin_(['complete','failed','processing']),UserJob.type.in_(types)).all()
    for j in jobs:
        try:
            job = get_job(j.id)
            job.check_status()
        except Exception as e:
            app.logger.exception("Unable to process job #{}".format(j.id))
    
    
    

@app.cli.command()
@click.option("--first_name")
@click.option("--last_name")
@click.option("--email")
@click.option("--password")
@click.option("--admin")
def find_or_create_user(first_name="", last_name="", email="", password="", admin=False):
    from app.databases.user_models import User
    """ Find existing user or create new user """
    user = User.query.filter(User.email == email).first()
    if admin == "true" or admin == "TRUE" or admin=="True":
        admin=True
    else:
        admin =False
    if not user:
        user = User(email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=app.user_manager.hash_password(password),
                    active=True,
                    confirmed_at=datetime.datetime.utcnow(),
                    administrator=admin
                )
        db.session.add(user)
        db.session.commit()
        user.add_all_create_permissions()
    return user
           
