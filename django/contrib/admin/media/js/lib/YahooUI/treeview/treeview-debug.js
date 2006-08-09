
/*                                                                                                                                                      
Copyright (c) 2006, Yahoo! Inc. All rights reserved.                                                                                                    
Code licensed under the BSD License:                                                                                                                    
http://developer.yahoo.net/yui/license.txt                                                                                                              
version: 0.11.0                                                                                                                                         
*/ 

/**
 * Contains the tree view state data and the root node.  This is an
 * ordered tree; child nodes will be displayed in the order created, and
 * there currently is no way to change this.
 *
 * @constructor
 * @param {string|HTMLElement} id The id of the element, or the element
 * itself that the tree will be inserted into.
 */
YAHOO.widget.TreeView = function(id) {
    if (id) { this.init(id); }
};

/**
 * Count of all nodes in all trees
 * @type int
 */
YAHOO.widget.TreeView.nodeCount = 0;

YAHOO.widget.TreeView.prototype = {

    /**
     * The id of tree container element
     *
     * @type String
     */
    id: null,

    /**
     * The host element for this tree
     * @private
     */
    _el: null,

     /**
     * Flat collection of all nodes in this tree
     *
     * @type Node[]
     * @private
     */
    _nodes: null,

    /**
     * We lock the tree control while waiting for the dynamic loader to return
     *
     * @type boolean
     */
    locked: false,

    /**
     * The animation to use for expanding children, if any
     *
     * @type string
     * @private
     */
    _expandAnim: null,

    /**
     * The animation to use for collapsing children, if any
     *
     * @type string
     * @private
     */
    _collapseAnim: null,

    /**
     * The current number of animations that are executing
     *
     * @type int
     * @private
     */
    _animCount: 0,

    /**
     * The maximum number of animations to run at one time.
     *
     * @type int
     */
    maxAnim: 2,

    /**
     * Sets up the animation for expanding children
     *
     * @param {string} the type of animation (acceptable values defined in 
     * YAHOO.widget.TVAnim)
     */
    setExpandAnim: function(type) {
        if (YAHOO.widget.TVAnim.isValid(type)) {
            this._expandAnim = type;
        }
    },

    /**
     * Sets up the animation for collapsing children
     *
     * @param {string} the type of animation (acceptable values defined in 
     * YAHOO.widget.TVAnim)
     */
    setCollapseAnim: function(type) {
        if (YAHOO.widget.TVAnim.isValid(type)) {
            this._collapseAnim = type;
        }
    },

    /**
     * Perform the expand animation if configured, or just show the
     * element if not configured or too many animations are in progress
     *
     * @param el {HTMLElement} the element to animate
     * @return {boolean} true if animation could be invoked, false otherwise
     */
    animateExpand: function(el) {
        this.logger.log("animating expand");

        if (this._expandAnim && this._animCount < this.maxAnim) {
            // this.locked = true;
            var tree = this;
            var a = YAHOO.widget.TVAnim.getAnim(this._expandAnim, el, 
                            function() { tree.expandComplete(); });
            if (a) { 
                ++this._animCount;
                a.animate();
            }

            return true;
        }

        return false;
    },

    /**
     * Perform the collapse animation if configured, or just show the
     * element if not configured or too many animations are in progress
     *
     * @param el {HTMLElement} the element to animate
     * @return {boolean} true if animation could be invoked, false otherwise
     */
    animateCollapse: function(el) {
        this.logger.log("animating collapse");

        if (this._collapseAnim && this._animCount < this.maxAnim) {
            // this.locked = true;
            var tree = this;
            var a = YAHOO.widget.TVAnim.getAnim(this._collapseAnim, el, 
                            function() { tree.collapseComplete(); });
            if (a) { 
                ++this._animCount;
                a.animate();
            }

            return true;
        }

        return false;
    },

    /**
     * Function executed when the expand animation completes
     */
    expandComplete: function() {
        this.logger.log("expand complete: " + this.id);
        --this._animCount;
        // this.locked = false;
    },

    /**
     * Function executed when the collapse animation completes
     */
    collapseComplete: function() {
        this.logger.log("collapse complete: " + this.id);
        --this._animCount;
        // this.locked = false;
    },

    /**
     * Initializes the tree
     *
     * @parm {string|HTMLElement} id the id of the element that will hold the tree
     * @private
     */
    init: function(id) {

        this.id = id;

        if ("string" !== typeof id) {
            this._el = id;
            this.id = this.generateId(id);
        }

        this._nodes = [];

        // store a global reference
        YAHOO.widget.TreeView.trees[this.id] = this;

        // Set up the root node
        this.root = new YAHOO.widget.RootNode(this);

        this.logger = new YAHOO.widget.LogWriter(this.toString());

        this.logger.log("tree init: " + this.id);
    },

    /**
     * Renders the tree boilerplate and visible nodes
     */
    draw: function() {
        var html = this.root.getHtml();
        this.getEl().innerHTML = html;
        this.firstDraw = false;
    },

    /**
     * Returns the tree's host element
     * @return {HTMLElement} the host element
     */
    getEl: function() {
        if (! this._el) {
            this._el = document.getElementById(this.id);
        }
        return this._el;
    },

    /**
     * Nodes register themselves with the tree instance when they are created.
     *
     * @param node {Node} the node to register
     * @private
     */
    regNode: function(node) {
        this._nodes[node.index] = node;
    },

    /**
     * Returns the root node of this tree
     *
     * @return {Node} the root node
     */
    getRoot: function() {
        return this.root;
    },

    /**
     * Configures this tree to dynamically load all child data
     *
     * @param {function} fnDataLoader the function that will be called to get the data
     * @param iconMode {int} configures the icon that is displayed when a dynamic
     * load node is expanded the first time without children.  By default, the 
     * "collapse" icon will be used.  If set to 1, the leaf node icon will be
     * displayed.
     */
    setDynamicLoad: function(fnDataLoader, iconMode) { 
        this.root.setDynamicLoad(fnDataLoader, iconMode);
    },

    /**
     * Expands all child nodes.  Note: this conflicts with the "multiExpand"
     * node property.  If expand all is called in a tree with nodes that
     * do not allow multiple siblings to be displayed, only the last sibling
     * will be expanded.
     */
    expandAll: function() { 
        if (!this.locked) {
            this.root.expandAll(); 
        }
    },

    /**
     * Collapses all expanded child nodes in the entire tree.
     */
    collapseAll: function() { 
        if (!this.locked) {
            this.root.collapseAll(); 
        }
    },

    /**
     * Returns a node in the tree that has the specified index (this index
     * is created internally, so this function probably will only be used
     * in html generated for a given node.)
     *
     * @param {int} nodeIndex the index of the node wanted
     * @return {Node} the node with index=nodeIndex, null if no match
     */
    getNodeByIndex: function(nodeIndex) {
        var n = this._nodes[nodeIndex];
        return (n) ? n : null;
    },

    /**
     * Returns a node that has a matching property and value in the data
     * object that was passed into its constructor.
     *
     * @param {object} property the property to search (usually a string)
     * @param {object} value the value we want to find (usuall an int or string)
     * @return {Node} the matching node, null if no match
     */
    getNodeByProperty: function(property, value) {
        for (var i in this._nodes) {
            var n = this._nodes[i];
            if (n.data && value == n.data[property]) {
                return n;
            }
        }

        return null;
    },

    /**
     * Returns a collection of nodes that have a matching property 
     * and value in the data object that was passed into its constructor.  
     *
     * @param {object} property the property to search (usually a string)
     * @param {object} value the value we want to find (usuall an int or string)
     * @return {Array} the matching collection of nodes, null if no match
     */
    getNodesByProperty: function(property, value) {
        var values = [];
        for (var i in this._nodes) {
            var n = this._nodes[i];
            if (n.data && value == n.data[property]) {
                values.push(n);
            }
        }

        return (values.length) ? values : null;
    },

    /**
     * Removes the node and its children, and optionally refreshes the branch 
     * of the tree that was affected.
     * @param {Node} The node to remove
     * @param {boolean} autoRefresh automatically refreshes branch if true
     * @return {boolean} False is there was a problem, true otherwise.
     */
    removeNode: function(node, autoRefresh) { 

        // Don't delete the root node
        if (node.isRoot()) {
            return false;
        }

        // Get the branch that we may need to refresh
        var p = node.parent;
        if (p.parent) {
            p = p.parent;
        }

        // Delete the node and its children
        this._deleteNode(node);

        // Refresh the parent of the parent
        if (autoRefresh && p && p.childrenRendered) {
            p.refresh();
        }

        return true;
    },

    /**
     * Deletes this nodes child collection, recursively.  Also collapses
     * the node, and resets the dynamic load flag.  The primary use for
     * this method is to purge a node and allow it to fetch its data
     * dynamically again.
     * @param {Node} node the node to purge
     */
    removeChildren: function(node) { 
        this.logger.log("Removing children for " + node);
        while (node.children.length) {
             this._deleteNode(node.children[0]);
        }

        node.childrenRendered = false;
        node.dynamicLoadComplete = false;
        // node.collapse();
        node.expand();
        node.collapse();
    },

    /**
     * Deletes the node and recurses children
     * @private
     */
    _deleteNode: function(node) { 
        // Remove all the child nodes first
        this.removeChildren(node);

        // Remove the node from the tree
        this.popNode(node);
    },

    /**
     * Removes the branch from the tree.  This differs from removeNode in
     * that the child collection is preserved to make it possible to
     * insert the branch into another part of the tree, or another tree.
     * @param {Node} the node to remove
     */
    popNode: function(node) { 
        var p = node.parent;

        // Update the parent's collection of children
        var a = [];

        for (var i=0, len=p.children.length;i<len;++i) {
            if (p.children[i] != node) {
                a[a.length] = p.children[i];
            }
        }

        p.children = a;

        // reset the childrenRendered flag for the parent
        p.childrenRendered = false;

         // Update the sibling relationship
        if (node.previousSibling) {
            node.previousSibling.nextSibling = node.nextSibling;
        }

        if (node.nextSibling) {
            node.nextSibling.previousSibling = node.previousSibling;
        }

        // Update the tree's node collection 
        delete this._nodes[node.index];
    },


    /**
     * toString
     * @return {string} string representation of the tree
     */
    toString: function() {
        return "TreeView " + this.id;
    },

    /**
     * private
     */
    generateId: function(el) {
        var id = el.id;

        if (!id) {
            id = "yui-tv-auto-id-" + YAHOO.widget.TreeView.counter;
            YAHOO.widget.TreeView.counter++;
        }

        return id;
    },

    /**
     * Abstract method that is executed when a node is expanded
     * @param node {Node} the node that was expanded
     */
    onExpand: function(node) { },

    /**
     * Abstract method that is executed when a node is collapsed
     * @param node {Node} the node that was collapsed.
     */
    onCollapse: function(node) { }

};

