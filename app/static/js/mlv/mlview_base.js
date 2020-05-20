
class MLViewBase{
	constructor(div,project,config){
		this.config=config;
		this.project_id=project.id;
    	this.project_name=project.name;
    	this.genome=project.data.genome;
    	this.permission = project.permission;
    	this.project_type=project.type;
    	this.anno_project_types=[];
    	this.update_browser_view=true;
    	
    	this.setUpSplit(div);
    	
    	this.waiting_icon= new WaitingIcon("mlv-table");
    	this.waiting_icon.show("Loading Data");
   
    	this.view_margins=500;
    	
    	let self =this;
    	
    	let data={
    		method:"get_viewset",
    		args:{}
    	}
    	
		if (config.filters){
			data.args.filters=config.filters;
		}
    	this.table_mode="table";
    	$.ajax({
		    url:"/meths/execute_project_action/"+project_id,
		    dataType:"json",
		    contentType:"application/json",
		    data:JSON.stringify(data),
		    type:"POST"
		}).done(function(response){
			self.parseData(project,response.data);
			 self.setUpTracks(project.data,response.data);
			 if (self.config.graphs){
				 self.setUpFilterPanel(response.data,project.data);
			 }
			 self.setUpTable(response.data,project.data,config);
		}); 	
    
	}
	
	parseData(){}
	
	setUpSplit(container){
		let div =$("#"+container);
	
		div.css("height","100%")
		this.browser_div = $("<div>").attr({id:"browser-panel"});
		let graphs = this.config.graphs;
		if (graphs){
			let lp = $("<div>").attr({id:"left-panel","class":"split split-horizontal"});
			let lt = $("<div>").attr({id:"left-top","class":"split split-vertical"})
						.css({overflow:"hidden",height:"100%"});
			let fp = $("<div>").attr("id","filter-panel")
						.css({overflow:"hidden",height:"100%"})		
			this.browser_div.attr("class","split split-vertical");
			lt.append(fp)
			if (graphs.position==="top"){
				lp.append(lt).append(this.browser_div);
			}
			else{
				lp.append(this.browser_div).append(lt);
			}
			div.append(lp);
			
				
		}
		else{
			this.browser_div.attr("class","split split-horizontal")
			div.append(this.browser_div);
		}
		
		let tbh= $("<div>").attr({id:"mlv-table-holder","class":"split split-horizontal"});
		div.append(tbh);
		if (graphs){
			Split(['#left-panel', '#mlv-table-holder'], {
				sizes: [50, 50],
				direction:"horizontal",
				gutterSize:5,
				onDragEnd:function(){$(window).trigger("resize")}
			});
			let order = ['#left-top', '#browser-panel'];
			let sizes=[30,70]
			if (graphs.position==="bottom"){
				order = [ '#browser-panel','#left-top'];
			}
			if (graphs.sizes){
				sizes=graphs.sizes;
			}
			Split(order, {
				sizes: sizes,
				direction:"vertical",
				gutterSize:5,
				minSize:20,
				onDragEnd:function(){
					$(window).trigger("resize");
				}
			});
			
		}
		else{
			Split(['#browser-panel', '#mlv-table-holder'], {
				sizes: [50, 50],
				direction:"horizontal",
				gutterSize:5,
				onDragEnd:function(){$(window).trigger("resize")}
			});
			
		}
		if (this.config.table_split){
			$("<div>").attr({id:"mlv-table","class":"split split-vertical"}).appendTo(tbh);
			$("<div>").attr({id:"mlv-table-bottom","class":"split split-verrical"}).appendTo(tbh);
			Split(['#mlv-table', '#mlv-table-bottom'], {
				sizes: [70, 30],
				direction:"vertical",
				gutterSize:5,
				onDragEnd:function(){$(window).trigger("resize")}
			});
		}
		else{
			$("<div>").attr({id:"mlv-table"}).css("height","100%").appendTo(tbh);
		}
	
		
		
	
		
	}
	
	setUpTracks(project_data,view_data){
    	let self = this;
    	let tracks_proxy = {
    		"http://userweb.molbiol.ox.ac.uk":"/molbiol_ox",
        	"http://sara.molbiol.ox.ac.uk":"/sara_molbiol_ox",
        	"http://genome.molbiol.ox.ac.uk":"/genome_molbiol_ox"
    	}
    	let add_ruler=true;
    	for (let tr of project_data.browser_config.state){
    		if (tr.type==="ruler"){
    			add_ruler=false;
    			break;
    		}
    	}
    	
    	this.browser= new SinglePanelBrowser("browser-panel",
    			project_data.browser_config.state,
    			{add_controls:true,tracks_proxy:tracks_proxy,add_ruler:add_ruler,
    			allowed_track_types:["bed","bigwig","bigbed","bam","ucsc_track","ruler"]}
    	);
    	this.browser_config = project_data.browser_config;
    	
    	let sel= $("<select id ='img-type-option'><option>png</option><option>svg</option><option>pdf</option><select>");
		let op = $("<i class='fas fa-camera-retro'></i>")
			.css({cursor:"pointer","margin-left":"4px","margin-right":"2px"})
			.attr({title:"Create Image","data-toggle":"tooltip"})
			.click(function(){
				self.saveBrowserImage();
			});
		this.browser.addToMenu(op);
		this.browser.addToMenu(sel);
		this.browser.panel.addListener("track_removed",function(c){
			self._saveState();
		})
		
		
    
    	
    
    	this.addMainTrackInteraction(view_data.views);    	
    	let cog = $("<i class='fas fa-cog'></i>")
		.css({cursor:"pointer","margin-left":"4px","margin-right":"2px"})
		.attr({title:"Feature Track Settings","data-toggle":"tooltip"})
		.click(function(){
			self.showFeatureTrackDialog();
		})
		this.browser.addToMenu(cog);
		
    	
    		
    	
    }
	
