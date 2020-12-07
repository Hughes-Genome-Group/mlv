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
				waiting_icon = new WaitingDialog("Uploading And Processing File");
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
			let d= $("<div>").attr({"class":"alert alert-info","id":"upload-info"})
			      .css({"margin-left":"auto","margin-right":"auto","width":"50%"})
			      .html(`<b>Please upload a file containing infomation about your genomic regions of interest</b><br>
			            <ul>
			      		<li>The file can either be a tab(.tsv) or comma(.csv) delmited text file and can also be gzipped (.gz)</li>
                        <li>The only requirement is that the first three columns (in order) specify the genomic location i.e. chromosome, start and finish </li>
                        <li>Normal bed files as well as excel data that has been saved as a .csv or .tsv file cab be used </li>
                        <li>There can be as many other columns as you like and column headers are not essential as column names can be added </li>
                        <li>Chromosome names need to be either UCSC (chr1,chr2,chrX) or Ensemble (1,2,X) format </li>
                        <li>Other file formats e.g. BigWig, Bam, BigBed etc can be added later </li>
 
`)
			$("#split-container").append(d)
			
		}
		else{
			loadMLVView(response);
		}
		
	});	
}

function loadMLVView(project){
	$("#upload-info").remove();
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
	waiting_icon= new WaitingDialog("Uploading And Processing File");
	waiting_icon.wait("Uploading File");
	mlvUploadFile(file,url,data,function(response){		
    	checkUploading();	
	});
	mlv_file_upload.remove();
	
	
}




