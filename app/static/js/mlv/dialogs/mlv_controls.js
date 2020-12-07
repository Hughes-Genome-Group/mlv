class MLVDialog{
	constructor(msg,config){
		if (!config){
			config={};
		}
		if (!config.type){
			config.type="information"
		}
		if (!config.mode){
			config.mode="ok";
		}
		if (config.close_on_ok===undefined){
			config.close_on_ok=true;
		}
		this.callback=config.callback;
		this.div=$("<div>");
		let self =this
		let buttons=[{
				text:"OK",
				click:function (e){
					if (self.callback){
						self.callback(true)
					}
					if (config.close_on_ok){
						self.div.dialog("close");
					}
				}
		}];
		if (config.mode==="ok_cancel"){
			buttons.unshift({
				text:"Cancel",
				click:function (e){
					if (self.callback){
						self.callback(false)
					}
					self.div.dialog("close");
				
			
			}

			});
		}
		let i = MLVDialog.types[config.type];
		let title= config.title?config.title:i.title;
		if (typeof msg === "string"){
			this.div.html(msg).css("font-size","14px");
		}
		else{
			this.div.append(msg)
		}
		
		this.div.dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:title,
			buttons:buttons,
			width:config.width?config.width:300
		}).dialogFix();
	
		let tb = this.div.parent().find(".ui-dialog-titlebar");
		tb.css({"background-color":i.colors[0],"border-color":i.colors[1]});
		let icon =$(`<i class='${i.icon}'></i>`)
			.css({"float":"left","margin-top":"4px","font-size":"18px"});
		tb.prepend(icon);
	}
	
	setMessage(msg){
		this.div.html(msg);
	}
	
	showMessage(msg){
		this.div.html(msg);
	}
	
	close(){
		this.div.dialog("close");
	}
}

MLVDialog.types={
	warning:{
		icon:"fas fa-exclamation-triangle",
		colors:["#fcf8e3","#faf2cc"],
		title:"Warning"
	},
	information:{
		icon:"fas fa-info-circle",
		colors:["#d9edf7","#bcdff1"],
		title:"Information"
	},
	success:{
		icon:"fas fa-check-circle",
		colors:["#dff0d8","#d0e9c6"],
		title:"Success"
	},
	danger:{
		icon:"fas fa-times-circle",
		colors:["#f2dede","#ebcccc"],
		title:"Error"
	},
	enter_details:{
		icon:"fas fa-sign-in-alt",
		colors:["#cce5ff","#b8daff"],
		title:"Enter Details"
		
	}

}

class MLVColumnCheck{
	constructor(div,columns,filter,msg){
		this.columns=columns;
		this.calculateGroups(columns,filter);
		
		if (!msg){
			msg = "Columns To Include"
		}
		if (msg !=="none"){
			div.append($("<label>").text(msg));
		}
		for (let name of this.group_names){
			div.append("<div><label>"+name +"</label></div>");
			let col_div=$("<div>").appendTo(div);
			
			let li = this.groups[name];
			for (let col of li){
				let parent =$("<div class='form-check form-check-inline'></div>");
				let id = "cluster-field-"+col.field;
				let check = $("<input>").attr({
					"class":"form-check-input",
					type:"checkbox",
					id:id
				}).data("field",col.field);
				let label = $("<span>").attr({
					"for":id
					}).text(col.name)
					parent.append(check).append(label).appendTo(col_div);
			}
		}
		
	}
	
	getCheckedColumns(){
		let ch_li=[];
		for (let c of this.columns){
			if ($("#cluster-field-"+c.field).prop("checked")){
				ch_li.push(c.field)
			}
		}
		return ch_li;
	}
	
	calculateGroups(columns,filter){
		let groups={};
		let group_list= [];
		groups["Other"]=[]
		
		for (let c of columns){
			if (filter && filter === "number"){
				if (c.datatype !=="integer" && c.datatype !== "double"){
					continue;s
				}
			}
			if (c.columnGroup){
				let li = groups[c.columnGroup]
				if (!li){
					li=[];
					group_list.push(c.columnGroup)
					groups[c.columnGroup]=li
				}
				li.push(c)
			}
			else{
				groups["Other"].push(c)
			}
		}
		for (let g in groups){
			let li = groups[g];
			li.sort(function(a,b){
				return a.name.localeCompare(b.name)
			})
		}
		group_list.sort(function(a,b){
			return a.localeCompare(b);
		
		});
		group_list.push("Other")
		this.groups=groups;
		this.group_names=group_list;
	}
	
	
}

class MLVClusterDialog{
	
	constructor(app,filter){
		this.app=app;
		this.div = $("<div>");
		let self = this;
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Select Columns and Method(s)",
    		autoOpen:true,
    		width:600,
    		position:{my:"center top",at:"center top"},
    		buttons:[
    			{
    				text:"Submit",
    				click:function(){				
    					self.submit();		
    				},
    				id:"ucsc-images-submit-btn"
    			},
    			{
    				text:"Cancel",
    				click:function(){
    					$(this).dialog("close");
    				}
    			},
    			
    		]
    	
    	}).dialogFix();
		this.message = $("<div class='alert'></div>").appendTo(this.div).hide();
		let d= $("<div style='margin-bottom:3px'></div>").appendTo(this.div)
		d.append("<label>Name of Analysis:</label>");
		this.name_input = $("<input type='text'>").css({"width":"200px","margin-left":"5px"})
			.appendTo(d);
		d.append($("<label>Methods:</label>").css({"margin-left":"5px"}));
		this.method_radios= {};
		for (let cl of ["UMAP","tSNE"]){		
			let t = $("<input>").attr({"type":"checkbox"}).css("margin-left","4px");
			if (cl==="UMAP"){
				t.attr("checked",true)
			}
			this.method_radios[cl]=t;
			d.append(t).append($("<span>").text(cl))
			
		}
		d.append($("<label>Number of Dimensions:</label>").css({"margin-left":"5px"}));
		this.dimensions_select=$("<select>").appendTo(d);
		for (let n=2;n<6;n++){
			this.dimensions_select.append($("<option>").text(n).attr("value",n));
		}
		
	
		
		let col_div =$("<div>").appendTo(this.div);
		this.col_chooser = new MLVColumnCheck(col_div,app.columns,filter)
		
	}
	
	submit(){
		
		let fields= this.col_chooser.getCheckedColumns();
		if (fields.length<3){
			this.msg.html("Please select more than 1 column ");
			return;
		}
		let self = this;
		let methods=[];
		for (let m in this.method_radios){
			if (this.method_radios[m].prop("checked")){
				methods.push(m)
			}
		}
		let data=
				{
					fields:fields,
					name:this.name_input.val(),
					methods:methods,
					dimensions:parseInt(this.dimensions_select.val())
					
				}
		this.app.initiateJob("cluster_by_fields_job",data);
		this.div.dialog("close");
		
		
	}
}


