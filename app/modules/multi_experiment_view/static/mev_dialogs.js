class MEVGroupChooser{
	constructor(proj,div_id){
		this.project_id=proj.id;
		this.project_name = proj.name;
		this.dialog_panel=$("#"+div_id);
		this.dialog_panel.append("<h4>Choose Psuedo Bulk</h6>");
		let self =this;
		this.column_div=$("<ul>").attr("class","list-group list-group-horizontal").appendTo(this.dialog_panel);
		this.executeProjectAction("get_all_groups",{}).then(function(resp){
			self.showGroups(resp.data);
		
		});
		
		
			
	}
		
	showGroups(data){
		let self =this;
		for (let item of data){
			let lgi= $("<li>").attr("class","list-group-item dv-hover").css("width","300px")
			.click(function(e){
				self.setGroup($(this).data("exp"));
				$(".dv-hover").css("background-color","white");
				$(this).css("background-color","lightgray");
			})
			.data("exp",item)
			.appendTo(this.column_div);
			let o = lgi;
			$("<h5>").text(item.name).appendTo(o);
			$("<div>").text("clusters:"+item["cluster_number"]).appendTo(o);
			$("<h6>").text("Experiments").appendTo(o);
			for (let exp of item["experiments"]){
				o.append(exp["name"]+"<br>")
			}
			$("<h6>").text("Description").appendTo(o);
			$("<p>").text(item.description).appendTo(lgi);
		}
			
	}
	
	setGroup(exp){
		this.executeProjectAction("set_group",{group_id:exp.id}).then(function(e){
			location.reload();
		})
	}
	executeProjectAction(action,args){
			if (!args){
				args={}
			}
			
			let data={
				method:action,
				args:args	
			}
		
			return fetch("/meths/execute_project_action/"+this.project_id,
			{
				method:"POST",
				body:JSON.stringify(data),
				headers:{
					"Accept":"application/json,text/plain,*/*",
					"Content-Type":"application/json"
				}
				
			}).then(resp=>resp.json());
	}
	
	
	
}

class MEVViewer{
	constructor(proj,div_id){
		this.project_id=proj.id;
		this.project_name=proj.name;
		this.permission=proj.permission;
		this.genome=proj.genome;
		this.setUpDom(div_id);
		
	}
	
	saveState(data){
		
		this.executeProjectAction("save_view",{data:data}).then(function(response){
				if (response.success){
					new MLVDialog("The view has been saved",{type:"success"});
				}
				else{
					new MLVDialog(response.msg,{type:"danger"});
				}			
		});	
		
	}
	
	
	setUpSaveMenu(){
		let self = this;
		this.save_menu=new MLVContextMenu(function(data){
			return [
				{
					text:"Save",
					func:function(){					
						let data=self.getState();
						self.saveState(data);						
					},
					icon:"fas fa-save",
					ghosted:self.permission !== "edit"
				},
				{
					text:"Save As",
					
					func:function(){
						let data = self.getState()
						new MEVSaveAsDialog(self.project_id,"group_view",self.genome,data)
					},
					icon:"far fa-save",
					ghosted:self.permission === "view_no_log_in"
				
				},
				{
					text:"Share",
					
					func:function(){
						new ShareObjectDialog(self.project_id,self.project_name)
					},
					icon:"fas fa-share",
					ghosted:self.permission !=="edit"
				
				},
				{
					text:"Make Public",
					
					func:function(){
						 makeObjectPublic(self.project_id,self.project_name);
					},
					icon:"fas fa-globe",
					ghosted:self.permission !== "edit"
				
				}
				
				
				
				
				
				
				];
		})	
	}
	
	setUpDom(div_id){
		let od =$("#"+div_id).addClass("split-container")
		$("<div>")
		.attr({
			"class":"split split-horizontal",
			id:"fp-heatmaps"
		}).appendTo(od);
		$("<div>").attr({
			"class":"grid split split-horizontal",
			id:"fp-samples"
		}).css({"padding":"5px",overflow:"auto"}).appendTo(od);
		Split(['#fp-heatmaps', '#fp-samples'], {
    		sizes: [50,50],
    		direction:"horizontal",
    		gutterSize:5,
    		onDragEnd:function(){$(window).trigger("resize")}
		});
		
	}
	
	addSaveShareMenuItems(menu){
		let self = this;
		this.addMenuItem(menu,"fas fa-save","Save Current View",function(e){
				self.saveState();
			},{float:"right"});
		this.addMenuItem(menu,"fas fa-share","Share View",function(e){
				new ShareObjectDialog(self.project_id,self.project_name);	
			},{float:"right"});
		this.addMenuItem(menu,"fas fa-globe","Make View Public",function(e){
				makeObjectPublic(self.project_id,self.project_name);			
			},{float:"right"});
				
		
	}
	
	addMenuItem(menu,icon,tooltip,func,css){
		let i = $("<i>").attr("class",icon+" mev-icon")
		.attr({title:tooltip,"data-toggle":"tooltip"})
		.click(function(e){
			func();
		});
		if (css){
			i.css(css);
		}
		
		i.appendTo(menu);
	}
	
	
	executeProjectAction(action,args){
		if (!args){
			args={}
		}
		
		let data={
			method:action,
			args:args	
		}
	
		return fetch("/meths/execute_project_action/"+this.project_id,
		{
			method:"POST",
			body:JSON.stringify(data),
			headers:{
				"Accept":"application/json,text/plain,*/*",
				"Content-Type":"application/json"
			}
			
		}).then(resp=>resp.json());
	}
}

class MEVGroupViewer extends MEVViewer{
	constructor(proj,div_id){
		super(proj,div_id);
		

		this.group_colors=[
			["HV","#0072B2"],["CH","#F0E442"],["CM","#009E73"],
			["CS","#56B4E9"],["CC","#E69F00"],["Se","#CC79A7"],["LFC","#D55E00"],["LCC","#000000"]
		];
		
		
		let data = proj.data
		this.clusters=data.clusters;
		this.experiments=data.experiments;
		this.exp_index={};
		
		this.heat_map_genes={};
		this.heat_maps={};
		this.heat_maps_collapse=false;
		for (let e of this.experiments){
			this.exp_index[e.id]=e;
			e.color=this.hexToRGB(e.color);
			this.heat_map_genes[e.id]={};	
			this.heat_maps[e.id]={
					type:0,
					cluster:1
			}
		}
		
		
		this.current_view=data.current_view;
		
	
		//all sample information
		
		this.sample_index={};
		this.sample_fields={};
		this.sample_filter=null;
		this.features=[];
		
		
		//fill with empty records
		this.samples=data.samples;
		this.sample_index={}
		for (let item of data.samples){
			this.sample_index[item.id]=item;
		}
				
				
		this.filter_panel= new FilterPanel(["fp-heatmaps","fp-samples"],this.samples,{menu_bar:true});
				
		this.setUpFeatureMenu();
		this.setUpSampleMenu();
		
		
		this.filter_panel.addRemoveListener(function(chart){
			//self.chartRemoved(chart);
		});
		let self=this;
		this.filter_panel.addListener(function(items,count){
			self.sample_number_span.text(count+"/"+self.samples.length)
		},"fpl")
		
		this.setState(data.current_view);
		
	}
	
	
	
	download(d){
	
		let data = new Blob([d],{type:'text/plain'});
	    
	    let save = $("<a download></a>").appendTo("body");
	     
	         let text_file = window.URL.createObjectURL(data); 
	         save.attr("download","all.json");
	         save.attr("target","_blank")
	         save.attr("href",text_file);
	         save[0].click();
	   save.remove();
	}

	
	
	
	
