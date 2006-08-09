/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
Version 0.11.0
*/


/**
* @class The superclass of all menu containers.
* @constructor
* @extends YAHOO.widget.Overlay
* @base YAHOO.widget.Overlay
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a MenuModule instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.MenuModule = function(p_oElement, p_oConfig) {

    YAHOO.widget.MenuModule.superclass.constructor.call(
        this, 
        p_oElement, 
        p_oConfig
    );

};

YAHOO.extend(YAHOO.widget.MenuModule, YAHOO.widget.Overlay);


// Constants

/**
* Constant representing the CSS class(es) to be applied to the root 
* HTMLDivElement of the MenuModule instance.
* @final
* @type String
*/
YAHOO.widget.MenuModule.prototype.CSS_CLASS_NAME = "yuimenu";


/**
* Constant representing the type of item to instantiate and add when parsing 
* the child nodes (either HTMLLIElement, HTMLOptGroupElement or 
* HTMLOptionElement) of a menu's DOM.  The default 
* is YAHOO.widget.MenuModuleItem.
* @final
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype.ITEM_TYPE = null;


/**
* Constant representing the tagname of the HTMLElement used to title 
* a group of items.
* @final
* @type String
*/
YAHOO.widget.MenuModule.prototype.GROUP_TITLE_TAG_NAME = "H6";


// Private properties

/**
* Array of HTMLElements used to title groups of items.
* @private
* @type {Array}
*/
YAHOO.widget.MenuModule.prototype._aGroupTitleElements = null;


/**
* Multi-dimensional array of items.
* @private
* @type {Array}
*/
YAHOO.widget.MenuModule.prototype._aItemGroups = null;


/**
* An array of HTMLUListElements, each of which is the parent node of each 
* items's HTMLLIElement node.
* @private
* @type {Array}
*/
YAHOO.widget.MenuModule.prototype._aListElements = null;


/**
* Reference to the Event utility singleton.
* @private
* @type {YAHOO.util.Event}
*/
YAHOO.widget.MenuModule.prototype._oEventUtil = YAHOO.util.Event;


/**
* Reference to the Dom utility singleton.
* @private
* @type {YAHOO.util.Dom}
*/
YAHOO.widget.MenuModule.prototype._oDom = YAHOO.util.Dom;


/**
* Reference to the item the mouse is currently over.
* @private
* @type {YAHOO.widget.MenuModuleItem}
*/
YAHOO.widget.MenuModule.prototype._oCurrentItem = null;


/** 
* The current state of a MenuModule instance's "mouseover" event
* @private
* @type {Boolean}
*/
YAHOO.widget.MenuModule.prototype._bFiredMouseOverEvent = false;


/** 
* The current state of a MenuModule instance's "mouseout" event
* @private
* @type {Boolean}
*/
YAHOO.widget.MenuModule.prototype._bFiredMouseOutEvent = false;


// Public properties

/**
* Reference to the item that has focus.
* @private
* @type {YAHOO.widget.MenuModuleItem}
*/
YAHOO.widget.MenuModule.prototype.activeItem = null;


/**
* Returns a MenuModule instance's parent object.
* @type {YAHOO.widget.MenuModuleItem}
*/
YAHOO.widget.MenuModule.prototype.parent = null;


/**
* Returns the HTMLElement (either HTMLSelectElement or HTMLDivElement)
* used create the MenuModule instance.
* @type {HTMLSelectElement/HTMLDivElement}
*/
YAHOO.widget.MenuModule.prototype.srcElement = null;


// Events

/**
* Fires when the mouse has entered a MenuModule instance.  Passes back the 
* DOM Event object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.mouseOverEvent = null;


/**
* Fires when the mouse has left a MenuModule instance.  Passes back the DOM 
* Event object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.mouseOutEvent = null;


/**
* Fires when the user mouses down on a MenuModule instance.  Passes back the 
* DOM Event object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.mouseDownEvent = null;


/**
* Fires when the user releases a mouse button while the mouse is over 
* a MenuModule instance.  Passes back the DOM Event object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.mouseUpEvent = null;


/**
* Fires when the user clicks the on a MenuModule instance.  Passes back the 
* DOM Event object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.clickEvent = null;


/**
* Fires when the user presses an alphanumeric key.  Passes back the 
* DOM Event object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.keyPressEvent = null;


/**
* Fires when the user presses a key.  Passes back the DOM Event 
* object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.keyDownEvent = null;


/**
* Fires when the user releases a key.  Passes back the DOM Event 
* object as an argument.
* @type {YAHOO.util.CustomEvent}
* @see YAHOO.util.CustomEvent
*/
YAHOO.widget.MenuModule.prototype.keyUpEvent = null;


/**
* The MenuModule class's initialization method. This method is automatically 
* called  by the constructor, and sets up all DOM references for 
* pre-existing markup, and creates required markup if it is not already present.
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a MenuModule instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.MenuModule.prototype.init = function(p_oElement, p_oConfig) {

    var Dom = this._oDom;
    var Event = this._oEventUtil;


    if(!this.ITEM_TYPE) {

        this.ITEM_TYPE = YAHOO.widget.MenuModuleItem;

    }


    this._aItemGroups = [];
    this._aListElements = [];
    this._aGroupTitleElements = [];


    var oElement;

    if(typeof p_oElement == "string") {

        oElement = document.getElementById(p_oElement);

    }
    else if(p_oElement.tagName) {

        oElement = p_oElement;

    }


    if(oElement) {

        switch(oElement.tagName) {
    
            case "DIV":

                this.srcElement = oElement;

                /* 
                    Note: we don't pass the user config in here yet 
                    because we only want it executed once, at the lowest 
                    subclass level.
                */ 
            
                YAHOO.widget.MenuModule.superclass.init.call(this, oElement);

                this.beforeInitEvent.fire(YAHOO.widget.MenuModule);


                /*
                    Populate the collection of item groups and item
                    group titles
                */

                var oNode = this.body.firstChild;
                var i = 0;

                do {

                    switch(oNode.tagName) {

                        case this.GROUP_TITLE_TAG_NAME:
                        
                            this._aGroupTitleElements[i] = oNode;

                        break;

                        case "UL":

                            this._aListElements[i] = oNode;
                            this._aItemGroups[i] = [];
                            i++;

                        break;

                    }

                }
                while((oNode = oNode.nextSibling));


                /*
                    Apply the "first-of-type" class to the first UL to mimic 
                    the "first-of-type" CSS3 psuedo class.
                */

                if(this._aListElements[0]) {

                    Dom.addClass(this._aListElements[0], "first-of-type");

                }

                this.logger = new YAHOO.widget.LogWriter(this.toString());

                this.logger.log("Source element: " + this.srcElement.tagName);
    
            break;
    
            case "SELECT":
    
                this.srcElement = oElement;
    
    
                /*
                    The source element is not something that we can use 
                    outright, so we need to create a new Overlay
                */
    
                var sId = Dom.generateId();

                /* 
                    Note: we don't pass the user config in here yet 
                    because we only want it executed once, at the lowest 
                    subclass level.
                */ 
            
                YAHOO.widget.MenuModule.superclass.init.call(this, sId); 

                this.beforeInitEvent.fire(YAHOO.widget.MenuModule);

                this.logger = new YAHOO.widget.LogWriter(this.toString());

                this.logger.log("Source element: " + this.srcElement.tagName);

            break;
    
        }

    }
    else {

        /* 
            Note: we don't pass the user config in here yet 
            because we only want it executed once, at the lowest 
            subclass level.
        */ 
    
        YAHOO.widget.MenuModule.superclass.init.call(this, p_oElement);

        this.beforeInitEvent.fire(YAHOO.widget.MenuModule);

        this.logger = new YAHOO.widget.LogWriter(this.toString());

        this.logger.log("No source element found.  " +
            "Created element with id: " + this.id);

    }


    if(this.element) {

        var oEl = this.element;
        var CustomEvent = YAHOO.util.CustomEvent;

        Dom.addClass(oEl, this.CSS_CLASS_NAME);

        // Assign DOM event handlers

        Event.addListener(
                oEl, 
                "mouseover", 
                this._onElementMouseOver, 
                this, 
                true
            );

        Event.addListener(oEl, "mouseout", this._onElementMouseOut, this, true);
        Event.addListener(oEl, "mousedown", this._onDOMEvent, this, true);
        Event.addListener(oEl, "mouseup", this._onDOMEvent, this, true);
        Event.addListener(oEl, "click", this._onElementClick, this, true);
        Event.addListener(oEl, "keydown", this._onDOMEvent, this, true);
        Event.addListener(oEl, "keyup", this._onDOMEvent, this, true);
        Event.addListener(oEl, "keypress", this._onDOMEvent, this, true);


        // Create custom events

        this.mouseOverEvent = new CustomEvent("mouseOverEvent", this);
        this.mouseOutEvent = new CustomEvent("mouseOutEvent", this);
        this.mouseDownEvent = new CustomEvent("mouseDownEvent", this);
        this.mouseUpEvent = new CustomEvent("mouseUpEvent", this);
        this.clickEvent = new CustomEvent("clickEvent", this);
        this.keyPressEvent = new CustomEvent("keyPressEvent", this);
        this.keyDownEvent = new CustomEvent("keyDownEvent", this);
        this.keyUpEvent = new CustomEvent("keyUpEvent", this);


        // Subscribe to Custom Events

        this.beforeRenderEvent.subscribe(this._onBeforeRender, this, true);
        this.renderEvent.subscribe(this._onRender, this, true);
        this.showEvent.subscribe(this._onShow, this, true);
        this.beforeHideEvent.subscribe(this._onBeforeHide, this, true);


        if(p_oConfig) {
    
            this.cfg.applyConfig(p_oConfig, true);
    
        }


        this.cfg.queueProperty("visible", false);


        if(this.srcElement) {

            this._initSubTree();

        }

    }


    this.initEvent.fire(YAHOO.widget.MenuModule);

};


// Private methods

/**
* Iterates the source element's childNodes collection and uses the child 
* nodes to instantiate MenuModule and MenuModuleItem instances.
* @private
*/
YAHOO.widget.MenuModule.prototype._initSubTree = function() {

    var oNode;

    this.logger.log("Searching DOM for items to initialize.");

    switch(this.srcElement.tagName) {

        case "DIV":

            if(this._aListElements.length > 0) {

                this.logger.log("Found " + 
                    this._aListElements.length + " item groups to initialize.");

                var i = this._aListElements.length - 1;

                do {

                    oNode = this._aListElements[i].firstChild;
    
                    this.logger.log("Scanning " + 
                        this._aListElements[i].childNodes.length + 
                        " child nodes for items to initialize.");

                    do {
    
                        switch(oNode.tagName) {
        
                            case "LI":

                                this.logger.log("Initializing " + 
                                    oNode.tagName + " node.");

                                this.addItem(new this.ITEM_TYPE(oNode), i);
        
                            break;
        
                        }
            
                    }
                    while((oNode = oNode.nextSibling));
            
                }
                while(i--);

            }

        break;

        case "SELECT":

            this.logger.log("Scanning " +  this.srcElement.childNodes.length + 
                " child nodes for items to initialize.");

            oNode = this.srcElement.firstChild;

            do {

                switch(oNode.tagName) {

                    case "OPTGROUP":
                    case "OPTION":

                        this.logger.log("Initializing " +  
                            oNode.tagName + " node.");

                        this.addItem(new this.ITEM_TYPE(oNode));

                    break;

                }

            }
            while((oNode = oNode.nextSibling));

        break;

    }

};


/**
* Returns the first enabled item in a menu instance.
* @return Returns a MenuModuleItem instance.
* @type YAHOO.widget.MenuModuleItem
* @private
*/
YAHOO.widget.MenuModule.prototype._getFirstEnabledItem = function() {

    var nGroups = this._aItemGroups.length;
    var oItem;
    var aItemGroup;

    for(var i=0; i<nGroups; i++) {

        aItemGroup = this._aItemGroups[i];
        
        if(aItemGroup) {

            var nItems = aItemGroup.length;
            
            for(var n=0; n<nItems; n++) {
            
                oItem = aItemGroup[n];
                
                if(!oItem.cfg.getProperty("disabled")) {
                
                    return oItem;
                
                }
    
                oItem = null;
    
            }
        
        }
    
    }
    
};


/**
* Determines if the value is one of the supported positions.
* @private
* @param {Object} p_sPosition The object to be evaluated.
* @return Returns true if the position is supported.
* @type Boolean
*/
YAHOO.widget.MenuModule.prototype._checkPosition = function(p_sPosition) {

    if(typeof p_sPosition == "string") {

        var sPosition = p_sPosition.toLowerCase();

        return ("dynamic,static".indexOf(sPosition) != -1);

    }

};