class MLVProjectInfoDialog{
	constructor(name,description,genome_info){
		
		this.div = $("<div>");
		let self = this;
		
		this.addSection("Name",name);
		this.addSection("Description",description);
		this.addSection("Genome",genome_info.label);
		this.addSection("Build",genome_info.build);
		this.addSection("Gene Annotation",genome_info.gene_description);
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Project Information",
    		autoOpen:true,
    		
    		position:{my:"center top",at:"center top"},
    		buttons:[    			
    			{
    				text:"OK",
    				click:function(){
    					$(this).dialog("close");
    				}
    			},
    			
    		]
    	
    	}).dialogFix();
		
		
	}
	
	addSection(title,content){
		this.div.append(`<div><label>${title}</label></div>`);
		this.div.append($("<div>").html(content));
	}
	
}


class DeleteColumnsDialog{
	
	constructor(app){
		this.app=app;
		this.div = $("<div>");
		let self = this;
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Delete Columns",
    		autoOpen:true,
    		width:600,
    		position:{my:"center top",at:"center top"},
    		buttons:[
    			{
    				text:"Delete",
    				click:function(){				
    					self.submit();		
    				},
    				id:"delete-columns-submit"
    			},
    			{
    				text:"Cancel",
    				click:function(){
    					$(this).dialog("close");
    				}
    			},
    			
    		]
    	
    	}).dialogFix();
		
		
	
	
		
		let col_div =$("<div>").appendTo(this.div);
		this.col_chooser = new MLVColumnCheck(col_div,app.columns,null,"Columns To Delete");
		this.message = $("<div class='alert alert-warning'>All data associated with deleted columns will be romved and cannot be undone</div>")
			.appendTo(this.div);
		
	}
	
	submit(){
		
		let self = this;
		let fields = this.col_chooser.getCheckedColumns();
		let data={
				columns: fields
		}
		$("#delete-columns-submit").attr("disabled",true);
		this.app.sendAction("delete_columns",data).done(function(response){
			if (response.success){
				self.message.removeClass("alert-warning").addClass("alert-success").html("The columns have been successfully removed").show();
				self.app.removeColumns(fields);
				if (response.data.history){
					self.app.history=response.data.history;
					if (self.app.history_dialog){
						self.app.history_dialog.refesh();
					}
				}
			}
			else{
				self.message.removeClass("alert-warning").addClass("alert-danger").html(response.msg).show();
				
			}
			
			
		});
		
	}
}

class CreateUCSCImages{
	constructor(app){
		this.app=app
		this.browser=app.browser;
		this.table=app.table;
		this.project_id=app.project_id;
		this.div=$("<div>");
		this.type= "mlv";
		let self =this;
		let d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div);
		let rb = $("<input>")
			.attr({name:"mlv-pic-type",type:"radio",value:"mlv",checked:true})
			.click(function(e){
				self.session_input.attr("disabled",true);
				self.type="mlv";
			})
		d.append(rb).append("<label>MLV - based on the browser</label><br>");
		
		
		
