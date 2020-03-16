class MLVHelpDialog{
	
    constructor(name,module,config){
    	if (!config){
    		config={};
    		
    	}
    	this.config=config;
    	this.name = name;
    	this.module =module;
    	var self = this;
    	this.edit_mode=false;
    	$.ajax({
    		url:"/meths/get_help_text/"+module+"/"+name,
    		dataType:"json",
    		type:"GET"	
    	}).done(function(response){
    		if (!response.not_show){
    			self._init(response);
    		}
    	});
    	
    }
    
    _init(response){
    	var self=  this
    	this.text=response.text;
    	this.div=$("<div>").attr("class","mlv-help-dialog");
    	this.display_div=$("<div>").html(this.text).appendTo(this.div);
    	this.textarea=$("<textarea>").css({height:"100%",width:"100%","min-height":"200px"}).appendTo(this.div).hide();
    	let buttons = [
    		 {
            		text:"OK",
            		click:function(){
            			self._handleOKClick();
            		},
            		id:"help-dialog-ok-button"
            	}	  
    	 ];
    	 if (response.admin){
    		buttons.push({	
    			text:"Edit",
        		click:function(){
        			self._handleEditClick();
        		},
        		id:"help-dialog-edit-button"
    		});  
    	 }
    	 let title = this.config.title?this.config.title:"Information"
    	 this.div.dialog({
              autoOpen: true,
              buttons:buttons,
              minWidth:500,
              height:400,
              title:"Help",
              close:function(e){
            	  self._notShowAgain();
            	  $(this).empty().remove();	 
              }
          }).dialogFix();
    	 //add remove checkbox
    	 var bp = this.div.parent().find(".ui-dialog-buttonpane");
    	 this.ns_checkbox=$("<input>").attr("type","checkbox");
    	 if (response.autoshow){ 
    		 bp.append(this.ns_checkbox).append("<span>Never show again</span>");
    	 }
    	 //
    	 var titlebar = this.div.parent().find(".ui-dialog-titlebar");
    	 var icon = MLVHelpDialog.type_icons[this.config.type?this.config.type:"help"]
    	 titlebar.prepend($(icon).css({"margin-top":"5px","margin-right":"5px","float":"left","font-size":"20px"}));
    }
    
    _handleEditClick(){
    	var self = this;
    	if (!this.edit_mode){
    		this.display_div.hide();
    		$("#help-dialog-edit-button").text("Save");
    		$("#help-dialog-ok-button").text("Cancel");
    		this.textarea.val(this.text).show();
    		this.div.resizeDialog();
    		this.edit_mode = true;
    	}
    	else{
    		var new_text=this.textarea.val();
    		$.ajax({
    			url:"/meths/save_help_text/"+this.module+"/"+this.name,
    			type:"POST",
    			dataType:"json",
    			data:{text:new_text}
    		}).done(function(resp){
    			self.text=new_text;
    			self.display_div.empty().html(new_text);
    			self._removeEditMode();
    			self.div.resizeDialog();
    			
    		})
    		
    		
    	}
    }
    
    _handleOKClick(){
    	if (this.edit_mode){
    		this._removeEditMode();
    	}
    	else{
    		this.div.dialog("close");
    	}
    	
    }
    
    _removeEditMode(){
    	this.edit_mode=false;
    	this.textarea.hide();
    	this.display_div.show();
    	$("#help-dialog-edit-button").text("Edit");
		$("#help-dialog-ok-button").text("OK");
    }
    
    _notShowAgain(){
    	if (this.ns_checkbox.prop("checked")){
    		$.ajax({
    			url:"/meths/not_show_help_text/"+this.module+"/"+this.name
    		});
    	}
    }
}

MLVHelpDialog.type_icons={
	help:"<i class='fas fa-question-circle'></i>",
	info:"<i class='fas fa-info-circle'></i>",
	warning:"<i class='fas fa-exclamation-circle'></i>"		
}


function mlvShowTooltips(tooltips){
	for (let tip of tooltips){
		let el =tip.el;
		if (typeof tip.el === "string"){
			el =$("#"+tip.el);
		}
	
		let pos = tip.pos?tip.pos:"right";
		el.popover({
			html:true,
			content:tip.msg,
			placement:pos
		});
		el.popover("show");
		
		
	}
	$(".popover").append("<i class='popover-close fas fa-times'></i>");
	
	$(".popover-close").click(function(e){
		let id = $(this).parent().attr("id");
		let el = $("[aria-describedby="+id+"]");
		el.popover("dispose");
	});
	
	
}
    
