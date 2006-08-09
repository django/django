/*
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
Version 0.11.0
*/

/**
* @class
* <p>YAHOO.widget.DateMath is used for simple date manipulation. The class is a static utility
* used for adding, subtracting, and comparing dates.</p>
*/
YAHOO.widget.DateMath = new function() {

	/**
	* Constant field representing Day
	* @alias YAHOO.widget.DateMath.DAY
	* @type String
	*/
	this.DAY = "D";

	/**
	* Constant field representing Week
	* @alias YAHOO.widget.DateMath.WEEK
	* @type String
	*/
	this.WEEK = "W";

	/**
	* Constant field representing Year
	* @alias YAHOO.widget.DateMath.YEAR
	* @type String
	*/
	this.YEAR = "Y";

	/**
	* Constant field representing Month
	* @alias YAHOO.widget.DateMath.MONTH
	* @type String
	*/
	this.MONTH = "M";

	/**
	* Constant field representing one day, in milliseconds
	* @alias YAHOO.widget.DateMath.ONE_DAY_MS
	* @type Integer
	*/
	this.ONE_DAY_MS = 1000*60*60*24;

	/**
	* Adds the specified amount of time to the this instance.
	* @alias YAHOO.widget.DateMath.add
	* @param {Date} date	The JavaScript Date object to perform addition on
	* @param {string} field	The this field constant to be used for performing addition.
	* @param {Integer} amount	The number of units (measured in the field constant) to add to the date.
	*/
	this.add = function(date, field, amount) {
		var d = new Date(date.getTime());
		switch (field) {
			case this.MONTH:
				var newMonth = date.getMonth() + amount;
				var years = 0;


				if (newMonth < 0) {
					while (newMonth < 0) {
						newMonth += 12;
						years -= 1;
					}
				} else if (newMonth > 11) {
					while (newMonth > 11) {
						newMonth -= 12;
						years += 1;
					}
				}
				
				d.setMonth(newMonth);
				d.setFullYear(date.getFullYear() + years);
				break;
			case this.DAY:
				d.setDate(date.getDate() + amount);
				break;
			case this.YEAR:
				d.setFullYear(date.getFullYear() + amount);
				break;
			case this.WEEK:
				d.setDate(date.getDate() + (amount * 7));
				break;
		}
		return d;
	};

	/**
	* Subtracts the specified amount of time from the this instance.
	* @alias YAHOO.widget.DateMath.subtract
	* @param {Date} date	The JavaScript Date object to perform subtraction on
	* @param {Integer} field	The this field constant to be used for performing subtraction.
	* @param {Integer} amount	The number of units (measured in the field constant) to subtract from the date.
	*/
	this.subtract = function(date, field, amount) {
		return this.add(date, field, (amount*-1));
	};

	/**
	* Determines whether a given date is before another date on the calendar.
	* @alias YAHOO.widget.DateMath.before
	* @param {Date} date		The Date object to compare with the compare argument
	* @param {Date} compareTo	The Date object to use for the comparison
	* @return {Boolean} true if the date occurs before the compared date; false if not.
	*/
	this.before = function(date, compareTo) {
		var ms = compareTo.getTime();
		if (date.getTime() < ms) {
			return true;
		} else {
			return false;
		}
	};

	/**
	* Determines whether a given date is after another date on the calendar.
	* @alias YAHOO.widget.DateMath.after
	* @param {Date} date		The Date object to compare with the compare argument
	* @param {Date} compareTo	The Date object to use for the comparison
	* @return {Boolean} true if the date occurs after the compared date; false if not.
	*/
	this.after = function(date, compareTo) {
		var ms = compareTo.getTime();
		if (date.getTime() > ms) {
			return true;
		} else {
			return false;
		}
	};

	/**
	* Determines whether a given date is between two other dates on the calendar.
	* @alias YAHOO.widget.DateMath.between
	* @param {Date} date		The date to check for
	* @param {Date} dateBegin	The start of the range
	* @param {Date} dateEnd		The end of the range
	* @return {Boolean} true if the date occurs between the compared dates; false if not.
	*/
	this.between = function(date, dateBegin, dateEnd) {
		if (this.after(date, dateBegin) && this.before(date, dateEnd)) {
			return true;
		} else {
			return false;
		}
	};
	
	/**
	* Retrieves a JavaScript Date object representing January 1 of any given year.
	* @alias YAHOO.widget.DateMath.getJan1
	* @param {Integer} calendarYear		The calendar year for which to retrieve January 1
	* @return {Date}	January 1 of the calendar year specified.
	*/
	this.getJan1 = function(calendarYear) {
		return new Date(calendarYear,0,1); 
	};

	/**
	* Calculates the number of days the specified date is from January 1 of the specified calendar year.
	* Passing January 1 to this function would return an offset value of zero.
	* @alias YAHOO.widget.DateMath.getDayOffset
	* @param {Date}	date	The JavaScript date for which to find the offset
	* @param {Integer} calendarYear	The calendar year to use for determining the offset
	* @return {Integer}	The number of days since January 1 of the given year
	*/
	this.getDayOffset = function(date, calendarYear) {
		var beginYear = this.getJan1(calendarYear); // Find the start of the year. This will be in week 1.
		
		// Find the number of days the passed in date is away from the calendar year start
		var dayOffset = Math.ceil((date.getTime()-beginYear.getTime()) / this.ONE_DAY_MS);
		return dayOffset;
	};

	/**
	* Calculates the week number for the given date. This function assumes that week 1 is the
	* week in which January 1 appears, regardless of whether the week consists of a full 7 days.
	* The calendar year can be specified to help find what a the week number would be for a given
	* date if the date overlaps years. For instance, a week may be considered week 1 of 2005, or
	* week 53 of 2004. Specifying the optional calendarYear allows one to make this distinction
	* easily.
	* @alias YAHOO.widget.DateMath.getWeekNumber
	* @param {Date}	date	The JavaScript date for which to find the week number
	* @param {Integer} calendarYear	OPTIONAL - The calendar year to use for determining the week number. Default is
	*											the calendar year of parameter "date".
	* @param {Integer} weekStartsOn	OPTIONAL - The integer (0-6) representing which day a week begins on. Default is 0 (for Sunday).
	* @return {Integer}	The week number of the given date.
	*/
	this.getWeekNumber = function(date, calendarYear, weekStartsOn) {
		date.setHours(12,0,0,0);

		if (! weekStartsOn) {
			weekStartsOn = 0;
		}
		if (! calendarYear) {
			calendarYear = date.getFullYear();
		}
		
		var weekNum = -1;
		
		var jan1 = this.getJan1(calendarYear);

		var jan1Offset = jan1.getDay() - weekStartsOn;
		var jan1DayOfWeek = (jan1Offset >= 0 ? jan1Offset : (7 + jan1Offset));

		var endOfWeek1 = this.add(jan1, this.DAY, (6 - jan1DayOfWeek));
		endOfWeek1.setHours(23,59,59,999);

		var month = date.getMonth();
		var day = date.getDate();
		var year = date.getFullYear();
		
		var dayOffset = this.getDayOffset(date, calendarYear); // Days since Jan 1, Calendar Year
			
		if (dayOffset < 0 || this.before(date, endOfWeek1)) {
			weekNum = 1;
		} else {
			weekNum = 2;
			var weekBegin = new Date(endOfWeek1.getTime() + 1);
			var weekEnd = this.add(weekBegin, this.WEEK, 1);

			while (! this.between(date, weekBegin, weekEnd)) {
				weekBegin = this.add(weekBegin, this.WEEK, 1);
				weekEnd = this.add(weekEnd, this.WEEK, 1);
				weekNum += 1;
			}
		}
		
		return weekNum;
	};

	/**
	* Determines if a given week overlaps two different years.
	* @alias YAHOO.widget.DateMath.isYearOverlapWeek
	* @param {Date}	weekBeginDate	The JavaScript Date representing the first day of the week.
	* @return {Boolean}	true if the date overlaps two different years.
	*/
	this.isYearOverlapWeek = function(weekBeginDate) {
		var overlaps = false;
		var nextWeek = this.add(weekBeginDate, this.DAY, 6);
		if (nextWeek.getFullYear() != weekBeginDate.getFullYear()) {
			overlaps = true;
		}
		return overlaps;
	};

	/**
	* Determines if a given week overlaps two different months.
	* @alias YAHOO.widget.DateMath.isMonthOverlapWeek
	* @param {Date}	weekBeginDate	The JavaScript Date representing the first day of the week.
	* @return {Boolean}	true if the date overlaps two different months.
	*/
	this.isMonthOverlapWeek = function(weekBeginDate) {
		var overlaps = false;
		var nextWeek = this.add(weekBeginDate, this.DAY, 6);
		if (nextWeek.getMonth() != weekBeginDate.getMonth()) {
			overlaps = true;
		}
		return overlaps;
	};

	/**
	* Gets the first day of a month containing a given date.
	* @alias YAHOO.widget.DateMath.findMonthStart
	* @param {Date}	date	The JavaScript Date used to calculate the month start
	* @return {Date}		The JavaScript Date representing the first day of the month
	*/
	this.findMonthStart = function(date) {
		var start = new Date(date.getFullYear(), date.getMonth(), 1);
		return start;
	};

	/**
	* Gets the last day of a month containing a given date.
	* @alias YAHOO.widget.DateMath.findMonthEnd
	* @param {Date}	date	The JavaScript Date used to calculate the month end
	* @return {Date}		The JavaScript Date representing the last day of the month
	*/
	this.findMonthEnd = function(date) {
		var start = this.findMonthStart(date);
		var nextMonth = this.add(start, this.MONTH, 1);
		var end = this.subtract(nextMonth, this.DAY, 1);
		return end;
	};

	/**
	* Clears the time fields from a given date, effectively setting the time to midnight.
	* @alias YAHOO.widget.DateMath.clearTime
	* @param {Date}	date	The JavaScript Date for which the time fields will be cleared
	* @return {Date}		The JavaScript Date cleared of all time fields
	*/
	this.clearTime = function(date) {
		date.setHours(0,0,0,0);
		return date;
	};
}
/**
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt 
**/

/**
* @class
* <p>Calendar_Core is the base class for the Calendar widget. In its most basic
* implementation, it has the ability to render a calendar widget on the page
* that can be manipulated to select a single date, move back and forth between
* months and years.</p>
* <p>To construct the placeholder for the calendar widget, the code is as
* follows:
*	<xmp>
*		<div id="cal1Container"></div>
*	</xmp>
* Note that the table can be replaced with any kind of element.
* </p>
* @constructor
* @param {String}	id			The id of the table element that will represent the calendar widget
* @param {String}	containerId	The id of the container element that will contain the calendar table
* @param {String}	monthyear	The month/year string used to set the current calendar page
* @param {String}	selected	A string of date values formatted using the date parser. The built-in
								default date format is MM/DD/YYYY. Ranges are defined using
								MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
								Any combination of these can be combined by delimiting the string with
								commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.Calendar_Core = function(id, containerId, monthyear, selected) {
	if (arguments.length > 0) {	
		if (! id) {
			YAHOO.log("No ID specified", "error");
		}
		if (! containerId) {
			YAHOO.log("No container ID specified", "error");
		}
		this.init(id, containerId, monthyear, selected);
	}
}

/**
* The path to be used for images loaded for the Calendar
* @type String
*/
YAHOO.widget.Calendar_Core.IMG_ROOT = (window.location.href.toLowerCase().indexOf("https") == 0 ? "https://a248.e.akamai.net/sec.yimg.com/i/" : "http://us.i1.yimg.com/us.yimg.com/i/");

/**
* Type constant used for renderers to represent an individual date (M/D/Y)
* @final
* @type String
*/
YAHOO.widget.Calendar_Core.DATE = "D";

/**
* Type constant used for renderers to represent an individual date across any year (M/D)
* @final
* @type String
*/
YAHOO.widget.Calendar_Core.MONTH_DAY = "MD";

/**
* Type constant used for renderers to represent a weekday
* @final
* @type String
*/
YAHOO.widget.Calendar_Core.WEEKDAY = "WD";

/**
* Type constant used for renderers to represent a range of individual dates (M/D/Y-M/D/Y)
* @final
* @type String
*/
YAHOO.widget.Calendar_Core.RANGE = "R";