	setUpFeatureMenu(){
		let self =this;
		this.feature_chooser = new ProjectChooserDialog("mev_feature_set","Choose Set",this.genome,"Get Data",
				{no_genome_column:true});
		this.feature_select_menu=new MLVContextMenu(function(data){
			return [
				{
					text:"Paste Gene List",
					func:function(){
						new GeneChooserDialog(self.project_id,self.experiments,function(genes){
							self.populateWithGenes(genes);
						});
					},
					icon:"fas fa-list-ul"
				},
				{
					text:"Choose Feature List",
					
					func:function(){
						self.feature_chooser.show(function(items){
							self.loadFeatureSet(items[0])
						});
					},
					icon:"fas fa-list-alt"
				
			}];
		})	
		let sf = $("<button>").attr("class","btn btn-secondary btn-sm")
				.text("Select Features")
				.click(function(e){
					self.feature_select_menu.show(null,e);
				
				})
				
		let t=$("<span>").text("Group By:").css({"font-weight":"bold"});
		this.hm_groupby_select = $("<select>").change(function(e){
			self.changeSampleMetadata($(this).val())
		});
		
		this.collapse_button= $("<button>").attr("class","btn btn-sm btn-secondary")
		    .text("collapse")
		    .click(function(e){
			self.heat_maps_collapse = !self.heat_maps_collapse;
			
				for (let id in self.heat_maps){
					let ch = self.filter_panel.charts["cluster-hm-"+id];
					if (!ch){
						continue;
					}
					if (self.heat_maps_collapse){
						ch.collapseGroups();
						self.collapse_button.text("Expand");
					}
					else{
						ch.uncollapseGroups();
						self.collapse_button.text("Collapse");
					}
					
				}
			
			
		});
		
		this.filter_panel.addMenuIcon(sf,"fp-heatmaps");
		this.filter_panel.addMenuIcon(t,"fp-heatmaps");
		this.filter_panel.addMenuIcon(this.hm_groupby_select,"fp-heatmaps");
		this.filter_panel.addMenuIcon(this.collapse_button,"fp-heatmaps");
		
		
	}
	
	
	setUpSampleMenu(){
		this.sample_chooser = new ProjectChooserDialog("mev_sample_set","Choose Filter",this.genome,"Filter",
				{no_genome_column:true});
		
		
		this.data_chooser = new ProjectChooserDialog("mev_sample_field","Choose Set",this.genome,"Get Data",
				{no_genome_column:true});
		let self =this;
		
		let dp= $("<div>").css("display","inline-block");
		let adb = $("<button>").attr("class","btn btn-secondary btn-sm")
		.text("Get Data")
		.click(function(e){
			self.data_chooser.show(function(items){
				let ids=[];
				for (let item of items){
					ids.push(item.id);
				}
				self.loadSampleData(ids);
			},self.sample_fields)
		}).appendTo(dp);
		
		$.ajax({
			url:"/meths/users/has_permission/mev_upload_sample_data",
			dataType:"json"
			
		}).done(function(response){
			if (response.permission){
				$("<button>").attr("class","btn btn-sm btn-secondary")
				.text("Upload Data")			
				.click(function(e){
					let default_ids=[];
					for (let i of self.samples){
						default_ids.push(i[self.default_id])
					}
					new MEVUploadSampleData(self.project_id,self.genome,default_ids,
							function(new_id){
								self.loadSampleData([new_id])
							}
					);
				}).appendTo(dp)
				
			}
		})
		
		
		let csb = $("<button>").attr("class","btn btn-secondary btn-sm")
		.text("Choose Filter")
		.click(function(e){
			self.sample_chooser.show(function(items){
				self.loadSampleSet(items[0].id)
			})
		});
		
		let aci =$("<button>").attr("class","btn btn-sm btn-secondary")
		    .text("Add Chart")
			.click(
			function(e){
				self.showAddChartDialog();
			}
				
		)
		
		
		let clb = $("<button>").attr("class","btn btn-secondary btn-sm")
		.text("Clear Filter")
		.click(function(e){
			self.filter_panel.removeCustomFilter("sample_group");
			self.sample_flter=null;
			self.set_name_span.text("All");
		});
		
		let sic= $("<button>").attr("class","btn btn-sm btn-secondary")
		.text("Save")	
		.click(function(e){
			self.save_menu.show(null,e)
		});
		let t = this.samples.length;
		
		this.sample_number_span=$("<span>").text(t+"/"+t);
		
		
		
		this.set_name_span=$("<span>").text("All");
		let f=this.filter_panel;
		f.addMenuIcon(dp,"fp-samples");
		f.addMenuIcon(csb,"fp-samples");
		f.addMenuIcon(this.set_name_span,"fp-samples");
		f.addMenuIcon(clb,"fp-samples");
		f.addMenuIcon(aci,"fp-samples");
		
		f.addMenuIcon(sic,"fp-samples");
		f.addMenuIcon(this.sample_number_span,"fp-samples");
		this.setUpSaveMenu();
	}
	
	loadSampleSet(id){
		fetch("/meths/get_project_data/"+id)
    	.then(response=>response.json())
    	.then(results=>{
    		let ids = results.data.sample_ids;
    		this.set_name_span.text(results.name);
    		this.filter_panel.addCustomFilter("sample_group","id",function(d){
				return ids.indexOf(d)!==-1;
			});
    		this.sample_filter=id;
    		
    	});
		
	}
	
	showAddChartDialog(){
		let cols=[];
		for(let c in this.sample_fields){
			cols.push(this.sample_fields[c]);
			
		}
		let self = this;
	
		new AddChartDialog(cols,function(config){
			config.div_name="fp-samples";
			self.filter_panel.addChart(config)
		},
		{"exclude_graph_types":["time_line_chart","heat_map","summary_heat_map","average_bar_chart"]})
		
	}
	
	loadFeatureSet(fs){
		let self = this;
		for(let h in this.heat_maps){
			this.filter_panel.removeChart("cluster-hm-"+h);
		}
		this.executeProjectAction("get_feature_set",{feature_set_id:fs.id}).then(function(resp){
				let cf="c1";
				let data = resp.data;
				for (let sample of self.samples){
					let sid= sample["id"]
					for (let v of data){
						let val = v[cf][sid-1];
						if (val!=null){
							sample[v["fid"]]=val;
						}	}
				}
				let columns=[];
				let param=[];
				for (let v of data){
					let exp_name=self.exp_index[v.exp_id].name
					let c={
						datatype:"double",
						field:v.fid,
						name:exp_name+"|"+v.type+"|"+v.name
							
					}
					param.push(v.fid);
					columns.push(c)
				}
				self.filter_panel.setColumns(columns);
				let dvs=[]
				for (let n=0;n<columns.length;n++){
					dvs.push(50-n);
				}
				let graph_config={
						type:"heat_map",
						row_color_scale:true,
						row_values:dvs,
						y_axis_width:200,
						group_by:self.current_sample_metadata,
						id:"cluster-hm-featureset",
						location:{x:0,y:0,width:12,height:6},
						div_name:"fp-heatmaps",
						title:fs.name,
						tooltip:{x_name:"sample",x_field:"id",y_name:"feature"},
						group_colors:{source:self.group_colors},
						param:param
						
					
					
				}
				self.filter_panel.addChart(graph_config);		
		});
	}
	
	
	
	loadSampleData(ids,next,group_by,feature_data){
		let self =this;		
		this.executeProjectAction("get_sample_data",{ids:ids,feature_data:feature_data}).then(function(resp){
			if (resp.success){
				if (feature_data){
					self.features= self.features.concat(feature_data);
				}
				for (let item of resp.data.data){
					let data_item = self.sample_index[item.id];
					for (let key in item){
						data_item[key]=item[key];
					}
				}
				let x_pos=0;
				for (let id in resp.data.fields){
					let field= resp.data.fields[id];
					self.sample_fields[id]=field
					
					if (!next){
						if(!field.is_feature){
							let graph={
								title:field.name,
								param:field.field,
								type:field.graph,
								id:"sample_"+field.id,
								location:{
									x:x_pos,
									y:0,
									height:4,
									width:4
								},
								div_name:"fp-samples"
							}
							x_pos+=4;
							if (x_pos===12){
								x_pos=0;
							}
							if (field.colors){
								let gc= {};
								gc[field.field]=field.colors;
								graph["group_colors"]=gc;
							}
							if (field.delimiter){
								graph["delimiter"]=field.delimiter;
							}
							self.filter_panel.addChart(graph,"fp-samples");
							
						}
						else{
							let gb= self.hm_groupby_select.val();
							let graph={
									title:field.name,
									param:[gb,field.field],
									type:"box_plot",
									show_points:true,
									show_outliers:true,
									id:"sample_"+field.id,
									location:{
										x:x_pos,
										y:0,
										height:4,
										width:6
									},
									div_name:"fp-samples"
								}
							self.filter_panel.addChart(graph,"fp-samples");
							
						}
					
				
					}
								
					
					if (field.datatype==="text" && !(field.delimiter)){
						self.hm_groupby_select.append($("<option>").val(field.field).text(field.name));
					}
					if (group_by){
						self.hm_groupby_select.val(group_by);
					}
					
				
				}
				let cols=[];
				for(let c in self.sample_fields){
					cols.push(self.sample_fields[c]);
					
				}
				self.filter_panel.setColumns(cols);
				if (next){
					for (let g of next){
						self.filter_panel.addChart(g,"fp-samples");
					}
					self._heat_maps_loaded=0;
					let maps_to_load=[];
					for (let e_id in self.heat_maps){
						if (self.heat_map_genes[e_id].ids.length >0 ){
							maps_to_load.push(e_id);
							self._heat_maps_loaded++;
							
						}
					}
					for (let e_id of maps_to_load){
						self.getGeneData(self.exp_index[e_id],"replace")
					}
							
				}
				
			}
			
		});	
	}
	
	
	
	
	
