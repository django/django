var row_level_permission = {
	
	
	copyToNew: function (id)
	{
	    var newForm = add_row_level_permission.form;
	    var form = document.getElementById("editRLPForm-"+id);
	    newForm.owner.selectedIndex = form.owner.selectedIndex;
	    newForm.perm.selectedIndex = form.perm.selectedIndex;
	    newForm.negative.checked = form.negative.checked;
	}	
}

