class ProjectCardDeck{
	constructor(element_id,filters,config){
		this.container=$("#"+element_id);
		if (!config){
			config={};
		}
		this.config=config;
		let self =this;
		this.limit=config.limit?config.limit:5;
		this.offset=0;
		this.filters={};
		if (filters){
			for (let key in filters){
				this.filters[key]=filters[key];
			}
			
		}
		this.filter_selects={};
		this.searchTerm="";
		this._init();
		this.loadData();
		
	}
	
		
	_init(){
	
		let self = this;
		let nav =$("<nav style='padding-top:5px;width:100%'>");
		if (!this.config.hide_navbar){
			this.addNavBar(nav);
		}
		
		let content_div = $("<div  class='tab-content row' id='nav-content-perms'></div>");
			
		
		content_div.append("<div class='card-deck' id='mlv-pro-card-deck'></div>")
		//content_div.append($("<button class='prj-more-button btn btn-sm'>More</button>").attr("id","more-project-button").hide())
		
			
		nav.append(content_div).appendTo(this.container);
		if (!this.config.hide_more_button){
			this.container.append($("<button class='prj-more-button btn btn-sm'>More</button>").attr("id","more-project-button").hide())
		}

		
		$(".prj-more-button").click(function(e){
			self.loadData(true);
		});
		
	
	}
	
	_submitSearch(){
		this.filters={};
		this.offset=0;
		for (let type in this.filter_selects){
			let val =this.filter_selects[type].val();
			if (val !== "all"){
				this.filters[type]=val;
			}
		}
		if (this.current_selected_user && this.autocomplete.val()){
			this.filters.user_id=this.current_selected_user;
		}
		
		this.search_term=$("#mlv-search").val();
		this.loadData();
		
	}
	
	
	addNavBar(nav){
		let nav_bar=$("<div class='nav nav-tabs project-nav-tab' id='nav-tab-perms-'role='tablist'>").appendTo(nav);
		this.filter_form= $("<form class='form-inline mr-auto'>").appendTo(nav_bar);
		let form= $("<form class='form-inline'>");
		form.append("<input class='form-control mr-sm-2' id ='mlv-search' type='text' placeholder='Search'>");
		let go_btn=$("<span class='btn btn-sm btn-primary'>Go</span>")
		form.append(go_btn);
		nav_bar.append(form);
		go_btn.off().click(function(e){
			self._submitSearch();
		});
		let self = this;
		$.ajax({
			 url:"/general/get_info",
			 dataType:"json",   
	    }).done(function(data){	
			self._setUpNavBar(data);
		});	
		
	}
	
	
	_setUpNavBar(data){
		let genome=this._addNavBarSelect("Genome",data.genomes,"genome");
		let type=this._addNavBarSelect("Type",data.projects,"type");
		let perms= [
			{name:"mine",label:"Mine"},
			{name:"shared",label:"Shared"},
			{name:"public",label:"Public"}
		];
		let ownership = this._addNavBarSelect("Ownership",perms,"perms");
		this.filter_form.append("<label>User:</label");
		this.filter_form.append(this._createUserSelect())
		$(".mlvil").css({"padding":"2px","height":"30px"});	
		
	}
	
	_createUserSelect(){
		let self = this;
		this.autocomplete = $("<input class='form-control mr-sm-2'>").autocomplete({
			source:"/meths/users/user_autocorrect",
			select:function(e,ui){
				self.current_selected_user=ui.item.value,
				$(this).val(ui.item.label);
				return false;
				
			}
		});
		return this.autocomplete;
	}
	