/**
* Adds an item to a group.
* @private
* @param {Number} p_nGroupIndex Number indicating the group to which
* the item belongs.
* @param {YAHOO.widget.MenuModuleItem} p_oItem The item to be added.
* @param {Number} p_nItemIndex Optional. Index at which the item 
* should be added.
* @return The item that was added.
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype._addItemToGroup = 

    function(p_nGroupIndex, p_oItem, p_nItemIndex) {

        var Dom = this._oDom;
        var oItem;

        if(p_oItem instanceof this.ITEM_TYPE) {

            oItem = p_oItem;     

        }
        else if(typeof p_oItem == "string") {

            oItem = new this.ITEM_TYPE(p_oItem);
        
        }


        if(oItem) {
        
            var nGroupIndex = typeof p_nGroupIndex == "number" ? 
                    p_nGroupIndex : 0;
            
            var aGroup = this._getItemGroup(nGroupIndex);
            
            var oGroupItem;
    

            if(!aGroup) {
    
                aGroup = this._createItemGroup(nGroupIndex);
    
            }


            if(typeof p_nItemIndex == "number") {
    
                var bAppend = (p_nItemIndex >= aGroup.length);            
    

                if(aGroup[p_nItemIndex]) {
        
                    aGroup.splice(p_nItemIndex, 0, oItem);
        
                }
                else {
        
                    aGroup[p_nItemIndex] = oItem;
        
                }
    
    
                oGroupItem = aGroup[p_nItemIndex];
    
                if(oGroupItem) {
    
                    if(bAppend && !oGroupItem.element.parentNode) {
            
                        this._aListElements[nGroupIndex].appendChild(
                            oGroupItem.element
                        );
        
                    }
                    else {
      
        
                        /**
                        * Returns the next sibling of an item in an array 
                        * @param {p_aArray} An array
                        * @param {p_nStartIndex} The index to start searching
                        * the array 
                        * @ignore
                        * @return Returns an item in an array
                        * @type Object 
                        */
                        function getNextItemSibling(p_aArray, p_nStartIndex) {
                
                            return (
                                    p_aArray[p_nStartIndex] || 
                                    getNextItemSibling(
                                        p_aArray, 
                                        (p_nStartIndex+1)
                                    )
                                );
                
                        }
        
        
                        var oNextItemSibling = 
                                getNextItemSibling(aGroup, (p_nItemIndex+1));
        
                        if(oNextItemSibling && !oGroupItem.element.parentNode) {
                
                            this._aListElements[nGroupIndex].insertBefore(
                                    oGroupItem.element, 
                                    oNextItemSibling.element
                                );
            
                        }
        
                    }
        
    
                    oGroupItem.parent = this;
            
                    this._subscribeToItemEvents(oGroupItem);
        
                    this._configureItemSubmenuModule(oGroupItem);
                    
                    this._updateItemProperties(nGroupIndex);
            
                    this.logger.log("Item inserted." + 
                        " Text: " + oGroupItem.cfg.getProperty("text") + ", " + 
                        " Index: " + oGroupItem.index + ", " + 
                        " Group Index: " + oGroupItem.groupIndex);

                    return oGroupItem;
        
                }
    
            }
            else {
        
                var nItemIndex = aGroup.length;
        
                aGroup[nItemIndex] = oItem;
        
        
                oGroupItem = aGroup[nItemIndex];
        
                if(oGroupItem) {
        
                    if(
                        !Dom.isAncestor(
                            this._aListElements[nGroupIndex], 
                            oGroupItem.element
                        )
                    ) {
        
                        this._aListElements[nGroupIndex].appendChild(
                            oGroupItem.element
                        );
        
                    }
        
                    oGroupItem.element.setAttribute("groupindex", nGroupIndex);
                    oGroupItem.element.setAttribute("index", nItemIndex);
            
                    oGroupItem.parent = this;
        
                    oGroupItem.index = nItemIndex;
                    oGroupItem.groupIndex = nGroupIndex;
            
                    this._subscribeToItemEvents(oGroupItem);
        
                    this._configureItemSubmenuModule(oGroupItem);
        
                    if(nItemIndex === 0) {
            
                        Dom.addClass(oGroupItem.element, "first-of-type");
            
                    }

                    this.logger.log("Item added." + 
                        " Text: " + oGroupItem.cfg.getProperty("text") + ", " + 
                        " Index: " + oGroupItem.index + ", " + 
                        " Group Index: " + oGroupItem.groupIndex);
            
                    return oGroupItem;
        
                }
        
            }

        }
    
    };


/**
* Removes an item from a group by index.
* @private
* @param {Number} p_nGroupIndex Number indicating the group to which
* the item belongs.
* @param {Number} p_nItemIndex Number indicating the index of the item to  
* be removed.
* @return The item that was removed.
* @type YAHOO.widget.MenuModuleItem
*/    
YAHOO.widget.MenuModule.prototype._removeItemFromGroupByIndex = 

    function(p_nGroupIndex, p_nItemIndex) {

        var nGroupIndex = typeof p_nGroupIndex == "number" ? p_nGroupIndex : 0;
        var aGroup = this._getItemGroup(nGroupIndex);
    
        if(aGroup) {
    
            var aArray = aGroup.splice(p_nItemIndex, 1);
            var oItem = aArray[0];
        
            if(oItem) {
        
                // Update the index and className properties of each member        
                
                this._updateItemProperties(nGroupIndex);
        
                if(aGroup.length === 0) {
        
                    // Remove the UL
        
                    var oUL = this._aListElements[nGroupIndex];
        
                    if(this.body && oUL) {
        
                        this.body.removeChild(oUL);
        
                    }
        
                    // Remove the group from the array of items
        
                    this._aItemGroups.splice(nGroupIndex, 1);
        
        
                    // Remove the UL from the array of ULs
        
                    this._aListElements.splice(nGroupIndex, 1);
        
        
                    /*
                         Assign the "first-of-type" class to the new first UL 
                         in the collection
                    */
        
                    oUL = this._aListElements[0];
        
                    if(oUL) {
        
                        this._oDom.addClass(oUL, "first-of-type");
        
                    }            
        
                }
        
        
                // Return a reference to the item that was removed
            
                return oItem;
        
            }
    
        }
    
    };


/**
* Removes a item from a group by reference.
* @private
* @param {Number} p_nGroupIndex Number indicating the group to which
* the item belongs.
* @param {YAHOO.widget.MenuModuleItem} p_oItem The item to be removed.
* @return The item that was removed.
* @type YAHOO.widget.MenuModuleItem
*/    
YAHOO.widget.MenuModule.prototype._removeItemFromGroupByValue =

    function(p_nGroupIndex, p_oItem) {

        var aGroup = this._getItemGroup(p_nGroupIndex);

        if(aGroup) {

            var nItems = aGroup.length;
            var nItemIndex = -1;
        
            if(nItems > 0) {
        
                var i = nItems-1;
            
                do {
            
                    if(aGroup[i] == p_oItem) {
            
                        nItemIndex = i;
                        break;    
            
                    }
            
                }
                while(i--);
            
                if(nItemIndex > -1) {
            
                    return this._removeItemFromGroupByIndex(
                                p_nGroupIndex, 
                                nItemIndex
                            );
            
                }
        
            }
        
        }
    
    };


/**
* Updates the index, groupindex, and className properties of the items
* in the specified group. 
* @private
* @param {Number} p_nGroupIndex Number indicating the group of items to update.
*/
YAHOO.widget.MenuModule.prototype._updateItemProperties = 

    function(p_nGroupIndex) {

        var aGroup = this._getItemGroup(p_nGroupIndex);
        var nItems = aGroup.length;
    
        if(nItems > 0) {
    
            var Dom = this._oDom;
            var i = nItems - 1;
            var oItem;
            var oLI;
    
            // Update the index and className properties of each member        
        
            do {
    
                oItem = aGroup[i];
    
                if(oItem) {
        
                    oLI = oItem.element;
    
                    oItem.index = i;
                    oItem.groupIndex = p_nGroupIndex;
    
                    oLI.setAttribute("groupindex", p_nGroupIndex);
                    oLI.setAttribute("index", i);
    
                    Dom.removeClass(oLI, "first-of-type");
    
                }
        
            }
            while(i--);
    
    
            if(oLI) {
    
                Dom.addClass(oLI, "first-of-type");
    
            }
    
        }
    
    };


/**
* Creates a new item group (array) and it's associated HTMLUlElement node 
* @private
* @param {Number} p_nIndex Number indicating the group to create.
* @return An item group.
* @type Array
*/
YAHOO.widget.MenuModule.prototype._createItemGroup = function(p_nIndex) {

    if(!this._aItemGroups[p_nIndex]) {

        this._aItemGroups[p_nIndex] = [];

        var oUL = document.createElement("ul");

        this._aListElements[p_nIndex] = oUL;

        return this._aItemGroups[p_nIndex];

    }

};


/**
* Returns the item group at the specified index.
* @private
* @param {Number} p_nIndex Number indicating the index of the item group to
* be retrieved.
* @return An array of items.
* @type Array
*/
YAHOO.widget.MenuModule.prototype._getItemGroup = function(p_nIndex) {

    var nIndex = ((typeof p_nIndex == "number") ? p_nIndex : 0);

    return this._aItemGroups[nIndex];

};


/**
* Subscribe's a MenuModule instance to it's parent MenuModule instance's events.
* @private
* @param {YAHOO.widget.MenuModuleItem} p_oItem The item to listen
* for events on.
*/
YAHOO.widget.MenuModule.prototype._configureItemSubmenuModule = 

    function(p_oItem) {

        var oSubmenu = p_oItem.cfg.getProperty("submenu");
    
        if(oSubmenu) {
    
            /*
                Listen for configuration changes to the parent MenuModule 
                instance so they they can be applied to the submenu.
            */
    
            this.cfg.configChangedEvent.subscribe(
                this._onParentMenuModuleConfigChange, 
                oSubmenu, 
                true
            );
            
            this.renderEvent.subscribe(
                this._onParentMenuModuleRender,
                oSubmenu, 
                true
            );
    
            oSubmenu.beforeShowEvent.subscribe(
                this._onSubmenuBeforeShow, 
                oSubmenu, 
                true
            );
    
            oSubmenu.showEvent.subscribe(this._onSubmenuShow, oSubmenu, true);
    
            oSubmenu.hideEvent.subscribe(this._onSubmenuHide, oSubmenu, true);
    
        }

};


/**
* Subscribes a MenuModule instance to the specified item's Custom Events.
* @private
* @param {YAHOO.widget.MenuModuleItem} p_oItem The item to listen for events on.
*/
YAHOO.widget.MenuModule.prototype._subscribeToItemEvents = function(p_oItem) {

    var aArguments = [this, p_oItem];

    p_oItem.focusEvent.subscribe(this._onItemFocus, aArguments);

    p_oItem.blurEvent.subscribe(this._onItemBlur, aArguments);

    p_oItem.cfg.configChangedEvent.subscribe(
        this._onItemConfigChange,
        aArguments
    );

};


/**
* Returns the offset width of a MenuModule instance.
* @private
*/
YAHOO.widget.MenuModule.prototype._getOffsetWidth = function() {

    var oClone = this.element.cloneNode(true);

    this._oDom.setStyle(oClone, "width", "");

    document.body.appendChild(oClone);

    var sWidth = oClone.offsetWidth;

    document.body.removeChild(oClone);

    return sWidth;

};


/**
* Determines if a DOM event was fired on an item and (if so) fires the item's
* associated Custom Event
* @private
* @param {HTMLElement} p_oElement The original target of the event.
* @param {String} p_sEventType The type/name of the Custom Event to fire.
* @param {Event} p_oDOMEvent The DOM event to pass back when firing the 
* Custom Event.
* @return An item.
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype._fireItemEvent = 

    function(p_oElement, p_sEventType, p_oDOMEvent) {

        var me = this;
    
        /**
        * Returns the specified element's parent HTMLLIElement (&#60;LI&#60;)
        * @param {p_oElement} An HTMLElement node
        * @ignore
        * @return Returns an HTMLElement node
        * @type HTMLElement 
        */
        function getItemElement(p_oElement) {
        
            if(p_oElement == me.element) {
    
                return;
            
            }
            else if(p_oElement.tagName == "LI") {
        
                return p_oElement;
        
            }
            else if(p_oElement.parentNode) {
    
                return getItemElement(p_oElement.parentNode);
        
            }
        
        }
    
    
        var oElement = getItemElement(p_oElement);
    
        if(oElement) {
    
            /*
                Retrieve the item that corresponds to the 
                HTMLLIElement (&#60;LI&#60;) and fire the Custom Event        
            */
    
            var nGroupIndex = parseInt(oElement.getAttribute("groupindex"), 10);
            var nIndex = parseInt(oElement.getAttribute("index"), 10);
            var oItem = this._aItemGroups[nGroupIndex][nIndex];
    
            if(!oItem.cfg.getProperty("disabled")) {
    
                oItem[p_sEventType].fire(p_oDOMEvent);
    
                return oItem;
    
            }
    
        }

    };


// Private DOM event handlers

/**
* Generic event handler for the MenuModule's root HTMLDivElement node.  Used 
* to handle "mousedown," "mouseup," "keydown," "keyup," and "keypress" events.
* @private
* @param {Event} p_oEvent Event object passed back by the event 
* utility (YAHOO.util.Event).
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance 
* corresponding to the HTMLDivElement that fired the event.
*/
YAHOO.widget.MenuModule.prototype._onDOMEvent = 

    function(p_oEvent, p_oMenuModule) {

        var Event = this._oEventUtil;

        // Map of DOM event types to Custom Event types

        var oEventTypes =  {
                "mousedown": "mouseDownEvent",
                "mouseup": "mouseUpEvent",
                "keydown": "keyDownEvent",
                "keyup": "keyUpEvent",
                "keypress": "keyPressEvent"
            };
    
        var sCustomEventType = oEventTypes[p_oEvent.type];
        
        var oTarget = Event.getTarget(p_oEvent);
    
        /*
            Check if the target was an element that is a part of a 
            an item and (if so), fire the associated custom event.
        */
    
        this._fireItemEvent(oTarget, sCustomEventType, p_oEvent);

    
        // Fire the associated custom event for the MenuModule
    
        this[sCustomEventType].fire(p_oEvent);
    
    
        /*
            Stop the propagation of the event at each MenuModule instance
            since menus can be embedded in eachother.
        */
            
        Event.stopPropagation(p_oEvent);

    };


/**
* "mouseover" event handler for the MenuModule's root HTMLDivElement node.
* @private
* @param {Event} p_oEvent Event object passed back by the event
* utility (YAHOO.util.Event).
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance 
* corresponding to the HTMLDivElement that fired the event.
*/
YAHOO.widget.MenuModule.prototype._onElementMouseOver = 

    function(p_oEvent, p_oMenuModule) {

        var Event = this._oEventUtil;
        var oTarget = Event.getTarget(p_oEvent);
    
        if(
            (
                oTarget == this.element || 
                this._oDom.isAncestor(this.element, oTarget)
            )  && 
            !this._bFiredMouseOverEvent
        ) {
    
            // Fire the "mouseover" Custom Event for the MenuModule instance
    
            this.mouseOverEvent.fire(p_oEvent);
    
            this._bFiredMouseOverEvent = true;
            this._bFiredMouseOutEvent = false;
    
        }
    
    
        /*
            Check if the target was an element that is a part of an item
            and (if so), fire the "mouseover" Custom Event.
        */
    
        if(!this._oCurrentItem) {
    
            this._oCurrentItem = 
                this._fireItemEvent(oTarget, "mouseOverEvent", p_oEvent);
    
        }
    
    
        /*
            Stop the propagation of the event at each MenuModule instance
            since menus can be embedded in eachother.
        */
    
        Event.stopPropagation(p_oEvent);

    };