	chartRemoved(chart){
		if (chart.id.startsWith("cluster-hm")){
			//let exp_id= chart.id.split("-")[2];
			//this.removeAllGenes(exp_id);
		}
		else{
			delete this.scatter_plots[chart.id];
		}
	}
	
	changeSampleMetadata(value){
		
		for (let id in this.filter_panel["charts"]){
			let ch = this.filter_panel["charts"][id];
			if (id.startsWith("cluster-hm")){
				this.filter_panel.charts[id].groupBy(value);
			}
		
		}	
	}
	
	
	
	filterSampleGroup(value){
		this.sample_filter_group=value;
		if (value==="All"){
			this.filter_panel.removeCustomFilter("sample_group")
		}
		else{
			let li = this.sample_groups[value];
			this.filter_panel.addCustomFilter("sample_group","id",function(d){
				return li.indexOf(d)!==-1;
			})
		}
	}
	

	
	getIndividualGeneData(e){
		
		let type = $("#sel-datatype-exp-"+e.id).val();
		let self = this;
		let gene_id=this.selected_genes[e.id][0];
		let gene_name=this.selected_genes[e.id][1];
		let args={
				gene_id:gene_id,
				group:this.selected_group,
				type:type
		}
		this.executeProjectAction("get_individual_gene_data",args).then(function(resp){
			self.addIndividualGeneData(resp.data);
			let chart = self.filter_panel.charts["gene-hm-"+e.id];
			let title= gene_name+ " "+e.name+" "+type;
			if (chart){
				chart.setTitle(title);
				chart.refreshColors();
			}
			else{
				self.addIndividualGeneChart(e,type,title);
			}
			
		});
		
	}
	
	addIndividualGeneChart(exp,type,title){
		let cs= null;
		let id= "gene-hm-"+exp.id;
		for (let dt of exp.main_data.datatypes){
			if (dt.col_name===type){
				cs = dt.scale;
				break;
			}
		}
		let param=[];
		for (let c in this.clusters){
			param.push("c"+c+"_"+exp.id);
		}
		let graph_config={
				type:"heat_map",
				group_by:this.current_sample_metadata,
				id:id,
				location:{x:6,y:0,width:6,height:8},
				universal_color_scale:cs,
				div_name:"fp-heatmaps",
				title:title,
				tooltip:{x_name:"sample",x_field:"combat_id",y_name:"cluster"},
				param:param
			}
		if (this.current_view){
			let saved_graph=false;
		
				let index=0;
				for (;index<this.current_view.charts.length;index++){
					let g= this.current_view.charts[index];
					if (g.id==id){
						graph_config=g;
						saved_graph=true;
						break;
					}
				}
				if (saved_graph){
					this.current_view.charts.splice(index,1);
				}
			
		}
		graph_config.group_colors={
			source:this.group_colors
		};
		
		this.filter_panel.addChart(graph_config);
	}
	
	getGeneDropDown(genes){
		let sel =$("<select>");
		for (let g in genes){
			let og = $("<optgroup>").attr("label",g).appendTo(sel);
			let cols = genes[g];
			for (let col of cols){
				$("<option>").val(col.field).text(col.name+"("+g+")").appendTo(og);
			}
				
		}
		return sel;
		
	}
	addScatterPlot(ids,title){
		let id = ids[0]+"_"+ids[1];
		this.scatter_plots[id]={
				ids:ids
		};
		let info = this.sample_metadata[this.sample_data_select.val()];
		this.filter_panel.addChart({
			param:[ids[0],ids[1]],
			axis:{
				x_label:this.genes[ids[0]].columnGroup+" "+this.genes[ids[0]].name,
				y_label:this.genes[ids[1]].columnGroup+" "+this.genes[ids[1]].name
			},
			type:"wgl_scatter_plot",
			title:title,
			id:id,
			group_colors:{
				source:this.group_colors
			},
			color_by:{
				column:{
					datatype:"text",
					field:info.field,
					name:info.name
				}
			}
		
			
		});
	}
	
