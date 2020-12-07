class BaseMEVDialog{
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

class GeneChooserDialog extends BaseMEVDialog {
	
	constructor(group_id,experiments,callback){
		super();
		let self =this;
		this.project_id=group_id;
		this.callback=callback;
		this.experiments=experiments;
		let lp= $("<div>").css({"display":"flex","flex":"10%","flex-direction":"column"});
		let rp= $("<div>").css({"flex":"90%","padding":"7px"});
		
		$("<p>").text("Paste in list of genes or proteins and press find").appendTo(lp)
		this.gene_text= $("<textarea>").css({"height":"150px"}).appendTo(lp);
		let but =$("<button>").attr("class","btn btn-sm btn-primary").text("Find").click(function(e){
			self.sendGeneList();
		}).appendTo(lp);
		this.setUpTable(rp);
		this.div=$("<div>").css("display","flex").append(lp).append(rp).dialog({
			close:function(){
				$(this).dialog("destroy").remove();
			},
			width:800,
			height:300,
			title:"Gene Selection",
			buttons:[{
				text:"submit",
				
				click:function(e){
					self.callback(self.getAllGenes())
					$(this).dialog("close");
					
				}
			}]
			
		}).dialogFix();
		
		
	}
	
	sendGeneList(){
		let self =this;
		let genes= this.gene_text.val().split(/\s+/g).filter(Boolean);
		let f_genes=[]
		for (let gene of genes){
			if (!gene || f_genes.indexOf(gene)!=-1){
				continue;
			}
			f_genes.push(gene);
		}
		this.executeProjectAction("get_similar_genes",({names:f_genes})).then(function(response){
			if (response.success){
				self.populateTable(f_genes,response.data);
			}
		});	
	}
	
	populateTable(genes,data){
		
		for (let gene of genes){
			if (!gene){
				continue;
			}
			let row = $("<tr>").appendTo(this.tbody);
			let t= $("<i>").attr("class","fas fa-trash").click(function(e){
				row.remove();
			})
			$("<td>").append(t).append($("<span>").text(gene)).appendTo(row);
			
			
			let info = data[gene];
			for (let e of this.experiments){
				let details = info[e.id];
				if (details){
					let td = $("<td>").appendTo(row).data("info",{
						exp_id:e.id,
						id:details.id,
						name:details.name
						
					});
					td.append("<span>"+details.name+"<span>");
					$("<input>").attr({type:"checkbox"}).prop("checked",true).appendTo(td);
				}
				else{
					row.append("<td>");
				}
			}
		}
	}
	
	getAllGenes(){
		let all_genes=[];
		this.tbody.find("td").each(function(i,e){
			let td= $(e);
			if (td.find("input").prop("checked")){
				if (td.data("info")){
					all_genes.push(td.data("info"))
				}
			}
		});
		return all_genes;
	}
	
	setUpTable(rp){
		this.table = $("<table>").appendTo(rp);
		let h= $("<thead>").appendTo(this.table);
		h.append($("<th>").text("Input").css("background-color","rgba(120,120,120,0.6"));
		for (let exp_id in this.experiments){
			let exp=this.experiments[exp_id];
		
			$("<th>").css({"background-color":exp.color})
			.text(exp.name).data("exp_id",exp_id)
			.appendTo(h);
		
			
		}
		this.tbody=$("<tbody>").appendTo(this.table);
	

	}
	
	
		
}

class MEVUploadSampleData extends BaseMEVDialog{
	constructor(project_id,genome,ids,callback){
		super();
		let self=this;
		this.project_id=project_id;
		this.genome=genome;
		this.div = $("<div>");
		this.callback=callback;
		this.info_div=$("<div>").attr("class","alert alert-info")
		.html("Please enter name and description of the field and upload a tab delimited text file containing"+
				" two columns. Thr first being sample id and the second the actual value. ")
		.appendTo(this.div);
		
    	this.div.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    			self.file_chooser.destroy();
    			
    		},
    		buttons:[{
    			text:"Submit",
    			click:function(e){
    				self.uploadData();
    			},
    			id:"sample-upload-button"
    		}],
    		title:"Create View",
    		width:380
    	}).dialogFix();
		$("#sample-upload-button").attr("disabled",true)
		this.ids=ids;
		this.file_chooser = new MLVFileChooser();
		this.div.append("<label>Name</label>");
		this.name_input = $("<input type='text' id='mlv-model-name' class='form-control'>")
			.appendTo(this.div);
		
		this.div.append("<label>Description</label>");
		this.desc_input =$("<textarea rows='3' id='mlv-model-description' class='form-control'></textarea>")
			.appendTo(this.div);
		
		let radio_div=$("<div>").appendTo(this.div);
		
		for (let t of ["continuous","discrete"]){
			$("<input>").attr({name:"source-data-type",type:"radio",value:t,checked:true})
				.appendTo(radio_div);
		     $("<label>").text(t).appendTo(radio_div);
		     $("<span>").css({"width":"20px","display":"inline-block"}).appendTo(radio_div)
			
			
			
		}
		
		this.is_public = $("<input>").attr("type","checkbox").appendTo(radio_div);
		$("<label>").text("Public").appendTo(radio_div);
		
		
		
		let b= $("<button>").attr("class","btn btn-sm btn-secondary")
		    .text("Upload File").click(function(e){
			self.file_chooser.showOpenDialog(function(file){
				self.parseFile(file)
			})
		}).appendTo(this.div);
		
	}
	
	parseFile(file){
		let lines = file.readAsText(lines=>{
			this.data={};
			let error = null;
			let type= $("input[name='source-data-type']:checked").val()
			for (let line of lines){
				let arr= line.split("\t")			
				this.data[arr[0]]=arr[1];
				if (this.ids.indexOf(arr[0])==-1){
					error= "Unrecognised sample id:"+arr[0];
					break;
				}
				if (type==="continuous"){
					arr[1]=parseFloat(arr[1])
					if (isNaN(arr[1])){
						error="Non continuous value:"+arr[1]
					}
				}
			}
			if (error){
				$("#sample-upload-button").attr("disabled",true);
				this.info_div.removeClass("alert-info").addClass("alert-danger")
				.html(error);
			}
			else{			
				this.info_div.removeClass("alert-danger").addClass("alert-info")
				.html("The file appears correct, please press submit");
				$("#sample-upload-button").attr("disabled",false)
			}
		});
		
	}
	uploadData(){
		let name = this.name_input.val();
		let desc= this.desc_input.val();
		let self =this;
		if ((!name)||(!desc)){
			this.info_div.removeClass("alert-info").addClass("alert-danger")
			.html("Please add name and description");
			return;
			
		}
		let args={
			name:name,
			description:desc,
			datatype:$("input[name='source-data-type']:checked").val(),
			data:this.data,
			genome:this.genome,
			is_public:this.is_public.prop("checked")
				
		}
		this.executeProjectAction("add_sample_data",args).then(function(response){
			if (response.success){
				self.info_div.removeClass("alert-danger").addClass("alert-info")
				.html("The data has been added to the database and the view");
				self.callback(response.data.id);				
			}
			else{
				self.info_div.removeClass("alert-info").addClass("alert-danger")
				.html("There was a problem please contact an adminisrator");
			}
		});
		
		
	}
}