/**
* Type constant used for renderers to represent a month across any year
* @final
* @type String
*/
YAHOO.widget.Calendar_Core.MONTH = "M";

/**
* Constant that represents the total number of date cells that are displayed in a given month
* including 
* @final
* @type Integer
*/
YAHOO.widget.Calendar_Core.DISPLAY_DAYS = 42;

/**
* Constant used for halting the execution of the remainder of the render stack
* @final
* @type String
*/
YAHOO.widget.Calendar_Core.STOP_RENDER = "S";

YAHOO.widget.Calendar_Core.prototype = {

	/**
	* The configuration object used to set up the calendars various locale and style options.
	* @type Object
	*/
	Config : null,

	/**
	* The parent CalendarGroup, only to be set explicitly by the parent group
	* @type CalendarGroup
	*/	
	parent : null,

	/**
	* The index of this item in the parent group
	* @type Integer
	*/
	index : -1,

	/**
	* The collection of calendar table cells
	* @type HTMLTableCellElement[]
	*/
	cells : null,

	/**
	* The collection of calendar week header cells
	* @type HTMLTableCellElement[]
	*/
	weekHeaderCells : null,

	/**
	* The collection of calendar week footer cells
	* @type HTMLTableCellElement[]
	*/
	weekFooterCells : null,
	
	/**
	* The collection of calendar cell dates that is parallel to the cells collection. The array contains dates field arrays in the format of [YYYY, M, D].
	* @type Array[](Integer[])
	*/
	cellDates : null,

	/**
	* The id that uniquely identifies this calendar. This id should match the id of the placeholder element on the page.
	* @type String
	*/
	id : null,

	/**
	* The DOM element reference that points to this calendar's container element. The calendar will be inserted into this element when the shell is rendered.
	* @type HTMLElement
	*/
	oDomContainer : null,

	/**
	* A Date object representing today's date.
	* @type Date
	*/
	today : null,

	/**
	* The list of render functions, along with required parameters, used to render cells. 
	* @type Array[]
	*/
	renderStack : null,

	/**
	* A copy of the initial render functions created before rendering.
	* @type Array
	* @private
	*/
	_renderStack : null,

	/**
	* A Date object representing the month/year that the calendar is currently set to
	* @type Date
	*/
	pageDate : null,

	/**
	* A Date object representing the month/year that the calendar is initially set to
	* @type Date
	* @private
	*/
	_pageDate : null,
	
	/**
	* A Date object representing the minimum selectable date
	* @type Date
	*/
	minDate : null,
	
	/**
	* A Date object representing the maximum selectable date
	* @type Date
	*/
	maxDate : null,
	
	/**
	* The list of currently selected dates. The data format for this local collection is 
	* an array of date field arrays, e.g:
	* [
	*	[2004,5,25],
	*	[2004,5,26]
	* ]
	* @type Array[](Integer[])
	*/
	selectedDates : null,

	/**
	* The private list of initially selected dates.
	* @type Array
	* @private
	*/
	_selectedDates : null,

	/**
	* A boolean indicating whether the shell of the calendar has already been rendered to the page
	* @type Boolean
	*/	
	shellRendered : false,

	/**
	* The HTML table element that represents this calendar
	* @type HTMLTableElement
	*/	
	table : null,

	/**
	* The HTML cell element that represents the main header cell TH used in the calendar table
	* @type HTMLTableCellElement
	*/	
	headerCell : null
};



/**
* Initializes the calendar widget. This method must be called by all subclass constructors.
* @param {String}	id			The id of the table element that will represent the calendar widget
* @param {String}	containerId	The id of the container element that will contain the calendar table
* @param {String}	monthyear	The month/year string used to set the current calendar page
* @param {String}	selected	A string of date values formatted using the date parser. The built-in
								default date format is MM/DD/YYYY. Ranges are defined using
								MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
								Any combination of these can be combined by delimiting the string with
								commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.Calendar_Core.prototype.init = function(id, containerId, monthyear, selected) {

	this.logger = new YAHOO.widget.LogWriter("Calendar_Core " + id);	

	this.setupConfig();

	this.id = id;

	this.cellDates = new Array();
	
	this.cells = new Array();
	
	this.renderStack = new Array();
	this._renderStack = new Array();

	this.oDomContainer = document.getElementById(containerId);
	
	if (! this.oDomContainer) {
		this.logger.log("No valid container present.", "error");
	}

	this.today = new Date();
	YAHOO.widget.DateMath.clearTime(this.today);

	var month;
	var year;

	if (monthyear) {
		var aMonthYear = monthyear.split(this.Locale.DATE_FIELD_DELIMITER);
		month = parseInt(aMonthYear[this.Locale.MY_MONTH_POSITION-1]);
		year = parseInt(aMonthYear[this.Locale.MY_YEAR_POSITION-1]);
	} else {
		month = this.today.getMonth()+1;
		year = this.today.getFullYear();
	}

	this.logger.log("Initialized with month/year of " + month + "/" + year, "info");

	this.pageDate = new Date(year, month-1, 1);
	this._pageDate = new Date(this.pageDate.getTime());

	if (selected) {
		this.selectedDates = this._parseDates(selected);
		this._selectedDates = this.selectedDates.concat();
	} else {
		this.selectedDates = new Array();
		this._selectedDates = new Array();
	}

	this.wireDefaultEvents();
	this.wireCustomEvents();
};


/**
* Wires the local DOM events for the Calendar, including cell selection, hover, and
* default navigation that is used for moving back and forth between calendar pages.
*/
YAHOO.widget.Calendar_Core.prototype.wireDefaultEvents = function() {
	
	/**
	* The default event function that is attached to a date link within a calendar cell
	* when the calendar is rendered. 
	* @param	e		The event
	* @param	cal		A reference to the calendar passed by the Event utility
	*/
	this.doSelectCell = function(e, cal) {		
		var cell = this;
		var index = cell.index;

		cal.logger.log("Selecting cell " + index + " via click", "info");

		var d = cal.cellDates[index];
		var date = new Date(d[0],d[1]-1,d[2]);
		
		if (! cal.isDateOOM(date) && ! YAHOO.util.Dom.hasClass(cell, cal.Style.CSS_CELL_RESTRICTED) && ! YAHOO.util.Dom.hasClass(cell, cal.Style.CSS_CELL_OOB)) {
			if (cal.Options.MULTI_SELECT) {
				var link = cell.getElementsByTagName("A")[0];
				link.blur();
				
				var cellDate = cal.cellDates[index];
				var cellDateIndex = cal._indexOfSelectedFieldArray(cellDate);
				
				if (cellDateIndex > -1) {	
					cal.deselectCell(index);
				} else {
					cal.selectCell(index);
				}	
				
			} else {
				var link = cell.getElementsByTagName("A")[0];
				link.blur()
				cal.selectCell(index);
			}
		}
	}

	/**
	* The event that is executed when the user hovers over a cell
	* @param	e		The event
	* @param	cal		A reference to the calendar passed by the Event utility
	* @private
	*/
	this.doCellMouseOver = function(e, cal) {
		var cell = this;
		var index = cell.index;
		var d = cal.cellDates[index];
		var date = new Date(d[0],d[1]-1,d[2]);

		if (! cal.isDateOOM(date) && ! YAHOO.util.Dom.hasClass(cell, cal.Style.CSS_CELL_RESTRICTED) && ! YAHOO.util.Dom.hasClass(cell, cal.Style.CSS_CELL_OOB)) {
			YAHOO.util.Dom.addClass(cell, cal.Style.CSS_CELL_HOVER);
		}
	}

	/**
	* The event that is executed when the user moves the mouse out of a cell
	* @param	e		The event
	* @param	cal		A reference to the calendar passed by the Event utility
	* @private
	*/
	this.doCellMouseOut = function(e, cal) {
		YAHOO.util.Dom.removeClass(this, cal.Style.CSS_CELL_HOVER);
	}
	
	/**
	* A wrapper event that executes the nextMonth method through a DOM event
	* @param	e		The event
	* @param	cal		A reference to the calendar passed by the Event utility
	* @private
	*/	
	this.doNextMonth = function(e, cal) {
		cal.nextMonth();
	}

	/**
	* A wrapper event that executes the previousMonth method through a DOM event
	* @param	e		The event
	* @param	cal		A reference to the calendar passed by the Event utility
	* @private
	*/		
	this.doPreviousMonth = function(e, cal) {
		cal.previousMonth();
	}
}

/**
* This function can be extended by subclasses to attach additional DOM events to
* the calendar. By default, this method is unimplemented.
*/
YAHOO.widget.Calendar_Core.prototype.wireCustomEvents = function() { }