	showScatterPlotDialog(){
		let groups={};
		let self =this;
		for (let e of this.experiments){
			groups[e.name]=[];
		}
		
		for (let fid in this.genes){
			let col = this.genes[fid];
			if (groups[col.columnGroup]){
				groups[col.columnGroup].push(col)
			}
		}
		for (let n in groups){
			groups[n].sort(function(a,b){
				return a.name.localeCompare(b.name);
			})
		}
		let x_sel = this.getGeneDropDown(groups);
		let y_sel= this.getGeneDropDown(groups);
		let ti = $("<input>").val("Scatter Plot");
		$("<div>").attr("class","dv-dialog")
		.append("<label>X Value:</label>").append(x_sel)
		.append("<label>Y Value:</label>").append(y_sel)
		.append("<label>Title:</label>").append(ti)
		.dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:"Add Scatter Plot",
			buttons:[{
				text:"Add Plot",
				click:function(e){
					self.addScatterPlot([x_sel.val(),y_sel.val()],ti.val())
					$(this).dialog("close");
					
				}
			}]
			
		}).dialogFix();
		
	}
	
	displayTypeChanged(exp){
		//does the chart exist
		let chart = this.filter_panel.charts["cluster-hm-"+exp.id];
		//let g_ch= this.filter_panel.charts["gene-hm-"+exp.id];
		if (!chart){
			return;
		}
		let i = this.heat_maps[exp.id].type;
		let info = exp.main_data.datatypes[i];
			
		chart.config.universal_color_scale.min = info.scale.min;
		chart.config.universal_color_scale.max=info.scale.max;
		chart.updateUniversalScale();
				
		this.getGeneData(exp,"update");
		//this.getIndividualGeneData(exp);
		
		/*for (let id in this.extra_data){
			let d= this.extra_data[id];
			this.addUpdateGraph(d.exp_id,d.data);
		}*/
		
		
		
	}
	
	
	getGeneData(e,action){
		let gids=this.heat_map_genes[e.id].ids;
		let self =this;
		let cluster=this.heat_maps[e.id]["cluster"];
		cluster=cluster?cluster:1;
		let type = e.main_data.datatypes[this.heat_maps[e.id].type].col_name;
		let args={
				experiment:e.id,
				type:type,
				group:this.selected_group,
				gene_ids:gids,
				cluster:cluster
							
		}
		this.executeProjectAction("get_gene_data",args).then(function(resp){
			self.addGeneData(resp.data,cluster);
			if (action !=="update"){
				self.replaceGeneGraph(e,gids);
			}
			else{
				let graph = self.filter_panel.charts["cluster-hm-"+e.id];
				graph.refreshColors();
				for (let id in self.scatter_plots){
					self.filter_panel.charts[id].refreshPositions();
				}
			}
			
		});
		
	}
	
	replaceGeneGraph(exp){
		this.filter_panel.removeChart("cluster-hm-"+exp.id);
		
	
		let graph_config=null;
		let gi = this.heat_map_genes[exp.id];
		
		if (!this.heat_maps[exp.id].graph){
			graph_config={
					type:"heat_map",
					group_by:this.hm_groupby_select.val(),
					id:"cluster-hm-"+exp.id,
					location:{x:0,y:0,width:12,height:4},
					div_name:"fp-heatmaps",
					title_color:exp.color,
					tooltip:{x_name:"sample",x_field:this.default_id,y_name:"gene"},
					collapse_groups:this.heat_maps_collapse,
					title:exp.name,
					group_colors:{
							source:this.group_colors
					},
					universal_color_scale:exp.main_data.datatypes[this.heat_maps[exp.id].type].scale,
					param:gi.ids,
					field_to_name:gi.id_to_name
				}
				
				
		}
		else{
			graph_config= this.heat_maps[exp.id].graph;
			this.heat_maps[exp.id].graph=null;
			this._heat_maps_loaded--;
		}
		graph_config.clickable_y_axis=true;
			
		this.filter_panel.addChart(graph_config);
		
				
		
		let self = this;
		let ch = this.filter_panel.charts["cluster-hm-"+exp.id];
		
		
		
		//add type select
		let t_sel=$("<select>");
		let c=0;
		for (let dt of exp.main_data.datatypes){
			t_sel.append($("<option>").text(dt.name).val(c))
			c++;
		}
		t_sel.change(function(e){
			let v = $(this).val();
			self.heat_maps[exp.id].type=v;
			self.displayTypeChanged(exp);
		});
		t_sel.val(self.heat_maps[exp.id].type);
		ch.addTitleControl(t_sel);
		
		//add cluster select for non bulk
		let cl_sel=null;
		if (!exp.bulk){
			cl_sel = $("<select>");
			for (let v in this.clusters){
				cl_sel.append($("<option>").text(this.clusters[v].name).val(v));
			}
			cl_sel.val(self.heat_maps[exp.id].cluster)
			cl_sel.change(function(e){
				let v= $(this).val();
				self.heat_maps[exp.id].cluster=v;
				self.getGeneData(exp,"update");
			})
		ch.addTitleControl(cl_sel)
		}
		
		//add cluster icon
		
		let clb=$("<i>").attr("class","fas fa-project-diagram").css({"margin-top":"4px","margin-left":"3px"})
		.click(function(e){
			ch.clusterData();
		});
		ch.addTitleControl(clb);
		//loaded from state - need to apply filter
		if (this._heat_maps_loaded===0){
			if (this.sample_filter){
				this.loadSampleSet(this.sample_filter)
			}
			this._heat_maps_laoded=null;
			
		}
		ch.addListener("y_click",function(type,data){
			let t= t_sel.val();
			let c= cl_sel?cl_sel.val():1;
			let f = data.field;
			let obj= {field_id:f,cluster:c,type:t,exp_id:exp.id};
			console.log(obj);
			self.loadSampleData(null,null,null,[obj])
		})

		
	}
	
	
	
	displayOtherGraphs(){
		let ch_index = {};
		for (let chart of this.current_view.charts){
			ch_index[chart.id]=chart;
			if (chart.id.startsWith("source")){
				this.filter_panel.addChart(chart);
			}
		}
		for (let id in this.scatter_plots){
			this.filter_panel.addChart(ch_index[id]);
		}
		for (let id in this.extra_data){
			let info= this.extra_data[id];
			$("#"+id).prop("checked",true);
			this.addUpdateGraph(info.exp_id,info.data,"add",ch_index[id]);
		}
		let v = this.current_view.sample_filter_group;
		if (v){
			this.sample_filter_select.val(v);
			this.filterSampleGroup(v);
		}
		this.initial_load=false;
	}
	
	
	
	addGeneData(data,cluster){
		let cf = "c"+cluster
		for (let sample of this.samples){
			let sid= sample["id"]
			for (let v of data){
				let val = v[cf][sid-1];
				if (val!=null){
					sample[v["field_id"]]=val;
				}
				else{
					if(sample[v["field_id"]]!==undefined){
						delete sample[v["field_id"]]
					}
				}
			}
		}
		
	}
	addIndividualGeneData(data){
		for (let cid in this.clusters){
			
		}
		for (let sample of this.samples){
			let sid=sample["id"];
			for (let c in this.clusters){
				let cid = "c"+c
				let val=data[cid][sid-1];
				if (val!==null){
					sample[cid+"_"+data.exp_id]=val;
				}
			}
			
		}
	}
	
	getState(){
		let sample_data_ids=[];
		for (let id in this.sample_fields){
			if (!this.sample_fields[id].is_feature){
				sample_data_ids.push(parseInt(id));
			}
		}
		
		let graphs= this.filter_panel.getGraphs();
		let sample_graphs=[];
		for (let g of graphs){
			if (!g.id.startsWith("cluster-hm")){
				sample_graphs.push(g)
			}
			else{
				let e_id = g.id.split("-")[2];
				this.heat_maps[e_id].graph=g;
			}
		}
		
		let data={
				heat_maps:this.heat_maps,
				heat_map_genes:this.heat_map_genes,
				hm_group_by:this.hm_groupby_select.val(),
				heat_maps_collapse:this.heat_maps_collapse,
				sample_data_ids:sample_data_ids,
				sample_graphs:sample_graphs,
				sample_filter:this.sample_filter,
				features:this.features
				
		}
		return data;
		
	
		
	}
	

	
	setState(state){
		let self=this;
		if (state.heat_map_genes){
			this.heat_map_genes=state.heat_map_genes;
			
		}
		else{
			
				new GeneChooserDialog(self.project_id,self.experiments,function(genes){
					self.populateWithGenes(genes);
				});
			
		}
		if (state.heat_maps){
			this.heat_maps=state.heat_maps;
		}
		
		this.default_id=state.default_id;
		
		
	
		this.heat_maps_collapse= state.heat_maps_collapse;
		let t  = state.heat_maps_collapse?"EXpand":"Collapse";
		this.collapse_button.text(t);
		this.sample_filter=state.sample_filter;
		
			
		this.loadSampleData(state.sample_data_ids,state.sample_graphs,state.hm_group_by,state.features)
		
	}
	
	
	
	getGeneInfo(gene_list,exp_id){
		let args = {
				exp_id:exp_id,
				gene_list:gene_list
				
		};
		let self =this;
		this.executeProjectAction("get_gene_info",args).then(function(data){
				for (let gene of data.data){
					self.addChosenGene(gene.name,gene.id,exp_id,exp_id);
				}
		});
	}
	
	showGeneListInput(exp_id){
		let ta= $("<textarea>").css("width","100%");
		let self =this;
		$("<div>").append(ta).dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:"Paste Gene List",
			buttons:[{
				text:"submit",
				click:function(e){
					self.getGeneInfo(ta.val().split(/(\s+)/).filter(Boolean),exp_id);
					$(this).dialog("close");
					
				}
			}]
			
		}).dialogFix();
		
	}
	
	
	clusterSelected(id){
		this.selected_cluster=id;
		let self =this;
		//do we have any graphs need updating
		
		for (let exp of this.experiments){
			if (exp.bulk){
				continue;
			}
			let id= "cluster-hm-"+exp.id;
			if (this.filter_panel.charts[id]){
				this.getGeneData(exp,false);
			}
		}
		for (let id in this.extra_data){
			let d= this.extra_data[id];
			this.addUpdateGraph(d.exp_id,d.data);
		}
		
		
		
		
	}
	

	
	setUpClusterPanel(){
		for (let e of this.experiments){
			for (let c in this.clusters){
				this.cluster_columns.push({
					datatype:"double",
					name:this.clusters[c].name,
					field:"c"+c+"_"+e.id,
					columnGroup:"cluster_"+e.id
				})
			}
		}
		let self = this;
		let first=true;
		for (let cid in this.clusters ){
			let cluster=this.clusters[cid];
			let d  = $("<span>").text(cluster.name).data("id",cid)
			.attr("class","mev-cluster-span dv-hover")
			this.cluster_panel.append(d);
			if (first && !self.current_view){
				d.css("background-color","lightgray");
				this.selected_cluster=cid;
				first=false;
			}
			if (self.current_view && self.current_view.selected_cluster==cid){
				d.css("background-color","lightgray");
				this.selected_cluster=cid;
			}
			
		}
		$(".mev-cluster-span").click(function(e){
			self.clusterSelected($(this).data("id"));
			$(".mev-cluster-span").css("background-color","white");
			$(this).css("background-color","lightgray");
		})
		
		this.exp_index={};
		
		for (let experiment of this.experiments){
			this.addExperimentPanel(experiment);
			this.exp_index[experiment.id]=experiment;
			
		}
		if (this.current_view){
			this.setState();
		}
	
		
	}
	
	removeExtraGraph(exp_id,data){
		let id = exp_id+"_"+data.col_name;
		delete this.extra_data[id];
		this.filter_panel.removeChart(id);
		
	}
	
	addUpdateGraph(exp_id,data,action,graph){
		let gene_ids=[];
		let columns=[];
		let param=[];
		let id = exp_id+"_"+data.col_name;
		for (let p of data.param){
			gene_ids.push(p.id);
			param.push(exp_id+"_"+p.id);
			columns.push({
				name:p.name,
				field:exp_id+"_"+p.id,
				columnGroup:data.name,
				sortable:true,
				filterable:true
			})
		};
		
		this.extra_data[id]={
				exp_id:exp_id,
				data:data
		};
		let self = this;
		let args={
			cluster:this.selected_cluster,
			group:this.selected_group,
			type:data.col_name,
			gene_ids:gene_ids
				
		};
		let chart_data=graph;
		let info = this.sample_metadata[this.sample_data_select.val()];
		if (!chart_data){
			chart_data={
				type:data.type,
				title:data.name,
				param:param,
				id:id,
				color_by:{
					column:{
						datatype:"text",
						field:info.field,
						name:info.name
					}
				},
				group_colors:{
					source:this.group_colors
				}
						
					
			};
		}
		this.executeProjectAction("get_gene_data",args).then(function(resp){
			let data = resp.data;
			let cf = "c"+self.selected_cluster;
			for (let sample of self.samples){
				let sid= sample["id"]
				for (let v of data){
					let val = v[cf][sid-1];
					if (val!=null){
						sample[exp_id+"_"+v["field_id"]]=val;
					}	}
			}
			if (action==="add"){
				self.filter_panel.addChart(chart_data);
			}
			else{
				self.filter_panel.charts[id].refreshPositions();
			}
			
			
		})
		
	}
	
	

	
	
	
	addExperimentPanel(experiment){
		let self = this;
		let op=$("<div>").appendTo(this.dialog_panel);
		let exp_title_div=$("<div>").appendTo(op).data("state","closed")
		.css({"max-width":"200px","background-color":"#17a2b8","cursor":"pointer","margin-bottom":"2px","margin-top":"2px"});
		$("<h6>"+experiment.name+"</h6>").css("display","inline-block").appendTo(exp_title_div);
		$("<i class='fas fa-caret-right'>").appendTo(exp_title_div).css({"font-size":"20px","margin-right":"3px","float":"right"});
		let gp = $("<div>").css("display","none").appendTo(op);
		exp_title_div.click(function(e){
			let th= $(this);
			if (th.data("state")==="closed"){
				gp.show();
				let i = th.find("i");
				i.removeClass("fa-caret-right").addClass("fa-caret-down");
				th.data("state","open")
			}
			else{
				gp.hide();
				let i = th.find("i");
				i.removeClass("fa-caret-down").addClass("fa-caret-right");
				th.data("state","closed");
			}
		})
		
		
		
		gp.append($("<span>").text(experiment.main_data.name+":").css({"font-weight":"bold","margin-right":"2px"}));
		let sel = $("<select>").attr("id","sel-datatype-exp-"+experiment.id);
		for (let dt of experiment.main_data.datatypes){
			sel.append($("<option>").text(dt.name).val(dt.col_name))
		}
		sel.change(function(e){
			self.displayTypeChanged(experiment,sel.val());
		})
		gp.append(sel);
		gp.append("<br>");
		let i =$("<input>").data("exp_id",experiment.id).appendTo(gp);
	 
		this.setUpAutocomplete(i,experiment.id,gp);
		this.exp_index[experiment.id]=experiment;
		i =$("<i>").attr("class","fas fa-list mev-icon")
			.data("exp_id",experiment.id)
			.click(function(e){
				self.showGeneListInput($(this).data("exp_id"));
			}).appendTo(gp);
	
		let d = $("<div>").attr("id","gene-panel-"+experiment.id).appendTo(gp);
		d.click(function(e){
			let i = $(e.target);
			let gid=i.data("gene_id");
			let type = i.data("type");
			let gene_name = i.data("gene_name")
			if (gid){
				if (type==="view"){
					self.selected_genes[experiment.id]=[gid,gene_name];
					self.getIndividualGeneData(experiment)
				}
				else if (type==="remove"){
					i.parent().remove();
					delete self.genes[gid];
					delete self.chosen_genes[gid];
					if (Object.keys(self.chosen_genes).length===0){
						$("#mev-group-submit-"+experiment.id).attr("disabled",true);
						$("#mev-group-remove-"+experiment.id).attr("disabled",true);
					}
					else{
						$("#mev-group-submit-"+experiment.id).attr("disabled",false);
					}
					
				}
			}
		});
		
		
		$("<button>").attr({"class":"btn btn-primary btn-sm mev-btn-sm",id:"mev-group-submit-"+experiment.id,disabled:true})
		.text("update")
		.click(function(e){
			self.getGeneData(experiment,true);
			$(this).attr("disabled",true)
		}).appendTo(gp);
		
		$("<button>").attr({"class":"btn btn-secondary btn-sm mev-btn-sm",id:"mev-group-remove-"+experiment.id,disabled:true})		
		.text("Remove All")	
		.click(function(e){
			self.removeAllGenes(experiment.id)
			
		}).appendTo(gp);
		
		
		let od_panel=$("<div>").appendTo(gp);
		for (let od of experiment.other_data){
			od_panel.append(od.name);
			$("<input>").data("exp",od).appendTo(od_panel)
			.attr({type:"checkbox",id:experiment.id+"_"+od.col_name}).click(function(e){
				if ($(this).prop("checked")){
					self.addUpdateGraph(experiment.id,$(this).data("exp"),"add");
				}
				else{
					self.removeExtraGraph(experiment.id,$(this).data("exp"));
				}
			})
			
		}
		
		
		
	}
	
	removeAllGenes(exp_id){
		let d= $("#gene-panel-"+exp_id);
		let self =this;
		d.find(".mev-chosen-gene").each(function(i,e){
			let id = $(e).data("gid");
			delete self.genes[id];
			delete self.chosen_genes[id];
		});
		d.find(".mev-chosen-gene").remove();
		$("#mev-group-submit-"+exp_id).attr("disabled",true);
		$("#mev-group-remove-"+exp_id).attr("disabled",true);
		
	}
	
	
	
	setUpAutocomplete(input,exp_id){
		let self =this;
		input.css({"padding":"2px","margin-top":"2px","margin-bottom":"2px"}).autocomplete({
				minLength:2,
				source:function(request,response){
					
					self.executeProjectAction("get_gene_suggest",{term:request.term,eid:exp_id}).then(function(data){
						response(data.data);
					})
				},
				select:function(e,ui){
					self.addChosenGene(ui.item.label,ui.item.value,exp_id);
					input.val("");
					return false;
				}
			})
	}
	
	
	hexToRGB(h) {
		  let r = 0, g = 0, b = 0;

		  // 3 digits
		  if (h.length == 4) {
		    r = "0x" + h[1] + h[1];
		    g = "0x" + h[2] + h[2];
		    b = "0x" + h[3] + h[3];
		  // 6 digits
		  } else if (h.length == 7) {
		    r = "0x" + h[1] + h[2];
		    g = "0x" + h[3] + h[4];
		    b = "0x" + h[5] + h[6];
		  }
		  
		  return "rgba("+ +r + "," + +g + "," + +b + ",0.6)";
		}
	
	
	populateWithGenes(data){
		let exp_ids={};
		this.filter_panel.removeChart("cluster-hm-featureset");
		for (let e of this.experiments){
			this.heat_map_genes[e.id].ids=[];
			this.heat_map_genes[e.id].id_to_name={};
			delete this.heat_maps[e.id].graph;
			this.heat_maps[e.id].cluster=1;
			this.heat_maps[e.id].type=0; 
			
		}
		
		for (let item of data){
			
			this.heat_map_genes[item.exp_id].ids.push(item.id);
			this.heat_map_genes[item.exp_id].id_to_name[item.id]=item.name;
			exp_ids[item.exp_id]=true
		}
		
		for (let exp_id in exp_ids){
			this.getGeneData(this.exp_index[exp_id],"replace")
		}
		
		
		
	}
	

	
}


