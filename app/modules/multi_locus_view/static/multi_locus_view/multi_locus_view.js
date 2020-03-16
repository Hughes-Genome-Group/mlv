var waiting_icon=null;
var mlv_file_upload=null;

function initializePage(){
	$.ajax({
		url:"/meths/get_project_data/"+project_id,
		dataType:"json",
		type:"GET"
	}).done(function(response){
		response.data.permission = response.permission;
		if (!response.data.viewset_id){
			if (response.data.uploading_file){
				waiting_icon = new WaitingDialog("Uploading And Proecessing File");
				waiting_icon.wait("Processing File");
				checkUploading();
				return;
			}
			if (response.status==="Failed Upload"){
				waiting_icon = new WaitingDialog("Uploading And Proecessing File");
				waiting_icon.showMessage("Processing has failed - please contact an administrator");
				return;
			}
			let config = {
					 compulsory_fields:{
					         1:{label:"chromosome",datatype:"text"},
					         2:{label:"start",datatype:"integer"},
					         3:{label:"finish",datatype:"integer"}
					    }
					}
			mlv_file_upload = new MLVFileUploadDialog(config);
			mlv_file_upload.setUploadCallback(uploadViewSet);
			
		}
		else{
			loadMLVView(response);
		}
		
	});	
}

function loadMLVView(project){
	new MLViewBase("split-container",
			project,
			{
				graphs:{position:"top",menu_bar:true},
				add_annotations:true,
				create_subset:true,
				add_peak_stats:true,
				cluster_on_columns:true
			}			
		)
}

function checkUploading(){
	waiting_icon.setWaitingMessage("Processing file");
	$.ajax({
		url:"/meths/get_project_data/"+project_id,
		dataType:"json"
		
	}).done(function(response){
		if (response.status==="Failed Upload"){
			waiting_icon.showMessage("Uploading has failed - please contact an administrator","danger");
			return;
		}
		if (!response.data.uploading_file){
			waiting_icon.remove();
			loadMLVView(response);
			
		}
		else{
			setTimeout(checkUploading,5000);
		}
	})
	
}


function uploadViewSet(file,fields,has_headers,delimiter){
	let url = "/meths/execute_project_action/"+project_id;
	let data = {
			method:"upload_file",
			arguments:{
				fields:fields,
				has_headers:has_headers,
				delimiter:delimiter
			}
	}
	waiting_icon= new WaitingDialog("Uploading And Proecessing File");
	waiting_icon.wait("Uploading File");
	mlvUploadFile(file,url,data,function(response){		
    	checkUploading();	
	});
	mlv_file_upload.remove();
	
	
}