/**
This method is called to initialize the widget configuration variables, including
style, localization, and other display and behavioral options.
<p>Config: Container for the CSS style configuration variables.</p>
<p><strong>Config.Style</strong> - Defines the CSS classes used for different calendar elements</p>
<blockquote>
	<div><em>CSS_CALENDAR</em> : Container table</div>
	<div><em>CSS_HEADER</em> : </div>
	<div><em>CSS_HEADER_TEXT</em> : Calendar header</div>
	<div><em>CSS_FOOTER</em> : Calendar footer</div>
	<div><em>CSS_CELL</em> : Calendar day cell</div>
	<div><em>CSS_CELL_OOM</em> : Calendar OOM (out of month) cell</div>
	<div><em>CSS_CELL_SELECTED</em> : Calendar selected cell</div>
	<div><em>CSS_CELL_RESTRICTED</em> : Calendar restricted cell</div>
	<div><em>CSS_CELL_TODAY</em> : Calendar cell for today's date</div>
	<div><em>CSS_ROW_HEADER</em> : The cell preceding a row (used for week number by default)</div>
	<div><em>CSS_ROW_FOOTER</em> : The cell following a row (not implemented by default)</div>
	<div><em>CSS_WEEKDAY_CELL</em> : The cells used for labeling weekdays</div>
	<div><em>CSS_WEEKDAY_ROW</em> : The row containing the weekday label cells</div>
	<div><em>CSS_CONTAINER</em> : The border style used for the default UED rendering</div>
	<div><em>CSS_2UPWRAPPER</em> : Special container class used to properly adjust the sizing and float</div>
	<div><em>CSS_NAV_LEFT</em> : Left navigation arrow</div>
	<div><em>CSS_NAV_RIGHT</em> : Right navigation arrow</div>
	<div><em>CSS_CELL_TOP</em> : Outlying cell along the top row</div>
	<div><em>CSS_CELL_LEFT</em> : Outlying cell along the left row</div>
	<div><em>CSS_CELL_RIGHT</em> : Outlying cell along the right row</div>
	<div><em>CSS_CELL_BOTTOM</em> : Outlying cell along the bottom row</div>
	<div><em>CSS_CELL_HOVER</em> : Cell hover style</div>
	<div><em>CSS_CELL_HIGHLIGHT1</em> : Highlight color 1 for styling cells</div>
	<div><em>CSS_CELL_HIGHLIGHT2</em> : Highlight color 2 for styling cells</div>
	<div><em>CSS_CELL_HIGHLIGHT3</em> : Highlight color 3 for styling cells</div>
	<div><em>CSS_CELL_HIGHLIGHT4</em> : Highlight color 4 for styling cells</div>

</blockquote>
<p><strong>Config.Locale</strong> - Defines the locale string arrays used for localization</p>
<blockquote>
	<div><em>MONTHS_SHORT</em> : Array of 12 months in short format ("Jan", "Feb", etc.)</div>
	<div><em>MONTHS_LONG</em> : Array of 12 months in short format ("Jan", "Feb", etc.)</div>
	<div><em>WEEKDAYS_1CHAR</em> : Array of 7 days in 1-character format ("S", "M", etc.)</div>
	<div><em>WEEKDAYS_SHORT</em> : Array of 7 days in short format ("Su", "Mo", etc.)</div>
	<div><em>WEEKDAYS_MEDIUM</em> : Array of 7 days in medium format ("Sun", "Mon", etc.)</div>
	<div><em>WEEKDAYS_LONG</em> : Array of 7 days in long format ("Sunday", "Monday", etc.)</div>
	<div><em>DATE_DELIMITER</em> : The value used to delimit series of multiple dates (Default: ",")</div>
	<div><em>DATE_FIELD_DELIMITER</em> : The value used to delimit date fields (Default: "/")</div>
	<div><em>DATE_RANGE_DELIMITER</em> : The value used to delimit date fields (Default: "-")</div>
	<div><em>MY_MONTH_POSITION</em> : The value used to determine the position of the month in a month/year combo (e.g. 12/2005) (Default: 1)</div>
	<div><em>MY_YEAR_POSITION</em> : The value used to determine the position of the year in a month/year combo (e.g. 12/2005) (Default: 2)</div>	
	<div><em>MD_MONTH_POSITION</em> : The value used to determine the position of the month in a month/day combo (e.g. 12/25) (Default: 1)</div>
	<div><em>MD_DAY_POSITION</em> : The value used to determine the position of the day in a month/day combo (e.g. 12/25) (Default: 2)</div>
	<div><em>MDY_MONTH_POSITION</em> : The value used to determine the position of the month in a month/day/year combo (e.g. 12/25/2005) (Default: 1)</div>
	<div><em>MDY_DAY_POSITION</em> : The value used to determine the position of the day in a month/day/year combo (e.g. 12/25/2005) (Default: 2)</div>
	<div><em>MDY_YEAR_POSITION</em> : The value used to determine the position of the year in a month/day/year combo (e.g. 12/25/2005) (Default: 3)</div>
</blockquote>
<p><strong>Config.Options</strong> - Defines other configurable calendar widget options</p>
<blockquote>
	<div><em>SHOW_WEEKDAYS</em> : Boolean, determines whether to display the weekday headers (defaults to true)</div>
	<div><em>LOCALE_MONTHS</em> : Array, points to the desired Config.Locale array (defaults to Config.Locale.MONTHS_LONG)</div>
	<div><em>LOCALE_WEEKDAYS</em> : Array, points to the desired Config.Locale array (defaults to Config.Locale.WEEKDAYS_SHORT)</div>
	<div><em>START_WEEKDAY</em> : Integer, 0-6, representing the day that a week begins on</div>
	<div><em>SHOW_WEEK_HEADER</em> : Boolean, determines whether to display row headers</div>
	<div><em>SHOW_WEEK_FOOTER</em> : Boolean, determines whether to display row footers</div>
	<div><em>HIDE_BLANK_WEEKS</em> : Boolean, determines whether to hide extra weeks that are completely OOM</div>
	<div><em>NAV_ARROW_LEFT</em> : String, the image path used for the left navigation arrow</div>
	<div><em>NAV_ARROW_RIGHT</em> : String, the image path used for the right navigation arrow</div>
</blockquote>
*/
YAHOO.widget.Calendar_Core.prototype.setupConfig = function() {
	/**
	* Container for the CSS style configuration variables.
	*/
	this.Config = new Object();
	
	this.Config.Style = {
		// Style variables
		CSS_ROW_HEADER: "calrowhead",
		CSS_ROW_FOOTER: "calrowfoot",
		CSS_CELL : "calcell",
		CSS_CELL_SELECTED : "selected",
		CSS_CELL_RESTRICTED : "restricted",
		CSS_CELL_TODAY : "today",
		CSS_CELL_OOM : "oom",
		CSS_CELL_OOB : "previous",
		CSS_HEADER : "calheader",
		CSS_HEADER_TEXT : "calhead",
		CSS_WEEKDAY_CELL : "calweekdaycell",
		CSS_WEEKDAY_ROW : "calweekdayrow",
		CSS_FOOTER : "calfoot",
		CSS_CALENDAR : "yui-calendar",
		CSS_CONTAINER : "yui-calcontainer",
		CSS_2UPWRAPPER : "yui-cal2upwrapper", 
		CSS_NAV_LEFT : "calnavleft",
		CSS_NAV_RIGHT : "calnavright",
		CSS_CELL_TOP : "calcelltop",
		CSS_CELL_LEFT : "calcellleft",
		CSS_CELL_RIGHT : "calcellright",
		CSS_CELL_BOTTOM : "calcellbottom",
		CSS_CELL_HOVER : "calcellhover",
		CSS_CELL_HIGHLIGHT1 : "highlight1",
		CSS_CELL_HIGHLIGHT2 : "highlight2",
		CSS_CELL_HIGHLIGHT3 : "highlight3",
		CSS_CELL_HIGHLIGHT4 : "highlight4"
	};

	this.Style = this.Config.Style;

	this.Config.Locale = {
		// Locale definition
		MONTHS_SHORT : ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
		MONTHS_LONG : ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
		WEEKDAYS_1CHAR : ["S", "M", "T", "W", "T", "F", "S"],
		WEEKDAYS_SHORT : ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
		WEEKDAYS_MEDIUM : ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
		WEEKDAYS_LONG : ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
		DATE_DELIMITER : ",",
		DATE_FIELD_DELIMITER : "/",
		DATE_RANGE_DELIMITER : "-",
		MY_MONTH_POSITION : 1,
		MY_YEAR_POSITION : 2,
		MD_MONTH_POSITION : 1,
		MD_DAY_POSITION : 2,
		MDY_MONTH_POSITION : 1,
		MDY_DAY_POSITION : 2,
		MDY_YEAR_POSITION : 3
	};

	this.Locale = this.Config.Locale;

	this.Config.Options = {
		// Configuration variables
		MULTI_SELECT : false,
		SHOW_WEEKDAYS : true,
		START_WEEKDAY : 0,
		SHOW_WEEK_HEADER : false,
		SHOW_WEEK_FOOTER : false,
		HIDE_BLANK_WEEKS : false,
		NAV_ARROW_LEFT : YAHOO.widget.Calendar_Core.IMG_ROOT + "us/tr/callt.gif",
		NAV_ARROW_RIGHT : YAHOO.widget.Calendar_Core.IMG_ROOT + "us/tr/calrt.gif"
	};

	this.Options = this.Config.Options;

	this.customConfig();

	if (! this.Options.LOCALE_MONTHS) {
		this.Options.LOCALE_MONTHS=this.Locale.MONTHS_LONG;
	}
	if (! this.Options.LOCALE_WEEKDAYS) {
		this.Options.LOCALE_WEEKDAYS=this.Locale.WEEKDAYS_SHORT;
	}

	// If true, reconfigure weekday arrays to place Mondays first
	if (this.Options.START_WEEKDAY > 0) {
		for (var w=0;w<this.Options.START_WEEKDAY;++w) {
			this.Locale.WEEKDAYS_SHORT.push(this.Locale.WEEKDAYS_SHORT.shift());
			this.Locale.WEEKDAYS_MEDIUM.push(this.Locale.WEEKDAYS_MEDIUM.shift());
			this.Locale.WEEKDAYS_LONG.push(this.Locale.WEEKDAYS_LONG.shift());		
		}
	}
};

/**
* This method is called when subclasses need to override configuration variables
* or create new ones. Values can be explicitly set as follows:
* <blockquote><code>
*	this.Config.Style.CSS_CELL = "newcalcell";
*	this.Config.Locale.MONTHS_SHORT = ["Jan", "Fv", "Mars", "Avr", "Mai", "Juin", "Juil", "Aot", "Sept", "Oct", "Nov", "Dc"];
* </code></blockquote>
*/
YAHOO.widget.Calendar_Core.prototype.customConfig = function() { };

/**
* Builds the date label that will be displayed in the calendar header or
* footer, depending on configuration.
* @return	The formatted calendar month label
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.buildMonthLabel = function() {
	var text = this.Options.LOCALE_MONTHS[this.pageDate.getMonth()] + " " + this.pageDate.getFullYear();
	return text;
};

/**
* Builds the date digit that will be displayed in calendar cells
* @return	The formatted day label
* @type	String
*/
YAHOO.widget.Calendar_Core.prototype.buildDayLabel = function(workingDate) {
	var day = workingDate.getDate();
	return day;
};



/**
* Builds the calendar table shell that will be filled in with dates and formatting.
* This method calls buildShellHeader, buildShellBody, and buildShellFooter (in that order) 
* to construct the pieces of the calendar table. The construction of the shell should
* only happen one time when the calendar is initialized.
*/
YAHOO.widget.Calendar_Core.prototype.buildShell = function() {
	
	this.table = document.createElement("TABLE");
	this.table.cellSpacing = 0;	
	YAHOO.widget.Calendar_Core.setCssClasses(this.table, [this.Style.CSS_CALENDAR]);

	this.table.id = this.id;
	
	this.buildShellHeader();
	this.buildShellBody();
	this.buildShellFooter();
	
	YAHOO.util.Event.addListener(window, "unload", this._unload, this);
};

/**
* Builds the calendar shell header by inserting a THEAD into the local calendar table.
*/
YAHOO.widget.Calendar_Core.prototype.buildShellHeader = function() {
	var head = document.createElement("THEAD");
	var headRow = document.createElement("TR");

	var headerCell = document.createElement("TH");
	
	var colSpan = 7;
	if (this.Config.Options.SHOW_WEEK_HEADER) {
		this.weekHeaderCells = new Array();
		colSpan += 1;
	}
	if (this.Config.Options.SHOW_WEEK_FOOTER) {
		this.weekFooterCells = new Array();
		colSpan += 1;
	}	
	
	headerCell.colSpan = colSpan;
	
	YAHOO.widget.Calendar_Core.setCssClasses(headerCell,[this.Style.CSS_HEADER_TEXT]);

	this.headerCell = headerCell;

	headRow.appendChild(headerCell);
	head.appendChild(headRow);

	// Append day labels, if needed
	if (this.Options.SHOW_WEEKDAYS) {
		var row = document.createElement("TR");
		var fillerCell;

		YAHOO.widget.Calendar_Core.setCssClasses(row,[this.Style.CSS_WEEKDAY_ROW]);
		
		if (this.Config.Options.SHOW_WEEK_HEADER) {
			fillerCell = document.createElement("TH");
			YAHOO.widget.Calendar_Core.setCssClasses(fillerCell,[this.Style.CSS_WEEKDAY_CELL]);
			row.appendChild(fillerCell);
		}
		
		for(var i=0;i<this.Options.LOCALE_WEEKDAYS.length;++i) {
			var cell = document.createElement("TH");
			YAHOO.widget.Calendar_Core.setCssClasses(cell,[this.Style.CSS_WEEKDAY_CELL]);
			cell.innerHTML=this.Options.LOCALE_WEEKDAYS[i];
			row.appendChild(cell);
		}

		if (this.Config.Options.SHOW_WEEK_FOOTER) {
			fillerCell = document.createElement("TH");
			YAHOO.widget.Calendar_Core.setCssClasses(fillerCell,[this.Style.CSS_WEEKDAY_CELL]);
			row.appendChild(fillerCell);
		}
				
		head.appendChild(row);
	}

	this.table.appendChild(head);
};

/**
* Builds the calendar shell body (6 weeks by 7 days)
*/
YAHOO.widget.Calendar_Core.prototype.buildShellBody = function() {
	// This should only get executed once
	this.tbody = document.createElement("TBODY");

	for (var r=0;r<6;++r) {
		var row = document.createElement("TR");
		
		for (var c=0;c<this.headerCell.colSpan;++c) {
			var cell;
			if (this.Config.Options.SHOW_WEEK_HEADER && c===0) { // Row header
				cell = document.createElement("TH");
				this.weekHeaderCells[this.weekHeaderCells.length] = cell;
			} else if (this.Config.Options.SHOW_WEEK_FOOTER && c==(this.headerCell.colSpan-1)){ // Row footer
				cell = document.createElement("TH");
				this.weekFooterCells[this.weekFooterCells.length] = cell;
			} else {
				cell = document.createElement("TD");
				this.cells[this.cells.length] = cell;
				YAHOO.widget.Calendar_Core.setCssClasses(cell, [this.Style.CSS_CELL]);
				YAHOO.util.Event.addListener(cell, "click", this.doSelectCell, this);

				YAHOO.util.Event.addListener(cell, "mouseover", this.doCellMouseOver, this);
				YAHOO.util.Event.addListener(cell, "mouseout", this.doCellMouseOut, this);
			}
			row.appendChild(cell);
		}
		this.tbody.appendChild(row);
	}
	
	this.table.appendChild(this.tbody);
};