/**
 * Global cache of tree instances
 *
 * @type Array
 * @private
 */
YAHOO.widget.TreeView.trees = [];

/**
 * @private
 */
YAHOO.widget.TreeView.counter = 0;

/**
 * Global method for getting a tree by its id.  Used in the generated
 * tree html.
 *
 * @param treeId {String} the id of the tree instance
 * @return {TreeView} the tree instance requested, null if not found.
 */
YAHOO.widget.TreeView.getTree = function(treeId) {
    var t = YAHOO.widget.TreeView.trees[treeId];
    return (t) ? t : null;
};


/**
 * Global method for getting a node by its id.  Used in the generated
 * tree html.
 *
 * @param treeId {String} the id of the tree instance
 * @param nodeIndex {String} the index of the node to return
 * @return {Node} the node instance requested, null if not found
 */
YAHOO.widget.TreeView.getNode = function(treeId, nodeIndex) {
    var t = YAHOO.widget.TreeView.getTree(treeId);
    return (t) ? t.getNodeByIndex(nodeIndex) : null;
};

/**
 * Adds an event.  Replace with event manager when available
 *
 * @param el the elment to bind the handler to
 * @param {string} sType the type of event handler
 * @param {function} fn the callback to invoke
 * @param {boolean} capture if true event is capture phase, bubble otherwise
 */
YAHOO.widget.TreeView.addHandler = function (el, sType, fn, capture) {
    capture = (capture) ? true : false;
    if (el.addEventListener) {
        el.addEventListener(sType, fn, capture);
    } else if (el.attachEvent) {
        el.attachEvent("on" + sType, fn);
    } else {
        el["on" + sType] = fn;
    }
};

/**
 * Attempts to preload the images defined in the styles used to draw the tree by
 * rendering off-screen elements that use the styles.
 */