class MEVGeneChooser{
	constructor(div,project_id,exp_id,callback){
		this.project_id=project_id;
		this.exp_id=exp_id;
		this.callback=callback;
		let input = $("<input>").appendTo(div);
		this.setUpAutocomplete(input,exp_id);
		let self =this;
		$("<i>").attr("class","fas fa-list mev-icon")
			.click(function(e){
				self.showGeneListInput();
			}).appendTo(div);
	}
	
	showGeneListInput(){
		let ta= $("<textarea>").css("width","100%");
		let self =this;
		$("<div>").append(ta).dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:"Paste Gene List",
			buttons:[{
				text:"submit",
				click:function(e){
					self.getGeneInfo(ta.val().split(/(\s+)/).filter(Boolean));
					$(this).dialog("close");
					
				}
			}]
			
		}).dialogFix();
	}
	
	getGeneInfo(gene_list){
		let args = {
			exp_id:this.exp_id,
			gene_list:gene_list	
		};
		let self =this;
		this.executeProjectAction("get_gene_info",args).then(function(resp){
			self.callback({data:resp.data,exp_id:self.exp_id});				
		});
	}
	
	
	
	
	
	setUpAutocomplete(input,exp_id,div){
		let self =this;
		input.autocomplete({
			minLength:2,
			source:function(request,response){
				self.executeProjectAction("get_gene_suggest",{term:request.term,eid:exp_id}).then(function(data){
					response(data.data);
				})
			},
			select:function(e,ui){
				let data=[{
					name:ui.item.label,
					id:ui.item.value
					
				}];
				self.callback({data:data,exp_id:self.exp_id});
				return false;
			}
		});
	}
	
	executeProjectAction(action,args){
		if (!args){
			args={}
		}	
		let data={
			method:action,
			args:args	
		}
		return fetch("/meths/execute_project_action/"+this.project_id,
		{
			method:"POST",
			body:JSON.stringify(data),
			headers:{
				"Accept":"application/json,text/plain,*/*",
				"Content-Type":"application/json"
			}
			
		}).then(resp=>resp.json());
	}	
}




