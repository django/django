/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
version: 0.11.1
*/

/**
 * The Connection Manager provides a simplified interface to the XMLHttpRequest
 * object.  It handles cross-browser instantiantion of XMLHttpRequest, negotiates the
 * interactive states and server response, returning the results to a pre-defined
 * callback you create.
 * @ class
 */
YAHOO.util.Connect =
{
/**
   * Array of MSFT ActiveX ids for XMLHttpRequest.
   * @private
   * @type array
   */
	_msxml_progid:[
			'MSXML2.XMLHTTP.3.0',
			'MSXML2.XMLHTTP',
			'Microsoft.XMLHTTP'
			],

  /**
   * Object literal of HTTP header(s)
   * @private
   * @type object
   */
	_http_header:{},

  /**
   * Determines if HTTP headers are set.
   * @private
   * @type boolean
   */
	_has_http_headers:false,

 /**
  * Property that that determines if a default header of
  * Content-Type of 'application/x-www-form-urlencoded'
  * will be added to any client HTTP headers sent.
  * @private
  * @type boolean
  */
    _default_post_header:true,

 /**
  * Property modified by setForm() to determine if the data
  * should be submitted as an HTML form.
  * @private
  * @type boolean
  */
    _isFormSubmit:false,

 /**
  * Property modified by setForm() to determine if a file(s)
  * upload is expected.
  * @private
  * @type boolean
  */
    _isFileUpload:false,

 /**
  * Property modified by setForm() to set a reference to the HTML
  * form node if the desired action is file upload.
  * @private
  * @type object
  */
    _formNode:null,

 /**
  * Property modified by setForm() to set the HTML form data
  * for each transaction.
  * @private
  * @type string
  */
    _sFormData:null,

 /**
  * Collection of polling references to the polling mechanism in handleReadyState.
  * @private
  * @type string
  */
    _poll:[],

 /**
  * Queue of timeout references for each transaction with a defined timeout value.
  * @private
  * @type string
  */
    _timeOut:[],

  /**
   * The polling frequency, in milliseconds, for HandleReadyState.
   * when attempting to determine a transaction's XHR readyState.
   * The default is 50 milliseconds.
   * @private
   * @type int
   */
     _polling_interval:50,

  /**
   * A transaction counter that increments the transaction id for each transaction.
   * @private
   * @type int
   */
     _transaction_id:0,

  /**
   * Member to add an ActiveX id to the existing xml_progid array.
   * In the event(unlikely) a new ActiveX id is introduced, it can be added
   * without internal code modifications.
   * @public
   * @param string id The ActiveX id to be added to initialize the XHR object.
   * @return void
   */
	setProgId:function(id)
	{
		this._msxml_progid.unshift(id);
		YAHOO.log('ActiveX Program Id  ' + id + ' added to _msxml_progid.', 'info', 'Connection');
	},

  /**
   * Member to enable or disable the default POST header.
   * @public
   * @param boolean b Use default header - true or false .
   * @return void
   */
	setDefaultPostHeader:function(b)
	{
		YAHOO.log('Default POST header set to  ' + b, 'info', 'Connection');
		this._default_post_header = b;
	},

  /**
   * Member to modify the default polling interval.
   * @public
   * @param {int} i The polling interval in milliseconds.
   * @return void
   */
	setPollingInterval:function(i)
	{
		if(typeof i == 'number' && isFinite(i)){
				this._polling_interval = i;
				YAHOO.log('Default polling interval set to  ' + i, 'info', 'Connection');
		}
	},

  /**
   * Instantiates a XMLHttpRequest object and returns an object with two properties:
   * the XMLHttpRequest instance and the transaction id.
   * @private
   * @param {int} transactionId Property containing the transaction id for this transaction.
   * @return connection object
   */
	createXhrObject:function(transactionId)
	{
		var obj,http;
		try
		{
			// Instantiates XMLHttpRequest in non-IE browsers and assigns to http.
			http = new XMLHttpRequest();
			//  Object literal with http and tId properties
			obj = { conn:http, tId:transactionId };
			YAHOO.log('XHR object created for transaction  ' + transactionId, 'info', 'Connection');
		}
		catch(e)
		{
			for(var i=0; i<this._msxml_progid.length; ++i){
				try
				{
					// Instantiates XMLHttpRequest for IE and assign to http.
					http = new ActiveXObject(this._msxml_progid[i]);
					//  Object literal with http and tId properties
					obj = { conn:http, tId:transactionId };
					YAHOO.log('ActiveX XHR object created for transaction  ' + transactionId, 'info', 'Connection');
					break;
				}
				catch(e){}
			}
		}
		finally
		{
			return obj;
		}
	},

  /**
   * This method is called by asyncRequest to create a
   * valid connection object for the transaction.  It also passes a
   * transaction id and increments the transaction id counter.
   * @private
   * @return object
   */
	getConnectionObject:function()
	{
		var o;
		var tId = this._transaction_id;

		try
		{
			o = this.createXhrObject(tId);
			if(o){
				this._transaction_id++;
			}
		}
		catch(e){}
		finally
		{
			return o;
		}
	},

  /**
   * Method for initiating an asynchronous request via the XHR object.
   * @public
   * @param {string} method HTTP transaction method
   * @param {string} uri Fully qualified path of resource
   * @param callback User-defined callback function or object
   * @param {string} postData POST body
   * @return {object} Returns the connection object
   */
	asyncRequest:function(method, uri, callback, postData)
	{
		var o = this.getConnectionObject();

		if(!o){
			YAHOO.log('Unable to create connection object.', 'error', 'Connection');
			return null;
		}
		else{
			if(this._isFormSubmit){
				if(this._isFileUpload){
					this.uploadFile(o.tId, callback, uri);
					this.releaseObject(o);
					return;
				}

				//If the specified HTTP method is GET, setForm() will return an
				//encoded string that is concatenated to the uri to
				//create a querystring.
				if(method == 'GET'){
					uri += "?" +  this._sFormData;
				}
				else if(method == 'POST'){
					postData =  this._sFormData;
				}
				this._sFormData = '';
			}

			o.conn.open(method, uri, true);

			if(this._isFormSubmit || (postData && this._default_post_header)){
				this.initHeader('Content-Type','application/x-www-form-urlencoded');
				YAHOO.log('Initialize default header Content-Type to application/x-www-form-urlencoded.', 'info', 'Connection');
				if(this._isFormSubmit){
					this._isFormSubmit = false;
				}
			}

			//Verify whether the transaction has any user-defined HTTP headers
			//and set them.
			if(this._has_http_headers){
				this.setHeader(o);
			}

			this.handleReadyState(o, callback);
			postData?o.conn.send(postData):o.conn.send(null);

			return o;
		}
	},

  /**
   * This method serves as a timer that polls the XHR object's readyState
   * property during a transaction, instead of binding a callback to the
   * onreadystatechange event.  Upon readyState 4, handleTransactionResponse
   * will process the response, and the timer will be cleared.
   *
   * @private
   * @param {object} o The connection object
   * @param callback User-defined callback object
   * @return void
   */
    handleReadyState:function(o, callback)
    {
        var timeOut = callback.timeout;
        var oConn = this;

        try
        {
            if(timeOut !== undefined){
            	this._timeOut[o.tId] = window.setTimeout(function(){ oConn.abort(o, callback, true) }, timeOut);
            }
            this._poll[o.tId] = window.setInterval(
                function(){
					if(o.conn && o.conn.readyState == 4){
						window.clearInterval(oConn._poll[o.tId]);
						oConn._poll.splice(o.tId);
						if(timeOut){
							oConn._timeOut.splice(o.tId);
						}

						oConn.handleTransactionResponse(o, callback);
                    }
                }
            ,this._polling_interval);
        }
        catch(e)
        {
            window.clearInterval(oConn._poll[o.tId]);
            oConn._poll.splice(o.tId);
			if(timeOut){
				oConn._timeOut.splice(o.tId);
			}

            oConn.handleTransactionResponse(o, callback);
        }
    },

  /**
   * This method attempts to interpret the server response and
   * determine whether the transaction was successful, or if an error or
   * exception was encountered.
   *
   * @private
   * @param {object} o The connection object
   * @param {object} callback - User-defined callback object
   * @param {boolean} determines if the transaction was aborted.
   * @return void
   */
    handleTransactionResponse:function(o, callback, isAbort)
    {
		// If no valid callback is provided, then do not process any callback handling.
		if(!callback){
			this.releaseObject(o);
			YAHOO.log('No callback object to process.  Transaction complete.', 'warn', 'Connection');
			return;
		}

		var httpStatus, responseObject;

		try
		{
			if(o.conn.status !== undefined && o.conn.status != 0){
				httpStatus = o.conn.status;
			}
			else{
				httpStatus = 13030;
			}
		}
		catch(e){
			// 13030 is the custom code to indicate the condition -- in Mozilla/FF --
			// when the o object's status and statusText properties are
			// unavailable, and a query attempt throws an exception.
			httpStatus = 13030;
		}

		if(httpStatus >= 200 && httpStatus < 300){
			responseObject = this.createResponseObject(o, callback.argument);
			if(callback.success){
				if(!callback.scope){
					callback.success(responseObject);
					YAHOO.log('Success callback. HTTP code is ' + httpStatus, 'info', 'Connection');
				}
				else{
					// If a scope property is defined, the callback will be fired from
					// the context of the object.
					callback.success.apply(callback.scope, [responseObject]);
					YAHOO.log('Success callback with scope. HTTP code is ' + httpStatus, 'info', 'Connection');
				}
			}
		}
		else{
			switch(httpStatus){
				// The following case labels are wininet.dll error codes that may be encountered.
				// Server timeout
				case 12002:
				// 12029 to 12031 correspond to dropped connections.
				case 12029:
				case 12030:
				case 12031:
				// Connection closed by server.
				case 12152:
				// See above comments for variable status.
				case 13030:
					responseObject = this.createExceptionObject(o.tId, callback.argument, isAbort);
					if(callback.failure){
						if(!callback.scope){
							callback.failure(responseObject);
							YAHOO.log('Failure callback. Exception detected. Status code is ' + httpStatus, 'warn', 'Connection');
						}
						else{
							callback.failure.apply(callback.scope,[responseObject]);
							YAHOO.log('Failure callback with scope. Exception detected. Status code is ' + httpStatus, 'warn', 'Connection');
						}
					}
					break;
				default:
					responseObject = this.createResponseObject(o, callback.argument);
					if(callback.failure){
						if(!callback.scope){
							callback.failure(responseObject);
							YAHOO.log('Failure callback. HTTP status code is ' + httpStatus, 'warn', 'Connection');
						}
						else{
							callback.failure.apply(callback.scope,[responseObject]);
							YAHOO.log('Failure callback with scope. HTTP status code is ' + httpStatus, 'warn', 'Connection');
						}
					}
			}
		}

		this.releaseObject(o);
    },

  /**
   * This method evaluates the server response, creates and returns the results via
   * its properties.  Success and failure cases will differ in the response
   * object's property values.
   * @private
   * @param {object} o The connection object
   * @param {} callbackArg User-defined argument or arguments to be passed to the callback
   * @return object
   */
    createResponseObject:function(o, callbackArg)
    {
		var obj = {};
		var headerObj = {};

		try
		{
			var headerStr = o.conn.getAllResponseHeaders();
			var header = headerStr.split('\n');
			for(var i=0; i < header.length; i++){
				var delimitPos = header[i].indexOf(':');
				if(delimitPos != -1){
					headerObj[header[i].substring(0,delimitPos)] = header[i].substring(delimitPos + 2);
				}
			}
		}
		catch(e){}

		obj.tId = o.tId;
		obj.status = o.conn.status;
		obj.statusText = o.conn.statusText;
		obj.getResponseHeader = headerObj;
		obj.getAllResponseHeaders = headerStr;
		obj.responseText = o.conn.responseText;
		obj.responseXML = o.conn.responseXML;

		if(typeof callbackArg !== undefined){
			obj.argument = callbackArg;
		}

		return obj;
    },

  /**
   * If a transaction cannot be completed due to dropped or closed connections,
   * there may be not be enough information to build a full response object.
   * The failure callback will be fired and this specific condition can be identified
   * by a status property value of 0.
   *
   * If an abort was successful, the status property will report a value of -1.
   *
   * @private
   * @param {int} tId Transaction Id
   * @param callbackArg The user-defined arguments
   * @param isAbort Determines if the exception is an abort.
   * @return object
   */
    createExceptionObject:function(tId, callbackArg, isAbort)
    {
		var COMM_CODE = 0;
		var COMM_ERROR = 'communication failure';
		var ABORT_CODE = -1;
		var ABORT_ERROR = 'transaction aborted';

		var obj = {};

		obj.tId = tId;
		if(isAbort){
			obj.status = ABORT_CODE;
			obj.statusText = ABORT_ERROR;
		}
		else{
			obj.status = COMM_CODE;
			obj.statusText = COMM_ERROR;
		}

		if(callbackArg){
			obj.argument = callbackArg;
		}

		return obj;
    },

  /**
   * Public method that stores the custom HTTP headers for each transaction.
   * @public
   * @param {string} label The HTTP header label
   * @param {string} value The HTTP header value
   * @return void
   */
	initHeader:function(label,value)
	{
		if(this._http_header[label] === undefined){
			this._http_header[label] = value;
		}
		else{
			this._http_header[label] =  value + "," + this._http_header[label];
		}

		this._has_http_headers = true;
	},

  /**
   * Accessor that sets the HTTP headers for each transaction.
   * @private
   * @param {object} o The connection object for the transaction.
   * @return void
   */
	setHeader:function(o)
	{
		for(var prop in this._http_header){
			if(this._http_header.propertyIsEnumerable){
				o.conn.setRequestHeader(prop, this._http_header[prop]);
				YAHOO.log('HTTP header ' + prop + ' set with value of ' + this._http_header[prop], 'info', 'Connection');
			}
		}
		delete this._http_header;

		this._http_header = {};
		this._has_http_headers = false;
	},

  /**
   * This method assembles the form label and value pairs and
   * constructs an encoded string.
   * asyncRequest() will automatically initialize the
   * transaction with a HTTP header Content-Type of
   * application/x-www-form-urlencoded.
   * @public
   * @param {string || object} form id or name attribute, or form object.
   * @param {string} optional boolean to indicate SSL environment.
   * @param {string} optional qualified path of iframe resource for SSL in IE.
   * @return void
   */
	setForm:function(formId, isUpload, secureUri)
	{
		this._sFormData = '';
		if(typeof formId == 'string'){
			// Determine if the argument is a form id or a form name.
			// Note form name usage is deprecated by supported
			// here for legacy reasons.
			var oForm = (document.getElementById(formId) || document.forms[formId]);
		}
		else if(typeof formId == 'object'){
			var oForm = formId;
		}
		else{
			YAHOO.log('Unable to create form object ' + formId, 'warn', 'Connection');
			return;
		}

		// If the isUpload argument is true, setForm will call createFrame to initialize
		// an iframe as the form target.
		//
		// The argument secureURI is also required by IE in SSL environments
		// where the secureURI string is a fully qualified HTTP path, used to set the source
		// of the iframe, to a stub resource in the same domain.
		if(isUpload){
			(typeof secureUri == 'string')?this.createFrame(secureUri):this.createFrame();
			this._isFormSubmit = true;
			this._isFileUpload = true;
			this._formNode = oForm;

			return;
		}

		var oElement, oName, oValue, oDisabled;
		var hasSubmit = false;

		// Iterate over the form elements collection to construct the
		// label-value pairs.
		for (var i=0; i<oForm.elements.length; i++){
			oDisabled = oForm.elements[i].disabled;

			// If the name attribute is not populated, the form field's
			// value will not be submitted.
			oElement = oForm.elements[i];
			oName = oForm.elements[i].name;
			oValue = oForm.elements[i].value;

			// Do not submit fields that are disabled or
			// do not have a name attribute value.
			if(!oDisabled && oName !== undefined)
			{
				switch (oElement.type)
				{
					case 'select-one':
					case 'select-multiple':
						for(var j=0; j<oElement.options.length; j++){
							if(oElement.options[j].selected){
									this._sFormData += encodeURIComponent(oName) + '=' + encodeURIComponent(oElement.options[j].value || oElement.options[j].text) + '&';
							}
						}
						break;
					case 'radio':
					case 'checkbox':
						if(oElement.checked){
							this._sFormData += encodeURIComponent(oName) + '=' + encodeURIComponent(oValue) + '&';
						}
						break;
					case 'file':
						// stub case as XMLHttpRequest will only send the file path as a string.
					case undefined:
						// stub case for fieldset element which returns undefined.
					case 'reset':
						// stub case for input type reset button.
					case 'button':
						// stub case for input type button elements.
						break;
					case 'submit':
						if(hasSubmit == false){
							this._sFormData += encodeURIComponent(oName) + '=' + encodeURIComponent(oValue) + '&';
							hasSubmit = true;
						}
						break;
					default:
						this._sFormData += encodeURIComponent(oName) + '=' + encodeURIComponent(oValue) + '&';
						break;
				}
			}
		}

		this._isFormSubmit = true;
		this._sFormData = this._sFormData.substr(0, this._sFormData.length - 1);

		YAHOO.log('Form initialized for transaction. POST message is: ' + this._sFormData, 'info', 'Connection');
	},

  /**
   * Creates an iframe to be used for form file uploads.  It is remove from the
   * document upon completion of the upload transaction.
   *
   * @private
   * @param {string} optional qualified path of iframe resource for SSL in IE.
   * @return void
   */
	createFrame:function(secureUri){

		// IE does not allow the setting of id and name attributes as DOM
		// properties.  A different iframe creation pattern is required for IE.
		if(window.ActiveXObject){
			var io = document.createElement('<IFRAME name="ioFrame" id="ioFrame">');
			if(secureUri){
				// IE will throw a security exception in an SSL environment if the
				// iframe source isn't set to a valid resource.
				io.src = secureUri;
			}
		}
		else{
			var io = document.createElement('IFRAME');
			io.id = 'ioFrame';
			io.name = 'ioFrame';
		}

		io.style.position = 'absolute';
		io.style.top = '-1000px';
		io.style.left = '-1000px';

		document.body.appendChild(io);
	},

  /**
   * Uploads HTML form, including files/attachments,  targeting the
   * iframe created in createFrame.
   *
   * @private
   * @param {int} id The transaction id.
   * @param {object} callback - User-defined callback object.
   * @param {string} uri Fully qualified path of resource.
   * @return void
   */
	uploadFile:function(id, callback, uri){
		// Initialize the HTML form properties in case they are
		// not defined in the HTML form.
		this._formNode.action = uri;
		this._formNode.enctype = 'multipart/form-data';
		this._formNode.method = 'POST';
		this._formNode.target = 'ioFrame';
		this._formNode.submit();

		// Reset form status properties.
		this._formNode = null;
		this._isFileUpload = false;
		this._isFormSubmit = false;

		// Create the upload callback handler that fires when the iframe
		// receives the load event.  Subsequently, the event handler is detached
		// and the iframe removed from the document.

		var uploadCallback = function()
		{
			var oResponse =
			{
				tId: id,
				responseText: document.getElementById("ioFrame").contentWindow.document.body.innerHTML,
				argument: callback.argument
			}

			if(callback.upload){
				if(!callback.scope){
					callback.upload(oResponse);
					YAHOO.log('Upload callback.', 'info', 'Connection');
				}
				else{
					callback.upload.apply(callback.scope, [oResponse]);
					YAHOO.log('Upload callback with object scope.', 'info', 'Connection');
				}
			}

			YAHOO.util.Event.removeListener("ioFrame", "load", uploadCallback);
			window.ioFrame.location.replace('#');
			setTimeout("document.body.removeChild(document.getElementById('ioFrame'))",100);
		};

		// Bind the onload handler to the iframe to detect the file upload response.
		YAHOO.util.Event.addListener("ioFrame", "load", uploadCallback);
	},

  /**
   * Public method to terminate a transaction, if it has not reached readyState 4.
   * @public
   * @param {object} o The connection object returned by asyncRequest.
   * @param {object} callback  User-defined callback object.
   * @param {string} isTimeout boolean to indicate if abort was a timeout.
   * @return void
   */
	abort:function(o, callback, isTimeout)
	{
		if(this.isCallInProgress(o)){
			window.clearInterval(this._poll[o.tId]);
			this._poll.splice(o.tId);
			if(isTimeout){
				this._timeOut.splice(o.tId);
			}
			o.conn.abort();

			this.handleTransactionResponse(o, callback, true);
			YAHOO.log('Transaction ' + o.tId + ' aborted.', 'info', 'Connection');

			return true;
		}
		else{
			YAHOO.log('Transaction ' + o.tId + ' abort failed.', 'warn', 'Connection');

			return false;
		}
	},

  /**
   * Public method to check if the transaction is still being processed.
   * @public
   * @param {object} o The connection object returned by asyncRequest
   * @return boolean
   */
	isCallInProgress:function(o)
	{
		// if the XHR object assigned to the transaction has not been dereferenced,
		// then check its readyState status.  Otherwise, return false.
		if(o.conn){
			return o.conn.readyState != 4 && o.conn.readyState != 0;
		}
		else{
			//The XHR object has been destroyed.
			return false;
		}
	},

  /**
   * Dereference the XHR instance and the connection object after the transaction is completed.
   * @private
   * @param {object} o The connection object
   * @return void
   */
	releaseObject:function(o)
	{
		//dereference the XHR instance.
		o.conn = null;

		YAHOO.log('Connection object for transaction ' + o.tId + ' destroyed.', 'info', 'Connection');

		//dereference the connection object.
		o = null;
	}
};