class MEVSaveAsDialog extends BaseMEVDialog{
	constructor (project_id,type,genome,data){
		super();
		let self = this;
		this.project_id=project_id;
		this.div = $("<div>")
		
    	.dialog({
    		close:function(){
    			$(this).dialog("destroy").remove();
    			self.subset_dialog=null;
    		},
    		title:"Create View",
    		width:380
    	}).dialogFix();
		this.info_div=$("<div>").attr("class","alert alert-info")
			.text("Please enter name and description of the view and press next")
			.appendTo(this.div);
		let d =$("<div>").appendTo(this.div);
		
		this.subset_form = new NameDescGenomeForm(d,type,
    			function(pid){
    				self.createSubset(pid,data);
    			},
    			{genome:genome,name:"Some Genes",desc:"Very Interesting"}
    	);
		
	}
	
	createSubset(id,data){
		let self =this;
		this.executeProjectAction("clone_view",({new_view:id,data:data})).then(function(response){
			if (response.success){
				let url = response.data.url;
				let html = "The View has been saved and can be accessed by the link below<br>"
				html+="<a href='"+url+"'>"+url+"</a>"
				self.info_div.removeClass("alert-info").addClass("alert-success").html(html);
			}
			else{
				let html = "Unable to create the view";
				self.info_div.removeClass("alert-info").addClass("alert-danger").html(html)
				
			}
		});	
		
		
	}
}





