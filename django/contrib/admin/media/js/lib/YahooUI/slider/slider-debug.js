
/*                                                                                                                                                      
Copyright (c) 2006, Yahoo! Inc. All rights reserved.                                                                                                    
Code licensed under the BSD License:                                                                                                                    
http://developer.yahoo.net/yui/license.txt                                                                                                              
version: 0.11.0                                                                                                                                         
*/ 

/**
 * A DragDrop implementation that can be used as a background for a
 * slider.  It takes a reference to the thumb instance 
 * so it can delegate some of the events to it.  The goal is to make the 
 * thumb jump to the location on the background when the background is 
 * clicked.  
 *
 * @extends YAHOO.util.DragDrop
 * @constructor
 * @param {String} id     The id of the element linked to this instance
 * @param {String} sGroup The group of related DragDrop items
 * @param {String} sType  The type of slider (horiz, vert, region)
 */
YAHOO.widget.Slider = function(sElementId, sGroup, oThumb, sType) {
	if (sElementId) {

        /**
         * The type of the slider (horiz, vert, region)
         * @type string
         */
        this.type = sType;

		this.init(sElementId, sGroup, true);

        this.logger = new YAHOO.widget.LogWriter(this.toString());

		var self = this;

		/**
		 * a YAHOO.widget.SliderThumb instance that we will use to 
		 * reposition the thumb when the background is clicked
		 *
		 * @type Slider 
		 */
		this.thumb = oThumb;

		// add handler for the handle onchange event
		oThumb.onChange = function() { 
			self.onThumbChange(); 
		};


		/**
		 * Overrides the isTarget property in YAHOO.util.DragDrop
		 * @private
		 */
		this.isTarget = false;
	
		/**
		 * Flag that determines if the thumb will animate when moved
		 * @type boolean
		 */
		this.animate = YAHOO.widget.Slider.ANIM_AVAIL;

        /**
         * Set to false to disable a background click thumb move
         */
        this.backgroundEnabled = true;

		/**
		 * Adjustment factor for tick animation, the more ticks, the
		 * faster the animation (by default)
		 *
		 * @type int
		 */
		this.tickPause = 40;
		if (oThumb._isHoriz && oThumb.xTicks && oThumb.xTicks.length) {
			this.tickPause = Math.round(360 / oThumb.xTicks.length);
		} else if (oThumb.yTicks && oThumb.yTicks.length) {
			this.tickPause = Math.round(360 / oThumb.yTicks.length);
		}

        this.logger.log("tickPause: " + this.tickPause);

		// delegate thumb methods
		oThumb.onMouseDown = function () { return self.focus(); };
		//oThumb.b4MouseDown = function () { return self.b4MouseDown(); };
		// oThumb.lock = function() { self.lock(); };
		// oThumb.unlock = function() { self.unlock(); };
		oThumb.onMouseUp = function() { self.thumbMouseUp(); };
		oThumb.onDrag = function() { self.fireEvents(); };
		oThumb.onAvailable = function() { return self.setStartSliderState(); };
	}
};

//YAHOO.widget.Slider.prototype = new YAHOO.util.DragDrop();
YAHOO.extend(YAHOO.widget.Slider, YAHOO.util.DragDrop);

// YAHOO.widget.Slider.prototype.onAvailable = function() {
    // this.logger.log("bg avail");
// };

/**
 * Factory method for creating a horizontal slider
 *
 * @param {String} sBGElId the id of the slider's background element
 * @param {String} sHandleElId the id of the thumb element
 * @param {int} iLeft the number of pixels the element can move left
 * @param {int} iRight the number of pixels the element can move right
 * @param {int} iTickSize optional parameter for specifying that the element 
 * should move a certain number pixels at a time.
 * @return {Slider} a horizontal slider control
 */
YAHOO.widget.Slider.getHorizSlider = 
	function (sBGElId, sHandleElId, iLeft, iRight, iTickSize) {
		return new YAHOO.widget.Slider(sBGElId, sBGElId, 
			new YAHOO.widget.SliderThumb(sHandleElId, sBGElId, 
							   iLeft, iRight, 0, 0, iTickSize), "horiz");
};