		rb = $("<input>")
			.attr({name:"mlv-pic-type",type:"radio",value:"ucsc"})
			.click(function(e){
				self.session_input.attr("disabled",false);
				self.type="ucsc"
			})
		this.ucsc_radio=rb;
		d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div);
		d.append(rb).append("<label>UCSC -Add a session URL</label><br>");
		this.session_input = $("<input type='text' class='form-control'>")
			.attr("disabled",true)
			.appendTo(d);
		
		
		d= $("<div style='margin-bottom:10px;white-space:nowrap'></div>").appendTo(this.div);
		d.append("<label>Margin Width(bp)</label>");
		this.margin_input = $("<input class='mlv-form-spinner' type='text'>")
		.appendTo(d);
		
		
		d.append("<label>Image Width (px)</label>");
		this.width_input =$("<input class ='mlv-form-spinner' type='text'></input>")
			.appendTo(d);
		
		d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div);
		this.preview_button = $("<button class='btn btn-sm btn-secondary'>Preview</button>").click(function(e){
			if (self.type === "ucsc"){
				self.previewUCSC();
			}
			else{
				self.previewMLV();
			}
			
		}).appendTo(d);
		d= $("<div style='height:300px;position:relative;margin-bottom:10px;overflow:auto;'></div>").appendTo(this.div);
		this.preview_image=$("<img>").appendTo(d).hide();
		this.image_spinner= $("<i class='fas fa-spinner fa-spin' style='font-size:30px;position:absolute;top:140px;left:250px;'></i>").appendTo(d).hide();
		let msg = "The image could not be retrieved. Make sure the url is correct"
		this.error_message = $("<div class='alert alert-warning'>"+msg+"</div>").appendTo(d).hide();
		
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Create UCSC Images",
    		autoOpen:true,
    		width:600,
    		position:{my:"center top",at:"center top"},
    		buttons:[
    			{
    				text:"Submit",
    				click:function(){
    					if (self.type==="ucsc"){
    						self.submitUCSC();
    					}
    					else{
    						self.submitMLV()
    					}
    					
    				},
    				id:"ucsc-images-submit-btn"
    			},
    			{
    				text:"Cancel",
    				click:function(){
    					$(this).dialog("close");
    				}
    			},
    			
    		]
    	
    	}).dialogFix();
		
		this.margin_input.val("1000").spinner({
			min:0,
			max:10000,
			step:500
		});
		this.width_input.val("500").spinner({
			min:100,
			max:1000,
			step:100
		});
		$(".mlv-form-spinner").css({
			width:"50px"
				
		});
		$("#ucsc-images-submit-btn").attr("disabled",true);
		$(".ui-spinner").css({"margin-right":"12px","margin-left":"3px"})
		this.checkPermission();
		
	}
	
	checkPermission(){
		let self = this;
		$.ajax({
			url:"/meths/users/has_permission/ucsc_create_images",
			dataType:"json"
			
		}).done(function(response){
			if (!response.permission){
				self.div.find("input").attr("disabled",true);
				self.error_message.html("If you want to create images from UCSC, please ask an administrator").show();
				self.ucsc_radio.attr("disabled",true)
			}
		})
		
	}
	
	
	submitMLV(){		
		let data={	
			tracks:this.browser.panel.getAllTrackConfigs(),
			margins:parseInt(this.margin_input.val()),
			image_width:parseInt(this.width_input.val())

		}
		this.app.initiateJob("mlv_images_job",data);
		
	}
	
	
	
	showSuccess(job_id){
		this.preview_image.hide()
		this.preview_button.attr("disabled",true);
		$("#ucsc-images-submit-btn").attr("disabled",true);
		this.error_message.removeClass("alert-danger")
			.addClass("alert-success")
			.html("The images are bing created - you will get an email when they are complete. You can follow the progress in my jobs.")
			.show();
		if (this.callback){
			this.callback(job_id);
		}
	}
	
	
	
	submitUCSC(){
		let self =this;
		let data={
				method:"make_ucsc_images",
				args:{
					session_url:this.session_input.val(),
					margins:parseInt(this.margin_input.val()),
					image_width:parseInt(this.width_input.val())
					
				}
		}
		$.ajax({
			url:"/meths/execute_project_action/"+this.project_id,
			type:"POST",
			data:JSON.stringify(data),
			dataType:"json",
			contentType:"application/json"
		}).done(function(response){
			if (response.success){
				self.showSuccess(response.data);
			}
			else{
				self.error_message.html(response.msg).show();
			}
			
		})
		
	}
	getLocation(){
		let row = this.table.grid.getSelectedRows()[0];
		if (!row){
			row =0;
		}
		let item =this.table.data_view.getItem(row);
		return {
			chr:item.chromosome,
			start:item.start,
			end:item.finish	
		}
		
	}
	
	setCallback(callback){
		this.callback=callback;
	}
	
	previewMLV(){
		let loc = this.getLocation()
		let margin = parseInt(this.margin_input.val());
		loc.start-=margin;
		loc.end+=margin;
		let data={
				tracks:this.browser.panel.getAllTrackConfigs(),
				width:this.width_input.val(),
				height:300,
				type:"png",
				position:loc,
				
		}
		this.preview_image.hide();
		this.error_message.hide();

		this.image_spinner.show();
		$("#ucsc-images-submit-btn").attr("disabled",true);
		let self = this;
		$.ajax({
			url:"/meths/create_track_image",
			contentType:"application/json",
			type:"POST",		
			data:JSON.stringify(data)
		}).done(function(url){
			self.image_spinner.hide();
			self.preview_image.attr("src",url).show();
			$("#ucsc-images-submit-btn").attr("disabled",false);
		});
			
		
	}
	
	
	previewUCSC(){
		let url = this.session_input.val();
		let margin = parseInt(this.margin_input.val());
		url=url.replace("hgTracks","hgRenderTracks");
		if (url.includes("/s/")){
			let arr=url.split("/");
			url= arr[0]+"//"+arr[2]+"/cgi-bin/hgRenderTracks?hgS_doOtherUser=submit&hgS_otherUserName="+arr[4]
			+"&hgS_otherUserSessionName="+arr[5];
		}
		let loc = this.getLocation();
		let args ="&position="+loc.chr+"%3A"+(loc.start-margin)+
				"-"+(loc.end+margin)+"&pix="+(this.width_input.val());
		let image = new Image();
		let self = this;
		this.preview_image.hide();
		this.error_message.hide();
		$("#ucsc-images-submit-btn").attr("disabled",true);
		image.onload = function () {
			self.image_spinner.hide();
			self.preview_image.attr("src",image.src).show();
			$("#ucsc-images-submit-btn").attr("disabled",false);
		};
		image.onerror=function(e){
			self.image_spinner.hide();
			self.error_message.show();
		}
		console.log(url+args);
		this.preview_image.hide();
		this.image_spinner.show();

		image.src =url+args;
	
	}
}


class CreateCompoundColumn{
	constructor(app){
		this.div=$("<div>");
		this.app=app;
		this.div.dialog({
			autoOpen:true,
			title:"Create Column",
			width:450,
			buttons:[
				{
					text:"Cancel",
					click:()=>{this.div.dialog("close")}
				},
				{
					text:"Create",
					click:()=>{this.submit()},
					id:"create-column-but"
				}
			],
			close:()=>{this.div.dialog("destroy").remove()}
		}).dialogFix();
		this.div.append("<label>Column Name</label>");
		this.name_input = $("<input type='text' class='form-control'>")
			.appendTo(this.div);
		let div =this.getDiv().appendTo(this.div);
		div.append("<label style='width:100px'>Field1</label>");
		
		
		this.field1= this.getSelect().appendTo(div);
		
	
		this.operand=$("<select>").append(this.getOption("log2 fold change","log_change"))
		                           .append(this.getOption("/","/"))
								   .append(this.getOption("*","*"))
								    .append(this.getOption("+","+"))
								    .append(this.getOption("-","-"));
		div =this.getDiv().appendTo(this.div);
		div.append("<label style='width:100px'>Operand</label>");
		div.append(this.operand);
		div =this.getDiv().appendTo(this.div);
		div.append("<label style='width:100px'>Field2</label>");
		this.field2= this.getSelect().appendTo(div);
		this.message = $("<div class='alert alert-warning'>The column is being generated </div>").hide()
		.appendTo(this.div);
		
		
	}
	
