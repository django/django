var row_level_permission = {
	copyToNew: function (id)
	{
	    var newForm = document.getElementById("addRLPForm");
	    var form = document.getElementById("editRLPForm-"+id);
	    newForm.owner.selectedIndex = form.owner.selectedIndex;
	    newForm.perm.selectedIndex = form.perm.selectedIndex;
	    newForm.negative.checked = form.negative.checked;
	},
	
	apply_selected: function ()
	{
		var eleList = document.getElementsByName("apply_checkbox");
		var formList = [];
		for(var i=0; eleList.length; i++)
		{
			var ele = eleList[i];
			if(ele.tagName == "INPUT") {
				if(ele.checked)	{
					ele.form.submit();
				}
			}
		}
		return false;
	},
	
	init: function() {
		
	}
}