/**
 * Factory method for creating a vertical slider
 *
 * @param {String} sBGElId the id of the slider's background element
 * @param {String} sHandleElId the id of the thumb element
 * @param {int} iUp the number of pixels the element can move up
 * @param {int} iDown the number of pixels the element can move down
 * @param {int} iTickSize optional parameter for specifying that the element 
 * should move a certain number pixels at a time.
 * @return {Slider} a vertical slider control
 */
YAHOO.widget.Slider.getVertSlider = 
	function (sBGElId, sHandleElId, iUp, iDown, iTickSize) {
		return new YAHOO.widget.Slider(sBGElId, sBGElId, 
			new YAHOO.widget.SliderThumb(sHandleElId, sBGElId, 0, 0, 
							   iUp, iDown, iTickSize), "vert");
};

/**
 * Factory method for creating a slider region like the one in the color
 * picker example
 *
 * @param {String} sBGElId the id of the slider's background element
 * @param {String} sHandleElId the id of the thumb element
 * @param {int} iLeft the number of pixels the element can move left
 * @param {int} iRight the number of pixels the element can move right
 * @param {int} iUp the number of pixels the element can move up
 * @param {int} iDown the number of pixels the element can move down
 * @param {int} iTickSize optional parameter for specifying that the element 
 * should move a certain number pixels at a time.
 * @return {Slider} a slider region control
 */
YAHOO.widget.Slider.getSliderRegion = 
	function (sBGElId, sHandleElId, iLeft, iRight, iUp, iDown, iTickSize) {
		return new YAHOO.widget.Slider(sBGElId, sBGElId, 
			new YAHOO.widget.SliderThumb(sHandleElId, sBGElId, iLeft, iRight, 
							   iUp, iDown, iTickSize), "region");
};

/**
 * By default, animation is available if the animation library is detected.
 * @type boolean
 */
YAHOO.widget.Slider.ANIM_AVAIL = true;

YAHOO.widget.Slider.prototype.setStartSliderState = function() {

    this.logger.log("Fixing state");

    this.setThumbCenterPoint();

    /**
     * The basline position of the background element, used
     * to determine if the background has moved since the last
     * operation.
     * @type int[]
     */
    this.baselinePos = YAHOO.util.Dom.getXY(this.getEl());

    this.thumb.startOffset = this.thumb.getOffsetFromParent(this.baselinePos);

    if (this.thumb._isRegion) {
        if (this.deferredSetRegionValue) {
            this.setRegionValue.apply(this, this.deferredSetRegionValue, true);
        } else {
            this.setRegionValue(0, 0, true);
        }
    } else {
        if (this.deferredSetValue) {
            this.setValue.apply(this, this.deferredSetValue, true);
        } else {
            this.setValue(0, true, true);
        }
    }
};

YAHOO.widget.Slider.prototype.setThumbCenterPoint = function() {

    var el = this.thumb.getEl();

    if (el) {
        /**
         * the center of the slider element is stored so we can position 
         * place it in the correct position when the background is clicked
         *
         * @type Coordinate
         */
        this.thumbCenterPoint = { 
                x: parseInt(el.offsetWidth/2, 10), 
                y: parseInt(el.offsetHeight/2, 10) 
        };
    }

};

/**
 * Lock the slider, overrides YAHOO.util.DragDrop
 */
YAHOO.widget.Slider.prototype.lock = function() {
	this.logger.log("locking");
	this.thumb.lock();
	this.locked = true;
};

/**
 * Unlock the slider, overrides YAHOO.util.DragDrop
 */
YAHOO.widget.Slider.prototype.unlock = function() {
	this.logger.log("unlocking");
	this.thumb.unlock();
	this.locked = false;
};

/**
 * handles mouseup event on the slider background
 *
 * @private
 */
YAHOO.widget.Slider.prototype.thumbMouseUp = function() {
	this.logger.log("bg mouseup");
    if (!this.isLocked() && !this.moveComplete) {
	    this.endMove();
    }

};

/**
 * Returns a reference to this slider's thumb
 */
YAHOO.widget.Slider.prototype.getThumb = function() {
    return this.thumb;
};