	getSelect(){
		let select= $("<select>").css("max-width","300px");
		 for (let column of this.app.columns){
			  if (column.datatype!=="integer" && column.datatype!=="double"){
				  continue;
			  }
			  select.append($('<option>',{
				  value:column.field,
				  text:column.name
			  }));
		  }
		return select;
	}
	
	submit(){
		let self = this;
		let args= {
				"field1":this.field1.val(),
				"field2":this.field2.val(),
				"operand":this.operand.val(),
				"name":this.name_input.val()
		}
		$("#create-column-but").attr("disabled",true);
		this.message.show();
		this.app.sendAction("create_compound_column",args).done(function(resp){
			if (resp.success){
				self.message.removeClass("alert-warning").addClass("alert-success").text("The column has been created")
				self.app._addDataToView(resp.data);
			}
			else{
				self.message.removeClass("alert-warning").addClass("alert-danger").text("There was a problem, please contact an adminisrator");
			}
		})
		
	}
	
	getDiv(){
		return $("<div>").css({"display":"inline-block","margin-right":"3px"});
	}
	
	getOption(name,val){
		return $("<option>").text(name).val(val)
	}
}


class EquationBuilderDialog{
    constructor(app){
    	this.app=app;
        this.calculateGroups(app.columns,"number");
        let self = this;
       
        this.div = $("<div>").dialog({
            close: ()=>{
                this.div.dialog("destroy").remove();
            },
            position:{my: "top",at: "top"},

            buttons:[
                {
                    text:"Submit",
                    click:function(){
                        self.submit();
                    },
                    id:"create-eq-button"

                },    
                {
                    text:"Reset",
                    click:function(){
                        self.reset();
                    }

                },
                        {
                    text:"Close",
                    click:function(){
                       self.div.dialog("close");
                    }

                }

            ],
            width:500,
            title:"Create Column"
        }).dialogFix();
        this.outer_div=$("<div>").appendTo(this.div);
        this.msg_div=$("<div>").appendTo(this.outer_div);
        this.msg_div.text("Drag column(s) form the left pane into the grey box and then click on an operand (+,-,*,/) Multiple columns in the same box will be summed or averaged depending on the value of the dropdown");
    	
    	let name_div = $("<div>").appendTo(this.outer_div);
    	name_div.append("<label>Column Name</label>");
		this.name_input = $("<input type='text' class='form-control'>")
			.appendTo(name_div);
		
        this.lower_div=$("<div>").css("display","flex").appendTo(this.div);
        this.drop_sections=[];

        this.addColumns();
        this.main_div= $("<div>").css("padding-left","10px")
        .css({display:"flex","flex-direction":"column","flex-basis":"100%","flex": 1})
        .appendTo(this.lower_div);
        this.main_div.append($("<label>").text("Equation").css({"font-weight":"bold"}));
        this.ds_div=$("<div>").appendTo(this.main_div).css("min-height","200px");
        this.addDropSection();
   
        let rd = $("<div>").appendTo(this.main_div);

        rd.append($("<label>").text("Final Transformation").css({"font-weight":"bold","display":"block"}));
        this.addRadioButton(rd,"none",true);
        this.addRadioButton(rd,"log2");
        this.addRadioButton(rd,"log10");

    }

    reset(){
        this.ds_div.empty();
        this.drop_sections=[];
        this.addDropSection();

    }

    submit(){
    	let name = this.name_input.val();
    	if (!name){
    		return;
    	}
        for (let d of this.drop_sections){
            if (d.count===0){
                return;
            }
        }
        let args = this.getEquation(name);
        let self = this;
        args.name= name;
        $("#create-eq-button").attr("disabled",true);
       
		this.msg_div.addClass("alert alert-info").html("The column is being created<i style= 'float:right' class='fa fa-spinner fa-spin'></i>")
		this.app.sendAction("create_compound_column",args).done(function(resp){
			if (resp.success){
				self.msg_div.removeClass("alert-info").addClass("alert-success").text("The column has been created")
				self.app._addDataToView(resp.data);
				self.app.history.push(resp.data.history);
		    	if (self.app.history_dialog){
		    		self.app.history_dialog.refresh();
		    	}
			}
			else{
				self.msg_div.removeClass("alert-info").addClass("alert-danger").text("There was a problem, please contact an adminisrator");
			}
		});
      

    }
    addColumns(){
    	this.col_index={};
        this.columns_div=$("<div>").appendTo(this.lower_div)
        .css({"margin-top":"10px",display:"flex","flex-direction":"column","max-height":"400px","overflow-y":"scroll","flex-basis":"100%","flex": 1});
        this.columns_div.append($("<label>").text("Columns").css({"font-weight":"bold"}));
        for (let gn of this.group_names){
        	this.columns_div.append($("<div>").text(gn).css({"font-weight":"bold"}));
        	let columns = this.groups[gn];
	        for (let col of columns){
	        	this.col_index[col.field]=col.name;
	            $("<div>")
	            .data("id",col.field)
	            .text(col.name)
	            .draggable({
	                helper:"clone"
	            })
	            .css({cursor:"copy"})
	            .appendTo(this.columns_div);
	        }
        }
    }

    addRadioButton(div, type,checked){
        let i = $("<input>").attr({type:"radio",name:"eq-final-trans",value:type}).appendTo(div);
        if (checked){
            i.attr("checked",true);
        }
        div.append($("<label>").text(type).css({"margin-right":"5px","margin-left":"2px"}));
    }

    addOperand(drop_section,div, symbol){
        let self = this;
        let sp= $("<span>").text(symbol)
        .css({"font-size":"20px","margin-left":"10px","cursor":"pointer","margin-left":"5px","margin-right":"5px"})
        .click(function(e){
            drop_section.operand=symbol;
            div.empty();
            div.append($("<span>").text(symbol).css({"font-size":"20px","margin-left":"5px","margin-right":"5px"}));
            self.addDropSection();
        });
        div.append(sp);
    }

