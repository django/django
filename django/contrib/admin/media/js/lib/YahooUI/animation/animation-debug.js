/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
Version: 0.11.1
*/


/**
 *
 * Base class for animated DOM objects.
 * @class Base animation class that provides the interface for building animated effects.
 * <p>Usage: var myAnim = new YAHOO.util.Anim(el, { width: { from: 10, to: 100 } }, 1, YAHOO.util.Easing.easeOut);</p>
 * @requires YAHOO.util.AnimMgr
 * @requires YAHOO.util.Easing
 * @requires YAHOO.util.Dom
 * @requires YAHOO.util.Event
 * @requires YAHOO.util.CustomEvent
 * @constructor
 * @param {String or HTMLElement} el Reference to the element that will be animated
 * @param {Object} attributes The attribute(s) to be animated.  
 * Each attribute is an object with at minimum a "to" or "by" member defined.  
 * Additional optional members are "from" (defaults to current value), "units" (defaults to "px").  
 * All attribute names use camelCase.
 * @param {Number} duration (optional, defaults to 1 second) Length of animation (frames or seconds), defaults to time-based
 * @param {Function} method (optional, defaults to YAHOO.util.Easing.easeNone) Computes the values that are applied to the attributes per frame (generally a YAHOO.util.Easing method)
 */

YAHOO.util.Anim = function(el, attributes, duration, method) {
   if (el) {
      this.init(el, attributes, duration, method); 
   }
};

