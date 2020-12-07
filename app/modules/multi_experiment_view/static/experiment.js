class MEVExperimentUpload{
	constructor(project,div){
		this.div=$("#"+div).css("padding","5px 50px");
		let self = this;
		this.project_id=project.id;
		this.div.append("<h3>Create Data Set</h3>")
		this.div.append("<h4>Data Set Type</h4>")
		let t_div=$("<div>").appendTo(this.div);
		let data = project.data;
		data.templates.push({
			id:"none",
			name:"Generic"
		});
		this.temp_radio = new MEVRadioGroup(t_div,data.templates,["id","name"],"temp-radio");
		let s_div=$("<div>").appendTo(this.div);
		$("<input>").attr({type:"checkbox",id:"use-sample-ids"}).appendTo(s_div)
		$("<label>").text("Has Sample Ids").appendTo(s_div);
		$("<button>").attr("class","btm btn-primary")
		    .appendTo(this.div).text("Upload File")
			.click(function(e){
				self.submit();
			});
				
	}
	
	checkFileUploaded(){
		let self = this;
		$.ajax({
			url:"/meths/get_project_data/"+this.project_id,
			type:"GET",
			dataType:"json"
		}).done(function(resp){
			if (resp.data.uploading_data){
				setTimeout(function(){
					self.checkFileUploaded();
				},20000)
			}
			else{
				if (!resp.data.uploading_error){
					let msg = "The data has been uploaded. A view can be created <a href='/projects/data_view/home'>here</a>";
					self.waiting_icon.showMessage(msg,"success")
				}
				else{
					self.waiting_icon.showMessage("There was a problem uplaoding data, please contact an administrator","danger");
				}
				
			}
		});
		
		
	}
	
	submit(){
		let self = this;
		new MLVFileChooser(function(file){
			let url ="/meths/execute_project_action/"+self.project_id;
			let data={
				method:"upload_data_file",
				arguments:{
					columns:file.fields,
					template:self.temp_radio.getCheckedValue(),
					use_sample_ids:$("#use-sample-ids").prop("checked")
					
				}
			}
			self.waiting_icon= new WaitingDialog("Uploading And Processing File");
			self.waiting_icon.wait("Uploading File");
			mlvUploadFile(file.file,url,data,function(resp){
				self.waiting_icon.setWaitingMessage("Processing File")
				self.checkFileUploaded();
			})		
			
		}).showOpenDialog();
		
	}
	
	
}

class MEVRadioGroup{
	constructor(div,data,param,name){
		this.name=name;
		let first = true;
		for (let item of data){
			let d = $("<div>").appendTo(div);
			$("<input>")
				.attr({type:"radio",name:name,value:item[param[0]]})
				.prop("checked",first)
				.appendTo(div);
		    $("<label>").text(item[param[1]]).appendTo(div);
		    first=false;
			
		}
	}
	
	getCheckedValue(){
		return $("input[name='"+this.name+"']:checked").val();
	}
}