class UsersAdminPanel{
    constructor(table_div,filter_div,info_div){
    	let self =this;
    	this.filter_div=filter_div;
        this.info_div=$("#"+info_div);
        this.setUpTable(table_div);
        
        let dv = $("#"+this.filter_div);
        dv.append($("<button>").attr("class","btn btn-primary btn-sm")
        	.text("Remove Deleted Projects")
        	.click(function(e){
        		self.removeDeletedProjects();
        	}));

    }
    
    deletePermission(id,div){
    	$.ajax({
   	 		url:"/meths/users/delete_user_permission/"+id,
   	 		dataType:"json"
    	}).done(data=>{
    		div.remove();
    	});
    	
    }
    
    removeDeletedProjects(){
    	$.ajax({
   	 		url:"/meths/remove_deleted_projects",
   	 		dataType:"json"
   	 	})
    	
    }
    
    
    addPermission(div,item){
    	let self = this;
    	let d = $("<div>").css({"margin-right":"5px"});
		d.append("<span style='display:inline-block;width:200px;margin-right:5px;'>"+item.permission+"</span>");
		d.append("<span style='display:inline-block;width:150px;margin-right:5px;'>"+item.value+"</span>");
		$("<i class='fas fa-trash' style='cursor:pointer'></i>").click(function(e){
			self.deletePermission($(this).data("perm_id"),$(this).parent());
		
		}).appendTo(d).data("perm_id",item.id);
		d.appendTo(div);
    	
    }
    
    
    addPermissionToDB(perm,val,user_id,div){
    	let self=this;
   	 	$.ajax({
   	 		url:"/meths/users/add_user_permission/"+user_id,
   	 		dataType:"json",
   	 		method:"POST",
   	 		data:{
   	 			perm:perm,
   	 			val:val,
   	 		}		
   	 	}).done(data=>{
   	 		let item={
   	 			permission:perm,
   	 			value:val,
   	 			id:data.id
   	 				
   	 		};
   	 		self.addPermission(div,item)
   	 	}); 	 		
   	}

   
    
    displayPermissions(user){
    	let self=this;
    	let div=$("<div>");
    	let perm_div=$("<div>").appendTo(div);
    	div.dialog({
			autoOpen: true,
		    title:user.name + " Permissions",
		    close:function(){
		    	$(this).dialog('destroy').remove()
		    },
		    width:500,
		    buttons:[{
		    	text:"OK",
		        click:function(){
		        	$(this).dialog("close");
		        }
		     }]  
		}).dialogFix();
    	 $.ajax({
              url:"/meths/users/get_all_user_permissions/"+user.id,
              dataType:"json"
          })
          .done(data=>{
        	 for (let item of data){
        		this.addPermission(perm_div,item);
        	 }
        	 let d= $("<div>").appendTo(div);
        	 let perm_input =  $("<input>").css({width:"200px","margin-right":"5px"}).appendTo(d);
        	 let val_input = $("<input>").css({width:"150px","margin-right":"5px"}).appendTo(d);
        	 $("<i class='fas fa-plus' style='cursor:pointer'></i>").click(function(e){
        		 let t= $(this);
        		 let val =t.data("val").val();
        		 let perm = t.data("perm").val();
        		 if (val && perm){
        			 self.addPermissionToDB(perm,val,user.id,perm_div);
        			 t.data("val").val("");
        			 t.data("perm").val("");
        		 }      		 
        	 }).data({perm:perm_input,val:val_input}).appendTo(d);       
          }); 
    	
    	
    }
    
    
    setUpTable(table_div){
        let self=this;
        let permissions_formatter=function(a,b,c){
            return "<i class='fas fa-lock-open'></i>";
        }

       

        let columns=[
            {field:"name",name:"User",datatype:"text",id:"name",sortable:true,filterable:true,width:100},
            {field:"institution",name:"Institution",datatype:"text",id:"institution",sortable:true,filterable:true,width:150},
            {field:"email",name:"Email",datatype:"text",id:"email",sortable:true,filterbale:true,width:150},
            {field:"project_num",name:"Project Number",datatype:"text",id:"project_num",sortable:true,width:100,filterbale:true},
            {field:"perm",name:"Permissions",datatype:"text",id:"permissions",formatter:permissions_formatter,width:80}
        ];

      
        $.ajax({
            url:"/meths/users/get_user_data",
            dataType:"json"
        })
        .done(data=>{  	    
            self.table = new MLVTable("mlv-table",columns);
            self.table.data_view.setItems(data);
            $(window).trigger("resize");
            self.table.addListener("row_clicked_listener",function(item,column,e){
                if (column.field === "perm"){
                    self.displayPermissions(item);
                }
            });
        
        }); 
    }
}