class MEVDataViewer extends MEVViewer{
	constructor(data,div_id){
		super(data,div_id);
		this.exp_id=data.data["exp_id"];
		this.exp_size=data.data["exp_size"];
		this.column_index={};
		let self =this;
		this.menu_div= $("<div>")
		.css({"height":"30px","overflow":"hidden","white-space":"nowrap"})
		.appendTo("#fp-samples");
		$("<div>").css({height:"calc(100% - 30px)"}).attr("id","the-table-div").appendTo("#fp-samples");
		this.w_dialog= new WaitingDialog("Loading Data");
		this.w_dialog.wait("Loading sample data");
		this.init(data.data)
	
	
	}
	
	getState(){
		
		this.current_view.graphs= this.filter_panel.getGraphs();
		return this.current_view;	
		
	}
	
	
	addDataToView(data){
		for (let col of data.columns){
    		this.columns.push(col);
    		this.column_index[col.id]=col;
    	}
		if (data.data){
			for (let id in data.data ){
        		let row = this.table.data_view.getItemById(parseInt(id));
        		if (!row){
        			continue;
        		}
        		let item =data.data[id]
        		for (let field in item){
        			row[field]=item[field]
        		}		
        	}
			
		}
		this.table.addColumns(data.columns);
    	this.table.updateGroupPanel();
    	this.filter_panel.setColumns(this.columns);
    	if (data.graphs){
    		for (let graph of data.graphs){
    			this.filter_panel.addChart(graph);   	
    		}
    	}	
	}
	
	
	
	
	addTagColumn(){
		let self = this;
		let d = $("<div>");
		d.append("<label>Tag Column Name:<label><br>")
		let input= $("<input>").appendTo(d);
		d.dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:"Add Tagging Column",
			buttons:[{
				text:"Add",
				id:"add-column-submit",
				click:function(e){
					if (d.data("all_done")){
						$(this).dialog("close");
					}
					else{
						let name = input.val();
						if (name){
							self.executeProjectAction("add_tagging_column",{name:name}).then(function(resp){
								if (resp.success){
									self.addDataToView(resp.data);
									let col =resp.data.columns[0];
									self.tag_column_select.append($("<option>").text(col.name).val(col.field))
									d.data("all_done",true)
									d.html("<div class='alert alert-success'>The column has been added. Use the <i class='fas fa-tag'></i> icon to add tags</div>");
								}
								$("#add-column-submit").text("OK")
								
							})
						}
					}
					
				}
			}]
			
		}).dialogFix();
		
	}
	
	
	getFields(field_ids,next){
		let self = this;
		
		this.executeProjectAction("get_experiment_data",{field_ids:field_ids}).then(function(resp){
			self.w_dialog.setWaitingMessage("Formatting Data");
			let cols = resp.data.columns;
			let rd= resp.data.data
			let dv = self.table.data_view;
			let dcs=[];
			let gcs=[];
			
			for (let c of cols){
				if (c.gene_column){
					gcs.push(c)
				}
				else{
					dcs.push(c)
				}
			}
			for (let i= 0;i<self.exp_size;i++){
				let item = dv.getItemById(i);
				for(let col of dcs){
					if (col.index == null){
						if (col.col_names){
							item[col.field]=col.col_names[rd[col.data_col][i]];
						}
						else{
							item[col.field]=rd[col.data_col][i];
						}
					}
					else{
						item[col.field]=rd[col.data_col][i][col.index-1]
					}
				}
			}
			
			for (let c of gcs){
				let d= resp.data.data[c.data_col];
				for (let id in d){
					let item = dv.getItemById(id);
					item[c.field]=d[id]
				}
			}
			
			for (let col of cols){
				delete col["data_col"];
				delete col["index"];
				delete col["gene_column"]
				delete col["col_names"]
				col.id=col.field;
				let cg= col.columnGroup;
				if (cg){
					if (!self.column_groups[cg]){
						col.master_group_column=true;
					}
					self.column_groups[cg]=true;
				}
			}
			self.columns = self.columns.concat(resp.data.columns)
			if (next){
				self.table.addColumns(self.columns);
			}
			else{
				self.current_view.fields=  self.current_view.fields.concat(field_ids);
				self.table.addColumns(resp.data.columns);
			}
			
			
	    	self.table.updateGroupPanel();
	    	self.filter_panel.setColumns(self.columns);
	    	if (next){
	    		if (self.current_view.graphs){
	    			for (let g of self.current_view.graphs){
	    				self.filter_panel.addChart(g);
	    			}
	    		}
	    	}
	    	self.w_dialog.remove();
		
		});
		
	}
	
	getSampleData(ids,next){
		let self = this;
		this.executeProjectAction("get_sample_data",{ids:ids}).then(function(resp){
			let rd= resp.data.data
			let dv = self.table.data_view;
			let cols = resp.data.fields;
			let sid_to_data={};
			for (let item of rd){
				sid_to_data[self.id_to_sample[item.id]]=item
				delete item.id
			}
			for (let item of dv.getItems()){
				let sample=sid_to_data[item.s];
				for (let key in sample){
					item[key]=sample[key]
				}
			}
			if (!self.column_groups["Sample Data"]){
				cols[0].master_group_column=true;
			}
			self.column_groups["Sample Data"]=true;
			self.columns = self.columns.concat(cols)
			
	    	if (next){
	    		self.w_dialog.setWaitingMessage("Loading Gene/Other Data");
	    		self.getFields(self.current_view.fields,true)
	    	}
	    	else{
	    		self.current_view.sample_fields=  self.current_view.sample_fields.concat(ids);
				self.table.addColumns(cols);
		    	self.table.updateGroupPanel();
		    	self.filter_panel.setColumns(self.columns);
		    	self.w_dialog.remove();    		
	    	}
	    	
		
		});
		
	}
	

	
	
	
	init(data){
		let self = this;
		this.columns=[];
		this.column_groups={};
		let d=[];
		for (let i=0;i<data["exp_size"];i++){
			d.push({"id":i,"s":data.sample_ids[i]});
		}
		this.id_to_sample={};
		
		for (let i=0;i<data.sample_index_to_id.length;i++){
			this.id_to_sample[data.sample_index_to_id[i]]=i;
		}
		
		this.filter_panel= new FilterPanel("fp-heatmaps",d,
				{menu_bar:true})
		this.data_view=new FilterPanelDataView(this.filter_panel);
		
		let td = $("<div>").attr("id","the-table-div-1").css("height","100%").appendTo("#the-table-div");
		
		this.table= new MLVTable("the-table-div-1",this.columns,this.data_view,{
			has_column_groups:true 

		});
		
	
		this.table.addListener("row_clicked_listener",function(item,column,e){
			self.filter_panel.highlightDataItem(item.id);
		});
		let gc_div=$("<div>").css("display","inline-block").appendTo(this.menu_div);
		this.gene_chooser= new MEVGeneChooser(gc_div,this.project_id,this.exp_id,function(genes){
			self.loadChosenGenes(genes);
		});
		$("<button>").attr("class","btn btn-sm btn-secondary")
		.text("Save")
		.click(function(e){
			self.save_menu.show(null,e)
		}).appendTo(this.menu_div);
		
		this.setUpSaveMenu();
		/*if (this.permission==="edit"){
			
			let p = $("<i>").attr("class","fas fa-plus mev-icon")
			.attr({title:"Add Tag Column","data-toggle":"tooltip"})
			.click(function(e){
				self.addTagColumn();
			});
			this.filter_panel.addMenuIcon(p);
			this.tag_column_select=$("<select>");
			this.tag_column_value=$("<input>").css("width","100px");
			this.filter_panel.addMenuIcon(this.tag_column_select);
			this.filter_panel.addMenuIcon(this.tag_column_value);
			for (let col of this.temp_data.columns){
				if (col.columnGroup==="Tags"){
					this.tag_column_select.append($("<option>").text(col.name).val(col.field));
				}
			}
			let i = $("<i>").attr("class","fas fa-tag mev-icon")
			.attr({title:"Tag selected items","data-toggle":"tooltip"})
			.click(function(e){
				self.tagFilteredItems();
			});
			this.filter_panel.addMenuIcon(i);
		
		}*/
		this.current_view=data.current_view;
	    $('[data-toggle="tooltip"]').tooltip();
	    this.getSampleData(data.current_view.sample_fields,true);
	 	
	}
	
	
	
	
	loadChosenGenes(genes){
		let gene_ids=[];
		let already=[];
		let self = this;
		for (let gene of genes.data){
			if (this.column_index[gene.id]){
				already.push(gene.name)
			}
			
				gene_ids.push(gene.id)
			
		}
		
		if (gene_ids.length>0){
			this.w_dialog= new WaitingDialog("Loading Data");
			this.w_dialog.wait("Loading Data");
			this.getFields(gene_ids);
		}
	}
	
	addImageTable(data){
		this.table_mode="table";
		let dv = new  MLVDataView(data.data);
		let self=this;
		let itd=$("<div>").attr("id","the-table-div-2")
		.css({height:"100%",display:"none"}).appendTo("#the-table-div");
		let columns= [
				{
					"field":"cluster_field",
					"name":"Cluster"
				},
				{
					"field":"cluster_id",
					"name":"Cluster ID"
				},
				
				{
					"field":"group",
					"name":"Value Type"
				},
				{
					"field":"group_id",
					"name":"Value"
				},			
				{
					"field":"boxes",
					"name":"Boxes"
				}	
			
		];
		for (let col of columns){
			col.datatype="text";
			col.sortable=true,
			col.filterable=true;
		}
		
		this.image_table = new MLVImageTable("the-table-div-2",dv,
			{
			base_url:data.link,
			initial_image_width:200,
			show_info_box:true
			
			
			});
		this.image_table.setColumns(columns);
		let i = $("<i>").attr("class","fas fa-chart-bar mev-icon")
		.attr({title:"Toggle table/static graphs","data-toggle":"tooltip"})
		.click(function(e){
			self.switchTableMode($(this))
		}).prependTo(this.menu_div);
		
		this.image_slider = $("<div>").attr({"id":"mlv-it-image-slider"})
        .css({width:"100px",display:"inline-block"}).slider({
	        max:200,
	        min:0,
	        value:100,
	        stop:function(e,ui){
	             let val =ui.value/100;
	             let width = parseInt(self.image_table.img_width*val);
	             let height= parseInt(self.image_table.img_height*val);
	             self.image_table.setImageDimensions([width,height],true);
	             //self.image_table.show();
	        }
        }).appendTo(this.menu_div).hide();
		
		this.addMenuItem(this.menu_div,"fas fa-filter","Filter Graphs",function(e){
			self.image_table.showFilterDialog();
		});
		
	}
	
	switchTableMode(icon){
		if (this.table_mode==="table"){
			icon.removeClass("fa-chart-bar");
			icon.addClass("fa-table");
			$("#the-table-div-1").hide();
			$("#the-table-div-2").show();
			this.table_mode="graphs";
			this.image_table.resize();
			this.image_slider.show();
			
		}
		else{
			icon.removeClass("fa-table");
			icon.addClass("fa-chart-bar");
			$("#the-table-div-2").hide();
			$("#the-table-div-1").show();
			this.table_mode="table";
			this.image_slider.hide();
			
			
		}
	}
	
	tagFilteredItems(){
		let items = this.table.data_view.getFilteredItems();
		let val = this.tag_column_value.val();
		let field = this.tag_column_select.val();
		if (!field){
			return;
		}
        let ids=[]
        for (let item of items){
        	ids.push(item.id)
            if (val){
                item[field]=val;
            }
            else{
                delete item[field];
            }
        }
        this.executeProjectAction("update_tagging_column",{ids:ids,value:val,field:field}).then(function(e){
        	
        })
        this.table.data_view.listeners.data_changed.forEach((func)=>{func(field)});
        this.table.grid.invalidate();
        //this.tablegrid.render();

	}
	
	
}





