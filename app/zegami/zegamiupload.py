import argparse
import io
import os
import re
import sys
from app import app,db


from app.zegami.lib import (
    api,
    run,
    auth
)



def count_dir(dir):
# counts number of files in a directory
    count = 0
    for filename in os.listdir(dir):
        full_path = dir + "/" + filename
        if os.path.isfile(full_path):
            count = count + 1
    return count

   
def get_client(credentials=None):
    '''Returns the client (bases on the settings in the app's config)'''
    info = app.config['ZEGAMI_SETTINGS']
    if not credentials:
        project=info["PROJECT"]
        username = info['USERNAME']
        password = info['PASS']
    else:
        project=credentials["project"]
        username=credentials["username"]
        password=credentials["password"]
    auth_client = auth.AuthClient(info['OAUTH_URL'])
    auth_client.set_name_pass(username,password)
    token = auth_client.get_user_token()
    if not token:
        return None
    client = api.Client(info['API_URL'], project, token)
    return client


def create_collection(name,desc,tsv_file,image_column,job=None,project=None,credentials=None):
    '''Creates a zegami collection
    Args:
        name(str): The name of the collection
        desc(str): The description of the collection
        tsv_file(str): The absolute path of the tsv file
        image_column(str): The header of the image column in the tsv file
        job (object) If supplied the job will be updated with the url
            which has the name of the image
        project(object) if supplied, the project will be updated with the url
    Returns:
        The url of the newly created collection
    '''
    info = app.config['ZEGAMI_SETTINGS']
   
    client = get_client(credentials)
    
    # create a collection with above name and description
    collection = client.create_collection(name, desc,
                                          dynamic=False)
   

    # get id of our collection's imageset and fill it with images
    imageset_id = collection["imageset_id"]
    if job:
        job.outputs=dict(job.outputs)
        job.outputs['zegami_collection_id']=collection['id']
        db.session.commit()
    if project:
        project.data["zegami_collection_id"]=collection['id']
        retuproject.update()
        
    dataset_id = collection["dataset_id"]
    with open(tsv_file) as f:
        client.upload_data(dataset_id, tsv_file, f)
        
    join_ds = client.create_join(
        "Join for " + name, imageset_id, dataset_id, join_field=image_column)
    collection['join_dataset_id'] = join_ds['id']

    # send our complete collection to zegami
    client.update_collection(collection['id'], collection)

  
    url = "https://zegami.com/collections/{}-{}".format(info['PROJECT'],collection['id'])
    return url,collection["id"]
    

def upload_images(image_dir,collection_id,job=None,project=None,from_count=0,credentials=None):
    '''Uploads images to an exisitng collection
    Args:
        image_dir(str): The full path of the directory containing the images
        collection_id(str): The id of the collection
        tsv_file(str): The absolute path of the tsv file
        job (object): optional If supplied the the job will be updated with the number of uploaded images
        project (object) optional - if supplied the project data will be updated with the number 
            of images uploaded.
        from_count (int): optional (default is 0) - The index (zero based) to start uploading 
            the images from. Used if image uploading was previously disrupted.
    Returns:
        The url of the newly created collection
    '''
    client = get_client(credentials)
    collection =client.get_collection(collection_id)
    collection=collection["collection"]
    imageset_id = collection["imageset_id"]
    count = 0
    total=count_dir(image_dir)
    for filename in os.listdir(image_dir):
        if count<from_count:
            count+=1
            continue
        full_path = image_dir + "/" + filename
        if os.path.isfile(full_path):
            print(count,")",filename)
            with open(os.path.join(image_dir, filename), 'rb') as f:
                client.upload_png(imageset_id, filename, f)
            count = count + 1
            if count%200 ==0:
                if job:
                    job.status="Uploaded {}/{} images".format(count,total)
                    job.outputs=dict(job.outputs)
                    job.outputs['images_upoaded']=count
                    db.session.commit()
                if project:
                    project.set_data("images_uploaded",count)
                    
                    

def update_collection(collection_id,upload_file):
    '''Updates the collection with the supplied file
    Args:
        collection_id(str): The id of the collection
        upload_file(str): The full path of the file containing the new information
    '''
    client = get_client()
    collection =client.get_collection(collection_id)
    dataset_id =collection['collection']['dataset_id']
    
    with open(upload_file) as f:
        client.upload_data(dataset_id, upload_file, f)
        

           
def create_new_set(collection_id,upload_file,name):
    '''Creates a new subset specified by the the supplied file
    Args:
        collection_id(str): The id of the original collection collection
        upload_file(str): The full path of the file containing a subset of the
            original collection
    Returns:
        The url of the newly created subset
    '''
    info = app.config['ZEGAMI_SETTINGS']
    
    desc="test"
    client = get_client()
    
    collection =client.get_collection(collection_id)
    
    imageset_id=collection['collection']["imageset_id"]
    new_collection = client.create_collection(name, desc,
                                          dynamic=False)
    
    new_collection['imageset_id'] = imageset_id
    client.update_collection(new_collection['id'], new_collection)
    
    dataset_id = new_collection["dataset_id"]
    with open(upload_file) as f:
        client.upload_data(dataset_id, upload_file, f)

    # join the imageset and the dataset together using the dataset join column
    join_ds = client.create_join(
        "Join for " + name, imageset_id, dataset_id, join_field="Image Name")

    # tell our collection where the join data lives
  
    new_collection['join_dataset_id'] = join_ds['id']

    # send our complete collection to zegami
    client.update_collection(new_collection['id'], new_collection)
    
    url = "https://zegami.com/collections/{}-{}".format(info['PROJECT'],new_collection['id'])
    return url

        
    
def delete_collection(collection_id):
    client =get_client()
    resp = client.delete_collection(collection_id)
    return resp.status_code==204
    
        
def get_tags(collection_id):
    client=get_client()
    return client.get_tags(collection_id)["tagRecords"]

  
    