YAHOO.widget.TreeView.preload = function(prefix) {
    prefix = prefix || "ygtv";
    var styles = ["tn","tm","tmh","tp","tph","ln","lm","lmh","lp","lph","loading"];

    var sb = [];
    
    for (var i = 0; i < styles.length; ++i) { 
        sb[sb.length] = '<span class="' + prefix + styles[i] + '">&#160;</span>';
    }

    var f = document.createElement("DIV");
    var s = f.style;
    s.position = "absolute";
    s.top = "-1000px";
    s.left = "-1000px";
    f.innerHTML = sb.join("");

    document.body.appendChild(f);
};

YAHOO.widget.TreeView.addHandler(window, 
                "load", YAHOO.widget.TreeView.preload);

/**
 * The base class for all tree nodes.  The node's presentation and behavior in
 * response to mouse events is handled in Node subclasses.
 *
 * @param oData {object} a string or object containing the data that will
 * be used to render this node
 * @param oParent {Node} this node's parent node
 * @param expanded {boolean} the initial expanded/collapsed state
 * @constructor
 */
YAHOO.widget.Node = function(oData, oParent, expanded) {
    if (oData) { this.init(oData, oParent, expanded); }
};

YAHOO.widget.Node.prototype = {

    /**
     * The index for this instance obtained from global counter in YAHOO.widget.TreeView.
     *
     * @type int
     */
    index: 0,

    /**
     * This node's child node collection.
     *
     * @type Node[] 
     */
    children: null,

    /**
     * Tree instance this node is part of
     *
     * @type TreeView
     */
    tree: null,

    /**
     * The data linked to this node.  This can be any object or primitive
     * value, and the data can be used in getNodeHtml().
     *
     * @type object
     */
    data: null,

    /**
     * Parent node
     *
     * @type Node
     */
    parent: null,

    /**
     * The depth of this node.  We start at -1 for the root node.
     *
     * @type int
     */
    depth: -1,

    /**
     * The href for the node's label.  If one is not specified, the href will
     * be set so that it toggles the node.
     *
     * @type string
     */
    href: null,

    /**
     * The label href target, defaults to current window
     *
     * @type string
     */
    target: "_self",

    /**
     * The node's expanded/collapsed state
     *
     * @type boolean
     */
    expanded: false,

    /**
     * Can multiple children be expanded at once?
     *
     * @type boolean
     */
    multiExpand: true,

    /**
     * Should we render children for a collapsed node?  It is possible that the
     * implementer will want to render the hidden data...  @todo verify that we 
     * need this, and implement it if we do.
     *
     * @type boolean
     */
    renderHidden: false,

    /**
     * This flag is set to true when the html is generated for this node's
     * children, and set to false when new children are added.
     * @type boolean
     */
    childrenRendered: false,

    /**
     * Dynamically loaded nodes only fetch the data the first time they are
     * expanded.  This flag is set to true once the data has been fetched.
     * @type boolean
     */
    dynamicLoadComplete: false,

    /**
     * This node's previous sibling
     *
     * @type Node
     */
    previousSibling: null,

    /**
     * This node's next sibling
     *
     * @type Node
     */
    nextSibling: null,

    /**
     * We can set the node up to call an external method to get the child
     * data dynamically.
     *
     * @type boolean
     * @private
     */
    _dynLoad: false,

    /**
     * Function to execute when we need to get this node's child data.
     *
     * @type function
     */
    dataLoader: null,

    /**
     * This is true for dynamically loading nodes while waiting for the
     * callback to return.
     *
     * @type boolean
     */
    isLoading: false,

    /**
     * The toggle/branch icon will not show if this is set to false.  This
     * could be useful if the implementer wants to have the child contain
     * extra info about the parent, rather than an actual node.
     *
     * @type boolean
     */
    hasIcon: true,

    /**
     * Used to configure what happens when a dynamic load node is expanded
     * and we discover that it does not have children.  By default, it is
     * treated as if it still could have children (plus/minus icon).  Set
     * iconMode to have it display like a leaf node instead.
     * @type int
     */
    iconMode: 0,

    /**
     * The node type
     * @private
     */
    _type: "Node",

    /*
    spacerPath: "http://us.i1.yimg.com/us.yimg.com/i/space.gif",
    expandedText: "Expanded",
    collapsedText: "Collapsed",
    loadingText: "Loading",
    */

    /**
     * Initializes this node, gets some of the properties from the parent
     *
     * @param oData {object} a string or object containing the data that will
     * be used to render this node
     * @param oParent {Node} this node's parent node
     * @param expanded {boolean} the initial expanded/collapsed state
     */
    init: function(oData, oParent, expanded) {
        this.data       = oData;
        this.children   = [];
        this.index      = YAHOO.widget.TreeView.nodeCount;
        ++YAHOO.widget.TreeView.nodeCount;
        this.expanded   = expanded;
        this.logger     = new YAHOO.widget.LogWriter(this.toString());

        // oParent should never be null except when we create the root node.
        if (oParent) {
            oParent.appendChild(this);
        }
    },

    /**
     * Certain properties for the node cannot be set until the parent
     * is known. This is called after the node is inserted into a tree.
     * the parent is also applied to this node's children in order to
     * make it possible to move a branch from one tree to another.
     * @param {Node} parentNode this node's parent node
     */
    applyParent: function(parentNode) {
        if (!parentNode) {
            return false;
        }

        this.tree   = parentNode.tree;
        this.parent = parentNode;
        this.depth  = parentNode.depth + 1;

        if (! this.href) {
            this.href = "javascript:" + this.getToggleLink();
        }

        if (! this.multiExpand) {
            this.multiExpand = parentNode.multiExpand;
        }

        this.tree.regNode(this);
        parentNode.childrenRendered = false;

        // cascade update existing children
        for (var i=0, len=this.children.length;i<len;++i) {
            this.children[i].applyParent(this);
        }

        return true;
    },

    /**
     * Appends a node to the child collection.
     *
     * @param childNode {Node} the new node
     * @return {Node} the child node
     * @private
     */
    appendChild: function(childNode) {
        if (this.hasChildren()) {
            var sib = this.children[this.children.length - 1];
            sib.nextSibling = childNode;
            childNode.previousSibling = sib;
        }
        this.children[this.children.length] = childNode;
        childNode.applyParent(this);

        return childNode;
    },

    /**
     * Appends this node to the supplied node's child collection
     * @param parentNode {Node} the node to append to.
     */
    appendTo: function(parentNode) {
        return parentNode.appendChild(this);
    },

    /**
    * Inserts this node before this supplied node
    *
    * @param node {Node} the node to insert this node before
    * @return {Node} the inserted node
    */
    insertBefore: function(node) {
        this.logger.log("insertBefore: " + node);
        var p = node.parent;
        if (p) {

            if (this.tree) {
                this.tree.popNode(this);
            }

            var refIndex = node.isChildOf(p);
            this.logger.log(refIndex);
            p.children.splice(refIndex, 0, this);
            if (node.previousSibling) {
                node.previousSibling.nextSibling = this;
            }
            this.previousSibling = node.previousSibling;
            this.nextSibling = node;
            node.previousSibling = this;

            this.applyParent(p);
        }

        return this;
    },
 
    /**
    * Inserts this node after the supplied node
    *
    * @param node {Node} the node to insert after
    * @return {Node} the inserted node
    */
    insertAfter: function(node) {
        this.logger.log("insertAfter: " + node);
        var p = node.parent;
        if (p) {

            if (this.tree) {
                this.tree.popNode(this);
            }

            var refIndex = node.isChildOf(p);
            this.logger.log(refIndex);

            if (!node.nextSibling) {
                return this.appendTo(p);
            }

            p.children.splice(refIndex + 1, 0, this);

            node.nextSibling.previousSibling = this;
            this.previousSibling = node;
            this.nextSibling = node.nextSibling;
            node.nextSibling = this;

            this.applyParent(p);
        }

        return this;
    },

    /**
    * Returns true if the Node is a child of supplied Node
    *
    * @param parentNode {Node} the Node to check
    * @return {boolean} The node index if this Node is a child of 
    *                   supplied Node, else -1.
    * @private
    */
    isChildOf: function(parentNode) {
        if (parentNode && parentNode.children) {
            for (var i=0, len=parentNode.children.length; i<len ; ++i) {
                if (parentNode.children[i] === this) {
                    return i;
                }
            }
        }

        return -1;
    },

    /**
     * Returns a node array of this node's siblings, null if none.
     *
     * @return Node[]
     */
    getSiblings: function() {
        return this.parent.children;
    },

    /**
     * Shows this node's children
     */
    showChildren: function() {
        if (!this.tree.animateExpand(this.getChildrenEl())) {
            if (this.hasChildren()) {
                this.getChildrenEl().style.display = "";
            }
        }
    },

    /**
     * Hides this node's children
     */
    hideChildren: function() {
        this.logger.log("hiding " + this.index);

        if (!this.tree.animateCollapse(this.getChildrenEl())) {
            this.getChildrenEl().style.display = "none";
        }
    },

    /**
     * Returns the id for this node's container div
     *
     * @return {string} the element id
     */
    getElId: function() {
        return "ygtv" + this.index;
    },

    /**
     * Returns the id for this node's children div
     *
     * @return {string} the element id for this node's children div
     */
    getChildrenElId: function() {
        return "ygtvc" + this.index;
    },

    /**
     * Returns the id for this node's toggle element
     *
     * @return {string} the toggel element id
     */
    getToggleElId: function() {
        return "ygtvt" + this.index;
    },


    /**
     * Returns the id for this node's spacer image.  The spacer is positioned
     * over the toggle and provides feedback for screen readers.
     * @return {string} the id for the spacer image
     */
    /*
    getSpacerId: function() {
        return "ygtvspacer" + this.index;
    }, 
    */

    /**
     * Returns this node's container html element
     * @return {HTMLElement} the container html element
     */
    getEl: function() {
        return document.getElementById(this.getElId());
    },

    /**
     * Returns the div that was generated for this node's children
     * @return {HTMLElement} this node's children div
     */
    getChildrenEl: function() {
        return document.getElementById(this.getChildrenElId());
    },

    /**
     * Returns the element that is being used for this node's toggle.
     * @return {HTMLElement} this node's toggle html element
     */
    getToggleEl: function() {
        return document.getElementById(this.getToggleElId());
    },

    /**
     * Returns the element that is being used for this node's spacer.
     * @return {HTMLElement} this node's spacer html element
     */
    /*
    getSpacer: function() {
        return document.getElementById( this.getSpacerId() ) || {};
    },
    */

    /*
    getStateText: function() {
        if (this.isLoading) {
            return this.loadingText;
        } else if (this.hasChildren(true)) {
            if (this.expanded) {
                return this.expandedText;
            } else {
                return this.collapsedText;
            }
        } else {
            return "";
        }
    },
    */

    /**
     * Generates the link that will invoke this node's toggle method
     * @return {string} the javascript url for toggling this node
     */
    getToggleLink: function() {
        return "YAHOO.widget.TreeView.getNode(\'" + this.tree.id + "\'," + 
            this.index + ").toggle()";
    },

    /**
     * Hides this nodes children (creating them if necessary), changes the
     * toggle style.
     */
    collapse: function() {
        // Only collapse if currently expanded
        if (!this.expanded) { return; }

        // fire the collapse event handler
        var ret = this.tree.onCollapse(this);

        if ("undefined" != typeof ret && !ret) {
            this.logger.log("Collapse was stopped by the event handler");
            return;
        }

        if (!this.getEl()) {
            this.expanded = false;
            return;
        }

        // hide the child div
        this.hideChildren();
        this.expanded = false;

        if (this.hasIcon) {
            this.getToggleEl().className = this.getStyle();
        }

        // this.getSpacer().title = this.getStateText();

    },

    /**
     * Shows this nodes children (creating them if necessary), changes the
     * toggle style, and collapses its siblings if multiExpand is not set.
     */
    expand: function() {
        // Only expand if currently collapsed.
        if (this.expanded) { return; }

        // fire the expand event handler
        var ret = this.tree.onExpand(this);

        if ("undefined" != typeof ret && !ret) {
            this.logger.log("Expand was stopped by the event handler");
            return;
        }

        if (!this.getEl()) {
            this.expanded = true;
            return;
        }

        if (! this.childrenRendered) {
            this.logger.log("children not rendered yet");
            this.getChildrenEl().innerHTML = this.renderChildren();
        } else {
            this.logger.log("CHILDREN RENDERED");
        }

        this.expanded = true;
        if (this.hasIcon) {
            this.getToggleEl().className = this.getStyle();
        }

        // this.getSpacer().title = this.getStateText();

        // We do an extra check for children here because the lazy
        // load feature can expose nodes that have no children.

        // if (!this.hasChildren()) {
        if (this.isLoading) {
            this.expanded = false;
            return;
        }

        if (! this.multiExpand) {
            var sibs = this.getSiblings();
            for (var i=0; i<sibs.length; ++i) {
                if (sibs[i] != this && sibs[i].expanded) { 
                    sibs[i].collapse(); 
                }
            }
        }

        this.showChildren();
    },

    /**
     * Returns the css style name for the toggle
     *
     * @return {string} the css class for this node's toggle
     */
    getStyle: function() {
        // this.logger.log("No children, " + " isDyanmic: " + this.isDynamic() + " expanded: " + this.expanded);
        if (this.isLoading) {
            this.logger.log("returning the loading icon");
            return "ygtvloading";
        } else {
            // location top or bottom, middle nodes also get the top style
            var loc = (this.nextSibling) ? "t" : "l";

            // type p=plus(expand), m=minus(collapase), n=none(no children)
            var type = "n";
            if (this.hasChildren(true) || (this.isDynamic() && !this.getIconMode())) {
            // if (this.hasChildren(true)) {
                type = (this.expanded) ? "m" : "p";
            }

            // this.logger.log("ygtv" + loc + type);
            return "ygtv" + loc + type;
        }
    },

    /**
     * Returns the hover style for the icon
     * @return {string} the css class hover state
     */
    getHoverStyle: function() { 
        var s = this.getStyle();
        if (this.hasChildren(true) && !this.isLoading) { 
            s += "h"; 
        }
        return s;
    },

    /**
     * Recursively expands all of this node's children.
     */
    expandAll: function() { 
        for (var i=0;i<this.children.length;++i) {
            var c = this.children[i];
            if (c.isDynamic()) {
                alert("Not supported (lazy load + expand all)");
                break;
            } else if (! c.multiExpand) {
                alert("Not supported (no multi-expand + expand all)");
                break;
            } else {
                c.expand();
                c.expandAll();
            }
        }
    },

    /**
     * Recursively collapses all of this node's children.
     */
    collapseAll: function() { 
        for (var i=0;i<this.children.length;++i) {
            this.children[i].collapse();
            this.children[i].collapseAll();
        }
    },

    /**
     * Configures this node for dynamically obtaining the child data
     * when the node is first expanded.  Calling it without the callback
     * will turn off dynamic load for the node.
     *
     * @param fmDataLoader {function} the function that will be used to get the data.
     * @param iconMode {int} configures the icon that is displayed when a dynamic
     * load node is expanded the first time without children.  By default, the 
     * "collapse" icon will be used.  If set to 1, the leaf node icon will be
     * displayed.
     */
    setDynamicLoad: function(fnDataLoader, iconMode) { 
        if (fnDataLoader) {
            this.dataLoader = fnDataLoader;
            this._dynLoad = true;
        } else {
            this.dataLoader = null;
            this._dynLoad = false;
        }

        if (iconMode) {
            this.iconMode = iconMode;
        }
    },

    /**
     * Evaluates if this node is the root node of the tree
     *
     * @return {boolean} true if this is the root node
     */
    isRoot: function() { 
        return (this == this.tree.root);
    },

    /**
     * Evaluates if this node's children should be loaded dynamically.  Looks for
     * the property both in this instance and the root node.  If the tree is
     * defined to load all children dynamically, the data callback function is
     * defined in the root node
     *
     * @return {boolean} true if this node's children are to be loaded dynamically
     */
    isDynamic: function() { 
        var lazy = (!this.isRoot() && (this._dynLoad || this.tree.root._dynLoad));
        // this.logger.log("isDynamic: " + lazy);
        return lazy;
    },

    getIconMode: function() {
        return (this.iconMode || this.tree.root.iconMode);
    },

    /**
     * Checks if this node has children.  If this node is lazy-loading and the
     * children have not been rendered, we do not know whether or not there
     * are actual children.  In most cases, we need to assume that there are
     * children (for instance, the toggle needs to show the expandable 
     * presentation state).  In other times we want to know if there are rendered
     * children.  For the latter, "checkForLazyLoad" should be false.
     *
     * @param checkForLazyLoad {boolean} should we check for unloaded children?
     * @return {boolean} true if this has children or if it might and we are
     * checking for this condition.
     */
    hasChildren: function(checkForLazyLoad) { 
        return ( this.children.length > 0 || 
                (checkForLazyLoad && this.isDynamic() && !this.dynamicLoadComplete) );
    },

    /**
     * Expands if node is collapsed, collapses otherwise.
     */
    toggle: function() {
        if (!this.tree.locked && ( this.hasChildren(true) || this.isDynamic()) ) {
            if (this.expanded) { this.collapse(); } else { this.expand(); }
        }
    },

    /**
     * Returns the markup for this node and its children.
     *
     * @return {string} the markup for this node and its expanded children.
     */
    getHtml: function() {
        var sb = [];
        sb[sb.length] = '<div class="ygtvitem" id="' + this.getElId() + '">';
        sb[sb.length] = this.getNodeHtml();
        sb[sb.length] = this.getChildrenHtml();
        sb[sb.length] = '</div>';
        return sb.join("");
    },

    /**
     * Called when first rendering the tree.  We always build the div that will
     * contain this nodes children, but we don't render the children themselves
     * unless this node is expanded.
     *
     * @return {string} the children container div html and any expanded children
     * @private
     */
    getChildrenHtml: function() {

        var sb = [];
        sb[sb.length] = '<div class="ygtvchildren"';
        sb[sb.length] = ' id="' + this.getChildrenElId() + '"';
        if (!this.expanded) {
            sb[sb.length] = ' style="display:none;"';
        }
        sb[sb.length] = '>';

        // Don't render the actual child node HTML unless this node is expanded.
        if ( (this.hasChildren(true) && this.expanded) ||
                (this.renderHidden && !this.isDynamic()) ) {
            sb[sb.length] = this.renderChildren();
        }

        sb[sb.length] = '</div>';

        return sb.join("");
    },

    /**
     * Generates the markup for the child nodes.  This is not done until the node
     * is expanded.
     *
     * @return {string} the html for this node's children
     * @private
     */
    renderChildren: function() {

        this.logger.log("rendering children for " + this.index);

        var node = this;

        if (this.isDynamic() && !this.dynamicLoadComplete) {
            this.isLoading = true;
            this.tree.locked = true;

            if (this.dataLoader) {
                this.logger.log("Using dynamic loader defined for this node");

                setTimeout( 
                    function() {
                        node.dataLoader(node, 
                            function() { 
                                node.loadComplete(); 
                            });
                    }, 10);
                
            } else if (this.tree.root.dataLoader) {
                this.logger.log("Using the tree-level dynamic loader");

                setTimeout( 
                    function() {
                        node.tree.root.dataLoader(node, 
                            function() { 
                                node.loadComplete(); 
                            });
                    }, 10);

            } else {
                this.logger.log("no loader found");
                return "Error: data loader not found or not specified.";
            }

            return "";

        } else {
            return this.completeRender();
        }
    },

    /**
     * Called when we know we have all the child data.
     * @return {string} children html
     */
    completeRender: function() {
        this.logger.log("completeRender: " + this.index + ", # of children: " + this.children.length);
        var sb = [];

        for (var i=0; i < this.children.length; ++i) {
            this.children[i].childrenRendered = false;
            sb[sb.length] = this.children[i].getHtml();
        }
        
        this.childrenRendered = true;

        return sb.join("");
    },

    /**
     * Load complete is the callback function we pass to the data provider
     * in dynamic load situations.
     */
    loadComplete: function() {
        this.logger.log("loadComplete: " + this.index);
        this.getChildrenEl().innerHTML = this.completeRender();
        this.dynamicLoadComplete = true;
        this.isLoading = false;
        this.expand();
        this.tree.locked = false;
    },

    /**
     * Returns this node's ancestor at the specified depth.
     *
     * @param {int} depth the depth of the ancestor.
     * @return {Node} the ancestor
     */
    getAncestor: function(depth) {
        if (depth >= this.depth || depth < 0)  {
            this.logger.log("illegal getAncestor depth: " + depth);
            return null;
        }

        var p = this.parent;
        
        while (p.depth > depth) {
            p = p.parent;
        }

        return p;
    },

    /**
     * Returns the css class for the spacer at the specified depth for
     * this node.  If this node's ancestor at the specified depth
     * has a next sibling the presentation is different than if it
     * does not have a next sibling
     *
     * @param {int} depth the depth of the ancestor.
     * @return {string} the css class for the spacer
     */
    getDepthStyle: function(depth) {
        return (this.getAncestor(depth).nextSibling) ? 
            "ygtvdepthcell" : "ygtvblankdepthcell";
    },

    /**
     * Get the markup for the node.  This is designed to be overrided so that we can
     * support different types of nodes.
     *
     * @return {string} The HTML that will render this node.
     */
    getNodeHtml: function() { 
        this.logger.log("Generating html");
        return ""; 
    },

    /**
     * Regenerates the html for this node and its children.  To be used when the
     * node is expanded and new children have been added.
     */
    refresh: function() {
        // this.loadComplete();
        this.getChildrenEl().innerHTML = this.completeRender();

        if (this.hasIcon) {
            var el = this.getToggleEl();
            if (el) {
                el.className = this.getStyle();
            }
        }
    },

    /**
     * toString
     * @return {string} string representation of the node
     */
    toString: function() {
        return "Node (" + this.index + ")";
    }

};