	addMainTrackInteraction(data,click_func){
		let ft = this.browser_config.feature_track;
		if (!ft){
			return;
		}
		let track_id = ft.track_id;
		let panel = this.browser.panel;
		let self=this;
		panel.allowUserFeatureClick();
		if (click_func){
			panel.addListener("feature_clicked",click_func);
		}
		else{
	    	panel.addListener("feature_clicked",function(track,feature){
	    		if (track.config.track_id===track_id){
	    			if (!feature){
	    				return;
	    			}
	    			let row =self.table.data_view.getRowById(feature.id);
	    			self.update_browser_view=false;
	    			self.table.grid.setSelectedRows([row]);
	    			self.update_browser_view=true;
	    			if (self.image_table){
	    				self.image_table.setSelectedTiles([feature.id])
	    			}
	    			if (self.table_mode==="images"){
	    				self.image_table.show(row);
	    				self.image_table.showInfoBox(self.table.data_view.getItemById(feature.id))
	    			}
	    			else{
	    				self.table.grid.scrollRowToTop(row);
	    			}
	    			
	    			self.current_feature=feature.id;
	    			
	    		}
	    	});
		}
    	panel.setTrackFeatureFilter(track_id,function(item){	
    		let row = self.table.data_view.getRowById(item.id)
    		return (row || row===0);
    	});
  
    	this.main_panel=panel;
    
    	let color_by = ft.color_by;
    	if (color_by){
			let field = color_by.column.field
			let cs = FilterPanel.getColorScale(color_by.column,
					data,
					color_by.scheme,
					"browser-panel");
			
			self.browser.panel.setTrackColorFunction(track_id,function(feature){
				let row = self.table.data_view.getItemById(feature.id)
				return cs.func(row[field])
			});
			
		}
    	
    	
    	
	}
	
