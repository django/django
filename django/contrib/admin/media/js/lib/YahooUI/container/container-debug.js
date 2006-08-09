/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
Version 0.11.1
*/

/**
* @class 
* Config is a utility used within an object to allow the implementer to maintain a list of local configuration properties and listen for changes to those properties dynamically using CustomEvent. The initial values are also maintained so that the configuration can be reset at any given point to its initial state.
* @param {object}	owner	The owner object to which this Config object belongs
* @constructor
*/
YAHOO.util.Config = function(owner) {
	if (owner) {
		this.init(owner);
	} else {
		YAHOO.log("No owner specified for Config object", "error");
	}
}

YAHOO.util.Config.prototype = {
	
	/**
	* Object reference to the owner of this Config object
	* @type object
	*/
	owner : null,

	/**
	* Object reference to the owner of this Config object
	* args: key, value
	* @type YAHOO.util.CustomEvent
	*/
	configChangedEvent : null,

	/**
	* Boolean flag that specifies whether a queue is currently being executed
	* @type boolean
	*/
	queueInProgress : false,

	/**
	* Adds a property to the Config object's private config hash. 
	* @param {string}	key	The configuration property's name
	* @param {object}	propertyObject	The object containing all of this property's arguments
	*/
	addProperty : function(key, propertyObject){},

	/**
	* Returns a key-value configuration map of the values currently set in the Config object.
	* @return {object} The current config, represented in a key-value map
	*/
	getConfig : function(){},

	/**
	* Returns the value of specified property.
	* @param {key}		The name of the property
	* @return {object}	The value of the specified property
	*/
	getProperty : function(key){},

	/**
	* Resets the specified property's value to its initial value.
	* @param {key}		The name of the property
	*/
	resetProperty : function(key){},

	/**
	* Sets the value of a property. If the silent property is passed as true, the property's event will not be fired.
	* @param {key}		The name of the property
	* @param {value}	The value to set the property to
	* @param {boolean}	Whether the value should be set silently, without firing the property event.
	* @return {boolean}	true, if the set was successful, false if it failed.
	*/
	setProperty : function(key,value,silent){},

	/**
	* Sets the value of a property and queues its event to execute. If the event is already scheduled to execute, it is
	* moved from its current position to the end of the queue.
	* @param {key}		The name of the property
	* @param {value}	The value to set the property to
	* @return {boolean}	true, if the set was successful, false if it failed.
	*/	
	queueProperty : function(key,value){},

	/**
	* Fires the event for a property using the property's current value.
	* @param {key}		The name of the property
	*/
	refireEvent : function(key){},

	/**
	* Applies a key-value object literal to the configuration, replacing any existing values, and queueing the property events.
	* Although the values will be set, fireQueue() must be called for their associated events to execute.
	* @param {object}	userConfig	The configuration object literal
	* @param {boolean}	init		When set to true, the initialConfig will be set to the userConfig passed in, so that calling a reset will reset the properties to the passed values.
	*/
	applyConfig : function(userConfig,init){},

	/**
	* Refires the events for all configuration properties using their current values.
	*/
	refresh : function(){},

	/**
	* Fires the normalized list of queued property change events
	*/
	fireQueue : function(){},

	/**
	* Subscribes an external handler to the change event for any given property. 
	* @param {string}	key			The property name
	* @param {Function}	handler		The handler function to use subscribe to the property's event
	* @param {object}	obj			The object to use for scoping the event handler (see CustomEvent documentation)
	* @param {boolean}	override	Optional. If true, will override "this" within the handler to map to the scope object passed into the method.
	*/	
	subscribeToConfigEvent : function(key,handler,obj,override){},

	/**
	* Unsubscribes an external handler from the change event for any given property. 
	* @param {string}	key			The property name
	* @param {Function}	handler		The handler function to use subscribe to the property's event
	* @param {object}	obj			The object to use for scoping the event handler (see CustomEvent documentation)
	*/
	unsubscribeFromConfigEvent: function(key,handler,obj){},

	/**
	* Validates that the value passed in is a boolean.
	* @param	{object}	val	The value to validate
	* @return	{boolean}	true, if the value is valid
	*/	
	checkBoolean: function(val) {
		if (typeof val == 'boolean') {
			return true;
		} else {
			return false;
		}
	},

	/**
	* Validates that the value passed in is a number.
	* @param	{object}	val	The value to validate
	* @return	{boolean}	true, if the value is valid
	*/
	checkNumber: function(val) {
		if (isNaN(val)) {
			return false;
		} else {
			return true;
		}
	}
}


