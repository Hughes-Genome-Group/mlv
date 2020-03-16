class UploadAnnotationSet{
	constructor(div,table){
		let self = this;
		this.table = table;
		this.div=$("#"+div)
		this.form = new NameDescGenomeForm(
			this.div,
			"annotation_set",
			function(project_id){
				self.uploadFile(project_id);
			}
		)
		
	}
	
	
	checkProgress(){
		let self =this;
		$.ajax({
			url:"/meths/get_project_data/"+this.project_id,
			dataType:"json",
		}).done(function(response){
			if (!response.data.processing_file){
				if (response.status==="failed"){
					self.waiting_dialog.showMessage("There was a problem processing the data - please contact an administrator")
				}
				else{
					self.allDone();
				}
			}
			else{
				setTimeout(function(){
					self.checkProgress();
				},10000)
						
			}	
		})		
		
	}
	
	allDone(){
		this.table.refresh();
		this.form.reset();
		let msg = "The annotations have been created.";
		msg+="It can be used to find intersections with features.";
		msg+="Annotations can be managed using the table on the left.";
		this.waiting_dialog.showMessage(msg);
		
	}
	

	
	uploadFile(project_id){
		let self = this;
		this.project_id=project_id;
		let config = {
			compulsory_fields:{
				1:{label:"chromosome",datatype:"text"},
				2:{label:"start",datatype:"integer"},
				3:{label:"finish",datatype:"integer"}
			}
		}
		let mlv_file_upload = new MLVFileUploadDialog(config);
		mlv_file_upload.setUploadCallback(function(file,fields,has_headers){
			let url = "/meths/execute_project_action/"+project_id;
			let data = {
					method:"create_from_file",
					arguments:{
						fields:fields,
						has_headers:has_headers
					}
			}
			self.waiting_dialog = new WaitingDialog("Creating Annotation Set");
			self.waiting_dialog.wait();

			mlvUploadFile(file,url,data,function(response){
				
		    	self.checkProgress();
				
			});
			mlv_file_upload.remove();

		
		});
	}	
}