    showCreateSubsetDialog(){
    	let self = this
    	let div =  $("<div>")
    	this.subset_dialog = div
    	.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    			self.subset_dialog=null;
    		},
    		title:"Create Subset"
    	}).dialogFix();
    
    	let num= this.table.data_view.getLength();
    	
    
		let sp = $("<input id='subset-region-number'>").width(60);
	
	
		$("<input>").attr({type:"radio",name:"subset-choice",value:"subset","checked":true}).appendTo(div);
		div.append("<span>From "+num+" filtered regions</span><br>");
		$("<input>").attr({type:"radio",name:"subset-choice",value:"random"}).appendTo(div);
		div.append("<span>From</span>").append(sp).append(" random regions");
		sp.spinner({
			min:100,
			max:5000,
			step:100 
		}).val(100);
		let f_d = $("<div>").appendTo(div)
		this.subset_form = new NameDescGenomeForm(f_d,this.project_type,
    			function(pid){
    				self.createSubset(pid);
    			},
    			{genome:this.genome,name:this.project_name+" subset",desc:"Created from "+this.project_name}
    	);
    }
    
    createSubset(project_id){
    	let chosen_ids=[];
    	let self = this;
    	let option = $("input[name='subset-choice']:checked").val();
    	if (option === "random"){
    		let id_list=[];
        	let data = this.table.data_view.getItems(); 
        	for (let item of data){
        		id_list.push(item.id);
        		
        	}
        	let num = $("#pad-peak-number").val();
        	for (let i=0;i<num;i++){
        		let index = Math.floor(Math.random() * id_list.length);
        		chosen_ids.push(id_list[index]);
        		id_list.splice(index,1);
        		if (id_list.length===0){
        			break;
        		}
        		
        	}
    	}
    	else{
    		
    		for (let item of this.table.data_view.getFilteredItems()){
    			chosen_ids.push(item.id);
    		}
    		
    	}
    	let data ={
    			method:"create_subset_from_parent",
    			args:{
    				parent_id:this.project_id,
    				ids:chosen_ids
    				
  			}
    	}
    	$.ajax({
    		url:"/meths/execute_project_action/"+project_id,
    		dataType:"json",
    		type:"POST",
    		data:JSON.stringify(data),
    		contentType:"application/json"
    	}).done(function(response){
    		if (! response.success){
    			$("#pad-information").html(response.msg)
    		}
    		else{
    			self.subset_dialog.dialog("close");
    			self.subset_waiting_dialog=new WaitingDialog("Creating Subset");
    			self.subset_waiting_dialog.wait();
    			self.checkSubsetCreation(project_id);
    		
    		}
    	});
    	
    }
    showFeatureTrackDialog(){
    	new FeatureTrackDialog(this);
    }
    
    checkSubsetCreation(project_id){
    	let self = this;
    	$.ajax({
    		url:"/meths/get_project_data/"+project_id,
    		dataType:"json",
    		type:"GET"
    	}).done(function(response){
    		if (!response.data.creating_subset){
    			if (response.data.subset_creation_failed){
        			self.subset_waiting_dialog.showMessage("Unable to create subset, please contact an administrator","danger")
    			}else{
    				let href = "/projects/"+self.project_type+"/"+project_id;
        			self.subset_waiting_dialog.showMessage("The project has been created and can be viewed <a href='"+href+"'>here</a>","success")
    				
    			} 			
    		}
    		else{
    			setTimeout(function(){
    				self.checkSubsetCreation(project_id)
    			},10000)
    		}
    	})
    }
	
	
	
	setUpFilterPanel(data,project_data){
    	 	
    	let self=this;  	
    	this.filter_panel=new FilterPanel("filter-panel",data.views,{
    		menu_bar:this.config.graphs.menu_bar,
    		graphs:project_data.graph_config
    	});
    	this.initialiseFilterPanel(data,project_data);
    
    }
	
	initialiseFilterPanel(){
	}
	
	getDefaultColumns(reponse,project_data){
		return [
            {"field":"chromosome","name":"Chr","datatype":"text",id:"i1",sortable:true,width:50,filterable:true,columnGroup:"Location"},
            {"field":"start","name":"Start","datatype":"integer",id:"i2",sortable:true,width:100,filterable:true,columnGroup:"Location"},
            {"field":"finish","name":"End","datatype":"integer",id:"i3",sortable:true,width:100,filterable:true,columnGroup:"Location"}
        ];
	}
	
	getCustomColumns(response,project_data){	
		let columns= [];
	
		for (let field in response.fields){
			
			let col = response.fields[field];
			if (col.no_show){
				continue;
			}
			col.field=field
			col.name=col.label
			delete col.label
			col.sortable=true
			col.filterable=true
			col.width=120;
			col.id=col.field
			columns.push(col)
		}
			
		columns.sort(function(a,b){
			if (a.name==="Tags"){
				return -1;
			}
			if (b.name=="Tags"){
				return 1;
			}
			let a_g = a.columnGroup?a.columnGroup:"x";
			let b_g = b.columnGroup?b.columnGroup:"x";
			if (a_g===b_g){
				return a.name.localeCompare(b.name)
			}
			return a_g.localeCompare(b_g);
		});
		
		return columns;
	}
	
	
		
	
	
	setUpTable(response,project_data,config){
		
		this.annotations = response.annotation_information;
		let table_div= "mlv-table";
    	let fields = response.fields;
    	let data= response.views;
    	let self = this;
    	let div = $("#"+table_div);
    	this.setupTableFormatMenu();
    	this.base_image_url = response.base_image_url;
  
    
    	//create menu
    	this.field_information=response.field_information;
    	if (this.field_information.current_tags){
    		this.tagging_field= this.field_information.current_tags["Tags"];
    		this.tagging_options=project_data.tag_color_scheme
    	}
    	let menu_div= $("<div>").attr("class","mlv-menu")
    		.css({"height":"30px","overflow":"hidden","white-space":"nowrap"})
    		.appendTo(div);
    	if (project_data.has_images){
    		this.image_icon= $("<i class='fas fa-table'></i>")
    			.css({"font-size":"18px"})
    			.attr({title:"Change Table Layout","data-toggle":"tooltip"})
    			.appendTo(menu_div)
    			.click(function(e){
				self.table_format_menu.show(null,e);
    			});
    	}
    
    	$("<i class='fas fa-sort-alpha-up'></i>")
    	  .css({"font-size":"18px"})
    	  .attr({title:"Sort Data","data-toggle":"tooltip"})
    	  .appendTo(menu_div)
    	  .click(function(e){
    		  self.table.showSortDialog();
    	  });
    	
    	$("<i class='fas fa-filter'></i>")
  	  		.css({"font-size":"18px"})
  	  		.attr({title:"Filter Data","data-toggle":"tooltip"})
  	  		.appendTo(menu_div)
  	  		.click(function(e){
  		  self.table.showFilterDialog();
  	  	});
    	
    	let d_icon=$("<i class='fas fa-download'></i>Download Data")
			.css({"font-size":"18px"})
			.attr({title:"Download Filtered Data","data-toggle":"tooltip"})
			.appendTo(menu_div)
			.click(function(e){
				let columns = self.table.grid.getColumns();
		    	let splice=-1;
		    	for (let index in columns){
			    	if (columns[index].id==="tn_column"){
			    		splice=index;
			    		break;
			    	}
		    	}
		    	if (splice!==-1){
		    		columns.splice(index,1)
		    	}
				self.table.showDownloadDialog(columns);
			});
    	if (this.permission === "edit"){
    		$("<i class='fas fa-save'></i>")
	  			.css({"font-size":"18px"})
	  			.attr({title:"Save Layout","data-toggle":"tooltip"})
	  			.appendTo(menu_div)
	  			.click(function(e){
	  				self._saveState(true);
	  			});
    	}
    	
    	if (this.config.create_subset && this.permission!=="view_no_log_in"){
    		$("<i class='fas fa-clone'></i>")
  			.css({"font-size":"18px"})
  			.attr({title:"Create Subset","data-toggle":"tooltip"})
  			.appendTo(menu_div)
  			.click(function(e){
  				self.showCreateSubsetDialog();
  			});
    	}
    	
    	if (config.add_annotations){
    		$("<i class='fas fa-stream'></i>")
    			.css("font-size","18px")
    			.attr({title:"Annotation Intersect","data-toggle":"tooltip"})
    			.appendTo(menu_div)
    			.click(function(e){
    				self.anno_context_menu.show(self.annotations,e);
    			});
    		this.setupAnnoContextMenu(this.permission);
    		
    	}
    	if (project_data.find_tss_distances_job_status !== "complete" && this.config.find_tss_distances!==false){
	    	$("<i class='fas fa-exchange-alt'></i>")
			.css("font-size","18px")
			.attr({title:"Find TSS Distances","data-toggle":"tooltip"})
			.appendTo(menu_div)
			.click(function(e){
				self.findTSSDistances();
			});
    	}
    	if (this.permission==="edit"){
	    	$("<i class='fas fa-columns'></i>")
			.css("font-size","18px")
			.attr({title:"Delete\Add Columns","data-toggle":"tooltip"})
			.appendTo(menu_div)
			.click(function(e){
				self.column_context_menu.show(null,e);
			})
			this.setUpColumnContextMenu();
    	}
    	
    	
    	if (this.tagging_field){
	    	$("<i class='fas fa-tags'></i>")
				.css("font-size","18px")
				.attr({title:"Open Tagging Dialog","data-toggle":"tooltip"})
				.appendTo(menu_div)
				.click(function(e){
					self.showTaggingDialog();   	
				});
    	}
    	
    	
    	if (this.config.add_peak_stats && this.permission==="edit"){
    		let ps_icon= $("<i class='fas fa-signature'></i>");
    		
			ps_icon.css("font-size","18px")
			.attr({title:"Calculate Peak stats","data-toggle":"tooltip"})
			.appendTo(menu_div)
			.click(function(e){
				new MLVPeakStatsDialog(self,ps_icon);   	
			});
			
			let info = project_data.peak_stats_job_status;
			if (info){
				if (info!=="complete" && info !=="failed"){
						this.calculatingPeakStats(project_data.peak_stat_job_id,ps_icon)
					}
				}
		}
    	
    	if (this.config.cluster_on_columns && this.permission==="edit"){
    		let ps_icon= $("<i class='fab fa-cloudsmith'></i>");
    		
			ps_icon.css("font-Filteredsize","18px")
			.attr({title:"Cluster on Columns","data-toggle":"tooltip",id:"cluster_by_fields_job"})
			.appendTo(menu_div)
			.click(function(e){
				new MLVClusterDialog(self,"number");   	
			});
			let info = project_data.cluster_by_fields_job_status;
			if (info){
				if (info!=="complete" && info !=="failed"){
						this.clusteringByFields(project_data.cluster_by_fields_job_id)
					}
				}
			
		
		}
    		
    	
    	
    	this.addToTableMenu(menu_div,project_data)
    	
    	
 
    	
    	
    	if (project_data.has_images) {
    		if (this.config.zegami !== false){
    		$("<img>")
    		.attr("src","/static/img/icons/zegami.png")
    		.css("cursor","pointer")
			.appendTo(menu_div)
			.click(function(e){
				new CreateZegamiCollection(self.project_id);
			});
    		}
    	}
    	else{
    	    
        	let icon =$("<i class='far fa-images'></i>")
    		.css("font-size","18px")
    			.appendTo(menu_div)
    			.attr({title:"Create Images","data-toggle":"tooltip"})
    			.click(function(e){
    				let row = self.table.getTopVisibleItem();
    				let a =new CreateUCSCImages(self.project_id,self.table,self.browser);
    				a.setCallback(function(jid){self.creatingImages(jid,icon)})
    			});
        	if (project_data.creating_images_job_status==="running"){
        		this.creatingImages(project_data.creating_images_job_id,icon)
        	
        		
        	}
        }

    	
    
    	
    	
    	
    	 this.image_slider = $("<div>").attr({"id":"mlv-it-image-slider"})
         .css({width:"250px",display:"inline-block"}).slider({
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
         }).appendTo(menu_div).hide();
    	 
    	 this.image_colorby=$("<i class='fas fa-palette'></i>")
	  		.css({"font-size":"18px"})
	  		.appendTo(menu_div)
	  		.click(function(e){
		  self.image_table.showColorByDialog("table-holder-div");
	  		}).hide();
    	 
    	 
    	
    	this.im_table_div = $("<div>")
    		.css({height:"calc(100% - 30px)",display:"none","overflow":"hidden","width":"100%"})
    		.attr("id","table-holder-div")
    		.appendTo(div);
    	
    	
    	$("<div>").css({height:"calc(100% - 30px)"}).attr("id","the-table-div").appendTo(div);
    	
    
    	let id=4;
    	this.columns=[];
    	let columns = this.getDefaultColumns(response,project_data);
    	this.columns= this.getCustomColumns(response,project_data);
    	let table_columns = columns.concat(this.columns);
    	 	
    
    	let dv =null;
    	if (this.filter_panel){
    		this.filter_panel.setColumns(this.columns);
    		dv = new FilterPanelDataView(this.filter_panel);
    		
    	}
    	else{
    		dv = new MLVDataView(data)
    	}
    	
    	this.waiting_icon.hide();
    	
    	this.table = new MLVTable("the-table-div",table_columns,dv);
    	if (project_data.has_images){
    		this.image_table = new MLVImageTable(this.im_table_div,dv,
    				{
    				base_url:response.base_image_url,
    				initial_image_width:150
    				});
    		this.image_table.addListener("image_selected",function(ids){
    			let id = ids[0];
    			self.current_feature=id;
    			self.table.grid.setSelectedRows([self.table.data_view.getRowById(id)]);
    		});
    		this.table.addListener("sort_listener",function(e,item){
    			if (self.table_mode==="images"){
    				self.image_table.show(self.table.data_view.getRowById(self.current_feature));
    			}
    		
    		});
    		this.image_table.show_info_box=true;
    		
    		this.image_table.setColumns(table_columns);
    		if (project_data.has_tiles){
    			this.tiled_image_base=response.base_image_url.replace("/tn","/track_image")
    		}
    		
    		
    	}
    	this.total_rows = data.length
    	this.row_number_text= $("<span>").text(data.length+"/"+data.length).css({"font-weight":"bold","float":"right"}).appendTo(menu_div);
    	
    	this.table.grid.onSelectedRowsChanged.subscribe(function(e,args){
    		let item = self.table.grid.getDataItem(args.rows[0]);
    		if (self.image_table){
    			self.image_table.setSelectedTiles([item.id])
    		}
    		self.current_feature=item.id;
    		self.tableClicked(item);	
    	});
    	
    	dv.addListener("data_filtered",function(filtered_number){
    		self.row_number_text.text(filtered_number+"/"+self.total_rows);
        	self.browser.panel.update();
        	/*if (self.table_mode==="images"){
				self.image_table.show(self.table.data_view.getRowById(self.current_feature));
			*/
    	})
    	
    	this.init(response,project_data);
    	$('[data-toggle="tooltip"]').tooltip();
    	
    }
	
	addToTableMenu(div){
	}
	
	
	init(response,project_data){
		let data = response.views;
		let margin = parseInt(project_data.browser_config.feature_track.margin);
		margin=margin?margin:1000;
    	if (project_data.browser_config.position){
    		let pos = project_data.browser_config.position;
    		this.browser.goToPosition(pos.chr,parseInt(pos.start)-margin,parseInt(pos.end)+margin);
    	}
    	else{	
    		this.table.grid.setSelectedRows([0]);
    	}
    	let ft = project_data.browser_config.feature_track;
    	if (ft){
    		if (ft.y_field){
    			this.browser.panel.tracks[ft.track_id].setYField(this.table.data_view,ft.y_field)
    		}
    		if (ft.label_field){
    			let dv= this.table.data_view;
    			this.browser.panel.setTrackLabelFunction(ft.track_id,function(f){
    					let item = dv.getItemById(f.id)
    					return item[ft.label_field];
    				
    			});
    			
    		}
    	}
    	let tc = project_data.table_config
    	if (tc){
    		if (tc.format && tc.format !== "table"){
   			 	this.setTableFormat(tc.format);
    		}
    		if (tc.sort_cols){
    			this.table.sortTable(tc.sort_cols);
    		}
    		if (tc.color_by){
    			let cb = FilterPanel.getColorScale(tc.color_by.column,data,tc.color_by.scheme,"table-holder-div");
    			this.image_table.setColorBy(cb);
    			
    			this.image_table.show();
    			$("#table-holder-div-bar").position({"my":"left top","at":"left top","of":"#table-holder-div"})
    		}
    		
    	}
    	
		
	}
	
	tableClicked(item){
		if (this.update_browser_view){
			if (this.tiled_image_base){
				let config={};
				let img = this.tiled_image_base+item.id+".png";
				config[item.chromosome]=[
					[item.start,item.finish,img]
				]
				this.browser.panel.force_redraw=true;
				this.browser.panel.setTrackAttribute("matrix_track","images",config)
			}
			let val = parseInt(this.browser_config.feature_track.margin);
			if (!(val) && val !==0){
				val=1000;
			}
			
			//this.browser.setHighlightedRegion(item.chromosome,item.start,item.finish);
			this.browser.goToPosition(item.chromosome,item.start-val,item.finish+val);
		}
		if (this.filter_panel){
			this.filter_panel.highlightDataItem(item.id);
		}
	}
	
	setUpColumnContextMenu(){
		let self =  this;
		this.column_context_menu=new MLVContextMenu(function(data){

			return [
				{
					text:"Create Column",
					func:function(){
						new CreateCompoundColumn(self);
					},
					icon:"fas fa-plus"
				},
				{
					text:"Delete Columns",
					
					func:function(){
						new DeleteColumnsDialog(self);
					},
					icon:"fas fa-trash"
				
			}];
		})
	}
	
	
    setupAnnoContextMenu(permission){

	    	
    	if (permission==="edit"){
    		this.add_annotations= new AddAnnotations(project_id,this.genome,
    				function(data){
	    					self.addAnnotations(data);
	    			},this.anno_project_types);
	    }
    	if (this.annotations){
    		if (Object.keys(this.annotations).length===0){
    			this.annotations=null;
    		}
    	}
    	
    	
    	let self = this;
    	this.anno_context_menu = new MLVContextMenu(
    		function(data){
    			
    				return [
    					{
    						text:"Create Annotation Set",
    						func:function(){
    							self.createAnnotationSet();
    						},
    						icon:"fas fa-plus-circle"
    					},
    					{
    						text:"Annotation Intersect ",
    						func:function(){
    							self.add_annotations.showDialog(self.annotations);
    						},
    						icon:"fas fa-stream",
    						ghosted:permission!=="edit"
    					},
    					{
    						func:function(){
    							new RemoveAnnotationsDialog(self.annotations,self.project_id,
    									function(success,ids){
    										self.annotationsRemoved(success,ids);
    									}
    							);
    						},
    						text:"Remove Intersection",
    						icon:"fas fa-trash",
    						ghosted:permission!=="edit" || !(self.annotations)
    						
    					}
    					
    				];		
    			
    		
    		}
    	)
    }
    
    setupTableFormatMenu(){
    	let self = this;
    	this.table_format_menu = new MLVContextMenu(
        		function(data){
        			let menu= [
        			{    				
        					text:"Table",
    						func:function(){
    							self.setTableFormat("table");
    						},
    						icon:"fas fa-table",
    						ghosted:self.table_mode==="table"	
        			},
        			{
        					text:"Images",
    						func:function(){
    							self.setTableFormat("images");
    						},
    						icon:"fas fa-images",
    						ghosted:self.table_mode==="images"	
        			},
        			{
        					text:"Table with Thumbnails",
    						func:function(){
    							self.setTableFormat("thumbnails");
    						},
    						icon:"fas fa-list",
    						ghosted:self.table_mode==="thumbnails"
        			}];
        			return menu;	
        		}
        	)
    	
    	
    	
    }
    
    createAnnotationSet(){
    	let ids=[]
		for(let item of this.table.data_view.getFilteredItems()){
			ids.push(item.id)
		}
		new AnnotationSetFromProject(this.project_id,ids,this.columns,
				{
					genome:this.genome,
					name:this.project_name+" annotations",
					desc:this.project_name+" annotations"
				});	
    }
    
	sendAction(method,args){
		let data={
			method:method,
			args:args
		}
		return $.ajax({
			url:"/meths/execute_project_action/"+this.project_id,
			dataType:"json",
			contentType:"application/json",
			data:JSON.stringify(data),
			type:"POST"
		})
		
	}
	
	getPermission(type){
		let self = this;
		return $.ajax({
			url:"/meths/users/has_permission/"+type,
			dataType:"json"
			
		});
	}
	
	removeColumns(fields){
		
		let table_columns=[];
		let this_columns=[];
		for (let col of this.table.grid.getColumns()){
			if (fields.indexOf(col.field)===-1){
				table_columns.push(col)
			}
		}
		for (let col of this.columns){
			if (fields.indexOf(col.field)===-1){
				this_columns.push(col)
			}
		}
		this.columns=this_columns;
		this.table.grid.setColumns(table_columns);
		this.table.updateGroupPanel();
		if (this.filter_panel){
			for (let f of fields){
				this.filter_panel.removeField(f);
			}
		}
		this._saveState();
	}
	
	
	annotationsRemoved(success,ids){
		if (success){
			let columns = this.table.grid.getColumns();
			for (let id of ids){
				let anno = this.annotations[id];
				if (this.filter_panel){
					this.filter_panel.removeField(anno["field"])
				}
				this.browser.panel.removeTrack("annotation_"+id);
				this.browser.panel.removeTrack("project_"+id);
				delete this.annotations[id];
				let splice=-1;
		    	for (let index in columns){
			    	if (columns[index].field===anno.field){
			    		splice=index;
			    		break;
			    	}
		    	}
		    	if (splice !==-1){	
		    		columns.splice(splice,1);
		    	}
			}
    		this.table.grid.setColumns(columns);
    		this.table.updateGroupPanel();
			
			
			if (Object.keys(this.annotations).length===0){
				this.annotations=null;
			}
			this.browser.panel.update();
			this._saveState();
			
		}
	}
	
	showTaggingDialog(){
		let target = this.table;
		let self=this;
		if (this.table_mode==="images"){
			target = this.image_table;
		}
		this.tagging_dialog =new TaggingDialog(target,this.tagging_field,
          		{
          			button:"Save",
          			options:this.tagging_options
          	
          		}
		);	 
		this.tagging_dialog.setCloseFunction(function(options){
			self.tagging_options=options;
			self.tagging_dialog=null;
		});
		
		this.tagging_dialog.setActionFunction(function(options){
			self.saveTags(options)
		})
      	
	}
	
	saveTags(options){
		let data=this.table.data_view.getItems();
		let tags={}
		for (let item of data){
			let val = item[this.tagging_field];
			if (val){
				tags[item.id]=val;
			}
		}	
		let waiting_dialog = new WaitingDialog("Saving Tags");
		let self =  this;
		waiting_dialog.wait("updating database")
	
		$.ajax({
			url:"/meths/execute_project_action/"+this.project_id,
			type:"POST",
			dataType:"json",
			contentType:"application/json",
			data:JSON.stringify({
				method:"update_tags",
				args:{
					tags:tags,
					tag_color_scheme:options
				}
			})
		}).done(function(response){
			if (response.success){
				waiting_dialog.showMessage(self.getSaveTagsMessage(),"success")
			}
			else{
				waiting_dialog.showMessage(response.msg,"danger");
			}
				
		})	
	
	}
	
	getSaveTagsMessage(){	
		return "The tags have been saved"
	}
    	
	
	
    addAnnotations(data){
    	if (!this.annotations){
    		this.annotations={};
    	}
    	let t_cols = this.table.grid.getColumns();
    	for (let col of data.columns){
    		if (!col.columnGroup){
    			col.columnGroup="Annotations"
    		}
    		t_cols.push(col);
    		this.columns.push(col)
    	}
    	
    	for (let item of data.data ){
    		let row = this.table.data_view.getItemById(item.id);
    		delete item.id;
    		for (let field in item){
    			row[field]=item[field]
    		}		
    	}
    	this.table.grid.setColumns(t_cols);
    	this.table.updateGroupPanel();
    	this.filter_panel.setColumns(this.columns);
    	//to do - add graphs / tracks
    	if (data.is_fields==0){
	    	for (let col of data.columns){
	    		this.filter_panel.addChart({
	    			type:"ring_chart",
	    			param:col.field,
	    			title:col.name,
	    			id:"anno_pie_"+col.id,
	    			location:{x:0,y:0,height:3,width:3}
	    		});
	    		this.annotations[col.id.split("_")[1]]={
	    			field:col.field,
	    			label:col.name
	    		}
	    	}
    	}
    	for (let track of data.tracks){
    		this.main_panel.addTrack(track,0)
    	}
    	for (let wig of data.wigs){
    		this.main_panel.addTrack(wig)
    	}
    	this.main_panel.update();
    	this._saveState();
    }
    
    
    getTracksToSave(){
    	return this.browser.panel.getAllTrackConfigs();
    }
    
    _saveState(show_confirm){	
		let state= this.getTracksToSave();
		let position=this.browser.getPosition();
		let browser_config={
				state:state,
				position:position,
				feature_track:this.browser_config.feature_track
		};
		let data = {
				browser_config:browser_config
		};
		if (this.filter_panel){
			data.graph_config = this.filter_panel.getGraphs();
		}
		let table_config={
				format:this.table_mode,
				sort_cols:this.table.getSortColumns()
				
				
		}
		if (this.image_table){
			if (this.image_table.color_by){
				table_config.color_by = {
					scheme:this.image_table.color_by.scheme,
					column:this.image_table.color_by.column
				}
			}
		}
		data.table_config=table_config;
	
		
		$.ajax({
			url:"/meths/update_object/"+this.project_id,
			contentType:"application/json",
			type:"POST",
			dataType:"json",
			data:JSON.stringify(data)
		}).done(function(response){
			if (!show_confirm){
				return;
			}
			if (response.success){
				new MLVDialog("The project has been saved",{type:"success"});
			}
			else{
				new MLVDialog(response.msg,{type:"danger"});
			}			
		})
	}
    
    findTSSDistances(){
    	let self = this;
    	let div =$("<div>");
    	div.append("<div>The distance from each region to the nearest tss site will be calculated</div>");
    	$("<input>").attr({
    		type:"checkbox",
    		id:"tss-GO-annotations"
    		
    	}).css("border-right","3px").appendTo(div);
    	$("<label>").attr({
			"for":"tss-GO-annotations"
			}).text("Include GO annoations").appendTo(div);
    	div.append("<br>");
    	$("<label>").attr({
			"for":"tss-GO-levels"
			}).text("GO Hierarchical Levels").css("border-right","3px").appendTo(div);
    	let sel = $("<select>").attr("id","tss-GO-levels").appendTo(div);
    	for (let n=1;n<6;n++){
    	  sel.append($('<option>',{
			  value:n,
			  text:n
		  }));
    	}
    	sel.val("3")
    	
    	
    	
    	new MLVDialog(div,{
    		mode:"ok_cancel",
    		title:"Find TSS distances",
    		close_on_ok:true,
    		callback:function(do_action){
    			if (do_action){
    				let go_levels=0;
    				if ($("#tss-GO-annotations").prop("checked")){
    					go_levels=parseInt(sel.val());
    				}
    				
    				self.sendAction("find_tss_distances",{go_levels:go_levels}).done(function(resp){
    					if (resp.success){
    						let wd=new WaitingDialog("Finding TSS Distances");
    						wd.wait("")
    						self.checkJobRunning("find_tss_distances_job_id","TSS",function(success){
    							self.addDataToView(wd,"get_tss_distances","TSS distances have been calculated");
    						})
    					}else{
    						console.log(resp.msg)
    					}
            		
        			});
    			

    			}
    		
    		}	 	 	
    		})
    }
   
    
    addDataToView(dialog,method,message){
    	let self =this;
    	dialog.showMessage(message+". The appropriate charts/data have been added","success");
    	self.sendAction(method,{}).done(function(response){
    		let data = response.data
        	for (let col of data.columns){
        		self.columns.push(col)
        	}
        	
        	for (let item of data.data ){
        		let row = self.table.data_view.getItemById(item.id);
        		delete item.id;
        		for (let field in item){
        			row[field]=item[field]
        		}		
        	}
        	self.table.addColumns(data.columns);
        	self.filter_panel.setColumns(self.columns);
        
        	for (let graph of data.graphs){
        		self.filter_panel.addChart(graph);
        	
        	}
        	self._saveState();
        
    	})
    	
    }
    _addDataToView(data){
    	for (let col of data.columns){
    		this.columns.push(col)
    	}
    	
    	for (let item of data.data ){
    		let row = this.table.data_view.getItemById(item.id);
    		delete item.id;
    		for (let field in item){
    			row[field]=item[field]
    		}		
    	}
    	this.table.addColumns(data.columns);
    	this.filter_panel.setColumns(this.columns);
    
    	for (let graph of data.graphs){
    		this.filter_panel.addChart(graph);
    	
    	}
    	this._saveState();
    }
    
    setTableFormat(type){
    	if (this.tagging_dialog){
    		this.tagging_dialog.close();
    	}
    	if (type==="images"){
    		this.removeThumbnailColumn();
        	$("#the-table-div").hide();
        	this.im_table_div.show();
        	this.image_table._resize(this.table.data_view.getRowById(this.current_feature));
        	this.table_mode="images";
        	this.image_slider.show();
        	this.image_colorby.show();
    	}
    	else if (type==="table"){
    		this.removeThumbnailColumn();
    		this.image_table.hide();
    		this.im_table_div.hide();
    		$("#the-table-div").show();
    		this.table.goToRow(this.table.data_view.getRowById(this.current_feature));
    		this.table_mode="table";
    		this.image_slider.hide();
    		this.image_colorby.hide();
    			
    	}
    	else if (type==="thumbnails"){
    		this.addThumbnailColumn();
    		this.image_table.hide();
    		this.im_table_div.hide();
    		$("#the-table-div").show(); 		
    		this.table.goToRow(this.table.data_view.getRowById(this.current_feature));
    		this.table_mode="thumbnails";
    		this.image_slider.hide();
    		this.image_colorby.hide();
    	}
    }
    
    
    
    creatingImages(job_id,icon){
    	icon.addClass("mlv-animate-flicker").attr("title","Images are being Created").off();
		this.checkJobRunning(job_id,"Create Images");

    }
    
    calculatingPeakStats(job_id,icon){
    	icon.addClass("mlv-animate-flicker").attr("title","Peak Stats are being calculated").off();
		this.checkJobRunning(job_id,"Create Images");
    }
    
    clusteringByFields(job_id){
    	$("#cluster_by_fields_job").addClass("mlv-animate-flicker").attr("title","Peak Stats are being calculated").off();
    	this.checkJobRunning(job_id,"Cluster on Fields");
    }
    
    checkJobRunning(tag,name,callback){
    	let self = this
    	if (isNaN(tag)){
    		$.ajax({
        		url:"/meths/get_project_data/"+this.project_id,
        		dataType:"json"
        		
        	}).done(function(response){
        		if (response.data[tag]){
        			self.checkJobRunning(response.data[tag],name,callback);
        			
        		}
        			
        		else{
        			setTimeout(function(){
        				self.checkJobRunning(tag,name,callback);
        			},30000)
        		}
        	})
    				
    	}
    	else{
    		$.ajax({
        		url:"/meths/jobs/check_job_status/"+tag,
        		dataType:"json"
        		
        	}).done(function(response){
        		if (response.status==="complete" || response.status==="failed"){
        			if (!callback){
        				if (response.status==="complete"){
        					let msg =`The ${name} job is complete, please refresh the page
        					to see the results`
        					new MLVDialog(msg,{type:"success"})
        				}
        				else{
        					let msg =`The ${name} job is failed, please contact an administrator`
            					new MLVDialog(msg,{type:"success"})
        				}
        			}else{
        				callback(response.status);
        			}
        			
        		}
        		else{
        			setTimeout(function(){
        				self.checkJobRunning(tag,name,callback);
        			},30000)
        		}
        	})
    		
    		
    	}
    	
    }
    
    removeThumbnailColumn(){
    	let columns = this.table.grid.getColumns();
    	let splice=-1;
    	for (let index in columns){
	    	if (columns[index].id==="tn_column"){
	    		splice=index;
	    		break;
	    	}
    	}
    	if (splice !==-1){
    		let options = this.table.grid.getOptions();
    		options.rowHeight=this.row_height;
    		columns.splice(splice,1);
    		this.table.grid.setOptions(options);
    		this.table.grid.setColumns(columns);
    		this.table.updateGroupPanel()
    	}
    	
    }
    addThumbnailColumn(){
    	let columns = this.table.grid.getColumns();
    	let options = this.table.grid.getOptions();	
    	columns.unshift(this.getThumbnailColumn());
    	this.row_height=options.rowHeight;
    	options.rowHeight=70;
    	this.table.grid.setOptions(options);
    	this.table.grid.setColumns(columns);
    	this.table.updateGroupPanel();
    }
    
    getThumbnailColumn(){
    	let self =this;
    	 return {
    			  id: "tn_column",
    			  name: "Thumbnail",
    			  field: "id",
                  width:150,
                  height:70,
                  formatter:function(a,b,val){
                	  let im =self.base_image_url+val;
                	  return `<img src='${im}.png' style='height:66px;width:142px'></img>` 
                  }
         };
    	
    }
    
    saveBrowserImage(){
		let type = $("#img-type-option").val();
		let width = this.browser.panel.getDiv().width();
		let height = this.browser.panel.getDiv().find("canvas").attr("height");
		let tracks=this.browser.panel.getAllTrackConfigs();
		let pos = this.browser.getPosition();
		let name = pos.chr+"_"+pos.start+"_"+pos.end;
		let data={
				tracks:tracks,
				width:width,
				height:300,
				type:type,
				position:pos,
				
		}
		$.ajax({
			url:"/meths/create_track_image",
			contentType:"application/json",
			type:"POST",
			
			data:JSON.stringify(data)
		}).done(function(data){
			
			let link =document.createElement("a");
			link.href=data
			link.download=name+"."+type
			link.click();
			$(link).remove();
		});	
	}
}


