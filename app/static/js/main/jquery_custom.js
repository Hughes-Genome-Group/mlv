class SendHelpMessageDialog{
	constructor(){
		let self =this;
		this.div=$("<div>");
		let g = $("<div class='form-group'></div>").appendTo(this.div);
		g.append("<label>Subject</label>")
		this.subject_input=$("<input>").attr("class","form-control").appendTo(g);
		g = $("<div class='form-group'></div>").appendTo(this.div)
		g.append("<label>Description of Problem</label>")
		this.text_input = $("<textarea>").attr({"class":"form-control",rows:6}).appendTo(g);
		this.div.dialog({
			autoOpen: true,
			width:400,
			title:"Email a Question",
			buttons:[
				{
					text:"Send",
					click:function(){
						self.send()
					},
					id:"help-dialog-send-button"
				},
				{
					text:"Cancel",
					click:function(){
						self.div.dialog("close")
					}
				}	
			],
			close:function(){
				self.div.dialog("destroy");
				self.div.remove();
			}
		})
	}
	
	send(){
		let self = this;
		$("#help-dialog-send-button").hide();
		let data={
			subject:this.subject_input.val(),
			text:this.text_input.val(),
			url:window.location.href
				
		}
		$.ajax({
			url:"/meths/send_help_email",
			type:"POST",
			dataType:"json",
			contentType:"application/json",
			data:JSON.stringify(data)
			
		}).done(function(resp){
			self.div.empty();
			self.div.append("<div class='alert alert-success'>An email has been sent and we will reply as soon as possible</div>");
			
		})
		 
      
	}
}






function __getElementHeight(el){
	let height= el.css("height");
	if (!height){
		return 0;
	}
	let a= parseInt(height.replace("px",""));
	return a;			
}

$.fn.extend({
  dialogFix: function() {
    return this.each(function() {
	      $(this).parent().find(".ui-dialog-titlebar-close").css("font-size","0px")
	      $(this).on("dialogresize dialogresizestop",function(e,ui){
	    	 $(this).resizeDialog();   	
	      });
	    }); 
  },
  resizeDialog:function(){
	  return this.each(function() {
		  let th=$(this);
		  let pa= th.parent();
		  let title_height =__getElementHeight(pa.find(".ui-dialog-titlebar"));
		      let button_height = __getElementHeight(pa.find(".ui-dialog-buttonpane"));
		       let pa_height=__getElementHeight(pa);  
		       let h = (pa_height-title_height-button_height-10)+"px"   	   
	            th.css({width:"auto",height:h});  
	    });
	  	  
  }
});


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




