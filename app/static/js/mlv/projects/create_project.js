var arr = window.location.href.split("/");
var project_type= arr[arr.length-2];

$(function(){
	  $("#submit-button").click(function(e){
		  submit_create_form();
	  });
	
	  	
})


function form_submitted(data){
	if (data.success){
		var href = "/projects/"+project_type+"/"+data.project_id;
		window.location=href;
	}
	else{
		var warning= $("<div>").attr("class","alert alert-danger").text(data.msg)
		$("#warning-holder").empty().append(warning)
	}
}


function submit_create_form(){	
	$.ajax({		
		url:"/meths/create_project/"+project_type,
		data:{
			name:$("#project-name").val(),
			description:$("#project-description").val(),
			genome:$("#genome-select").val(),
			email:$("#user-email").val()
			
		},
		type:"POST",
		dataType:"json"
	}).done(function(data){
		form_submitted(data);
	})
}