class ChooseExperimentDialog{
	constructor(project_id,div){
		this.outer_div= $("#"+div)
		this.div=$("<div>").attr("class","row").appendTo(this.outer_div);
		this.project_id=project_id;
		this.executeProjectAction("get_all_experiments").then(resp=>{
			this.init(resp.data);
		})
	}
	
	init(data){
		let self =this;
		let e_div =$("<div>").attr("class","col-sm-2").append("<h5>1. Select Experiment</h5>").appendTo(this.div);
		this.exp_div = $("<div>").attr("class","list-group").appendTo(e_div);
		let r_div =$("<div>").attr("class","col-sm-4").append("<h5>2. Select Rows</h5>").appendTo(this.div);
		this.row_div = $("<div>").attr("class","list-group ").appendTo(r_div);
		let c_div =$("<div>").attr("class","col-sm-6").append("<h5>3. Select Columns</h5>").appendTo(this.div);
		this.column_div=$("<div>").attr("class","list-group ").appendTo(c_div);
		for (let item of data){
			let lgi= $("<div>").attr("class","list-group-item dv-hover")
			.click(function(e){
				self.loadExperiment($(this).data("exp"));
				$(".dv-hover").css("background-color","white");
				$(this).css("background-color","lightgray");
			})
			.data("exp",item)
			.appendTo(this.exp_div);
			let o = $("<div>").attr("class","d-flex w-100 justify-content-between").appendTo(lgi);
			$("<h5>").text(item.name).appendTo(o);
			$("<small>").text(item.data["item_count"]).appendTo(o);
			$("<p>").text(item.description).appendTo(lgi);
			
		}
		let d = $("<div>").attr("class","d-flex justify-content-center").appendTo(this.outer_div);
		$("<button>").text("Submit").attr("class","btn btn-primary")
		.click(function(e){
			self.submit()
		})
		.appendTo(d);
		
		
	}
	
