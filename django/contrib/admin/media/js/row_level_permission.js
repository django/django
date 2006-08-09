var add_row_level_permission = {
	init: function() {
	   // Grab the elements we’ll need.                                                                                                                                      
	   add_row_level_permission.form = document.getElementById("addRLPForm");
	   add_row_level_permission.results_div = document.getElementById("rlpResults");

	   // This is so we can fade it in later.                                                                                                                                
	   YAHOO.util.Dom.setStyle(add_row_level_permission.results_div, "opacity", 0);
	
	   // Hijack the form.                                                                                                                                                   
	   YAHOO.util.Event.addListener(add_row_level_permission.form, "submit", add_row_level_permission.submit_func);
	},
	
	submit_func: function(e) {
	   YAHOO.util.Event.preventDefault(e);
	
		//TODO: Remove any error messages here
	
	   YAHOO.util.Connect.setForm(add_row_level_permission.form);
	
	   //Temporarily disable the form.                                                                                                                                       
	   for(var i=0; i<add_row_level_permission.form.elements.length; i++) {
	      add_row_level_permission.form.elements[i].disabled = true;
	   }
	   var cObj = YAHOO.util.Connect.asyncRequest("POST", 
	   									add_row_level_permission.form.action+"?ajax" , 
										add_row_level_permission.ajax_callback);
	},
	
	ajax_callback: {
      success: function(o) {
	  	var response_obj = eval('(' + o.responseText + ')');
	  	// Set up the animation on the results div.
		var result_fade_out = null;
		if(response_obj.result) {
			result_fade_out = row_level_permission.output_success(response_obj.text, add_row_level_permission.results_div);
			var results=response_obj.results
			var new_rows = [];
			var table = row_level_permission.edit_table;
			for(var i=0; i<results.length; i++) {
				row = add_row_level_permission.add_rlp_row(results[i].id, results[i].permission, results[i].hash);
				var row_fade_in = new YAHOO.util.Anim(row, {
								 opacity: { from: 0, to: 100 } 
								 }, 1, YAHOO.util.Easing.easeOut);
				row_fade_in.onStart.subscribe(function() {
		    		table.appendChild(row);
				});
				row_fade_in.animate();
			}
		} else {
			result_fade_out = row_level_permission.output_error(response_obj.text, 
														add_row_level_permission.results_div);
		}
		for(var i=0; i<add_row_level_permission.form.elements.length; i++)
			add_row_level_permission.form.elements[i].disabled = false;
		result_fade_out.animate();
	 },
      
      failure: function(o) {
	 		alert('An error has occurred');
		for(var i=0; i<add_row_level_permission.form.elements.length; i++)
			add_row_level_permission.form.elements[i].disabled = false;		
      }
   },
   
   add_rlp_row: function(id, permission, hash) {
		var emptyRow = document.getElementById('empty_editRLP');
		var newRow = emptyRow.cloneNode(true);
		var form = YAHOO.util.Dom.getElementsByClassName('editRLPForm', 'form', newRow);
		form=form[0]; 
		form.owner.options.selectedIndex = add_row_level_permission.form.owner.selectedIndex;
		form.perm.options.selectedIndex = row_level_permission.find_in_select(form.perm, permission);
		form.negative.checked =add_row_level_permission.form.negative.checked;
		form.id = "editRLPForm-"+id;
		newRow.id = "editRLP-"+id;
		
		var delete_link = YAHOO.util.Dom.getElementsByClassName('deleteLink', 'a', form);
		delete_link = delete_link[0];
		delete_link.href = "../../../auth/row_level_permission/"+hash+"/delete/";
		
		var copy_link = YAHOO.util.Dom.getElementsByClassName('copyToNewLink', 'a', newRow);
		copy_link = copy_link[0];
		copy_link.href = "javascript:row_level_permission.copyToNew("+id+")";
		
		form.action = "../../../auth/row_level_permission/"+hash+"/change/"		

		row_level_permission.add_delete_listener(delete_link);
		row_level_permission.add_apply_listener(form);

		return newRow; 
   },
};