/**
 * A custom YAHOO.widget.Node that handles the unique nature of 
 * the virtual, presentationless root node.
 *
 * @extends YAHOO.widget.Node
 * @constructor
 */
YAHOO.widget.RootNode = function(oTree) {
	// Initialize the node with null params.  The root node is a
	// special case where the node has no presentation.  So we have
	// to alter the standard properties a bit.
	this.init(null, null, true);
	
	/**
	 * For the root node, we get the tree reference from as a param
	 * to the constructor instead of from the parent element.
	 *
	 * @type TreeView
	 */
	this.tree = oTree;
};

YAHOO.widget.RootNode.prototype = new YAHOO.widget.Node();

// overrides YAHOO.widget.Node
YAHOO.widget.RootNode.prototype.getNodeHtml = function() { 
	return ""; 
};

YAHOO.widget.RootNode.prototype.toString = function() { 
    return "RootNode";
};

YAHOO.widget.RootNode.prototype.loadComplete = function() { 
    this.tree.draw();
};
/**
 * The default node presentation.  The first parameter should be
 * either a string that will be used as the node's label, or an object
 * that has a string propery called label.  By default, the clicking the
 * label will toggle the expanded/collapsed state of the node.  By
 * changing the href property of the instance, this behavior can be
 * changed so that the label will go to the specified href.
 *
 * @extends YAHOO.widget.Node
 * @constructor
 * @param oData {object} a string or object containing the data that will
 * be used to render this node
 * @param oParent {YAHOO.widget.Node} this node's parent node
 * @param expanded {boolean} the initial expanded/collapsed state
 */