/**
 * Try to focus the element when clicked so we can add
 * accessibility features
 *
 * @private
 */
YAHOO.widget.Slider.prototype.focus = function() {
    this.logger.log("focus");

    // Focus the background element if possible
    var el = this.getEl();

    if (el.focus) {
        el.focus();
    }

    this.verifyOffset();

    if (this.isLocked()) {
        return false;
    } else {
        this.onSlideStart();
	    return true;
    }
};

/**
 * Event that fires when the value of the slider has changed
 *
 * @param {int} offsetFromStart the number of pixels the thumb has moved
 * from its start position. Normal horizontal and vertical sliders will only
 * have the firstOffset.  Regions will have both, the first is the horizontal
 * offset, the second the vertical.
 */
YAHOO.widget.Slider.prototype.onChange = function (firstOffset, secondOffset) { 
	/* override me */ 
	this.logger.log("onChange: " + firstOffset + ", " + secondOffset);
};

/**
 * Event that fires when the at the beginning of the slider thumb move
 */
YAHOO.widget.Slider.prototype.onSlideStart = function () { 
	/* override me */ 
	this.logger.log("onSlideStart");
};

/**
 * Event that fires at the end of a slider thumb move
 */
YAHOO.widget.Slider.prototype.onSlideEnd = function () { 
	/* override me */ 
	this.logger.log("onSlideEnd");
};

/**
 * Returns the slider's thumb offset from the start position
 *
 * @return {int} the current value
 */
YAHOO.widget.Slider.prototype.getValue = function () { 
	return this.thumb.getValue();
};

/**
 * Returns the slider's thumb X offset from the start position
 *
 * @return {int} the current horizontal offset
 */
YAHOO.widget.Slider.prototype.getXValue = function () { 
	return this.thumb.getXValue();
};

/**
 * Returns the slider's thumb Y offset from the start position
 *
 * @return {int} the current vertical offset
 */
YAHOO.widget.Slider.prototype.getYValue = function () { 
	return this.thumb.getYValue();
};

/**
 * Internal handler for the slider thumb's onChange event
 * @private
 */
YAHOO.widget.Slider.prototype.onThumbChange = function () { 
	var t = this.thumb;
	if (t._isRegion) {
		t.onChange(t.getXValue(), t.getYValue());
	} else {
		t.onChange(t.getValue());
	}

};

/**
 * Provides a way to set the value of the slider in code.
 *
 * @param {int} newOffset the number of pixels the thumb should be
 * positioned away from the initial start point 
 * @param {boolean} skipAnim set to true to disable the animation
 * for this move action (but not others).
 * @param {boolean} force ignore the locked setting and set value anyway
 * @return {boolean} true if the move was performed, false if it failed
 */
YAHOO.widget.Slider.prototype.setValue = function(newOffset, skipAnim, force) {
    this.logger.log("setValue " + newOffset);

    if (!this.thumb.available) {
        this.logger.log("defer setValue until after onAvailble");
        this.deferredSetValue = arguments;
        return false;
    }

    if (this.isLocked() && !force) {
        this.logger.log("Can't set the value, the control is locked");
        return false;
    }

	if ( isNaN(newOffset) ) {
		this.logger.log("setValue, Illegal argument: " + newOffset);
		return false;
	}

	var t = this.thumb;
	var newX, newY;
    this.verifyOffset();
	if (t._isRegion) {
        return false;
	} else if (t._isHoriz) {
        this.onSlideStart();
		newX = t.initPageX + newOffset + this.thumbCenterPoint.x;
		this.moveThumb(newX, t.initPageY, skipAnim);
	} else {
        this.onSlideStart();
		newY = t.initPageY + newOffset + this.thumbCenterPoint.y;
		this.moveThumb(t.initPageX, newY, skipAnim);
	}

	return true;
};

/**
 * Provides a way to set the value of the region slider in code.
 *
 * @param {int} newOffset the number of pixels the thumb should be
 * positioned away from the initial start point 
 * @param {int} newOffset2 the number of pixels the thumb should be
 * positioned away from the initial start point (y axis for region)
 * @param {boolean} skipAnim set to true to disable the animation
 * for this move action (but not others).
 * @param {boolean} force ignore the locked setting and set value anyway
 * @return {boolean} true if the move was performed, false if it failed
 */