/**
* Initializes the configuration object and all of its local members.
* @param {object}	owner	The owner object to which this Config object belongs
*/
YAHOO.util.Config.prototype.init = function(owner) {

	this.owner = owner;
	this.configChangedEvent = new YAHOO.util.CustomEvent("configChanged");
	this.queueInProgress = false;

	/* Private Members */

	var config = {};
	var initialConfig = {};
	var eventQueue = [];

	/**
	* @private
	* Fires a configuration property event using the specified value. 
	* @param {string}	key			The configuration property's name
	* @param {value}	object		The value of the correct type for the property
	*/ 
	var fireEvent = function( key, value ) {
		YAHOO.log("Firing Config event: " + key + "=" + value, "info");
		
		key = key.toLowerCase();

		var property = config[key];

		if (typeof property != 'undefined' && property.event) {
			property.event.fire(value);
		}	
	}
	/* End Private Members */

	/**
	 * @alias YAHOO.util.Config.prototype.addProperty
	 */
	this.addProperty = function( key, propertyObject ) {
		key = key.toLowerCase();
		
		YAHOO.log("Added property: " + key, "info");

		config[key] = propertyObject;

		propertyObject.event = new YAHOO.util.CustomEvent(key);
		propertyObject.key = key;

		if (propertyObject.handler) {
			propertyObject.event.subscribe(propertyObject.handler, this.owner, true);
		}

		this.setProperty(key, propertyObject.value, true);
		
		if (! propertyObject.suppressEvent) {
			this.queueProperty(key, propertyObject.value);
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.getConfig
	 */
	this.getConfig = function() {
		var cfg = {};
			
		for (var prop in config) {
			var property = config[prop]
			if (typeof property != 'undefined' && property.event) {
				cfg[prop] = property.value;
			}
		}
		
		return cfg;
	}

	/**
	 * @alias YAHOO.util.Config.prototype.getProperty
	 */
	this.getProperty = function(key) {
		key = key.toLowerCase();

		var property = config[key];
		if (typeof property != 'undefined' && property.event) {
			return property.value;
		} else {
			return undefined;
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.resetProperty
	 */
	this.resetProperty = function(key) {
		key = key.toLowerCase();

		var property = config[key];
		if (typeof property != 'undefined' && property.event) {
			this.setProperty(key, initialConfig[key].value);
		} else {
			return undefined;
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.setProperty
	 */
	this.setProperty = function(key, value, silent) {
		key = key.toLowerCase();
		
		YAHOO.log("setProperty: " + key + "=" + value, "info");

		if (this.queueInProgress && ! silent) {
			this.queueProperty(key,value); // Currently running through a queue... 
			return true;
		} else {
			var property = config[key];
			if (typeof property != 'undefined' && property.event) {
				if (property.validator && ! property.validator(value)) { // validator
					return false;
				} else {
					property.value = value;
					if (! silent) {
						fireEvent(key, value);
						this.configChangedEvent.fire([key, value]);
					}
					return true;
				}
			} else {
				return false;
			}
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.queueProperty
	 */
	this.queueProperty = function(key, value) {
		key = key.toLowerCase();

		YAHOO.log("queueProperty: " + key + "=" + value, "info");

		var property = config[key];
							
		if (typeof property != 'undefined' && property.event) {
			if (typeof value != 'undefined' && property.validator && ! property.validator(value)) { // validator
				return false;
			} else {

				if (typeof value != 'undefined') {
					property.value = value;
				} else {
					value = property.value;
				}

				var foundDuplicate = false;

				for (var i=0;i<eventQueue.length;i++) {
					var queueItem = eventQueue[i];

					if (queueItem) {
						var queueItemKey = queueItem[0];
						var queueItemValue = queueItem[1];
						
						if (queueItemKey.toLowerCase() == key) {
							// found a dupe... push to end of queue, null current item, and break
							eventQueue[i] = null;
							eventQueue.push([key, (typeof value != 'undefined' ? value : queueItemValue)]);
							foundDuplicate = true;
							break;
						}
					}
				}
				
				if (! foundDuplicate && typeof value != 'undefined') { // this is a refire, or a new property in the queue
					eventQueue.push([key, value]);
				}
			}

			if (property.supercedes) {
				for (var s=0;s<property.supercedes.length;s++) {
					var supercedesCheck = property.supercedes[s];

					for (var q=0;q<eventQueue.length;q++) {
						var queueItemCheck = eventQueue[q];

						if (queueItemCheck) {
							var queueItemCheckKey = queueItemCheck[0];
							var queueItemCheckValue = queueItemCheck[1];
							
							if ( queueItemCheckKey.toLowerCase() == supercedesCheck.toLowerCase() ) {
								eventQueue.push([queueItemCheckKey, queueItemCheckValue]);
								eventQueue[q] = null;
								break;
							}
						}
					}
				}
			}
	
			YAHOO.log("Config event queue: " + this.outputEventQueue(), "info");

			return true;
		} else {
			return false;
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.refireEvent
	 */
	this.refireEvent = function(key) {
		key = key.toLowerCase();

		var property = config[key];
		if (typeof property != 'undefined' && property.event && typeof property.value != 'undefined') {
			if (this.queueInProgress) {
				this.queueProperty(key);
			} else {
				fireEvent(key, property.value);
			}
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.applyConfig
	 */
	this.applyConfig = function(userConfig, init) {
		if (init) {
			initialConfig = userConfig;
		}
		for (var prop in userConfig) {
			this.queueProperty(prop, userConfig[prop]);
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.refresh
	 */
	this.refresh = function() {
		for (var prop in config) {
			this.refireEvent(prop);
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.fireQueue
	 */
	this.fireQueue = function() {
		this.queueInProgress = true;
		for (var i=0;i<eventQueue.length;i++) {
			var queueItem = eventQueue[i];
			if (queueItem) {
				var key = queueItem[0];
				var value = queueItem[1];
				
				var property = config[key];
				property.value = value;

				fireEvent(key,value);
			}
		}
		
		this.queueInProgress = false;
		eventQueue = new Array();
	}

	/**
	 * @alias YAHOO.util.Config.prototype.subscribeToConfigEvent
	 */
	this.subscribeToConfigEvent = function(key, handler, obj, override) {
		key = key.toLowerCase();

		var property = config[key];
		if (typeof property != 'undefined' && property.event) {
			if (! YAHOO.util.Config.alreadySubscribed(property.event, handler, obj)) {
				property.event.subscribe(handler, obj, override);
			}
			return true;
		} else {
			return false;
		}
	}


	/**
	 * @alias YAHOO.util.Config.prototype.unsubscribeFromConfigEvent
	 */
	this.unsubscribeFromConfigEvent = function(key, handler, obj) {
		key = key.toLowerCase();

		var property = config[key];
		if (typeof property != 'undefined' && property.event) {
			return property.event.unsubscribe(handler, obj);
		} else {
			return false;
		}
	}

	/**
	 * @alias YAHOO.util.Config.prototype.toString
	 */
	this.toString = function() {
		var output = "Config";
		if (this.owner) {
			output += " [" + this.owner.toString() + "]";
		}
		return output;
	}

	/**
	 * @alias YAHOO.util.Config.prototype.outputEventQueue
	 */
	this.outputEventQueue = function() {
		var output = "";
		for (var q=0;q<eventQueue.length;q++) {
			var queueItem = eventQueue[q];
			if (queueItem) {
				output += queueItem[0] + "=" + queueItem[1] + ", ";
			}
		}
		return output;
	}
}

/**
* Checks to determine if a particular function/object pair are already subscribed to the specified CustomEvent
* @param {YAHOO.util.CustomEvent} evt	The CustomEvent for which to check the subscriptions
* @param {Function}	fn	The function to look for in the subscribers list
* @param {object}	obj	The execution scope object for the subscription
* @return {boolean}	true, if the function/object pair is already subscribed to the CustomEvent passed in
*/
YAHOO.util.Config.alreadySubscribed = function(evt, fn, obj) {
	for (var e=0;e<evt.subscribers.length;e++) {
		var subsc = evt.subscribers[e];
		if (subsc && subsc.obj == obj && subsc.fn == fn) {
			return true;
			break;
		}
	}
	return false;
}

/**
* @class 
* Module is a JavaScript representation of the Standard Module Format. Standard Module Format is a simple standard for markup containers where child nodes representing the header, body, and footer of the content are denoted using the CSS classes "hd", "bd", and "ft" respectively. Module is the base class for all other classes in the YUI Container package.
* @param {string}	el	The element ID representing the Module <em>OR</em>
* @param {Element}	el	The element representing the Module
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this module. See configuration documentation for more details.
* @constructor
*/
YAHOO.widget.Module = function(el, userConfig) {
	if (el) { 
		this.init(el, userConfig); 
	} else {
		YAHOO.log("No element or element ID specified for Module instantiation", "error");
	}
}

/**
* Constant representing the prefix path to use for non-secure images
* @type string
*/
YAHOO.widget.Module.IMG_ROOT = "http://us.i1.yimg.com/us.yimg.com/i/";

/**
* Constant representing the prefix path to use for securely served images
* @type string
*/
YAHOO.widget.Module.IMG_ROOT_SSL = "https://a248.e.akamai.net/sec.yimg.com/i/";

/**
* Constant for the default CSS class name that represents a Module
* @type string
* @final
*/
YAHOO.widget.Module.CSS_MODULE = "module";

/**
* Constant representing the module header
* @type string
* @final
*/
YAHOO.widget.Module.CSS_HEADER = "hd";

/**
* Constant representing the module body
* @type string
* @final
*/
YAHOO.widget.Module.CSS_BODY = "bd";

/**
* Constant representing the module footer
* @type string
* @final
*/
YAHOO.widget.Module.CSS_FOOTER = "ft";

/**
* Constant representing the url for the "src" attribute of the iframe used to monitor changes to the browser's base font size
* @type string
* @final
*/
YAHOO.widget.Module.RESIZE_MONITOR_SECURE_URL = null;

YAHOO.widget.Module.prototype = {

	/**
	* The class's constructor function
	* @type function
	*/
	constructor : YAHOO.widget.Module,

	/**
	* The main module element that contains the header, body, and footer
	* @type Element
	*/
	element : null, 

	/**
	* The header element, denoted with CSS class "hd"
	* @type Element
	*/
	header : null,

	/**
	* The body element, denoted with CSS class "bd"
	* @type Element
	*/
	body : null,

	/**
	* The footer element, denoted with CSS class "ft"
	* @type Element
	*/
	footer : null,

	/**
	* The id of the element
	* @type string
	*/
	id : null,

	/**
	* Array of elements
	* @type Element[]
	*/
	childNodesInDOM : null,

	/**
	* The string representing the image root
	* @type string
	*/
	imageRoot : YAHOO.widget.Module.IMG_ROOT,

	/**
	* CustomEvent fired prior to class initalization.
	* args: class reference of the initializing class, such as this.beforeInitEvent.fire(YAHOO.widget.Module)
	* @type YAHOO.util.CustomEvent
	*/
	beforeInitEvent : null,

	/**
	* CustomEvent fired after class initalization.
	* args: class reference of the initializing class, such as this.initEvent.fire(YAHOO.widget.Module)
	* @type YAHOO.util.CustomEvent
	*/
	initEvent : null,

	/**
	* CustomEvent fired when the Module is appended to the DOM
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	appendEvent : null,

	/**
	* CustomEvent fired before the Module is rendered
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	beforeRenderEvent : null,

	/**
	* CustomEvent fired after the Module is rendered
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	renderEvent : null,

	/**
	* CustomEvent fired when the header content of the Module is modified
	* args: string/element representing the new header content
	* @type YAHOO.util.CustomEvent
	*/
	changeHeaderEvent : null,

	/**
	* CustomEvent fired when the body content of the Module is modified
	* args: string/element representing the new body content
	* @type YAHOO.util.CustomEvent
	*/
	changeBodyEvent : null,

	/**
	* CustomEvent fired when the footer content of the Module is modified
	* args: string/element representing the new footer content
	* @type YAHOO.util.CustomEvent
	*/
	changeFooterEvent : null,

	/**
	* CustomEvent fired when the content of the Module is modified
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	changeContentEvent : null,

	/**
	* CustomEvent fired when the Module is destroyed
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	destroyEvent : null,

	/**
	* CustomEvent fired before the Module is shown
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	beforeShowEvent : null,

	/**
	* CustomEvent fired after the Module is shown
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	showEvent : null,

	/**
	* CustomEvent fired before the Module is hidden
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	beforeHideEvent : null,
	
	/**
	* CustomEvent fired after the Module is hidden
	* args: none
	* @type YAHOO.util.CustomEvent
	*/
	hideEvent : null,
		
	/**
	* Initializes the custom events for Module which are fired automatically at appropriate times by the Module class.
	*/
	initEvents : function() {

		this.beforeInitEvent		= new YAHOO.util.CustomEvent("beforeInit");
		this.initEvent				= new YAHOO.util.CustomEvent("init");

		this.appendEvent			= new YAHOO.util.CustomEvent("append");

		this.beforeRenderEvent		= new YAHOO.util.CustomEvent("beforeRender");
		this.renderEvent			= new YAHOO.util.CustomEvent("render");

		this.changeHeaderEvent		= new YAHOO.util.CustomEvent("changeHeader");
		this.changeBodyEvent		= new YAHOO.util.CustomEvent("changeBody");
		this.changeFooterEvent		= new YAHOO.util.CustomEvent("changeFooter");

		this.changeContentEvent		= new YAHOO.util.CustomEvent("changeContent");

		this.destroyEvent			= new YAHOO.util.CustomEvent("destroy");
		this.beforeShowEvent		= new YAHOO.util.CustomEvent("beforeShow");
		this.showEvent				= new YAHOO.util.CustomEvent("show");
		this.beforeHideEvent		= new YAHOO.util.CustomEvent("beforeHide");
		this.hideEvent				= new YAHOO.util.CustomEvent("hide");
	}, 

	/**
	* String representing the current user-agent platform
	* @type string
	*/
	platform : function() {
					var ua = navigator.userAgent.toLowerCase();
					if (ua.indexOf("windows") != -1 || ua.indexOf("win32") != -1) {
						return "windows";
					} else if (ua.indexOf("macintosh") != -1) {
						return "mac";
					} else {
						return false;
					}
				}(),

	/**
	* String representing the current user-agent browser
	* @type string
	*/
	browser : function() {
			var ua = navigator.userAgent.toLowerCase();
				  if (ua.indexOf('opera')!=-1) { // Opera (check first in case of spoof)
					 return 'opera';
				  } else if (ua.indexOf('msie 7')!=-1) { // IE7
					 return 'ie7';
				  } else if (ua.indexOf('msie') !=-1) { // IE
					 return 'ie';
				  } else if (ua.indexOf('safari')!=-1) { // Safari (check before Gecko because it includes "like Gecko")
					 return 'safari';
				  } else if (ua.indexOf('gecko') != -1) { // Gecko
					 return 'gecko';
				  } else {
					 return false;
				  }
			}(),

	/**
	* Boolean representing whether or not the current browsing context is secure (https)
	* @type boolean
	*/
	isSecure : function() {
		if (window.location.href.toLowerCase().indexOf("https") == 0) {
			return true;
		} else {
			return false;
		}
	}(),

	/**
	* Initializes the custom events for Module which are fired automatically at appropriate times by the Module class.
	*/
	initDefaultConfig : function() {
		// Add properties //

		this.cfg.addProperty("visible", { value:true, handler:this.configVisible, validator:this.cfg.checkBoolean } );
		this.cfg.addProperty("effect", { suppressEvent:true, supercedes:["visible"] } );
		this.cfg.addProperty("monitorresize", { value:true, handler:this.configMonitorResize } );
	},

	/**
	* The Module class's initialization method, which is executed for Module and all of its subclasses. This method is automatically called by the constructor, and  sets up all DOM references for pre-existing markup, and creates required markup if it is not already present.
	* @param {string}	el	The element ID representing the Module <em>OR</em>
	* @param {Element}	el	The element representing the Module
	* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this module. See configuration documentation for more details.
	*/
	init : function(el, userConfig) {

		this.initEvents();

		this.beforeInitEvent.fire(YAHOO.widget.Module);

		this.cfg = new YAHOO.util.Config(this);
		
		if (this.isSecure) {
			this.imageRoot = YAHOO.widget.Module.IMG_ROOT_SSL;
		}

		if (typeof el == "string") {
			var elId = el;

			el = document.getElementById(el);
			if (! el) {
				el = document.createElement("DIV");
				el.id = elId;
			}
		}

		this.element = el;
		
		if (el.id) {
			this.id = el.id;
		} 

		var childNodes = this.element.childNodes;

		if (childNodes) {
			for (var i=0;i<childNodes.length;i++) {
				var child = childNodes[i];
				switch (child.className) {
					case YAHOO.widget.Module.CSS_HEADER:
						this.header = child;
						break;
					case YAHOO.widget.Module.CSS_BODY:
						this.body = child;
						break;
					case YAHOO.widget.Module.CSS_FOOTER:
						this.footer = child;
						break;
				}
			}
		}

		this.initDefaultConfig();

		YAHOO.util.Dom.addClass(this.element, YAHOO.widget.Module.CSS_MODULE);

		if (userConfig) {
			this.cfg.applyConfig(userConfig, true);
		}

		// Subscribe to the fireQueue() method of Config so that any queued configuration changes are
		// excecuted upon render of the Module
		if (! YAHOO.util.Config.alreadySubscribed(this.renderEvent, this.cfg.fireQueue, this.cfg)) {
			this.renderEvent.subscribe(this.cfg.fireQueue, this.cfg, true);
		}

		this.initEvent.fire(YAHOO.widget.Module);
	},

	/**
	* Initialized an empty DOM element that is placed out of the visible area that can be used to detect text resize.
	*/
	initResizeMonitor : function() {

        if(this.browser != "opera") {

            var resizeMonitor = document.getElementById("_yuiResizeMonitor");
    
            if (! resizeMonitor) {
    
                resizeMonitor = document.createElement("iframe");
    
                var bIE = (this.browser.indexOf("ie") === 0);
    
                if(this.isSecure && this.RESIZE_MONITOR_SECURE_URL && bIE) {
    
                    resizeMonitor.src = this.RESIZE_MONITOR_SECURE_URL;
    
                }
                
                resizeMonitor.id = "_yuiResizeMonitor";
                resizeMonitor.style.visibility = "hidden";
                
                document.body.appendChild(resizeMonitor);
    
                resizeMonitor.style.width = "10em";
                resizeMonitor.style.height = "10em";
                resizeMonitor.style.position = "absolute";
                
                var nLeft = -1 * resizeMonitor.offsetWidth,
                    nTop = -1 * resizeMonitor.offsetHeight;
    
                resizeMonitor.style.top = nTop + "px";
                resizeMonitor.style.left =  nLeft + "px";
                resizeMonitor.style.borderStyle = "none";
                resizeMonitor.style.borderWidth = "0";
                YAHOO.util.Dom.setStyle(resizeMonitor, "opacity", "0");
                
                resizeMonitor.style.visibility = "visible";
    
                if(!bIE) {
    
                    var doc = resizeMonitor.contentWindow.document;
    
                    doc.open();
                    doc.close();
                
                }
    
            }
    
            if(resizeMonitor && resizeMonitor.contentWindow) {
    
                this.resizeMonitor = resizeMonitor;
    
                YAHOO.util.Event.addListener(this.resizeMonitor.contentWindow, "resize", this.onDomResize, this, true);
    
            }
        
        }

	},

	/**
	* Event handler fired when the resize monitor element is resized.
	*/
	onDomResize : function(e, obj) { 

        var nLeft = -1 * this.resizeMonitor.offsetWidth,
            nTop = -1 * this.resizeMonitor.offsetHeight;
        
        this.resizeMonitor.style.top = nTop + "px";
        this.resizeMonitor.style.left =  nLeft + "px";
	
	},

	/**
	* Sets the Module's header content to the HTML specified, or appends the passed element to the header. If no header is present, one will be automatically created.
	* @param {string}	headerContent	The HTML used to set the header <em>OR</em>
	* @param {Element}	headerContent	The Element to append to the header
	*/	
	setHeader : function(headerContent) {
		if (! this.header) {
			this.header = document.createElement("DIV");
			this.header.className = YAHOO.widget.Module.CSS_HEADER;
		}
		
		if (typeof headerContent == "string") {
			this.header.innerHTML = headerContent;
		} else {
			this.header.innerHTML = "";
			this.header.appendChild(headerContent);
		}

		this.changeHeaderEvent.fire(headerContent);
		this.changeContentEvent.fire();
	},

	/**
	* Appends the passed element to the header. If no header is present, one will be automatically created.
	* @param {Element}	element	The element to append to the header
	*/	
	appendToHeader : function(element) {
		if (! this.header) {
			this.header = document.createElement("DIV");
			this.header.className = YAHOO.widget.Module.CSS_HEADER;
		}
		
		this.header.appendChild(element);
		this.changeHeaderEvent.fire(element);
		this.changeContentEvent.fire();
	},

	/**
	* Sets the Module's body content to the HTML specified, or appends the passed element to the body. If no body is present, one will be automatically created.
	* @param {string}	bodyContent	The HTML used to set the body <em>OR</em>
	* @param {Element}	bodyContent	The Element to append to the body
	*/		
	setBody : function(bodyContent) {
		if (! this.body) {
			this.body = document.createElement("DIV");
			this.body.className = YAHOO.widget.Module.CSS_BODY;
		}

		if (typeof bodyContent == "string")
		{
			this.body.innerHTML = bodyContent;
		} else {
			this.body.innerHTML = "";
			this.body.appendChild(bodyContent);
		}

		this.changeBodyEvent.fire(bodyContent);
		this.changeContentEvent.fire();
	},

	/**
	* Appends the passed element to the body. If no body is present, one will be automatically created.
	* @param {Element}	element	The element to append to the body
	*/
	appendToBody : function(element) {
		if (! this.body) {
			this.body = document.createElement("DIV");
			this.body.className = YAHOO.widget.Module.CSS_BODY;
		}

		this.body.appendChild(element);
		this.changeBodyEvent.fire(element);
		this.changeContentEvent.fire();
	},

	/**
	* Sets the Module's footer content to the HTML specified, or appends the passed element to the footer. If no footer is present, one will be automatically created.
	* @param {string}	footerContent	The HTML used to set the footer <em>OR</em>
	* @param {Element}	footerContent	The Element to append to the footer
	*/	
	setFooter : function(footerContent) {
		if (! this.footer) {
			this.footer = document.createElement("DIV");
			this.footer.className = YAHOO.widget.Module.CSS_FOOTER;
		}

		if (typeof footerContent == "string") {
			this.footer.innerHTML = footerContent;
		} else {
			this.footer.innerHTML = "";
			this.footer.appendChild(footerContent);
		}

		this.changeFooterEvent.fire(footerContent);
		this.changeContentEvent.fire();
	},

	/**
	* Appends the passed element to the footer. If no footer is present, one will be automatically created.
	* @param {Element}	element	The element to append to the footer
	*/
	appendToFooter : function(element) {
		if (! this.footer) {
			this.footer = document.createElement("DIV");
			this.footer.className = YAHOO.widget.Module.CSS_FOOTER;
		}

		this.footer.appendChild(element);
		this.changeFooterEvent.fire(element);
		this.changeContentEvent.fire();
	},

	/**
	* Renders the Module by inserting the elements that are not already in the main Module into their correct places. Optionally appends the Module to the specified node prior to the render's execution. NOTE: For Modules without existing markup, the appendToNode argument is REQUIRED. If this argument is ommitted and the current element is not present in the document, the function will return false, indicating that the render was a failure.
	* @param {string}	appendToNode	The element id to which the Module should be appended to prior to rendering <em>OR</em>
	* @param {Element}	appendToNode	The element to which the Module should be appended to prior to rendering	
	* @param {Element}	moduleElement	OPTIONAL. The element that represents the actual Standard Module container. 
	* @return {boolean} Success or failure of the render
	*/
	render : function(appendToNode, moduleElement) {
		this.beforeRenderEvent.fire();

		if (! moduleElement) {
			moduleElement = this.element;
		}

		var me = this;
		var appendTo = function(element) {
			if (typeof element == "string") {
				element = document.getElementById(element);
			}
			
			if (element) {
				element.appendChild(me.element);
				me.appendEvent.fire();
			}
		}

		if (appendToNode) {
			appendTo(appendToNode);
		} else { // No node was passed in. If the element is not pre-marked up, this fails
			if (! YAHOO.util.Dom.inDocument(this.element)) {
				YAHOO.log("Render failed. Must specify appendTo node if Module isn't already in the DOM.", "error");
				return false;
			}
		}

		// Need to get everything into the DOM if it isn't already
		
		if (this.header && ! YAHOO.util.Dom.inDocument(this.header)) {
			// There is a header, but it's not in the DOM yet... need to add it
			var firstChild = moduleElement.firstChild;
			if (firstChild) { // Insert before first child if exists
				moduleElement.insertBefore(this.header, firstChild);
			} else { // Append to empty body because there are no children
				moduleElement.appendChild(this.header);
			}
		}

		if (this.body && ! YAHOO.util.Dom.inDocument(this.body)) {
			// There is a body, but it's not in the DOM yet... need to add it
			if (this.footer && YAHOO.util.Dom.isAncestor(this.moduleElement, this.footer)) { // Insert before footer if exists in DOM
				moduleElement.insertBefore(this.body, this.footer);
			} else { // Append to element because there is no footer
				moduleElement.appendChild(this.body);
			}
		}

		if (this.footer && ! YAHOO.util.Dom.inDocument(this.footer)) {
			// There is a footer, but it's not in the DOM yet... need to add it
			moduleElement.appendChild(this.footer);
		}

		this.renderEvent.fire();
		return true;
	},

	/**
	* Removes the Module element from the DOM and sets all child elements to null.
	*/
	destroy : function() {
		if (this.element) {
			var parent = this.element.parentNode;
		}
		if (parent) {
			parent.removeChild(this.element);
		}

		this.element = null;
		this.header = null;
		this.body = null;
		this.footer = null;

		this.destroyEvent.fire();
	},

	/**
	* Shows the Module element by setting the visible configuration property to true. Also fires two events: beforeShowEvent prior to the visibility change, and showEvent after.
	*/
	show : function() {
		this.cfg.setProperty("visible", true);
	},

	/**
	* Hides the Module element by setting the visible configuration property to false. Also fires two events: beforeHideEvent prior to the visibility change, and hideEvent after.
	*/
	hide : function() {
		this.cfg.setProperty("visible", false);
	},

	// BUILT-IN EVENT HANDLERS FOR MODULE //

	/**
	* Default event handler for changing the visibility property of a Module. By default, this is achieved by switching the "display" style between "block" and "none".
	* This method is responsible for firing showEvent and hideEvent.
	*/
	configVisible : function(type, args, obj) {
		var visible = args[0];
		if (visible) {
			this.beforeShowEvent.fire();
			YAHOO.util.Dom.setStyle(this.element, "display", "block");
			this.showEvent.fire();
		} else {
			this.beforeHideEvent.fire();
			YAHOO.util.Dom.setStyle(this.element, "display", "none");
			this.hideEvent.fire();
		}
	},

	/**
	* Default event handler for the "monitorresize" configuration property
	*/
	configMonitorResize : function(type, args, obj) {
		var monitor = args[0];
		if (monitor) {
			this.initResizeMonitor();
		} else {
			YAHOO.util.Event.removeListener(this.resizeMonitor, "resize", this.onDomResize);
			this.resizeMonitor = null;
		}
	}
}

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.Module.prototype.toString = function() {
	return "Module " + this.id;
}

/**
* @class Overlay is a Module that is absolutely positioned above the page flow. It has convenience methods for positioning and sizing, as well as options for controlling zIndex and constraining the Overlay's position to the current visible viewport. Overlay also contains a dynamicly generated IFRAME which is placed beneath it for Internet Explorer 6 and 5.x so that it will be properly rendered above SELECT elements.
* @param {string}	el	The element ID representing the Overlay <em>OR</em>
* @param {Element}	el	The element representing the Overlay
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Overlay. See configuration documentation for more details.
* @constructor
*/
YAHOO.widget.Overlay = function(el, userConfig) {
	YAHOO.widget.Overlay.superclass.constructor.call(this, el, userConfig);
}

YAHOO.extend(YAHOO.widget.Overlay, YAHOO.widget.Module);

/**
* The URL of the blank image that will be placed in the iframe
* @type string
* @final
*/
YAHOO.widget.Overlay.IFRAME_SRC = "promo/m/irs/blank.gif";

/**
* Constant representing the top left corner of an element, used for configuring the context element alignment
* @type string
* @final
*/
YAHOO.widget.Overlay.TOP_LEFT = "tl";

/**
* Constant representing the top right corner of an element, used for configuring the context element alignment
* @type string
* @final
*/
YAHOO.widget.Overlay.TOP_RIGHT = "tr";

/**
* Constant representing the top bottom left corner of an element, used for configuring the context element alignment
* @type string
* @final
*/
YAHOO.widget.Overlay.BOTTOM_LEFT = "bl";

/**
* Constant representing the bottom right corner of an element, used for configuring the context element alignment
* @type string
* @final
*/
YAHOO.widget.Overlay.BOTTOM_RIGHT = "br";

/**
* Constant representing the default CSS class used for an Overlay
* @type string
* @final
*/
YAHOO.widget.Overlay.CSS_OVERLAY = "overlay";

/**
* CustomEvent fired before the Overlay is moved.
* args: x,y that the Overlay will be moved to
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Overlay.prototype.beforeMoveEvent = null;

/**
* CustomEvent fired after the Overlay is moved.
* args: x,y that the Overlay was moved to
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Overlay.prototype.moveEvent = null;

/**
* The Overlay initialization method, which is executed for Overlay and all of its subclasses. This method is automatically called by the constructor, and  sets up all DOM references for pre-existing markup, and creates required markup if it is not already present.
* @param {string}	el	The element ID representing the Overlay <em>OR</em>
* @param {Element}	el	The element representing the Overlay
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Overlay. See configuration documentation for more details.
*/
YAHOO.widget.Overlay.prototype.init = function(el, userConfig) {
	YAHOO.widget.Overlay.superclass.init.call(this, el/*, userConfig*/);  // Note that we don't pass the user config in here yet because we only want it executed once, at the lowest subclass level
	
	this.beforeInitEvent.fire(YAHOO.widget.Overlay);

	YAHOO.util.Dom.addClass(this.element, YAHOO.widget.Overlay.CSS_OVERLAY);

	if (userConfig) {
		this.cfg.applyConfig(userConfig, true);
	}

	if (this.platform == "mac" && this.browser == "gecko") {
		if (! YAHOO.util.Config.alreadySubscribed(this.showEvent,this.showMacGeckoScrollbars,this)) {
			this.showEvent.subscribe(this.showMacGeckoScrollbars,this,true);
		}
		if (! YAHOO.util.Config.alreadySubscribed(this.hideEvent,this.hideMacGeckoScrollbars,this)) {
			this.hideEvent.subscribe(this.hideMacGeckoScrollbars,this,true);
		}
	}

	this.initEvent.fire(YAHOO.widget.Overlay);

}

/**
* Initializes the custom events for Overlay which are fired automatically at appropriate times by the Overlay class.
*/
YAHOO.widget.Overlay.prototype.initEvents = function() {
	YAHOO.widget.Overlay.superclass.initEvents.call(this);

	this.beforeMoveEvent = new YAHOO.util.CustomEvent("beforeMove", this);
	this.moveEvent = new YAHOO.util.CustomEvent("move", this);
}

/**
* Initializes the class's configurable properties which can be changed using the Overlay's Config object (cfg).
*/
YAHOO.widget.Overlay.prototype.initDefaultConfig = function() {
	YAHOO.widget.Overlay.superclass.initDefaultConfig.call(this);

	// Add overlay config properties //
	this.cfg.addProperty("x", { handler:this.configX, validator:this.cfg.checkNumber, suppressEvent:true, supercedes:["iframe"] } );
	this.cfg.addProperty("y", { handler:this.configY, validator:this.cfg.checkNumber, suppressEvent:true, supercedes:["iframe"] } );
	this.cfg.addProperty("xy",{ handler:this.configXY, suppressEvent:true, supercedes:["iframe"] } );

	this.cfg.addProperty("context",	{ handler:this.configContext, suppressEvent:true, supercedes:["iframe"] } );
	this.cfg.addProperty("fixedcenter", { value:false, handler:this.configFixedCenter, validator:this.cfg.checkBoolean, supercedes:["iframe","visible"] } );

	this.cfg.addProperty("width", { handler:this.configWidth, suppressEvent:true, supercedes:["iframe"] } );
	this.cfg.addProperty("height", { handler:this.configHeight, suppressEvent:true, supercedes:["iframe"] } );

	this.cfg.addProperty("zIndex", { value:null, handler:this.configzIndex } );

	this.cfg.addProperty("constraintoviewport", { value:false, handler:this.configConstrainToViewport, validator:this.cfg.checkBoolean, supercedes:["iframe","x","y","xy"] } );
	this.cfg.addProperty("iframe", { value:(this.browser == "ie" ? true : false), handler:this.configIframe, validator:this.cfg.checkBoolean, supercedes:["zIndex"] } );
}

/**
* Moves the Overlay to the specified position. This function is identical to calling this.cfg.setProperty("xy", [x,y]);
* @param {int}	x	The Overlay's new x position
* @param {int}	y	The Overlay's new y position
*/
YAHOO.widget.Overlay.prototype.moveTo = function(x, y) {
	this.cfg.setProperty("xy",[x,y]);
}

/**
* Adds a special CSS class to the Overlay when Mac/Gecko is in use, to work around a Gecko bug where
* scrollbars cannot be hidden. See https://bugzilla.mozilla.org/show_bug.cgi?id=187435
*/
YAHOO.widget.Overlay.prototype.hideMacGeckoScrollbars = function() {
	YAHOO.util.Dom.removeClass(this.element, "show-scrollbars");
	YAHOO.util.Dom.addClass(this.element, "hide-scrollbars");
}

/**
* Removes a special CSS class from the Overlay when Mac/Gecko is in use, to work around a Gecko bug where
* scrollbars cannot be hidden. See https://bugzilla.mozilla.org/show_bug.cgi?id=187435
*/
YAHOO.widget.Overlay.prototype.showMacGeckoScrollbars = function() {
	YAHOO.util.Dom.removeClass(this.element, "hide-scrollbars");
	YAHOO.util.Dom.addClass(this.element, "show-scrollbars");
}

// BEGIN BUILT-IN PROPERTY EVENT HANDLERS //

/**
* The default event handler fired when the "visible" property is changed. This method is responsible for firing showEvent and hideEvent.
*/
YAHOO.widget.Overlay.prototype.configVisible = function(type, args, obj) {
	var visible = args[0];
	var currentVis = YAHOO.util.Dom.getStyle(this.element, "visibility");

	var effect = this.cfg.getProperty("effect");

	var effectInstances = new Array();
	if (effect) {
		if (effect instanceof Array) {
			for (var i=0;i<effect.length;i++) {
				var eff = effect[i];
				effectInstances[effectInstances.length] = eff.effect(this, eff.duration);
			}
		} else {
			effectInstances[effectInstances.length] = effect.effect(this, effect.duration);
		}
	}

	var isMacGecko = (this.platform == "mac" && this.browser == "gecko");

	if (visible) { // Show
		if (isMacGecko) {
			this.showMacGeckoScrollbars();
		}	

		if (effect) { // Animate in
			if (visible) { // Animate in if not showing
				if (currentVis != "visible") {
					this.beforeShowEvent.fire();
					for (var i=0;i<effectInstances.length;i++) {
						var e = effectInstances[i];
						if (i == 0 && ! YAHOO.util.Config.alreadySubscribed(e.animateInCompleteEvent,this.showEvent.fire,this.showEvent)) {
							e.animateInCompleteEvent.subscribe(this.showEvent.fire,this.showEvent,true); // Delegate showEvent until end of animateInComplete
						}
						e.animateIn();
					}
				}
			}
		} else { // Show
			if (currentVis != "visible") {
				this.beforeShowEvent.fire();
				YAHOO.util.Dom.setStyle(this.element, "visibility", "visible");
				this.cfg.refireEvent("iframe");
				this.showEvent.fire();
			}
		}

	} else { // Hide
		if (isMacGecko) {
			this.hideMacGeckoScrollbars();
		}	

		if (effect) { // Animate out if showing
			if (currentVis == "visible") {
				this.beforeHideEvent.fire();
				for (var i=0;i<effectInstances.length;i++) {
					var e = effectInstances[i];
					if (i == 0 && ! YAHOO.util.Config.alreadySubscribed(e.animateOutCompleteEvent,this.hideEvent.fire,this.hideEvent)) {				
						e.animateOutCompleteEvent.subscribe(this.hideEvent.fire,this.hideEvent,true); // Delegate hideEvent until end of animateOutComplete
					}
					e.animateOut();
				}
			}
		} else { // Simple hide
			if (currentVis == "visible") {
				this.beforeHideEvent.fire();
				YAHOO.util.Dom.setStyle(this.element, "visibility", "hidden");
				this.cfg.refireEvent("iframe");
				this.hideEvent.fire();
			}
		}	
	}
}

/**
* Center event handler used for centering on scroll/resize, but only if the Overlay is visible
*/
YAHOO.widget.Overlay.prototype.doCenterOnDOMEvent = function() {
	if (this.cfg.getProperty("visible")) {
		this.center();
	}
}

/**
* The default event handler fired when the "fixedcenter" property is changed.
*/
YAHOO.widget.Overlay.prototype.configFixedCenter = function(type, args, obj) {
	var val = args[0];

	if (val) {
		this.center();
			
		if (! YAHOO.util.Config.alreadySubscribed(this.beforeShowEvent, this.center, this)) {
			this.beforeShowEvent.subscribe(this.center, this, true);
		}
		
		if (! YAHOO.util.Config.alreadySubscribed(YAHOO.widget.Overlay.windowResizeEvent, this.doCenterOnDOMEvent, this)) {
			YAHOO.widget.Overlay.windowResizeEvent.subscribe(this.doCenterOnDOMEvent, this, true);
		}

		if (! YAHOO.util.Config.alreadySubscribed(YAHOO.widget.Overlay.windowScrollEvent, this.doCenterOnDOMEvent, this)) {
			YAHOO.widget.Overlay.windowScrollEvent.subscribe( this.doCenterOnDOMEvent, this, true);
		}
	} else {
		YAHOO.widget.Overlay.windowResizeEvent.unsubscribe(this.doCenterOnDOMEvent, this);
		YAHOO.widget.Overlay.windowScrollEvent.unsubscribe(this.doCenterOnDOMEvent, this);
	}
}

/**
* The default event handler fired when the "height" property is changed.
*/
YAHOO.widget.Overlay.prototype.configHeight = function(type, args, obj) {
	var height = args[0];
	var el = this.element;
	YAHOO.util.Dom.setStyle(el, "height", height);
	this.cfg.refireEvent("iframe");
}

/**
* The default event handler fired when the "width" property is changed.
*/
YAHOO.widget.Overlay.prototype.configWidth = function(type, args, obj) {
	var width = args[0];
	var el = this.element;
	YAHOO.util.Dom.setStyle(el, "width", width);
	this.cfg.refireEvent("iframe");
}

/**
* The default event handler fired when the "zIndex" property is changed.
*/
YAHOO.widget.Overlay.prototype.configzIndex = function(type, args, obj) {
	var zIndex = args[0];

	var el = this.element;

	if (! zIndex) {
		zIndex = YAHOO.util.Dom.getStyle(el, "zIndex");
		if (! zIndex || isNaN(zIndex)) {
			zIndex = 0;
		}
	}

	if (this.iframe) {
		if (zIndex <= 0) {
			zIndex = 1;
		}
		YAHOO.util.Dom.setStyle(this.iframe, "zIndex", (zIndex-1));
	}

	YAHOO.util.Dom.setStyle(el, "zIndex", zIndex);
	this.cfg.setProperty("zIndex", zIndex, true);
}

/**
* The default event handler fired when the "xy" property is changed.
*/
YAHOO.widget.Overlay.prototype.configXY = function(type, args, obj) {
	var pos = args[0];
	var x = pos[0];
	var y = pos[1];

	this.cfg.setProperty("x", x);
	this.cfg.setProperty("y", y);

	this.beforeMoveEvent.fire([x,y]);

	x = this.cfg.getProperty("x");
	y = this.cfg.getProperty("y");

	YAHOO.log("xy: " + [x,y], "iframe");

	this.cfg.refireEvent("iframe");
	this.moveEvent.fire([x,y]);
}

/**
* The default event handler fired when the "x" property is changed.
*/
YAHOO.widget.Overlay.prototype.configX = function(type, args, obj) {
	var x = args[0];
	var y = this.cfg.getProperty("y");

	this.cfg.setProperty("x", x, true);
	this.cfg.setProperty("y", y, true);

	this.beforeMoveEvent.fire([x,y]);

	x = this.cfg.getProperty("x");
	y = this.cfg.getProperty("y");

	YAHOO.util.Dom.setX(this.element, x, true);
	
	this.cfg.setProperty("xy", [x, y], true);

	this.cfg.refireEvent("iframe");
	this.moveEvent.fire([x, y]);
}

/**
* The default event handler fired when the "y" property is changed.
*/
YAHOO.widget.Overlay.prototype.configY = function(type, args, obj) {
	var x = this.cfg.getProperty("x");
	var y = args[0];

	this.cfg.setProperty("x", x, true);
	this.cfg.setProperty("y", y, true);

	this.beforeMoveEvent.fire([x,y]);

	x = this.cfg.getProperty("x");
	y = this.cfg.getProperty("y");

	YAHOO.util.Dom.setY(this.element, y, true);

	this.cfg.setProperty("xy", [x, y], true);

	this.cfg.refireEvent("iframe");
	this.moveEvent.fire([x, y]);
}

/**
* The default event handler fired when the "iframe" property is changed.
*/
YAHOO.widget.Overlay.prototype.configIframe = function(type, args, obj) {

	var val = args[0];

	var el = this.element;
	
	var showIframe = function() {
		if (this.iframe) {
			this.iframe.style.display = "block";
		}
	}

	var hideIframe = function() {
		if (this.iframe) {
			this.iframe.style.display = "none";
		}
	}

	if (val) { // IFRAME shim is enabled

		if (! YAHOO.util.Config.alreadySubscribed(this.showEvent, showIframe, this)) {
			this.showEvent.subscribe(showIframe, this, true);
		}
		if (! YAHOO.util.Config.alreadySubscribed(this.hideEvent, hideIframe, this)) {
			this.hideEvent.subscribe(hideIframe, this, true);
		}

		var x = this.cfg.getProperty("x");
		var y = this.cfg.getProperty("y");

		if (! x || ! y) {
			YAHOO.log("syncPosition needed for iframe", "iframe");
			this.syncPosition();
			x = this.cfg.getProperty("x");
			y = this.cfg.getProperty("y");
		}

		YAHOO.log("iframe positioning to: " + [x,y], "iframe");

		if (! isNaN(x) && ! isNaN(y)) {
			if (! this.iframe) {
				this.iframe = document.createElement("iframe");
				if (this.isSecure) {
					this.iframe.src = this.imageRoot + YAHOO.widget.Overlay.IFRAME_SRC;
				}
				
				var parent = el.parentNode;
				if (parent) {
					parent.appendChild(this.iframe);
				} else {
					document.body.appendChild(this.iframe);
				}

				YAHOO.util.Dom.setStyle(this.iframe, "position", "absolute");
				YAHOO.util.Dom.setStyle(this.iframe, "border", "none");
				YAHOO.util.Dom.setStyle(this.iframe, "margin", "0");
				YAHOO.util.Dom.setStyle(this.iframe, "padding", "0");
				YAHOO.util.Dom.setStyle(this.iframe, "opacity", "0");
				if (this.cfg.getProperty("visible")) {
					showIframe.call(this);
				} else {
					hideIframe.call(this);
				}
			}
			
			var iframeDisplay = YAHOO.util.Dom.getStyle(this.iframe, "display");

			if (iframeDisplay == "none") {
				this.iframe.style.display = "block";
			}

			YAHOO.util.Dom.setXY(this.iframe, [x,y]);

			var width = el.clientWidth;
			var height = el.clientHeight;

			YAHOO.util.Dom.setStyle(this.iframe, "width", (width+2) + "px");
			YAHOO.util.Dom.setStyle(this.iframe, "height", (height+2) + "px");

			if (iframeDisplay == "none") {
				this.iframe.style.display = "none";
			}
		}
	} else {
		if (this.iframe) {
			this.iframe.style.display = "none";
		}
		this.showEvent.unsubscribe(showIframe, this);
		this.hideEvent.unsubscribe(hideIframe, this);
	}
}


/**
* The default event handler fired when the "constraintoviewport" property is changed.
*/
YAHOO.widget.Overlay.prototype.configConstrainToViewport = function(type, args, obj) {
	var val = args[0];
	if (val) {
		if (! YAHOO.util.Config.alreadySubscribed(this.beforeMoveEvent, this.enforceConstraints, this)) {
			this.beforeMoveEvent.subscribe(this.enforceConstraints, this, true);
		}
	} else {
		this.beforeMoveEvent.unsubscribe(this.enforceConstraints, this);
	}
}

/**
* The default event handler fired when the "context" property is changed.
*/
YAHOO.widget.Overlay.prototype.configContext = function(type, args, obj) {
	var contextArgs = args[0];

	if (contextArgs) {
		var contextEl = contextArgs[0];
		var elementMagnetCorner = contextArgs[1];
		var contextMagnetCorner = contextArgs[2];

		if (contextEl) {
			if (typeof contextEl == "string") {
				this.cfg.setProperty("context", [document.getElementById(contextEl),elementMagnetCorner,contextMagnetCorner], true);
			}
			
			if (elementMagnetCorner && contextMagnetCorner) {
				this.align(elementMagnetCorner, contextMagnetCorner);
			}
		}	
	}
}


// END BUILT-IN PROPERTY EVENT HANDLERS //

/**
* Aligns the Overlay to its context element using the specified corner points (represented by the constants TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, and BOTTOM_RIGHT.
* @param {string} elementAlign		The string representing the corner of the Overlay that should be aligned to the context element
* @param {string} contextAlign		The corner of the context element that the elementAlign corner should stick to.
*/
YAHOO.widget.Overlay.prototype.align = function(elementAlign, contextAlign) {
	var contextArgs = this.cfg.getProperty("context");
	if (contextArgs) {
		var context = contextArgs[0];
		
		var element = this.element;
		var me = this;

		if (! elementAlign) {
			elementAlign = contextArgs[1];
		}

		if (! contextAlign) {
			contextAlign = contextArgs[2];
		}

		if (element && context) {
			var elementRegion = YAHOO.util.Dom.getRegion(element);
			var contextRegion = YAHOO.util.Dom.getRegion(context);

			var doAlign = function(v,h) {
				switch (elementAlign) {
					case YAHOO.widget.Overlay.TOP_LEFT:
						me.moveTo(h,v);
						break;
					case YAHOO.widget.Overlay.TOP_RIGHT:
						me.moveTo(h-element.offsetWidth,v);
						break;
					case YAHOO.widget.Overlay.BOTTOM_LEFT:
						me.moveTo(h,v-element.offsetHeight);
						break;
					case YAHOO.widget.Overlay.BOTTOM_RIGHT:
						me.moveTo(h-element.offsetWidth,v-element.offsetHeight);
						break;
				}
			}

			switch (contextAlign) {
				case YAHOO.widget.Overlay.TOP_LEFT:
					doAlign(contextRegion.top, contextRegion.left);
					break;
				case YAHOO.widget.Overlay.TOP_RIGHT:
					doAlign(contextRegion.top, contextRegion.right);
					break;		
				case YAHOO.widget.Overlay.BOTTOM_LEFT:
					doAlign(contextRegion.bottom, contextRegion.left);
					break;
				case YAHOO.widget.Overlay.BOTTOM_RIGHT:
					doAlign(contextRegion.bottom, contextRegion.right);
					break;
			}
		}
	}
}

/**
* The default event handler executed when the moveEvent is fired, if the "constraintoviewport" is set to true.
*/
YAHOO.widget.Overlay.prototype.enforceConstraints = function(type, args, obj) {
	var pos = args[0];

	var x = pos[0];
	var y = pos[1];

	var width = parseInt(this.cfg.getProperty("width"));

	if (isNaN(width)) {
		width = 0;
	}

	var offsetHeight = this.element.offsetHeight;
	var offsetWidth = (width>0?width:this.element.offsetWidth); //this.element.offsetWidth;

	var viewPortWidth = YAHOO.util.Dom.getViewportWidth();
	var viewPortHeight = YAHOO.util.Dom.getViewportHeight();

	var scrollX = window.scrollX || document.documentElement.scrollLeft;
	var scrollY = window.scrollY || document.documentElement.scrollTop;

	var topConstraint = scrollY + 10;
	var leftConstraint = scrollX + 10;
	var bottomConstraint = scrollY + viewPortHeight - offsetHeight - 10;
	var rightConstraint = scrollX + viewPortWidth - offsetWidth - 10;
	
	if (x < leftConstraint) {
		x = leftConstraint;
	} else if (x > rightConstraint) {
		x = rightConstraint;
	}

	if (y < topConstraint) {
		y = topConstraint;
	} else if (y > bottomConstraint) {
		y = bottomConstraint;
	}

	this.cfg.setProperty("x", x, true);
	this.cfg.setProperty("y", y, true);
	this.cfg.setProperty("xy", [x,y], true);
}

/**
* Centers the container in the viewport.
*/
YAHOO.widget.Overlay.prototype.center = function() {
	var scrollX = document.documentElement.scrollLeft || document.body.scrollLeft;
	var scrollY = document.documentElement.scrollTop || document.body.scrollTop;

	var viewPortWidth = YAHOO.util.Dom.getClientWidth();
	var viewPortHeight = YAHOO.util.Dom.getClientHeight();

	var elementWidth = this.element.offsetWidth;
	var elementHeight = this.element.offsetHeight;

	var x = (viewPortWidth / 2) - (elementWidth / 2) + scrollX;
	var y = (viewPortHeight / 2) - (elementHeight / 2) + scrollY;
	
	this.element.style.left = parseInt(x) + "px";
	this.element.style.top = parseInt(y) + "px";
	this.syncPosition();

	this.cfg.refireEvent("iframe");
}

/**
* Synchronizes the Panel's "xy", "x", and "y" properties with the Panel's position in the DOM. This is primarily used to update position information during drag & drop.
*/
YAHOO.widget.Overlay.prototype.syncPosition = function() {
	var pos = YAHOO.util.Dom.getXY(this.element);
	this.cfg.setProperty("x", pos[0], true);
	this.cfg.setProperty("y", pos[1], true);
	this.cfg.setProperty("xy", pos, true);
}

/**
* Event handler fired when the resize monitor element is resized.
*/
YAHOO.widget.Overlay.prototype.onDomResize = function(e, obj) {
	YAHOO.widget.Overlay.superclass.onDomResize.call(this, e, obj);
	this.cfg.refireEvent("iframe");
}

/**
* Removes the Overlay element from the DOM and sets all child elements to null.
*/
YAHOO.widget.Overlay.prototype.destroy = function() {
	if (this.iframe) {
		this.iframe.parentNode.removeChild(this.iframe);
	}
	
	this.iframe = null;

	YAHOO.widget.Overlay.superclass.destroy.call(this);  
};

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.Overlay.prototype.toString = function() {
	return "Overlay " + this.id;
}

/**
* A singleton CustomEvent used for reacting to the DOM event for window scroll
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Overlay.windowScrollEvent = new YAHOO.util.CustomEvent("windowScroll");

/**
* A singleton CustomEvent used for reacting to the DOM event for window resize
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Overlay.windowResizeEvent = new YAHOO.util.CustomEvent("windowResize");

/**
* The DOM event handler used to fire the CustomEvent for window scroll
* @type Function
*/
YAHOO.widget.Overlay.windowScrollHandler = function(e) {
	YAHOO.widget.Overlay.windowScrollEvent.fire();
}

/**
* The DOM event handler used to fire the CustomEvent for window resize
* @type Function
*/
YAHOO.widget.Overlay.windowResizeHandler = function(e) {
	YAHOO.widget.Overlay.windowResizeEvent.fire();
}

/**
* @private
*/
YAHOO.widget.Overlay._initialized == null;

if (YAHOO.widget.Overlay._initialized == null) {
	YAHOO.util.Event.addListener(window, "scroll", YAHOO.widget.Overlay.windowScrollHandler);
	YAHOO.util.Event.addListener(window, "resize", YAHOO.widget.Overlay.windowResizeHandler);

	YAHOO.widget.Overlay._initialized = true;
}

/**
* @class
* OverlayManager is used for maintaining the focus status of multiple Overlays.
* @param {Array}	overlays	Optional. A collection of Overlays to register with the manager.
* @param {object}	userConfig		The object literal representing the user configuration of the OverlayManager
* @constructor
*/
YAHOO.widget.OverlayManager = function(userConfig) {
	this.init(userConfig);
}

/**
* The CSS class representing a focused Overlay
* @type string
*/
YAHOO.widget.OverlayManager.CSS_FOCUSED = "focused";

YAHOO.widget.OverlayManager.prototype = {

	constructor : YAHOO.widget.OverlayManager,

	/**
	* The array of Overlays that are currently registered
	* @type Array
	*/
	overlays : null,

	/**
	* Initializes the default configuration of the OverlayManager
	*/	
	initDefaultConfig : function() {
		this.cfg.addProperty("overlays", { suppressEvent:true } );
		this.cfg.addProperty("focusevent", { value:"mousedown" } );
	}, 

	/**
	* Returns the currently focused Overlay
	* @return {Overlay}	The currently focused Overlay
	*/
	getActive : function() {},

	/**
	* Focuses the specified Overlay
	* @param {Overlay}	The Overlay to focus
	* @param {string}	The id of the Overlay to focus
	*/
	focus : function(overlay) {},

	/**
	* Removes the specified Overlay from the manager
	* @param {Overlay}	The Overlay to remove
	* @param {string}	The id of the Overlay to remove
	*/
	remove: function(overlay) {},

	/**
	* Removes focus from all registered Overlays in the manager
	*/
	blurAll : function() {},

	/**
	* Initializes the OverlayManager
	* @param {Array}	overlays	Optional. A collection of Overlays to register with the manager.
	* @param {object}	userConfig		The object literal representing the user configuration of the OverlayManager
	*/
	init : function(userConfig) {
		this.cfg = new YAHOO.util.Config(this);

		this.initDefaultConfig();

		if (userConfig) {
			this.cfg.applyConfig(userConfig, true);
		}
		this.cfg.fireQueue();

		var activeOverlay = null;

		this.getActive = function() {
			return activeOverlay;
		}

		this.focus = function(overlay) {
			var o = this.find(overlay);
			if (o) {
				this.blurAll();
				activeOverlay = o;
				YAHOO.util.Dom.addClass(activeOverlay.element, YAHOO.widget.OverlayManager.CSS_FOCUSED);
				this.overlays.sort(this.compareZIndexDesc);
				var topZIndex = YAHOO.util.Dom.getStyle(this.overlays[0].element, "zIndex");
				if (! isNaN(topZIndex) && this.overlays[0] != overlay) {
					activeOverlay.cfg.setProperty("zIndex", (parseInt(topZIndex) + 1));
				}
				this.overlays.sort(this.compareZIndexDesc);
			}
		}

		this.remove = function(overlay) {
			var o = this.find(overlay);
			if (o) {
				var originalZ = YAHOO.util.Dom.getStyle(o.element, "zIndex");
				o.cfg.setProperty("zIndex", -1000, true);
				this.overlays.sort(this.compareZIndexDesc);
				this.overlays = this.overlays.slice(0, this.overlays.length-1);
				o.cfg.setProperty("zIndex", originalZ, true);

				o.cfg.setProperty("manager", null);
				o.focusEvent = null
				o.blurEvent = null;
				o.focus = null;
				o.blur = null;
			}
		}

		this.blurAll = function() {
			activeOverlay = null;
			for (var o=0;o<this.overlays.length;o++) {
				YAHOO.util.Dom.removeClass(this.overlays[o].element, YAHOO.widget.OverlayManager.CSS_FOCUSED);
			}		
		}

		var overlays = this.cfg.getProperty("overlays");
		
		if (! this.overlays) {
			this.overlays = new Array();
		}

		if (overlays) {
			this.register(overlays);
			this.overlays.sort(this.compareZIndexDesc);
		}
	},

	/**
	* Registers an Overlay or an array of Overlays with the manager. Upon registration, the Overlay receives functions for focus and blur, along with CustomEvents for each.
	* @param {Overlay}	overlay		An Overlay to register with the manager.
	* @param {Overlay[]}	overlay		An array of Overlays to register with the manager.
	* @return	{boolean}	True if any Overlays are registered.
	*/
	register : function(overlay) {
		if (overlay instanceof YAHOO.widget.Overlay) {
			overlay.cfg.addProperty("manager", { value:this } );

			overlay.focusEvent = new YAHOO.util.CustomEvent("focus");
			overlay.blurEvent = new YAHOO.util.CustomEvent("blur");
			
			var mgr=this;

			overlay.focus = function() {
				mgr.focus(this);
				this.focusEvent.fire();
			} 

			overlay.blur = function() {
				mgr.blurAll();
				this.blurEvent.fire();
			}

			var focusOnDomEvent = function(e,obj) {
				overlay.focus();
			}
			
			var focusevent = this.cfg.getProperty("focusevent");
			YAHOO.util.Event.addListener(overlay.element,focusevent,focusOnDomEvent,this,true);

			var zIndex = YAHOO.util.Dom.getStyle(overlay.element, "zIndex");
			if (! isNaN(zIndex)) {
				overlay.cfg.setProperty("zIndex", parseInt(zIndex));
			} else {
				overlay.cfg.setProperty("zIndex", 0);
			}
			
			this.overlays.push(overlay);
			return true;
		} else if (overlay instanceof Array) {
			var regcount = 0;
			for (var i=0;i<overlay.length;i++) {
				if (this.register(overlay[i])) {
					regcount++;
				}
			}
			if (regcount > 0) {
				return true;
			}
		} else {
			return false;
		}
	},

	/**
	* Attempts to locate an Overlay by instance or ID.
	* @param {Overlay}	overlay		An Overlay to locate within the manager
	* @param {string}	overlay		An Overlay id to locate within the manager
	* @return	{Overlay}	The requested Overlay, if found, or null if it cannot be located.
	*/
	find : function(overlay) {
		if (overlay instanceof YAHOO.widget.Overlay) {
			for (var o=0;o<this.overlays.length;o++) {
				if (this.overlays[o] == overlay) {
					return this.overlays[o];
				}
			}
		} else if (typeof overlay == "string") {
			for (var o=0;o<this.overlays.length;o++) {
				if (this.overlays[o].id == overlay) {
					return this.overlays[o];
				}
			}			
		}
		return null;
	},

	/**
	* Used for sorting the manager's Overlays by z-index.
	* @private
	*/
	compareZIndexDesc : function(o1, o2) {
		var zIndex1 = o1.cfg.getProperty("zIndex");
		var zIndex2 = o2.cfg.getProperty("zIndex");

		if (zIndex1 > zIndex2) {
			return -1;
		} else if (zIndex1 < zIndex2) {
			return 1;
		} else {
			return 0;
		}
	},

	/**
	* Shows all Overlays in the manager.
	*/
	showAll : function() {
		for (var o=0;o<this.overlays.length;o++) {
			this.overlays[o].show();
		}
	},

	/**
	* Hides all Overlays in the manager.
	*/
	hideAll : function() {
		for (var o=0;o<this.overlays.length;o++) {
			this.overlays[o].hide();
		}
	},

	/**
	* Returns a string representation of the object.
	* @type string
	*/ 
	toString : function() {
		return "OverlayManager";
	}

}

/**
* KeyListener is a utility that provides an easy interface for listening for keydown/keyup events fired against DOM elements.
* @param {Element}	attachTo	The element or element ID to which the key event should be attached
* @param {string}	attachTo	The element or element ID to which the key event should be attached
* @param {object}	keyData		The object literal representing the key(s) to detect. Possible attributes are shift(boolean), alt(boolean), ctrl(boolean) and keys(either an int or an array of ints representing keycodes).
* @param {function}	handler		The CustomEvent handler to fire when the key event is detected
* @param {object}	handler		An object literal representing the handler. 
* @param {string}	event		Optional. The event (keydown or keyup) to listen for. Defaults automatically to keydown.
* @constructor
*/
YAHOO.util.KeyListener = function(attachTo, keyData, handler, event) {
	if (! attachTo) {
		YAHOO.log("No attachTo element specified", "error");
	}
	if (! keyData) {
		YAHOO.log("No keyData specified", "error");
	}
	if (! handler) {
		YAHOO.log("No handler specified", "error");
	}

	if (! event) {
		event = YAHOO.util.KeyListener.KEYDOWN;
	}

	var keyEvent = new YAHOO.util.CustomEvent("keyPressed");
	
	this.enabledEvent = new YAHOO.util.CustomEvent("enabled");
	this.disabledEvent = new YAHOO.util.CustomEvent("disabled");

	if (typeof attachTo == 'string') {
		attachTo = document.getElementById(attachTo);
	}

	if (typeof handler == 'function') {
		keyEvent.subscribe(handler);
	} else {
		keyEvent.subscribe(handler.fn, handler.scope, handler.correctScope);
	}

	/**
	* Handles the key event when a key is pressed.
	* @private
	*/
	function handleKeyPress(e, obj) {
		var keyPressed = e.charCode || e.keyCode;
		
		if (! keyData.shift)	keyData.shift = false;
		if (! keyData.alt)		keyData.alt = false;
		if (! keyData.ctrl)		keyData.ctrl = false;

		// check held down modifying keys first
		if (e.shiftKey == keyData.shift && 
			e.altKey   == keyData.alt &&
			e.ctrlKey  == keyData.ctrl) { // if we pass this, all modifiers match

			if (keyData.keys instanceof Array) {
				for (var i=0;i<keyData.keys.length;i++) {
					if (keyPressed == keyData.keys[i]) {
						keyEvent.fire(keyPressed, e);
						break;
					}
				}
			} else {
				if (keyPressed == keyData.keys) {
					keyEvent.fire(keyPressed, e);
				}
			}
		}
	}

	this.enable = function() {
		if (! this.enabled) {
			YAHOO.util.Event.addListener(attachTo, event, handleKeyPress);
			this.enabledEvent.fire(keyData);
		}
		this.enabled = true;
	}

	this.disable = function() {
		if (this.enabled) {
			YAHOO.util.Event.removeListener(attachTo, event, handleKeyPress);
			this.disabledEvent.fire(keyData);
		}
		this.enabled = false;
	}

	/**
	* Returns a string representation of the object.
	* @type string
	*/ 
	this.toString = function() {
		return "KeyListener [" + keyData.keys + "] " + attachTo.tagName + (attachTo.id ? "[" + attachTo.id + "]" : "");
	}

}

/**
* Constant representing the DOM "keydown" event.
* @final
*/
YAHOO.util.KeyListener.KEYDOWN = "keydown";

/**
* Constant representing the DOM "keyup" event.
* @final
*/
YAHOO.util.KeyListener.KEYUP = "keyup";

/**
* Boolean indicating the enabled/disabled state of the Tooltip
* @type Booleam
*/
YAHOO.util.KeyListener.prototype.enabled = null;

/**
* Enables the KeyListener, by dynamically attaching the key event to the appropriate DOM element.
*/
YAHOO.util.KeyListener.prototype.enable = function() {};

/**
* Disables the KeyListener, by dynamically removing the key event from the appropriate DOM element.
*/
YAHOO.util.KeyListener.prototype.disable = function() {};

/**
* CustomEvent fired when the KeyListener is enabled
* args: keyData
* @type YAHOO.util.CustomEvent
*/
YAHOO.util.KeyListener.prototype.enabledEvent = null;

/**
* CustomEvent fired when the KeyListener is disabled
* args: keyData
* @type YAHOO.util.CustomEvent
*/
YAHOO.util.KeyListener.prototype.disabledEvent = null;

/**
* @class
* Tooltip is an implementation of Overlay that behaves like an OS tooltip, displaying when the user mouses over a particular element, and disappearing on mouse out.
* @param {string}	el	The element ID representing the Tooltip <em>OR</em>
* @param {Element}	el	The element representing the Tooltip
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Overlay. See configuration documentation for more details.
* @constructor
*/
YAHOO.widget.Tooltip = function(el, userConfig) {
	YAHOO.widget.Tooltip.superclass.constructor.call(this, el, userConfig);
}

YAHOO.extend(YAHOO.widget.Tooltip, YAHOO.widget.Overlay);

YAHOO.widget.Tooltip.logger = new YAHOO.widget.LogWriter("Tooltip");

/**
* Constant representing the Tooltip CSS class
* @type string
* @final
*/
YAHOO.widget.Tooltip.CSS_TOOLTIP = "tt";

/**
* The Tooltip initialization method. This method is automatically called by the constructor. A Tooltip is automatically rendered by the init method, and it also is set to be invisible by default, and constrained to viewport by default as well.
* @param {string}	el	The element ID representing the Tooltip <em>OR</em>
* @param {Element}	el	The element representing the Tooltip
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Tooltip. See configuration documentation for more details.
*/
YAHOO.widget.Tooltip.prototype.init = function(el, userConfig) {
	this.logger = YAHOO.widget.Tooltip.logger;

	if (document.readyState && document.readyState != "complete") {
		var deferredInit = function() {
			this.init(el, userConfig);
		}
		YAHOO.util.Event.addListener(window, "load", deferredInit, this, true);
	} else {
		YAHOO.widget.Tooltip.superclass.init.call(this, el);

		this.beforeInitEvent.fire(YAHOO.widget.Tooltip);

		YAHOO.util.Dom.addClass(this.element, YAHOO.widget.Tooltip.CSS_TOOLTIP);

		if (userConfig) {
			this.cfg.applyConfig(userConfig, true);
		}
		
		this.cfg.queueProperty("visible",false);
		this.cfg.queueProperty("constraintoviewport",true);

		this.setBody("");
		this.render(this.cfg.getProperty("container"));

		this.initEvent.fire(YAHOO.widget.Tooltip);
	}
}

/**
* Initializes the class's configurable properties which can be changed using the Overlay's Config object (cfg).
*/
YAHOO.widget.Tooltip.prototype.initDefaultConfig = function() {
	YAHOO.widget.Tooltip.superclass.initDefaultConfig.call(this);

	this.cfg.addProperty("preventoverlap",		{ value:true, validator:this.cfg.checkBoolean, supercedes:["x","y","xy"] } );

	this.cfg.addProperty("showdelay",			{ value:200, handler:this.configShowDelay, validator:this.cfg.checkNumber } );
	this.cfg.addProperty("autodismissdelay",	{ value:5000, handler:this.configAutoDismissDelay, validator:this.cfg.checkNumber } );
	this.cfg.addProperty("hidedelay",			{ value:250, handler:this.configHideDelay, validator:this.cfg.checkNumber } );

	this.cfg.addProperty("text",				{ handler:this.configText, suppressEvent:true } );
	this.cfg.addProperty("container",			{ value:document.body, handler:this.configContainer } );
}

// BEGIN BUILT-IN PROPERTY EVENT HANDLERS //

/**
* The default event handler fired when the "text" property is changed.
*/
YAHOO.widget.Tooltip.prototype.configText = function(type, args, obj) {
	var text = args[0];
	if (text) {
		this.setBody(text);
	}
}

/**
* The default event handler fired when the "container" property is changed.
*/
YAHOO.widget.Tooltip.prototype.configContainer = function(type, args, obj) {
	var container = args[0];
	if (typeof container == 'string') {
		this.cfg.setProperty("container", document.getElementById(container), true);
	}
}

/**
* The default event handler fired when the "context" property is changed.
*/
YAHOO.widget.Tooltip.prototype.configContext = function(type, args, obj) {
	var context = args[0];
	if (context) {
		
		// Normalize parameter into an array
		if (! (context instanceof Array)) {
			if (typeof context == "string") {
				this.cfg.setProperty("context", [document.getElementById(context)], true);
			} else { // Assuming this is an element
				this.cfg.setProperty("context", [context], true);
			}
			context = this.cfg.getProperty("context");
		}


		// Remove any existing mouseover/mouseout listeners
		if (this._context) {
			for (var c=0;c<this._context.length;++c) {
				var el = this._context[c];
				YAHOO.util.Event.removeListener(el, "mouseover", this.onContextMouseOver);
				YAHOO.util.Event.removeListener(el, "mousemove", this.onContextMouseMove);
				YAHOO.util.Event.removeListener(el, "mouseout", this.onContextMouseOut);
			}
		}

		// Add mouseover/mouseout listeners to context elements
		this._context = context;
		for (var c=0;c<this._context.length;++c) {
			var el = this._context[c];
			YAHOO.util.Event.addListener(el, "mouseover", this.onContextMouseOver, this);
			YAHOO.util.Event.addListener(el, "mousemove", this.onContextMouseMove, this);
			YAHOO.util.Event.addListener(el, "mouseout", this.onContextMouseOut, this);
		}
	}
}

// END BUILT-IN PROPERTY EVENT HANDLERS //

// BEGIN BUILT-IN DOM EVENT HANDLERS //

/**
* The default event handler fired when the user moves the mouse while over the context element.
* @param {DOMEvent} e	The current DOM event
* @param {object}	obj	The object argument
*/
YAHOO.widget.Tooltip.prototype.onContextMouseMove = function(e, obj) {
	obj.pageX = YAHOO.util.Event.getPageX(e);
	obj.pageY = YAHOO.util.Event.getPageY(e);

}

/**
* The default event handler fired when the user mouses over the context element.
* @param {DOMEvent} e	The current DOM event
* @param {object}	obj	The object argument
*/
YAHOO.widget.Tooltip.prototype.onContextMouseOver = function(e, obj) {

	if (obj.hideProcId) {
		clearTimeout(obj.hideProcId);
		obj.logger.log("Clearing hide timer: " + obj.hideProcId, "time");
		obj.hideProcId = null;
	}
	
	var context = this;
	YAHOO.util.Event.addListener(context, "mousemove", obj.onContextMouseMove, obj);

	if (context.title) {
		obj._tempTitle = context.title;
		context.title = "";
	}

	/**
	* The unique process ID associated with the thread responsible for showing the Tooltip.
	* @type int
	*/
	obj.showProcId = obj.doShow(e, context);
	obj.logger.log("Setting show tooltip timeout: " + this.showProcId, "time");
}

/**
* The default event handler fired when the user mouses out of the context element.
* @param {DOMEvent} e	The current DOM event
* @param {object}	obj	The object argument
*/
YAHOO.widget.Tooltip.prototype.onContextMouseOut = function(e, obj) {
	var el = this;

	if (obj._tempTitle) {
		el.title = obj._tempTitle;
		obj._tempTitle = null;
	}
	
	if (obj.showProcId) {
		clearTimeout(obj.showProcId);
		obj.logger.log("Clearing show timer: " + obj.showProcId, "time");
		obj.showProcId = null;		
	}

	if (obj.hideProcId) {
		clearTimeout(obj.hideProcId);
		obj.logger.log("Clearing hide timer: " + obj.hideProcId, "time");
		obj.hideProcId = null;
	}


	obj.hideProcId = setTimeout(function() {
				obj.hide();
				}, obj.cfg.getProperty("hidedelay"));
}

// END BUILT-IN DOM EVENT HANDLERS //

/**
* Processes the showing of the Tooltip by setting the timeout delay and offset of the Tooltip.
* @param {DOMEvent} e	The current DOM event
* @return {int}	The process ID of the timeout function associated with doShow
*/
YAHOO.widget.Tooltip.prototype.doShow = function(e, context) {
	
	var yOffset = 25;
	if (this.browser == "opera" && context.tagName == "A") {
		yOffset += 12;
	}

	var me = this;
	return setTimeout(
		function() {
			if (me._tempTitle) {
				me.setBody(me._tempTitle);
			} else {
				me.cfg.refireEvent("text");
			}

			me.logger.log("Show tooltip", "time");
			me.moveTo(me.pageX, me.pageY + yOffset);
			if (me.cfg.getProperty("preventoverlap")) {
				me.preventOverlap(me.pageX, me.pageY);
			}
			
			YAHOO.util.Event.removeListener(context, "mousemove", me.onContextMouseMove);

			me.show();
			me.hideProcId = me.doHide();
			me.logger.log("Hide tooltip time active: " + me.hideProcId, "time");
		},
	this.cfg.getProperty("showdelay"));
}

/**
* Sets the timeout for the auto-dismiss delay, which by default is 5 seconds, meaning that a tooltip will automatically dismiss itself after 5 seconds of being displayed.
*/
YAHOO.widget.Tooltip.prototype.doHide = function() {
	var me = this;
	me.logger.log("Setting hide tooltip timeout", "time");
	return setTimeout(
		function() {
			me.logger.log("Hide tooltip", "time");
			me.hide();
		},
		this.cfg.getProperty("autodismissdelay"));
}

/**
* Fired when the Tooltip is moved, this event handler is used to prevent the Tooltip from overlapping with its context element.
*/
YAHOO.widget.Tooltip.prototype.preventOverlap = function(pageX, pageY) {
	
	var height = this.element.offsetHeight;
	
	var elementRegion = YAHOO.util.Dom.getRegion(this.element);

	elementRegion.top -= 5;
	elementRegion.left -= 5;
	elementRegion.right += 5;
	elementRegion.bottom += 5;

	var mousePoint = new YAHOO.util.Point(pageX, pageY);
	
	this.logger.log("context " + elementRegion, "ttip");
	this.logger.log("mouse " + mousePoint, "ttip");

	if (elementRegion.contains(mousePoint)) {
		this.logger.log("OVERLAP", "warn");
		this.cfg.setProperty("y", (pageY-height-5))
	}
}

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.Tooltip.prototype.toString = function() {
	return "Tooltip " + this.id;
}

/**
* @class
* Panel is an implementation of Overlay that behaves like an OS window, with a draggable header and an optional close icon at the top right.
* @param {string}	el	The element ID representing the Panel <em>OR</em>
* @param {Element}	el	The element representing the Panel
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Panel. See configuration documentation for more details.
* @constructor
*/
YAHOO.widget.Panel = function(el, userConfig) {
	YAHOO.widget.Panel.superclass.constructor.call(this, el, userConfig);
}

YAHOO.extend(YAHOO.widget.Panel, YAHOO.widget.Overlay);

/**
* Constant representing the default CSS class used for a Panel
* @type string
* @final
*/
YAHOO.widget.Panel.CSS_PANEL = "panel";

/**
* Constant representing the default CSS class used for a Panel's wrapping container
* @type string
* @final
*/
YAHOO.widget.Panel.CSS_PANEL_CONTAINER = "panel-container";

/**
* CustomEvent fired after the modality mask is shown
* args: none
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Panel.prototype.showMaskEvent = null;

/**
* CustomEvent fired after the modality mask is hidden
* args: none
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Panel.prototype.hideMaskEvent = null;

/**
* The Overlay initialization method, which is executed for Overlay and all of its subclasses. This method is automatically called by the constructor, and  sets up all DOM references for pre-existing markup, and creates required markup if it is not already present.
* @param {string}	el	The element ID representing the Overlay <em>OR</em>
* @param {Element}	el	The element representing the Overlay
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Overlay. See configuration documentation for more details.
*/
YAHOO.widget.Panel.prototype.init = function(el, userConfig) {
	YAHOO.widget.Panel.superclass.init.call(this, el/*, userConfig*/);  // Note that we don't pass the user config in here yet because we only want it executed once, at the lowest subclass level
	
	this.beforeInitEvent.fire(YAHOO.widget.Panel);

	YAHOO.util.Dom.addClass(this.element, YAHOO.widget.Panel.CSS_PANEL);

	this.buildWrapper();			
	
	if (userConfig) {
		this.cfg.applyConfig(userConfig, true);
	}

	this.beforeRenderEvent.subscribe(function() {
		var draggable = this.cfg.getProperty("draggable");
		if (draggable) {
			if (! this.header) {
				this.setHeader("&nbsp;");
			}
		}
	}, this, true);

	this.initEvent.fire(YAHOO.widget.Panel);

}

/**
* Initializes the custom events for Module which are fired automatically at appropriate times by the Module class.
*/
YAHOO.widget.Panel.prototype.initEvents = function() {
	YAHOO.widget.Panel.superclass.initEvents.call(this);

	this.showMaskEvent = new YAHOO.util.CustomEvent("showMask");
	this.hideMaskEvent = new YAHOO.util.CustomEvent("hideMask");

	this.dragEvent = new YAHOO.util.CustomEvent("drag");
}

/**
* Initializes the class's configurable properties which can be changed using the Panel's Config object (cfg).
*/
YAHOO.widget.Panel.prototype.initDefaultConfig = function() {
	YAHOO.widget.Panel.superclass.initDefaultConfig.call(this);

	// Add panel config properties //

	this.cfg.addProperty("close", { value:true, handler:this.configClose, validator:this.cfg.checkBoolean, supercedes:["visible"] } );
	this.cfg.addProperty("draggable", { value:true,	handler:this.configDraggable, validator:this.cfg.checkBoolean, supercedes:["visible"] } );

	this.cfg.addProperty("underlay", { value:"shadow", handler:this.configUnderlay, supercedes:["visible"] } );
	this.cfg.addProperty("modal",	{ value:false, handler:this.configModal, validator:this.cfg.checkBoolean, supercedes:["visible"] } );

	this.cfg.addProperty("keylisteners", { handler:this.configKeyListeners, suppressEvent:true, supercedes:["visible"] } );
}

// BEGIN BUILT-IN PROPERTY EVENT HANDLERS //

/**
* The default event handler fired when the "close" property is changed. The method controls the appending or hiding of the close icon at the top right of the Panel.
*/
YAHOO.widget.Panel.prototype.configClose = function(type, args, obj) {
	var val = args[0];

	var doHide = function(e, obj) {
		obj.hide();
	}

	if (val) {
		if (! this.close) {
			this.close = document.createElement("DIV");
			YAHOO.util.Dom.addClass(this.close, "close");

			if (this.isSecure) {
				YAHOO.util.Dom.addClass(this.close, "secure");
			} else {
				YAHOO.util.Dom.addClass(this.close, "nonsecure");
			}

			this.close.innerHTML = "&nbsp;";
			this.innerElement.appendChild(this.close);
			YAHOO.util.Event.addListener(this.close, "click", doHide, this);	
		} else {
			this.close.style.display = "block";
		}
	} else {
		if (this.close) {
			this.close.style.display = "none";
		}
	}
}

/**
* The default event handler fired when the "draggable" property is changed.
*/
YAHOO.widget.Panel.prototype.configDraggable = function(type, args, obj) {
	var val = args[0];
	if (val) {
		if (this.header) {
			YAHOO.util.Dom.setStyle(this.header,"cursor","move");
			this.registerDragDrop();
		}
	} else {
		if (this.dd) {
			this.dd.unreg();
		}
		if (this.header) {
			YAHOO.util.Dom.setStyle(this.header,"cursor","auto");
		}
	}
}

/**
* The default event handler fired when the "underlay" property is changed.
*/
YAHOO.widget.Panel.prototype.configUnderlay = function(type, args, obj) {
	var val = args[0];

	switch (val.toLowerCase()) {
		case "shadow":
			YAHOO.util.Dom.removeClass(this.element, "matte");
			YAHOO.util.Dom.addClass(this.element, "shadow");

			if (! this.underlay) { // create if not already in DOM
				this.underlay = document.createElement("DIV");
				this.underlay.className = "underlay";
				this.underlay.innerHTML = "&nbsp;";
				this.element.appendChild(this.underlay);
			} 

			this.sizeUnderlay();
			break;
		case "matte":
			YAHOO.util.Dom.removeClass(this.element, "shadow");
			YAHOO.util.Dom.addClass(this.element, "matte");
			break;
		case "none":
		default:
			YAHOO.util.Dom.removeClass(this.element, "shadow");
			YAHOO.util.Dom.removeClass(this.element, "matte");
			break;
	}
}

/**
* The default event handler fired when the "modal" property is changed. This handler subscribes or unsubscribes to the show and hide events to handle the display or hide of the modality mask.
*/
YAHOO.widget.Panel.prototype.configModal = function(type, args, obj) {
	var modal = args[0];

	if (modal) {
		this.buildMask();

		if (! YAHOO.util.Config.alreadySubscribed( this.showEvent, this.showMask, this ) ) {
			this.showEvent.subscribe(this.showMask, this, true);
		}
		if (! YAHOO.util.Config.alreadySubscribed( this.hideEvent, this.hideMask, this) ) {
			this.hideEvent.subscribe(this.hideMask, this, true);
		}
		if (! YAHOO.util.Config.alreadySubscribed( YAHOO.widget.Overlay.windowResizeEvent, this.sizeMask, this ) ) {
			YAHOO.widget.Overlay.windowResizeEvent.subscribe(this.sizeMask, this, true);
		}
		if (! YAHOO.util.Config.alreadySubscribed( YAHOO.widget.Overlay.windowScrollEvent, this.sizeMask, this ) ) {
			YAHOO.widget.Overlay.windowScrollEvent.subscribe(this.sizeMask, this, true);
		}
	} else {
		this.beforeShowEvent.unsubscribe(this.showMask, this);
		this.hideEvent.unsubscribe(this.hideMask, this);
		YAHOO.widget.Overlay.windowResizeEvent.unsubscribe(this.sizeMask);
		YAHOO.widget.Overlay.windowScrollEvent.unsubscribe(this.sizeMask);
	}
}

/**
* The default event handler fired when the "keylisteners" property is changed. 
*/
YAHOO.widget.Panel.prototype.configKeyListeners = function(type, args, obj) {
	var listeners = args[0];

	if (listeners) {
		if (listeners instanceof Array) {
			for (var i=0;i<listeners.length;i++) {
				var listener = listeners[i];

				if (! YAHOO.util.Config.alreadySubscribed(this.showEvent, listener.enable, listener)) {
					this.showEvent.subscribe(listener.enable, listener, true);
				}
				if (! YAHOO.util.Config.alreadySubscribed(this.hideEvent, listener.disable, listener)) {
					this.hideEvent.subscribe(listener.disable, listener, true);
					this.destroyEvent.subscribe(listener.disable, listener, true);
				}
			}
		} else {
			if (! YAHOO.util.Config.alreadySubscribed(this.showEvent, listeners.enable, listeners)) {
				this.showEvent.subscribe(listeners.enable, listeners, true);
			}
			if (! YAHOO.util.Config.alreadySubscribed(this.hideEvent, listeners.disable, listeners)) {
				this.hideEvent.subscribe(listeners.disable, listeners, true);
				this.destroyEvent.subscribe(listeners.disable, listeners, true); 
			}
		}
	} 
}

// END BUILT-IN PROPERTY EVENT HANDLERS //


/**
* Builds the wrapping container around the Panel that is used for positioning the shadow and matte underlays. The container element is assigned to a  local instance variable called container, and the element is reinserted inside of it.
*/
YAHOO.widget.Panel.prototype.buildWrapper = function() {
	var elementParent = this.element.parentNode;

	var elementClone = this.element.cloneNode(true);
	this.innerElement = elementClone;
	this.innerElement.style.visibility = "inherit";

	YAHOO.util.Dom.addClass(this.innerElement, YAHOO.widget.Panel.CSS_PANEL);

	var wrapper = document.createElement("DIV");
	wrapper.className = YAHOO.widget.Panel.CSS_PANEL_CONTAINER;
	wrapper.id = elementClone.id + "_c";
	
	wrapper.appendChild(elementClone);
	
	if (elementParent) {
		elementParent.replaceChild(wrapper, this.element);
	}

	this.element = wrapper;

	// Resynchronize the local field references

	var childNodes = this.innerElement.childNodes;
	if (childNodes) {
		for (var i=0;i<childNodes.length;i++) {
			var child = childNodes[i];
			switch (child.className) {
				case YAHOO.widget.Module.CSS_HEADER:
					this.header = child;
					break;
				case YAHOO.widget.Module.CSS_BODY:
					this.body = child;
					break;
				case YAHOO.widget.Module.CSS_FOOTER:
					this.footer = child;
					break;
			}
		}
	}

	this.initDefaultConfig(); // We've changed the DOM, so the configuration must be re-tooled to get the DOM references right
}

/**
* Adjusts the size of the shadow based on the size of the element.
*/
YAHOO.widget.Panel.prototype.sizeUnderlay = function() {
	if (this.underlay && this.browser != "gecko" && this.browser != "safari") {
		this.underlay.style.width = this.innerElement.offsetWidth + "px";
		this.underlay.style.height = this.innerElement.offsetHeight + "px";
	}
}

/**
* Event handler fired when the resize monitor element is resized.
*/
YAHOO.widget.Panel.prototype.onDomResize = function(e, obj) { 
	YAHOO.widget.Panel.superclass.onDomResize.call(this, e, obj);
	var me = this;
	setTimeout(function() {
		me.sizeUnderlay();
	}, 0);
};

/**
* Registers the Panel's header for drag & drop capability.
*/
YAHOO.widget.Panel.prototype.registerDragDrop = function() {
	if (this.header) {
		this.dd = new YAHOO.util.DD(this.element.id, this.id);

		if (! this.header.id) {
			this.header.id = this.id + "_h";
		}
		
		var me = this;

		this.dd.startDrag = function() {

			if (me.browser == "ie") {
				YAHOO.util.Dom.addClass(me.element,"drag");
			}

			if (me.cfg.getProperty("constraintoviewport")) {
				var offsetHeight = me.element.offsetHeight;
				var offsetWidth = me.element.offsetWidth;

				var viewPortWidth = YAHOO.util.Dom.getViewportWidth();
				var viewPortHeight = YAHOO.util.Dom.getViewportHeight();

				var scrollX = window.scrollX || document.documentElement.scrollLeft;
				var scrollY = window.scrollY || document.documentElement.scrollTop;

				var topConstraint = scrollY + 10;
				var leftConstraint = scrollX + 10;
				var bottomConstraint = scrollY + viewPortHeight - offsetHeight - 10;
				var rightConstraint = scrollX + viewPortWidth - offsetWidth - 10;

				this.minX = leftConstraint
				this.maxX = rightConstraint;
				this.constrainX = true;

				this.minY = topConstraint;
				this.maxY = bottomConstraint;
				this.constrainY = true;
			} else {
				this.constrainX = false;
				this.constrainY = false;
			}

			me.dragEvent.fire("startDrag", arguments);
		}
		
		this.dd.onDrag = function() {
			me.syncPosition();
			me.cfg.refireEvent("iframe");
			if (this.platform == "mac" && this.browser == "gecko") {
				this.showMacGeckoScrollbars();
			}

			me.dragEvent.fire("onDrag", arguments);
		}

		this.dd.endDrag = function() {
			if (me.browser == "ie") {
				YAHOO.util.Dom.removeClass(me.element,"drag");
			}

			me.dragEvent.fire("endDrag", arguments);
		}

		this.dd.setHandleElId(this.header.id);
		this.dd.addInvalidHandleType("INPUT");
		this.dd.addInvalidHandleType("SELECT");
		this.dd.addInvalidHandleType("TEXTAREA");
	}
}

/**
* Builds the mask that is laid over the document when the Panel is configured to be modal.
*/
YAHOO.widget.Panel.prototype.buildMask = function() {
	if (! this.mask) {
		this.mask = document.createElement("DIV");
		this.mask.id = this.id + "_mask";
		this.mask.className = "mask";
		this.mask.innerHTML = "&nbsp;";

		var maskClick = function(e, obj) {
			YAHOO.util.Event.stopEvent(e);
		}

		YAHOO.util.Event.addListener(this.mask, maskClick, this);

		document.body.appendChild(this.mask);
	}
}

/**
* Hides the modality mask.
*/
YAHOO.widget.Panel.prototype.hideMask = function() {
	if (this.cfg.getProperty("modal") && this.mask) {
		this.mask.style.display = "none";
		this.hideMaskEvent.fire();
		YAHOO.util.Dom.removeClass(document.body, "masked");
	}
}

/**
* Shows the modality mask.
*/
YAHOO.widget.Panel.prototype.showMask = function() {
	if (this.cfg.getProperty("modal") && this.mask) {
		YAHOO.util.Dom.addClass(document.body, "masked");
		this.sizeMask();
		this.mask.style.display = "block";
		this.showMaskEvent.fire();
	}
}

/**
* Sets the size of the modality mask to cover the entire scrollable area of the document
*/
YAHOO.widget.Panel.prototype.sizeMask = function() {
	if (this.mask) {
		this.mask.style.height = YAHOO.util.Dom.getDocumentHeight()+"px";
		this.mask.style.width = YAHOO.util.Dom.getDocumentWidth()+"px";
	}
}

/**
* The default event handler fired when the "height" property is changed.
*/
YAHOO.widget.Panel.prototype.configHeight = function(type, args, obj) {
	var height = args[0];
	var el = this.innerElement;
	YAHOO.util.Dom.setStyle(el, "height", height);
	this.cfg.refireEvent("underlay");
	this.cfg.refireEvent("iframe");
}

/**
* The default event handler fired when the "width" property is changed.
*/
YAHOO.widget.Panel.prototype.configWidth = function(type, args, obj) {
	var width = args[0];
	var el = this.innerElement;
	YAHOO.util.Dom.setStyle(el, "width", width);
	this.cfg.refireEvent("underlay");
	this.cfg.refireEvent("iframe");
}

/**
* Renders the Panel by inserting the elements that are not already in the main Panel into their correct places. Optionally appends the Panel to the specified node prior to the render's execution. NOTE: For Panels without existing markup, the appendToNode argument is REQUIRED. If this argument is ommitted and the current element is not present in the document, the function will return false, indicating that the render was a failure.
* @param {string}	appendToNode	The element id to which the Module should be appended to prior to rendering <em>OR</em>
* @param {Element}	appendToNode	The element to which the Module should be appended to prior to rendering	
* @return {boolean} Success or failure of the render
*/
YAHOO.widget.Panel.prototype.render = function(appendToNode) {
	return YAHOO.widget.Panel.superclass.render.call(this, appendToNode, this.innerElement);
}

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.Panel.prototype.toString = function() {
	return "Panel " + this.id;
}

/**
* @class
* Dialog is an implementation of Panel that can be used to submit form data. Built-in functionality for buttons with event handlers is included, and button sets can be build dynamically, or the preincluded ones for Submit/Cancel and OK/Cancel can be utilized. Forms can be processed in 3 ways -- via an asynchronous Connection utility call, a simple form POST or GET, or manually.
* @param {string}	el	The element ID representing the Dialog <em>OR</em>
* @param {Element}	el	The element representing the Dialog
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Dialog. See configuration documentation for more details.
* @constructor
*/
YAHOO.widget.Dialog = function(el, userConfig) {
	YAHOO.widget.Dialog.superclass.constructor.call(this, el, userConfig);
}

YAHOO.extend(YAHOO.widget.Dialog, YAHOO.widget.Panel);

/**
* Constant representing the default CSS class used for a Dialog
* @type string
* @final
*/
YAHOO.widget.Dialog.CSS_DIALOG = "dialog";


/**
* CustomEvent fired prior to submission
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Dialog.prototype.beforeSubmitEvent = null;

/**
* CustomEvent fired after submission
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Dialog.prototype.submitEvent = null;

/**
* CustomEvent fired prior to manual submission
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Dialog.prototype.manualSubmitEvent = null;

/**
* CustomEvent fired prior to asynchronous submission
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Dialog.prototype.asyncSubmitEvent = null;

/**
* CustomEvent fired prior to form-based submission
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Dialog.prototype.formSubmitEvent = null;

/**
* CustomEvent fired after cancel
* @type YAHOO.util.CustomEvent
*/
YAHOO.widget.Dialog.prototype.cancelEvent = null;


/**
* Initializes the class's configurable properties which can be changed using the Dialog's Config object (cfg).
*/
YAHOO.widget.Dialog.prototype.initDefaultConfig = function() {
	YAHOO.widget.Dialog.superclass.initDefaultConfig.call(this);

	/**
	* The internally maintained callback object for use with the Connection utility
	* @type object
	* @private
	*/
	this.callback = {
		success : null,
		failure : null,
		argument: null,
		scope : this
	}

	this.doSubmit = function() {
		var method = this.cfg.getProperty("postmethod");
		switch (method) {
			case "async":
				YAHOO.util.Connect.setForm(this.form.name);
				var cObj = YAHOO.util.Connect.asyncRequest('POST', this.form.action, this.callback);
				this.asyncSubmitEvent.fire();
				break;
			case "form":
				this.form.submit();
				this.formSubmitEvent.fire();
				break;
			case "none":
			case "manual":
				this.manualSubmitEvent.fire();
				break;
		}
	}

	// Add form dialog config properties //
	this.cfg.addProperty("postmethod", { value:"async", validator:function(val) { 
													if (val != "form" && val != "async" && val != "none" && val != "manual") {
														return false;
													} else {
														return true;
													}
												} });

	this.cfg.addProperty("buttons",		{ value:"none",	handler:this.configButtons } );
}

/**
* Initializes the custom events for Dialog which are fired automatically at appropriate times by the Dialog class.
*/
YAHOO.widget.Dialog.prototype.initEvents = function() {
	YAHOO.widget.Dialog.superclass.initEvents.call(this);
	
	this.beforeSubmitEvent	= new YAHOO.util.CustomEvent("beforeSubmit");
	this.submitEvent		= new YAHOO.util.CustomEvent("submit");

	this.manualSubmitEvent	= new YAHOO.util.CustomEvent("manualSubmit");
	this.asyncSubmitEvent	= new YAHOO.util.CustomEvent("asyncSubmit");
	this.formSubmitEvent	= new YAHOO.util.CustomEvent("formSubmit");

	this.cancelEvent		= new YAHOO.util.CustomEvent("cancel");
}

/**
* The Dialog initialization method, which is executed for Dialog and all of its subclasses. This method is automatically called by the constructor, and  sets up all DOM references for pre-existing markup, and creates required markup if it is not already present.
* @param {string}	el	The element ID representing the Dialog <em>OR</em>
* @param {Element}	el	The element representing the Dialog
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this Dialog. See configuration documentation for more details.
*/
YAHOO.widget.Dialog.prototype.init = function(el, userConfig) {
	YAHOO.widget.Dialog.superclass.init.call(this, el/*, userConfig*/);  // Note that we don't pass the user config in here yet because we only want it executed once, at the lowest subclass level
	
	this.beforeInitEvent.fire(YAHOO.widget.Dialog);

	YAHOO.util.Dom.addClass(this.element, YAHOO.widget.Dialog.CSS_DIALOG);

	this.cfg.setProperty("visible", false);

	if (userConfig) {
		this.cfg.applyConfig(userConfig, true);
	}

	this.renderEvent.subscribe(this.registerForm, this, true);

	this.showEvent.subscribe(this.focusFirst, this, true);
	this.beforeHideEvent.subscribe(this.blurButtons, this, true);

	this.beforeRenderEvent.subscribe(function() {
		var buttonCfg = this.cfg.getProperty("buttons");
		if (buttonCfg && buttonCfg != "none") {
			if (! this.footer) {
				this.setFooter("");
			}
		}
	}, this, true);

	this.initEvent.fire(YAHOO.widget.Dialog);
}

/**
* Prepares the Dialog's internal FORM object, creating one if one is not currently present.
*/
YAHOO.widget.Dialog.prototype.registerForm = function() {
	var form = this.element.getElementsByTagName("FORM")[0];

	if (! form) {
		var formHTML = "<form name=\"frm_" + this.id + "\" action=\"\"></form>";
		this.body.innerHTML += formHTML;
		form = this.element.getElementsByTagName("FORM")[0];
	}

	this.firstFormElement = function() {
		for (var f=0;f<form.elements.length;f++ ) {
			var el = form.elements[f];
			if (el.focus) {
				if (el.type && el.type != "hidden") {
					return el;
					break;
				}
			}
		}
		return null;
	}();

	this.lastFormElement = function() {
		for (var f=form.elements.length-1;f>=0;f-- ) {
			var el = form.elements[f];
			if (el.focus) {
				if (el.type && el.type != "hidden") {
					return el;
					break;
				}
			}
		}
		return null;
	}();

	this.form = form;

	if (this.cfg.getProperty("modal") && this.form) {

		var me = this;
		
		var firstElement = this.firstFormElement || this.firstButton;
		if (firstElement) {
			this.preventBackTab = new YAHOO.util.KeyListener(firstElement, { shift:true, keys:9 }, {fn:me.focusLast, scope:me, correctScope:true} );
			this.showEvent.subscribe(this.preventBackTab.enable, this.preventBackTab, true);
			this.hideEvent.subscribe(this.preventBackTab.disable, this.preventBackTab, true);
		}

		var lastElement = this.lastButton || this.lastFormElement;
		if (lastElement) {
			this.preventTabOut = new YAHOO.util.KeyListener(lastElement, { shift:false, keys:9 }, {fn:me.focusFirst, scope:me, correctScope:true} );
			this.showEvent.subscribe(this.preventTabOut.enable, this.preventTabOut, true);
			this.hideEvent.subscribe(this.preventTabOut.disable, this.preventTabOut, true);
		}
	}
}

// BEGIN BUILT-IN PROPERTY EVENT HANDLERS //

/**
* The default event handler for the "buttons" configuration property
*/
YAHOO.widget.Dialog.prototype.configButtons = function(type, args, obj) {
	var buttons = args[0];
	if (buttons != "none") {
		this.buttonSpan = null;
		this.buttonSpan = document.createElement("SPAN");
		this.buttonSpan.className = "button-group";

		for (var b=0;b<buttons.length;b++) {
			var button = buttons[b];

			var htmlButton = document.createElement("BUTTON");

			if (button.isDefault) {
				htmlButton.className = "default";
				this.defaultHtmlButton = htmlButton;
			}

			htmlButton.appendChild(document.createTextNode(button.text));
			YAHOO.util.Event.addListener(htmlButton, "click", button.handler, this, true);

			this.buttonSpan.appendChild(htmlButton);		
			button.htmlButton = htmlButton;

			if (b == 0) {
				this.firstButton = button.htmlButton;
			}

			if (b == (buttons.length-1)) {
				this.lastButton = button.htmlButton;
			}

		}

		this.setFooter(this.buttonSpan);

		this.cfg.refireEvent("iframe");
		this.cfg.refireEvent("underlay");
	} else { // Do cleanup
		if (this.buttonSpan) {
			if (this.buttonSpan.parentNode) {
				this.buttonSpan.parentNode.removeChild(this.buttonSpan);
			}

			this.buttonSpan = null;
			this.firstButton = null;
			this.lastButton = null;
			this.defaultHtmlButton = null;
		}
	}
}

/**
* The default handler fired when the "success" property is changed. Used for asynchronous submission only.
*/ 
YAHOO.widget.Dialog.prototype.configOnSuccess = function(type,args,obj){};

/**
* The default handler fired when the "failure" property is changed. Used for asynchronous submission only.
*/ 
YAHOO.widget.Dialog.prototype.configOnFailure = function(type,args,obj){};

/**
* Executes a submission of the form based on the value of the postmethod property.
*/
YAHOO.widget.Dialog.prototype.doSubmit = function() {};

/**
* The default event handler used to focus the first field of the form when the Dialog is shown.
*/
YAHOO.widget.Dialog.prototype.focusFirst = function(type,args,obj) {
	if (args) {
		var e = args[1];
		if (e) {
			YAHOO.util.Event.stopEvent(e);
		}
	}

	if (this.firstFormElement) {
		this.firstFormElement.focus();
	} else {
		this.focusDefaultButton();
	}
}

/**
* Sets the focus to the last button in the button or form element in the Dialog
*/
YAHOO.widget.Dialog.prototype.focusLast = function(type,args,obj) {
	if (args) {
		var e = args[1];
		if (e) {
			YAHOO.util.Event.stopEvent(e);
		}
	}

	var buttons = this.cfg.getProperty("buttons");
	if (buttons && buttons instanceof Array) {
		this.focusLastButton();
	} else {
		if (this.lastFormElement) {
			this.lastFormElement.focus();
		}
	}
}

/**
* Sets the focus to the button that is designated as the default. By default, his handler is executed when the show event is fired.
*/
YAHOO.widget.Dialog.prototype.focusDefaultButton = function() {
	if (this.defaultHtmlButton) {
		this.defaultHtmlButton.focus();
	}
}

/**
* Blurs all the html buttons
*/
YAHOO.widget.Dialog.prototype.blurButtons = function() {
	var buttons = this.cfg.getProperty("buttons");
	if (buttons && buttons instanceof Array) {
		var html = buttons[0].htmlButton;
		if (html) {
			html.blur();
		}
	}
}

/**
* Sets the focus to the first button in the button list
*/
YAHOO.widget.Dialog.prototype.focusFirstButton = function() {
	var buttons = this.cfg.getProperty("buttons");
	if (buttons && buttons instanceof Array) {
		var html = buttons[0].htmlButton;
		if (html) {
			html.focus();
		}
	}
}

/**
* Sets the focus to the first button in the button list
*/
YAHOO.widget.Dialog.prototype.focusLastButton = function() {
	var buttons = this.cfg.getProperty("buttons");
	if (buttons && buttons instanceof Array) {
		var html = buttons[buttons.length-1].htmlButton;
		if (html) {
			html.focus();
		}
	}
}

// END BUILT-IN PROPERTY EVENT HANDLERS //

/**
* Built-in function hook for writing a validation function that will be checked for a "true" value prior to a submit. This function, as implemented by default, always returns true, so it should be overridden if validation is necessary.
*/
YAHOO.widget.Dialog.prototype.validate = function() {
	return true;
}

/**
* Executes a submit of the Dialog followed by a hide, if validation is successful.
*/
YAHOO.widget.Dialog.prototype.submit = function() {
	if (this.validate()) {
		this.beforeSubmitEvent.fire();
		this.doSubmit();
		this.submitEvent.fire();
		this.hide();
		return true;
	} else {
		return false;
	}
}

/**
* Executes the cancel of the Dialog followed by a hide.
*/
YAHOO.widget.Dialog.prototype.cancel = function() {
	this.cancelEvent.fire();
	this.hide();	
}

/**
* Returns a JSON-compatible data structure representing the data currently contained in the form.
* @return {object} A JSON object reprsenting the data of the current form.
*/
YAHOO.widget.Dialog.prototype.getData = function() {
	var form = this.form;
	var data = {};

	if (form) {
		for (var i in this.form) {
			var formItem = form[i];
			if (formItem) {
				if (formItem.tagName) { // Got a single form item
					switch (formItem.tagName) {
						case "INPUT":
							switch (formItem.type) {
								case "checkbox": 
									data[i] = formItem.checked;
									break;
								case "textbox":
								case "text":
								case "hidden":
									data[i] = formItem.value;
									break;
							}
							break;
						case "TEXTAREA":
							data[i] = formItem.value;
							break;
						case "SELECT":
							var val = new Array();
							for (var x=0;x<formItem.options.length;x++)	{
								var option = formItem.options[x];
								if (option.selected) {
									var selval = option.value;
									if (! selval || selval == "") {
										selval = option.text;
									}
									val[val.length] = selval;
								}
							}
							data[i] = val;
							break;
					}
				} else if (formItem[0] && formItem[0].tagName) { // this is an array of form items
					switch (formItem[0].tagName) {
						case "INPUT" :
							switch (formItem[0].type) {
								case "radio":
									for (var r=0; r<formItem.length; r++) {
										var radio = formItem[r];
										if (radio.checked) {
											data[radio.name] = radio.value;
											break;
										}
									}
									break;
								case "checkbox":
									var cbArray = new Array();
									for (var c=0; c<formItem.length; c++) {
										var check = formItem[c];
										if (check.checked) {
											cbArray[cbArray.length] = check.value;
										}
									}
									data[formItem[0].name] = cbArray;
									break;
							}
					}
				}
			}
		}	
	}
	return data;
}

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.Dialog.prototype.toString = function() {
	return "Dialog " + this.id;
}

/**
* @class
* SimpleDialog is a simple implementation of Dialog that can be used to submit a single value. Forms can be processed in 3 ways -- via an asynchronous Connection utility call, a simple form POST or GET, or manually.
* @param {string}	el	The element ID representing the SimpleDialog <em>OR</em>
* @param {Element}	el	The element representing the SimpleDialog
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this SimpleDialog. See configuration documentation for more details.
* @constructor
*/
YAHOO.widget.SimpleDialog = function(el, userConfig) {
	YAHOO.widget.SimpleDialog.superclass.constructor.call(this, el, userConfig);
}

YAHOO.extend(YAHOO.widget.SimpleDialog, YAHOO.widget.Dialog);

/**
* Constant for the standard network icon for a blocking action
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.ICON_BLOCK = "nt/ic/ut/bsc/blck16_1.gif";

/**
* Constant for the standard network icon for alarm
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.ICON_ALARM = "nt/ic/ut/bsc/alrt16_1.gif";

/**
* Constant for the standard network icon for help
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.ICON_HELP  = "nt/ic/ut/bsc/hlp16_1.gif";

/**
* Constant for the standard network icon for info
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.ICON_INFO  = "nt/ic/ut/bsc/info16_1.gif";

/**
* Constant for the standard network icon for warn
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.ICON_WARN  = "nt/ic/ut/bsc/warn16_1.gif";

/**
* Constant for the standard network icon for a tip
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.ICON_TIP   = "nt/ic/ut/bsc/tip16_1.gif";

/**
* Constant representing the default CSS class used for a SimpleDialog
* @type string
* @final
*/
YAHOO.widget.SimpleDialog.CSS_SIMPLEDIALOG = "simple-dialog";

/**
* Initializes the class's configurable properties which can be changed using the SimpleDialog's Config object (cfg).
*/
YAHOO.widget.SimpleDialog.prototype.initDefaultConfig = function() {
	YAHOO.widget.SimpleDialog.superclass.initDefaultConfig.call(this);

	// Add dialog config properties //
	this.cfg.addProperty("icon",	{ value:"none",	handler:this.configIcon, suppressEvent:true } );
	this.cfg.addProperty("text",	{ value:"", handler:this.configText, suppressEvent:true, supercedes:["icon"] } );
}


/**
* The SimpleDialog initialization method, which is executed for SimpleDialog and all of its subclasses. This method is automatically called by the constructor, and  sets up all DOM references for pre-existing markup, and creates required markup if it is not already present.
* @param {string}	el	The element ID representing the SimpleDialog <em>OR</em>
* @param {Element}	el	The element representing the SimpleDialog
* @param {object}	userConfig	The configuration object literal containing the configuration that should be set for this SimpleDialog. See configuration documentation for more details.
*/
YAHOO.widget.SimpleDialog.prototype.init = function(el, userConfig) {
	YAHOO.widget.SimpleDialog.superclass.init.call(this, el/*, userConfig*/);  // Note that we don't pass the user config in here yet because we only want it executed once, at the lowest subclass level

	this.beforeInitEvent.fire(YAHOO.widget.SimpleDialog);

	YAHOO.util.Dom.addClass(this.element, YAHOO.widget.SimpleDialog.CSS_SIMPLEDIALOG);

	this.cfg.queueProperty("postmethod", "manual");

	if (userConfig) {
		this.cfg.applyConfig(userConfig, true);
	}

	this.beforeRenderEvent.subscribe(function() {
		if (! this.body) {
			this.setBody("");
		}
	}, this, true);

	this.initEvent.fire(YAHOO.widget.SimpleDialog);

}
/**
* Prepares the SimpleDialog's internal FORM object, creating one if one is not currently present, and adding the value hidden field.
*/
YAHOO.widget.SimpleDialog.prototype.registerForm = function() {
	YAHOO.widget.SimpleDialog.superclass.registerForm.call(this);
	this.form.innerHTML += "<input type=\"hidden\" name=\"" + this.id + "\" value=\"\"/>";
}

// BEGIN BUILT-IN PROPERTY EVENT HANDLERS //

/**
* Fired when the "icon" property is set.
*/
YAHOO.widget.SimpleDialog.prototype.configIcon = function(type,args,obj) {
	var icon = args[0];
	if (icon && icon != "none") {
		var iconHTML = "<img src=\"" + this.imageRoot + icon + "\" class=\"icon\" />";
		this.body.innerHTML = iconHTML + this.body.innerHTML;
	}
}

/**
* Fired when the "text" property is set.
*/
YAHOO.widget.SimpleDialog.prototype.configText = function(type,args,obj) {
	var text = args[0];
	if (text) {
		this.setBody(text);
		this.cfg.refireEvent("icon");
	}
}
// END BUILT-IN PROPERTY EVENT HANDLERS //

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.SimpleDialog.prototype.toString = function() {
	return "SimpleDialog " + this.id;
}

/**
* @class
* ContainerEffect encapsulates animation transitions that are executed when an Overlay is shown or hidden.
* @param {Overlay}	overlay		The Overlay that the animation should be associated with
* @param {object}	attrIn		The object literal representing the animation arguments to be used for the animate-in transition. The arguments for this literal are: attributes(object, see YAHOO.util.Anim for description), duration(float), and method(i.e. YAHOO.util.Easing.easeIn).
* @param {object}	attrOut		The object literal representing the animation arguments to be used for the animate-out transition. The arguments for this literal are: attributes(object, see YAHOO.util.Anim for description), duration(float), and method(i.e. YAHOO.util.Easing.easeIn).
* @param {Element}	targetElement	Optional. The target element that should be animated during the transition. Defaults to overlay.element.
* @param {class}	Optional. The animation class to instantiate. Defaults to YAHOO.util.Anim. Other options include YAHOO.util.Motion.
* @constructor
*/
YAHOO.widget.ContainerEffect = function(overlay, attrIn, attrOut, targetElement, animClass) {
	if (! animClass) {
		animClass = YAHOO.util.Anim;
	}

	/**
	* The overlay to animate
	*/
	this.overlay = overlay;
	/**
	* The animation attributes to use when transitioning into view
	*/
	this.attrIn = attrIn;
	/**
	* The animation attributes to use when transitioning out of view
	*/
	this.attrOut = attrOut;
	/**
	* The target element to be animated
	*/
	this.targetElement = targetElement || overlay.element;
	/**
	* The animation class to use for animating the overlay
	*/
	this.animClass = animClass;
}

/**
* Initializes the animation classes and events.
*/
YAHOO.widget.ContainerEffect.prototype.init = function() {
	this.beforeAnimateInEvent = new YAHOO.util.CustomEvent("beforeAnimateIn");
	this.beforeAnimateOutEvent = new YAHOO.util.CustomEvent("beforeAnimateOut");

	this.animateInCompleteEvent = new YAHOO.util.CustomEvent("animateInComplete");
	this.animateOutCompleteEvent = new YAHOO.util.CustomEvent("animateOutComplete");

	this.animIn = new this.animClass(this.targetElement, this.attrIn.attributes, this.attrIn.duration, this.attrIn.method);
	this.animIn.onStart.subscribe(this.handleStartAnimateIn, this);
	this.animIn.onTween.subscribe(this.handleTweenAnimateIn, this);
	this.animIn.onComplete.subscribe(this.handleCompleteAnimateIn, this);

	this.animOut = new this.animClass(this.targetElement, this.attrOut.attributes, this.attrOut.duration, this.attrOut.method);
	this.animOut.onStart.subscribe(this.handleStartAnimateOut, this);
	this.animOut.onTween.subscribe(this.handleTweenAnimateOut, this);
	this.animOut.onComplete.subscribe(this.handleCompleteAnimateOut, this);
}

/**
* Triggers the in-animation.
*/
YAHOO.widget.ContainerEffect.prototype.animateIn = function() {
	this.beforeAnimateInEvent.fire();
	this.animIn.animate();
}

/**
* Triggers the out-animation.
*/
YAHOO.widget.ContainerEffect.prototype.animateOut = function() {
	this.beforeAnimateOutEvent.fire();
	this.animOut.animate();
}

/**
* The default onStart handler for the in-animation.
*/
YAHOO.widget.ContainerEffect.prototype.handleStartAnimateIn = function(type, args, obj) { }
/**
* The default onTween handler for the in-animation.
*/
YAHOO.widget.ContainerEffect.prototype.handleTweenAnimateIn = function(type, args, obj) { }
/**
* The default onComplete handler for the in-animation.
*/
YAHOO.widget.ContainerEffect.prototype.handleCompleteAnimateIn = function(type, args, obj) { }

/**
* The default onStart handler for the out-animation.
*/
YAHOO.widget.ContainerEffect.prototype.handleStartAnimateOut = function(type, args, obj) { }
/**
* The default onTween handler for the out-animation.
*/
YAHOO.widget.ContainerEffect.prototype.handleTweenAnimateOut = function(type, args, obj) { }
/**
* The default onComplete handler for the out-animation.
*/
YAHOO.widget.ContainerEffect.prototype.handleCompleteAnimateOut = function(type, args, obj) { }

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.ContainerEffect.prototype.toString = function() {
	var output = "ContainerEffect";
	if (this.overlay) {
		output += " [" + this.overlay.toString() + "]";
	}
	return output;
}

/**
* A pre-configured ContainerEffect instance that can be used for fading an overlay in and out.
* @param {Overlay}	The Overlay object to animate
* @param {float}	The duration of the animation
* @type ContainerEffect
*/
YAHOO.widget.ContainerEffect.FADE = function(overlay, dur) {
	var fade = new YAHOO.widget.ContainerEffect(overlay, { attributes:{opacity: {from:0, to:1}}, duration:dur, method:YAHOO.util.Easing.easeIn }, { attributes:{opacity: {to:0}}, duration:dur, method:YAHOO.util.Easing.easeOut}, overlay.element );

	fade.handleStartAnimateIn = function(type,args,obj) {
		YAHOO.util.Dom.addClass(obj.overlay.element, "hide-select");
		
		if (! obj.overlay.underlay) {
			obj.overlay.cfg.refireEvent("underlay");
		}

		if (obj.overlay.underlay) {
			obj.initialUnderlayOpacity = YAHOO.util.Dom.getStyle(obj.overlay.underlay, "opacity");
			obj.overlay.underlay.style.filter = null;
		}

		YAHOO.util.Dom.setStyle(obj.overlay.element, "visibility", "visible"); 
		YAHOO.util.Dom.setStyle(obj.overlay.element, "opacity", 0);
	}

	fade.handleCompleteAnimateIn = function(type,args,obj) {
		YAHOO.util.Dom.removeClass(obj.overlay.element, "hide-select");

		if (obj.overlay.element.style.filter) {
			obj.overlay.element.style.filter = null;
		}			
		
		if (obj.overlay.underlay) {
			YAHOO.util.Dom.setStyle(obj.overlay.underlay, "opacity", obj.initialUnderlayOpacity);
		}

		obj.overlay.cfg.refireEvent("iframe");
		obj.animateInCompleteEvent.fire();
	}

	fade.handleStartAnimateOut = function(type, args, obj) {
		YAHOO.util.Dom.addClass(obj.overlay.element, "hide-select");

		if (obj.overlay.underlay) {
			obj.overlay.underlay.style.filter = null;
		}
	}

	fade.handleCompleteAnimateOut =  function(type, args, obj) { 
		YAHOO.util.Dom.removeClass(obj.overlay.element, "hide-select");
		if (obj.overlay.element.style.filter) {
			obj.overlay.element.style.filter = null;
		}				
		YAHOO.util.Dom.setStyle(obj.overlay.element, "visibility", "hidden");
		YAHOO.util.Dom.setStyle(obj.overlay.element, "opacity", 1); 

		obj.overlay.cfg.refireEvent("iframe");

		obj.animateOutCompleteEvent.fire();
	};	

	fade.init();
	return fade;
};


/**
* A pre-configured ContainerEffect instance that can be used for sliding an overlay in and out.
* @param {Overlay}	The Overlay object to animate
* @param {float}	The duration of the animation
* @type ContainerEffect
*/
YAHOO.widget.ContainerEffect.SLIDE = function(overlay, dur) {
	var x = overlay.cfg.getProperty("x") || YAHOO.util.Dom.getX(overlay.element);
	var y = overlay.cfg.getProperty("y") || YAHOO.util.Dom.getY(overlay.element);

	var clientWidth = YAHOO.util.Dom.getClientWidth();
	var offsetWidth = overlay.element.offsetWidth;

	var slide = new YAHOO.widget.ContainerEffect(overlay, { 
															attributes:{ points: { to:[x, y] } }, 
															duration:dur, 
															method:YAHOO.util.Easing.easeIn 
														}, 
														{ 
															attributes:{ points: { to:[(clientWidth+25), y] } },
															duration:dur, 
															method:YAHOO.util.Easing.easeOut
														},
														overlay.element,
														YAHOO.util.Motion
												);

	slide.handleStartAnimateIn = function(type,args,obj) {
		obj.overlay.element.style.left = (-25-offsetWidth) + "px";
		obj.overlay.element.style.top  = y + "px";
	}
	
	slide.handleTweenAnimateIn = function(type, args, obj) {


		var pos = YAHOO.util.Dom.getXY(obj.overlay.element);

		var currentX = pos[0];
		var currentY = pos[1];

		if (YAHOO.util.Dom.getStyle(obj.overlay.element, "visibility") == "hidden" && currentX < x) {
			YAHOO.util.Dom.setStyle(obj.overlay.element, "visibility", "visible");
		}

		obj.overlay.cfg.setProperty("xy", [currentX,currentY], true);
		obj.overlay.cfg.refireEvent("iframe");
	}
	
	slide.handleCompleteAnimateIn = function(type, args, obj) {
		obj.overlay.cfg.setProperty("xy", [x,y], true);
		obj.startX = x;
		obj.startY = y;
		obj.overlay.cfg.refireEvent("iframe");
		obj.animateInCompleteEvent.fire();
	}

	slide.handleStartAnimateOut = function(type, args, obj) {
		var clientWidth = YAHOO.util.Dom.getViewportWidth();
		
		var pos = YAHOO.util.Dom.getXY(obj.overlay.element);

		var x = pos[0];
		var y = pos[1];

		var currentTo = obj.animOut.attributes.points.to;
		obj.animOut.attributes.points.to = [(clientWidth+25), y];
	}

	slide.handleTweenAnimateOut = function(type, args, obj) {
		var pos = YAHOO.util.Dom.getXY(obj.overlay.element);

		var x = pos[0];
		var y = pos[1];

		obj.overlay.cfg.setProperty("xy", [x,y], true);
		obj.overlay.cfg.refireEvent("iframe");
	}

	slide.handleCompleteAnimateOut = function(type, args, obj) { 
		YAHOO.util.Dom.setStyle(obj.overlay.element, "visibility", "hidden");		
		var offsetWidth = obj.overlay.element.offsetWidth;

		obj.overlay.cfg.setProperty("xy", [x,y]);
		obj.animateOutCompleteEvent.fire();
	};	

	slide.init();
	return slide;
}
