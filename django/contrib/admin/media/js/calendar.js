/*
calendar.js - Calendar functions by Adrian Holovaty
*/

function removeChildren(a) { // "a" is reference to an object
    while (a.hasChildNodes()) a.removeChild(a.lastChild);
}

// quickElement(tagType, parentReference, textInChildNode, [, attribute, attributeValue ...]);
function quickElement() {
    var obj = document.createElement(arguments[0]);
    if (arguments[2] != '' && arguments[2] != null) {
        var textNode = document.createTextNode(arguments[2]);
        obj.appendChild(textNode);
    }
    var len = arguments.length;
    for (var i = 3; i < len; i += 2) {
        obj.setAttribute(arguments[i], arguments[i+1]);
    }
    arguments[1].appendChild(obj);
    return obj;
}

// CalendarNamespace -- Provides a collection of HTML calendar-related helper functions
var CalendarNamespace = {
    monthsOfYear: gettext('January February March April May June July August September October November December').split(' '),
    daysOfWeek: gettext('S M T W T F S').split(' '),
    isLeapYear: function(year) {
        return (((year % 4)==0) && ((year % 100)!=0) || ((year % 400)==0));
    },
    getDaysInMonth: function(month,year) {
        var days;
        if (month==1 || month==3 || month==5 || month==7 || month==8 || month==10 || month==12) {
            days = 31;
        }
        else if (month==4 || month==6 || month==9 || month==11) {
            days = 30;
        }
        else if (month==2 && CalendarNamespace.isLeapYear(year)) {
            days = 29;
        }
        else {
            days = 28;
        }
        return days;
    },
    draw: function(month, year, div_id, callback) { // month = 1-12, year = 1-9999
        month = parseInt(month);
        year = parseInt(year);
        var calDiv = document.getElementById(div_id);
        removeChildren(calDiv);
        var calTable = document.createElement('table');
        quickElement('caption', calTable, CalendarNamespace.monthsOfYear[month-1] + ' ' + year);
        var tableBody = quickElement('tbody', calTable);

        // Draw days-of-week header
        var tableRow = quickElement('tr', tableBody);
        for (var i = 0; i < 7; i++) {
            quickElement('th', tableRow, CalendarNamespace.daysOfWeek[i]);
        }

        var startingPos = new Date(year, month-1, 1).getDay();
        var days = CalendarNamespace.getDaysInMonth(month, year);

        // Draw blanks before first of month
        tableRow = quickElement('tr', tableBody);
        for (var i = 0; i < startingPos; i++) {
            var _cell = quickElement('td', tableRow, ' ');
            _cell.style.backgroundColor = '#f3f3f3';
        }

        // Draw days of month
        var currentDay = 1;
        for (var i = startingPos; currentDay <= days; i++) {
            if (i%7 == 0 && currentDay != 1) {
                tableRow = quickElement('tr', tableBody);
            }
            var cell = quickElement('td', tableRow, '');
            quickElement('a', cell, currentDay, 'href', 'javascript:void(' + callback + '('+year+','+month+','+currentDay+'));');
            currentDay++;
        }

        // Draw blanks after end of month (optional, but makes for valid code)
        while (tableRow.childNodes.length < 7) {
            var _cell = quickElement('td', tableRow, ' ');
            _cell.style.backgroundColor = '#f3f3f3';
        }

        calDiv.appendChild(calTable);
    }
}

// Calendar -- A calendar instance
function Calendar(div_id, callback) {
    // div_id (string) is the ID of the element in which the calendar will
    //     be displayed
    // callback (string) is the name of a JavaScript function that will be
    //     called with the parameters (year, month, day) when a day in the
    //     calendar is clicked
    this.div_id = div_id;
    this.callback = callback;
    this.today = new Date();
    this.currentMonth = this.today.getMonth() + 1;
    this.currentYear = this.today.getFullYear();
}
Calendar.prototype = {
    drawCurrent: function() {
        CalendarNamespace.draw(this.currentMonth, this.currentYear, this.div_id, this.callback);
    },
    drawDate: function(month, year) {
        this.currentMonth = month;
        this.currentYear = year;
        this.drawCurrent();
    },
    drawPreviousMonth: function() {
        if (this.currentMonth == 1) {
            this.currentMonth = 12;
            this.currentYear--;
        }
        else {
            this.currentMonth--;
        }
        this.drawCurrent();
    },
    drawNextMonth: function() {
        if (this.currentMonth == 12) {
            this.currentMonth = 1;
            this.currentYear++;
        }
        else {
            this.currentMonth++;
        }
        this.drawCurrent();
    },
    drawPreviousYear: function() {
        this.currentYear--;
        this.drawCurrent();
    },
    drawNextYear: function() {
        this.currentYear++;
        this.drawCurrent();
    }
}