/**
* Builds the calendar shell footer. In the default implementation, there is
* no footer.
*/
YAHOO.widget.Calendar_Core.prototype.buildShellFooter = function() { };

/**
* Outputs the calendar shell to the DOM, inserting it into the placeholder element.
*/
YAHOO.widget.Calendar_Core.prototype.renderShell = function() {
	this.oDomContainer.appendChild(this.table);
	this.shellRendered = true;
};

/**
* Renders the calendar after it has been configured. The render() method has a specific call chain that will execute
* when the method is called: renderHeader, renderBody, renderFooter.
* Refer to the documentation for those methods for information on 
* individual render tasks.
*/
YAHOO.widget.Calendar_Core.prototype.render = function() {
	if (! this.shellRendered) {
		this.buildShell();
		this.renderShell();
	}

	this.resetRenderers();

	this.cellDates.length = 0;

	// Find starting day of the current month
	var workingDate = YAHOO.widget.DateMath.findMonthStart(this.pageDate);

	this.renderHeader();
	this.renderBody(workingDate);
	this.renderFooter();

	this.onRender();
};



/**
* Appends the header contents into the widget header.
*/
YAHOO.widget.Calendar_Core.prototype.renderHeader = function() {
	this.logger.log("Rendering header", "info");

	this.headerCell.innerHTML = "";
	
	var headerContainer = document.createElement("DIV");
	headerContainer.className = this.Style.CSS_HEADER;
	
	headerContainer.appendChild(document.createTextNode(this.buildMonthLabel()));
	
	this.headerCell.appendChild(headerContainer);
};

/**
* Appends the calendar body. The default implementation calculates the number of
* OOM (out of month) cells that need to be rendered at the start of the month, renders those, 
* and renders all the day cells using the built-in cell rendering methods.
*
* While iterating through all of the cells, the calendar checks for renderers in the
* local render stack that match the date of the current cell, and then applies styles
* as necessary.
* 
* @param {Date}	workingDate	The current working Date object being used to generate the calendar
*/
YAHOO.widget.Calendar_Core.prototype.renderBody = function(workingDate) {
	this.logger.log("Rendering body", "info");

	this.preMonthDays = workingDate.getDay();
	if (this.Options.START_WEEKDAY > 0) {
		this.preMonthDays -= this.Options.START_WEEKDAY;
	}
	if (this.preMonthDays < 0) {
		this.preMonthDays += 7;
	}
	
	this.logger.log(this.preMonthDays + " preciding out-of-month days", "info");

	this.monthDays = YAHOO.widget.DateMath.findMonthEnd(workingDate).getDate();
	this.logger.log(this.monthDays + " month days", "info");

	this.postMonthDays = YAHOO.widget.Calendar_Core.DISPLAY_DAYS-this.preMonthDays-this.monthDays;
	this.logger.log(this.postMonthDays + " post-month days", "info");
	
	workingDate = YAHOO.widget.DateMath.subtract(workingDate, YAHOO.widget.DateMath.DAY, this.preMonthDays);
	this.logger.log("Calendar page starts on " + workingDate, "info");
	
	var weekRowIndex = 0;
	
	for (var c=0;c<this.cells.length;++c) {
		var cellRenderers = new Array();
		
		var cell = this.cells[c];
		this.clearElement(cell);

		cell.index = c;
		cell.id = this.id + "_cell" + c;
		
		this.cellDates[this.cellDates.length]=[workingDate.getFullYear(),workingDate.getMonth()+1,workingDate.getDate()]; // Add this date to cellDates

		if (workingDate.getDay() == this.Options.START_WEEKDAY) {
			var rowHeaderCell = null;
			var rowFooterCell = null;
			
			if (this.Options.SHOW_WEEK_HEADER) {
				rowHeaderCell = this.weekHeaderCells[weekRowIndex];
				this.clearElement(rowHeaderCell);
			}
			
			if (this.Options.SHOW_WEEK_FOOTER) {
				rowFooterCell = this.weekFooterCells[weekRowIndex];
				this.clearElement(rowFooterCell);
			}			
			
			if (this.Options.HIDE_BLANK_WEEKS && this.isDateOOM(workingDate) && ! YAHOO.widget.DateMath.isMonthOverlapWeek(workingDate)) {
				// The first day of the week is not in this month, and it's not an overlap week
				continue;
			} else {
				if (rowHeaderCell) {
					this.renderRowHeader(workingDate, rowHeaderCell);
				}
				if (rowFooterCell) {
					this.renderRowFooter(workingDate, rowFooterCell);
				}	
			}
		}

		this.logger.log("Rendering cell " + cell.id + " (" + workingDate.getFullYear() + "-" + (workingDate.getMonth()+1) + "-" + workingDate.getDate() + ")", "cellrender");

		var renderer = null;
		
		if (workingDate.getFullYear()	== this.today.getFullYear() &&
			workingDate.getMonth()		== this.today.getMonth() &&
			workingDate.getDate()		== this.today.getDate()) {
			cellRenderers[cellRenderers.length]=this.renderCellStyleToday;
		}
		
		if (this.isDateOOM(workingDate)) {
			cellRenderers[cellRenderers.length]=this.renderCellNotThisMonth;
		} else {
			for (var r=0;r<this.renderStack.length;++r) {
				var rArray = this.renderStack[r];
				var type = rArray[0];
				
				var month;
				var day;
				var year;

				switch (type) {
					case YAHOO.widget.Calendar_Core.DATE:
						month = rArray[1][1];
						day = rArray[1][2];
						year = rArray[1][0];

						if (workingDate.getMonth()+1 == month && workingDate.getDate() == day && workingDate.getFullYear() == year) {
							renderer = rArray[2];
							this.renderStack.splice(r,1);
						}
						break;
					case YAHOO.widget.Calendar_Core.MONTH_DAY:
						month = rArray[1][0];
						day = rArray[1][1];
						
						if (workingDate.getMonth()+1 == month && workingDate.getDate() == day) {
							renderer = rArray[2];
							this.renderStack.splice(r,1);
						}
						break;
					case YAHOO.widget.Calendar_Core.RANGE:
						var date1 = rArray[1][0];
						var date2 = rArray[1][1];

						var d1month = date1[1];
						var d1day = date1[2];
						var d1year = date1[0];
						
						var d1 = new Date(d1year, d1month-1, d1day);

						var d2month = date2[1];
						var d2day = date2[2];
						var d2year = date2[0];

						var d2 = new Date(d2year, d2month-1, d2day);

						if (workingDate.getTime() >= d1.getTime() && workingDate.getTime() <= d2.getTime()) {
							renderer = rArray[2];

							if (workingDate.getTime()==d2.getTime()) { 
								this.renderStack.splice(r,1);
							}
						}
						break;
					case YAHOO.widget.Calendar_Core.WEEKDAY:
						
						var weekday = rArray[1][0];
						if (workingDate.getDay()+1 == weekday) {
							renderer = rArray[2];
						}
						break;
					case YAHOO.widget.Calendar_Core.MONTH:
						
						month = rArray[1][0];
						if (workingDate.getMonth()+1 == month) {
							renderer = rArray[2];
						}
						break;
				}
				
				if (renderer) {
					cellRenderers[cellRenderers.length]=renderer;
				}
			}

		}

		if (this._indexOfSelectedFieldArray([workingDate.getFullYear(),workingDate.getMonth()+1,workingDate.getDate()]) > -1) {
			cellRenderers[cellRenderers.length]=this.renderCellStyleSelected; 
		}

		if (this.minDate) {
			this.minDate = YAHOO.widget.DateMath.clearTime(this.minDate);
		}
		if (this.maxDate) {
			this.maxDate = YAHOO.widget.DateMath.clearTime(this.maxDate);
		}

		if (
			(this.minDate && (workingDate.getTime() < this.minDate.getTime())) ||
			(this.maxDate && (workingDate.getTime() > this.maxDate.getTime()))
		) {
			cellRenderers[cellRenderers.length]=this.renderOutOfBoundsDate;
		} else {
			cellRenderers[cellRenderers.length]=this.renderCellDefault;	
		}
		
		for (var x=0;x<cellRenderers.length;++x) {
			var ren = cellRenderers[x];
			this.logger.log("renderer[" + x + "] for (" + workingDate.getFullYear() + "-" + (workingDate.getMonth()+1) + "-" + workingDate.getDate() + ")", "cellrender");

			if (ren.call(this,workingDate,cell) == YAHOO.widget.Calendar_Core.STOP_RENDER) {
				break;
			}
		}
		
		workingDate = YAHOO.widget.DateMath.add(workingDate, YAHOO.widget.DateMath.DAY, 1); // Go to the next day
		if (workingDate.getDay() == this.Options.START_WEEKDAY) {
			weekRowIndex += 1;
		}

		YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL);

		if (c >= 0 && c <= 6) {
			YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_TOP);
		}
		if ((c % 7) == 0) {
			YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_LEFT);
		}
		if (((c+1) % 7) == 0) {
			YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_RIGHT);
		}
		
		var postDays = this.postMonthDays; 
		if (postDays >= 7 && this.Options.HIDE_BLANK_WEEKS) {
			var blankWeeks = Math.floor(postDays/7);
			for (var p=0;p<blankWeeks;++p) {
				postDays -= 7;
			}
		}
		
		if (c >= ((this.preMonthDays+postDays+this.monthDays)-7)) {
			YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_BOTTOM);
		}
	
		this.logger.log("Final styles for (" + workingDate.getFullYear() + "-" + (workingDate.getMonth()+1) + "-" + workingDate.getDate() + "): " + cell.className, "cellrender");

	}
		
};

/**
* Appends the contents of the calendar widget footer into the shell. By default, 
* the calendar does not contain a footer, and this method must be implemented by 
* subclassing the widget.
*/
YAHOO.widget.Calendar_Core.prototype.renderFooter = function() { };

/**
* @private
*/
YAHOO.widget.Calendar_Core.prototype._unload = function(e, cal) {
	for (var c in cal.cells) {
		c = null;
	}
	
	cal.cells = null;
	
	cal.tbody = null;
	cal.oDomContainer = null;
	cal.table = null;
	cal.headerCell = null;
	
	cal = null;
};
												  
												  
/****************** BEGIN BUILT-IN TABLE CELL RENDERERS ************************************/

YAHOO.widget.Calendar_Core.prototype.renderOutOfBoundsDate = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_OOB);
	cell.innerHTML = workingDate.getDate();
	return YAHOO.widget.Calendar_Core.STOP_RENDER;
}

/**
* Renders the row header for a week. The date passed in should be
* the first date of the given week.
* @param {Date}					workingDate		The current working Date object (beginning of the week) being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
*/
YAHOO.widget.Calendar_Core.prototype.renderRowHeader = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_ROW_HEADER);
	
	var useYear = this.pageDate.getFullYear();
	
	if (! YAHOO.widget.DateMath.isYearOverlapWeek(workingDate)) {
		useYear = workingDate.getFullYear();
	}
	
	var weekNum = YAHOO.widget.DateMath.getWeekNumber(workingDate, useYear, this.Options.START_WEEKDAY);
	cell.innerHTML = weekNum;
	
	if (this.isDateOOM(workingDate) && ! YAHOO.widget.DateMath.isMonthOverlapWeek(workingDate)) {
		YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_OOM);	
	}
};

/**
* Renders the row footer for a week. The date passed in should be
* the first date of the given week.
* @param {Date}					workingDate		The current working Date object (beginning of the week) being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
*/
YAHOO.widget.Calendar_Core.prototype.renderRowFooter = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_ROW_FOOTER);
	
	if (this.isDateOOM(workingDate) && ! YAHOO.widget.DateMath.isMonthOverlapWeek(workingDate)) {
		YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_OOM);	
	}
};

