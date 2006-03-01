/* 'Magic' date parsing, by Simon Willison (6th October 2003)
   http://simon.incutio.com/archive/2003/10/06/betterDateInput
   Adapted for 6newslawrence.com, 28th January 2004
*/

/* Finds the index of the first occurence of item in the array, or -1 if not found */
if (typeof Array.prototype.indexOf == 'undefined') {
    Array.prototype.indexOf = function(item) {
        var len = this.length;
        for (var i = 0; i < len; i++) {
            if (this[i] == item) {
                return i;
            }
        }
        return -1;
    };
}
/* Returns an array of items judged 'true' by the passed in test function */
if (typeof Array.prototype.filter == 'undefined') {
    Array.prototype.filter = function(test) {
        var matches = [];
        var len = this.length;
        for (var i = 0; i < len; i++) {
            if (test(this[i])) {
                matches[matches.length] = this[i];
            }
        }
        return matches;
    };
}

var monthNames = gettext("January February March April May June July August September October November December").split(" ");
var weekdayNames = gettext("Sunday Monday Tuesday Wednesday Thursday Friday Saturday").split(" ");

/* Takes a string, returns the index of the month matching that string, throws
   an error if 0 or more than 1 matches
*/
function parseMonth(month) {
    var matches = monthNames.filter(function(item) { 
        return new RegExp("^" + month, "i").test(item);
    });
    if (matches.length == 0) {
        throw new Error("Invalid month string");
    }
    if (matches.length > 1) {
        throw new Error("Ambiguous month");
    }
    return monthNames.indexOf(matches[0]);
}
/* Same as parseMonth but for days of the week */
function parseWeekday(weekday) {
    var matches = weekdayNames.filter(function(item) {
        return new RegExp("^" + weekday, "i").test(item);
    });
    if (matches.length == 0) {
        throw new Error("Invalid day string");
    }
    if (matches.length > 1) {
        throw new Error("Ambiguous weekday");
    }
    return weekdayNames.indexOf(matches[0]);
}

/* Array of objects, each has 're', a regular expression and 'handler', a 
   function for creating a date from something that matches the regular 
   expression. Handlers may throw errors if string is unparseable. 
*/
var dateParsePatterns = [
    // Today
    {   re: /^tod/i,
        handler: function() { 
            return new Date();
        } 
    },
    // Tomorrow
    {   re: /^tom/i,
        handler: function() {
            var d = new Date(); 
            d.setDate(d.getDate() + 1); 
            return d;
        }
    },
    // Yesterday
    {   re: /^yes/i,
        handler: function() {
            var d = new Date();
            d.setDate(d.getDate() - 1);
            return d;
        }
    },
    // 4th
    {   re: /^(\d{1,2})(st|nd|rd|th)?$/i, 
        handler: function(bits) {
            var d = new Date();
            d.setDate(parseInt(bits[1], 10));
            return d;
        }
    },
    // 4th Jan
    {   re: /^(\d{1,2})(?:st|nd|rd|th)? (\w+)$/i, 
        handler: function(bits) {
            var d = new Date();
            d.setDate(parseInt(bits[1], 10));
            d.setMonth(parseMonth(bits[2]));
            return d;
        }
    },
    // 4th Jan 2003
    {   re: /^(\d{1,2})(?:st|nd|rd|th)? (\w+),? (\d{4})$/i,
        handler: function(bits) {
            var d = new Date();
            d.setDate(parseInt(bits[1], 10));
            d.setMonth(parseMonth(bits[2]));
            d.setYear(bits[3]);
            return d;
        }
    },
    // Jan 4th
    {   re: /^(\w+) (\d{1,2})(?:st|nd|rd|th)?$/i, 
        handler: function(bits) {
            var d = new Date();
            d.setDate(parseInt(bits[2], 10));
            d.setMonth(parseMonth(bits[1]));
            return d;
        }
    },
    // Jan 4th 2003
    {   re: /^(\w+) (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})$/i,
        handler: function(bits) {
            var d = new Date();
            d.setDate(parseInt(bits[2], 10));
            d.setMonth(parseMonth(bits[1]));
            d.setYear(bits[3]);
            return d;
        }
    },
    // next Tuesday - this is suspect due to weird meaning of "next"
    {   re: /^next (\w+)$/i,
        handler: function(bits) {
            var d = new Date();
            var day = d.getDay();
            var newDay = parseWeekday(bits[1]);
            var addDays = newDay - day;
            if (newDay <= day) {
                addDays += 7;
            }
            d.setDate(d.getDate() + addDays);
            return d;
        }
    },
    // last Tuesday
    {   re: /^last (\w+)$/i,
        handler: function(bits) {
            throw new Error("Not yet implemented");
        }
    },
    // mm/dd/yyyy (American style)
    {   re: /(\d{1,2})\/(\d{1,2})\/(\d{4})/,
        handler: function(bits) {
            var d = new Date();
            d.setYear(bits[3]);
            d.setDate(parseInt(bits[2], 10));
            d.setMonth(parseInt(bits[1], 10) - 1); // Because months indexed from 0
            return d;
        }
    },
    // yyyy-mm-dd (ISO style)
    {   re: /(\d{4})-(\d{1,2})-(\d{1,2})/,
        handler: function(bits) {
            var d = new Date();
            d.setYear(parseInt(bits[1]));
            d.setDate(parseInt(bits[3], 10));
            d.setMonth(parseInt(bits[2], 10) - 1);
            return d;
        }
    },
];

function parseDateString(s) {
    for (var i = 0; i < dateParsePatterns.length; i++) {
        var re = dateParsePatterns[i].re;
        var handler = dateParsePatterns[i].handler;
        var bits = re.exec(s);
        if (bits) {
            return handler(bits);
        }
    }
    throw new Error("Invalid date string");
}

function fmt00(x) {
    // fmt00: Tags leading zero onto numbers 0 - 9.
    // Particularly useful for displaying results from Date methods.
    //
    if (Math.abs(parseInt(x)) < 10){
        x = "0"+ Math.abs(x);
    }
    return x;
}

function parseDateStringISO(s) {
    try {
        var d = parseDateString(s);
        return d.getFullYear() + '-' + (fmt00(d.getMonth() + 1)) + '-' + fmt00(d.getDate())
    }
    catch (e) { return s; }
}
function magicDate(input) {
    var messagespan = input.id + 'Msg';
    try {
        var d = parseDateString(input.value);
        input.value = d.getFullYear() + '-' + (fmt00(d.getMonth() + 1)) + '-' + 
            fmt00(d.getDate());
        input.className = '';
        // Human readable date
        if (document.getElementById(messagespan)) {
            document.getElementById(messagespan).firstChild.nodeValue = d.toDateString();
            document.getElementById(messagespan).className = 'normal';
        }
    }
    catch (e) {
        input.className = 'error';
        var message = e.message;
        // Fix for IE6 bug
        if (message.indexOf('is null or not an object') > -1) {
            message = 'Invalid date string';
        }
        if (document.getElementById(messagespan)) {
            document.getElementById(messagespan).firstChild.nodeValue = message;
            document.getElementById(messagespan).className = 'error';
        }
    }
}