YAHOO.widget.TextNode = function(oData, oParent, expanded) {
    // this.type = "TextNode";

    if (oData) { 
        this.init(oData, oParent, expanded);
        this.setUpLabel(oData);
    }

    /**
     * @private
     */
    this.logger     = new YAHOO.widget.LogWriter(this.toString());
};

YAHOO.widget.TextNode.prototype = new YAHOO.widget.Node();

/**
 * The CSS class for the label href.  Defaults to ygtvlabel, but can be
 * overridden to provide a custom presentation for a specific node.
 *
 * @type string
 */
YAHOO.widget.TextNode.prototype.labelStyle = "ygtvlabel";

/**
 * The derived element id of the label for this node
 *
 * @type string
 */
YAHOO.widget.TextNode.prototype.labelElId = null;

/**
 * The text for the label.  It is assumed that the oData parameter will
 * either be a string that will be used as the label, or an object that
 * has a property called "label" that we will use.
 *
 * @type string
 */
YAHOO.widget.TextNode.prototype.label = null;

/**
 * Sets up the node label
 * 
 * @param oData string containing the label, or an object with a label property
 */
YAHOO.widget.TextNode.prototype.setUpLabel = function(oData) { 
    if (typeof oData == "string") {
        oData = { label: oData };
    }
    this.label = oData.label;
    
    // update the link
    if (oData.href) {
        this.href = oData.href;
    }

    // set the target
    if (oData.target) {
        this.target = oData.target;
    }

    if (oData.style) {
        this.labelStyle = oData.style;
    }

    this.labelElId = "ygtvlabelel" + this.index;
};