/**
* Renders a single standard calendar cell in the calendar widget table.
* All logic for determining how a standard default cell will be rendered is 
* encapsulated in this method, and must be accounted for when extending the
* widget class.
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellDefault = function(workingDate, cell) {
	cell.innerHTML = "";
	var link = document.createElement("a");

	link.href="javascript:void(null);";
	link.name=this.id+"__"+workingDate.getFullYear()+"_"+(workingDate.getMonth()+1)+"_"+workingDate.getDate();

	link.appendChild(document.createTextNode(this.buildDayLabel(workingDate)));
	cell.appendChild(link);
};

/**
* Renders a single standard calendar cell using the CSS hightlight1 style
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellStyleHighlight1 = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_HIGHLIGHT1);
};

/**
* Renders a single standard calendar cell using the CSS hightlight2 style
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellStyleHighlight2 = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_HIGHLIGHT2);
};

/**
* Renders a single standard calendar cell using the CSS hightlight3 style
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellStyleHighlight3 = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_HIGHLIGHT3);
};

/**
* Renders a single standard calendar cell using the CSS hightlight4 style
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellStyleHighlight4 = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_HIGHLIGHT4);
};

/**
* Applies the default style used for rendering today's date to the current calendar cell
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return	YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellStyleToday = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_TODAY);
};

/**
* Applies the default style used for rendering selected dates to the current calendar cell
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return	YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellStyleSelected = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_SELECTED);
};

/**
* Applies the default style used for rendering dates that are not a part of the current
* month (preceding or trailing the cells for the current month)
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return	YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderCellNotThisMonth = function(workingDate, cell) {
	YAHOO.util.Dom.addClass(cell, this.Style.CSS_CELL_OOM);
	cell.innerHTML=workingDate.getDate();
	return YAHOO.widget.Calendar_Core.STOP_RENDER;
};

/**
* Renders the current calendar cell as a non-selectable "black-out" date using the default
* restricted style.
* @param {Date}					workingDate		The current working Date object being used to generate the calendar
* @param {HTMLTableCellElement}	cell			The current working cell in the calendar
* @return	YAHOO.widget.Calendar_Core.STOP_RENDER if rendering should stop with this style, null or nothing if rendering
*			should not be terminated
* @type String
*/
YAHOO.widget.Calendar_Core.prototype.renderBodyCellRestricted = function(workingDate, cell) {
	YAHOO.widget.Calendar_Core.setCssClasses(cell, [this.Style.CSS_CELL,this.Style.CSS_CELL_RESTRICTED]);
	cell.innerHTML=workingDate.getDate();
	return YAHOO.widget.Calendar_Core.STOP_RENDER;
};
/******************** END BUILT-IN TABLE CELL RENDERERS ************************************/

/******************** BEGIN MONTH NAVIGATION METHODS ************************************/
/**
* Adds the designated number of months to the current calendar month, and sets the current
* calendar page date to the new month.
* @param {Integer}	count	The number of months to add to the current calendar
*/
YAHOO.widget.Calendar_Core.prototype.addMonths = function(count) {
	this.pageDate = YAHOO.widget.DateMath.add(this.pageDate, YAHOO.widget.DateMath.MONTH, count);
	this.resetRenderers();
	this.onChangePage();
};

/**
* Subtracts the designated number of months from the current calendar month, and sets the current
* calendar page date to the new month.
* @param {Integer}	count	The number of months to subtract from the current calendar
*/
YAHOO.widget.Calendar_Core.prototype.subtractMonths = function(count) {
	this.pageDate = YAHOO.widget.DateMath.subtract(this.pageDate, YAHOO.widget.DateMath.MONTH, count);
	this.resetRenderers();
	this.onChangePage();
};

/**
* Adds the designated number of years to the current calendar, and sets the current
* calendar page date to the new month.
* @param {Integer}	count	The number of years to add to the current calendar
*/
YAHOO.widget.Calendar_Core.prototype.addYears = function(count) {
	this.pageDate = YAHOO.widget.DateMath.add(this.pageDate, YAHOO.widget.DateMath.YEAR, count);
	this.resetRenderers();
	this.onChangePage();
};

/**
* Subtcats the designated number of years from the current calendar, and sets the current
* calendar page date to the new month.
* @param {Integer}	count	The number of years to subtract from the current calendar
*/
YAHOO.widget.Calendar_Core.prototype.subtractYears = function(count) {
	this.pageDate = YAHOO.widget.DateMath.subtract(this.pageDate, YAHOO.widget.DateMath.YEAR, count);
	this.resetRenderers();
	this.onChangePage();
};

/**
* Navigates to the next month page in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.nextMonth = function() {
	this.addMonths(1);
};

/**
* Navigates to the previous month page in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.previousMonth = function() {
	this.subtractMonths(1);
};

/**
* Navigates to the next year in the currently selected month in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.nextYear = function() {
	this.addYears(1);
};

/**
* Navigates to the previous year in the currently selected month in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.previousYear = function() {
	this.subtractYears(1);
};

/****************** END MONTH NAVIGATION METHODS ************************************/

/************* BEGIN SELECTION METHODS *************************************************************/

/**
* Resets the calendar widget to the originally selected month and year, and 
* sets the calendar to the initial selection(s).
*/
YAHOO.widget.Calendar_Core.prototype.reset = function() {
	this.selectedDates.length = 0;
	this.selectedDates = this._selectedDates.concat();

	this.pageDate = new Date(this._pageDate.getTime());
	this.onReset();
};

/**
* Clears the selected dates in the current calendar widget and sets the calendar
* to the current month and year.
*/
YAHOO.widget.Calendar_Core.prototype.clear = function() {
	this.selectedDates.length = 0;
	this.pageDate = new Date(this.today.getTime());
	this.onClear();
};

/**
* Selects a date or a collection of dates on the current calendar. This method, by default,
* does not call the render method explicitly. Once selection has completed, render must be 
* called for the changes to be reflected visually.
* @param	{String/Date/Date[]}	date	The date string of dates to select in the current calendar. Valid formats are
*								individual date(s) (12/24/2005,12/26/2005) or date range(s) (12/24/2005-1/1/2006).
*								Multiple comma-delimited dates can also be passed to this method (12/24/2005,12/11/2005-12/13/2005).
*								This method can also take a JavaScript Date object or an array of Date objects.
* @return						Array of JavaScript Date objects representing all individual dates that are currently selected.
* @type Date[]
*/
YAHOO.widget.Calendar_Core.prototype.select = function(date) {
	this.onBeforeSelect();
	this.logger.log("Select: " + date, "info");

	var aToBeSelected = this._toFieldArray(date);
	this.logger.log("Selection field array: " + aToBeSelected, "info");

	for (var a=0;a<aToBeSelected.length;++a) {
		var toSelect = aToBeSelected[a]; // For each date item in the list of dates we're trying to select
		if (this._indexOfSelectedFieldArray(toSelect) == -1) { // not already selected?
			this.selectedDates[this.selectedDates.length]=toSelect;
		}
	}
	
	if (this.parent) {
		this.parent.sync(this);
	}

	this.onSelect();

	return this.getSelectedDates();
};

/**
* Selects a date on the current calendar by referencing the index of the cell that should be selected.
* This method is used to easily select a single cell (usually with a mouse click) without having to do
* a full render. The selected style is applied to the cell directly.
* @param	{Integer}	cellIndex	The index of the cell to select in the current calendar. 
* @return							Array of JavaScript Date objects representing all individual dates that are currently selected.
* @type Date[]
*/
YAHOO.widget.Calendar_Core.prototype.selectCell = function(cellIndex) {
	this.onBeforeSelect();

	this.cells = this.tbody.getElementsByTagName("TD");

	var cell = this.cells[cellIndex];
	var cellDate = this.cellDates[cellIndex];

	var dCellDate = this._toDate(cellDate);
	this.logger.log("Select: " + dCellDate, "info");

	var selectDate = cellDate.concat();

	this.selectedDates.push(selectDate);
	
	if (this.parent) {
		this.parent.sync(this);
	}

	this.renderCellStyleSelected(dCellDate,cell);

	this.onSelect();
	this.doCellMouseOut.call(cell, null, this);

	return this.getSelectedDates();
};

/**
* Deselects a date or a collection of dates on the current calendar. This method, by default,
* does not call the render method explicitly. Once deselection has completed, render must be 
* called for the changes to be reflected visually.
* @param	{String/Date/Date[]}	date	The date string of dates to deselect in the current calendar. Valid formats are
*								individual date(s) (12/24/2005,12/26/2005) or date range(s) (12/24/2005-1/1/2006).
*								Multiple comma-delimited dates can also be passed to this method (12/24/2005,12/11/2005-12/13/2005).
*								This method can also take a JavaScript Date object or an array of Date objects.	
* @return						Array of JavaScript Date objects representing all individual dates that are currently selected.
* @type Date[]
*/
YAHOO.widget.Calendar_Core.prototype.deselect = function(date) {
	this.onBeforeDeselect();

	var aToBeSelected = this._toFieldArray(date);

	this.logger.log("Select: " + aToBeSelected, "info");

	for (var a=0;a<aToBeSelected.length;++a) {
		var toSelect = aToBeSelected[a]; // For each date item in the list of dates we're trying to select
		var index = this._indexOfSelectedFieldArray(toSelect);
	
		if (index != -1) {	
			this.selectedDates.splice(index,1);
		}
	}

	if (this.parent) {
		this.parent.sync(this);
	} 

	this.onDeselect();
	return this.getSelectedDates();
};

/**
* Deselects a date on the current calendar by referencing the index of the cell that should be deselected.
* This method is used to easily deselect a single cell (usually with a mouse click) without having to do
* a full render. The selected style is removed from the cell directly.
* @param	{Integer}	cellIndex	The index of the cell to deselect in the current calendar. 
* @return							Array of JavaScript Date objects representing all individual dates that are currently selected.
* @type Date[]
*/
YAHOO.widget.Calendar_Core.prototype.deselectCell = function(i) {
	this.onBeforeDeselect();
	this.cells = this.tbody.getElementsByTagName("TD");

	var cell = this.cells[i];
	var cellDate = this.cellDates[i];
	var cellDateIndex = this._indexOfSelectedFieldArray(cellDate);

	var dCellDate = this._toDate(cellDate);
	this.logger.log("Deselect: " + dCellDate, "info");

	var selectDate = cellDate.concat();

	if (cellDateIndex > -1) {
		if (this.pageDate.getMonth() == dCellDate.getMonth() &&
			this.pageDate.getFullYear() == dCellDate.getFullYear()) {
			YAHOO.util.Dom.removeClass(cell, this.Style.CSS_CELL_SELECTED);
		}

		this.selectedDates.splice(cellDateIndex, 1);
	}


	if (this.parent) {
		this.parent.sync(this);
	}

	this.onDeselect();
	return this.getSelectedDates();
};

/**
* Deselects all dates on the current calendar.
* @return				Array of JavaScript Date objects representing all individual dates that are currently selected.
*						Assuming that this function executes properly, the return value should be an empty array.
*						However, the empty array is returned for the sake of being able to check the selection status
*						of the calendar.
* @type Date[]
*/
YAHOO.widget.Calendar_Core.prototype.deselectAll = function() {
	this.onBeforeDeselect();
	var count = this.selectedDates.length;
	this.selectedDates.length = 0;

	if (this.parent) {
		this.parent.sync(this);
	}
	
	if (count > 0) {
		this.onDeselect();
	}

	return this.getSelectedDates();
};
/************* END SELECTION METHODS *************************************************************/


/************* BEGIN TYPE CONVERSION METHODS ****************************************************/

/**
* Converts a date (either a JavaScript Date object, or a date string) to the internal data structure
* used to represent dates: [[yyyy,mm,dd],[yyyy,mm,dd]].
* @private
* @param	{String/Date/Date[]}	date	The date string of dates to deselect in the current calendar. Valid formats are
*								individual date(s) (12/24/2005,12/26/2005) or date range(s) (12/24/2005-1/1/2006).
*								Multiple comma-delimited dates can also be passed to this method (12/24/2005,12/11/2005-12/13/2005).
*								This method can also take a JavaScript Date object or an array of Date objects.	
* @return						Array of date field arrays
* @type Array[](Integer[])
*/
YAHOO.widget.Calendar_Core.prototype._toFieldArray = function(date) {
	var returnDate = new Array();

	if (date instanceof Date) {
		returnDate = [[date.getFullYear(), date.getMonth()+1, date.getDate()]];
	} else if (typeof date == 'string') {
		returnDate = this._parseDates(date);
	} else if (date instanceof Array) {
		for (var i=0;i<date.length;++i) {
			var d = date[i];
			returnDate[returnDate.length] = [d.getFullYear(),d.getMonth()+1,d.getDate()];
		}
	}
	
	return returnDate;
};