/**
* "mouseout" event handler for the MenuModule's root HTMLDivElement node.
* @private
* @param {Event} p_oEvent Event object passed back by the event
* utility (YAHOO.util.Event).
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance 
* corresponding to the HTMLDivElement that fired the event.
*/
YAHOO.widget.MenuModule.prototype._onElementMouseOut = 

    function(p_oEvent, p_oMenuModule) {

        var Dom = this._oDom;
        var Event = this._oEventUtil;
        var oRelatedTarget = Event.getRelatedTarget(p_oEvent);
        var bLIMouseOut = true;
        var bMovingToSubmenu = false;
            
    
        // Determine where the mouse is going
    
        if(this._oCurrentItem && oRelatedTarget) {
    
            if(
                oRelatedTarget == this._oCurrentItem.element || 
                Dom.isAncestor(this._oCurrentItem.element, oRelatedTarget)
            ) {
    
                bLIMouseOut = false;
    
            }
    
    
            var oSubmenu = this._oCurrentItem.cfg.getProperty("submenu");
    
            if(
                oSubmenu && 
                (
                    oRelatedTarget == oSubmenu.element ||
                    Dom.isAncestor(oSubmenu.element, oRelatedTarget)
                )
            ) {
    
                bMovingToSubmenu = true;
    
            }
    
        }
    
    
        if(this._oCurrentItem && (bLIMouseOut || bMovingToSubmenu)) {
    
            // Fire the "mouseout" Custom Event for the item
    
            this._oCurrentItem.mouseOutEvent.fire(p_oEvent);
    
            this._oCurrentItem = null;
    
        }
    
    
        if(
            !this._bFiredMouseOutEvent && 
            (
                !Dom.isAncestor(this.element, oRelatedTarget) ||
                bMovingToSubmenu
            )
        ) {
    
            // Fire the "mouseout" Custom Event for the MenuModule instance
    
            this.mouseOutEvent.fire(p_oEvent);
    
            this._bFiredMouseOutEvent = true;
            this._bFiredMouseOverEvent = false;
    
        }
    
    
        /*
            Stop the propagation of the event at each MenuModule instance
            since menus can be embedded in eachother.
        */
    
        Event.stopPropagation(p_oEvent);

    };


/**
* "click" event handler for the MenuModule's root HTMLDivElement node.
* @private
* @param {Event} p_oEvent Event object passed back by the 
* event utility (YAHOO.util.Event).
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance 
* corresponding to the HTMLDivElement that fired the event.
*/         
YAHOO.widget.MenuModule.prototype._onElementClick = 

    function(p_oEvent, p_oMenuModule) {

        var Event = this._oEventUtil;
        
        var oTarget = Event.getTarget(p_oEvent);
        
        /*
            Check if the target was a DOM element that is a part of an
            item and (if so), fire the associated "click" 
            Custom Event.
        */
        
        var oItem = this._fireItemEvent(oTarget, "clickEvent", p_oEvent);
        
        var bCurrentPageURL; // Indicates if the URL points to the current page
    
    
        if(oItem) {
    
            var sURL = oItem.cfg.getProperty("url");
            var oSubmenu = oItem.cfg.getProperty("submenu");
            
            bCurrentPageURL = (sURL.substr((sURL.length-1),1) == "#");
    
            /*
                ACCESSIBILITY FEATURE FOR SCREEN READERS: Expand/collapse the
                submenu when the user clicks on the submenu indicator image.
            */        
    
            if(oTarget == oItem.submenuIndicator && oSubmenu) {

                if(oSubmenu.cfg.getProperty("visible")) {
        
                    oSubmenu.hide();
        
                }
                else {

                    var oActiveItem = this.activeItem;
               

                    // Hide any other submenus that might be visible
                
                    if(oActiveItem && oActiveItem != this) {
                
                        this.clearActiveItem();
                
                    }

                    this.activeItem = oItem;
        
                    oItem.cfg.setProperty("selected", true);

                    oSubmenu.show();
        
                }
        
            }
            else if(oTarget.tagName != "A" && !bCurrentPageURL) {
                
                /*
                    Follow the URL of the item regardless of whether or 
                    not the user clicked specifically on the
                    HTMLAnchorElement (&#60;A&#60;) node.
                */
    
                document.location = sURL;
        
            }
        
        }
            
    
        switch(oTarget.tagName) {
        
            case "A":
            
                if(bCurrentPageURL) {
    
                    // Don't follow URLs that are equal to "#"
    
                    Event.preventDefault(p_oEvent);
                
                }
                else {
    
                    /*
                        Break if the anchor's URL is something other than "#" 
                        to prevent the call to "stopPropagation" from be 
                        executed.  This is required for Safari to be able to 
                        follow the URL.
                    */
                
                    break;
                
                }
            
            default:
    
                /*
                    Stop the propagation of the event at each MenuModule 
                    instance since Menus can be embedded in eachother.
                */
    
                Event.stopPropagation(p_oEvent);
            
            break;
        
        }
    
    
        // Fire the associated "click" Custom Event for the MenuModule instance
    
        this.clickEvent.fire(p_oEvent);

    };


// Private Custom Event handlers


/**
* "beforerender" Custom Event handler for a MenuModule instance.  Appends all 
* of the HTMLUListElement (&#60;UL&#60;s) nodes (and their child 
* HTMLLIElement (&#60;LI&#60;)) nodes and their accompanying title nodes to  
* the body of the MenuModule instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuModule.prototype._onBeforeRender = 

    function(p_sType, p_aArgs, p_oMenuModule) {

        var Dom = this._oDom;
        var oConfig = this.cfg;
        var oEl = this.element;
        var nListElements = this._aListElements.length;
    

        if(oConfig.getProperty("position") == "static") {
    
            oConfig.queueProperty("iframe", false);
            oConfig.queueProperty("visible", true);
            
        }
    
    
        if(nListElements > 0) {
    
            var i = 0;
            var bFirstList = true;
            var oUL;
            var oGroupTitle;
    
    
            do {
    
                oUL = this._aListElements[i];
    
                if(oUL) {
    
                    if(bFirstList) {
            
                        Dom.addClass(oUL, "first-of-type");
                        bFirstList = false;
            
                    }
    
    
                    if(!Dom.isAncestor(oEl, oUL)) {
    
                        this.appendToBody(oUL);
    
                    }
    
    
                    oGroupTitle = this._aGroupTitleElements[i];
    
                    if(oGroupTitle) {
    
                        if(!Dom.isAncestor(oEl, oGroupTitle)) {
    
                            oUL.parentNode.insertBefore(oGroupTitle, oUL);
    
                        }
    
    
                        Dom.addClass(oUL, "hastitle");
    
                    }
    
                }
    
                i++;
    
            }
            while(i < nListElements);
    
        }

    };


/**
* "render" Custom Event handler for a MenuModule instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuModule.prototype._onRender = 

    function(p_sType, p_aArgs, p_oMenuModule) {

        if(this.cfg.getProperty("position") == "dynamic") {
    
            var sWidth = this.element.parentNode.tagName == "BODY" ? 
                    this.element.offsetWidth : this._getOffsetWidth();
        
            this.cfg.setProperty("width", (sWidth + "px"));
    
        }

    };


/**
* "show" Custom Event handler for a MenuModule instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuModule.prototype._onShow = 

    function(p_sType, p_aArgs, p_oMenuModule) {
    
        /*
            Setting focus to an item in the newly visible submenu alerts the 
            contents of the submenu to the screen reader.
        */

        this.setInitialFocus();
    
    };


/**
* "hide" Custom Event handler for a MenuModule instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuModule.prototype._onBeforeHide = 

    function(p_sType, p_aArgs, p_oMenuModule) {

        var oActiveItem = this.activeItem;

        if(oActiveItem) {
    
            oActiveItem.blur();

            if(oActiveItem.cfg.getProperty("selected")) {
    
                oActiveItem.cfg.setProperty("selected", false);
    
            }
    
            var oSubmenu = oActiveItem.cfg.getProperty("submenu");
    
            if(oSubmenu && oSubmenu.cfg.getProperty("visible")) {
    
                oSubmenu.hide();
    
            }
    
        }

    };


/**
* "configchange" Custom Event handler for a submenu.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oSubmenu The submenu that subscribed
* to the event.
*/
YAHOO.widget.MenuModule.prototype._onParentMenuModuleConfigChange = 

    function(p_sType, p_aArgs, p_oSubmenu) {
    
        var sPropertyName = p_aArgs[0][0];
        var oPropertyValue = p_aArgs[0][1];
    
        switch(sPropertyName) {
    
            case "iframe":
            case "constraintoviewport":
    
                p_oSubmenu.cfg.setProperty(sPropertyName, oPropertyValue);
                    
            break;        
            
        }
    
    };


/**
* "render" Custom Event handler for a MenuModule instance.  Renders a  
* submenu in response to the firing of it's parent's "render" event.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oSubmenu The submenu that subscribed
* to the event.
*/
YAHOO.widget.MenuModule.prototype._onParentMenuModuleRender = 

    function(p_sType, p_aArgs, p_oSubmenu) {

        /*
            Set the "iframe" and "constraintoviewport" configuration 
            properties to match the parent MenuModule
        */ 
    
        var oParentMenu = p_oSubmenu.parent.parent;
    
        p_oSubmenu.cfg.applyConfig(
        
            {
                constraintoviewport: 
                    oParentMenu.cfg.getProperty("constraintoviewport"),
    
                xy: [0,0],
    
                iframe: oParentMenu.cfg.getProperty("iframe")
    
            }
        
        );
    
    
        if(this._oDom.inDocument(this.element)) {
    
            this.render();
    
        }
        else {
    
            this.render(this.parent.element);
    
        }
    
    };


/**
* "beforeshow" Custom Event handler for a submenu.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oSubmenu The submenu that fired
* the event.
*/
YAHOO.widget.MenuModule.prototype._onSubmenuBeforeShow = 

    function(p_sType, p_aArgs, p_oSubmenu) {
    
        var oParent = this.parent;
        var aAlignment = oParent.parent.cfg.getProperty("submenualignment");

        this.cfg.setProperty(
            "context", 
            [
                oParent.element, 
                aAlignment[0], 
                aAlignment[1]
            ]
        );

        oParent.submenuIndicator.alt = 
            oParent.EXPANDED_SUBMENU_INDICATOR_ALT_TEXT;
    
    };


/**
* "show" Custom Event handler for a submenu.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oSubmenu The submenu that fired
* the event.
*/
YAHOO.widget.MenuModule.prototype._onSubmenuShow = 

    function(p_sType, p_aArgs, p_oSubmenu) {
    
        var oParent = this.parent;

        oParent.submenuIndicator.alt = 
            oParent.EXPANDED_SUBMENU_INDICATOR_ALT_TEXT;
    
    };


/**
* "hide" Custom Event handler for a submenu.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oSubmenu The submenu that fired
* the event.
*/
YAHOO.widget.MenuModule.prototype._onSubmenuHide = 

    function(p_sType, p_aArgs, p_oSubmenu) {
    
        var oParent = this.parent;

        if(oParent.parent.cfg.getProperty("visible")) {

            oParent.cfg.setProperty("selected", false);
    
            oParent.focus();
        
        }

        oParent.submenuIndicator.alt = 
            oParent.COLLAPSED_SUBMENU_INDICATOR_ALT_TEXT;
    
    };


/**
* "focus" YAHOO.util.CustomEvent handler for a MenuModule instance's items.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {Array} p_aObjects Array containing the current MenuModule instance 
* and the item that fired the event.
*/
YAHOO.widget.MenuModule.prototype._onItemFocus = 

    function(p_sType, p_aArgs, p_aObjects) {
    
        var me = p_aObjects[0];
        var oItem = p_aObjects[1];
    
        me.activeItem = oItem;
    
    };


/**
* "blur" YAHOO.util.CustomEvent handler for a MenuModule instance's items.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {Array} p_aObjects Array containing the current MenuModule instance 
* and the item that fired the event.
*/
YAHOO.widget.MenuModule.prototype._onItemBlur = 

    function(p_sType, p_aArgs, p_aObjects) {
    
        var me = p_aObjects[0];
        var oItem = p_aObjects[1];
        var oSubmenu = oItem.cfg.getProperty("submenu");
    
        if(!oSubmenu || (oSubmenu && !oSubmenu.cfg.getProperty("visible"))) {
    
            me.activeItem = null;
    
        }
    
    };


/**
* "configchange" YAHOO.util.CustomEvent handler for the MenuModule 
* instance's items.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the 
* event was fired.
* @param {Array} p_aObjects Array containing the current MenuModule instance 
* and the item that fired the event.
*/
YAHOO.widget.MenuModule.prototype._onItemConfigChange = 

    function(p_sType, p_aArgs, p_aObjects) {

        var me = p_aObjects[0];    
        var sProperty = p_aArgs[0][0];
        var oItem = p_aObjects[1];
    
        switch(sProperty) {
    
            case "submenu":
    
                var oSubmenu = p_aArgs[0][1];
    
                if(oSubmenu) {
    
                    me._configureItemSubmenuModule(oItem);
    
                }
    
            break;
    
            case "text":
            case "helptext":
    
                /*
                    A change to an item's "text" or "helptext"
                    configuration properties requires the width of the parent
                    MenuModule instance to be recalculated.
                */
    
                if(me.element.style.width) {
        
                    var sWidth = me._getOffsetWidth() + "px";
    
                    me._oDom.setStyle(me.element, "width", sWidth);
    
                }
    
            break;
    
        }
    
    };


/**
* The default event handler executed when the moveEvent is fired, if the 
* "constraintoviewport" configuration property is set to true.
*/
YAHOO.widget.MenuModule.prototype.enforceConstraints = 

    function(type, args, obj) {

        var Dom = this._oDom;
        var oConfig = this.cfg;
    
        var pos = args[0];
            
        var x = pos[0];
        var y = pos[1];
        
        var bod = document.getElementsByTagName('body')[0];
        var htm = document.getElementsByTagName('html')[0];
        
        var bodyOverflow = Dom.getStyle(bod, "overflow");
        var htmOverflow = Dom.getStyle(htm, "overflow");
        
        var offsetHeight = this.element.offsetHeight;
        var offsetWidth = this.element.offsetWidth;
        
        var viewPortWidth = Dom.getClientWidth();
        var viewPortHeight = Dom.getClientHeight();
        
        var scrollX = window.scrollX || document.body.scrollLeft;
        var scrollY = window.scrollY || document.body.scrollTop;
        
        var topConstraint = scrollY + 10;
        var leftConstraint = scrollX + 10;
        var bottomConstraint = scrollY + viewPortHeight - offsetHeight - 10;
        var rightConstraint = scrollX + viewPortWidth - offsetWidth - 10;
        
        var aContext = oConfig.getProperty("context");
        var oContextElement = aContext ? aContext[0] : null;
    
    
        if (x < 10) {
    
            x = leftConstraint;
    
        } else if ((x + offsetWidth) > viewPortWidth) {
    
            if(
                oContextElement && 
                ((x - oContextElement.offsetWidth) > offsetWidth)
            ) {
    
                x = (x - (oContextElement.offsetWidth + offsetWidth));
    
            }
            else {
    
                x = rightConstraint;
    
            }
    
        }
    
        if (y < 10) {
    
            y = topConstraint;
    
        } else if (y > bottomConstraint) {
    
            if(oContextElement && (y > offsetHeight)) {
    
                y = ((y + oContextElement.offsetHeight) - offsetHeight);
    
            }
            else {
    
                y = bottomConstraint;
    
            }
    
        }
    
        oConfig.setProperty("x", x, true);
        oConfig.setProperty("y", y, true);
    
    };