YAHOO.widget.Slider.prototype.setRegionValue = function(newOffset, newOffset2, skipAnim) {

    if (!this.thumb.available) {
        this.logger.log("defer setRegionValue until after onAvailble");
        this.deferredSetRegionValue = arguments;
        return false;
    }

    if (this.isLocked() && !force) {
        this.logger.log("Can't set the value, the control is locked");
        return false;
    }

	if ( isNaN(newOffset) ) {
		this.logger.log("setRegionValue, Illegal argument: " + newOffset);
		return false;
	}

	var t = this.thumb;
	if (t._isRegion) {
        this.onSlideStart();
		var newX = t.initPageX + newOffset + this.thumbCenterPoint.x;
		var newY = t.initPageY + newOffset2 + this.thumbCenterPoint.y;
		this.moveThumb(newX, newY, skipAnim);
	    return true;
	}

    return false;

};

/**
 * Checks the background position element position.  If it has moved from the
 * baseline position, the constraints for the thumb are reset
 * @return {boolean} True if the offset is the same as the baseline.
 */
YAHOO.widget.Slider.prototype.verifyOffset = function() {

    var newPos = YAHOO.util.Dom.getXY(this.getEl());
    this.logger.log("newPos: " + newPos);

    if (newPos[0] != this.baselinePos[0] || newPos[1] != this.baselinePos[1]) {
        this.logger.log("background moved, resetting constraints");
        this.thumb.resetConstraints();
        this.baselinePos = newPos;
        return false;
    }

    return true;
};

/**
 * Move the associated slider moved to a timeout to try to get around the 
 * mousedown stealing moz does when I move the slider element between the 
 * cursor and the background during the mouseup event
 *
 * @param {int} x the X coordinate of the click
 * @param {int} y the Y coordinate of the click
 * @param {boolean} skipAnim don't animate if the move happend onDrag
 * @private
 */
YAHOO.widget.Slider.prototype.moveThumb = function(x, y, skipAnim) {

        this.logger.log("move thumb", "warn");

	var t = this.thumb;
	var self = this;

    if (!t.available) {
        this.logger.log("thumb is not available yet, aborting move");
        return;
    }

	this.logger.log("move thumb, x: "  + x + ", y: " + y);

    // this.verifyOffset();

	t.setDelta(this.thumbCenterPoint.x, this.thumbCenterPoint.y);

	var _p = t.getTargetCoord(x, y);
    var p = [_p.x, _p.y];


	if (this.animate && YAHOO.widget.Slider.ANIM_AVAIL && t._graduated && !skipAnim) {
		this.logger.log("graduated");
		// this.thumb._animating = true;
		this.lock();
		
		setTimeout( function() { self.moveOneTick(p); }, this.tickPause );

	} else if (this.animate && YAHOO.widget.Slider.ANIM_AVAIL && !skipAnim) {
		this.logger.log("animating to " + p);

		// this.thumb._animating = true;
		this.lock();

		var oAnim = new YAHOO.util.Motion( 
                t.id, { points: { to: p } }, 0.4, YAHOO.util.Easing.easeOut );

		oAnim.onComplete.subscribe( function() { self.endMove(); } );
		oAnim.animate();
	} else {
		t.setDragElPos(x, y);
		// this.fireEvents();
		this.endMove();
	}
};

/**
 * Move the slider one tick mark towards its final coordinate.  Used
 * for the animation when tick marks are defined
 *
 * @param {int[]} the destination coordinate
 * @private
 */