/**
* Converts a date field array [yyyy,mm,dd] to a JavaScript Date object.
* @private
* @param	{Integer[]}		dateFieldArray	The date field array to convert to a JavaScript Date.
* @return					JavaScript Date object representing the date field array
* @type Date
*/
YAHOO.widget.Calendar_Core.prototype._toDate = function(dateFieldArray) {
	if (dateFieldArray instanceof Date) {
		return dateFieldArray;
	} else {
		return new Date(dateFieldArray[0],dateFieldArray[1]-1,dateFieldArray[2]);
	}
};
/************* END TYPE CONVERSION METHODS ******************************************************/


/************* BEGIN UTILITY METHODS ****************************************************/
/**
* Converts a date field array [yyyy,mm,dd] to a JavaScript Date object.
* @private
* @param	{Integer[]}	array1	The first date field array to compare
* @param	{Integer[]}	array2	The first date field array to compare
* @return						The boolean that represents the equality of the two arrays
* @type Boolean
*/
YAHOO.widget.Calendar_Core.prototype._fieldArraysAreEqual = function(array1, array2) {
	var match = false;

	if (array1[0]==array2[0]&&array1[1]==array2[1]&&array1[2]==array2[2]) {
		match=true;	
	}

	return match;
};

/**
* Gets the index of a date field array [yyyy,mm,dd] in the current list of selected dates.
* @private
* @param	{Integer[]}		find	The date field array to search for
* @return					The index of the date field array within the collection of selected dates.
*								-1 will be returned if the date is not found.
* @type Integer
*/
YAHOO.widget.Calendar_Core.prototype._indexOfSelectedFieldArray = function(find) {
	var selected = -1;

	for (var s=0;s<this.selectedDates.length;++s) {
		var sArray = this.selectedDates[s];
		if (find[0]==sArray[0]&&find[1]==sArray[1]&&find[2]==sArray[2]) {
			selected = s;
			break;
		}
	}

	return selected;
};

/**
* Determines whether a given date is OOM (out of month).
* @param	{Date}	date	The JavaScript Date object for which to check the OOM status
* @return	{Boolean}	true if the date is OOM
*/
YAHOO.widget.Calendar_Core.prototype.isDateOOM = function(date) {
	var isOOM = false;
	if (date.getMonth() != this.pageDate.getMonth()) {
		isOOM = true;
	}
	return isOOM;
};

/************* END UTILITY METHODS *******************************************************/

/************* BEGIN EVENT HANDLERS ******************************************************/

/**
* Event executed before a date is selected in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.onBeforeSelect = function() {
	if (! this.Options.MULTI_SELECT) {
		this.clearAllBodyCellStyles(this.Style.CSS_CELL_SELECTED);
		this.deselectAll();
	}
};

/**
* Event executed when a date is selected in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.onSelect = function() { };

/**
* Event executed before a date is deselected in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.onBeforeDeselect = function() { };

/**
* Event executed when a date is deselected in the calendar widget.
*/
YAHOO.widget.Calendar_Core.prototype.onDeselect = function() { };

/**
* Event executed when the user navigates to a different calendar page.
*/
YAHOO.widget.Calendar_Core.prototype.onChangePage = function() {
		var me = this;

		this.renderHeader();
		if (this.renderProcId) {
			clearTimeout(this.renderProcId);
		}
		this.renderProcId = setTimeout(function() {
											me.render();
											me.renderProcId = null;
										}, 1);
};

/**
* Event executed when the calendar widget is rendered.
*/
YAHOO.widget.Calendar_Core.prototype.onRender = function() { };

/**
* Event executed when the calendar widget is reset to its original state.
*/
YAHOO.widget.Calendar_Core.prototype.onReset = function() { this.render(); };

/**
* Event executed when the calendar widget is completely cleared to the current month with no selections.
*/
YAHOO.widget.Calendar_Core.prototype.onClear = function() { this.render(); };

/**
* Validates the calendar widget. This method has no default implementation
* and must be extended by subclassing the widget.
* @return	Should return true if the widget validates, and false if
* it doesn't.
* @type Boolean
*/
YAHOO.widget.Calendar_Core.prototype.validate = function() { return true; };

/************* END EVENT HANDLERS *********************************************************/


/************* BEGIN DATE PARSE METHODS ***************************************************/


/**
* Converts a date string to a date field array
* @private
* @param	{String}	sDate			Date string. Valid formats are mm/dd and mm/dd/yyyy.
* @return				A date field array representing the string passed to the method
* @type Array[](Integer[])
*/
YAHOO.widget.Calendar_Core.prototype._parseDate = function(sDate) {
	var aDate = sDate.split(this.Locale.DATE_FIELD_DELIMITER);
	var rArray;

	if (aDate.length == 2) {
		rArray = [aDate[this.Locale.MD_MONTH_POSITION-1],aDate[this.Locale.MD_DAY_POSITION-1]];
		rArray.type = YAHOO.widget.Calendar_Core.MONTH_DAY;
	} else {
		rArray = [aDate[this.Locale.MDY_YEAR_POSITION-1],aDate[this.Locale.MDY_MONTH_POSITION-1],aDate[this.Locale.MDY_DAY_POSITION-1]];
		rArray.type = YAHOO.widget.Calendar_Core.DATE;
	}
	return rArray;
};

/**
* Converts a multi or single-date string to an array of date field arrays
* @private
* @param	{String}	sDates		Date string with one or more comma-delimited dates. Valid formats are mm/dd, mm/dd/yyyy, mm/dd/yyyy-mm/dd/yyyy
* @return							An array of date field arrays
* @type Array[](Integer[])
*/
YAHOO.widget.Calendar_Core.prototype._parseDates = function(sDates) {
	var aReturn = new Array();

	var aDates = sDates.split(this.Locale.DATE_DELIMITER);
	
	for (var d=0;d<aDates.length;++d) {
		var sDate = aDates[d];

		if (sDate.indexOf(this.Locale.DATE_RANGE_DELIMITER) != -1) {
			// This is a range
			var aRange = sDate.split(this.Locale.DATE_RANGE_DELIMITER);

			var dateStart = this._parseDate(aRange[0]);
			var dateEnd = this._parseDate(aRange[1]);

			var fullRange = this._parseRange(dateStart, dateEnd);
			aReturn = aReturn.concat(fullRange);
		} else {
			// This is not a range
			var aDate = this._parseDate(sDate);
			aReturn.push(aDate);
		}
	}
	return aReturn;
};

/**
* Converts a date range to the full list of included dates
* @private
* @param	{Integer[]}	startDate	Date field array representing the first date in the range
* @param	{Integer[]}	endDate		Date field array representing the last date in the range
* @return							An array of date field arrays
* @type Array[](Integer[])
*/
YAHOO.widget.Calendar_Core.prototype._parseRange = function(startDate, endDate) {
	var dStart   = new Date(startDate[0],startDate[1]-1,startDate[2]);
	var dCurrent = YAHOO.widget.DateMath.add(new Date(startDate[0],startDate[1]-1,startDate[2]),YAHOO.widget.DateMath.DAY,1);
	var dEnd     = new Date(endDate[0],  endDate[1]-1,  endDate[2]);

	var results = new Array();
	results.push(startDate);
	while (dCurrent.getTime() <= dEnd.getTime()) {
		results.push([dCurrent.getFullYear(),dCurrent.getMonth()+1,dCurrent.getDate()]);
		dCurrent = YAHOO.widget.DateMath.add(dCurrent,YAHOO.widget.DateMath.DAY,1);
	}
	return results;
};

/************* END DATE PARSE METHODS *****************************************************/

/************* BEGIN RENDERER METHODS *****************************************************/

/**
* Resets the render stack of the current calendar to its original pre-render value.
*/
YAHOO.widget.Calendar_Core.prototype.resetRenderers = function() {
	this.renderStack = this._renderStack.concat();
};

/**
* Clears the inner HTML, CSS class and style information from the specified cell.
* @param	{HTMLTableCellElement}	The cell to clear
*/ 
YAHOO.widget.Calendar_Core.prototype.clearElement = function(cell) {
	cell.innerHTML = "&nbsp;";
	cell.className="";
};

/**
* Adds a renderer to the render stack. The function reference passed to this method will be executed
* when a date cell matches the conditions specified in the date string for this renderer.
* @param	{String}	sDates		A date string to associate with the specified renderer. Valid formats
*									include date (12/24/2005), month/day (12/24), and range (12/1/2004-1/1/2005)
* @param	{Function}	fnRender	The function executed to render cells that match the render rules for this renderer.
*/
YAHOO.widget.Calendar_Core.prototype.addRenderer = function(sDates, fnRender) {
	var aDates = this._parseDates(sDates);
	for (var i=0;i<aDates.length;++i) {
		var aDate = aDates[i];
	
		if (aDate.length == 2) { // this is either a range or a month/day combo
			if (aDate[0] instanceof Array) { // this is a range
				this._addRenderer(YAHOO.widget.Calendar_Core.RANGE,aDate,fnRender);
			} else { // this is a month/day combo
				this._addRenderer(YAHOO.widget.Calendar_Core.MONTH_DAY,aDate,fnRender);
			}
		} else if (aDate.length == 3) {
			this._addRenderer(YAHOO.widget.Calendar_Core.DATE,aDate,fnRender);
		}
	}
};

/**
* The private method used for adding cell renderers to the local render stack.
* This method is called by other methods that set the renderer type prior to the method call.
* @private
* @param	{String}	type		The type string that indicates the type of date renderer being added.
*									Values are YAHOO.widget.Calendar_Core.DATE, YAHOO.widget.Calendar_Core.MONTH_DAY, YAHOO.widget.Calendar_Core.WEEKDAY,
*									YAHOO.widget.Calendar_Core.RANGE, YAHOO.widget.Calendar_Core.MONTH
* @param	{Array}		aDates		An array of dates used to construct the renderer. The format varies based
*									on the renderer type
* @param	{Function}	fnRender	The function executed to render cells that match the render rules for this renderer.
*/
YAHOO.widget.Calendar_Core.prototype._addRenderer = function(type, aDates, fnRender) {
	var add = [type,aDates,fnRender];
	this.renderStack.unshift(add);	
	
	this._renderStack = this.renderStack.concat();
};

/**
* Adds a month to the render stack. The function reference passed to this method will be executed
* when a date cell matches the month passed to this method.
* @param	{Integer}	month		The month (1-12) to associate with this renderer
* @param	{Function}	fnRender	The function executed to render cells that match the render rules for this renderer.
*/
YAHOO.widget.Calendar_Core.prototype.addMonthRenderer = function(month, fnRender) {
	this._addRenderer(YAHOO.widget.Calendar_Core.MONTH,[month],fnRender);
};

/**
* Adds a weekday to the render stack. The function reference passed to this method will be executed
* when a date cell matches the weekday passed to this method.
* @param	{Integer}	weekay		The weekday (1-7) to associate with this renderer
* @param	{Function}	fnRender	The function executed to render cells that match the render rules for this renderer.
*/
YAHOO.widget.Calendar_Core.prototype.addWeekdayRenderer = function(weekday, fnRender) {
	this._addRenderer(YAHOO.widget.Calendar_Core.WEEKDAY,[weekday],fnRender);
};
//// END RENDERER METHODS ////

//// BEGIN CSS METHODS ////

/**
* Sets the specified array of CSS classes into the referenced element
* @param	{HTMLElement}	element		The element to set the CSS classes into
* @param	{String[]}		aStyles		An array of CSS class names
*/
YAHOO.widget.Calendar_Core.setCssClasses = function(element, aStyles) {
	element.className = "";
	var className = aStyles.join(" ");
	element.className = className;
};