	_addNavBarSelect(title,arr,name){
		this.filter_form.append("<label>"+title+":</label");
		let select = $("<select class=' mlvil form-control'></select>");
		arr.unshift({name:"all",label:"All"});
		for (let item of arr){
	           select.append($('<option>', {
	                value: item.name,
	                text: item.label
	            }));
	    }
		
		select.appendTo(this.filter_form);
		this.filter_selects[name]=select;
		if (this.filters[name]){
			select.val(this.filters[name]);
		}
			
	}

	
	loadData(more){
		let url="/meths/get_project_information";
		let data={
			limit:this.limit,
			offset:this.offset,
			filters:this.filters,
			main_only:true,
			search_term:this.search_term
			
		};
		let self=this;
		$.ajax({
			 url:url,
			 type:"POST",
			 data:JSON.stringify(data),
			 contentType: "application/json",
			 dataType:"json",   
	        })
	        .done(function(data){
	        	if (!more){
	        		$("#mlv-pro-card-deck").empty();
	        	}
	        	self.offset+=data.projects.length;
	        	if (data.projects.length ==0 && !more){
	        		$("#mlv-pro-card-deck")
    				.append($("<div style ='margin-top:3px;width:100%' class='alert alert-warning''>There are no items in this view</div>"))
    				return;
    			}
	        	for (let project of data.projects){
	    			self.addCard(project);
	    		}	
	        	if (data.more){
    				$("#more-project-button").show();
    			}
    			else{
    				$("#more-project-button").hide();
    			}
	        	if (more){
	        		$("html").scrollTop(5000);	
	        	}
	      });		
	}
	
	
	_addHighlight(text){
		if (!text){
			return text;
		}
		let index = text.toLowerCase().indexOf(this.search_term.toLowerCase());
		if (index!==-1){
			let text1= text.substring(0,index);
			let text3=text.substring(index+this.search_term.length,text.length);
			return text1+"<span class='bg-warning'>"+this.search_term+"</span>"+text3;
		}
		return text;
	}
	
	addCard(proj){
		let deck=$("#mlv-pro-card-deck");
		
		let id =proj.id;
		//let name = proj.name;

		let self = this;
		let g= this;
		let card = $("<div id ='mlv-card-"+id+"' class='card card-mlv card-project'>").data("project",proj);
			
		card.append("<img  class='img-fluid' style='opacity:0.4' src='"+proj.large_icon+"'>");
		card.append("<div class='card-img-overlay'>"+proj.type_label+"</div>");
		let card_body=$("<div class='card-body d-flex flex-column'></div>").appendTo(card);
			
		let n=proj.name
		let desc=proj.description;
		if (this.search_term){
			n=this._addHighlight(n);
			desc=this._addHighlight(desc);
		}
		
		card_body.append("<h6 class='card-title'>"+n+"</h6>");
		
		
		card_body.append("<div class='card-text text-muted'>"+desc+"</div>");
		let list_group = $("<ul class='list-group list-group-flush mt-auto'>").appendTo(card_body);
		
		list_group.append("<li class='list-group-item'><img src='"+proj.genome_icon+"'></i>"+proj.genome+"</li>");
		list_group.append("<li class='list-group-item'><i class='fa fa-info-circle'></i>"+proj.status+"</li>");
		
		list_group.append("<li class='list-group-item'><i class='fa fa-calendar'></i>"+proj.date_added+"</li>");
		
		let name = proj.firstname+" "+proj.lastname;
		if (!proj.is_mine){
			if (proj.is_public){
				name+=" (public)";
			}
			else{
				name+=" (shared)";
			}
		}
		list_group.append("<li class='list-group-item'><i class='fa fa-user'></i>"+name+"</li>");
		
		
			
		let footer =$(" <div class='card-footer'></div>").appendTo(card);
		
		
		let url ="/projects/"+proj.type+"/"+proj.id;
		
		
		let view_but = $("<a href='"+url+"' class='btn btn-primary btn-sm'>View</a>").appendTo(footer);
		if (proj.is_mine){
			if (!proj.is_public){
				footer.append($("<i class='fa o-icon-project fa-globe pull-right align-middle' data-toggle='popover' title='make public''></i>").bstooltip()
					.click(function(e){
						makeObjectPublic(id,proj.name);
				}));
			}
			footer.append($("<i class='fa o-icon-project fa-share pull-right align-middle' data-toggle='popover' title='share'></i>").bstooltip()
					.click(function(e){
						new ShareObjectDialog(id,proj.name)
					}));
			footer.append($("<i class='fas o-icon-project fa-trash-alt pull-right align-middle' data-toggle='popover' title='delete''></i>")
					.bstooltip()
					.click(function(e){
						new DeleteObjectDialog(id,proj.name,function(){self.projectDeleted(card)});
			}));
		}
		deck.append(card)	
	}
	
	
	showDeleteDialog(){
		new DeleteObjectDialog(self.genome,id,type,function(){self.projectDeleted(card,type)});
		
	}
	
	
	