YAHOO.widget.Slider.prototype.moveOneTick = function(finalCoord) {

	var t = this.thumb;
	var curCoord = YAHOO.util.Dom.getXY(t.getEl());
	var tmp;

    // var thresh = Math.min(t.tickSize + (Math.floor(t.tickSize/2)), 10);
    // var thresh = 10;
    // var thresh = t.tickSize + (Math.floor(t.tickSize/2));

	var nextCoord = null;

	if (t._isRegion) {
        nextCoord = this._getNextX(curCoord, finalCoord);
		var tmpX = (nextCoord) ? nextCoord[0] : curCoord[0];
        nextCoord = this._getNextY([tmpX, curCoord[1]], finalCoord);

	} else if (t._isHoriz) {
        nextCoord = this._getNextX(curCoord, finalCoord);
	} else {
        nextCoord = this._getNextY(curCoord, finalCoord);
	}

	this.logger.log("moveOneTick: " + 
			" finalCoord: " + finalCoord +
			" curCoord: " + curCoord +
			" nextCoord: " + nextCoord);

	if (nextCoord) {

		// move to the next coord
		// YAHOO.util.Dom.setXY(t.getEl(), nextCoord);

        // var el = t.getEl();
        // YAHOO.util.Dom.setStyle(el, "left", (nextCoord[0] + this.thumb.deltaSetXY[0]) + "px");
        // YAHOO.util.Dom.setStyle(el, "top",  (nextCoord[1] + this.thumb.deltaSetXY[1]) + "px");

        this.thumb.alignElWithMouse(t.getEl(), nextCoord[0], nextCoord[1]);
		
		// check if we are in the final position, if not make a recursive call
		if (!(nextCoord[0] == finalCoord[0] && nextCoord[1] == finalCoord[1])) {
			var self = this;
			setTimeout(function() { self.moveOneTick(finalCoord); }, 
					this.tickPause);
		} else {
            this.endMove();
		}
	} else {
        this.endMove();
	}

	//this.tickPause = Math.round(this.tickPause/2);
};

/**
 * Returns the next X tick value based on the current coord and the target coord.
 * @private/
 */
YAHOO.widget.Slider.prototype._getNextX = function(curCoord, finalCoord) {
    this.logger.log("getNextX: " + curCoord + ", " + finalCoord);
    var t = this.thumb;
    var thresh;
    var tmp = [];
    var nextCoord = null;
    if (curCoord[0] > finalCoord[0]) {
        thresh = t.tickSize - this.thumbCenterPoint.x;
        tmp = t.getTargetCoord( curCoord[0] - thresh, curCoord[1] );
        nextCoord = [tmp.x, tmp.y];
    } else if (curCoord[0] < finalCoord[0]) {
        thresh = t.tickSize + this.thumbCenterPoint.x;
        tmp = t.getTargetCoord( curCoord[0] + thresh, curCoord[1] );
        nextCoord = [tmp.x, tmp.y];
    } else {
        // equal, do nothing
    }

    return nextCoord;
};

/**
 * Returns the next Y tick value based on the current coord and the target coord.
 * @private/
 */
YAHOO.widget.Slider.prototype._getNextY = function(curCoord, finalCoord) {
    var t = this.thumb;
    // var thresh = t.tickSize;
    // var thresh = t.tickSize + this.thumbCenterPoint.y;
    var thresh;
    var tmp = [];
    var nextCoord = null;

    if (curCoord[1] > finalCoord[1]) {
        thresh = t.tickSize - this.thumbCenterPoint.y;
        tmp = t.getTargetCoord( curCoord[0], curCoord[1] - thresh );
        nextCoord = [tmp.x, tmp.y];
    } else if (curCoord[1] < finalCoord[1]) {
        thresh = t.tickSize + this.thumbCenterPoint.y;
        tmp = t.getTargetCoord( curCoord[0], curCoord[1] + thresh );
        nextCoord = [tmp.x, tmp.y];
    } else {
        // equal, do nothing
    }

    return nextCoord;
};

/**
 * Resets the constraints before moving the thumb.
 * @private
 */
YAHOO.widget.Slider.prototype.b4MouseDown = function(e) {
    this.thumb.autoOffset();
    this.thumb.resetConstraints();
};


/**
 * Handles the mousedown event for the slider background
 *
 * @private
 */