/**
* Removes all styles from all body cells in the current calendar table.
* @param	{style}		The CSS class name to remove from all calendar body cells
*/
YAHOO.widget.Calendar_Core.prototype.clearAllBodyCellStyles = function(style) {
	for (var c=0;c<this.cells.length;++c) {
		YAHOO.util.Dom.removeClass(this.cells[c],style);
	}
};

//// END CSS METHODS ////

//// BEGIN GETTER/SETTER METHODS ////
/**
* Sets the calendar's month explicitly.
* @param {Integer}	month		The numeric month, from 1 (January) to 12 (December)
*/
YAHOO.widget.Calendar_Core.prototype.setMonth = function(month) {
	this.pageDate.setMonth(month);
};

/**
* Sets the calendar's year explicitly.
* @param {Integer}	year		The numeric 4-digit year
*/
YAHOO.widget.Calendar_Core.prototype.setYear = function(year) {
	this.pageDate.setFullYear(year);
};

/**
* Gets the list of currently selected dates from the calendar.
* @return	An array of currently selected JavaScript Date objects.
* @type Date[]
*/
YAHOO.widget.Calendar_Core.prototype.getSelectedDates = function() {
	var returnDates = new Array();

	for (var d=0;d<this.selectedDates.length;++d) {
		var dateArray = this.selectedDates[d];

		var date = new Date(dateArray[0],dateArray[1]-1,dateArray[2]);
		returnDates.push(date);
	}

	returnDates.sort();
	return returnDates;
};

/// END GETTER/SETTER METHODS ///

/**
* Returns a string representing the current browser.
* @type String
*/
YAHOO.widget.Calendar_Core._getBrowser = function() {
  /**
   * UserAgent
   * @private
   * @type String
   */
  var ua = navigator.userAgent.toLowerCase();
  
  if (ua.indexOf('opera')!=-1) // Opera (check first in case of spoof)
	 return 'opera';
  else if (ua.indexOf('msie')!=-1) // IE
	 return 'ie';
  else if (ua.indexOf('safari')!=-1) // Safari (check before Gecko because it includes "like Gecko")
	 return 'safari';
  else if (ua.indexOf('gecko') != -1) // Gecko
	 return 'gecko';
 else
  return false;
}

/**
* Returns a string representation of the object.
* @type string
*/
YAHOO.widget.Calendar_Core.prototype.toString = function() {
	return "Calendar_Core " + this.id;
}

YAHOO.widget.Cal_Core = YAHOO.widget.Calendar_Core;/**
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt 
**/

/**
* @class
* Calendar is the default implementation of the YAHOO.widget.Calendar_Core base class.
* This class is the UED-approved version of the calendar selector widget. For all documentation
* on the implemented methods listed here, see the documentation for YAHOO.widget.Calendar_Core.
* @constructor
* @param {String}	id			The id of the table element that will represent the calendar widget
* @param {String}	containerId	The id of the container element that will contain the calendar table
* @param {String}	monthyear	The month/year string used to set the current calendar page
* @param {String}	selected	A string of date values formatted using the date parser. The built-in
								default date format is MM/DD/YYYY. Ranges are defined using
								MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
								Any combination of these can be combined by delimiting the string with
								commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.Calendar = function(id, containerId, monthyear, selected) {
	if (arguments.length > 0) {
		this.init(id, containerId, monthyear, selected);
	}
}

YAHOO.widget.Calendar.prototype = new YAHOO.widget.Calendar_Core();

YAHOO.widget.Calendar.prototype.buildShell = function() {
	this.border = document.createElement("DIV");
	this.border.className =  this.Style.CSS_CONTAINER;
	
	this.table = document.createElement("TABLE");
	this.table.cellSpacing = 0;	
	
	YAHOO.widget.Calendar_Core.setCssClasses(this.table, [this.Style.CSS_CALENDAR]);

	this.border.id = this.id;
	
	this.buildShellHeader();
	this.buildShellBody();
	this.buildShellFooter();
};

YAHOO.widget.Calendar.prototype.renderShell = function() {
	this.border.appendChild(this.table);
	this.oDomContainer.appendChild(this.border);
	this.shellRendered = true;
};

YAHOO.widget.Calendar.prototype.renderHeader = function() {
	this.headerCell.innerHTML = "";
	
	var headerContainer = document.createElement("DIV");
	headerContainer.className = this.Style.CSS_HEADER;
	
	if (this.linkLeft) {
		YAHOO.util.Event.removeListener(this.linkLeft, "mousedown", this.previousMonth);
	}
	this.linkLeft = document.createElement("A");
	this.linkLeft.innerHTML = "&nbsp;";
	YAHOO.util.Event.addListener(this.linkLeft, "mousedown", this.previousMonth, this, true);
	this.linkLeft.style.backgroundImage =  "url(" + this.Options.NAV_ARROW_LEFT + ")";
	this.linkLeft.className = this.Style.CSS_NAV_LEFT;
	
	if (this.linkRight) {
		YAHOO.util.Event.removeListener(this.linkRight, "mousedown", this.nextMonth);
	}
	this.linkRight = document.createElement("A");
	this.linkRight.innerHTML = "&nbsp;";
	YAHOO.util.Event.addListener(this.linkRight, "mousedown", this.nextMonth, this, true);
	this.linkRight.style.backgroundImage = "url(" + this.Options.NAV_ARROW_RIGHT + ")";
	this.linkRight.className = this.Style.CSS_NAV_RIGHT;
	
	headerContainer.appendChild(this.linkLeft);
	headerContainer.appendChild(document.createTextNode(this.buildMonthLabel()));
	headerContainer.appendChild(this.linkRight);
	
	this.headerCell.appendChild(headerContainer);
};

YAHOO.widget.Cal = YAHOO.widget.Calendar;/**
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt 
**/

/**
* @class
* <p>YAHOO.widget.CalendarGroup is a special container class for YAHOO.widget.Calendar_Core. This class facilitates
* the ability to have multi-page calendar views that share a single dataset and are
* dependent on each other.</p>
* 
* <p>The calendar group instance will refer to each of its elements using a 0-based index.
* For example, to construct the placeholder for a calendar group widget with id "cal1" and
* containerId of "cal1Container", the markup would be as follows:
*	<xmp>
*		<div id="cal1Container_0"></div>
*		<div id="cal1Container_1"></div>
*	</xmp>
* The tables for the calendars ("cal1_0" and "cal1_1") will be inserted into those containers.
* </p>
* @constructor
* @param {Integer}		pageCount	The number of pages that this calendar should display.
* @param {String}		id			The id of the element that will be inserted into the DOM.
* @param {String}	containerId	The id of the container element that the calendar will be inserted into.
* @param {String}		monthyear	The month/year string used to set the current calendar page
* @param {String}		selected	A string of date values formatted using the date parser. The built-in
									default date format is MM/DD/YYYY. Ranges are defined using
									MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
									Any combination of these can be combined by delimiting the string with
									commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.CalendarGroup = function(pageCount, id, containerId, monthyear, selected) {
	if (arguments.length > 0) {
		this.init(pageCount, id, containerId, monthyear, selected);
	}
}

/**
* Initializes the calendar group. All subclasses must call this method in order for the
* group to be initialized properly.
* @param {Integer}		pageCount	The number of pages that this calendar should display.
* @param {String}		id			The id of the element that will be inserted into the DOM.
* @param {String}		containerId	The id of the container element that the calendar will be inserted into.
* @param {String}		monthyear	The month/year string used to set the current calendar page
* @param {String}		selected	A string of date values formatted using the date parser. The built-in
									default date format is MM/DD/YYYY. Ranges are defined using
									MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
									Any combination of these can be combined by delimiting the string with
									commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.CalendarGroup.prototype.init = function(pageCount, id, containerId, monthyear, selected) {
	this.logger = new YAHOO.widget.LogWriter("CalendarGroup " + id);	
	
	this.id = id;
	this.selectedDates = new Array();
	this.containerId = containerId;
	
	this.pageCount = pageCount;

	this.pages = new Array();

	for (var p=0;p<pageCount;++p) {
		var cal = this.constructChild(id + "_" + p, this.containerId + "_" + p , monthyear, selected);
				
		cal.parent = this;
		
		cal.index = p;

		cal.pageDate.setMonth(cal.pageDate.getMonth()+p);
		cal._pageDate = new Date(cal.pageDate.getFullYear(),cal.pageDate.getMonth(),cal.pageDate.getDate());
		this.pages.push(cal);
	}
	
	this.doNextMonth = function(e, calGroup) {
		calGroup.nextMonth();
	};
	
	this.doPreviousMonth = function(e, calGroup) {
		calGroup.previousMonth();
	};
	
	this.logger.log("Initialized " + pageCount + "-page CalendarGroup", "info");
};

/**
* Adds a function to all child Calendars within this CalendarGroup.
* @param {String}		fnName		The name of the function
* @param {Function}		fn			The function to apply to each Calendar page object
*/
YAHOO.widget.CalendarGroup.prototype.setChildFunction = function(fnName, fn) {
	for (var p=0;p<this.pageCount;++p) {
		this.pages[p][fnName] = fn;
	}
}

/**
* Calls a function within all child Calendars within this CalendarGroup.
* @param {String}		fnName		The name of the function
* @param {Array}		args		The arguments to pass to the function
*/
YAHOO.widget.CalendarGroup.prototype.callChildFunction = function(fnName, args) {
	for (var p=0;p<this.pageCount;++p) {
		var page = this.pages[p];
		if (page[fnName]) {
			var fn = page[fnName];
			fn.call(page, args);
		}
	}	
}

/**
* Constructs a child calendar. This method can be overridden if a subclassed version of the default
* calendar is to be used.
* @param {String}		id			The id of the element that will be inserted into the DOM.
* @param {String}		containerId	The id of the container element that the calendar will be inserted into.
* @param {String}		monthyear	The month/year string used to set the current calendar page
* @param {String}		selected	A string of date values formatted using the date parser. The built-in
									default date format is MM/DD/YYYY. Ranges are defined using
									MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
									Any combination of these can be combined by delimiting the string with
									commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
* @return							The YAHOO.widget.Calendar_Core instance that is constructed
* @type YAHOO.widget.Calendar_Core
*/
YAHOO.widget.CalendarGroup.prototype.constructChild = function(id,containerId,monthyear,selected) {
	return new YAHOO.widget.Calendar_Core(id,containerId,monthyear,selected);
};


/**
* Sets the calendar group's month explicitly. This month will be set into the first
* page of the multi-page calendar, and all other months will be iterated appropriately.
* @param {Integer}	month		The numeric month, from 1 (January) to 12 (December)
*/
YAHOO.widget.CalendarGroup.prototype.setMonth = function(month) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.setMonth(month+p);
	}
};

/**
* Sets the calendar group's year explicitly. This year will be set into the first
* page of the multi-page calendar, and all other months will be iterated appropriately.
* @param {Integer}	year		The numeric 4-digit year
*/
YAHOO.widget.CalendarGroup.prototype.setYear = function(year) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		if ((cal.pageDate.getMonth()+1) == 1 && p>0)
		{
			year+=1;
		}
		cal.setYear(year);
	}
};

