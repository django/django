
/*                                                                                                                                                      
Copyright (c) 2006, Yahoo! Inc. All rights reserved.                                                                                                    
Code licensed under the BSD License:                                                                                                                    
http://developer.yahoo.net/yui/license.txt                                                                                                              
version: 0.11.0                                                                                                                                         
*/ 

/**
 * The Yahoo global namespace
 * @constructor
 */
var YAHOO = window.YAHOO || {};

/**
 * Returns the namespace specified and creates it if it doesn't exist
 *
 * YAHOO.namespace("property.package");
 * YAHOO.namespace("YAHOO.property.package");
 *
 * Either of the above would create YAHOO.property, then
 * YAHOO.property.package
 *
 * @param  {String} ns The name of the namespace
 * @return {Object}    A reference to the namespace object
 */
YAHOO.namespace = function(ns) {

    if (!ns || !ns.length) {
        return null;
    }

    var levels = ns.split(".");
    var nsobj = YAHOO;

    // YAHOO is implied, so it is ignored if it is included
    for (var i=(levels[0] == "YAHOO") ? 1 : 0; i<levels.length; ++i) {
        nsobj[levels[i]] = nsobj[levels[i]] || {};
        nsobj = nsobj[levels[i]];
    }

    return nsobj;
};

/**
 * Uses YAHOO.widget.Logger to output a log message, if the widget is available.
 *
 * @param  {string}  sMsg       The message to log.
 * @param  {string}  sCategory  The log category for the message.  Default
 *                              categories are "info", "warn", "error", time".
 *                              Custom categories can be used as well. (opt)
 * @param  {string}  sSource    The source of the the message (opt)
 * @return {boolean}            True if the log operation was successful.
 */
YAHOO.log = function(sMsg, sCategory, sSource) {
    var l = YAHOO.widget.Logger;
    if(l && l.log) {
        return l.log(sMsg, sCategory, sSource);
    } else {
        return false;
    }
};

/**
 * Utility to set up the prototype, constructor and superclass properties to
 * support an inheritance strategy that can chain constructors and methods.
 *
 * @param {Function} subclass   the object to modify
 * @param {Function} superclass the object to inherit
 */
YAHOO.extend = function(subclass, superclass) {
    var f = function() {};
    f.prototype = superclass.prototype;
    subclass.prototype = new f();
    subclass.prototype.constructor = subclass;
    subclass.superclass = superclass.prototype;
    if (superclass.prototype.constructor == Object.prototype.constructor) {
        superclass.prototype.constructor = superclass;
    }
};

YAHOO.namespace("util");
YAHOO.namespace("widget");
YAHOO.namespace("example");

