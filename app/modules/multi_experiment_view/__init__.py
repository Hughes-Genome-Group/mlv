from app import module_methods,app
from app.ngs.project import get_projects_summary


def get_stuff(user):
    user_id=None
    if user.is_authenticated:
        user_id=user.id
    filters={
        "type":["experiment","experiment_group","group_view","data_view"]
    }
    projects= get_projects_summary(user_id=user_id,filters=filters,limit=100,is_administrator=user.administrator,extra_fields=",projects.data AS data")
    ret_obj={
        "experiment_group":[],
        "experiment":[],
        "data_view":[],
        "group_view":[]
    }
 
    for p in projects:
        
        p["details"]=[
            ["fas fa-user-circle","Owner",p["user"]],
            ["fas fa-calendar-week","Date Added",p["date_added"]]
        ]
        
        if p["type"]=="experiment":
            p["details"]=p["details"]+\
            [
                ["fas fa-list","Size",p["data"].get("item_count")],
                ["fas fa-flask","Exp",p["data"].get("type")]        
            ]
         
       
        ret_obj[p["type"]].append(p)
        
        if p["type"]=="data_view":
            size=0
            exp_name=""
            vd =  p["data"].get("view_data")
            if vd:
                size= vd.get("size")
                exp_name=vd.get("exp_name")
                p["exp_id"]=vd.get("exp_id");
                
            p["details"]=p["details"]+\
            [
                ["fas fa-list","Size",size],
                ["fas fa-flask","Exp",exp_name]        
            ]
            
            
        
        if p["type"]=="experiment_group":
            exps=[]
            exp_info=p["data"].get("experiments")
            if exp_info:
                for item in exp_info:
                    exps.append(item.get("name"))
            size=0
            if p["data"].get("clusters"):
                size = len(p["data"]["clusters"])
            p["details"].append(["fas fa-project-diagram","Clusters",size])
            p["experiments"]=exps
        
        if p["type"]=="group_view":
            group_name = p["data"].get("group_name")
            p["details"].append(["fas fa-project-diagram","Clsuter",group_name])
            p["group_id"]=p["data"].get("group_id")
        
        del p["data"]
    return ret_obj

module_methods["multi_experiment_view"]=get_stuff