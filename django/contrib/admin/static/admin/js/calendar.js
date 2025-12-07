/*global gettext, pgettext, get_format, quickElement, removeChildren*/
/*
calendar.js - Calendar functions by Adrian Holovaty
depends on core.js for utility functions like removeChildren or quickElement
*/
'use strict';
{
    // CalendarNamespace -- Provides a collection of HTML calendar-related helper functions
    const CalendarNamespace = {
        monthsOfYear: [
            gettext('January'),
            gettext('February'),
            gettext('March'),
            gettext('April'),
            gettext('May'),
            gettext('June'),
            gettext('July'),
            gettext('August'),
            gettext('September'),
            gettext('October'),
            gettext('November'),
            gettext('December')
        ],
        monthsOfYearAbbrev: [
            pgettext('abbrev. month January', 'Jan'),
            pgettext('abbrev. month February', 'Feb'),
            pgettext('abbrev. month March', 'Mar'),
            pgettext('abbrev. month April', 'Apr'),
            pgettext('abbrev. month May', 'May'),
            pgettext('abbrev. month June', 'Jun'),
            pgettext('abbrev. month July', 'Jul'),
            pgettext('abbrev. month August', 'Aug'),
            pgettext('abbrev. month September', 'Sep'),
            pgettext('abbrev. month October', 'Oct'),
            pgettext('abbrev. month November', 'Nov'),
            pgettext('abbrev. month December', 'Dec')
        ],
        daysOfWeek: [
            gettext('Sunday'),
            gettext('Monday'),
            gettext('Tuesday'),
            gettext('Wednesday'),
            gettext('Thursday'),
            gettext('Friday'),
            gettext('Saturday')
        ],
        daysOfWeekAbbrev: [
            pgettext('abbrev. day Sunday', 'Sun'),
            pgettext('abbrev. day Monday', 'Mon'),
            pgettext('abbrev. day Tuesday', 'Tue'),
            pgettext('abbrev. day Wednesday', 'Wed'),
            pgettext('abbrev. day Thursday', 'Thur'),
            pgettext('abbrev. day Friday', 'Fri'),
            pgettext('abbrev. day Saturday', 'Sat')
        ],
        daysOfWeekInitial: [
            pgettext('one letter Sunday', 'S'),
            pgettext('one letter Monday', 'M'),
            pgettext('one letter Tuesday', 'T'),
            pgettext('one letter Wednesday', 'W'),
            pgettext('one letter Thursday', 'T'),
            pgettext('one letter Friday', 'F'),
            pgettext('one letter Saturday', 'S')
        ],
        firstDayOfWeek: parseInt(get_format('FIRST_DAY_OF_WEEK')),
        isLeapYear: function(year) {
            return (((year % 4) === 0) && ((year % 100) !== 0 ) || ((year % 400) === 0));
        },
        getDaysInMonth: function(month, year) {
            let days;
            if (month === 1 || month === 3 || month === 5 || month === 7 || month === 8 || month === 10 || month === 12) {
                days = 31;
            }
            else if (month === 4 || month === 6 || month === 9 || month === 11) {
                days = 30;
            }
            else if (month === 2 && CalendarNamespace.isLeapYear(year)) {
                days = 29;
            }
            else {
                days = 28;
            }
            return days;
        },
        draw: function(month, year, div_id, callback, selected) { // month = 1-12, year = 1-9999
            const today = new Date();
            const todayDay = today.getDate();
            const todayMonth = today.getMonth() + 1;
            const todayYear = today.getFullYear();
            let todayClass = '';

            // Use UTC functions here because the date field does not contain time
            // and using the UTC function variants prevent the local time offset
            // from altering the date, specifically the day field.  For example:
            //
            // ```
            // var x = new Date('2013-10-02');
            // var day = x.getDate();
            // ```
            //
            // The day variable above will be 1 instead of 2 in, say, US Pacific time
            // zone.
            let isSelectedMonth = false;
            if (typeof selected !== 'undefined') {
                isSelectedMonth = (selected.getUTCFullYear() === year && (selected.getUTCMonth() + 1) === month);
            }

            month = parseInt(month);
            year = parseInt(year);
            const calDiv = document.getElementById(div_id);
            removeChildren(calDiv);
            const calTable = document.createElement('table');
            quickElement('caption', calTable, CalendarNamespace.monthsOfYear[month - 1] + ' ' + year);
            const tableBody = quickElement('tbody', calTable);

            // Draw days-of-week header
            let tableRow = quickElement('tr', tableBody);
            for (let i = 0; i < 7; i++) {
                quickElement('th', tableRow, CalendarNamespace.daysOfWeekInitial[(i + CalendarNamespace.firstDayOfWeek) % 7]);
            }

            const startingPos = new Date(year, month - 1, 1 - CalendarNamespace.firstDayOfWeek).getDay();
            const days = CalendarNamespace.getDaysInMonth(month, year);

            let nonDayCell;

            // Draw blanks before first of month
            tableRow = quickElement('tr', tableBody);
            for (let i = 0; i < startingPos; i++) {
                nonDayCell = quickElement('td', tableRow, ' ');
                nonDayCell.className = "nonday";
            }

            function calendarMonth(y, m) {
                function onClick(e) {
                    e.preventDefault();
                    callback(y, m, this.textContent);
                }
                return onClick;
            }

            // Draw days of month
            let currentDay = 1;
            for (let i = startingPos; currentDay <= days; i++) {
                if (i % 7 === 0 && currentDay !== 1) {
                    tableRow = quickElement('tr', tableBody);
                }
                if ((currentDay === todayDay) && (month === todayMonth) && (year === todayYear)) {
                    todayClass = 'today';
                } else {
                    todayClass = '';
                }

                // use UTC function; see above for explanation.
                if (isSelectedMonth && currentDay === selected.getUTCDate()) {
                    if (todayClass !== '') {
                        todayClass += " ";
                    }
                    todayClass += "selected";
                }

                const cell = quickElement('td', tableRow, '', 'class', todayClass);
                const link = quickElement('a', cell, currentDay, 'role', 'button', 'href', '#');
                link.addEventListener('click', calendarMonth(year, month));
                currentDay++;
            }

            // Draw blanks after end of month (optional, but makes for valid code)
            while (tableRow.childNodes.length < 7) {
                nonDayCell = quickElement('td', tableRow, ' ');
                nonDayCell.className = "nonday";
            }

            calDiv.appendChild(calTable);
        }
    };

    // Calendar -- A calendar instance
    function Calendar(div_id, callback, selected) {
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
        if (typeof selected !== 'undefined') {
            this.selected = selected;
        }
    }
    Calendar.prototype = {
        drawCurrent: function() {
            CalendarNamespace.draw(this.currentMonth, this.currentYear, this.div_id, this.callback, this.selected);
        },
        drawDate: function(month, year, selected) {
            this.currentMonth = month;
            this.currentYear = year;

            if(selected) {
                this.selected = selected;
            }

            this.drawCurrent();
        },
        drawPreviousMonth: function() {
            if (this.currentMonth === 1) {
                this.currentMonth = 12;
                this.currentYear--;
            }
            else {
                this.currentMonth--;
            }
            this.drawCurrent();
        },
        drawNextMonth: function() {
            if (this.currentMonth === 12) {
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
    };
    window.Calendar = Calendar;
    window.CalendarNamespace = CalendarNamespace;
}