/**
 * Returns the label element
 *
 * @return {object} the element
 */
YAHOO.widget.TextNode.prototype.getLabelEl = function() { 
    return document.getElementById(this.labelElId);
};

// overrides YAHOO.widget.Node
YAHOO.widget.TextNode.prototype.getNodeHtml = function() { 
    this.logger.log("Generating html");
    var sb = [];

    sb[sb.length] = '<table border="0" cellpadding="0" cellspacing="0">';
    sb[sb.length] = '<tr>';
    
    for (i=0;i<this.depth;++i) {
        // sb[sb.length] = '<td class="ygtvdepthcell">&#160;</td>';
        sb[sb.length] = '<td class="' + this.getDepthStyle(i) + '">&#160;</td>';
    }

    var getNode = 'YAHOO.widget.TreeView.getNode(\'' +
                    this.tree.id + '\',' + this.index + ')';

    sb[sb.length] = '<td';
    // sb[sb.length] = ' onselectstart="return false"';
    sb[sb.length] = ' id="' + this.getToggleElId() + '"';
    sb[sb.length] = ' class="' + this.getStyle() + '"';
    if (this.hasChildren(true)) {
        sb[sb.length] = ' onmouseover="this.className=';
        sb[sb.length] = getNode + '.getHoverStyle()"';
        sb[sb.length] = ' onmouseout="this.className=';
        sb[sb.length] = getNode + '.getStyle()"';
    }
    sb[sb.length] = ' onclick="javascript:' + this.getToggleLink() + '">';

    /*
    sb[sb.length] = '<img id="' + this.getSpacerId() + '"';
    sb[sb.length] = ' alt=""';
    sb[sb.length] = ' tabindex=0';
    sb[sb.length] = ' src="' + this.spacerPath + '"';
    sb[sb.length] = ' title="' + this.getStateText() + '"';
    sb[sb.length] = ' class="ygtvspacer"';
    // sb[sb.length] = ' onkeypress="return ' + getNode + '".onKeyPress()"';
    sb[sb.length] = ' />';
    */

    sb[sb.length] = '&#160;';

    sb[sb.length] = '</td>';
    sb[sb.length] = '<td>';
    sb[sb.length] = '<a';
    sb[sb.length] = ' id="' + this.labelElId + '"';
    sb[sb.length] = ' class="' + this.labelStyle + '"';
    sb[sb.length] = ' href="' + this.href + '"';
    sb[sb.length] = ' target="' + this.target + '"';
    sb[sb.length] = ' onclick="return ' + getNode + '.onLabelClick(' + getNode +')"';
    if (this.hasChildren(true)) {
        sb[sb.length] = ' onmouseover="document.getElementById(\'';
        sb[sb.length] = this.getToggleElId() + '\').className=';
        sb[sb.length] = getNode + '.getHoverStyle()"';
        sb[sb.length] = ' onmouseout="document.getElementById(\'';
        sb[sb.length] = this.getToggleElId() + '\').className=';
        sb[sb.length] = getNode + '.getStyle()"';
    }
    sb[sb.length] = ' >';
    sb[sb.length] = this.label;
    sb[sb.length] = '</a>';
    sb[sb.length] = '</td>';
    sb[sb.length] = '</tr>';
    sb[sb.length] = '</table>';

    return sb.join("");
};