var row_level_permission = {
	init: function() {
		row_level_permission.results_div = document.getElementById("rlpResults");
		row_level_permission.edit_table = document.getElementById('current-rlpTable');
	},
	
	find_in_select: function(select,val) {
		options = select.options;
		for(var i=0; i<options.length; i++) {
			if(options[i].value==val) {
				return i
			}
		}
		return -1;
	},
	
	add_apply_listener: function(el) {
		YAHOO.util.Event.addListener(
          el,
          'submit',
          function(e) {
		  	YAHOO.util.Event.preventDefault(e);
			row_level_permission.applyRLP(this.action, this);
		  }
    	);	
	},

	add_delete_listener: function(el) {
	    YAHOO.util.Event.addListener(
	          el,
	          'click',
	          function(e) {
			  	YAHOO.util.Event.preventDefault(e);
				row_level_permission.deleteRLP(this.href);
			  }
	    );
	},
	
	deleteRLP: function(url) {
		var confirm_ans = confirm("Are you sure?");
	    if(confirm_ans)
			var cObj = YAHOO.util.Connect.asyncRequest("POST", 
	   									url+"?ajax" , 
										row_level_permission.delete_callback);
		return false; 
	},
	
	delete_callback: {
		success: function(o)
		{
			var response_obj = eval('(' + o.responseText + ')');
		  	// Set up the animation on the results div.
			var result_fade_out = null;
			if(response_obj.result) {
				result_fade_out = row_level_permission.output_success(response_obj.text, document.getElementById("rlpResults"));
				var row_fade_out = new YAHOO.util.Anim('editRLP-'+response_obj.id, {
								 opacity: { from:100, to: 0 } 
								 }, 1, YAHOO.util.Easing.easeOut);
				row_fade_out.onComplete.subscribe(function() {
					var row = document.getElementById('editRLP-'+response_obj.id);
					var table = row_level_permission.edit_table;
		    		table.removeChild(row);
				});
				row_fade_out.animate();
			} else {
				result_fade_out = row_level_permission.output_errort(response_obj.text, 
														row_level_permission.results_div);
			}
			result_fade_out.animate();
		},
		failure: function(o)
		{
			alert('An error has occurred');
		}
	},
	
	output_error: function(text, div){
		YAHOO.util.Dom.replaceClass(div, "system-message", "errornote");
		return row_level_permission.output_text(text, div);
	},

	output_success: function(text, div){
		YAHOO.util.Dom.replaceClass(div, "errornote", "system-message");
		return row_level_permission.output_text(text, div);
	},
	
	output_text: function (text, div) {
		 var result_fade_out = new YAHOO.util.Anim(div, {
					      opacity: { to: 0 }
					   }, 0.25, YAHOO.util.Easing.easeOut);
			var success_message = document.createElement('p');
			success_message.innerHTML = text;
			YAHOO.util.Dom.setStyle(div, 'display', 'block');
			var result_fade_in = new YAHOO.util.Anim(div, {
					opacity: { to: 1 }
				     }, 0.25, YAHOO.util.Easing.easeIn);
			result_fade_out.onComplete.subscribe(function() {
				    div.innerHTML = '';
				    div.appendChild(success_message);
				    result_fade_in.animate();
				 });	
			return result_fade_out;				   
	},
	
	applyRLP: function(url, form) {
		YAHOO.util.Connect.setForm(form);
		var cObj = YAHOO.util.Connect.asyncRequest("POST", 
	   									url+"?ajax" , 
										row_level_permission.apply_callback);
		return false; 
	},
	
	apply_callback: {
		success: function(o)
		{
			var response_obj = eval('(' + o.responseText + ')');
		  	// Set up the animation on the results div.
			var result_fade_out = null;
			if(response_obj.result) {
				result_fade_out = row_level_permission.output_success(response_obj.text, document.getElementById("rlpResults"));
				var row_highlight_on = new YAHOO.util.ColorAnim('editRLP-'+response_obj.id, {
								 backgroundColor: { to: 'rgb(255, 255, 204)' } 
								 }, 1);
				var row_highlight_off = new YAHOO.util.ColorAnim('editRLP-'+response_obj.id, {
								 backgroundColor: { to: 'rgb(255, 255, 255)' } 
								 }, 1);
				row_highlight_on.onComplete.subscribe(function() {
					row_highlight_off.animate();
					});
				row_highlight_on.animate(); 
			} else {
				result_fade_out = row_level_permission.output_errort(response_obj.text, 
														row_level_permission.results_div);
			}
			result_fade_out.animate();
		},
		failure: function(o)
		{
			alert('An error has occurred');
		}
	},	
	
	copyToNew: function (id)
	{
	    var newForm = add_row_level_permission.form;
	    var form = document.getElementById("editRLPForm-"+id);
	    newForm.owner.selectedIndex = form.owner.selectedIndex;
	    newForm.perm.selectedIndex = form.perm.selectedIndex;
	    newForm.negative.checked = form.negative.checked;
	}	
}