    getEquation(name){
    	let history={
    	        	label:"Added "+name+" Column",
    	}
    	let info="";
        for (let d of this.drop_sections){
            let arr=[];
            let name_arr=[];
            for (let col in d.columns){
                arr.push(col);
                name_arr.push(this.col_index[col])
            }
            if (name_arr.length===1){
            	info+=name_arr[0]+" ";
            }
            else{
            	info+=`${d.aggregate}(${name_arr.join(",")})`;
            }
            if (d.operand){
            	info+=(` ${d.operand} `);
            }
            
            d.columns=arr; 
        }
        let final_trans = $("input[name='eq-final-trans']:checked").val();
        if (final_trans !=="none"){
        	info = final_trans+"("+info+")";
        }
        history.info=info;
        return {
        	history:history,
            stages:this.drop_sections,
            final_trans:final_trans
        }

    }
    addDropSection(){
        let drop_section={
            columns:{},
            count:0,
            aggregate:"SUM"
        }
        let all_div = $("<div>").appendTo(this.ds_div);
        let agg_select= $("<select disabled><option>SUM</option><option>AVERAGE</option></select>");
        agg_select.change(function(e){
            drop_section.aggregate=$(this).val();
        })
        all_div.append(agg_select)
        this.drop_sections.push(drop_section);
        let ds_div=$("<div>").appendTo(all_div)
        .css({"min-height":"40px","background-color":"lightgray"})
        .droppable({
            drop:function(e,ui){
               let id  = ui.draggable.data("id");
               if (drop_section.columns[id]){
                   return;
               }
               let d= $("<div>").text(ui.draggable.text());
               drop_section.columns[id]=true;
               drop_section.count++;
               if (drop_section.count>1){
                    agg_select.attr("disabled",false);
               }
               $("<i class='fas fa-trash'></i>").css("float","right").click(function(e){
                   d.remove();
                   delete drop_section.columns[id];
                   drop_section.count--;
                   if (drop_section.count<2){
                       agg_select.attr("disabled",true);
                   }
               }).appendTo(d);
               ds_div.append(d);
            }
        });

        let odiv= $("<div>").css("text-align","center").appendTo(all_div);
        this.addOperand(drop_section,odiv,"+");
        this.addOperand(drop_section,odiv,"-");
        this.addOperand(drop_section,odiv,"*");
        this.addOperand(drop_section,odiv,"/");
        this.div.resize();


        
    }
    
    calculateGroups(columns,filter){
		let groups={};
		let group_list= [];
		groups["Other"]=[]
		
		for (let c of columns){
			if (filter && filter === "number"){
				if (c.datatype !=="integer" && c.datatype !== "double"){
					continue;s
				}
			}
			if (c.columnGroup){
				let li = groups[c.columnGroup]
				if (!li){
					li=[];
					group_list.push(c.columnGroup)
					groups[c.columnGroup]=li
				}
				li.push(c)
			}
			else{
				groups["Other"].push(c)
			}
		}
		for (let g in groups){
			let li = groups[g];
			li.sort(function(a,b){
				return a.name.localeCompare(b.name)
			})
		}
		group_list.sort(function(a,b){
			return a.localeCompare(b);
		
		});
		group_list.push("Other")
		this.groups=groups;
		this.group_names=group_list;
	}

}




class MLVPeakStatsDialog{
	constructor(app,icon){
		this.app=app;
		this.icon=icon;
		let self =this;
		this.bigwig_number=0;
		this.div=$("<div>");
		this.div.append("<div class='info-text'> Enter the url(s) of publically accesible BigWig files to process and press Add</div>")
		let d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div)
		
		d.append("<label>BigWig URL(S)</label>");
	
		this.bigwig_input = $("<textarea class='form-control'></textarea>")
			.appendTo(d);
		

		$("<button>")
		.css("margin-top","3px")
		.text("Add").attr("class","btn btn-sm btn-primary").
		click(function(e){
			self.error_message.empty().hide()
			let text = self.bigwig_input.val();
			let arr = text.trim().match(/[^\s]+/g)
			for (let url of arr){
				self.addWigFile(url);
			}
		}).appendTo(d);
		this.div.append("<label> BigWig Tracks to Process</label><br>")
		this.bigwigs= $("<div style='margin-bottom:10px'></div>").appendTo(this.div);
	
		this.error_message=$("<div class='alert alert-danger'></div>").appendTo(this.div).hide();
		
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Add Peak Stats",
    		autoOpen:true,
    		width:400,
    		height:400,
    		buttons:[
    			{
    				text:"Submit",
    				click:function(){
    					self.submit();
    				},
    				id:"peak-stats-submit"
    			},
    			{
    				text:"Cancel",
    				click:function(){
    					$(this).dialog("close");
    				}
    			}
    		]
    	
    	}).dialogFix();
		$("#peak-stats-submit").attr("disabled",true);
	}
	
	addWigFile(url){
	
		let self = this;

		$.ajax({
			url:"/meths/validate_track_url",
			type:"POST",
			dataType:"json",
			data:{url:url}
		}).done(function(result){
			if (result.valid){
				self.bigwigs.append(self.getBigWigDiv(url));
				self.bigwig_input.val("");
				self.bigwig_number++;
				$("#peak-stats-submit").attr("disabled",false);
				
			}
			else{
				self.error_message.append("<span>"+url+"</span><br><span>is invalid</span>").show();
			}
		})
	}
	
	getBigWigDiv(url){
		let d = $("<div>");
		let self = this;
		let arr =url.split("/")
		let name = arr[arr.length-1].split(".")[0];
		let n_i= $("<input>").val(name).appendTo(d);
	
		$("<i class='fas fa-trash'></i>")
		.css({cursor:"pointer",float:"right","font-size":"18px"})
		.click(function(e){
			d.remove();
			self.bigwig_number--;
			if (self.bigwig_number===0){
				$("#peak-stats-submit").attr("disabled",true);
			}
			
		}).appendTo(d);
		d.data("bigwig",url).data("name",n_i)
		return d
	}
	
	submit(){
		let names=[];
		let wig_locations=[];
		let self = this;
		this.bigwigs.children().each(function(index,item){
			names.push($(item).data("name").val());
			wig_locations.push($(item).data("bigwig"))
		})
		
		let data={
				method:"initiate_job",
				args:{
					inputs:{
						wig_locations:wig_locations,
						wig_names:names
					},
					job:"peak_stats_job"				
				}
		}
		
		
		$.ajax({
			url:"/meths/execute_project_action/"+this.app.project_id,
			type:"POST",
			data:JSON.stringify(data),
			dataType:"json",
			contentType:"application/json"
		}).done(function(response){
			if (response.success){
				self.div.children().hide();
				self.error_message.removeClass("alert-danger")
						.addClass("alert-success")
						.html("Peak stats are being calculated. You can follow the progress in my jobs.")
						.show();
				self.app.jobSent(response.data)
				
			}
			else{
				self.error_message.html(response.msg).show();
			}
			
		});
		
		
	}
	
	
	
}