	loadExperiment(exp){
		this.executeProjectAction("get_experiment_columns",{id:exp.id}).then(resp=>{
			this.populateGetRows(resp.data,exp);
		})
	}
	
	populateGetRows(cols,exp){
		this.row_div.empty();
		this.column_div.empty();
		let col_name_list = [];
		this.id_to_col={};
		let self = this;
		this.experiment= exp.id;
		for (let item of cols){
			col_name_list.push({
				label:item.name,
				value:item.id
				
			});
			this.id_to_col[item.id]=item;
		}
		let count = exp.data["item_count"];
		let all_div=$("<div>").attr("class","list-group-item sr-item").appendTo(this.row_div);
		
		$("<input>").attr({type:"radio",name:"mev-row-choice",value:"all","class":"dv-large-radion"})
		.appendTo(all_div);
		$("<span>").text("All Rows("+count+")").appendTo(all_div)
	
		
		
		let subset_div=$("<div>").attr("class","list-group-item sr-item").appendTo(this.row_div);
		$("<input>").attr({type:"radio",name:"mev-row-choice",value:"subset"}).appendTo(subset_div);
		$("<span>").text("Subset").appendTo(subset_div);
		let suggest = Math.ceil(count/1000)*100;
		this.count_input= $("<input>").attr({type:"text",value:suggest}).appendTo(subset_div);
		

		let query_div=$("<div>").attr("class","list-group-item sr-item").appendTo(this.row_div);
		$("<input>").attr({type:"radio",name:"mev-row-choice",value:"query"}).appendTo(query_div);
		$("<span>").text("Query").appendTo(query_div);
		let df = $("<div>").appendTo(query_div);
		this.query= new RowQueryBuilder(col_name_list,this.id_to_col,df);
		
		
	
		this.column_choose = new MEVColumnCheck(this.column_div,cols,null,this.experiment,this.project_id);
		
		$("input[name=mev-row-choice]").click(function(e){
			$(".sr-item").css("background-color","white");
			if ($(this).val()==="subset"){
				self.count_input.focus();
			}
			if ($(this).val()==="query"){
				self.query.focus();
			}
			$(this).parent().css("background-color","lightgray");
		})
	
		
		
	}
	
	submit(){
		let to_send ={};
		let data= {}
		let query_type = $("input[name=mev-row-choice]:checked").val();
		to_send.experiment=this.experiment;
		let cols =this.column_choose.getCheckedColumns();
		to_send.fields = cols.columns;
		to_send.sample_fields= cols.sample_columns;
		if (query_type ==="subset"){
			data.count= parseInt(this.count_input.val())
		}
		else if (query_type === "query"){
			data.query= this.query.getQuery()
		}
		to_send.data=data;
		to_send.query_type=query_type;
		new WaitingDialog("Processing").wait("Processing");
		
		this.executeProjectAction("build_experiment_query",to_send).then(function(resp){
			location.reload();
		})
		
	}
	
	
	
	
	
	executeProjectAction(action,args){
		if (!args){
			args={}
		}
		
		let data={
			method:action,
			args:args	
		}
	
		return fetch("/meths/execute_project_action/"+this.project_id,
		{
			method:"POST",
			body:JSON.stringify(data),
			headers:{
				"Accept":"application/json,text/plain,*/*",
				"Content-Type":"application/json"
			}
			
		}).then(resp=>resp.json());
	}
	
	
}

class MEVColumnCheck{
	constructor(div,columns,filter,exp_id,proj_id){
		this.columns=columns;
		
		this.calculateGroups(columns,filter);
		this.exp_id=exp_id;
		this.project_id=proj_id;
		let self = this;

		for (let name of this.group_names){
			let li = this.groups[name];
			
			let ti = $("<h6>").text(name).appendTo(div);	
			let col_div=$("<div>").appendTo(div);
			if (li.length>100){
				let li_input = $("<i class = 'fas fa-list mev-icon'></i>").click(function(e){
					self.showGeneListInput(col_div)
				}).appendTo(col_div);
				continue;
				
			}
			this.addGroupCheckBox(ti,col_div);
			
			
			
		
			for (let col of li){
				let parent =$("<div class='form-check form-check-inline'></div>");
				let id = "cluster-field-"+col.id;
				let check = $("<input>").attr({
					"class":"form-check-input",
					type:"checkbox",
					id:id
				}).data("id",col.id);
				let label = $("<span>").attr({
					"for":id
					}).text(col.name)
					parent.append(check).append(label).appendTo(col_div);
			}
		}
		
	}
	
	getGeneInfo(gene_list,exp_id,div){
		let args = {
				exp_id:exp_id,
				gene_list:gene_list
				
		};
		let self =this;
		this.executeProjectAction("get_gene_info",args).then(function(resp){
				console.log(resp.success);
				for (let gene of resp.data){
					self.addChosenGene(gene.name,gene.id,div);
				}
		});
	}
	executeProjectAction(action,args){
		if (!args){
			args={}
		}
		
		let data={
			method:action,
			args:args	
		}
	
		return fetch("/meths/execute_project_action/"+this.project_id,
		{
			method:"POST",
			body:JSON.stringify(data),
			headers:{
				"Accept":"application/json,text/plain,*/*",
				"Content-Type":"application/json"
			}
			
		}).then(resp=>resp.json());
	}
	
	
	addChosenGene(gene_name,gene_id,div){
		let parent =$("<div class='form-check form-check-inline'></div>");
		let id = "cluster-field-"+gene_id;
		let check = $("<input>").attr({
			"class":"form-check-input",
			type:"checkbox",
			id:id
		}).data("id",gene_id).prop("checked",true);
		let label = $("<span>").attr({
			"for":id
			}).text(gene_name)
			parent.append(check).append(label).appendTo(div);
		
	}
	
	showGeneListInput(div){
		let ta= $("<textarea>").css("width","100%");
		let self =this;
		$("<div>").append(ta).dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:"Paste Gene List",
			buttons:[{
				text:"submit",
				click:function(e){
					self.getGeneInfo(ta.val().split(/(\s+)/).filter(Boolean),self.exp_id,div);
					$(this).dialog("close");
					
				}
			}]
			
		}).dialogFix();
		
	}
	
	
	addGroupCheckBox(loc,div){
		$("<input>").attr({type:"checkbox"}).appendTo(loc)
		.click(function(e){
			let c= $(this).prop("checked")
			div.find("input").prop("checked",c)
		})
	}
	
	getCheckedColumns(){
		let ch_li=[];
		let sc_li=[];
		for (let c of this.columns){
			if ($("#cluster-field-"+c.id).prop("checked")){
				if (c.group==="Sample"){
					sc_li.push(c.id)
				}
				else{
					ch_li.push(c.id)
				}
			}
		}
		return {"columns":ch_li,"sample_columns":sc_li};
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
			if (c.group){
				let li = groups[c.group]
				if (!li){
					li=[];
					group_list.push(c.group)
					groups[c.group]=li
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

class RowQueryBuilder{
	constructor(columns,id_to_col,div){
		let self = this;
		this.id_to_col=id_to_col;
		this.field_input=$("<input>").appendTo(div)
		.autocomplete({
			source:columns,
			select:function(e,ui){
				self.updateOperand(ui.item.value);
				 e.preventDefault();
				 $(this).val(ui.item.label);
				 self.field_id=ui.item.value;
			}
		})
		this.operand_select = $("<select>").appendTo(div);
		this.value_input = $("<input>").appendTo(div)
		
	}
	
	focus(){
		this.field_input.focus();
	}
	
	getQuery(){
		return {
			field:this.field_id,
			operand:this.operand_select.val(),
			value:this.value_input.val()
						
		}
	}
	
	updateOperand(col_id){
		let col = this.id_to_col[col_id];
		let sel = this.operand_select;
		sel.empty();
		if (col.datatype==="text"){
			sel.append($("<option>").text("!=").val("!="));
			sel.append($("<option>").text("=").val("="));
			sel.append($("<option>").text("in").val("in"));
		}
		else{
			sel.append($("<option>").text("=").val("="));
			sel.append($("<option>").text(">").val(">"));
			sel.append($("<option>").text("<").val("<"));
			sel.append($("<option>").text("!=").val("!="));
		}
	}
	
}