YAHOO.util.Anim.prototype = {
   /**
    * toString method
    * @return {String} string represenation of anim obj
    */
   toString: function() {
      var el = this.getEl();
      var id = el.id || el.tagName;
      return ("Anim " + id);
   },
   
   patterns: { // cached for performance
      noNegatives:      /width|height|opacity|padding/i, // keep at zero or above
      offsetAttribute:  /^((width|height)|(top|left))$/, // use offsetValue as default
      defaultUnit:      /width|height|top$|bottom$|left$|right$/i, // use 'px' by default
      offsetUnit:       /\d+(em|%|en|ex|pt|in|cm|mm|pc)$/i // IE may return these, so convert these to offset
   },
   
   /**
    * Returns the value computed by the animation's "method".
    * @param {String} attr The name of the attribute.
    * @param {Number} start The value this attribute should start from for this animation.
    * @param {Number} end  The value this attribute should end at for this animation.
    * @return {Number} The Value to be applied to the attribute.
    */
   doMethod: function(attr, start, end) {
      return this.method(this.currentFrame, start, end - start, this.totalFrames);
   },
   
   /**
    * Applies a value to an attribute
    * @param {String} attr The name of the attribute.
    * @param {Number} val The value to be applied to the attribute.
    * @param {String} unit The unit ('px', '%', etc.) of the value.
    */
   setAttribute: function(attr, val, unit) {
      if ( this.patterns.noNegatives.test(attr) ) {
         val = (val > 0) ? val : 0;
      }

      YAHOO.util.Dom.setStyle(this.getEl(), attr, val + unit);
   },                  
   
   /**
    * Returns current value of the attribute.
    * @param {String} attr The name of the attribute.
    * @return {Number} val The current value of the attribute.
    */
   getAttribute: function(attr) {
      var el = this.getEl();
      var val = YAHOO.util.Dom.getStyle(el, attr);

      if (val !== 'auto' && !this.patterns.offsetUnit.test(val)) {
         return parseFloat(val);
      }
      
      var a = this.patterns.offsetAttribute.exec(attr) || [];
      var pos = !!( a[3] ); // top or left
      var box = !!( a[2] ); // width or height
      
      // use offsets for width/height and abs pos top/left
      if ( box || (YAHOO.util.Dom.getStyle(el, 'position') == 'absolute' && pos) ) {
         val = el['offset' + a[0].charAt(0).toUpperCase() + a[0].substr(1)];
      } else { // default to zero for other 'auto'
         val = 0;
      }

      return val;
   },
   
   /**
    * Returns the unit to use when none is supplied.
    * Applies the "defaultUnit" test to decide whether to use pixels or not
    * @param {attr} attr The name of the attribute.
    * @return {String} The default unit to be used.
    */
   getDefaultUnit: function(attr) {
       if ( this.patterns.defaultUnit.test(attr) ) {
         return 'px';
       }
       
       return '';
   },
      
   /**
    * Sets the actual values to be used during the animation.
    * Should only be needed for subclass use.
    * @param {Object} attr The attribute object
    * @private 
    */
   setRuntimeAttribute: function(attr) {
      var start;
      var end;
      var attributes = this.attributes;

      this.runtimeAttributes[attr] = {};
      
      var isset = function(prop) {
         return (typeof prop !== 'undefined');
      };
      
      if ( !isset(attributes[attr]['to']) && !isset(attributes[attr]['by']) ) {
         return false; // note return; nothing to animate to
      }
      
      start = ( isset(attributes[attr]['from']) ) ? attributes[attr]['from'] : this.getAttribute(attr);

      // To beats by, per SMIL 2.1 spec
      if ( isset(attributes[attr]['to']) ) {
         end = attributes[attr]['to'];
      } else if ( isset(attributes[attr]['by']) ) {
         if (start.constructor == Array) {
            end = [];
            for (var i = 0, len = start.length; i < len; ++i) {
               end[i] = start[i] + attributes[attr]['by'][i];
            }
         } else {
            end = start + attributes[attr]['by'];
         }
      }
      
      this.runtimeAttributes[attr].start = start;
      this.runtimeAttributes[attr].end = end;

      // set units if needed
      this.runtimeAttributes[attr].unit = ( isset(attributes[attr].unit) ) ? attributes[attr]['unit'] : this.getDefaultUnit(attr);
   },

   /**
    * @param {String or HTMLElement} el Reference to the element that will be animated
    * @param {Object} attributes The attribute(s) to be animated.  
    * Each attribute is an object with at minimum a "to" or "by" member defined.  
    * Additional optional members are "from" (defaults to current value), "units" (defaults to "px").  
    * All attribute names use camelCase.
    * @param {Number} duration (optional, defaults to 1 second) Length of animation (frames or seconds), defaults to time-based
    * @param {Function} method (optional, defaults to YAHOO.util.Easing.easeNone) Computes the values that are applied to the attributes per frame (generally a YAHOO.util.Easing method)
    */ 
   init: function(el, attributes, duration, method) {
      /**
       * Whether or not the animation is running.
       * @private
       * @type Boolean
       */
      var isAnimated = false;
      
      /**
       * A Date object that is created when the animation begins.
       * @private
       * @type Date
       */
      var startTime = null;
      
      /**
       * The number of frames this animation was able to execute.
       * @private
       * @type Int
       */
      var actualFrames = 0; 

      /**
       * The element to be animated.
       * @private
       * @type HTMLElement
       */
      el = YAHOO.util.Dom.get(el);
      
      /**
       * The collection of attributes to be animated.  
       * Each attribute must have at least a "to" or "by" defined in order to animate.  
       * If "to" is supplied, the animation will end with the attribute at that value.  
       * If "by" is supplied, the animation will end at that value plus its starting value. 
       * If both are supplied, "to" is used, and "by" is ignored. 
       * @member YAHOO#util#Anim
       * Optional additional member include "from" (the value the attribute should start animating from, defaults to current value), and "unit" (the units to apply to the values).
       * @type Object
       */
      this.attributes = attributes || {};
      
      /**
       * The length of the animation.  Defaults to "1" (second).
       * @type Number
       */
      this.duration = duration || 1;
      
      /**
       * The method that will provide values to the attribute(s) during the animation. 
       * Defaults to "YAHOO.util.Easing.easeNone".
       * @type Function
       */
      this.method = method || YAHOO.util.Easing.easeNone;

      /**
       * Whether or not the duration should be treated as seconds.
       * Defaults to true.
       * @type Boolean
       */
      this.useSeconds = true; // default to seconds
      
      /**
       * The location of the current animation on the timeline.
       * In time-based animations, this is used by AnimMgr to ensure the animation finishes on time.
       * @type Int
       */
      this.currentFrame = 0;
      
      /**
       * The total number of frames to be executed.
       * In time-based animations, this is used by AnimMgr to ensure the animation finishes on time.
       * @type Int
       */
      this.totalFrames = YAHOO.util.AnimMgr.fps;
      
      
      /**
       * Returns a reference to the animated element.
       * @return {HTMLElement}
       */
      this.getEl = function() { return el; };
      
      /**
       * Checks whether the element is currently animated.
       * @return {Boolean} current value of isAnimated.    
       */
      this.isAnimated = function() {
         return isAnimated;
      };
      
      /**
       * Returns the animation start time.
       * @return {Date} current value of startTime.     
       */
      this.getStartTime = function() {
         return startTime;
      };      
      
      this.runtimeAttributes = {};
      
      var logger = {};
      logger.log = function() {YAHOO.log.apply(window, arguments)};
      
      logger.log('creating new instance of ' + this);
      
      /**
       * Starts the animation by registering it with the animation manager.   
       */
      this.animate = function() {
         if ( this.isAnimated() ) { return false; }
         
         this.currentFrame = 0;
         
         this.totalFrames = ( this.useSeconds ) ? Math.ceil(YAHOO.util.AnimMgr.fps * this.duration) : this.duration;
   
         YAHOO.util.AnimMgr.registerElement(this);
      };
        
      /**
       * Stops the animation.  Normally called by AnimMgr when animation completes.
       */ 
      this.stop = function() {
         YAHOO.util.AnimMgr.stop(this);
      };
      
      var onStart = function() {
         this.onStart.fire();
         for (var attr in this.attributes) {
            this.setRuntimeAttribute(attr);
         }
         
         isAnimated = true;
         actualFrames = 0;
         startTime = new Date(); 
      };
      
      /**
       * Feeds the starting and ending values for each animated attribute to doMethod once per frame, then applies the resulting value to the attribute(s).
       * @private
       */
       
      var onTween = function() {
         var data = {
            duration: new Date() - this.getStartTime(),
            currentFrame: this.currentFrame
         };
         
         data.toString = function() {
            return (
               'duration: ' + data.duration +
               ', currentFrame: ' + data.currentFrame
            );
         };
         
         this.onTween.fire(data);
         
         var runtimeAttributes = this.runtimeAttributes;
         
         for (var attr in runtimeAttributes) {
            this.setAttribute(attr, this.doMethod(attr, runtimeAttributes[attr].start, runtimeAttributes[attr].end), runtimeAttributes[attr].unit); 
         }
         
         actualFrames += 1;
      };
      
      var onComplete = function() {
         var actual_duration = (new Date() - startTime) / 1000 ;
         
         var data = {
            duration: actual_duration,
            frames: actualFrames,
            fps: actualFrames / actual_duration
         };
         
         data.toString = function() {
            return (
               'duration: ' + data.duration +
               ', frames: ' + data.frames +
               ', fps: ' + data.fps
            );
         };
         
         isAnimated = false;
         actualFrames = 0;
         this.onComplete.fire(data);
      };
      
      /**
       * Custom event that fires after onStart, useful in subclassing
       * @private
       */   
      this._onStart = new YAHOO.util.CustomEvent('_start', this, true);

      /**
       * Custom event that fires when animation begins
       * Listen via subscribe method (e.g. myAnim.onStart.subscribe(someFunction)
       */   
      this.onStart = new YAHOO.util.CustomEvent('start', this);
      
      /**
       * Custom event that fires between each frame
       * Listen via subscribe method (e.g. myAnim.onTween.subscribe(someFunction)
       */
      this.onTween = new YAHOO.util.CustomEvent('tween', this);
      
      /**
       * Custom event that fires after onTween
       * @private
       */
      this._onTween = new YAHOO.util.CustomEvent('_tween', this, true);
      
      /**
       * Custom event that fires when animation ends
       * Listen via subscribe method (e.g. myAnim.onComplete.subscribe(someFunction)
       */
      this.onComplete = new YAHOO.util.CustomEvent('complete', this);
      /**
       * Custom event that fires after onComplete
       * @private
       */
      this._onComplete = new YAHOO.util.CustomEvent('_complete', this, true);

      this._onStart.subscribe(onStart);
      this._onTween.subscribe(onTween);
      this._onComplete.subscribe(onComplete);
   }
};