YAHOO.widget.Slider.prototype.onMouseDown = function(e) {
    // this.resetConstraints(true);
    // this.thumb.resetConstraints(true);

	if (! this.isLocked() && this.backgroundEnabled) {
		var x = YAHOO.util.Event.getPageX(e);
		var y = YAHOO.util.Event.getPageY(e);
		this.logger.log("bg mousedown: " + x + "," + y);

		this.focus();
		this.moveThumb(x, y);
	}
	
};

/**
 * Handles the onDrag event for the slider background
 *
 * @private
 */
YAHOO.widget.Slider.prototype.onDrag = function(e) {
	if (! this.isLocked()) {
		var x = YAHOO.util.Event.getPageX(e);
		var y = YAHOO.util.Event.getPageY(e);
		this.moveThumb(x, y, true);
	}
};

/**
 * Fired when the slider movement ends
 *
 * @private
 */
YAHOO.widget.Slider.prototype.endMove = function () {
	// this._animating = false;
	this.unlock();
	this.moveComplete = true;
	this.fireEvents();
	
};

/**
 * Fires the change event if the value has been changed.  Ignored if we are in
 * the middle of an animation as the event will fire when the animation is
 * complete
 *
 * @private
 */
YAHOO.widget.Slider.prototype.fireEvents = function () {

	var t = this.thumb;
	// this.logger.log("FireEvents: " + t._isRegion);

	t.cachePosition();

	if (! this.isLocked()) {
		if (t._isRegion) {
			this.logger.log("region");
			var newX = t.getXValue();
			var newY = t.getYValue();

			if (newX != this.previousX || newY != this.previousY) {
				// this.logger.log("Firing onchange");
				this.onChange( newX, newY );
			}

			this.previousX = newX;
			this.previousY = newY;

		} else {
			var newVal = t.getValue();
			if (newVal != this.previousVal) {
				this.logger.log("Firing onchange: " + newVal);
				this.onChange( newVal );
			}
			this.previousVal = newVal;
		}

		if (this.moveComplete) {
			this.onSlideEnd();
			this.moveComplete = false;
		}

	}
};

/**
 * toString
 * @return {string} string representation of the instance
 */
YAHOO.widget.Slider.prototype.toString = function () { 
    return ("Slider (" + this.type +") " + this.id);
};

/**
 * A drag and drop implementation to be used as the thumb of a slider.
 *
 * @extends YAHOO.util.DD
 * @constructor
 * @param {String} id the id of the slider html element
 * @param {String} sGroup the group of related DragDrop items
 * @param {int} iLeft the number of pixels the element can move left
 * @param {int} iRight the number of pixels the element can move right
 * @param {int} iUp the number of pixels the element can move up
 * @param {int} iDown the number of pixels the element can move down
 * @param {int} iTickSize optional parameter for specifying that the element 
 * should move a certain number pixels at a time.
 */
YAHOO.widget.SliderThumb = function(id, sGroup, iLeft, iRight, iUp, iDown, iTickSize) {

	if (id) {
		this.init(id, sGroup);

        /**
         * The id of the thumbs parent HTML element (the slider background element).
         * @type string
         */
        this.parentElId = sGroup;
	}

    this.logger = new YAHOO.widget.LogWriter(this.toString());

	/**
	 * Overrides the isTarget property in YAHOO.util.DragDrop
	 * @private
	 */
	this.isTarget = false;

    /**
     * The tick size for this slider
     * @type int
     */
	this.tickSize = iTickSize;

    /**
     * Informs the drag and drop util that the offsets should remain when
     * resetting the constraints.  This preserves the slider value when
     * the constraints are reset
     * @type boolean
     */
    this.maintainOffset = true;

	this.initSlider(iLeft, iRight, iUp, iDown, iTickSize);

    this.scroll = false;

};

// YAHOO.widget.SliderThumb.prototype = new YAHOO.util.DD();
YAHOO.extend(YAHOO.widget.SliderThumb, YAHOO.util.DD);

/**
 * Returns the difference between the location of the thumb and its parent.
 * @param {Array} Optionally accepts the position of the parent
 * @type int[]
 */
YAHOO.widget.SliderThumb.prototype.getOffsetFromParent = function(parentPos) {
    var myPos = YAHOO.util.Dom.getXY(this.getEl());
    var ppos  = parentPos || YAHOO.util.Dom.getXY(this.parentElId);

    return [ (myPos[0] - ppos[0]), (myPos[1] - ppos[1]) ];
};