	projectDeleted(card){
		let data = card.data("project")
		this.offset--;
		card.remove();
	}
	
}


class ProjectCreatePanel{
	constructor(div_id){
		let container=$("#"+div_id)
		this.card_deck=$("<div class='card-deck' id='mlv-card-deck'></div>").appendTo(container);
		$.ajax({
            url:"/meths/get_create_projects",
            dataType:"json"
        })
        .done(data=>{
        	this._init(data);	
        });	
		
	}
	
	_init(data){
		for (let p_name in data.projects){
			let proj= data.projects[p_name];
			let card = $("<div  class='card card-mlv card-project'>");
			
			card.append("<img class='img-fluid' style='opacity:0.4' src='"+proj.large_icon+"'>");
			card.append("<div class='card-img-overlay'>"+proj.label+"</div>");
			let card_body=$("<div style= 'font-size:0.9em' class='card-body d-flex flex-column'></div>")
			.html(proj.description).appendTo(card);
			//let footer =$(" <div class='card-footer'></div>").appendTo(card);
			let url = "/projects/"+p_name+"/home";
			/*let view_but = $("<a href='"+url+"' class='btn btn-primary btn-sm'>Create</a>").appendTo(footer).data("proj",p_name);
			if ( !data.permissions[p_name]){
				view_but.attr("disabled",true)
			}*/
			card.data("url",url).click(function(e){
				window.location = $(this).data("url");
			})
		
			card.appendTo(this.card_deck);
			
		}
	}
	
	
	
}

class ShareObjectDialog{
	constructor(object_id,object_name){
		let self =  this;
	    this.object_id=object_id;
	    this.shared_users={};
	    this.div=$("<div>");
		this.div.dialog({
            autoOpen: true,
            close:()=>{
            	self.div.dialog("destroy").remove()
            },
            title: "Share "+object_name,
           
        	buttons:[
        		
        		{
        			text:"Cancel",
        			click:()=>{self.div.dialog("close")}
        		}	
        	]     
        }).dialogFix();
		this.init();	
	}
	
	
	addUser(user){
		let self = this;
		let div =$("<div>").attr("id","remove-user-"+user.uid).css("white-space","nowrap");
		let user_id= user.uid;
		this.shared_users[user.uid]=user;
		$("<span>").css({width:"150px",display:"inline-block"}).text(user.first_name+" "+user.last_name).appendTo(div);
		let del_icon = $("<i class='fas fa-trash'></i>")
		.css("margin-left","3px")
		.click(()=>{
			self.removeUser(user_id);
			
		});
		let perm_type=$("<select>").css("margin-left","3px")
		.data("uid",user.uid)
		.append("<option>view</option>").append("<option>edit</option>")
		.val(user.level)
		perm_type.on("change",function(){
			self.updatePermissionType($(this).data("uid"),$(this).val())
		})
		div.append(perm_type)
		div.append(del_icon);
		this.div.append(div);	
	}
	
	updatePermissionType(uid,permission){
		 $.ajax({
			 url:"/meths/update_permission_type_for_object/"+this.object_id+"/"+uid+"/"+permission,
	         dataType:"json"
	     })
	     .done(data=>{      	
	     });	
		
		
	}
	
