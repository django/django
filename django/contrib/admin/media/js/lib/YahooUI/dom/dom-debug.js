/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
Version: 0.11.1
*/

/**
 * @class Provides helper methods for DOM elements.
 */
YAHOO.util.Dom = function() {
   var ua = navigator.userAgent.toLowerCase();
   var isOpera = (ua.indexOf('opera') > -1);
   var isSafari = (ua.indexOf('safari') > -1);
   var isIE = (window.ActiveXObject);

   var id_counter = 0;
   var util = YAHOO.util; // internal shorthand
   var property_cache = {}; // to cache case conversion for set/getStyle
   var logger = {};
   logger.log = function() {YAHOO.log.apply(window, arguments)};
   
   var toCamel = function(property) {
      var convert = function(prop) {
         var test = /(-[a-z])/i.exec(prop);
         return prop.replace(RegExp.$1, RegExp.$1.substr(1).toUpperCase());
      };
      
      while(property.indexOf('-') > -1) {
         property = convert(property);
      }

      return property;
      //return property.replace(/-([a-z])/gi, function(m0, m1) {return m1.toUpperCase()}) // cant use function as 2nd arg yet due to safari bug
   };
   
   var toHyphen = function(property) {
      if (property.indexOf('-') > -1) { // assume hyphen
         return property;
      }
      
      var converted = '';
      for (var i = 0, len = property.length;i < len; ++i) {
         if (property.charAt(i) == property.charAt(i).toUpperCase()) {
            converted = converted + '-' + property.charAt(i).toLowerCase();
         } else {
            converted = converted + property.charAt(i);
         }
      }

      return converted;
      //return property.replace(/([a-z])([A-Z]+)/g, function(m0, m1, m2) {return (m1 + '-' + m2.toLowerCase())});
   };
   
   // improve performance by only looking up once
   var cacheConvertedProperties = function(property) {
      property_cache[property] = {
         camel: toCamel(property),
         hyphen: toHyphen(property)
      };
   };
   
   return {
      /**
       * Returns an HTMLElement reference
       * @alias YAHOO.util.Dom.get
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID for getting a DOM reference, an actual DOM reference, or an Array of IDs and/or HTMLElements.
       * @return {HTMLElement/Array} A DOM reference to an HTML element or an array of HTMLElements.
       */
      get: function(el) {
         if (!el) { return null; } // nothing to work with
         
         if (typeof el != 'string' && !(el instanceof Array) ) { // assuming HTMLElement or HTMLCollection, so pass back as is
            logger.log('get(' + el + ') returning ' + el, 'info', 'Dom');
            return el;
         }
         
         if (typeof el == 'string') { // ID
            logger.log('get("' + el + '") returning ' + document.getElementById(el), 'info', 'Dom');
            return document.getElementById(el);
         }
         else { // array of ID's and/or elements
            var collection = [];
            for (var i = 0, len = el.length; i < len; ++i) {
               collection[collection.length] = util.Dom.get(el[i]);
            }
            
            logger.log('get("' + el + '") returning ' + collection, 'info', 'Dom');
            return collection;
         }

         logger.log('element ' + el + ' not found', 'error', 'Dom');
         return null; // safety, should never happen
      },
   
      /**
       * Normalizes currentStyle and ComputedStyle.
       * @alias YAHOO.util.Dom.getStyle
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements.
       * @param {String} property The style property whose value is returned.
       * @return {String/Array} The current value of the style property for the element(s).
       */
      getStyle: function(el, property) {
         var f = function(el) {
            var value = null;
            var dv = document.defaultView;
            
            if (!property_cache[property]) {
               cacheConvertedProperties(property);
            }
            
            var camel = property_cache[property]['camel'];
            var hyphen = property_cache[property]['hyphen'];

            if (property == 'opacity' && el.filters) {// IE opacity
               value = 1;
               try {
                  value = el.filters.item('DXImageTransform.Microsoft.Alpha').opacity / 100;
               } catch(e) {
                  try {
                     value = el.filters.item('alpha').opacity / 100;
                  } catch(e) {}
               }
            } else if (el.style[camel]) { // camelCase for valid styles
               value = el.style[camel];
            }
            else if (isIE && el.currentStyle && el.currentStyle[camel]) { // camelCase for currentStyle; isIE to workaround broken Opera 9 currentStyle
               value = el.currentStyle[camel];
            }
            else if ( dv && dv.getComputedStyle ) { // hyphen-case for computedStyle
               var computed = dv.getComputedStyle(el, '');
               
               if (computed && computed.getPropertyValue(hyphen)) {
                  value = computed.getPropertyValue(hyphen);
               }
            }
      
            logger.log('getStyle ' + property + ' returning ' + value, 'info', 'Dom');
            return value;
         };
         
         return util.Dom.batch(el, f, util.Dom, true);
      },
   
      /**
       * Wrapper for setting style properties of HTMLElements.  Normalizes "opacity" across modern browsers.
       * @alias YAHOO.util.Dom.setStyle
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements.
       * @param {String} property The style property to be set.
       * @param {String} val The value to apply to the given property.
       */
      setStyle: function(el, property, val) {
         if (!property_cache[property]) {
            cacheConvertedProperties(property);
         }
         
         var camel = property_cache[property]['camel'];
         
         var f = function(el) {
            switch(property) {
               case 'opacity' :
                  if (isIE && typeof el.style.filter == 'string') { // in case not appended
                     el.style.filter = 'alpha(opacity=' + val * 100 + ')';
                     
                     if (!el.currentStyle || !el.currentStyle.hasLayout) {
                        el.style.zoom = 1; // when no layout or cant tell
                     }
                  } else {
                     el.style.opacity = val;
                     el.style['-moz-opacity'] = val;
                     el.style['-khtml-opacity'] = val;
                  }

                  break;
               default :
                  el.style[camel] = val;
            }
            
            logger.log('setStyle setting ' + property + ' to ' + val, 'info', 'Dom');
            
         };
         
         util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Gets the current position of an element based on page coordinates.  Element must be part of the DOM tree to have page coordinates (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.getXY
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements
       * @return {Array} The XY position of the element(s)
       */
      getXY: function(el) {
         var f = function(el) {
   
         // has to be part of document to have pageXY
            if (el.offsetParent === null || this.getStyle(el, 'display') == 'none') {
               logger.log('getXY failed: element not available', 'error', 'Dom');
               return false;
            }
            
            var parentNode = null;
            var pos = [];
            var box;
            
            if (el.getBoundingClientRect) { // IE
               box = el.getBoundingClientRect();
               var doc = document;
               if ( !this.inDocument(el) && parent.document != document) {// might be in a frame, need to get its scroll
                  doc = parent.document;

                  if ( !this.isAncestor(doc.documentElement, el) ) {
                     logger.log('getXY failed: element not available', 'error', 'Dom');
                     return false;                 
                  }

               }

               var scrollTop = Math.max(doc.documentElement.scrollTop, doc.body.scrollTop);
               var scrollLeft = Math.max(doc.documentElement.scrollLeft, doc.body.scrollLeft);
               
               return [box.left + scrollLeft, box.top + scrollTop];
            }
            else { // safari, opera, & gecko
               pos = [el.offsetLeft, el.offsetTop];
               parentNode = el.offsetParent;
               if (parentNode != el) {
                  while (parentNode) {
                     pos[0] += parentNode.offsetLeft;
                     pos[1] += parentNode.offsetTop;
                     parentNode = parentNode.offsetParent;
                  }
               }
               if (isSafari && this.getStyle(el, 'position') == 'absolute' ) { // safari doubles in some cases
                  pos[0] -= document.body.offsetLeft;
                  pos[1] -= document.body.offsetTop;
               } 
            }
            
            if (el.parentNode) { parentNode = el.parentNode; }
            else { parentNode = null; }
      
            while (parentNode && parentNode.tagName.toUpperCase() != 'BODY' && parentNode.tagName.toUpperCase() != 'HTML') 
            { // account for any scrolled ancestors
               pos[0] -= parentNode.scrollLeft;
               pos[1] -= parentNode.scrollTop;
      
               if (parentNode.parentNode) { parentNode = parentNode.parentNode; } 
               else { parentNode = null; }
            }
      
            logger.log('getXY returning ' + pos, 'info', 'Dom');
            
            return pos;
         };
         
         return util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Gets the current X position of an element based on page coordinates.  The element must be part of the DOM tree to have page coordinates (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.getX
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements
       * @return {String/Array} The X position of the element(s)
       */
      getX: function(el) {
         return util.Dom.getXY(el)[0];
      },
      
      /**
       * Gets the current Y position of an element based on page coordinates.  Element must be part of the DOM tree to have page coordinates (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.getY
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements
       * @return {String/Array} The Y position of the element(s)
       */
      getY: function(el) {
         return util.Dom.getXY(el)[1];
      },
      
      /**
       * Set the position of an html element in page coordinates, regardless of how the element is positioned.
       * The element(s) must be part of the DOM tree to have page coordinates (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.setXY
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements
       * @param {Array} pos Contains X & Y values for new position (coordinates are page-based)
       * @param {Boolean} noRetry By default we try and set the position a second time if the first fails
       */
      setXY: function(el, pos, noRetry) {
         var f = function(el) {
            var style_pos = this.getStyle(el, 'position');
            if (style_pos == 'static') { // default to relative
               this.setStyle(el, 'position', 'relative');
               style_pos = 'relative';
            }
            
            var pageXY = this.getXY(el);
            if (pageXY === false) { // has to be part of doc to have pageXY
               logger.log('setXY failed: element not available', 'error', 'Dom');
               return false; 
            }
            
            var delta = [ // assuming pixels; if not we will have to retry
               parseInt( this.getStyle(el, 'left'), 10 ),
               parseInt( this.getStyle(el, 'top'), 10 )
            ];
         
            if ( isNaN(delta[0]) ) {// in case of 'auto'
               delta[0] = (style_pos == 'relative') ? 0 : el.offsetLeft;
            } 
            if ( isNaN(delta[1]) ) { // in case of 'auto'
               delta[1] = (style_pos == 'relative') ? 0 : el.offsetTop;
            } 
      
            if (pos[0] !== null) { el.style.left = pos[0] - pageXY[0] + delta[0] + 'px'; }
            if (pos[1] !== null) { el.style.top = pos[1] - pageXY[1] + delta[1] + 'px'; }
      
            var newXY = this.getXY(el);
      
            // if retry is true, try one more time if we miss 
            if (!noRetry && (newXY[0] != pos[0] || newXY[1] != pos[1]) ) {
               this.setXY(el, pos, true);
            }
            
            logger.log('setXY setting position to ' + pos, 'info', 'Dom');
         };
         
         util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Set the X position of an html element in page coordinates, regardless of how the element is positioned.
       * The element must be part of the DOM tree to have page coordinates (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.setX
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements.
       * @param {Int} x to use as the X coordinate for the element(s).
       */
      setX: function(el, x) {
         util.Dom.setXY(el, [x, null]);
      },
      
      /**
       * Set the Y position of an html element in page coordinates, regardless of how the element is positioned.
       * The element must be part of the DOM tree to have page coordinates (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.setY
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements.
       * @param {Int} x to use as the Y coordinate for the element(s).
       */
      setY: function(el, y) {
         util.Dom.setXY(el, [null, y]);
      },
      
      /**
       * Returns the region position of the given element.
       * The element must be part of the DOM tree to have a region (display:none or elements not appended return false).
       * @alias YAHOO.util.Dom.getRegion
       * @param {String/HTMLElement/Array} el Accepts a string to use as an ID, an actual DOM reference, or an Array of IDs and/or HTMLElements.
       * @return {Region/Array} A Region or array of Region instances containing "top, left, bottom, right" member data.
       */
      getRegion: function(el) {
         var f = function(el) {
            var region = new YAHOO.util.Region.getRegion(el);
            logger.log('getRegion returning ' + region, 'info', 'Dom');
            return region;
         };
         
         return util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Returns the width of the client (viewport).
       * Now using getViewportWidth.  This interface left intact for back compat.
       * @alias YAHOO.util.Dom.getClientWidth
       * @return {Int} The width of the viewable area of the page.
       */
      getClientWidth: function() {
         return util.Dom.getViewportWidth();
      },
      
      /**
       * Returns the height of the client (viewport).
       * Now using getViewportHeight.  This interface left intact for back compat.
       * @alias YAHOO.util.Dom.getClientHeight
       * @return {Int} The height of the viewable area of the page.
       */
      getClientHeight: function() {
         return util.Dom.getViewportHeight();
      },

      /**
       * Returns a array of HTMLElements with the given class
       * For optimized performance, include a tag and/or root node if possible
       * @alias YAHOO.util.Dom.getElementsByClassName
       * @param {String} className The class name to match against
       * @param {String} tag (optional) The tag name of the elements being collected
       * @param {String/HTMLElement} root (optional) The HTMLElement or an ID to use as the starting point 
       * @return {Array} An array of elements that have the given class name
       */
      getElementsByClassName: function(className, tag, root) {
         var method = function(el) { return util.Dom.hasClass(el, className) };
         return util.Dom.getElementsBy(method, tag, root);
      },

      /**
       * Determines whether an HTMLElement has the given className
       * @alias YAHOO.util.Dom.hasClass
       * @param {String/HTMLElement/Array} el The element or collection to test
       * @param {String} className the class name to search for
       * @return {Boolean/Array} A boolean value or array of boolean values
       */
      hasClass: function(el, className) {
         var re = new RegExp('(?:^|\\s+)' + className + '(?:\\s+|$)');
         
         var f = function(el) {
            logger.log('hasClass returning ' + re.test(el['className']), 'info', 'Dom');
            return re.test(el['className']);
         };
         
         return util.Dom.batch(el, f, util.Dom, true);
      },
   
      /**
       * Adds a class name to a given element or collection of elements
       * @alias YAHOO.util.Dom.addClass
       * @param {String/HTMLElement/Array} el The element or collection to add the class to
       * @param {String} className the class name to add to the class attribute
       */
      addClass: function(el, className) {
         var f = function(el) {
            if (this.hasClass(el, className)) { return; } // already present
            
            logger.log('addClass adding ' + className, 'info', 'Dom');
            
            el['className'] = [el['className'], className].join(' ');
         };
         
         util.Dom.batch(el, f, util.Dom, true);
      },
   
      /**
       * Removes a class name from a given element or collection of elements
       * @alias YAHOO.util.Dom.removeClass
       * @param {String/HTMLElement/Array} el The element or collection to remove the class from
       * @param {String} className the class name to remove from the class attribute
       */
      removeClass: function(el, className) {
         var re = new RegExp('(?:^|\\s+)' + className + '(?:\\s+|$)', 'g');

         var f = function(el) {
            if (!this.hasClass(el, className)) { return; } // not present
            
            logger.log('removeClass removing ' + className, 'info', 'Dom');
            
            var c = el['className'];
            el['className'] = c.replace(re, ' ');
            if ( this.hasClass(el, className) ) { // in case of multiple adjacent
               this.removeClass(el, className);
            }
            
         };
         
         util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Replace a class with another class for a given element or collection of elements.
       * If no oldClassName is present, the newClassName is simply added.
       * @alias YAHOO.util.Dom.replaceClass
       * @param {String/HTMLElement/Array} el The element or collection to remove the class from
       * @param {String} oldClassName the class name to be replaced
       * @param {String} newClassName the class name that will be replacing the old class name
       */
      replaceClass: function(el, oldClassName, newClassName) {
         var re = new RegExp('(?:^|\\s+)' + oldClassName + '(?:\\s+|$)', 'g');

         var f = function(el) {
            logger.log('replaceClass replacing ' + oldClassName + ' with ' + newClassName, 'info', 'Dom');
         
            if ( !this.hasClass(el, oldClassName) ) {
               this.addClass(el, newClassName); // just add it if nothing to replace
               return; // note return
            }
         
            el['className'] = el['className'].replace(re, ' ' + newClassName + ' ');

            if ( this.hasClass(el, oldClassName) ) { // in case of multiple adjacent
               this.replaceClass(el, oldClassName, newClassName);
            }
         };
         
         util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Generates a unique ID
       * @alias YAHOO.util.Dom.generateId
       * @param {String/HTMLElement/Array} el (optional) An optional element array of elements to add an ID to (no ID is added if one is already present)
       * @param {String} prefix (optional) an optional prefix to use (defaults to "yui-gen")
       * @return {String/Array} The generated ID, or array of generated IDs (or original ID if already present on an element)
       */
      generateId: function(el, prefix) {
         prefix = prefix || 'yui-gen';
         el = el || {};
         
         var f = function(el) {
            if (el) {
               el = util.Dom.get(el);
            } else {
               el = {}; // just generating ID in this case
            }
            
            if (!el.id) {
               el.id = prefix + id_counter++; 
               logger.log('generateId generating ' + el.id, 'info', 'Dom');
            } // dont override existing
            
            logger.log('generateId returning ' + el.id, 'info', 'Dom');
            
            return el.id;
         };
         
         return util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Determines whether an HTMLElement is an ancestor of another HTML element in the DOM hierarchy
       * @alias YAHOO.util.Dom.isAncestor
       * @param {String/HTMLElement} haystack The possible ancestor
       * @param {String/HTMLElement} needle The possible descendent
       * @return {Boolean} Whether or not the haystack is an ancestor of needle
       */
      isAncestor: function(haystack, needle) {
         haystack = util.Dom.get(haystack);
         if (!haystack || !needle) { return false; }
         
         var f = function(needle) {
            if (haystack.contains && !isSafari) { // safari "contains" is broken
               logger.log('isAncestor returning ' + haystack.contains(needle), 'info', 'Dom');
               return haystack.contains(needle);
            }
            else if ( haystack.compareDocumentPosition ) {
               logger.log('isAncestor returning ' + !!(haystack.compareDocumentPosition(needle) & 16), 'info', 'Dom');
               return !!(haystack.compareDocumentPosition(needle) & 16);
            }
            else { // loop up and test each parent
               var parent = needle.parentNode;
               
               while (parent) {
                  if (parent == haystack) {
                     logger.log('isAncestor returning true', 'info', 'Dom');
                     return true;
                  }
                  else if (parent.tagName.toUpperCase() == 'HTML') {
                     logger.log('isAncestor returning false', 'info', 'Dom');
                     return false;
                  }
                  
                  parent = parent.parentNode;
               }
               logger.log('isAncestor returning false', 'info', 'Dom');
               return false;
            }    
         };
         
         return util.Dom.batch(needle, f, util.Dom, true);     
      },
      
      /**
       * Determines whether an HTMLElement is present in the current document
       * @alias YAHOO.util.Dom.inDocument
       * @param {String/HTMLElement} el The element to search for
       * @return {Boolean} Whether or not the element is present in the current document
       */
      inDocument: function(el) {
         var f = function(el) {
            return this.isAncestor(document.documentElement, el);
         };
         
         return util.Dom.batch(el, f, util.Dom, true);
      },
      
      /**
       * Returns a array of HTMLElements that pass the test applied by supplied boolean method
       * For optimized performance, include a tag and/or root node if possible
       * @alias YAHOO.util.Dom.getElementsBy
       * @param {Function} method A boolean method to test elements with
       * @param {String} tag (optional) The tag name of the elements being collected
       * @param {String/HTMLElement} root (optional) The HTMLElement or an ID to use as the starting point 
       */
      getElementsBy: function(method, tag, root) {
         tag = tag || '*';
         root = util.Dom.get(root) || document;
         
         var nodes = [];
         var elements = root.getElementsByTagName(tag);
         
         if ( !elements.length && (tag == '*' && root.all) ) {
            elements = root.all; // IE < 6
         }
         
         for (var i = 0, len = elements.length; i < len; ++i) 
         {
            if ( method(elements[i]) ) { nodes[nodes.length] = elements[i]; }
         }

         logger.log('getElementsBy returning ' + nodes, 'info', 'Dom');
         
         return nodes;
      },
      
      /**
       * Returns an array of elements that have had the supplied method applied.
       * The method is called with the element(s) as the first arg, and the optional param as the second ( method(el, o) )
       * @alias YAHOO.util.Dom.batch
       * @param {String/HTMLElement/Array} el (optional) An element or array of elements to apply the method to
       * @param {Function} method The method to apply to the element(s)
       * @param {Generic} (optional) o An optional arg that is passed to the supplied method
       * @param {Boolean} (optional) override Whether or not to override the scope of "method" with "o"
       * @return {HTMLElement/Array} The element(s) with the method applied
       */
      batch: function(el, method, o, override) {
         var id = el;
         el = util.Dom.get(el);
         
         var scope = (override) ? o : window;
         
         if (!el || el.tagName || !el.length) { // is null or not a collection (tagName for SELECT and others that can be both an element and a collection)
            if (!el) {
               logger.log(id + ' not available', 'error', 'Dom');
               return false;
            }
            return method.call(scope, el, o);
         } 
         
         var collection = [];
         
         for (var i = 0, len = el.length; i < len; ++i) {
            if (!el[i]) {
               id = id[i];
               logger.log(id + ' not available', 'error', 'Dom');
            }
            collection[collection.length] = method.call(scope, el[i], o);
         }
         
         return collection;
      },
      
      /**
       * Returns the height of the document.
       * @alias YAHOO.util.Dom.getDocumentHeight
       * @return {Int} The height of the actual document (which includes the body and its margin).
       */
      getDocumentHeight: function() {
         var scrollHeight=-1,windowHeight=-1,bodyHeight=-1;
         var marginTop = parseInt(util.Dom.getStyle(document.body, 'marginTop'), 10);
         var marginBottom = parseInt(util.Dom.getStyle(document.body, 'marginBottom'), 10);
         
         var mode = document.compatMode;
         
         if ( (mode || isIE) && !isOpera ) { // (IE, Gecko)
            switch (mode) {
               case 'CSS1Compat': // Standards mode
                  scrollHeight = ((window.innerHeight && window.scrollMaxY) ?  window.innerHeight+window.scrollMaxY : -1);
                  windowHeight = [document.documentElement.clientHeight,self.innerHeight||-1].sort(function(a, b){return(a-b);})[1];
                  bodyHeight = document.body.offsetHeight + marginTop + marginBottom;
                  break;
               
               default: // Quirks
                  scrollHeight = document.body.scrollHeight;
                  bodyHeight = document.body.clientHeight;
            }
         } else { // Safari & Opera
            scrollHeight = document.documentElement.scrollHeight;
            windowHeight = self.innerHeight;
            bodyHeight = document.documentElement.clientHeight;
         }
      
         var h = [scrollHeight,windowHeight,bodyHeight].sort(function(a, b){return(a-b);});
         logger.log('getDocumentHeight returning ' + h[2], 'info', 'Dom');
         return h[2];
      },
      
      /**
       * Returns the width of the document.
       * @alias YAHOO.util.Dom.getDocumentWidth
       * @return {Int} The width of the actual document (which includes the body and its margin).
       */
      getDocumentWidth: function() {
         var docWidth=-1,bodyWidth=-1,winWidth=-1;
         var marginRight = parseInt(util.Dom.getStyle(document.body, 'marginRight'), 10);
         var marginLeft = parseInt(util.Dom.getStyle(document.body, 'marginLeft'), 10);
         
         var mode = document.compatMode;
         
         if (mode || isIE) { // (IE, Gecko, Opera)
            switch (mode) {
               case 'CSS1Compat': // Standards mode
                  docWidth = document.documentElement.clientWidth;
                  bodyWidth = document.body.offsetWidth + marginLeft + marginRight;
                  winWidth = self.innerWidth || -1;
                  break;
                  
               default: // Quirks
                  bodyWidth = document.body.clientWidth;
                  winWidth = document.body.scrollWidth;
                  break;
            }
         } else { // Safari
            docWidth = document.documentElement.clientWidth;
            bodyWidth = document.body.offsetWidth + marginLeft + marginRight;
            winWidth = self.innerWidth;
         }
      
         var w = [docWidth,bodyWidth,winWidth].sort(function(a, b){return(a-b);});
         logger.log('getDocumentWidth returning ' + w[2], 'info', 'Dom');
         return w[2];
      },

      /**
       * Returns the current height of the viewport.
       * @alias YAHOO.util.Dom.getViewportHeight
       * @return {Int} The height of the viewable area of the page (excludes scrollbars).
       */
      getViewportHeight: function() {
         var height = -1;
         var mode = document.compatMode;
      
         if ( (mode || isIE) && !isOpera ) {
            switch (mode) { // (IE, Gecko)
               case 'CSS1Compat': // Standards mode
                  height = document.documentElement.clientHeight;
                  break;
      
               default: // Quirks
                  height = document.body.clientHeight;
            }
         } else { // Safari, Opera
            height = self.innerHeight;
         }
      
         logger.log('getViewportHeight returning ' + height, 'info', 'Dom');
         return height;
      },
      
      /**
       * Returns the current width of the viewport.
       * @alias YAHOO.util.Dom.getViewportWidth
       * @return {Int} The width of the viewable area of the page (excludes scrollbars).
       */
      
      getViewportWidth: function() {
         var width = -1;
         var mode = document.compatMode;
         
         if (mode || isIE) { // (IE, Gecko, Opera)
            switch (mode) {
            case 'CSS1Compat': // Standards mode 
               width = document.documentElement.clientWidth;
               break;
               
            default: // Quirks
               width = document.body.clientWidth;
            }
         } else { // Safari
            width = self.innerWidth;
         }
         logger.log('getViewportWidth returning ' + width, 'info', 'Dom');
         return width;
      }
   };
}();

/**
 * @class A region is a representation of an object on a grid.  It is defined
 * by the top, right, bottom, left extents, so is rectangular by default.  If 
 * other shapes are required, this class could be extended to support it.
 *
 * @param {int} t the top extent
 * @param {int} r the right extent
 * @param {int} b the bottom extent
 * @param {int} l the left extent
 * @constructor
 */
YAHOO.util.Region = function(t, r, b, l) {

    /**
     * The region's top extent
     * @type int
     */
    this.top = t;
    
    /**
     * The region's top extent as index, for symmetry with set/getXY
     * @type int
     */
    this[1] = t;

    /**
     * The region's right extent
     * @type int
     */
    this.right = r;

    /**
     * The region's bottom extent
     * @type int
     */
    this.bottom = b;

    /**
     * The region's left extent
     * @type int
     */
    this.left = l;
    
    /**
     * The region's left extent as index, for symmetry with set/getXY
     * @type int
     */
    this[0] = l;
};

/**
 * Returns true if this region contains the region passed in
 *
 * @param  {Region}  region The region to evaluate
 * @return {boolean}        True if the region is contained with this region, 
 *                          else false
 */
YAHOO.util.Region.prototype.contains = function(region) {
    return ( region.left   >= this.left   && 
             region.right  <= this.right  && 
             region.top    >= this.top    && 
             region.bottom <= this.bottom    );

    // this.logger.debug("does " + this + " contain " + region + " ... " + ret);
};

/**
 * Returns the area of the region
 *
 * @return {int} the region's area
 */
YAHOO.util.Region.prototype.getArea = function() {
    return ( (this.bottom - this.top) * (this.right - this.left) );
};

/**
 * Returns the region where the passed in region overlaps with this one
 *
 * @param  {Region} region The region that intersects
 * @return {Region}        The overlap region, or null if there is no overlap
 */
YAHOO.util.Region.prototype.intersect = function(region) {
    var t = Math.max( this.top,    region.top    );
    var r = Math.min( this.right,  region.right  );
    var b = Math.min( this.bottom, region.bottom );
    var l = Math.max( this.left,   region.left   );
    
    if (b >= t && r >= l) {
        return new YAHOO.util.Region(t, r, b, l);
    } else {
        return null;
    }
};

/**
 * Returns the region representing the smallest region that can contain both
 * the passed in region and this region.
 *
 * @param  {Region} region The region that to create the union with
 * @return {Region}        The union region
 */
YAHOO.util.Region.prototype.union = function(region) {
    var t = Math.min( this.top,    region.top    );
    var r = Math.max( this.right,  region.right  );
    var b = Math.max( this.bottom, region.bottom );
    var l = Math.min( this.left,   region.left   );

    return new YAHOO.util.Region(t, r, b, l);
};

/**
 * toString
 * @return string the region properties
 */
YAHOO.util.Region.prototype.toString = function() {
    return ( "Region {"    +
             "top: "       + this.top    + 
             ", right: "   + this.right  + 
             ", bottom: "  + this.bottom + 
             ", left: "    + this.left   + 
             "}" );
};

/**
 * Returns a region that is occupied by the DOM element
 *
 * @param  {HTMLElement} el The element
 * @return {Region}         The region that the element occupies
 * @static
 */
YAHOO.util.Region.getRegion = function(el) {
    var p = YAHOO.util.Dom.getXY(el);

    var t = p[1];
    var r = p[0] + el.offsetWidth;
    var b = p[1] + el.offsetHeight;
    var l = p[0];

    return new YAHOO.util.Region(t, r, b, l);
};

/////////////////////////////////////////////////////////////////////////////


/**
 * @class
 *
 * A point is a region that is special in that it represents a single point on 
 * the grid.
 *
 * @param {int} x The X position of the point
 * @param {int} y The Y position of the point
 * @constructor
 * @extends Region
 */
YAHOO.util.Point = function(x, y) {
   if (x instanceof Array) { // accept output from Dom.getXY
      y = x[1];
      x = x[0];
   }
   
    /**
     * The X position of the point, which is also the right, left and index zero (for Dom.getXY symmetry)
     * @type int
     */

    this.x = this.right = this.left = this[0] = x;
     
    /**
     * The Y position of the point, which is also the top, bottom and index one (for Dom.getXY symmetry)
     * @type int
     */
    this.y = this.top = this.bottom = this[1] = y;
};

YAHOO.util.Point.prototype = new YAHOO.util.Region();