// Event handlers for configuration properties

/**
* Event handler for when the "position" configuration property of a
* MenuModule changes.
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance fired
* the event.
* @see YAHOO.widget.Overlay#configIframe
*/
YAHOO.widget.MenuModule.prototype.configPosition = 

    function(p_sType, p_aArgs, p_oMenuModule) {

        var sCSSPosition = p_aArgs[0] == "static" ? "static" : "absolute";
    
        this._oDom.setStyle(this.element, "position", sCSSPosition);
    
    };


// Public methods

YAHOO.widget.MenuModule.prototype.toString = function() {

    return ("Menu " + this.id);

};


/**
* Sets the title of a group of items.
* @param {String} p_sGroupTitle The title of the group.
* @param {Number} p_nGroupIndex Optional. Number indicating the group to which
* the title belongs.
*/
YAHOO.widget.MenuModule.prototype.setItemGroupTitle = 

    function(p_sGroupTitle, p_nGroupIndex) {
        
        if(typeof p_sGroupTitle == "string" && p_sGroupTitle.length > 0) {
    
            var Dom = this._oDom;

            var nGroupIndex = 
                    typeof p_nGroupIndex == "number" ? p_nGroupIndex : 0;
    
            var oTitle = this._aGroupTitleElements[nGroupIndex];
    
    
            if(oTitle) {
    
                oTitle.innerHTML = p_sGroupTitle;
                
            }
            else {
    
                oTitle = document.createElement(this.GROUP_TITLE_TAG_NAME);
                        
                oTitle.innerHTML = p_sGroupTitle;
    
                this._aGroupTitleElements[nGroupIndex] = oTitle;
    
            }
    
    
            var i = this._aGroupTitleElements.length - 1;
            var nFirstIndex;
    
            do {
    
                if(this._aGroupTitleElements[i]) {
    
                    Dom.removeClass(
                        this._aGroupTitleElements[i],
                        "first-of-type"
                    );

                    nFirstIndex = i;
    
                }
    
            }
            while(i--);
    
    
            if(nFirstIndex !== null) {
    
                Dom.addClass(
                    this._aGroupTitleElements[nFirstIndex], 
                    "first-of-type"
                );
    
            }
    
        }
    
    };


/**
* Appends the specified item to a MenuModule instance.
* @param {YAHOO.widget.MenuModuleItem} p_oItem The item to be added.
* @param {Number} p_nGroupIndex Optional. Number indicating the group to which
* the item belongs.
* @return The item that was added to the MenuModule.
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype.addItem = function(p_oItem, p_nGroupIndex) {

    if(p_oItem) {

        return this._addItemToGroup(p_nGroupIndex, p_oItem);
        
    }

};


/**
* Inserts an item into a MenuModule instance at the specified index.
* @param {YAHOO.widget.MenuModuleItem} p_oItem The item to be inserted.
* @param {Number} p_nItemIndex Number indicating the ordinal position 
* at which the item should be added.
* @param {Number} p_nGroupIndex Optional. Number indicating the group to which
* the item belongs.
* @return The item that was inserted into the MenuModule.
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype.insertItem = 

    function(p_oItem, p_nItemIndex, p_nGroupIndex) {
    
        if(p_oItem) {
    
            return this._addItemToGroup(p_nGroupIndex, p_oItem, p_nItemIndex);
    
        }
    
    };


/**
* Removes the specified item from a MenuModule instance.
* @param {YAHOO.widget.MenuModuleItem/Number} p_oObject The item or index of 
* the item to be removed.
* @param {Number} p_nGroupIndex Optional. Number indicating the group to which
* the item belongs.
* @return The item that was removed from the MenuModule.
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype.removeItem =

    function(p_oObject, p_nGroupIndex) {
    
        if(typeof p_oObject != "undefined") {
    
            var oItem;
    
            if(p_oObject instanceof YAHOO.widget.MenuModuleItem) {
    
                oItem = 
                    this._removeItemFromGroupByValue(p_nGroupIndex, p_oObject);           
    
            }
            else if(typeof p_oObject == "number") {
    
                oItem = 
                    this._removeItemFromGroupByIndex(p_nGroupIndex, p_oObject);
    
            }
    
            if(oItem) {
    
                oItem.destroy();

                this.logger.log("Item removed." + 
                    " Text: " + oItem.cfg.getProperty("text") + ", " + 
                    " Index: " + oItem.index + ", " + 
                    " Group Index: " + oItem.groupIndex);
    
                return oItem;
    
            }
    
        }
    
    };


/**
* Returns a multi-dimensional array of all of a MenuModule's items.
* @return An array of items.
* @type Array
*/        
YAHOO.widget.MenuModule.prototype.getItemGroups = function() {

    return this._aItemGroups;

};


/**
* Returns the item at the specified index.
* @param {Number} p_nItemIndex Number indicating the ordinal position of the 
* item to be retrieved.
* @param {Number} p_nGroupIndex Optional. Number indicating the group to which
* the item belongs.
* @return An item.
* @type YAHOO.widget.MenuModuleItem
*/
YAHOO.widget.MenuModule.prototype.getItem = 

    function(p_nItemIndex, p_nGroupIndex) {
    
        if(typeof p_nItemIndex == "number") {
    
            var aGroup = this._getItemGroup(p_nGroupIndex);
    
            if(aGroup) {
    
                return aGroup[p_nItemIndex];
            
            }
    
        }
    
    };


/**
* Removes the MenuModule instance's element from the DOM and sets all child 
* elements to null.
*/
YAHOO.widget.MenuModule.prototype.destroy = function() {

    // Remove DOM event handlers

    this._oEventUtil.purgeElement(this.element);


    // Remove Custom Event listeners

    this.mouseOverEvent.unsubscribeAll();
    this.mouseOutEvent.unsubscribeAll();
    this.mouseDownEvent.unsubscribeAll();
    this.mouseUpEvent.unsubscribeAll();
    this.clickEvent.unsubscribeAll();
    this.keyPressEvent.unsubscribeAll();
    this.keyDownEvent.unsubscribeAll();
    this.keyUpEvent.unsubscribeAll();
    this.beforeMoveEvent.unsubscribeAll();


    var nItemGroups = this._aItemGroups.length;
    var nItems;
    var oItemGroup;
    var oItem;
    var i;
    var n;


    // Remove all items

    if(nItemGroups > 0) {

        i = nItemGroups - 1;

        do {

            oItemGroup = this._aItemGroups[i];

            if(oItemGroup) {

                nItems = oItemGroup.length;
    
                if(nItems > 0) {
    
                    n = nItems - 1;
        
                    do {

                        oItem = this._aItemGroups[i][n];

                        if(oItem) {
        
                            oItem.destroy();
                        }
        
                    }
                    while(n--);
    
                }

            }

        }
        while(i--);

    }        


    // Continue with the superclass implementation of this method

    YAHOO.widget.MenuModule.superclass.destroy.call(this);
    
    this.logger.log("Destroyed.");

};




/**
* Sets focus to a MenuModule instance's first enabled item.
*/
YAHOO.widget.MenuModule.prototype.setInitialFocus = function() {

    var oItem = this._getFirstEnabledItem();
    
    if(oItem) {
    
        oItem.focus();
    }
    
};


/**
* Sets the "selected" configuration property of a MenuModule instance's first
* enabled item to "true."
*/
YAHOO.widget.MenuModule.prototype.setInitialSelection = function() {

    var oItem = this._getFirstEnabledItem();
    
    if(oItem) {
    
        oItem.cfg.setProperty("selected", true);
    }        

};


/**
* Sets the "selected" configuration property of a MenuModule instance's active 
* item to "false," blurs the item and hide's the item's submenu.
*/
YAHOO.widget.MenuModule.prototype.clearActiveItem = function () {

    if(this.activeItem) {

        var oConfig = this.activeItem.cfg;

        oConfig.setProperty("selected", false);

        var oSubmenu = oConfig.getProperty("submenu");

        if(oSubmenu) {

            oSubmenu.hide();

        }

    }

};


/**
* Initializes the class's configurable properties which can be changed using 
* the MenuModule's Config object (cfg).
*/
YAHOO.widget.MenuModule.prototype.initDefaultConfig = function() {

    YAHOO.widget.MenuModule.superclass.initDefaultConfig.call(this);

    var oConfig = this.cfg;

	// Add configuration properties

    oConfig.addProperty(
        "position", 
        {
            value: "dynamic", 
            handler: this.configPosition, 
            validator: this._checkPosition 
        } 
    );

    oConfig.refireEvent("position");

    oConfig.addProperty("submenualignment", { value: ["tl","tr"] } );

};