/**
 * @class Handles animation queueing and threading.
 * Used by Anim and subclasses.
 */
YAHOO.util.AnimMgr = new function() {
   /** 
    * Reference to the animation Interval
    * @private
    * @type Int
    */
   var thread = null;
   
   /** 
    * The current queue of registered animation objects.
    * @private
    * @type Array
    */   
   var queue = [];

   /** 
    * The number of active animations.
    * @private
    * @type Int
    */      
   var tweenCount = 0;

   /** 
    * Base frame rate (frames per second). 
    * Arbitrarily high for better x-browser calibration (slower browsers drop more frames).
    * @type Int
    * 
    */
   this.fps = 200;

   /** 
    * Interval delay in milliseconds, defaults to fastest possible.
    * @type Int
    * 
    */
   this.delay = 1;

   /**
    * Adds an animation instance to the animation queue.
    * All animation instances must be registered in order to animate.
    * @param {object} tween The Anim instance to be be registered
    */
   this.registerElement = function(tween) {
      queue[queue.length] = tween;
      tweenCount += 1;
      tween._onStart.fire();
      this.start();
   };
   
   this.unRegister = function(tween, index) {
      tween._onComplete.fire();
      index = index || getIndex(tween);
      if (index != -1) { queue.splice(index, 1); }
      
      tweenCount -= 1;
      if (tweenCount <= 0) { this.stop(); }
   };
   
   /**
    * Starts the animation thread.
	 * Only one thread can run at a time.
    */   
   this.start = function() {
      if (thread === null) { thread = setInterval(this.run, this.delay); }
   };

   /**
    * Stops the animation thread or a specific animation instance.
    * @param {object} tween A specific Anim instance to stop (optional)
    * If no instance given, Manager stops thread and all animations.
    */   
   this.stop = function(tween) {
      if (!tween) {
         clearInterval(thread);
         for (var i = 0, len = queue.length; i < len; ++i) {
            if (queue[i].isAnimated()) {
               this.unRegister(tween, i);  
            }
         }
         queue = [];
         thread = null;
         tweenCount = 0;
      }
      else {
         this.unRegister(tween);
      }
   };
   
   /**
    * Called per Interval to handle each animation frame.
    */   
   this.run = function() {
      for (var i = 0, len = queue.length; i < len; ++i) {
         var tween = queue[i];
         if ( !tween || !tween.isAnimated() ) { continue; }

         if (tween.currentFrame < tween.totalFrames || tween.totalFrames === null)
         {
            tween.currentFrame += 1;
            
            if (tween.useSeconds) {
               correctFrame(tween);
            }
            tween._onTween.fire();        
         }
         else { YAHOO.util.AnimMgr.stop(tween, i); }
      }
   };
   
   var getIndex = function(anim) {
      for (var i = 0, len = queue.length; i < len; ++i) {
         if (queue[i] == anim) {
            return i; // note return;
         }
      }
      return -1;
   };
   
   /**
    * On the fly frame correction to keep animation on time.
    * @private
    * @param {Object} tween The Anim instance being corrected.
    */
   var correctFrame = function(tween) {
      var frames = tween.totalFrames;
      var frame = tween.currentFrame;
      var expected = (tween.currentFrame * tween.duration * 1000 / tween.totalFrames);
      var elapsed = (new Date() - tween.getStartTime());
      var tweak = 0;
      
      if (elapsed < tween.duration * 1000) { // check if falling behind
         tweak = Math.round((elapsed / expected - 1) * tween.currentFrame);
      } else { // went over duration, so jump to end
         tweak = frames - (frame + 1); 
      }
      if (tweak > 0 && isFinite(tweak)) { // adjust if needed
         if (tween.currentFrame + tweak >= frames) {// dont go past last frame
            tweak = frames - (frame + 1);
         }
         
         tween.currentFrame += tweak;     
      }
   };
};
/**
 *
 * @class Used to calculate Bezier splines for any number of control points.
 *
 */