	removeUser(user_id){
		let self = this;
		 $.ajax({
	            url:"/meths/unshare_object_with/"+this.object_id+"/"+user_id,
	            dataType:"json"
	        })
	        .done(data=>{
	        	delete self.shared_users[user_id]
	        	$("#remove-user-"+user_id).remove();        	
	        });	
	}
	
	init(){
		let self = this;
		this.autocomplete = $("<input>").attr({placeholder:"enter user name"})
				.css("z-index",10000).autocomplete({
			source:"/meths/users/user_autocorrect",
			select:function(e,ui){
				
				let arr = ui.item.label.split(" ");
				self.current_selected_user={
						"uid":ui.item.value,
						"first_name":arr[0],
						"last_name":arr[1],
						"level":"view"
				}
				self.autocomplete.val(ui.item.label);
				return false;
				
			}
		});
		let but = $("<button>").attr("class","btn btn-sm btn-primary").text("Add").click(function(e){
			if (self.current_selected_user && !self.shared_users[self.current_selected_user.uid]){
				 $.ajax({
			            url:"/meths/share_object_with/"+self.object_id+"/"+self.current_selected_user.uid,
			            dataType:"json"
			        })
			        .done(data=>{
			        	self.addUser(self.current_selected_user);
			        	self.current_selected_user=null;
			        	self.autocomplete.val("");
			        });
				
			}
		});
		
		this.div.append(this.autocomplete)
		this.div.append(but);
		let dd= $("<div>").css("white-space","nowrap").appendTo(this.div);
		dd.append("<br><label style='font-weight:bold;display:inline-block;width:150px'>Shared With:</label>");
		dd.append("<label style='inline-block;font-weight:bold;'>Pemission</label>");
		 $.ajax({
	            url:"/meths/get_shared_details_for_object/"+this.object_id,
	            dataType:"json"
	        })
	        .done(data=>{
	        	self.users=data;
	        	for (let user of data){
	        		self.addUser(user)
	        	}	           
	      });		
	}
}

function makeObjectPublic(id,name){
	 $.ajax({
         url:"/meths/make_object_public/"+id,
         dataType:"json"
     })
     .done(data=>{
     	let d = $("<div>");
     	let text=data,msg
     	if (data.success){
     	 text=name +" was made public, you can share it with the following link<br>"+data.url
     	}
     	d.html(text);
     	d.dialog({
             autoOpen: true,
             width:400,
             close:()=>{
             	d.dialog("destroy").remove()
             },
             title: "Make "+name+" public",
            
         	buttons:[
         		{
         			text:"OK",
         			click:()=>{d.dialog("close")}
         		}	
         	]     
         }).dialogFix();
     });	
}


class DeleteObjectDialog{
	constructor(project_id,name,callback){
	    let self=this;
        this.div = $("<div>").text("Are you sure you want to delete the project "+name+"?");
        this.project_id=project_id;
        this.callback=callback;
        this.is_done=false;
        
        
      
        this.div.dialog({
            autoOpen: true,
            close:()=>{
            	self.div.dialog("destroy").remove()
            },
            title: "Delete "+name,
            dialogClass: "error",
        	buttons:[
        		{
        			text:"OK",
        			click:()=>{
        				if (self.is_done){
        					self.div.dialog("close")
        				}
        				else{
        					self.deleteItem();
        				}
        			}
        		
        		},
        		{
        			text:"Cancel",
        			click:()=>{self.div.dialog("close")}
        		}
        	
        	]
          
        }).dialogFix();
       
       
	}
	deleteItem(){
		let self = this;
		 $.ajax({
	            url:"/meths/delete_object/"+this.project_id,
	            dataType:"json"
	        })
	        .done(data=>{
	        	self.is_done=true;
	            if (data.success){
	            	this.div.text("The Project was deleted sucessfully");
	            	 if (self.callback){
	 	            	self.callback()
	 	            }
	            }
	            else{
	            	this.div.text("There was a problem and the Project could not be deleted");
	            }
	           
	      });
	}
	
}
