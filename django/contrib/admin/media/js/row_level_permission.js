/**
 * @author clong
 */
      //dojo.require("dojo.io.*");
      //dojo.require("dojo.event.*");
      //dojo.require("dojo.lfx.*");
      //dojo.require("dojo.widget.*");
      //dojo.require("dojo.json");

function addButtonPressed(obj_ct, obj_id)
{
    return;
  dojo.io.bind({
		 url: "/rlp/add/"+obj_ct+"/"+obj_id+"/ajax/", 
		 handler: addCallback,
		 formNode: dojo.byId('addRLPForm')
	      });
}

function addCallback(type, data, evt)
{
    if (type == 'error')
	alert('Error when retrieving data from the server!');
    else
    {
	dictData = dojo.json.evalJson(data);
	if(dictData.result == false)
	{
	    //outputError(dictData.text);
	    return;
	}
	alert("Success!");
	//outputMsg(dictData.text);
	//dojo.lfx.html.highlight(dojo.byId("editRLP-"+dictData.id), [184, 204, 228], 1000).play();
    }
}

function applyButtonPressed(id)
{
return;
    strArray = id.split("/");
  dojo.io.bind({
		 url: "/rlp/change/"+id+'/ajax/', 
		 handler: editCallback,
		 formNode: dojo.byId('editRLPForm-'+strArray[1])
	      });
}

function editCallback(type, data, evt)
{
    if (type == 'error')
	alert('Error when retrieving data from the server!');
    else
    {
	dictData = dojo.json.evalJson(data);
	if(dictData.result == false)
	{
	    outputError(dictData.text);
	    dojo.lfx.html.highlight(dojo.byId("editRLP-"+dictData.id), [255, 0, 0], 1000).play();
	    alert("Error");
	    return;
	}
	outputMessage(dictData.text);
	dojo.lfx.html.highlight(dojo.byId("editRLP-"+dictData.id), [184, 204, 228], 1000).play();
    }
}

function deleteRLP(id)
{
return;
    var confirm_ans = confirm("Are you sure?");
    if(confirm_ans) 
    {
	dojo.io.bind({
		   url: '/rlp/delete/'+id+'/ajax',
		   handler: deleteCallback,
		    mimetype: 'text/json'
		});
    }
}

function deleteCallback(type, data, evt)
{
    if (type == 'error')
	alert('Error when retrieving data from the server!');
    else
    {
	dictData = dojo.json.evalJson(data);
	if(dictData.result == false)
	{
	    //outputError(dictData.text);
	    dojo.lfx.html.highlight(dojo.byId("editRLP-"+dictData.id), [255, 0, 0], 1000).play();
	    return;
	}
	outputMessage(dictData.text);
	var row = dojo.byId('editRLP-'+dictData.id);    
	var fadeOut = dojo.lfx.fadeOut(row, 1000, null, function(n) {
		    var table = dojo.byId('rlpTable');
		    table.deleteRow(row.rowIndex);    
		    });
	dojo.lfx.html.highlight(row, [255, 0, 0], 500).play(1500);
	fadeOut.play();
    }
}

function copyToNew(id)
{
    var newForm = document.addRLPForm;
    var form = dojo.byId("editRLPForm-"+id);
    newForm.owner.selectedIndex = form.owner.selectedIndex;
    newForm.perm.selectedIndex = form.perm.selectedIndex;
    newForm.negative.checked = form.negative.checked;
}

function outputErrors(errs)
{
    var output = genOutput('errors', errs);
    dojo.lfx.html.highlight(output, [240, 0, 0], 3000).play();
}

function outputMessage(messages)
{
    var output = genOutput('messages', messages);
    dojo.lfx.html.highlight(output, [184, 204, 228], 3000).play();
}

function genOutput(id, str)
{
    var list = document.createElement("ul");
    list.id = id;
    var txt = document.createTextNode(str);
    var ele = document.createElement("li");
    ele.appendChild(txt);
    list.appendChild(ele);
    var output = dojo.byId('output');
    removeChildrenFromNode(output);
    output.appendChild(list);
    return output;
}


function removeChildrenFromNode(node)
{
  
	while (node.hasChildNodes())
	{
	  node.removeChild(node.firstChild);
	}
}


function init()
{
    for(var i=0; i<document.forms.length; i++)
    {
	document.forms[i].reset();
    }
}

//dojo.addOnLoad(init);