/**
* @class The MenuModuleItem class allows you to create and modify an item for a
* MenuModule instance.
* @constructor
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a MenuModuleItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.MenuModuleItem = function(p_oObject, p_oConfig) {

    if(p_oObject) {

        this.init(p_oObject, p_oConfig);

    }

};

YAHOO.widget.MenuModuleItem.prototype = {

    // Constants

    /**
    * Constant representing the path to the image to be used for the submenu
    * arrow indicator.
    * @final
    * @type String
    */
    SUBMENU_INDICATOR_IMAGE_PATH: "nt/ic/ut/alt1/menuarorght8_nrm_1.gif",


    /**
    * Constant representing the path to the image to be used for the submenu
    * arrow indicator when a MenuModuleItem instance is selected.
    * @final
    * @type String
    */
    SELECTED_SUBMENU_INDICATOR_IMAGE_PATH: 
        "nt/ic/ut/alt1/menuarorght8_hov_1.gif",


    /**
    * Constant representing the path to the image to be used for the submenu
    * arrow indicator when a MenuModuleItem instance is disabled.
    * @final
    * @type String
    */
    DISABLED_SUBMENU_INDICATOR_IMAGE_PATH: 
        "nt/ic/ut/alt1/menuarorght8_dim_1.gif",


    /**
    * Constant representing the alt text for the image to be used for the 
    * submenu arrow indicator.
    * @final
    * @type String
    */
    COLLAPSED_SUBMENU_INDICATOR_ALT_TEXT: "Collapsed.  Click to expand.",


    /**
    * Constant representing the alt text for the image to be used for the 
    * submenu arrow indicator when the submenu is visible.
    * @final
    * @type String
    */
    EXPANDED_SUBMENU_INDICATOR_ALT_TEXT: "Expanded.  Click to collapse.",


    /**
    * Constant representing the alt text for the image to be used for the 
    * submenu arrow indicator when a MenuModuleItem instance is disabled.
    * @final
    * @type String
    */
    DISABLED_SUBMENU_INDICATOR_ALT_TEXT: "Disabled.",


    /**
    * Constant representing the CSS class(es) to be applied to the root 
    * HTMLLIElement of the MenuModuleItem.
    * @final
    * @type String
    */
    CSS_CLASS_NAME: "yuimenuitem",


    /**
    * Constant representing the type of menu to instantiate when creating 
    * submenu instances from parsing the child nodes (either HTMLSelectElement 
    * or HTMLDivElement) of the item's DOM.  The default 
    * is YAHOO.widget.MenuModule.
    * @final
    * @type YAHOO.widget.MenuModule
    */
    SUBMENU_TYPE: null,


    /**
    * Constant representing the type of item to instantiate when 
    * creating item instances from parsing the child nodes (either 
    * HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
    * submenu's DOM.  
    * The default is YAHOO.widget.MenuModuleItem.
    * @final
    * @type YAHOO.widget.MenuModuleItem
    */
    SUBMENU_ITEM_TYPE: null,


    /**
    * Constant representing the prefix path to use for non-secure images
    * @type string
    */
    IMG_ROOT: "http://us.i1.yimg.com/us.yimg.com/i/",
    

    /**
    * Constant representing the prefix path to use for securely served images
    * @type string
    */
    IMG_ROOT_SSL: "https://a248.e.akamai.net/sec.yimg.com/i/",


    // Private member variables
    
    /**
    * Reference to the HTMLAnchorElement of the MenuModuleItem's core internal
    * DOM structure.
    * @private
    * @type {HTMLAnchorElement}
    */
    _oAnchor: null,
    

    /**
    * Reference to the text node of the MenuModuleItem's core internal
    * DOM structure.
    * @private
    * @type {Text}
    */
    _oText: null,
    
    
    /**
    * Reference to the HTMLElement (&#60;EM&#60;) used to create the optional
    * help text for a MenuModuleItem instance.
    * @private
    * @type {HTMLElement}
    */
    _oHelpTextEM: null,
    
    
    /**
    * Reference to the submenu for a MenuModuleItem instance.
    * @private
    * @type {YAHOO.widget.MenuModule}
    */
    _oSubmenu: null,
    
    
    /**
    * Reference to the Dom utility singleton.
    * @private
    * @type {YAHOO.util.Dom}
    */
    _oDom: YAHOO.util.Dom,


    // Public properties

	/**
	* The class's constructor function
	* @type YAHOO.widget.MenuModuleItem
	*/
	constructor: YAHOO.widget.MenuModuleItem,


	/**
	* The string representing the image root
	* @type string
	*/
	imageRoot: null,


	/**
	* Boolean representing whether or not the current browsing context 
	* is secure (https)
	* @type boolean
	*/
	isSecure: YAHOO.widget.Module.prototype.isSecure,


    /**
    * Returns the ordinal position of a MenuModuleItem instance in a group.
    * @type Number
    */
    index: null,


    /**
    * Returns the index of the group to which a MenuModuleItem instance belongs.
    * @type Number
    */
    groupIndex: null,


    /**
    * Returns the parent object for a MenuModuleItem instance.
    * @type {YAHOO.widget.MenuModule}
    */
    parent: null,


    /**
    * Returns the HTMLLIElement for a MenuModuleItem instance.
    * @type {HTMLLIElement}
    */
    element: null,


    /**
    * Returns the HTMLElement (either HTMLLIElement, HTMLOptGroupElement or
    * HTMLOptionElement) used create the MenuModuleItem instance.
    * @type {HTMLLIElement/HTMLOptGroupElement/HTMLOptionElement}
    */
    srcElement: null,


    /**
    * Specifies an arbitrary value for a MenuModuleItem instance.
    * @type {Object}
    */
    value: null,


    /**
    * Reference to the HTMLImageElement used to create the submenu
    * indicator for a MenuModuleItem instance.
    * @type {HTMLImageElement}
    */
    submenuIndicator: null,


	/**
	* String representing the browser
	* @type string
	*/
	browser: YAHOO.widget.Module.prototype.browser,


    // Events

    /**
    * Fires when a MenuModuleItem instances's HTMLLIElement is removed from
    * it's parent HTMLUListElement node.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    destroyEvent: null,


    /**
    * Fires when the mouse has entered a MenuModuleItem instance.  Passes
    * back the DOM Event object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    mouseOverEvent: null,


    /**
    * Fires when the mouse has left a MenuModuleItem instance.  Passes back  
    * the DOM Event object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    mouseOutEvent: null,


    /**
    * Fires when the user mouses down on a MenuModuleItem instance.  Passes 
    * back the DOM Event object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    mouseDownEvent: null,


    /**
    * Fires when the user releases a mouse button while the mouse is 
    * over a MenuModuleItem instance.  Passes back the DOM Event object as
    * an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    mouseUpEvent: null,


    /**
    * Fires when the user clicks the on a MenuModuleItem instance.  Passes 
    * back the DOM Event object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    clickEvent: null,


    /**
    * Fires when the user presses an alphanumeric key.  Passes back the 
    * DOM Event object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    keyPressEvent: null,


    /**
    * Fires when the user presses a key.  Passes back the DOM Event 
    * object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    keyDownEvent: null,


    /**
    * Fires when the user releases a key.  Passes back the DOM Event 
    * object as an argument.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    keyUpEvent: null,


    /**
    * Fires when a MenuModuleItem instance receives focus.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    focusEvent: null,


    /**
    * Fires when a MenuModuleItem instance loses the input focus.
    * @type {YAHOO.util.CustomEvent}
    * @see YAHOO.util.CustomEvent
    */
    blurEvent: null,


    /**
    * The MenuModuleItem class's initialization method. This method is 
    * automatically called by the constructor, and sets up all DOM references 
    * for pre-existing markup, and creates required markup if it is not
    * already present.
    * @param {String or HTMLElement} p_oObject String or HTMLElement 
    * (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
    * source HTMLElement node.
    * @param {Object} p_oConfig The configuration object literal containing 
    * the configuration for a MenuModuleItem instance. See the configuration 
    * class documentation for more details.
    */
    init: function(p_oObject, p_oConfig) {

        this.imageRoot = (this.isSecure) ? this.IMG_ROOT_SSL : this.IMG_ROOT;


        if(!this.SUBMENU_TYPE) {
    
            this.SUBMENU_TYPE = YAHOO.widget.MenuModule;
    
        }

        if(!this.SUBMENU_ITEM_TYPE) {
    
            this.SUBMENU_ITEM_TYPE = YAHOO.widget.MenuModuleItem;
    
        }


        // Create the config object

        this.cfg = new YAHOO.util.Config(this);

        this.initDefaultConfig();

        var oConfig = this.cfg;


        if(this._checkString(p_oObject)) {

            this._createRootNodeStructure();

            oConfig.setProperty("text", p_oObject);

        }
        else if(this._checkDOMNode(p_oObject)) {

            switch(p_oObject.tagName) {

                case "OPTION":

                    this._createRootNodeStructure();

                    oConfig.setProperty("text", p_oObject.text);

                    this.srcElement = p_oObject;

                break;

                case "OPTGROUP":

                    this._createRootNodeStructure();

                    oConfig.setProperty("text", p_oObject.label);

                    this.srcElement = p_oObject;

                    this._initSubTree();

                break;

                case "LI":

                    // Get the anchor node (if it exists)

                    var oAnchor = this._getFirstElement(p_oObject, "A");
                    var sURL = "#";
                    var sText = null;


                    // Capture the "text" and/or the "URL"

                    if(oAnchor) {

                        sURL = oAnchor.getAttribute("href");

                        if(oAnchor.innerText) {
                
                            sText = oAnchor.innerText;
                
                        }
                        else {
                
                            var oRange = oAnchor.ownerDocument.createRange();
                
                            oRange.selectNodeContents(oAnchor);
                
                            sText = oRange.toString();             
                
                        }

                    }
                    else {

                        var oText = p_oObject.firstChild;

                        sText = oText.nodeValue;

                        oAnchor = document.createElement("a");
                        
                        oAnchor.setAttribute("href", sURL);

                        p_oObject.replaceChild(oAnchor, oText);
                        
                        oAnchor.appendChild(oText);

                    }


                    this.srcElement = p_oObject;
                    this.element = p_oObject;
                    this._oAnchor = oAnchor;
    

                    // Check if emphasis has been applied to the MenuModuleItem

                    var oEmphasisNode = this._getFirstElement(oAnchor);
                    var bEmphasis = false;
                    var bStrongEmphasis = false;

                    if(oEmphasisNode) {

                        // Set a reference to the text node 

                        this._oText = oEmphasisNode.firstChild;

                        switch(oEmphasisNode.tagName) {

                            case "EM":

                                bEmphasis = true;

                            break;

                            case "STRONG":

                                bStrongEmphasis = true;

                            break;

                        }

                    }
                    else {

                        // Set a reference to the text node 

                        this._oText = oAnchor.firstChild;

                    }


                    /*
                        Set these properties silently to sync up the 
                        configuration object without making changes to the 
                        element's DOM
                    */ 

                    oConfig.setProperty("text", sText, true);
                    oConfig.setProperty("url", sURL, true);
                    oConfig.setProperty("emphasis", bEmphasis, true);
                    oConfig.setProperty(
                        "strongemphasis", 
                        bStrongEmphasis, 
                        true
                    );

                    this._initSubTree();

                break;

            }            

        }


        if(this.element) {


            this._oDom.addClass(this.element, this.CSS_CLASS_NAME);


            // Create custom events
    
            var CustomEvent = YAHOO.util.CustomEvent;
    
            this.destroyEvent = new CustomEvent("destroyEvent", this);
            this.mouseOverEvent = new CustomEvent("mouseOverEvent", this);
            this.mouseOutEvent = new CustomEvent("mouseOutEvent", this);
            this.mouseDownEvent = new CustomEvent("mouseDownEvent", this);
            this.mouseUpEvent = new CustomEvent("mouseUpEvent", this);
            this.clickEvent = new CustomEvent("clickEvent", this);
            this.keyPressEvent = new CustomEvent("keyPressEvent", this);
            this.keyDownEvent = new CustomEvent("keyDownEvent", this);
            this.keyUpEvent = new CustomEvent("keyUpEvent", this);
            this.focusEvent = new CustomEvent("focusEvent", this);
            this.blurEvent = new CustomEvent("blurEvent", this);


            if(p_oConfig) {
    
                oConfig.applyConfig(p_oConfig);
    
            }        

            oConfig.fireQueue();

        }

    },


    // Private methods

    /**
    * Returns an HTMLElement's first HTMLElement node
    * @private
    * @param {HTMLElement} p_oElement The element to be evaluated.
    * @param {String} p_sTagName Optional. The tagname of the element.
    * @return Returns an HTMLElement node.
    * @type Boolean
    */
    _getFirstElement: function(p_oElement, p_sTagName) {

        var oElement;

        if(p_oElement.firstChild && p_oElement.firstChild.nodeType == 1) {

            oElement = p_oElement.firstChild;

        }
        else if(
            p_oElement.firstChild && 
            p_oElement.firstChild.nextSibling && 
            p_oElement.firstChild.nextSibling.nodeType == 1
        ) {

            oElement = p_oElement.firstChild.nextSibling;

        }


        if(p_sTagName) {

            return (oElement && oElement.tagName == p_sTagName) ? 
                oElement : false;

        }

        return oElement;

    },


    /**
    * Determines if an object is a string
    * @private
    * @param {Object} p_oObject The object to be evaluated.
    * @return Returns true if the object is a string.
    * @type Boolean
    */
    _checkString: function(p_oObject) {

        return (typeof p_oObject == "string");

    },


    /**
    * Determines if an object is an HTMLElement.
    * @private
    * @param {Object} p_oObject The object to be evaluated.
    * @return Returns true if the object is an HTMLElement.
    * @type Boolean
    */
    _checkDOMNode: function(p_oObject) {

        return (p_oObject && p_oObject.tagName);

    },


    /**
    * Creates the core DOM structure for a MenuModuleItem instance.
    * @private
    */
    _createRootNodeStructure: function () {

        this.element = document.createElement("li");

        this._oText = document.createTextNode("");

        this._oAnchor = document.createElement("a");
        this._oAnchor.appendChild(this._oText);
        
        this.cfg.refireEvent("url");

        this.element.appendChild(this._oAnchor);            

    },


    /**
    * Iterates the source element's childNodes collection and uses the  
    * child nodes to instantiate other menus.
    * @private
    */
    _initSubTree: function() {

        var Menu = this.SUBMENU_TYPE;
        var MenuModuleItem = this.SUBMENU_ITEM_TYPE;
        var oSrcEl = this.srcElement;
        var oConfig = this.cfg;


        if(oSrcEl.childNodes.length > 0) {

            var oNode = oSrcEl.firstChild;
            var aOptions = [];

            do {

                switch(oNode.tagName) {
        
                    case "DIV":
        
                        oConfig.setProperty("submenu", (new Menu(oNode)));
        
                    break;
 
                    case "OPTION":

                        aOptions[aOptions.length] = oNode;

                    break;
       
                }
            
            }        
            while((oNode = oNode.nextSibling));


            var nOptions = aOptions.length;

            if(nOptions > 0) {
    
                oConfig.setProperty(
                    "submenu", 
                    (new Menu(this._oDom.generateId()))
                );
    
                for(var n=0; n<nOptions; n++) {
    
                    this._oSubmenu.addItem((new MenuModuleItem(aOptions[n])));
    
                }
    
            }

        }

    },


    // Event handlers for configuration properties

    /**
    * Event handler for when the "text" configuration property of
    * a MenuModuleItem instance changes. 
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */
    configText: function(p_sType, p_aArgs, p_oItem) {

        var sText = p_aArgs[0];


        if(this._oText) {

            this._oText.nodeValue = sText;

        }

    },


    /**
    * Event handler for when the "helptext" configuration property of
    * a MenuModuleItem instance changes. 
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */    
    configHelpText: function(p_sType, p_aArgs, p_oItem) {

        var me = this;
        var Dom = this._oDom;
        var oHelpText = p_aArgs[0];
        var oEl = this.element;
        var oConfig = this.cfg;
        var aNodes = [oEl, this._oAnchor];
        var oImg = this.submenuIndicator;


        /**
        * Adds the "hashelptext" class to the necessary nodes and refires the 
        * "selected" and "disabled" configuration events
        * @ignore
        */
        function initHelpText() {

            Dom.addClass(aNodes, "hashelptext");

            if(oConfig.getProperty("disabled")) {

                oConfig.refireEvent("disabled");

            }

            if(oConfig.getProperty("selected")) {

                oConfig.refireEvent("selected");

            }                

        }


        /**
        * Removes the "hashelptext" class and corresponding DOM element (EM)
        * @ignore
        */
        function removeHelpText() {

            Dom.removeClass(aNodes, "hashelptext");

            oEl.removeChild(me._oHelpTextEM);
            me._oHelpTextEM = null;

        }


        if(this._checkDOMNode(oHelpText)) {

            if(this._oHelpTextEM) {

                this._oHelpTextEM.parentNode.replaceChild(
                    oHelpText, 
                    this._oHelpTextEM
                );

            }
            else {

                this._oHelpTextEM = oHelpText;

                oEl.insertBefore(this._oHelpTextEM, oImg);

            }

            initHelpText();

        }
        else if(this._checkString(oHelpText)) {

            if(oHelpText.length === 0) {

                removeHelpText();

            }
            else {

                if(!this._oHelpTextEM) {

                    this._oHelpTextEM = document.createElement("em");

                    oEl.insertBefore(this._oHelpTextEM, oImg);

                }

                this._oHelpTextEM.innerHTML = oHelpText;

                initHelpText();

            }

        }
        else if(!oHelpText && this._oHelpTextEM) {

            removeHelpText();

        }

    },


    /**
    * Event handler for when the "url" configuration property of
    * a MenuModuleItem instance changes.  
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */    
    configURL: function(p_sType, p_aArgs, p_oItem) {

        var sURL = p_aArgs[0];

        if(!sURL) {

            sURL = "#";

        }

        this._oAnchor.setAttribute("href", sURL);

    },


    /**
    * Event handler for when the "emphasis" configuration property of
    * a MenuModuleItem instance changes.  
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */    
    configEmphasis: function(p_sType, p_aArgs, p_oItem) {

        var bEmphasis = p_aArgs[0];
        var oAnchor = this._oAnchor;
        var oText = this._oText;
        var oConfig = this.cfg;
        var oEM;


        if(bEmphasis && oConfig.getProperty("strongemphasis")) {

            oConfig.setProperty("strongemphasis", false);

        }


        if(oAnchor) {

            if(bEmphasis) {

                oEM = document.createElement("em");
                oEM.appendChild(oText);

                oAnchor.appendChild(oEM);

            }
            else {

                oEM = this._getFirstElement(oAnchor, "EM");

                oAnchor.removeChild(oEM);
                oAnchor.appendChild(oText);

            }

        }

    },


    /**
    * Event handler for when the "strongemphasis" configuration property of
    * a MenuModuleItem instance changes. 
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */    
    configStrongEmphasis: function(p_sType, p_aArgs, p_oItem) {

        var bStrongEmphasis = p_aArgs[0];
        var oAnchor = this._oAnchor;
        var oText = this._oText;
        var oConfig = this.cfg;
        var oStrong;

        if(bStrongEmphasis && oConfig.getProperty("emphasis")) {

            oConfig.setProperty("emphasis", false);

        }

        if(oAnchor) {

            if(bStrongEmphasis) {

                oStrong = document.createElement("strong");
                oStrong.appendChild(oText);

                oAnchor.appendChild(oStrong);

            }
            else {

                oStrong = this._getFirstElement(oAnchor, "STRONG");

                oAnchor.removeChild(oStrong);
                oAnchor.appendChild(oText);

            }

        }

    },


    /**
    * Event handler for when the "disabled" configuration property of
    * a MenuModuleItem instance changes. 
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */    
    configDisabled: function(p_sType, p_aArgs, p_oItem) {

        var bDisabled = p_aArgs[0];
        var Dom = this._oDom;
        var oAnchor = this._oAnchor;
        var aNodes = [this.element, oAnchor];
        var oEM = this._oHelpTextEM;
        var oConfig = this.cfg;
        var oImg = this.submenuIndicator;
        var sImageSrc;
        var sImageAlt;


        if(oEM) {

            aNodes[2] = oEM;

        }

        if(bDisabled) {

            if(oConfig.getProperty("selected")) {

                oConfig.setProperty("selected", false);

            }

            oAnchor.removeAttribute("href");

            Dom.addClass(aNodes, "disabled");

            sImageSrc = this.DISABLED_SUBMENU_INDICATOR_IMAGE_PATH;
            sImageAlt = this.DISABLED_SUBMENU_INDICATOR_ALT_TEXT;

        }
        else {

            oAnchor.setAttribute("href", oConfig.getProperty("url"));

            Dom.removeClass(aNodes, "disabled");

            sImageSrc = this.SUBMENU_INDICATOR_IMAGE_PATH;
            sImageAlt = this.COLLAPSED_SUBMENU_INDICATOR_ALT_TEXT;

        }


        if(oImg) {

            oImg.src = this.imageRoot + sImageSrc;
            oImg.alt = sImageAlt;

        }

    },


    /**
    * Event handler for when the "selected" configuration property of
    * a MenuModuleItem instance changes. 
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */    
    configSelected: function(p_sType, p_aArgs, p_oItem) {

        if(!this.cfg.getProperty("disabled")) {

            var Dom = this._oDom;
            var bSelected = p_aArgs[0];
            var oEM = this._oHelpTextEM;
            var aNodes = [this.element, this._oAnchor];
            var oImg = this.submenuIndicator;
            var sImageSrc;


            if(oEM) {
    
                aNodes[2] = oEM;  
    
            }
    
            if(bSelected) {
    
                Dom.addClass(aNodes, "selected");
                sImageSrc = this.SELECTED_SUBMENU_INDICATOR_IMAGE_PATH;
    
            }
            else {
    
                Dom.removeClass(aNodes, "selected");
                sImageSrc = this.SUBMENU_INDICATOR_IMAGE_PATH;
    
            }
    
            if(oImg) {
    
                oImg.src = document.images[(this.imageRoot + sImageSrc)].src;

            }

        }

    },


    /**
    * Event handler for when the "submenu" configuration property of
    * a MenuModuleItem instance changes. 
    * @param {String} p_sType The name of the event that was fired.
    * @param {Array} p_aArgs Collection of arguments sent when the 
    * event was fired.
    * @param {YAHOO.widget.MenuModuleItem} p_oItem The MenuModuleItem instance 
    * that fired the event.
    */
    configSubmenu: function(p_sType, p_aArgs, p_oItem) {

        var Dom = this._oDom;
        var oEl = this.element;
        var oSubmenu = p_aArgs[0];
        var oImg = this.submenuIndicator;
        var oConfig = this.cfg;
        var aNodes = [this.element, this._oAnchor];


        if(oSubmenu) {

            // Set the submenu's parent to this MenuModuleItem instance

            oSubmenu.parent = this;

            this._oSubmenu = oSubmenu;


            if(!oImg) { 

                var me = this;

                function preloadImage(p_sPath) {

                    var sPath = me.imageRoot + p_sPath;

                    if(!document.images[sPath]) {

                        var oImg = document.createElement("img");
                        oImg.src = sPath;
                        oImg.name = sPath;
                        oImg.id = sPath;
                        oImg.style.display = "none";
                        
                        document.body.appendChild(oImg);

                    }
                
                }

                preloadImage(this.SUBMENU_INDICATOR_IMAGE_PATH);
                preloadImage(this.SELECTED_SUBMENU_INDICATOR_IMAGE_PATH);
                preloadImage(this.DISABLED_SUBMENU_INDICATOR_IMAGE_PATH);

                oImg = document.createElement("img");
                oImg.src = (this.imageRoot + this.SUBMENU_INDICATOR_IMAGE_PATH);
                oImg.alt = this.COLLAPSED_SUBMENU_INDICATOR_ALT_TEXT;

                oEl.appendChild(oImg);

                this.submenuIndicator = oImg;

                Dom.addClass(aNodes, "hassubmenu");


                if(oConfig.getProperty("disabled")) {

                    oConfig.refireEvent("disabled");

                }

                if(oConfig.getProperty("selected")) {

                    oConfig.refireEvent("selected");

                }                

            }

        }
        else {

            Dom.removeClass(aNodes, "hassubmenu");

            if(oImg) {

                oEl.removeChild(oImg);

            }

            if(this._oSubmenu) {

                this._oSubmenu.destroy();

            }

        }

    },


    // Public methods

	/**
	* Initializes an item's configurable properties.
	*/
	initDefaultConfig : function() {

        var oConfig = this.cfg;
        var CheckBoolean = oConfig.checkBoolean;


        // Define the config properties

        oConfig.addProperty(
            "text", 
            { 
                value: "", 
                handler: this.configText, 
                validator: this._checkString, 
                suppressEvent: true 
            }
        );
        
        oConfig.addProperty("helptext", { handler: this.configHelpText });
        
        oConfig.addProperty(
            "url", 
            { value: "#", handler: this.configURL, suppressEvent: true }
        );
        
        oConfig.addProperty(
            "emphasis", 
            { 
                value: false, 
                handler: this.configEmphasis, 
                validator: CheckBoolean, 
                suppressEvent: true 
            }
        );

        oConfig.addProperty(
            "strongemphasis",
            {
                value: false,
                handler: this.configStrongEmphasis,
                validator: CheckBoolean,
                suppressEvent: true
            }
        );

        oConfig.addProperty(
            "disabled",
            {
                value: false,
                handler: this.configDisabled,
                validator: CheckBoolean,
                suppressEvent: true
            }
        );

        oConfig.addProperty(
            "selected",
            {
                value: false,
                handler: this.configSelected,
                validator: CheckBoolean,
                suppressEvent: true
            }
        );

        oConfig.addProperty("submenu", { handler: this.configSubmenu });

	},


    /**
    * Finds the next enabled MenuModuleItem instance in a MenuModule instance 
    * @return Returns a MenuModuleItem instance.
    * @type YAHOO.widget.MenuModuleItem
    */
    getNextEnabledSibling: function() {

        if(this.parent instanceof YAHOO.widget.MenuModule) {

            var nGroupIndex = this.groupIndex;

            /**
            * Returns the next item in an array 
            * @param {p_aArray} An array
            * @param {p_nStartIndex} The index to start searching the array 
            * @ignore
            * @return Returns an item in an array
            * @type Object 
            */
            function getNextArrayItem(p_aArray, p_nStartIndex) {
    
                return p_aArray[p_nStartIndex] || 
                    getNextArrayItem(p_aArray, (p_nStartIndex+1));
    
            }
    
    
            var aItemGroups = this.parent.getItemGroups();
            var oNextItem;
    
    
            if(this.index < (aItemGroups[nGroupIndex].length - 1)) {
    
                oNextItem = getNextArrayItem(
                        aItemGroups[nGroupIndex], 
                        (this.index+1)
                    );
    
            }
            else {
    
                var nNextGroupIndex;
    
                if(nGroupIndex < (aItemGroups.length - 1)) {
    
                    nNextGroupIndex = nGroupIndex + 1;
    
                }
                else {
    
                    nNextGroupIndex = 0;
    
                }
    
                var aNextGroup = getNextArrayItem(aItemGroups, nNextGroupIndex);
    
                // Retrieve the first MenuModuleItem instance in the next group
    
                oNextItem = getNextArrayItem(aNextGroup, 0);
    
            }
    
            return oNextItem.cfg.getProperty("disabled") ? 
                        oNextItem.getNextEnabledSibling() : oNextItem;

        }

    },


    /**
    * Finds the previous enabled MenuModuleItem instance in a 
    * MenuModule instance 
    * @return Returns a MenuModuleItem instance.
    * @type YAHOO.widget.MenuModuleItem
    */
    getPreviousEnabledSibling: function() {

        if(this.parent instanceof YAHOO.widget.MenuModule) {

            var nGroupIndex = this.groupIndex;

            /**
            * Returns the previous item in an array 
            * @param {p_aArray} An array
            * @param {p_nStartIndex} The index to start searching the array 
            * @ignore
            * @return Returns an item in an array
            * @type Object 
            */
            function getPreviousArrayItem(p_aArray, p_nStartIndex) {
    
                return p_aArray[p_nStartIndex] || 
                    getPreviousArrayItem(p_aArray, (p_nStartIndex-1));
    
            }


            /**
            * Get the index of the first item in an array 
            * @param {p_aArray} An array
            * @param {p_nStartIndex} The index to start searching the array 
            * @ignore
            * @return Returns an item in an array
            * @type Object 
            */    
            function getFirstItemIndex(p_aArray, p_nStartIndex) {
    
                return p_aArray[p_nStartIndex] ? 
                    p_nStartIndex : 
                    getFirstItemIndex(p_aArray, (p_nStartIndex+1));
    
            }
    
            var aItemGroups = this.parent.getItemGroups();
            var oPreviousItem;
    
            if(
                this.index > getFirstItemIndex(aItemGroups[nGroupIndex], 0)
            ) {
    
                oPreviousItem = 
                    getPreviousArrayItem(
                        aItemGroups[nGroupIndex], 
                        (this.index-1)
                    );
    
            }
            else {
    
                var nPreviousGroupIndex;
    
                if(nGroupIndex > getFirstItemIndex(aItemGroups, 0)) {
    
                    nPreviousGroupIndex = nGroupIndex - 1;
    
                }
                else {
    
                    nPreviousGroupIndex = aItemGroups.length - 1;
    
                }
    
                var aPreviousGroup = 
                        getPreviousArrayItem(aItemGroups, nPreviousGroupIndex);
    
                oPreviousItem = 
                    getPreviousArrayItem(
                        aPreviousGroup, 
                        (aPreviousGroup.length - 1)
                    );
    
            }
    
            return oPreviousItem.cfg.getProperty("disabled") ? 
                    oPreviousItem.getPreviousEnabledSibling() : oPreviousItem;

        }

    },


    /**
    * Causes a MenuModuleItem instance to receive the focus and fires the
    * focus event.
    */
    focus: function() {

        var oParent = this.parent;
        var oAnchor = this._oAnchor;
        var oActiveItem = oParent.activeItem;

        if(
            !this.cfg.getProperty("disabled") && 
            oParent && 
            oParent.cfg.getProperty("visible")
        ) {

            if(oActiveItem) {

                oActiveItem.blur();

            }

            oAnchor.focus();

            /*
                Opera 8.5 doesn't always focus the anchor if a MenuModuleItem
                instance has a submenu, this is fixed by calling "focus"
                twice.
            */
            if(oParent && this.browser == "opera" && this._oSubmenu) {

                oAnchor.focus();

            }

            this.focusEvent.fire();

        }

    },


    /**
    * Causes a MenuModuleItem instance to lose focus and fires the onblur event.
    */    
    blur: function() {

        var oParent = this.parent;

        if(
            !this.cfg.getProperty("disabled") && 
            oParent && 
            this._oDom.getStyle(oParent.element, "visibility") == "visible"
        ) {

            this._oAnchor.blur();

            this.blurEvent.fire();

        }

    },


	/**
	* Removes a MenuModuleItem instance's HTMLLIElement from it's parent
    * HTMLUListElement node.
	*/
    destroy: function() {

        var oEl = this.element;

        if(oEl) {

            // Remove CustomEvent listeners
    
            this.mouseOverEvent.unsubscribeAll();
            this.mouseOutEvent.unsubscribeAll();
            this.mouseDownEvent.unsubscribeAll();
            this.mouseUpEvent.unsubscribeAll();
            this.clickEvent.unsubscribeAll();
            this.keyPressEvent.unsubscribeAll();
            this.keyDownEvent.unsubscribeAll();
            this.keyUpEvent.unsubscribeAll();
            this.focusEvent.unsubscribeAll();
            this.blurEvent.unsubscribeAll();
            this.cfg.configChangedEvent.unsubscribeAll();


            // Remove the element from the parent node

            var oParentNode = oEl.parentNode;

            if(oParentNode) {

                oParentNode.removeChild(oEl);

                this.destroyEvent.fire();

            }

            this.destroyEvent.unsubscribeAll();

        }

    }

};