/**
 * The (X and Y) difference between the thumb location and its parent 
 * (the slider background) when the control is instantiated.  
 * @type int[]
 */
YAHOO.widget.SliderThumb.prototype.startOffset = null;

/**
 * Flag used to figure out if this is a horizontal or vertical slider
 *
 * @type boolean
 * @private
 */
YAHOO.widget.SliderThumb.prototype._isHoriz = false;

/**
 * Cache the last value so we can check for change
 *
 * @type int
 * @private
 */
YAHOO.widget.SliderThumb.prototype._prevVal = 0;

/**
 * initial element X
 *
 * @type int
 * @private
 */
// YAHOO.widget.SliderThumb.prototype._initX = 0;

/**
 * initial element Y
 *
 * @type int
 * @private
 */
// YAHOO.widget.SliderThumb.prototype._initY = 0;

/**
 * The slider is _graduated if there is a tick interval defined
 *
 * @type boolean
 * @private
 */
YAHOO.widget.SliderThumb.prototype._graduated = false;

/**
 * Set up the slider, must be called in the constructor of all subclasses
 *
 * @param {int} iLeft the number of pixels the element can move left
 * @param {int} iRight the number of pixels the element can move right
 * @param {int} iUp the number of pixels the element can move up
 * @param {int} iDown the number of pixels the element can move down
 * @param {int} iTickSize the width of the tick interval.
 */
YAHOO.widget.SliderThumb.prototype.initSlider = function (iLeft, iRight, iUp, iDown, 
		iTickSize) {

	this.setXConstraint(iLeft, iRight, iTickSize);
	this.setYConstraint(iUp, iDown, iTickSize);

	if (iTickSize && iTickSize > 1) {
		this._graduated = true;
	}

	this._isHoriz = (iLeft > 0 || iRight > 0); 
	this._isVert   = (iUp > 0 ||  iDown > 0);
	this._isRegion = (this._isHoriz && this._isVert); 

};

/**
 * Clear's the slider's ticks
 */
YAHOO.widget.SliderThumb.prototype.clearTicks = function () {
    YAHOO.widget.SliderThumb.superclass.clearTicks.call(this);
    this._graduated = false;
};

/**
 * Gets the current offset from the element's start position in
 * pixels.
 *
 * @return {int} the number of pixels (positive or negative) the
 * slider has moved from the start position.
 */
YAHOO.widget.SliderThumb.prototype.getValue = function () {
    if (!this.available) { return 0; }
    var val = (this._isHoriz) ? this.getXValue() : this.getYValue();
    this.logger.log("getVal: " + val);
    return val;
};

/**
 * Gets the current X offset from the element's start position in
 * pixels.
 *
 * @return {int} the number of pixels (positive or negative) the
 * slider has moved horizontally from the start position.
 */
YAHOO.widget.SliderThumb.prototype.getXValue = function () {
    if (!this.available) { return 0; }
    var newOffset = this.getOffsetFromParent();
	return (newOffset[0] - this.startOffset[0]);
};

/**
 * Gets the current Y offset from the element's start position in
 * pixels.
 *
 * @return {int} the number of pixels (positive or negative) the
 * slider has moved vertically from the start position.
 */
YAHOO.widget.SliderThumb.prototype.getYValue = function () {
    if (!this.available) { return 0; }
    var newOffset = this.getOffsetFromParent();
	return (newOffset[1] - this.startOffset[1]);
};

/**
 * toString
 * @return {string} string representation of the instance
 */
YAHOO.widget.SliderThumb.prototype.toString = function () { 
    return "SliderThumb " + this.id;
};

/**
 * The onchange event for the handle/thumb is delegated to the YAHOO.widget.Slider
 * instance it belongs to.
 *
 * @private
 */
YAHOO.widget.SliderThumb.prototype.onChange = function (x, y) { };

if ("undefined" == typeof YAHOO.util.Anim) {
	YAHOO.widget.Slider.ANIM_AVAIL = false;
}