class CreateZegamiCollection{
	constructor(project_id){
		this.project_id=project_id;
		let self =this;
		this.div=$("<div>");
		let d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div)
		d.append("<label>Username</label>");
		let msg ="Usually your email address"
			d.append($("<p class= 'info-text'></p>").text(msg));
		this.username_input = $("<input type='text' class='form-control'>")
			.appendTo(d);
		
		d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div)
		d.append("<label>Project ID</label>");
		msg ="The code which appears before the hyphen in one of your collection urls e.g ztrbzvw2"
		d.append($("<p class= 'info-text'></p>").text(msg));
		this.project_input = $("<input type='text' class='form-control'>")
			.appendTo(d);
		
		d= $("<div style='margin-bottom:10px'></div>").appendTo(this.div)
		d.append("<label>Password</label>");
		this.password_input = $("<input type='password' class='form-control'>")
			.appendTo(d);
		this.error_message=$("<div class='alert alert-danger'></div>").appendTo(this.div).hide();
		
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Create Zegami Collection",
    		autoOpen:true,
    		width:280,
    		buttons:[
    			{
    				text:"Submit",
    				click:function(){
    					self.submit();
    				},
    				id:"zegami-submit-btn"
    			},
    			{
    				text:"Cancel",
    				click:function(){
    					$(this).dialog("close");
    				}
    			}
    		]
    	
    	}).dialogFix();
	}
	
	submit(){
		let self =this;
		let project=this.project_input.val();
		let username= this.username_input.val();
		let password = this.password_input.val();
		if (!project){
			this.project_input.focus();
			return;
		}
		if (!username){
			this.username_input.focus();
			return;
		}
		if (!password){
			this.password_input.focus();
			return;
		}		
		
		let data={
				method:"upload_zegami_collection",
				args:{
					project:project,
					username:username,
					password:password
				}
		}
		$.ajax({
			url:"/meths/execute_project_action/"+this.project_id,
			type:"POST",
			data:JSON.stringify(data),
			dataType:"json",
			contentType:"application/json"
		}).done(function(response){
			if (response.success){
				if (response.data.log_in_failed){
					self.error_message.html("Cannot log into Zegami - please check your credentials are correct").show();
				}
				else{
					$("#zegami-submit-btn").attr("disabled",true);
					self.div.find("input").attr("disabled",true);
					self.error_message.removeClass("alert-danger")
						.addClass("alert-success")
						.html("A Zegami collection is being created - you will get an email when this is complete. You can follow the progress in my jobs.")
						.show();
				}
			}
			else{
				self.error_message.html(response.msg).show();
			}
			
		})
		
	}
	
	
	
}






class WaitingDialog{
	constructor(title){
		this.div=$("<div>");
		this.spinners=[
			"fa-spinner",
			"fa-circle-notch",
			"fa-sync",
			"fa-cog",
			"fa-stroopwafel"		
		];
		this.spin_types=[
			"fa-spin",
			"fa-pulse"
		]

		this.div.dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:title,
			autoOpen:true,
			title:title
		}).dialogFix();
		this.div.append("<div><i class='fas fa-spinner fa-spin' style='font-size:36px'></i><div>");
		this.div.find("div").css({margin:"10px"});
	}
	
	wait(msg){
		this.div.empty();
		let spin = "fas "+ this.spinners[Math.floor(Math.random()*5)]+" ";
		spin+=this.spin_types[Math.floor(Math.random()*2)]
		
		this.div.append("<div><i class='"+spin+"' style='font-size:36px'></i><div>");
		if (msg){
			this.msg_div=$("<div>").text(msg).appendTo(this.div);
		}
		this.div.find("div").css({margin:"10px","text-align":"center"});
	}
	setWaitingMessage(text){
		this.msg_div.text(text)
	}
	remove(){
		this.div.dialog("close");
	}
	showMessage(msg,type){
		this.div.empty();
		this.msg_div=$("<div>").html(msg).appendTo(this.div);
		if (type){
			this.msg_div.addClass("alert alert-"+type);
		}
		this.div.find("div").css({margin:"10px"});
	}
	
}