/**
* @class Extends YAHOO.widget.MenuModule to provide a set of default mouse and 
* key event behaviors.
* @constructor
* @extends YAHOO.widget.MenuModule
* @base YAHOO.widget.MenuModule
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a Menu instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.Menu = function(p_oElement, p_oConfig) {

    YAHOO.widget.Menu.superclass.constructor.call(
            this, 
            p_oElement,
            p_oConfig
        );

};

YAHOO.extend(YAHOO.widget.Menu, YAHOO.widget.MenuModule);


/**
* The Menu class's initialization method. This method is automatically 
* called by the constructor, and sets up all DOM references for pre-existing 
* markup, and creates required markup if it is not already present.
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a Menu instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.Menu.prototype.init = function(p_oElement, p_oConfig) {

    if(!this.ITEM_TYPE) {

        this.ITEM_TYPE = YAHOO.widget.MenuItem;

    }


    // Call the init of the superclass (YAHOO.widget.Menu)

    YAHOO.widget.Menu.superclass.init.call(this, p_oElement);


    this.beforeInitEvent.fire(YAHOO.widget.Menu);


    // Add event handlers

    this.showEvent.subscribe(this._onMenuShow, this, true);
    this.mouseOverEvent.subscribe(this._onMenuMouseOver, this, true);
    this.keyDownEvent.subscribe(this._onMenuKeyDown, this, true);


    if(p_oConfig) {

        this.cfg.applyConfig(p_oConfig, true);

    }
    
    this.initEvent.fire(YAHOO.widget.Menu);

};


// Private event handlers

/**
* "show" Custom Event handler for a menu.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.Menu} p_oMenu The menu that fired the event.
*/
YAHOO.widget.Menu.prototype._onMenuShow = 

    function(p_sType, p_aArgs, p_oMenu) {

        var oParent = this.parent;

        if(oParent && oParent.parent instanceof YAHOO.widget.Menu) {

            var aAlignment = oParent.parent.cfg.getProperty("submenualignment");
    
            this.cfg.setProperty(
                "submenualignment", 
                [ aAlignment[0], aAlignment[1] ]
            );
        
        }

    };


/**
* "mouseover" Custom Event handler for a Menu instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.Menu} p_oMenu The Menu instance that fired the event.
*/
YAHOO.widget.Menu.prototype._onMenuMouseOver = 

    function(p_sType, p_aArgs, p_oMenu) {
    
        /*
            If the menu is a submenu, then select the menu's parent
            MenuItem instance
        */
    
        if(this.parent) {
    
            this.parent.cfg.setProperty("selected", true);
    
        }
    
    };