/**
 * Executed when the label is clicked
 * @param me {Node} this node
 * @scope the anchor tag clicked
 * @return false to cancel the anchor click
 */
YAHOO.widget.TextNode.prototype.onLabelClick = function(me) { 
    me.logger.log("onLabelClick " + this.label);
    //return true;
};

YAHOO.widget.TextNode.prototype.toString = function() { 
    return "TextNode (" + this.index + ") " + this.label;
};

/**
 * A menu-specific implementation that differs from TextNode in that only 
 * one sibling can be expanded at a time.
 * @extends YAHOO.widget.TextNode
 * @constructor
 */
YAHOO.widget.MenuNode = function(oData, oParent, expanded) {
	if (oData) { 
		this.init(oData, oParent, expanded);
		this.setUpLabel(oData);
	}

    /**
     * Menus usually allow only one branch to be open at a time.
     * @type boolean
     */
	this.multiExpand = false;

    /**
     * @private
     */
    this.logger     = new YAHOO.widget.LogWriter(this.toString());

};

YAHOO.widget.MenuNode.prototype = new YAHOO.widget.TextNode();

YAHOO.widget.MenuNode.prototype.toString = function() { 
    return "MenuNode (" + this.index + ") " + this.label;
};

/**
 * This implementation takes either a string or object for the
 * oData argument.  If is it a string, we will use it for the display
 * of this node (and it can contain any html code).  If the parameter
 * is an object, we look for a parameter called "html" that will be
 * used for this node's display.
 *
 * @extends YAHOO.widget.Node
 * @constructor
 * @param oData {object} a string or object containing the data that will
 * be used to render this node
 * @param oParent {YAHOO.widget.Node} this node's parent node
 * @param expanded {boolean} the initial expanded/collapsed state
 * @param hasIcon {boolean} specifies whether or not leaf nodes should
 * have an icon
 */
YAHOO.widget.HTMLNode = function(oData, oParent, expanded, hasIcon) {
    if (oData) { 
        this.init(oData, oParent, expanded);
        this.initContent(oData, hasIcon);
    }
};

YAHOO.widget.HTMLNode.prototype = new YAHOO.widget.Node();

/**
 * The CSS class for the html content container.  Defaults to ygtvhtml, but 
 * can be overridden to provide a custom presentation for a specific node.
 *
 * @type string
 */
YAHOO.widget.HTMLNode.prototype.contentStyle = "ygtvhtml";

/**
 * The generated id that will contain the data passed in by the implementer.
 *
 * @type string
 */
YAHOO.widget.HTMLNode.prototype.contentElId = null;

/**
 * The HTML content to use for this node's display
 *
 * @type string
 */
YAHOO.widget.HTMLNode.prototype.content = null;

/**
 * Sets up the node label
 *
 * @param {object} An html string or object containing an html property
 * @param {boolean} hasIcon determines if the node will be rendered with an
 * icon or not
 */
YAHOO.widget.HTMLNode.prototype.initContent = function(oData, hasIcon) { 
    if (typeof oData == "string") {
        oData = { html: oData };
    }

    this.html = oData.html;
    this.contentElId = "ygtvcontentel" + this.index;
    this.hasIcon = hasIcon;

    /**
     * @private
     */
    this.logger = new YAHOO.widget.LogWriter(this.toString());
};