/**
* Calls the render function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.render = function() {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.render();
	}
};

/**
* Calls the select function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.select = function(date) {
	var ret;
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		ret = cal.select(date);
	}
	return ret;
};

/**
* Calls the selectCell function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.selectCell = function(cellIndex) {
	var ret;
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		ret = cal.selectCell(cellIndex);
	}
	return ret;
};

/**
* Calls the deselect function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.deselect = function(date) {
	var ret;
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		ret = cal.deselect(date);
	}
	return ret;
};

/**
* Calls the deselectAll function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.deselectAll = function() {
	var ret;
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		ret = cal.deselectAll();
	}
	return ret;
};

/**
* Calls the deselectAll function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.deselectCell = function(cellIndex) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.deselectCell(cellIndex);
	}
	return this.getSelectedDates();
};

/**
* Calls the reset function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.reset = function() {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.reset();
	}
};

/**
* Calls the clear function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.clear = function() {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.clear();
	}
};

/**
* Calls the nextMonth function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.nextMonth = function() {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.nextMonth();
	}
};

/**
* Calls the previousMonth function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.previousMonth = function() {
	for (var p=this.pages.length-1;p>=0;--p)
	{
		var cal = this.pages[p];
		cal.previousMonth();
	}
};

/**
* Calls the nextYear function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.nextYear = function() {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.nextYear();
	}
};

/**
* Calls the previousYear function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.previousYear = function() {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.previousYear();
	}
};

/**
* Synchronizes the data values for all child calendars within the group. If the sync
* method is called passing in the caller object, the values of all children will be set
* to the values of the caller. If the argument is ommitted, the values from all children
* will be combined into one distinct list and set into each child.
* @param	{YAHOO.widget.Calendar_Core}	caller		The YAHOO.widget.Calendar_Core that is initiating the call to sync().
* @return								Array of selected dates, in JavaScript Date object form.
* @type Date[]
*/
YAHOO.widget.CalendarGroup.prototype.sync = function(caller) {
	var calendar;

	if (caller)
	{
		this.selectedDates = caller.selectedDates.concat();
	} else {
		var hash = new Object();
		var combinedDates = new Array();

		for (var p=0;p<this.pages.length;++p)
		{
			calendar = this.pages[p];

			var values = calendar.selectedDates;

			for (var v=0;v<values.length;++v)
			{
				var valueArray = values[v];
				hash[valueArray.toString()] = valueArray;
			}
		}

		for (var val in hash)
		{
			combinedDates[combinedDates.length]=hash[val];
		}
		
		this.selectedDates = combinedDates.concat();
	}

	// Set all the values into the children
	for (p=0;p<this.pages.length;++p)
	{
		calendar = this.pages[p];
		if (! calendar.Options.MULTI_SELECT) {
			calendar.clearAllBodyCellStyles(calendar.Config.Style.CSS_CELL_SELECTED);
		}
		calendar.selectedDates = this.selectedDates.concat();
		
	}
	
	return this.getSelectedDates();
};

/**
* Gets the list of currently selected dates from the calendar.
* @return			An array of currently selected JavaScript Date objects.
* @type Date[]
*/
YAHOO.widget.CalendarGroup.prototype.getSelectedDates = function() { 
	var returnDates = new Array();

	for (var d=0;d<this.selectedDates.length;++d)
	{
		var dateArray = this.selectedDates[d];

		var date = new Date(dateArray[0],dateArray[1]-1,dateArray[2]);
		returnDates.push(date);
	}

	returnDates.sort();
	return returnDates;
};

/**
* Calls the addRenderer function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.addRenderer = function(sDates, fnRender) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.addRenderer(sDates, fnRender);
	}
};

/**
* Calls the addMonthRenderer function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.addMonthRenderer = function(month, fnRender) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.addMonthRenderer(month, fnRender);
	}
};

/**
* Calls the addWeekdayRenderer function of all child calendars within the group.
*/
YAHOO.widget.CalendarGroup.prototype.addWeekdayRenderer = function(weekday, fnRender) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal.addWeekdayRenderer(weekday, fnRender);
	}
};

/**
* Sets an event handler universally across all child calendars within the group. For instance,
* to set the onSelect handler for all child calendars to a function called fnSelect, the call would be:
* <code>
* calGroup.wireEvent("onSelect", fnSelect);
* </code>
* @param	{String}	eventName	The name of the event to handler to set within all child calendars.
* @param	{Function}	fn			The function to set into the specified event handler.
*/
YAHOO.widget.CalendarGroup.prototype.wireEvent = function(eventName, fn) {
	for (var p=0;p<this.pages.length;++p)
	{
		var cal = this.pages[p];
		cal[eventName] = fn;
	}
};

/**
* Returns a string representation of the object.
* @type string
*/ 
YAHOO.widget.CalendarGroup.prototype.toString = function() {
	return "CalendarGroup " + this.id;
}

YAHOO.widget.CalGrp = YAHOO.widget.CalendarGroup;/**
Copyright (c) 2006, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt 
**/

/**
* @class
* Calendar2up_Cal is the default implementation of the Calendar_Core base class, when used
* in a 2-up view. This class is the UED-approved version of the calendar selector widget. For all documentation
* on the implemented methods listed here, see the documentation for Calendar_Core. This class
* has some special attributes that only apply to calendars rendered within the calendar group implementation. 
* There should be no reason to instantiate this class directly.
* @constructor
* @param {String}	id			The id of the table element that will represent the calendar widget
* @param {String}	containerId	The id of the container element that will contain the calendar table
* @param {String}	monthyear	The month/year string used to set the current calendar page
* @param {String}	selected	A string of date values formatted using the date parser. The built-in
								default date format is MM/DD/YYYY. Ranges are defined using
								MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
								Any combination of these can be combined by delimiting the string with
								commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.Calendar2up_Cal = function(id, containerId, monthyear, selected) {
	if (arguments.length > 0)
	{
		this.init(id, containerId, monthyear, selected);
	}
}

YAHOO.widget.Calendar2up_Cal.prototype = new YAHOO.widget.Calendar_Core();

/**
* Renders the header for each individual calendar in the 2-up view. More
* specifically, this method handles the placement of left and right arrows for
* navigating between calendar pages.
*/
YAHOO.widget.Calendar2up_Cal.prototype.renderHeader = function() {
	this.headerCell.innerHTML = "";
	
	var headerContainer = document.createElement("DIV");
	headerContainer.className = this.Style.CSS_HEADER;
	
	if (this.index == 0) {

		if (this.linkLeft) {
			YAHOO.util.Event.removeListener(this.linkLeft, "mousedown", this.parent.doPreviousMonth);
		}
		this.linkLeft = document.createElement("A");
		this.linkLeft.innerHTML = "&nbsp;";
		this.linkLeft.style.backgroundImage =  "url(" + this.Options.NAV_ARROW_LEFT + ")";
		this.linkLeft.className = this.Style.CSS_NAV_LEFT;
		
		YAHOO.util.Event.addListener(this.linkLeft, "mousedown", this.parent.doPreviousMonth, this.parent);
		headerContainer.appendChild(this.linkLeft);
	}
	
	headerContainer.appendChild(document.createTextNode(this.buildMonthLabel()));
	
	if (this.index == 1) {

		if (this.linkRight) {
			YAHOO.util.Event.removeListener(this.linkRight, "mousedown", this.parent.doNextMonth);
		}
		this.linkRight = document.createElement("A");
		this.linkRight.innerHTML = "&nbsp;";
		this.linkRight.style.backgroundImage = "url(" + this.Options.NAV_ARROW_RIGHT + ")";
		this.linkRight.className = this.Style.CSS_NAV_RIGHT;

		YAHOO.util.Event.addListener(this.linkRight, "mousedown", this.parent.doNextMonth, this.parent);
		headerContainer.appendChild(this.linkRight);
	}
	
	this.headerCell.appendChild(headerContainer);
};




/**
* @class
* Calendar2up is the default implementation of the CalendarGroup base class, when used
* in a 2-up view. This class is the UED-approved version of the 2-up calendar selector widget. For all documentation
* on the implemented methods listed here, see the documentation for CalendarGroup. 
* @constructor
* @param {String}	id			The id of the table element that will represent the calendar widget
* @param {String}	containerId	The id of the container element that will contain the calendar table
* @param {String}	monthyear	The month/year string used to set the current calendar page
* @param {String}	selected	A string of date values formatted using the date parser. The built-in
								default date format is MM/DD/YYYY. Ranges are defined using
								MM/DD/YYYY-MM/DD/YYYY. Month/day combinations are defined using MM/DD.
								Any combination of these can be combined by delimiting the string with
								commas. Example: "12/24/2005,12/25,1/18/2006-1/21/2006"
*/
YAHOO.widget.Calendar2up = function(id, containerId, monthyear, selected) {
	if (arguments.length > 0)
	{	
		this.buildWrapper(containerId);
		this.init(2, id, containerId, monthyear, selected);
	}
}

YAHOO.widget.Calendar2up.prototype = new YAHOO.widget.CalendarGroup();

/**
* CSS class representing the wrapper for the 2-up calendar
* @type string
*/
YAHOO.widget.Calendar2up.CSS_2UPWRAPPER = "yui-cal2upwrapper";

/**
* CSS class representing the container for the calendar
* @type string
*/
YAHOO.widget.Calendar2up.CSS_CONTAINER = "yui-calcontainer";

/**
* CSS class representing the container for the 2-up calendar
* @type string
*/
YAHOO.widget.Calendar2up.CSS_2UPCONTAINER = "cal2up";

/**
* CSS class representing the title for the 2-up calendar
* @type string
*/
YAHOO.widget.Calendar2up.CSS_2UPTITLE = "title";

/**
* CSS class representing the close icon for the 2-up calendar
* @type string
*/
YAHOO.widget.Calendar2up.CSS_2UPCLOSE = "close-icon";

/**
* Implementation of CalendarGroup.constructChild that ensures that child calendars of 
* Calendar2up will be of type Calendar2up_Cal.
*/
YAHOO.widget.Calendar2up.prototype.constructChild = function(id,containerId,monthyear,selected) {
	var cal = new YAHOO.widget.Calendar2up_Cal(id,containerId,monthyear,selected);
	return cal;
};

/**
* Builds the wrapper container for the 2-up calendar.
* @param {String} containerId	The id of the outer container element.
*/
YAHOO.widget.Calendar2up.prototype.buildWrapper = function(containerId) {
	var outerContainer = document.getElementById(containerId);
	
	outerContainer.className = YAHOO.widget.Calendar2up.CSS_2UPWRAPPER;
	
	var innerContainer = document.createElement("DIV");
	innerContainer.className = YAHOO.widget.Calendar2up.CSS_CONTAINER;
	innerContainer.id = containerId + "_inner";
	
	var cal1Container = document.createElement("DIV");
	cal1Container.id = containerId + "_0";
	cal1Container.className = YAHOO.widget.Calendar2up.CSS_2UPCONTAINER;
	cal1Container.style.marginRight = "10px";
	
	var cal2Container = document.createElement("DIV");
	cal2Container.id = containerId + "_1"; 
	cal2Container.className = YAHOO.widget.Calendar2up.CSS_2UPCONTAINER;
	
	outerContainer.appendChild(innerContainer);
	innerContainer.appendChild(cal1Container);
	innerContainer.appendChild(cal2Container);
	
	this.innerContainer = innerContainer;
	this.outerContainer = outerContainer;
}

/**
* Renders the 2-up calendar.
*/
YAHOO.widget.Calendar2up.prototype.render = function() {
	this.renderHeader();
	YAHOO.widget.CalendarGroup.prototype.render.call(this);
	this.renderFooter();
};

/**
* Renders the header located at the top of the container for the 2-up calendar.
*/
YAHOO.widget.Calendar2up.prototype.renderHeader = function() {
	if (! this.title) {
		this.title = "";
	}
	if (! this.titleDiv)
	{
		this.titleDiv = document.createElement("DIV");
		if (this.title == "")
		{
			this.titleDiv.style.display="none";
		}
	}

	this.titleDiv.className = YAHOO.widget.Calendar2up.CSS_2UPTITLE;
	this.titleDiv.innerHTML = this.title;

	if (this.outerContainer.style.position == "absolute")
	{
		var linkClose = document.createElement("A");
		linkClose.href = "javascript:void(null)";
		YAHOO.util.Event.addListener(linkClose, "click", this.hide, this);

		var imgClose = document.createElement("IMG");
		imgClose.src = YAHOO.widget.Calendar_Core.IMG_ROOT + "us/my/bn/x_d.gif";
		imgClose.className = YAHOO.widget.Calendar2up.CSS_2UPCLOSE;

		linkClose.appendChild(imgClose);

		this.linkClose = linkClose;

		this.titleDiv.appendChild(linkClose);
	}

	this.innerContainer.insertBefore(this.titleDiv, this.innerContainer.firstChild);
}

/**
* Hides the 2-up calendar's outer container from view.
*/
YAHOO.widget.Calendar2up.prototype.hide = function(e, cal) {
	if (! cal)
	{
		cal = this;
	}
	cal.outerContainer.style.display = "none";
}

/**
* Renders a footer for the 2-up calendar container. By default, this method is
* unimplemented.
*/
YAHOO.widget.Calendar2up.prototype.renderFooter = function() {}

YAHOO.widget.Cal2up = YAHOO.widget.Calendar2up;