/**
* "mouseover" Custom Event handler for a Menu instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.Menu} p_oMenu The Menu instance that fired the event.
*/
YAHOO.widget.Menu.prototype._onMenuKeyDown = 

    function(p_sType, p_aArgs, p_oMenu) {
    
        if(this.cfg.getProperty("position") == "dynamic") {
    
            var oDOMEvent = p_aArgs[0];
            var oParent = this.parent;
        
            if(oDOMEvent.keyCode == 27) { // Esc key
        
                this.hide();
        
                // Set focus to the parent MenuItem if one exists
        
                if(oParent) {
        
                    oParent.focus();

                    if(oParent.parent instanceof YAHOO.widget.Menu) {

                        oParent.cfg.setProperty("selected", true);
        
                    }

                    YAHOO.util.Event.preventDefault(oDOMEvent);
        
                }
            
            }
        
        }
    
    };
    

// Public event handlers

/**
* Event handler fired when the resize monitor element is resized.
*/
YAHOO.widget.Menu.prototype.onDomResize = function(e, obj) {

    if(!this._handleResize) {
    
        this._handleResize = true;
        return;
    
    }

    this.logger.log("Browser font sized changed.");

    var me = this;
    var oConfig = this.cfg;

    if(oConfig.getProperty("position") == "dynamic") {

        oConfig.setProperty("width", (this._getOffsetWidth() + "px"));
        
        if(this.parent && oConfig.getProperty("visible")) {

            function align() {

                me.align();
            
            }

            window.setTimeout(align, 0);
            
        }

    }

    YAHOO.widget.Menu.superclass.onDomResize.call(this, e, obj);

};    


/**
* @class The MenuItem class allows you to create and modify an item for a
* Menu instance.  MenuItem extends YAHOO.widget.MenuModuleItem to provide a 
* set of default mouse and key event behaviors.
* @constructor
* @extends YAHOO.widget.MenuModuleItem
* @base YAHOO.widget.MenuModuleItem
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a MenuItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.MenuItem = function(p_oObject, p_oConfig) {

    YAHOO.widget.MenuItem.superclass.constructor.call(
        this, 
        p_oObject, 
        p_oConfig
    );

};

YAHOO.extend(YAHOO.widget.MenuItem, YAHOO.widget.MenuModuleItem);


/**
* The MenuItem class's initialization method. This method is automatically
* called by the constructor, and sets up all DOM references for
* pre-existing markup, and creates required markup if it is not
* already present.
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a MenuItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.MenuItem.prototype.init = function(p_oObject, p_oConfig) {

    if(!this.SUBMENU_TYPE) {

        this.SUBMENU_TYPE = YAHOO.widget.Menu;

    }

    if(!this.SUBMENU_ITEM_TYPE) {

        this.SUBMENU_ITEM_TYPE = YAHOO.widget.MenuItem;

    }


    /* 
        Call the init of the superclass (YAHOO.widget.MenuModuleItem)
        Note: We don't pass the user config in here yet 
        because we only want it executed once, at the lowest 
        subclass level.
    */ 

    YAHOO.widget.MenuItem.superclass.init.call(this, p_oObject);  


    // Add event handlers to each "MenuItem" instance

    this.keyDownEvent.subscribe(this._onKeyDown, this, true);
    this.mouseOverEvent.subscribe(this._onMouseOver, this, true);
    this.mouseOutEvent.subscribe(this._onMouseOut, this, true);

    var oConfig = this.cfg;

    if(p_oConfig) {

        oConfig.applyConfig(p_oConfig, true);

    }

    oConfig.fireQueue();

};


// Constants

/**
* Constant representing the path to the image to be used for the checked state.
* @final
* @type String
*/
YAHOO.widget.MenuItem.prototype.CHECKED_IMAGE_PATH = 
    "nt/ic/ut/bsc/menuchk8_nrm_1.gif";

/**
* Constant representing the path to the image to be used for the selected 
* checked state.
* @final
* @type String
*/
YAHOO.widget.MenuItem.prototype.SELECTED_CHECKED_IMAGE_PATH = 
    "nt/ic/ut/bsc/menuchk8_hov_1.gif";

/**
* Constant representing the path to the image to be used for the disabled 
* checked state.
* @final
* @type String
*/
YAHOO.widget.MenuItem.prototype.DISABLED_CHECKED_IMAGE_PATH = 
    "nt/ic/ut/bsc/menuchk8_dim_1.gif";

/**
* Constant representing the alt text for the image to be used for the 
* checked image.
* @final
* @type String
*/
YAHOO.widget.MenuItem.prototype.CHECKED_IMAGE_ALT_TEXT = "Checked.";


/**
* Constant representing the alt text for the image to be used for the 
* checked image when the item is disabled.
* @final
* @type String
*/
YAHOO.widget.MenuItem.prototype.DISABLED_CHECKED_IMAGE_ALT_TEXT = 
    "Checked. (Item disabled.)";


// Private properties

/**
* Reference to the HTMLImageElement used to create the checked
* indicator for a MenuItem instance.
* @private
* @type {HTMLImageElement}
*/
YAHOO.widget.MenuItem.prototype._checkImage = null;


// Private event handlers


/**
* "keydown" Custom Event handler for a MenuItem instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuItem.prototype._onKeyDown = 

    function(p_sType, p_aArgs, p_oMenuItem) {

        var Event = YAHOO.util.Event;
        var oDOMEvent = p_aArgs[0];
        var oParent = this.parent;
        var oConfig = this.cfg;
        var oMenuItem;
    

        switch(oDOMEvent.keyCode) {
    
            case 38:    // Up arrow
            case 40:    // Down arrow
    
                if(
                    this == oParent.activeItem && 
                    !oConfig.getProperty("selected")
                ) {
    
                    oConfig.setProperty("selected", true);
    
                }
                else {
    
                    var oNextItem = (oDOMEvent.keyCode == 38) ? 
                            this.getPreviousEnabledSibling() : 
                            this.getNextEnabledSibling();
            
                    if(oNextItem) {

                        oParent.clearActiveItem();

                        oNextItem.cfg.setProperty("selected", true);
            
                        oNextItem.focus();
    
                    }
    
                }
    
                Event.preventDefault(oDOMEvent);

            break;
            
    
            case 39:    // Right arrow

                oParent.clearActiveItem();

                oConfig.setProperty("selected", true);
                
                this.focus();


                var oSubmenu = oConfig.getProperty("submenu");
    
                if(oSubmenu) {

                    oSubmenu.show();
                    oSubmenu.setInitialSelection();                    
    
                }
                else if(
                    YAHOO.widget.MenuBarItem && 
                    oParent.parent && 
                    oParent.parent instanceof YAHOO.widget.MenuBarItem
                ) {

                    oParent.hide();
    
                    // Set focus to the parent MenuItem if one exists
    
                    oMenuItem = oParent.parent;
    
                    if(oMenuItem) {
    
                        oMenuItem.focus();
                        oMenuItem.cfg.setProperty("selected", true);
    
                    }                    
                
                }
    
                Event.preventDefault(oDOMEvent);

            break;
    
    
            case 37:    // Left arrow
    
                // Only hide if this this is a MenuItem of a submenu
    
                if(oParent.parent) {
    
                    oParent.hide();
    
                    // Set focus to the parent MenuItem if one exists
    
                    oMenuItem = oParent.parent;
    
                    if(oMenuItem) {
    
                        oMenuItem.focus();
                        oMenuItem.cfg.setProperty("selected", true);
    
                    }
    
                }

                Event.preventDefault(oDOMEvent);
    
            break;        
    
        }
    
    };


/**
* "mouseover" Custom Event handler for a MenuItem instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuItem.prototype._onMouseOver = 

    function(p_sType, p_aArgs, p_oMenuItem) {

        var oParent = this.parent;
        var oConfig = this.cfg;
        var oActiveItem = oParent.activeItem;
    
    
        // Hide any other submenus that might be visible
    
        if(oActiveItem && oActiveItem != this) {
    
            oParent.clearActiveItem();
    
        }
    
    
        // Select and focus the current MenuItem instance
    
        oConfig.setProperty("selected", true);
        this.focus();
    
    
        // Show the submenu for this instance
    
        var oSubmenu = oConfig.getProperty("submenu");
    
        if(oSubmenu) {
    
            oSubmenu.show();
    
        }
    
    };


/**
* "mouseout" Custom Event handler for a MenuItem instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuItem.prototype._onMouseOut = 

    function(p_sType, p_aArgs, p_oMenuItem) {
    
        var oConfig = this.cfg;
        var oSubmenu = oConfig.getProperty("submenu");

        oConfig.setProperty("selected", false);
    
        if(oSubmenu) {
    
            var oDOMEvent = p_aArgs[0];
            var oRelatedTarget = YAHOO.util.Event.getRelatedTarget(oDOMEvent);
    
            if(
                !(
                    oRelatedTarget == oSubmenu.element || 
                    YAHOO.util.Dom.isAncestor(oSubmenu.element, oRelatedTarget)
                )
            ) {
    
                oSubmenu.hide();
    
            }
    
        }
    
    };


// Event handlers for configuration properties

/**
* Event handler for when the "checked" configuration property of
* a MenuItem instance changes. 
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the 
* event was fired.
* @param {YAHOO.widget.MenuItem} p_oItem The MenuItem instance 
* that fired the event.
*/    
YAHOO.widget.MenuItem.prototype.configChecked =

    function(p_sType, p_aArgs, p_oItem) {
    
        var Dom = YAHOO.util.Dom;
        var bChecked = p_aArgs[0];
        var oEl = this.element;
        var oConfig = this.cfg;
        var oImg;
        

        if(bChecked) {

            var me = this;

            function preloadImage(p_sPath) {

                var sPath = me.imageRoot + p_sPath;

                if(!document.images[sPath]) {

                    var oImg = document.createElement("img");
                    oImg.src = sPath;
                    oImg.name = sPath;
                    oImg.id = sPath;
                    oImg.style.display = "none";
                    
                    document.body.appendChild(oImg);

                }
            
            }

            preloadImage(this.CHECKED_IMAGE_PATH);
            preloadImage(this.SELECTED_CHECKED_IMAGE_PATH);
            preloadImage(this.DISABLED_CHECKED_IMAGE_PATH);


            oImg = document.createElement("img");
            oImg.src = (this.imageRoot + this.CHECKED_IMAGE_PATH);
            oImg.alt = this.CHECKED_IMAGE_ALT_TEXT;

            var oSubmenu = this.cfg.getProperty("submenu");

            if(oSubmenu) {

                oEl.insertBefore(oImg, oSubmenu.element);

            }
            else {

                oEl.appendChild(oImg);            

            }


            Dom.addClass([oEl, oImg], "checked");

            this._checkImage = oImg;

            if(oConfig.getProperty("disabled")) {

                oConfig.refireEvent("disabled");

            }

            if(oConfig.getProperty("selected")) {

                oConfig.refireEvent("selected");

            }
        
        }
        else {

            oImg = this._checkImage;

            Dom.removeClass([oEl, oImg], "checked");

            if(oImg) {

                oEl.removeChild(oImg);

            }

            this._checkImage = null;
        
        }

    };
    

/**
* Event handler for when the "selected" configuration property of
* a MenuItem instance changes. 
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the 
* event was fired.
* @param {YAHOO.widget.MenuItem} p_oItem The MenuItem instance 
* that fired the event.
*/    
YAHOO.widget.MenuItem.prototype.configSelected = 

    function(p_sType, p_aArgs, p_oItem) {

        YAHOO.widget.MenuItem.superclass.configSelected.call(
                this, p_sType, p_aArgs, p_oItem
            );        
    
        var oConfig = this.cfg;

        if(!oConfig.getProperty("disabled") && oConfig.getProperty("checked")) {

            var bSelected = p_aArgs[0];

            var sSrc = this.imageRoot + (bSelected ? 
                this.SELECTED_CHECKED_IMAGE_PATH : this.CHECKED_IMAGE_PATH);

            this._checkImage.src = document.images[sSrc].src;
            
        }            
    
    };


/**
* Event handler for when the "disabled" configuration property of
* a MenuItem instance changes. 
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the 
* event was fired.
* @param {YAHOO.widget.MenuItem} p_oItem The MenuItem instance 
* that fired the event.
*/    
YAHOO.widget.MenuItem.prototype.configDisabled = 

    function(p_sType, p_aArgs, p_oItem) {
    
        YAHOO.widget.MenuItem.superclass.configDisabled.call(
                this, p_sType, p_aArgs, p_oItem
            );        
    
        if(this.cfg.getProperty("checked")) {
    
            var bDisabled = p_aArgs[0];
            var sAlt = this.CHECKED_IMAGE_ALT_TEXT;
            var sSrc = this.CHECKED_IMAGE_PATH;
            var oImg = this._checkImage;
            
            if(bDisabled) {
    
                sAlt = this.DISABLED_CHECKED_IMAGE_ALT_TEXT;
                sSrc = this.DISABLED_CHECKED_IMAGE_PATH;
            
            }

            oImg.src = document.images[(this.imageRoot + sSrc)].src;
            oImg.alt = sAlt;
            
        }    
            
    };


// Public methods
    
/**
* Initializes the class's configurable properties which can be changed using 
* the MenuModule's Config object (cfg).
*/
YAHOO.widget.MenuItem.prototype.initDefaultConfig = function() {

    YAHOO.widget.MenuItem.superclass.initDefaultConfig.call(this);

	// Add configuration properties

    this.cfg.addProperty(
        "checked", 
        {
            value: false, 
            handler: this.configChecked, 
            validator: this.cfg.checkBoolean, 
            suppressEvent: true 
        } 
    );

};


