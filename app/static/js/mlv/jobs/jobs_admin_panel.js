class JobsAdminPanel{
    constructor(table_div,filter_div,info_div,my_jobs){
    	this.my_jobs=my_jobs;
    	this.filter_div=filter_div;
        this.info_div=$("#"+info_div);
        this._setUpTable(table_div)

    }

    displayJobInfo(job_id){
    	if (my_jobs){
    		return;
    	}
        let self = this;
        $.ajax({
            url:"/meths/jobs/get_job_info/"+job_id,
            dataType:"json"
        })
        .done(data=>{
            self.info_div.jsonview(data);
        }); 
    }

    sendCommand(url,job_id){
        let self=this;
        $.ajax({
            url:url+job_id,
            dataType:"json"
        })
        .done(data=>{
            self.info_div.jsonview(data.info);
        	self.table.setValue(job_id,"status",data.status);
            
        }); 
    }
    
    _setUpFilterPanel(data){
        this.filter_panel= new FilterPanel(this.filter_div,data,(info)=>{
            this.table.data_view.setItems(info);

        });
        let width =6;
        if (!this.my_jobs){
        	width=4;
        }
     
        this.filter_panel.addChart({type:"row_chart",
        							param:"status",
        							title:"Status",
        							location:{x:0,y:0,width:width,height:6},
        							cap:15});
        this.filter_panel.addChart({type:"ring_chart",
        						   param:"job_type",
        						   title:"Job Type",
        						   location:{x:width,y:0,width:width,height:6},
        						   cap:15
        						   });
        if (!this.my_jobs){
        	this.filter_panel.addChart({type:"row_chart",
        								param:"user_name",
        								title:"User",
        								location:{x:width*2,y:0,width:width,height:6},
        								cap:20});
      
        }
        this.filter_panel.setColumns([
        	 {"field":"status","name":"Status","datatype":"text"},
             {"field":"job_type","name":"Job Type","datatype":"text"},
             {"field":"user_name","name":"User","datatype":"text"},
             {"field":"genome","name":"Genome","datatype":"text"}
        	
        ])
        this.filter_panel.addChart({
        	type:"time_line_chart",
        	param:"sent_on",
        	title:"Jobs",
        	interval:"week",
        	location:{x:0,y:6,width:12,height:4}
        })
        
    }
    
    
    _setUpTable(table_div){
        let self=this;
        let status_renderer=function(a,b,c){
            let icon =  "<i class='fa fa-spinner fa-spin'></i>";
            if (c==="failed"){
                icon = "<i class='fa fa-exclamation-triangle' style='color:red'></i>";
            }
            else if(c==="complete"){
                icon = "<i class='fas fa-check-square' style='color:green'></i>";
            }
            return icon;
        }

        let info_renderer=function(a,b,c){
            return "<i class='fa fa-info-circle' style='cursor:pointer;font-size:12px'></i>";
        }

        let action_renderer=function(a,b,c){
            if (c!=="complete"){
                return "<i class= 'fas fa-cogs' style='cursor:pointer'></i>";
            }
        }

        let columns=[
            {"field":"status","name":"","datatype":"text",id:"i1",sortable:true,formatter:status_renderer,width:40},
            {"field":"info","name":"","datatype":"text",id:"i2",sortable:true,width:30,formatter:info_renderer},
            {"field":"status","name":"","datatype":"text",id:"i3",sortable:true,width:35,formatter:action_renderer},
            {"field":"status","name":"Status","datatype":"text",id:"c1",sortable:true,width:100,filterbale:true},
            {"field":"job_type","name":"Job Type","datatype":"text",id:"c2",sortable:true,width:220},
            {"field":"user_name","name":"User","datatype":"text",id:"c3",sortable:true,filterable:true,width:150},
            {"field":"sent_on","name":"Date Sent","datatype":"date",id:"c4",sortable:true,width:180},
            {"field":"genome","name":"Genome","datatype":"text",id:"c5",sortable:true,width:80},
        ];

       
        let cm = new MLVContextMenu(function(item){
            if (item.status=="failed"){
                return [
                    {
                        text:"re-send",
                        func:function(){
                            self.sendCommand("/meths/jobs/resend_job/",item.id);
                        },
                        icon:"far fa-share-square"
                    },
                    {
                        text:"re-process",
                        func:function(){
                            self.sendCommand("/meths/jobs/reprocess_job/",item.id);
                        },
                        icon:"fas fa-cog"

                    }

                ];
            }
            if (item.status !== "complete"){
                return [
                    {
                        text:"check status",
                        func:function(){
                            self.sendCommand("/meths/jobs/check_job_status/",item.id);
                        },
                        icon:"fas fa-info"
                    },
                    {
                    	text:"kill job",
                    	func:function(){
                    		self.sendCommand("/meths/jobs/kill_job/",item.id)
                    	},
                    	icon:"fas fa-skull"
                    }
                ];
            }
        });

      
        let url="/meths/jobs/get_jobs";
        if (this.my_jobs){
        	url+="?my_jobs=true";
        }
        $.ajax({
            url:url,
            dataType:"json"
        })
        .done(data=>{
        	self._setUpFilterPanel(data);
        	let dv = new FilterPanelDataView(this.filter_panel);
            self.displayJobInfo(data[0].id);
            self.table = new MLVTable("mlv-table",columns,dv);
            dv.setItems(data);
            $(window).trigger("resize");
            self.table.addListener("row_clicked_listener",function(item,column,e){
                if (column.field === "info"){
                    self.displayJobInfo(item.id)
                }
                if (column.id ==="i3" && item.status !== "complete"){
                    cm.show(item,e);
                }
            });
            $("#"+table_div).mouseleave(function(e){
            	if (e.target.className!=="fas fa-cogs"){
            		cm._removeMenu();
            	}
            });
            self.table.grid.onScroll.subscribe(function(e, args){
                cm._removeMenu();
            });
        }); 

       

    }
}
