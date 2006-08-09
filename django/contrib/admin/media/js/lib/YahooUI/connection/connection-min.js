/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
version: 0.11.1
*/
YAHOO.util.Connect={_msxml_progid:['MSXML2.XMLHTTP.3.0','MSXML2.XMLHTTP','Microsoft.XMLHTTP'],_http_header:{},_has_http_headers:false,_default_post_header:true,_isFormSubmit:false,_isFileUpload:false,_formNode:null,_sFormData:null,_poll:[],_timeOut:[],_polling_interval:50,_transaction_id:0,setProgId:function(id)
{this._msxml_progid.unshift(id);},setDefaultPostHeader:function(b)
{this._default_post_header=b;},setPollingInterval:function(i)
{if(typeof i=='number'&&isFinite(i)){this._polling_interval=i;}},createXhrObject:function(transactionId)
{var obj,http;try
{http=new XMLHttpRequest();obj={conn:http,tId:transactionId};}
catch(e)
{for(var i=0;i<this._msxml_progid.length;++i){try
{http=new ActiveXObject(this._msxml_progid[i]);obj={conn:http,tId:transactionId};break;}
catch(e){}}}
finally
{return obj;}},getConnectionObject:function()
{var o;var tId=this._transaction_id;try
{o=this.createXhrObject(tId);if(o){this._transaction_id++;}}
catch(e){}
finally
{return o;}},asyncRequest:function(method,uri,callback,postData)
{var o=this.getConnectionObject();if(!o){return null;}
else{if(this._isFormSubmit){if(this._isFileUpload){this.uploadFile(o.tId,callback,uri);this.releaseObject(o);return;}
if(method=='GET'){uri+="?"+this._sFormData;}
else if(method=='POST'){postData=this._sFormData;}
this._sFormData='';}
o.conn.open(method,uri,true);if(this._isFormSubmit||(postData&&this._default_post_header)){this.initHeader('Content-Type','application/x-www-form-urlencoded');if(this._isFormSubmit){this._isFormSubmit=false;}}
if(this._has_http_headers){this.setHeader(o);}
this.handleReadyState(o,callback);postData?o.conn.send(postData):o.conn.send(null);return o;}},handleReadyState:function(o,callback)
{var timeOut=callback.timeout;var oConn=this;try
{if(timeOut!==undefined){this._timeOut[o.tId]=window.setTimeout(function(){oConn.abort(o,callback,true)},timeOut);}
this._poll[o.tId]=window.setInterval(function(){if(o.conn&&o.conn.readyState==4){window.clearInterval(oConn._poll[o.tId]);oConn._poll.splice(o.tId);if(timeOut){oConn._timeOut.splice(o.tId);}
oConn.handleTransactionResponse(o,callback);}},this._polling_interval);}
catch(e)
{window.clearInterval(oConn._poll[o.tId]);oConn._poll.splice(o.tId);if(timeOut){oConn._timeOut.splice(o.tId);}
oConn.handleTransactionResponse(o,callback);}},handleTransactionResponse:function(o,callback,isAbort)
{if(!callback){this.releaseObject(o);return;}
var httpStatus,responseObject;try
{if(o.conn.status!==undefined&&o.conn.status!=0){httpStatus=o.conn.status;}
else{httpStatus=13030;}}
catch(e){httpStatus=13030;}
if(httpStatus>=200&&httpStatus<300){responseObject=this.createResponseObject(o,callback.argument);if(callback.success){if(!callback.scope){callback.success(responseObject);}
else{callback.success.apply(callback.scope,[responseObject]);}}}
else{switch(httpStatus){case 12002:case 12029:case 12030:case 12031:case 12152:case 13030:responseObject=this.createExceptionObject(o.tId,callback.argument,isAbort);if(callback.failure){if(!callback.scope){callback.failure(responseObject);}
else{callback.failure.apply(callback.scope,[responseObject]);}}
break;default:responseObject=this.createResponseObject(o,callback.argument);if(callback.failure){if(!callback.scope){callback.failure(responseObject);}
else{callback.failure.apply(callback.scope,[responseObject]);}}}}
this.releaseObject(o);},createResponseObject:function(o,callbackArg)
{var obj={};var headerObj={};try
{var headerStr=o.conn.getAllResponseHeaders();var header=headerStr.split('\n');for(var i=0;i<header.length;i++){var delimitPos=header[i].indexOf(':');if(delimitPos!=-1){headerObj[header[i].substring(0,delimitPos)]=header[i].substring(delimitPos+2);}}}
catch(e){}
obj.tId=o.tId;obj.status=o.conn.status;obj.statusText=o.conn.statusText;obj.getResponseHeader=headerObj;obj.getAllResponseHeaders=headerStr;obj.responseText=o.conn.responseText;obj.responseXML=o.conn.responseXML;if(typeof callbackArg!==undefined){obj.argument=callbackArg;}
return obj;},createExceptionObject:function(tId,callbackArg,isAbort)
{var COMM_CODE=0;var COMM_ERROR='communication failure';var ABORT_CODE=-1;var ABORT_ERROR='transaction aborted';var obj={};obj.tId=tId;if(isAbort){obj.status=ABORT_CODE;obj.statusText=ABORT_ERROR;}
else{obj.status=COMM_CODE;obj.statusText=COMM_ERROR;}
if(callbackArg){obj.argument=callbackArg;}
return obj;},initHeader:function(label,value)
{if(this._http_header[label]===undefined){this._http_header[label]=value;}
else{this._http_header[label]=value+","+this._http_header[label];}
this._has_http_headers=true;},setHeader:function(o)
{for(var prop in this._http_header){if(this._http_header.propertyIsEnumerable){o.conn.setRequestHeader(prop,this._http_header[prop]);}}
delete this._http_header;this._http_header={};this._has_http_headers=false;},setForm:function(formId,isUpload,secureUri)
{this._sFormData='';if(typeof formId=='string'){var oForm=(document.getElementById(formId)||document.forms[formId]);}
else if(typeof formId=='object'){var oForm=formId;}
else{return;}
if(isUpload){(typeof secureUri=='string')?this.createFrame(secureUri):this.createFrame();this._isFormSubmit=true;this._isFileUpload=true;this._formNode=oForm;return;}
var oElement,oName,oValue,oDisabled;var hasSubmit=false;for(var i=0;i<oForm.elements.length;i++){oDisabled=oForm.elements[i].disabled;oElement=oForm.elements[i];oName=oForm.elements[i].name;oValue=oForm.elements[i].value;if(!oDisabled&&oName)
{switch(oElement.type)
{case'select-one':case'select-multiple':for(var j=0;j<oElement.options.length;j++){if(oElement.options[j].selected){this._sFormData+=encodeURIComponent(oName)+'='+encodeURIComponent(oElement.options[j].value||oElement.options[j].text)+'&';}}
break;case'radio':case'checkbox':if(oElement.checked){this._sFormData+=encodeURIComponent(oName)+'='+encodeURIComponent(oValue)+'&';}
break;case'file':case undefined:case'reset':case'button':break;case'submit':if(hasSubmit==false){this._sFormData+=encodeURIComponent(oName)+'='+encodeURIComponent(oValue)+'&';hasSubmit=true;}
break;default:this._sFormData+=encodeURIComponent(oName)+'='+encodeURIComponent(oValue)+'&';break;}}}
this._isFormSubmit=true;this._sFormData=this._sFormData.substr(0,this._sFormData.length-1);},createFrame:function(secureUri){if(window.ActiveXObject){var io=document.createElement('<IFRAME name="ioFrame" id="ioFrame">');if(secureUri){io.src=secureUri;}}
else{var io=document.createElement('IFRAME');io.id='ioFrame';io.name='ioFrame';}
io.style.position='absolute';io.style.top='-1000px';io.style.left='-1000px';document.body.appendChild(io);},uploadFile:function(id,callback,uri){this._formNode.action=uri;this._formNode.enctype='multipart/form-data';this._formNode.method='POST';this._formNode.target='ioFrame';this._formNode.submit();this._formNode=null;this._isFileUpload=false;this._isFormSubmit=false;var uploadCallback=function()
{var oResponse={tId:id,responseText:document.getElementById("ioFrame").contentWindow.document.body.innerHTML,argument:callback.argument}
if(callback.upload){if(!callback.scope){callback.upload(oResponse);}
else{callback.upload.apply(callback.scope,[oResponse]);}}
YAHOO.util.Event.removeListener("ioFrame","load",uploadCallback);window.ioFrame.location.replace('#');setTimeout("document.body.removeChild(document.getElementById('ioFrame'))",100);};YAHOO.util.Event.addListener("ioFrame","load",uploadCallback);},abort:function(o,callback,isTimeout)
{if(this.isCallInProgress(o)){window.clearInterval(this._poll[o.tId]);this._poll.splice(o.tId);if(isTimeout){this._timeOut.splice(o.tId);}
o.conn.abort();this.handleTransactionResponse(o,callback,true);return true;}
else{return false;}},isCallInProgress:function(o)
{if(o.conn){return o.conn.readyState!=4&&o.conn.readyState!=0;}
else{return false;}},releaseObject:function(o)
{o.conn=null;o=null;}};