/**
* @class Creates a list of options which vary depending on the context in 
* which the menu is invoked.
* @constructor
* @extends YAHOO.widget.Menu
* @base YAHOO.widget.Menu
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a ContextMenu instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.ContextMenu = function(p_oElement, p_oConfig) {

    YAHOO.widget.ContextMenu.superclass.constructor.call(
            this, 
            p_oElement,
            p_oConfig
        );

};

YAHOO.extend(YAHOO.widget.ContextMenu, YAHOO.widget.Menu);


YAHOO.widget.ContextMenu.prototype._oTrigger = null;


/**
* The ContextMenu class's initialization method. This method is automatically  
* called by the constructor, and sets up all DOM references for pre-existing 
* markup, and creates required markup if it is not already present.
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a ContextMenu instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.ContextMenu.prototype.init = function(p_oElement, p_oConfig) {

    if(!this.ITEM_TYPE) {

        this.ITEM_TYPE = YAHOO.widget.ContextMenuItem;

    }


    // Call the init of the superclass (YAHOO.widget.Menu)

    YAHOO.widget.ContextMenu.superclass.init.call(this, p_oElement);


    this.beforeInitEvent.fire(YAHOO.widget.ContextMenu);


    if(p_oConfig) {

        this.cfg.applyConfig(p_oConfig, true);

    }
    
    
    this.initEvent.fire(YAHOO.widget.ContextMenu);


};


// Private event handlers

/**
* "mousedown" event handler for the document object.
* @private
* @param {Event} p_oEvent Event object passed back by the 
* event utility (YAHOO.util.Event).
* @param {YAHOO.widget.ContextMenu} p_oMenu The ContextMenu instance 
* handling the event.
*/
YAHOO.widget.ContextMenu.prototype._onDocumentMouseDown = 

    function(p_oEvent, p_oMenu) {
    
        var oTarget = YAHOO.util.Event.getTarget(p_oEvent);
        var oTargetEl = this._oTargetElement;
    
        if(
            oTarget != oTargetEl || 
            !YAHOO.util.Dom.isAncestor(oTargetEl, oTarget)
        ) {
    
            this.hide();
        
        }
    
    };


/**
* "click" event handler for the HTMLElement node that triggered the event. 
* Used to cancel default behaviors in Opera.
* @private
* @param {Event} p_oEvent Event object passed back by the 
* event utility (YAHOO.util.Event).
* @param {YAHOO.widget.ContextMenu} p_oMenu The ContextMenu instance 
* handling the event.
*/
YAHOO.widget.ContextMenu.prototype._onTriggerClick = 

    function(p_oEvent, p_oMenu) {

        if(p_oEvent.ctrlKey) {
        
            YAHOO.util.Event.stopEvent(p_oEvent);
    
        }
        
    };


/**
* "contextmenu" event handler ("mousedown" for Opera) for the HTMLElement 
* node that triggered the event.
* @private
* @param {Event} p_oEvent Event object passed back by the 
* event utility (YAHOO.util.Event).
* @param {YAHOO.widget.ContextMenu} p_oMenu The ContextMenu instance 
* handling the event.
*/
YAHOO.widget.ContextMenu.prototype._onTriggerContextMenu = 

    function(p_oEvent, p_oMenu) {

        var Event = YAHOO.util.Event;
        var oConfig = this.cfg;

        if(p_oEvent.type == "mousedown") {
        
            if(!p_oEvent.ctrlKey) {
    
                return;
            
            }
        
            Event.stopEvent(p_oEvent);
    
        }
    
    
        this.contextEventTarget = Event.getTarget(p_oEvent);
    
    
        // Position and display the context menu
    
        var nX = Event.getPageX(p_oEvent);
        var nY = Event.getPageY(p_oEvent);
    
    
        oConfig.applyConfig( { x:nX, y:nY, visible:true } );
        oConfig.fireQueue();
    
    
        // Prevent the browser's default context menu from appearing
    
        Event.preventDefault(p_oEvent);
    
    };


// Public properties

/**
* Returns the HTMLElement node that was the target of the "contextmenu" 
* DOM event.
* @type HTMLElement
*/
YAHOO.widget.ContextMenu.prototype.contextEventTarget = null;


// Public methods

/**
* Initializes the class's configurable properties which can be changed using 
* a ContextMenu instance's Config object (cfg).
*/
YAHOO.widget.ContextMenu.prototype.initDefaultConfig = function() {

    YAHOO.widget.ContextMenu.superclass.initDefaultConfig.call(this);


	// Add a configuration property

    this.cfg.addProperty("trigger", { handler: this.configTrigger });

};


// Event handlers for configuration properties

/**
* Event handler for when the "trigger" configuration property of
* a MenuItem instance. 
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the 
* event was fired.
* @param {YAHOO.widget.ContextMenu} p_oMenu The ContextMenu that instance fired
* the event.
*/
YAHOO.widget.ContextMenu.prototype.configTrigger = 

    function(p_sType, p_aArgs, p_oMenu) {
    
        var Event = YAHOO.util.Event;
        var oTrigger = p_aArgs[0];
    
        if(oTrigger) {
    

            /*
                If there is a current "trigger" - remove the event handlers 
                from that element(s) before assigning new ones
            */
            if(this._oTrigger) {
            
                Event.purgeElement(this._oTrigger);

            }


            this._oTrigger = oTrigger;


            /*
                Listen for the "mousedown" event in Opera b/c it does not 
                support the "contextmenu" event
            */ 
      
            var bOpera = (this.browser == "opera");
    
            Event.addListener(
                oTrigger, 
                (bOpera ? "mousedown" : "contextmenu"), 
                this._onTriggerContextMenu,
                this,
                true
            );
    
    
            /*
                Assign a "click" event handler to the trigger element(s) for
                Opera to prevent default browser behaviors.
            */
    
            if(bOpera) {
            
                Event.addListener(
                    oTrigger, 
                    "click", 
                    this._onTriggerClick,
                    this,
                    true
                );
    
            }
    
    
            // Assign a "mousedown" event handler to the document
        
            Event.addListener(
                document, 
                "mousedown", 
                this._onDocumentMouseDown,
                this,
                true
            );        
    
        }
        
    };


/**
* @class Creates an item for a context menu instance.
* @constructor
* @extends YAHOO.widget.MenuItem
* @base YAHOO.widget.MenuItem
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a ContextMenuItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.ContextMenuItem = function(p_oObject, p_oConfig) {

    YAHOO.widget.ContextMenuItem.superclass.constructor.call(
        this, 
        p_oObject, 
        p_oConfig
    );

};

YAHOO.extend(YAHOO.widget.ContextMenuItem, YAHOO.widget.MenuItem);


/**
* The ContextMenuItem class's initialization method. This method is
* automatically called by the constructor, and sets up all DOM references for
* pre-existing markup, and creates required markup if it is not
* already present.
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a ContextMenuItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.ContextMenuItem.prototype.init = 

    function(p_oObject, p_oConfig) {
    
        if(!this.SUBMENU_TYPE) {
    
            this.SUBMENU_TYPE = YAHOO.widget.ContextMenu;
    
        }
    
        if(!this.SUBMENU_ITEM_TYPE) {
    
            this.SUBMENU_ITEM_TYPE = YAHOO.widget.ContextMenuItem;
    
        }
    
    
        /* 
            Call the init of the superclass (YAHOO.widget.MenuItem)
            Note: We don't pass the user config in here yet 
            because we only want it executed once, at the lowest 
            subclass level.
        */ 
    
        YAHOO.widget.ContextMenuItem.superclass.init.call(this, p_oObject);

        var oConfig = this.cfg;
    
        if(p_oConfig) {
    
            oConfig.applyConfig(p_oConfig, true);
    
        }
    
        oConfig.fireQueue();
    
    };


/**
* @class Horizontal collection of items, each of which can contain a submenu.
* Extends YAHOO.widget.MenuModule to provide a set of default mouse and 
* key event behaviors.
* @constructor
* @extends YAHOO.widget.MenuModule
* @base YAHOO.widget.MenuModule
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a MenuBar instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.MenuBar = function(p_oElement, p_oConfig) {

    YAHOO.widget.MenuBar.superclass.constructor.call(
            this, 
            p_oElement,
            p_oConfig
        );

};

YAHOO.extend(YAHOO.widget.MenuBar, YAHOO.widget.MenuModule);


/**
* The MenuBar class's initialization method. This method is automatically 
* called by the constructor, and sets up all DOM references for pre-existing 
* markup, and creates required markup if it is not already present.
* @param {String or HTMLElement} p_oElement String id or HTMLElement 
* (either HTMLSelectElement or HTMLDivElement) of the source HTMLElement node.
* @param {Object} p_oConfig Optional. The configuration object literal 
* containing the configuration for a MenuBar instance. See 
* configuration class documentation for more details.
*/
YAHOO.widget.MenuBar.prototype.init = function(p_oElement, p_oConfig) {

    if(!this.ITEM_TYPE) {

        this.ITEM_TYPE = YAHOO.widget.MenuBarItem;

    }


    // Call the init of the superclass (YAHOO.widget.MenuModule)

    YAHOO.widget.MenuBar.superclass.init.call(this, p_oElement);


    this.beforeInitEvent.fire(YAHOO.widget.MenuBar);

    var oConfig = this.cfg;

    /*
        Set the default value for the "position" configuration property
        to "static" 
    */
    if(!p_oConfig || (p_oConfig && !p_oConfig.position)) {

        oConfig.queueProperty("position", "static");

    }

    /*
        Set the default value for the "submenualignment" configuration property
        to "tl" and "bl" 
    */
    if(!p_oConfig || (p_oConfig && !p_oConfig.submenualignment)) {

        oConfig.queueProperty("submenualignment", ["tl","bl"]);

    }


    if(p_oConfig) {

        oConfig.applyConfig(p_oConfig, true);

    }
    
    this.initEvent.fire(YAHOO.widget.MenuBar);

};


// Constants

/**
* Constant representing the CSS class(es) to be applied to the root 
* HTMLDivElement of the MenuBar instance.
* @final
* @type String
*/
YAHOO.widget.MenuBar.prototype.CSS_CLASS_NAME = "yuimenubar";


/**
* @class The MenuBarItem class allows you to create and modify an item for a
* MenuBar instance.  MenuBarItem extends YAHOO.widget.MenuModuleItem to provide 
* a set of default mouse and key event behaviors.
* @constructor
* @extends YAHOO.widget.MenuModuleItem
* @base YAHOO.widget.MenuModuleItem
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a MenuBarItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.MenuBarItem = function(p_oObject, p_oConfig) {

    YAHOO.widget.MenuBarItem.superclass.constructor.call(
        this, 
        p_oObject, 
        p_oConfig
    );

};

YAHOO.extend(YAHOO.widget.MenuBarItem, YAHOO.widget.MenuModuleItem);


/**
* The MenuBarItem class's initialization method. This method is automatically
* called by the constructor, and sets up all DOM references for
* pre-existing markup, and creates required markup if it is not
* already present.
* @param {String or HTMLElement} p_oObject String or HTMLElement 
* (either HTMLLIElement, HTMLOptGroupElement or HTMLOptionElement) of the 
* source HTMLElement node.
* @param {Object} p_oConfig The configuration object literal containing 
* the configuration for a MenuBarItem instance. See the configuration 
* class documentation for more details.
*/
YAHOO.widget.MenuBarItem.prototype.init = function(p_oObject, p_oConfig) {

    if(!this.SUBMENU_TYPE) {

        this.SUBMENU_TYPE = YAHOO.widget.Menu;

    }

    if(!this.SUBMENU_ITEM_TYPE) {

        this.SUBMENU_ITEM_TYPE = YAHOO.widget.MenuItem;

    }


    /* 
        Call the init of the superclass (YAHOO.widget.MenuModuleItem)
        Note: We don't pass the user config in here yet 
        because we only want it executed once, at the lowest 
        subclass level.
    */ 

    YAHOO.widget.MenuBarItem.superclass.init.call(this, p_oObject);  


    // Add event handlers to each "MenuBarItem" instance

    this.keyDownEvent.subscribe(this._onKeyDown, this, true);

    var oConfig = this.cfg;

    if(p_oConfig) {

        oConfig.applyConfig(p_oConfig, true);

    }

    oConfig.fireQueue();

};


// Constants

/**
* Constant representing the CSS class(es) to be applied to the root 
* HTMLLIElement of the MenuBarItem.
* @final
* @type String
*/
YAHOO.widget.MenuBarItem.prototype.CSS_CLASS_NAME = "yuimenubaritem";


/**
* Constant representing the path to the image to be used for the submenu
* arrow indicator.
* @final
* @type String
*/
YAHOO.widget.MenuBarItem.prototype.SUBMENU_INDICATOR_IMAGE_PATH =
    "nt/ic/ut/alt1/menuarodwn8_nrm_1.gif";


/**
* Constant representing the path to the image to be used for the submenu
* arrow indicator when a MenuBarItem instance is selected.
* @final
* @type String
*/
YAHOO.widget.MenuBarItem.prototype.SELECTED_SUBMENU_INDICATOR_IMAGE_PATH =
    "nt/ic/ut/alt1/menuarodwn8_hov_1.gif";


/**
* Constant representing the path to the image to be used for the submenu
* arrow indicator when a MenuBarItem instance is disabled.
* @final
* @type String
*/
YAHOO.widget.MenuBarItem.prototype.DISABLED_SUBMENU_INDICATOR_IMAGE_PATH = 
    "nt/ic/ut/alt1/menuarodwn8_dim_1.gif";


// Private event handlers

/**
* "keydown" Custom Event handler for a MenuBarItem instance.
* @private
* @param {String} p_sType The name of the event that was fired.
* @param {Array} p_aArgs Collection of arguments sent when the event 
* was fired.
* @param {YAHOO.widget.MenuModule} p_oMenuModule The MenuModule instance that 
* fired the event.
*/
YAHOO.widget.MenuBarItem.prototype._onKeyDown =

    function(p_sType, p_aArgs, p_oMenuItem) {

        var Event = YAHOO.util.Event;
        var oDOMEvent = p_aArgs[0];
        var oConfig = this.cfg;
        var oParent = this.parent;
    
        switch(oDOMEvent.keyCode) {
    
            case 37:    // Left arrow
            case 39:    // Right arrow
    
                if(
                    this == oParent.activeItem && 
                    !oConfig.getProperty("selected")
                ) {
    
                    oConfig.setProperty("selected", true);
    
                }
                else {
    
                    var oNextItem = (oDOMEvent.keyCode == 37) ? 
                            this.getPreviousEnabledSibling() : 
                            this.getNextEnabledSibling();
            
                    if(oNextItem) {

                        oParent.clearActiveItem();

                        oNextItem.cfg.setProperty("selected", true);
            
                        oNextItem.focus();
    
                    }
    
                }

                Event.preventDefault(oDOMEvent);
    
            break;
    
            case 40:    // Down arrow

                oParent.clearActiveItem();
                        
                oConfig.setProperty("selected", true);
                
                this.focus();

                var oSubmenu = oConfig.getProperty("submenu");
    
                if(oSubmenu) {
        
                    oSubmenu.show();
                    oSubmenu.setInitialSelection();
    
                }

                Event.preventDefault(oDOMEvent);
    
            break;
    
        }
    
    };