class NameDescGenomeForm{
	constructor(div,project_type,callback,defaults){
		if (typeof div === "string"){
			this.div=$("#"+div);
		}
		else{
			this.div=div;
		}
		if(!defaults){
			defaults={};
		}
		
		this.project_type=project_type;
		this.callback=callback;
		this.defaults=defaults;
		let self=this;
		
		
		this.div.append("<label>Name</label>");
		this.name_input = $("<input type='text' id='mlv-model-name' class='form-control'>")
			.appendTo(this.div);
		
		this.div.append("<label>Description</label>");
		this.desc_input =$("<textarea rows='3' id='mlv-model-description' class='form-control'></textarea>")
			.appendTo(this.div);
		
		this.div.append("<label>Genome</label>");
		this.genome_select=$("<select class='form-control'></select>")
			.change(function(e){
				self.allFilledIn();
			})
			.appendTo(this.div);
		
		this.div.find("input").on("blur keypress",function(e){
			
			self.allFilledIn();
		});
		
		$("<option>").text("--Select--").val("").appendTo(this.genome_select);
		
		let b_text=defaults.button_text?defaults.button_text:"Next";
		let c_div=$("<div style ='text-align:center'></div>").appendTo(this.div);
		this.submit_button = $("<button>")
			.attr({"class":"btn btn-sm btn-primary",disabled:true})
			.css({"margin-top":"5px"})
			.text(b_text)
			.click(function(e){
				self.submit();
			}).appendTo(c_div);
		
		this.error_alert = $("<div class ='alert alert-danger'></div>")
			.css({visibility:"hidden"})
			.appendTo(this.div);
		
		this.addGenomes();
		
	}	
	
	allFilledIn(){
		if (this.name_input.val() && this.desc_input.val() && this.genome_select.val()){
			this.submit_button.attr("disabled",false);
		}
		else{
			this.submit_button.attr("disabled",true);
		}	
	}
	
	reset(){
		this.disableAll(false);
		this.submit_button.attr("disabled",true);
		this.name_input.val("");
		this.desc_input.val("");
		this.genome_select.val("");
	}
	disableAll(bool){
		this.submit_button.attr("disabled",bool);
		this.name_input.attr("disabled",bool);
		this.desc_input.attr("disabled",bool);
		this.genome_select.attr("disabled",bool);
	
		
	}
	
	submit(){
		let self = this;
		this.disableAll(true);
		$.ajax({		
			url:"/meths/create_project/"+this.project_type,
			data:{
				name:this.name_input.val(),
				description:this.desc_input.val(),
				genome:this.genome_select.val()
				
			},
			type:"POST",
			dataType:"json"
		}).done(function(response){
			if (response.success){
				self.callback(response.project_id)
			}
			else{
				self.disableAll(false);
				self.error_alert.text(response.msg).css({visibility:"visible"});
			}
		})			
	}
	
	addGenomes(){
		let self= this;
		$.ajax({
			url:"/meths/get_genomes",
			dataType:"json"
		}).done(function(genomes){
			 for (let genome of genomes){
		            self.genome_select.append($('<option>', {
		                value: genome.name,
		                text: genome.label
		            }));
		     }
			 if (self.defaults){
				 self.genome_select.val(self.defaults.genome).attr("disabled",true);
				 self.name_input.val(self.defaults.name);
				 self.desc_input.val(self.defaults.desc);
				 self.submit_button.attr("disabled",false)
			 }
		})
	}
	
}


class RemoveAnnotationsDialog{
	constructor(annotations,project_if,callback){
		this.annotations=annotations;
		this.project_id=project_id;
		this.to_delete=[];
		let self = this;
		this.callback=callback;
		this.div=$("<div>");
		for (let id in annotations){
			let a= annotations[id]
		
			let d = $("<div>").attr("class","mlv-list-item").data("id",id);
			d.append("<span>"+a.label+"<span>");
			let db = $("<i class='fas fa-trash'></i>").click(function(e){
				let p = $(this).parent();
				self.to_delete.push(p.data("id"));
				p.remove();
			})
			d.append(db).appendTo(this.div);
		}
		
		this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Remove Intersections",
    		autoOpen:true,
    		buttons:[
    			{
    				text:"Cancel",
    				click:function(e){
    					self.div.dialog("close");
    				},
    				id:"mlv-remove-anno-cancel"
    			},
    			{
    				text:"OK",
    				click:function(e){
    					self.removeAnnotations();
    				},
    				id:"mlv-remove-anno-ok"
    				
    			}
    		]
    	
    	}).dialogFix();
		
	}
	removeAnnotations(){
		let self = this;
		let data={
				method:"remove_annotation_intersections",
				args:{
					ids:this.to_delete
				}
		}
		$.ajax({
			url:"/meths/execute_project_action/"+this.project_id,
			dataType:"json",
			type:"POST",
			contentType:"application/json",
			data:JSON.stringify(data)
		}).done(function(response){
			$("#mlv-remove-anno-ok").hide()
			$("#mlv-remove-anno-cancel").text("Close");
			 if (response.success){
				 self.callback(true,self.to_delete);
				 self.div.html("The annotations have been successfully removed");
				
			 }
			 else{
				 self.callback(false,self.to_delete);
				 self.div.html("There was a problem removing the annotations");
			 }
		});
		
	}
	
	
}

class AddAnnotations{
	constructor(app,project_types){
		let config={
				show_types:true
		}
		if (!project_types){
			project_types="annotation_set";
			config.show_types=false;
		}
		else{
			project_types.push("annotation_set")
		}
		this.project_chooser = new ProjectChooserDialog(project_types,
				"Select Annotations to Calculate Intersections",
				app.genome,
				"Next",config);
		this.project_id=app.project_id;
		this.app=app;
	}
	