/**
 * Returns the outer html element for this node's content
 *
 * @return {HTMLElement} the element
 */
YAHOO.widget.HTMLNode.prototype.getContentEl = function() { 
    return document.getElementById(this.contentElId);
};

// overrides YAHOO.widget.Node
YAHOO.widget.HTMLNode.prototype.getNodeHtml = function() { 
    this.logger.log("Generating html");
    var sb = [];

    sb[sb.length] = '<table border="0" cellpadding="0" cellspacing="0">';
    sb[sb.length] = '<tr>';
    
    for (i=0;i<this.depth;++i) {
        sb[sb.length] = '<td class="' + this.getDepthStyle(i) + '">&#160;</td>';
    }

    if (this.hasIcon) {
        sb[sb.length] = '<td';
        sb[sb.length] = ' id="' + this.getToggleElId() + '"';
        sb[sb.length] = ' class="' + this.getStyle() + '"';
        sb[sb.length] = ' onclick="javascript:' + this.getToggleLink() + '"';
        if (this.hasChildren(true)) {
            sb[sb.length] = ' onmouseover="this.className=';
            sb[sb.length] = 'YAHOO.widget.TreeView.getNode(\'';
            sb[sb.length] = this.tree.id + '\',' + this.index +  ').getHoverStyle()"';
            sb[sb.length] = ' onmouseout="this.className=';
            sb[sb.length] = 'YAHOO.widget.TreeView.getNode(\'';
            sb[sb.length] = this.tree.id + '\',' + this.index +  ').getStyle()"';
        }
        sb[sb.length] = '>&#160;</td>';
    }

    sb[sb.length] = '<td';
    sb[sb.length] = ' id="' + this.contentElId + '"';
    sb[sb.length] = ' class="' + this.contentStyle + '"';
    sb[sb.length] = ' >';
    sb[sb.length] = this.html;
    sb[sb.length] = '</td>';
    sb[sb.length] = '</tr>';
    sb[sb.length] = '</table>';

    return sb.join("");
};

YAHOO.widget.HTMLNode.prototype.toString = function() { 
    return "HTMLNode (" + this.index + ")";
};

/**
 * A static factory class for tree view expand/collapse animations
 *
 * @constructor
 */
YAHOO.widget.TVAnim = function() {
    return {
        /**
         * Constant for the fade in animation
         * 
         * @type string
         */
        FADE_IN: "TVFadeIn",

        /**
         * Constant for the fade out animation
         * 
         * @type string
         */
        FADE_OUT: "TVFadeOut",

        /**
         * Returns a ygAnim instance of the given type
         *
         * @param type {string} the type of animation
         * @param el {HTMLElement} the element to element (probably the children div)
         * @param callback {function} function to invoke when the animation is done.
         * @return {YAHOO.util.Animation} the animation instance
         */
        getAnim: function(type, el, callback) {
            if (YAHOO.widget[type]) {
                return new YAHOO.widget[type](el, callback);
            } else {
                return null;
            }
        },

        /**
         * Returns true if the specified animation class is available
         *
         * @param type {string} the type of animation
         * @return {boolean} true if valid, false if not
         */
        isValid: function(type) {
            return (YAHOO.widget[type]);
        }
    };
} ();

/**
 * A 1/2 second fade-in animation.
 *
 * @constructor
 * @param el {HTMLElement} the element to animate
 * @param callback {function} function to invoke when the animation is finished
 */
YAHOO.widget.TVFadeIn = function(el, callback) {
    /**
     * The element to animate
     * @type HTMLElement
     */
    this.el = el;

    /**
     * the callback to invoke when the animation is complete
     *
     * @type function
     */
    this.callback = callback;

    /**
     * @private
     */
    this.logger = new YAHOO.widget.LogWriter(this.toString());
};

/**
 * Performs the animation
 */
YAHOO.widget.TVFadeIn.prototype = {
    animate: function() {
        var tvanim = this;

        var s = this.el.style;
        s.opacity = 0.1;
        s.filter = "alpha(opacity=10)";
        s.display = "";

        // var dur = ( navigator.userAgent.match(/msie/gi) ) ? 0.05 : 0.4;
        var dur = 0.4; 
        // this.logger.log("duration: " + dur);
        // var a = new ygAnim_Fade(this.el, dur, 1);
        // a.setStart(0.1);
        // a.onComplete = function() { tvanim.onComplete(); };

        // var a = new YAHOO.util.Anim(this.el, 'opacity', 0.1, 1);
        var a = new YAHOO.util.Anim(this.el, {opacity: {from: 0.1, to: 1, unit:""}}, dur);
        a.onComplete.subscribe( function() { tvanim.onComplete(); } );
        a.animate();
    },

    /**
     * Clean up and invoke callback
     */
    onComplete: function() {
        this.callback();
    },

    toString: function() {
        return "TVFadeIn";
    }
};

/**
 * A 1/2 second fade out animation.
 *
 * @constructor
 * @param el {HTMLElement} the element to animate
 * @param callback {Function} function to invoke when the animation is finished
 */
YAHOO.widget.TVFadeOut = function(el, callback) {
    /**
     * The element to animate
     * @type HTMLElement
     */
    this.el = el;

    /**
     * the callback to invoke when the animation is complete
     *
     * @type function
     */
    this.callback = callback;

    /**
     * @private
     */
    this.logger = new YAHOO.widget.LogWriter(this.toString());
};

/**
 * Performs the animation
 */
YAHOO.widget.TVFadeOut.prototype = {
    animate: function() {
        var tvanim = this;
        // var dur = ( navigator.userAgent.match(/msie/gi) ) ? 0.05 : 0.4;
        var dur = 0.4;
        // this.logger.log("duration: " + dur);
        // var a = new ygAnim_Fade(this.el, dur, 0.1);
        // a.onComplete = function() { tvanim.onComplete(); };

        // var a = new YAHOO.util.Anim(this.el, 'opacity', 1, 0.1);
        var a = new YAHOO.util.Anim(this.el, {opacity: {from: 1, to: 0.1, unit:""}}, dur);
        a.onComplete.subscribe( function() { tvanim.onComplete(); } );
        a.animate();
    },

    /**
     * Clean up and invoke callback
     */
    onComplete: function() {
        var s = this.el.style;
        s.display = "none";
        // s.opacity = 1;
        s.filter = "alpha(opacity=100)";
        this.callback();
    },

    toString: function() {
        return "TVFadeOut";
    }
};

