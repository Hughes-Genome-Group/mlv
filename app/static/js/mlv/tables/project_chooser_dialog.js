class ProjectChooserDialog{
    constructor(project_type,title,database,button_text,options){
    	if (!button_text){
    		button_text="Add"
    	}
    	
    	if (!options){
    		options={};
    	}
    	
    	this.options=options;
    	


    	this.database=database;
        this.project_type=project_type
        var self=this;
        this.count =ProjectChooserDialog.count;
        ProjectChooserDialog.count++;
        this.div = $("<div>");
        let buttons=[
            {
                text:"Cancel",
                click:()=>{this.div.dialog("close")}
            },
            {
                text:button_text,
                click:()=>{
                    this.callback(this.table.getSelectedItems());
                    this.div.dialog("close")
                }
            }
        ];
        this.div.dialog({
            autoOpen: false, 
            buttons:buttons,
            title:title,
            width:600,
            height:400
        }).dialogFix();
     
        this._addTable();
        this.has_data=false;
      
    }

    _addTable(){	
        this.table_div=$("<div>").attr("id","pc-table-"+this.count).css({position:"absolute",top:"5px",bottom:"5px",right:"5px",left:"5px"});
        this.div.append(this.table_div);
        let url="/meths/get_project_columns_for_type/"+this.project_type;
        //legacy
        if (this.config){
        	url=this.config.column_url;
        }
        $.ajax({
            url:url,
            dataType:"json"
        })
        .done(columns=>{
        	if (this.options.show_types){
        		columns.push({
        			field:"type_label",
        			id:"type_label",
        			name:"Type",
        			filterable:true,
        			sortable:true
        		})
        	}
            this.table = new MLVTable("pc-table-"+this.count,columns);
        });
    }
    


    show(callback){
        this.callback=callback;
        if (this.has_data){
            this.div.dialog("open");
        }
        else{
            this._loadData(true);
            
        }     
    }

    _loadData(auto_open){
        this.has_data=true;
        let url="/meths/get_project_information";
        let to_send={
        		filters:{
        			type:this.project_type
        		},
        		offset:0,
        		limit:100000
        };
        if (this.database){
        	to_send.filters.genome=this.database;
        }
        $.ajax({
            url:url,
            dataType:"json",
            type:"POST",
            data:JSON.stringify(to_send),
            contentType:"application/json"
        })
        .done(data=>{
            this.table.data_view.setItems(data.projects);
            if (auto_open){
            	this.div.dialog("open");
            }
            this.table.resize();
        });
    }
}

ProjectChooserDialog.count=0;


class ProjectManagementTable{
	constructor(div,project_type){
		this.project_type=project_type;
		this._addTable(div);
		
	}
	
	_loadData(){
		
		  let url="/meths/get_project_information";
	      let to_send={
	        		filters:{
	        			type:this.project_type,
	        			perms:"mine"
	        		},
	        		offset:0,
	        		limit:100000
	        };
	        $.ajax({
	            url:url,
	            dataType:"json",
	            type:"POST",
	            data:JSON.stringify(to_send),
	            contentType:"application/json"
	        })
	        .done(data=>{
	            this.table.data_view.setItems(data.projects);
	 		   this.table.resize();
	        });
		
		
	}
	
    refresh(){
    	this._loadData();
    }
    
    setViewFunction(func){
    	this.view_function=func;
    }
	
	
	