class FeatureTrackDialog{
	constructor(app){
		this.app=app;
		let self = this;
		this.col_info={};
		for (let col of app.columns){
			this.col_info[col.field]=col;
		}
	
		let buttons=[
			{
				text:"Close",
				click:function (e){
			
					self.div.dialog("close");
				}
			}		
		];
		this.div=$("<div>");
		this.init()
		this.div.dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			title:"Feature Track Settings",
			buttons:buttons
		}).dialogFix();

		
	}
	
	setTrackYAxis(y_field){
		let conf = this.app.browser_config.feature_track;
		let tid= conf.track_id;
		if (!y_field){
			this.app.browser.panel.tracks[tid].setYField(null);
		}
		else{
			
			this.app.browser.panel.tracks[tid].setYField(this.app.table.data_view,y_field);
			
		}
		conf.y_field=y_field;
		this.app.browser.panel.update();
	}
	
	setTrackLabel(field){
		if (field==="none"){
			field=null;
		}
		let conf = this.app.browser_config.feature_track;
		let dv = this.app.table.data_view;
		if (field){
			this.app.browser.panel.setTrackLabelFunction(conf.track_id,function(f){
				let item = dv.getItemById(f.id)
				return item[field];
			
			})
		}
		else{
			this.app.browser.panel.setTrackLabelFunction(conf.track_id,null);
		}
		conf.label_field=field;
		this.app.browser.panel.update();
		
	}
	
	init(){
		let conf = this.app.browser_config.feature_track;
		let columns=this.app.columns;
		let self = this;
		this.div.append("<label class='mlv-block-label'>Feature Y Axis</label>");
		let msg= "The field to set the vertical position of the feature";
		this.div.append($("<p class= 'info-text'></p>").text(msg));
		let sel = $("<select>").appendTo(this.div);
		let text_select=$("<select>");
		for (let col of columns){
			$("<option>").text(col.name).val(col.field).appendTo(text_select)
			if (col.datatype !=="double" && col.datatype!="integer"){
				continue;
			}
			$("<option>").text(col.name).val(col.field).appendTo(sel)
		}
		sel.append($("<option>").text("Default").val("none"));
		text_select.append($("<option>").text("None").val("none"));
		if (conf.y_field){
			sel.val(conf.y_field.field)
		}
		else{
			sel.val("none")
		}
		sel.change(function(e){
			let v = $(this).val();
			let info=null;
			if (v !== "none"){
				let col = self.col_info[v];
				self.setTrackYAxis({field:v,name:col.name})
				
			}
			else{
				self.setTrackYAxis(null)
			}
		});
		
		if (conf.label_field){
			text_select.val(conf.label_field)
		}
		else{
			text_select.val("none");
		}
		text_select.change(function(e){;
			self.setTrackLabel($(this).val())
			
		})
		this.div.append("<label  class = 'mlv-block-label'>Feature Label</label>")
		this.div.append(text_select);
		
		
		this.div.append("<label class='mlv-block-label'>Feature Color</label>");
		let text= "None";
		if (conf.color_by){
			text= conf.color_by.column.name;
		}
		this.color_by_text = $("<span>").text(text).appendTo(this.div);
		$("<i class='fas fa-sync-alt'></i>").css({pointer:"cursor","margin-left":"10px"})
			.click(function(e){
				self.showBrowserColorBy();
			})
			.appendTo(this.div);
		
		
		
		
		
		
		this.div.append("<label class ='mlv-block-label'>Margin size</label>");
		msg = "The distance either side of the feture to show";
		this.div.append($("<p class= 'info-text'></p>").text(msg));
		let sp = $("<input>").width(60).appendTo(this.div);
		let val = conf.margin?conf.margin:1000;
		sp.spinner({
			change:function(e,ui){
				conf.margin= sp.val();
			},
			min:100,
			max:5000,
			step:100 
		}).val(val);
				
	}
	
	showBrowserColorBy(){
		let self =this.app;
		let label = this.color_by_text;
		let track_id = self.browser_config.feature_track.track_id;
		let func=function(d){
			if (d){
				self.browser.panel.setTrackColorFunction(track_id,function(feature){
					let item =self.table.data_view.getItemById(feature.id);
					return d.func(item[d.column.field])
				  
				});
				self.browser_config.feature_track.color_by={
						column:d.column,
						scheme:d.scheme
				}
				label.text(d.column.name);
			}else{
				let fts = self.browser.panel.getCurrentTrackFeatures(track_id);
				for (let f of fts){
					delete f.color;
				}
				    	
				
				self.browser.panel.setTrackColorFunction(track_id,null);
				self.browser_config.feature_track.color_by=null;
				label.text("None")
			}
			
			
			
			self.browser.panel.update();
		}
		let existing=null;
		if (self.browser_config.feature_track){
			existing= self.browser_config.feature_track.color_by
		}
		new ColorByDialog(self.columns,
				self.table.data_view.getItems(),
				"browser-panel",
				func,null,existing);
			
	}
	

}