	showDialog(){
		let self=this;
		
		this.project_chooser.show(function(ids){
			if(ids.length===1){
				self.getExtraFields(ids[0])
			}
			else{
				self.sendJob(ids);
			}
		});
	}

	
	getExtraFields(item){
		let self = this;
		$.ajax({
			url:"/meths/get_project_fields/"+item.id,
			dataType:"json"
		}).done(function(response){
			if (response.length==0){
				self.sendJob([item])
			}
			else{
				
				let div=$("<div>");
				let column_div =$("<div>")
				let rb = $("<input>")
				.attr({name:"anno-type",type:"radio",value:"single",checked:true})
				.click(function(e){
					column_div.find("input[type=checkbox]").attr("disabled",true);
				})
				div.append(rb).append("<label>Single True/False Column</label>");
			
			
			
			
				
				
				
				
				$("<div>").text("A single TRUE/FALSE column, indicating overlap will be added").appendTo(div);
				div.append("<hr>");
				
				rb = $("<input>")
				.attr({name:"anno-type",type:"radio",value:"multi"})
				.click(function(e){
					column_div.find("input[type=checkbox]").attr("disabled",false);
					
				})
				div.append(rb).append("<label>Annotation Columns</label><br>");
				$("<div>").text("Select columns, whose values will be added from the annotation if an overlap occurs").appendTo(div);
				
				column_div.appendTo(div)
				let col_check=new  MLVColumnCheck(column_div,response,null,"none")
				div.dialog({
					close:function(){
						$(this).dialog("destroy").remove();
					},
					title:"Information to Record",
					buttons:[{
						text:"OK",
						click:function(e){
							let ec = col_check.getCheckedColumns();
							if (ec.length===0 || $("input[name=anno-type]:checked").val()==="single"){
								ec=null;
							}
							self.sendJob([item],ec);
							div.dialog("close");
							
						}
					}]
				}).dialogFix();
				column_div.find("input[type=checkbox]").attr("disabled",true);			
			}		
		})
		
	}
	


	
	sendJob(items,extra_columns){	
		let self= this;
		let ids=[];	
		for (let item of items){			
			ids.push(item.id);
		}
		let args= {
				ids:ids,
				extra_columns:extra_columns
		}	
		this.app.initiateJob("annotation_intersection_job",args);
		
		
	}

}

class AnnotationSetFromProject{
	constructor(project_id,ids,all_cols,defaults){
		this.project_id=project_id;
		this.ids=ids;
		this.all_cols;
		this.div = $("<div>");
		this.div.append("<label>Columns To Include</div>");
		let col_div=$("<div>");
		for (let col of all_cols){
			let parent =$("<div class='form-check form-check-inline'></div>");
			let id = "anno-check-"+col.field;
			let check = $("<input>").attr({
					"class":"form-check-input",
					type:"checkbox",
					id:"id"
			}).data("field",col.field);
			let label = $("<label>").attr({
				"class":"form-check-label",
				"for":id
				}).text(col.name)
			parent.append(check).append(label).appendTo(col_div);
		}
		this.div.append(col_div);
    	this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    		},
    		title:"Create Annotation Set From Project",
    		autoOpen:true,
    		width:350,
    		position:{my:"center top",at:"center top"}
    	
    	}).dialogFix();
    	let self=this;
		this.desc = new NameDescGenomeForm(this.div,"annotation_set",
				function(anno_id){
					self.createAnnotation(anno_id);
				},
				defaults);		
	}
	
	checkProgress(){
		let self =this;
		$.ajax({
			url:"/meths/get_project_data/"+this.anno_id,
			dataType:"json",
		}).done(function(response){
			if (!response.data.processing_file){
				self.allDone()
			}
			else{
				setTimeout(function(){
					self.checkProgress();
				},10000)
						
			}
			
		})		
		
	}
	
	allDone(){
		let msg = "The annotations have been created.";
		msg+="It can be used to find intersections with features.";
		msg+="Annotations can be managed <a href='/projects/annotation_set/home'>here</a>";
		this.waiting_dialog.showMessage(msg);
	}
	
	createAnnotation(anno_id){
		this.anno_id=anno_id;
		let fields=[];
		let self = this;
		this.div.find(".form-check-input").each(function(index,el){
			let cb = $(el);
			if (cb.prop("checked")){
				fields.push(cb.data("field"))
			}
		});
	
		
		let data={
			method:"create_from_project",
			args:{
				ids:this.ids,
				project_id:this.project_id,
				fields:fields			
			}
		}
		$.ajax({
			url:"/meths/execute_project_action/"+anno_id,
			dataType:"json",
			type:"POST",
			contentType:"application/json",
			data:JSON.stringify(data)
		}).done(function(response){
			self.checkProgress()
		});
		this.div.dialog("close");
		this.waiting_dialog = new WaitingDialog("Creating Annotation Set");
		this.waiting_dialog.wait();
		
		
	}
	
}
class MLVHistoryDialog{
	constructor(app){
		
		this.div = $("<div>");
		let self = this;
		this.app=app;
		this.app.history_dialog=this;
		
	
		
	
		this.div.dialog({
    		close:function(){
    			self.app.history_dialog=null;
    			$(this).dialog("destroy").remove();
    			
    		},
    		title:"History",
    		autoOpen:true,
    		height:400,
    		width:350,
    		
    		position:{my:"center top",at:"center top"},
    		buttons:[    			
    			{
    				text:"OK",
    				click:function(){
    					$(this).dialog("close");
    				}
    			},
    			
    		]
    	
    	}).dialogFix();
		this.refresh();
		
		
		
	}
	refresh(){
		this.div.empty();
		for (let i  in this.app.history){
			this.addHistory(i,this.app.history[i])
		}
	}
	
	addHistory(index,history){
		let self = this;
		let d=$("<div>").data("index",index).attr("id","div-"+history.id);
		let hd = $("<div>").appendTo(d);
		let sp= $("<span>").css({"padding-top":"5px",float:"right"}).appendTo(hd);
		let ind = parseInt(index)+1;
		hd.append(`<label>${ind}.${history.label}</label>`);
		$("<i>").attr("class","far fa-eye").click(function(e){
			if (id.css("display")==="block"){
				id.css("display","none");
			}
			else{
				id.css("display","block");
			}
			
		}).appendTo(sp)
		
		
		let cl = "fas fa-spinner fa-spin";
		if (history.status==="complete"){
			cl="fas fa-check";
		}
		if (history.status==="failed"){
			cl="fas fa-exclamation"
		}
		$("<i>").attr("class",cl).appendTo(sp);
		if (this.app.permission==="edit"){
			$("<i>").attr("class","fas fa-times").css({"font-size":"16px","margin-left":"3px"}).click(function(e){
				self.app.removeAction(history);
				d.remove();
			}).appendTo(sp);
		}
		
		
		
		
		let id=$("<pre>").text(history.info).css("display","none")
		.css({"overflow":"hidden","white-space":"pre-wrap"}).appendTo(d)
		
		
		
		this.div.append(d);
	}
	
}





