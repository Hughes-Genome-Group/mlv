class WaitingIcon{
	constructor(element_id){
		this.element_id=element_id;
	}
	
	show(msg){
		this.div=$("<div>").css({transform: "translate(-50%, -50%)",
            "position":"absolute",
            "top":"50%",
            "left":"50%"
        });
		let p= $("<p>").css("text-align","center");
		p.append($("<i class='fa fa-spinner fa-spin fa-10x'></i>").css("font-size","50px"));
		this.div.append(p);
		this.message= $("<p>").css("text-align","center").attr("id","mlv-waiting-msg").text(msg);
        this.div.append(this.message);
		$("#"+this.element_id).append(this.div);     
		 
		
	}
	hide(){
		this.div.remove();
	}
	
	changeMessage(msg){
		this.message.text(msg)
	}
	
	showURL(url){
		this.hide();
		this.div=$("<div>");
		this.div.append("<p>The Project was succussfully created and can be viewed at the following link:</p><br>");
    	this.div.append($("<a>").attr("href",url).text(url));
    	$("#"+this.element_id).append(this.div);
    	
		
	}
	showMessage(msg,type){
		this.hide();
		this.div=$("<div class='alert alert-"+type+"' role='alert'></div>").text(msg);
		$("#"+this.element_id).append(this.div);
	}
	
}


function _getElementHeight(el){
	let height= el.css("height");
	if (!height){
		return 0;
	}
	let a= parseInt(height.replace("px",""));
	return a;
	
}

function _changeDialogSize(th){
	  let pa= th.parent();
	  let title_height =_getElementHeight(pa.find(".ui-dialog-titlebar"));
	  let button_height = _getElementHeight(pa.find(".ui-dialog-buttonpane"));
	  let pa_height=_getElementHeight(pa);
	  console.log(title_height);
	  console.log(button_height);
	  console.log(pa_height);
	  
	  let h = (pa_height-title_height-button_height-15)+"px"   	   
      th.css({width:"100%",height:h});
	
}
function jqueryDialogFixes(dialog){
	  dialog.on("dialogdrag",function(e,ui){
      	if (ui.position.top<50){
      		ui.position.top=50;
      	}
      });
      dialog.on("dialogopen",function(e,ui){
      	if ($(this).parent().position().top<50){
      		$(this).parent().css("top","50px");
      	}
      	
      });
      dialog.on("dialogresize",function(e,ui){
    	  let th=$(this);
    	  _changeDialogSize(th);
    	  
    	
    	  
      });
      dialog.on("dialogresizestop",function(e,ui){
    	  let th=$(this);
    	  _changeDialogSize(th);  
      });
 
}