YAHOO.util.Bezier = new function() 
{
   /**
    * Get the current position of the animated element based on t.
    * Each point is an array of "x" and "y" values (0 = x, 1 = y)
    * At least 2 points are required (start and end).
    * First point is start. Last point is end.
    * Additional control points are optional.    
    * @param {Array} points An array containing Bezier points
    * @param {Number} t A number between 0 and 1 which is the basis for determining current position
    * @return {Array} An array containing int x and y member data
    */
   this.getPosition = function(points, t)
   {  
      var n = points.length;
      var tmp = [];

      for (var i = 0; i < n; ++i){
         tmp[i] = [points[i][0], points[i][1]]; // save input
      }
      
      for (var j = 1; j < n; ++j) {
         for (i = 0; i < n - j; ++i) {
            tmp[i][0] = (1 - t) * tmp[i][0] + t * tmp[parseInt(i + 1, 10)][0];
            tmp[i][1] = (1 - t) * tmp[i][1] + t * tmp[parseInt(i + 1, 10)][1]; 
         }
      }
   
      return [ tmp[0][0], tmp[0][1] ]; 
   
   };
};

(function() {
	/**
	 * @class ColorAnim subclass for color fading
	 * <p>Usage: <code>var myAnim = new Y.ColorAnim(el, { backgroundColor: { from: '#FF0000', to: '#FFFFFF' } }, 1, Y.Easing.easeOut);</code></p>
	 * <p>Color values can be specified with either 112233, #112233, [255,255,255], or rgb(255,255,255)
	 * @requires YAHOO.util.Anim
	 * @requires YAHOO.util.AnimMgr
	 * @requires YAHOO.util.Easing
	 * @requires YAHOO.util.Bezier
	 * @requires YAHOO.util.Dom
	 * @requires YAHOO.util.Event
	 * @alias YAHOO.util.ColorAnim
	 * @constructor
	 * @param {HTMLElement | String} el Reference to the element that will be animated
	 * @param {Object} attributes The attribute(s) to be animated.
	 * Each attribute is an object with at minimum a "to" or "by" member defined.
	 * Additional optional members are "from" (defaults to current value), "units" (defaults to "px").
	 * All attribute names use camelCase.
	 * @param {Number} duration (optional, defaults to 1 second) Length of animation (frames or seconds), defaults to time-based
	 * @param {Function} method (optional, defaults to YAHOO.util.Easing.easeNone) Computes the values that are applied to the attributes per frame (generally a YAHOO.util.Easing method)
	 */
   YAHOO.util.ColorAnim = function(el, attributes, duration,  method) {
      YAHOO.util.ColorAnim.superclass.constructor.call(this, el, attributes, duration, method);
   };
   
   YAHOO.extend(YAHOO.util.ColorAnim, YAHOO.util.Anim);
   
   // shorthand
   var Y = YAHOO.util;
   var superclass = Y.ColorAnim.superclass;
   /**
 	* @alias YAHOO.util.ColorAnim.prototype
 	*/
   var proto = Y.ColorAnim.prototype;
   
   /**
    * toString method
 	* @alias YAHOO.util.ColorAnim.prototype.toString
    * @return {String} string represenation of anim obj
    */
   proto.toString = function() {
      var el = this.getEl();
      var id = el.id || el.tagName;
      return ("ColorAnim " + id);
   };
   
   /**
    * Only certain attributes should be treated as colors.
 	* @alias YAHOO.util.ColorAnim.prototype.color
    * @type Object
    */
   proto.patterns.color = /color$/i;
   proto.patterns.rgb    = /^rgb\(([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\)$/i;
   proto.patterns.hex    = /^#?([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})$/i;
   proto.patterns.hex3   = /^#?([0-9A-F]{1})([0-9A-F]{1})([0-9A-F]{1})$/i;
   
   /**
    * Attempts to parse the given string and return a 3-tuple.
 	* @alias YAHOO.util.ColorAnim.prototype.parseColor
    * @param {String} s The string to parse.
    * @return {Array} The 3-tuple of rgb values.
    */
   proto.parseColor = function(s) {
      if (s.length == 3) { return s; }
   
      var c = this.patterns.hex.exec(s);
      if (c && c.length == 4) {
         return [ parseInt(c[1], 16), parseInt(c[2], 16), parseInt(c[3], 16) ];
      }
   
      c = this.patterns.rgb.exec(s);
      if (c && c.length == 4) {
         return [ parseInt(c[1], 10), parseInt(c[2], 10), parseInt(c[3], 10) ];
      }
   
      c = this.patterns.hex3.exec(s);
      if (c && c.length == 4) {
         return [ parseInt(c[1] + c[1], 16), parseInt(c[2] + c[2], 16), parseInt(c[3] + c[3], 16) ];
      }
      
      return null;
   };
   
   /**
    * Returns current value of the attribute.
 	* @alias YAHOO.util.ColorAnim.prototype.getAttribute
    * @param {String} attr The name of the attribute.
    * @return {Number} val The current value of the attribute.
    */
   proto.getAttribute = function(attr) {
      var el = this.getEl();
      if (  this.patterns.color.test(attr) ) {
         var val = YAHOO.util.Dom.getStyle(el, attr);
         
         if (val == 'transparent') { // bgcolor default
            var parent = el.parentNode; // try and get from an ancestor
            val = Y.Dom.getStyle(parent, attr);
         
            while (parent && val == 'transparent') {
               parent = parent.parentNode;
               val = Y.Dom.getStyle(parent, attr);
               if (parent.tagName.toUpperCase() == 'HTML') {
                  val = 'ffffff';
               }
            }
         }
      } else {
         val = superclass.getAttribute.call(this, attr);
      }

      return val;
   };
   
   /**
    * Returns the value computed by the animation's "method".
 	* @alias YAHOO.util.ColorAnim.prototype.doMethod
    * @param {String} attr The name of the attribute.
    * @param {Number} start The value this attribute should start from for this animation.
    * @param {Number} end  The value this attribute should end at for this animation.
    * @return {Number} The Value to be applied to the attribute.
    */
   proto.doMethod = function(attr, start, end) {
      var val;
   
      if ( this.patterns.color.test(attr) ) {
         val = [];
         for (var i = 0, len = start.length; i < len; ++i) {
            val[i] = superclass.doMethod.call(this, attr, start[i], end[i]);
         }
         
         val = 'rgb('+Math.floor(val[0])+','+Math.floor(val[1])+','+Math.floor(val[2])+')';
      }
      else {
         val = superclass.doMethod.call(this, attr, start, end);
      }

      return val;
   };
   
   /**
    * Sets the actual values to be used during the animation.
    * Should only be needed for subclass use.setRuntimeAttribute
 	* @alias YAHOO.util.ColorAnim.prototype.
    * @param {Object} attr The attribute object
    * @private 
    */
   proto.setRuntimeAttribute = function(attr) {
      superclass.setRuntimeAttribute.call(this, attr);
      
      if ( this.patterns.color.test(attr) ) {
         var attributes = this.attributes;
         var start = this.parseColor(this.runtimeAttributes[attr].start);
         var end = this.parseColor(this.runtimeAttributes[attr].end);
         // fix colors if going "by"
         if ( typeof attributes[attr]['to'] === 'undefined' && typeof attributes[attr]['by'] !== 'undefined' ) {
            end = this.parseColor(attributes[attr].by);
         
            for (var i = 0, len = start.length; i < len; ++i) {
               end[i] = start[i] + end[i];
            }
         }
         
         this.runtimeAttributes[attr].start = start;
         this.runtimeAttributes[attr].end = end;
      }
   };
})();
/*
TERMS OF USE - EASING EQUATIONS
Open source under the BSD License.
Copyright © 2001 Robert Penner All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the author nor the names of contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

*/

YAHOO.util.Easing = {

   /**
    * Uniform speed between points.
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeNone: function (t, b, c, d) {
   	return c*t/d + b;
   },
   
   /**
    * Begins slowly and accelerates towards end. (quadratic)
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeIn: function (t, b, c, d) {
   	return c*(t/=d)*t + b;
   },

   /**
    * Begins quickly and decelerates towards end.  (quadratic)
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeOut: function (t, b, c, d) {
   	return -c *(t/=d)*(t-2) + b;
   },
   
   /**
    * Begins slowly and decelerates towards end. (quadratic)
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeBoth: function (t, b, c, d) {
   	if ((t/=d/2) < 1) return c/2*t*t + b;
   	return -c/2 * ((--t)*(t-2) - 1) + b;
   },
   
   /**
    * Begins slowly and accelerates towards end. (quartic)
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeInStrong: function (t, b, c, d) {
   	return c*(t/=d)*t*t*t + b;
   },
   
   /**
    * Begins quickly and decelerates towards end.  (quartic)
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeOutStrong: function (t, b, c, d) {
   	return -c * ((t=t/d-1)*t*t*t - 1) + b;
   },
   
   /**
    * Begins slowly and decelerates towards end. (quartic)
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   easeBothStrong: function (t, b, c, d) {
   	if ((t/=d/2) < 1) return c/2*t*t*t*t + b;
   	return -c/2 * ((t-=2)*t*t*t - 2) + b;
   },

   /**
    * snap in elastic effect
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @param {Number} p Period (optional)
    * @return {Number} The computed value for the current animation frame.
    */

   elasticIn: function (t, b, c, d, a, p) {
   	if (t==0) return b;  if ((t/=d)==1) return b+c;  if (!p) p=d*.3;
   	if (!a || a < Math.abs(c)) { a=c; var s=p/4; }
   	else var s = p/(2*Math.PI) * Math.asin (c/a);
   	return -(a*Math.pow(2,10*(t-=1)) * Math.sin( (t*d-s)*(2*Math.PI)/p )) + b;
   },

   /**
    * snap out elastic effect
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @param {Number} p Period (optional)
    * @return {Number} The computed value for the current animation frame.
    */
   elasticOut: function (t, b, c, d, a, p) {
   	if (t==0) return b;  if ((t/=d)==1) return b+c;  if (!p) p=d*.3;
   	if (!a || a < Math.abs(c)) { a=c; var s=p/4; }
   	else var s = p/(2*Math.PI) * Math.asin (c/a);
   	return a*Math.pow(2,-10*t) * Math.sin( (t*d-s)*(2*Math.PI)/p ) + c + b;
   },
   
   /**
    * snap both elastic effect
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @param {Number} p Period (optional)
    * @return {Number} The computed value for the current animation frame.
    */
   elasticBoth: function (t, b, c, d, a, p) {
   	if (t==0) return b;  if ((t/=d/2)==2) return b+c;  if (!p) p=d*(.3*1.5);
   	if (!a || a < Math.abs(c)) { a=c; var s=p/4; }
   	else var s = p/(2*Math.PI) * Math.asin (c/a);
   	if (t < 1) return -.5*(a*Math.pow(2,10*(t-=1)) * Math.sin( (t*d-s)*(2*Math.PI)/p )) + b;
   	return a*Math.pow(2,-10*(t-=1)) * Math.sin( (t*d-s)*(2*Math.PI)/p )*.5 + c + b;
   },


   /**
    * back easing in - backtracking slightly, then reversing direction and moving to target
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @param {Number) s Overshoot (optional)
    * @return {Number} The computed value for the current animation frame.
    */
   backIn: function (t, b, c, d, s) {
   	if (typeof s == 'undefined') s = 1.70158;
   	return c*(t/=d)*t*((s+1)*t - s) + b;
   },

   /**
    * back easing out - moving towards target, overshooting it slightly,
    * then reversing and coming back to target
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @param {Number) s Overshoot (optional)
    * @return {Number} The computed value for the current animation frame.
    */
   backOut: function (t, b, c, d, s) {
   	if (typeof s == 'undefined') s = 1.70158;
   	return c*((t=t/d-1)*t*((s+1)*t + s) + 1) + b;
   },
   
   /**
    * back easing in/out - backtracking slightly, then reversing direction and moving to target,
    * then overshooting target, reversing, and finally coming back to target
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @param {Number) s Overshoot (optional)
    * @return {Number} The computed value for the current animation frame.
    */
   backBoth: function (t, b, c, d, s) {
   	if (typeof s == 'undefined') s = 1.70158; 
   	if ((t/=d/2) < 1) return c/2*(t*t*(((s*=(1.525))+1)*t - s)) + b;
   	return c/2*((t-=2)*t*(((s*=(1.525))+1)*t + s) + 2) + b;
   },

   /**
    * bounce in
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   bounceIn: function (t, b, c, d) {
   	return c - YAHOO.util.Easing.bounceOut(d-t, 0, c, d) + b;
   },
   
   /**
    * bounce out
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   bounceOut: function (t, b, c, d) {
   	if ((t/=d) < (1/2.75)) {
   		return c*(7.5625*t*t) + b;
   	} else if (t < (2/2.75)) {
   		return c*(7.5625*(t-=(1.5/2.75))*t + .75) + b;
   	} else if (t < (2.5/2.75)) {
   		return c*(7.5625*(t-=(2.25/2.75))*t + .9375) + b;
   	} else {
   		return c*(7.5625*(t-=(2.625/2.75))*t + .984375) + b;
   	}
   },
   
   /**
    * bounce both
    * @param {Number} t Time value used to compute current value.
    * @param {Number} b Starting value.
    * @param {Number} c Delta between start and end values.
    * @param {Number} d Total length of animation.
    * @return {Number} The computed value for the current animation frame.
    */
   bounceBoth: function (t, b, c, d) {
   	if (t < d/2) return YAHOO.util.Easing.bounceIn(t*2, 0, c, d) * .5 + b;
   	return YAHOO.util.Easing.bounceOut(t*2-d, 0, c, d) * .5 + c*.5 + b;
   }
};


(function() {
	/**
	 * @class Anim subclass for moving elements along a path defined by the "points" member of "attributes".  All "points" are arrays with x, y coordinates.
	 * <p>Usage: <code>var myAnim = new YAHOO.util.Motion(el, { points: { to: [800, 800] } }, 1, YAHOO.util.Easing.easeOut);</code></p>
	 * @requires YAHOO.util.Anim
	 * @requires YAHOO.util.AnimMgr
	 * @requires YAHOO.util.Easing
	 * @requires YAHOO.util.Bezier
	 * @requires YAHOO.util.Dom
	 * @requires YAHOO.util.Event
	 * @requires YAHOO.util.CustomEvent 
	 * @alias YAHOO.util.Motion
	 * @constructor
	 * @param {String or HTMLElement} el Reference to the element that will be animated
	 * @param {Object} attributes The attribute(s) to be animated.  
	 * Each attribute is an object with at minimum a "to" or "by" member defined.  
	 * Additional optional members are "from" (defaults to current value), "units" (defaults to "px").  
	 * All attribute names use camelCase.
	 * @param {Number} duration (optional, defaults to 1 second) Length of animation (frames or seconds), defaults to time-based
	 * @param {Function} method (optional, defaults to YAHOO.util.Easing.easeNone) Computes the values that are applied to the attributes per frame (generally a YAHOO.util.Easing method)
	 */
   YAHOO.util.Motion = function(el, attributes, duration,  method) {
      if (el) { // dont break existing subclasses not using YAHOO.extend
         YAHOO.util.Motion.superclass.constructor.call(this, el, attributes, duration, method);
      }
   };

   YAHOO.extend(YAHOO.util.Motion, YAHOO.util.ColorAnim);
   
   // shorthand
   var Y = YAHOO.util;
   var superclass = Y.Motion.superclass;
   var proto = Y.Motion.prototype;

   /**
    * toString method
	* @alias YAHOO.util.Motion.prototype.toString
    * @return {String} string represenation of anim obj
    */
   proto.toString = function() {
      var el = this.getEl();
      var id = el.id || el.tagName;
      return ("Motion " + id);
   };
   
   proto.patterns.points = /^points$/i;
   
   /**
    * Applies a value to an attribute
	* @alias YAHOO.util.Motion.prototype.setAttribute
    * @param {String} attr The name of the attribute.
    * @param {Number} val The value to be applied to the attribute.
    * @param {String} unit The unit ('px', '%', etc.) of the value.
    */
   proto.setAttribute = function(attr, val, unit) {
      if (  this.patterns.points.test(attr) ) {
         unit = unit || 'px';
         superclass.setAttribute.call(this, 'left', val[0], unit);
         superclass.setAttribute.call(this, 'top', val[1], unit);
      } else {
         superclass.setAttribute.call(this, attr, val, unit);
      }
   };
   
   /**
    * Sets the default value to be used when "from" is not supplied.
	* @alias YAHOO.util.Motion.prototype.getAttribute
    * @param {String} attr The attribute being set.
    * @param {Number} val The default value to be applied to the attribute.
    */
   proto.getAttribute = function(attr) {
      if (  this.patterns.points.test(attr) ) {
         var val = [
            superclass.getAttribute.call(this, 'left'),
            superclass.getAttribute.call(this, 'top')
         ];
      } else {
         val = superclass.getAttribute.call(this, attr);
      }

      return val;
   };
   
   /**
    * Returns the value computed by the animation's "method".
	* @alias YAHOO.util.Motion.prototype.doMethod
    * @param {String} attr The name of the attribute.
    * @param {Number} start The value this attribute should start from for this animation.
    * @param {Number} end  The value this attribute should end at for this animation.
    * @return {Number} The Value to be applied to the attribute.
    */
   proto.doMethod = function(attr, start, end) {
      var val = null;

      if ( this.patterns.points.test(attr) ) {
         var t = this.method(this.currentFrame, 0, 100, this.totalFrames) / 100;				
         val = Y.Bezier.getPosition(this.runtimeAttributes[attr], t);
      } else {
         val = superclass.doMethod.call(this, attr, start, end);
      }
      return val;
   };
   
   /**
    * Sets the actual values to be used during the animation.
    * Should only be needed for subclass use.
	* @alias YAHOO.util.Motion.prototype.setRuntimeAttribute
    * @param {Object} attr The attribute object
    * @private 
    */
   proto.setRuntimeAttribute = function(attr) {
      if ( this.patterns.points.test(attr) ) {
         var el = this.getEl();
         var attributes = this.attributes;
         var start;
         var control = attributes['points']['control'] || [];
         var end;
         var i, len;
         
         if (control.length > 0 && !(control[0] instanceof Array) ) { // could be single point or array of points
            control = [control];
         } else { // break reference to attributes.points.control
            var tmp = []; 
            for (i = 0, len = control.length; i< len; ++i) {
               tmp[i] = control[i];
            }
            control = tmp;
         }

         if (Y.Dom.getStyle(el, 'position') == 'static') { // default to relative
            Y.Dom.setStyle(el, 'position', 'relative');
         }
   
         if ( isset(attributes['points']['from']) ) {
            Y.Dom.setXY(el, attributes['points']['from']); // set position to from point
         } 
         else { Y.Dom.setXY( el, Y.Dom.getXY(el) ); } // set it to current position
         
         start = this.getAttribute('points'); // get actual top & left
         
         // TO beats BY, per SMIL 2.1 spec
         if ( isset(attributes['points']['to']) ) {
            end = translateValues.call(this, attributes['points']['to'], start);
            
            var pageXY = Y.Dom.getXY(this.getEl());
            for (i = 0, len = control.length; i < len; ++i) {
               control[i] = translateValues.call(this, control[i], start);
            }

            
         } else if ( isset(attributes['points']['by']) ) {
            end = [ start[0] + attributes['points']['by'][0], start[1] + attributes['points']['by'][1] ];
            
            for (i = 0, len = control.length; i < len; ++i) {
               control[i] = [ start[0] + control[i][0], start[1] + control[i][1] ];
            }
         }

         this.runtimeAttributes[attr] = [start];
         
         if (control.length > 0) {
            this.runtimeAttributes[attr] = this.runtimeAttributes[attr].concat(control); 
         }

         this.runtimeAttributes[attr][this.runtimeAttributes[attr].length] = end;
      }
      else {
         superclass.setRuntimeAttribute.call(this, attr);
      }
   };
   
   var translateValues = function(val, start) {
      var pageXY = Y.Dom.getXY(this.getEl());
      val = [ val[0] - pageXY[0] + start[0], val[1] - pageXY[1] + start[1] ];

      return val; 
   };
   
   var isset = function(prop) {
      return (typeof prop !== 'undefined');
   };
})();
(function() {
	/**
	 * @class Anim subclass for scrolling elements to a position defined by the "scroll" member of "attributes".  All "scroll" members are arrays with x, y scroll positions.
	 * <p>Usage: <code>var myAnim = new YAHOO.util.Scroll(el, { scroll: { to: [0, 800] } }, 1, YAHOO.util.Easing.easeOut);</code></p>
	 * @requires YAHOO.util.Anim
	 * @requires YAHOO.util.AnimMgr
	 * @requires YAHOO.util.Easing
	 * @requires YAHOO.util.Bezier
	 * @requires YAHOO.util.Dom
	 * @requires YAHOO.util.Event
	 * @requires YAHOO.util.CustomEvent 
	 * @alias YAHOO.util.Scroll
	 * @constructor
	 * @param {String or HTMLElement} el Reference to the element that will be animated
	 * @param {Object} attributes The attribute(s) to be animated.  
	 * Each attribute is an object with at minimum a "to" or "by" member defined.  
	 * Additional optional members are "from" (defaults to current value), "units" (defaults to "px").  
	 * All attribute names use camelCase.
	 * @param {Number} duration (optional, defaults to 1 second) Length of animation (frames or seconds), defaults to time-based
	 * @param {Function} method (optional, defaults to YAHOO.util.Easing.easeNone) Computes the values that are applied to the attributes per frame (generally a YAHOO.util.Easing method)
	 */
   YAHOO.util.Scroll = function(el, attributes, duration,  method) {
      if (el) { // dont break existing subclasses not using YAHOO.extend
         YAHOO.util.Scroll.superclass.constructor.call(this, el, attributes, duration, method);
      }
   };

   YAHOO.extend(YAHOO.util.Scroll, YAHOO.util.ColorAnim);
   
   // shorthand
   var Y = YAHOO.util;
   var superclass = Y.Scroll.superclass;
   var proto = Y.Scroll.prototype;

   /**
    * toString method
	* @alias YAHOO.util.Scroll.prototype.toString
    * @return {String} string represenation of anim obj
    */
   proto.toString = function() {
      var el = this.getEl();
      var id = el.id || el.tagName;
      return ("Scroll " + id);
   };
   
   /**
    * Returns the value computed by the animation's "method".
	* @alias YAHOO.util.Scroll.prototype.doMethod
    * @param {String} attr The name of the attribute.
    * @param {Number} start The value this attribute should start from for this animation.
    * @param {Number} end  The value this attribute should end at for this animation.
    * @return {Number} The Value to be applied to the attribute.
    */
   proto.doMethod = function(attr, start, end) {
      var val = null;
   
      if (attr == 'scroll') {
         val = [
            this.method(this.currentFrame, start[0], end[0] - start[0], this.totalFrames),
            this.method(this.currentFrame, start[1], end[1] - start[1], this.totalFrames)
         ];
         
      } else {
         val = superclass.doMethod.call(this, attr, start, end);
      }
      return val;
   };
   
   /**
    * Returns current value of the attribute.
	* @alias YAHOO.util.Scroll.prototype.getAttribute
    * @param {String} attr The name of the attribute.
    * @return {Number} val The current value of the attribute.
    */
   proto.getAttribute = function(attr) {
      var val = null;
      var el = this.getEl();
      
      if (attr == 'scroll') {
         val = [ el.scrollLeft, el.scrollTop ];
      } else {
         val = superclass.getAttribute.call(this, attr);
      }
      
      return val;
   };
   
   /**
    * Applies a value to an attribute
	* @alias YAHOO.util.Scroll.prototype.setAttribute
    * @param {String} attr The name of the attribute.
    * @param {Number} val The value to be applied to the attribute.
    * @param {String} unit The unit ('px', '%', etc.) of the value.
    */
   proto.setAttribute = function(attr, val, unit) {
      var el = this.getEl();
      
      if (attr == 'scroll') {
         el.scrollLeft = val[0];
         el.scrollTop = val[1];
      } else {
         superclass.setAttribute.call(this, attr, val, unit);
      }
   };
})();