	_addTable(div){
		let self =this;
		   let columns=[
	            {"field":"name","name":"Name","datatype":"text",id:"name",sortable:true,width:150},
	            {"field":"status","name":"Status","datatype":"text",id:"status",sortable:true,width:100},
	            {"field":"genome","name":"Genome","datatype":"text",id:"status",sortable:true,width:100},	           
	            {"field":"date_added",name:"Date Added",datatype:"date",sortable:true,width:100},
	            {"field":"view","name":"","datatype":"text",id:"share",sortable:false,width:40,
	            	formatter:()=>{
		            	return "<i class='fa fa-eye'></i>"
	            	}
	            },
	            {"field":"public","name":"","datatype":"text",id:"public",sortable:false,width:35,
	            	formatter:()=>{
	            		return "<i class='fa fa-globe'></i>";
	            		
	            	}
	            },
	            {"field":"share","name":"","datatype":"text",id:"share",sortable:false,width:35,
	            	formatter:()=>{
		            	return "<i class='fa fa-share'></i>"
	            	}
	            },
	            {"field":"delete","name":"","datatype":"text",id:"delete",sortable:false,width:35,
	            	formatter:()=>{
	            		return "<i class='fas fa-trash'></i>"
	            	}
				},
	            {"field":"description","name":"Description","datatype":"text",id:"c3",sortable:true,width:300}
	        ];
		   this.table=new MLVTable(div,columns);
		   this.table.addListener("row_clicked_listener",function(item,column,e){
	            if (column.field === "share"){
	                new ShareObjectDialog(item.id,item.name)
	            }
	            if (column.field === "public" && item.status === "complete"){
	                makeObjectPublic(item.id,item.name)
	            }
	            if (column.field==="delete"){
	            	new DeleteObjectDialog(item.id,item.name,function(){
	            		self.table.data_view.deleteItem(item.id);
	            	})
	            }
	            if (column.field==="view"){
	            	if (self.view_function){
	            		self.view_function(item);
	            	}
	            	else{
	            		window.location="/project/"+self.project_type+"/"+item.id;
	            	}
	            	
	            }
	        });
		   
		   this._loadData();
		   
	}
	
}


//obsolete
class MLVTableDialog{
    constructor(config){
        this.config=config;
        var self=this;
        this.div = $("<div>");
        let buttons=[
            {
                text:"Cancel",
                click:()=>{this.div.dialog("close")}
            },
            {
                text:"Add",
                click:()=>{
                    this.callback(this.table.getSelectedItems());
                    this.div.dialog("close")
                }
            }
        ];
        if (config.add_form){
            buttons.unshift({
                text:"New",
                click:()=>{
                    this.table_div.hide();
                    this.form_div.show();
                }
            })
        }

     

        this.div.dialog({
            autoOpen: false, 
            buttons:buttons,
            title:this.config.title,
            width:600,
            height:400
        }).dialogFix();
       //$('.ui-button').css({"background-color":"#007bff !important"});
       //$('.ui-button-text').css({"color":"white"});
        this._addTable();
        this.has_data=false;
        if (config.add_form){
            this._addForm();
        }
        
    }

    _addTable(){
        this.table_div=$("<div>").attr("id",this.config.table_name).css({position:"absolute",top:"5px",bottom:"5px",right:"5px",left:"5px"});
        this.div.append(this.table_div);
        this.data_view=new MLVDataView();
        
        $.ajax({
            url:this.config.column_url,
            dataType:"json"
        })
        .done(columns=>{
            let count=0;
            for (let column of columns){
                column.id="col"+count;
                column.sortable=true;
                count++;
            }
            this.table = new MLVTable(this.config.table_name,columns,this.data_view);
        });
    }

    _newItemAdded(data){
        this.form_div.hide();
        this.table_div.show();
        this.data_view.addItem(data);
        let row = this.data_view.getRowById(data.id);
        this.table.scrollRowIntoView(row);
        this.table.setSelectedRows([row])
    }

    _addForm(){
        this.form_div=$("<div>").attr("id",this.config.table_name+"-form-div");
        this.div.append(this.form_div); 
        this.input_form = new BaseInputForm(this.config.table_name+"-form-div",
                                            this.config.add_form.inputs_url,
                                            this.config.add_form.submit_url,
                                            data=>{
                                                this._newItemAdded(data);
                                            },
                                           ()=>{
                                                this.form_div.hide();
                                                this.table_div.show();
                                            }
                                            );
        this.form_div.hide();  
    }


    show(callback){
        this.callback=callback
        if (this.has_data){
            this.div.dialog("open");
        }
        else{
            this._loadData();
            
        }
        
        
        
    }

    _loadData(){
        this.has_data=true;
        $.ajax({
            url:this.config.data_url,
            dataType:"json"
        })
        .done(data=>{
            this.data_view.setItems(data);
            this.div.dialog("open");
            this.table.resize();
        });
    }
  
}
