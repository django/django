// Inserts shortcut buttons after all of the following:
//     <input type="text" class="vDateField">
//     <input type="text" class="vTimeField">

var DateTimeShortcuts = {
    calendars: [],
    calendarInputs: [],
    clockInputs: [],
    calendarDivName1: 'calendarbox', // name of calendar <div> that gets toggled
    calendarDivName2: 'calendarin',  // name of <div> that contains calendar
    clockDivName: 'clockbox',        // name of clock <div> that gets toggled
    admin_media_prefix: '',
    init: function() {
        // Deduce admin_media_prefix by looking at the <script>s in the
        // current document and finding the URL of *this* module.
        var scripts = document.getElementsByTagName('script');
        for (var i=0; i<scripts.length; i++) {
            if (scripts[i].src.match(/DateTimeShortcuts/)) {
                var idx = scripts[i].src.indexOf('js/admin/DateTimeShortcuts');
                DateTimeShortcuts.admin_media_prefix = scripts[i].src.substring(0, idx);
                break;
            }
        }

        var inputs = document.getElementsByTagName('input');
        for (i=0; i<inputs.length; i++) {
            var inp = inputs[i];
            if (inp.getAttribute('type') == 'text' && inp.className.match(/vTimeField/)) {
                DateTimeShortcuts.addClock(inp);
            }
            else if (inp.getAttribute('type') == 'text' && inp.className.match(/vDateField/)) {
                DateTimeShortcuts.addCalendar(inp);
            }
        }
    },
    // Add clock widget to a given field
    addClock: function(inp) {
        var num = DateTimeShortcuts.clockInputs.length;
        DateTimeShortcuts.clockInputs[num] = inp;

        // Shortcut links (clock icon and "Now" link)
        var shortcuts_span = document.createElement('span');
        inp.parentNode.insertBefore(shortcuts_span, inp.nextSibling);
        var now_link = document.createElement('a');
        now_link.setAttribute('href', "javascript:DateTimeShortcuts.handleClockQuicklink(" + num + ", new Date().getHourMinute());");
        now_link.appendChild(document.createTextNode('Now'));
        var clock_link = document.createElement('a');
        clock_link.setAttribute('href', 'javascript:DateTimeShortcuts.openClock(' + num + ');');
        quickElement('img', clock_link, '', 'src', DateTimeShortcuts.admin_media_prefix + 'img/admin/icon_clock.gif', 'alt', 'Clock');
        shortcuts_span.appendChild(document.createTextNode('\240'));
        shortcuts_span.appendChild(now_link);
        shortcuts_span.appendChild(document.createTextNode('\240|\240'));
        shortcuts_span.appendChild(clock_link);

        // Create clock link div
        //
        // Markup looks like:
        // <div id="clockbox1" class="clockbox module">
        //     <h2>Choose a time</h2>
        //     <ul class="timelist">
        //         <li><a href="#">Now</a></li>
        //         <li><a href="#">Midnight</a></li>
        //         <li><a href="#">6 a.m.</a></li>
        //         <li><a href="#">Noon</a></li>
        //     </ul>
        //     <p class="calendar-cancel"><a href="#">Cancel</a></p>
        // </div>

        var clock_box = document.createElement('div');
        clock_box.style.display = 'none';
        clock_box.style.position = 'absolute';
        clock_box.style.left = findPosX(clock_link) + 17 + 'px';
        clock_box.style.top = findPosY(clock_link) - 30 + 'px';
        clock_box.className = 'clockbox module';
        clock_box.setAttribute('id', DateTimeShortcuts.clockDivName + num);
        document.body.appendChild(clock_box);
        addEvent(clock_box, 'click', DateTimeShortcuts.cancelEventPropagation);

        quickElement('h2', clock_box, 'Choose a time');
        time_list = quickElement('ul', clock_box, '');
        time_list.className = 'timelist';
        quickElement("a", quickElement("li", time_list, ""), "Now", "href", "javascript:DateTimeShortcuts.handleClockQuicklink(" + num + ", new Date().getHourMinute());")
        quickElement("a", quickElement("li", time_list, ""), "Midnight", "href", "javascript:DateTimeShortcuts.handleClockQuicklink(" + num + ", '00:00');")
        quickElement("a", quickElement("li", time_list, ""), "6 a.m.", "href", "javascript:DateTimeShortcuts.handleClockQuicklink(" + num + ", '06:00');")
        quickElement("a", quickElement("li", time_list, ""), "Noon", "href", "javascript:DateTimeShortcuts.handleClockQuicklink(" + num + ", '12:00');")

        cancel_p = quickElement('p', clock_box, '');
        cancel_p.className = 'calendar-cancel';
        quickElement('a', cancel_p, 'Cancel', 'href', 'javascript:DateTimeShortcuts.dismissClock(' + num + ');');
    },
    openClock: function(num) {
        document.getElementById(DateTimeShortcuts.clockDivName + num).style.display = 'block';
        addEvent(window, 'click', function() { DateTimeShortcuts.dismissClock(num); return true; });
    },
    dismissClock: function(num) {
       document.getElementById(DateTimeShortcuts.clockDivName + num).style.display = 'none';
       window.onclick = null;
    },
    handleClockQuicklink: function(num, val) {
       DateTimeShortcuts.clockInputs[num].value = val;
       DateTimeShortcuts.dismissClock(num);
    },
    // Add calendar widget to a given field.
    addCalendar: function(inp) {
        var num = DateTimeShortcuts.calendars.length;

        DateTimeShortcuts.calendarInputs[num] = inp;

        // Shortcut links (calendar icon and "Today" link)
        var shortcuts_span = document.createElement('span');
        inp.parentNode.insertBefore(shortcuts_span, inp.nextSibling);
        var today_link = document.createElement('a');
        today_link.setAttribute('href', 'javascript:DateTimeShortcuts.handleCalendarQuickLink(' + num + ', 0);');
        today_link.appendChild(document.createTextNode('Today'));
        var cal_link = document.createElement('a');
        cal_link.setAttribute('href', 'javascript:DateTimeShortcuts.openCalendar(' + num + ');');
        quickElement('img', cal_link, '', 'src', DateTimeShortcuts.admin_media_prefix + 'img/admin/icon_calendar.gif', 'alt', 'Calendar');
        shortcuts_span.appendChild(document.createTextNode('\240'));
        shortcuts_span.appendChild(today_link);
        shortcuts_span.appendChild(document.createTextNode('\240|\240'));
        shortcuts_span.appendChild(cal_link);

        // Create calendarbox div.
        //
        // Markup looks like:
        //
        // <div id="calendarbox3" class="calendarbox module">
        //     <h2>
        //           <a href="#" class="link-previous">&lsaquo;</a>
        //           <a href="#" class="link-next">&rsaquo;</a> February 2003
        //     </h2>
        //     <div class="calendar" id="calendarin3">
        //         <!-- (cal) -->
        //     </div>
        //     <div class="calendar-shortcuts">
        //          <a href="#">Yesterday</a> | <a href="#">Today</a> | <a href="#">Tomorrow</a>
        //     </div>
        //     <p class="calendar-cancel"><a href="#">Cancel</a></p>
        // </div>
        var cal_box = document.createElement('div');
        cal_box.style.display = 'none';
        cal_box.style.position = 'absolute';
        cal_box.style.left = findPosX(cal_link) + 17 + 'px';
        cal_box.style.top = findPosY(cal_link) - 75 + 'px';
        cal_box.className = 'calendarbox module';
        cal_box.setAttribute('id', DateTimeShortcuts.calendarDivName1 + num);
        document.body.appendChild(cal_box);
        addEvent(cal_box, 'click', DateTimeShortcuts.cancelEventPropagation);

        // next-prev links
        var cal_nav = quickElement('div', cal_box, '');
        var cal_nav_prev = quickElement('a', cal_nav, '<', 'href', 'javascript:DateTimeShortcuts.drawPrev('+num+');');
        cal_nav_prev.className = 'calendarnav-previous';
        var cal_nav_next = quickElement('a', cal_nav, '>', 'href', 'javascript:DateTimeShortcuts.drawNext('+num+');');
        cal_nav_next.className = 'calendarnav-next';
        cal_box.appendChild(cal_nav);

        // main box
        var cal_main = quickElement('div', cal_box, '', 'id', DateTimeShortcuts.calendarDivName2 + num);
        cal_main.className = 'calendar';
        DateTimeShortcuts.calendars[num] = new Calendar(DateTimeShortcuts.calendarDivName2 + num, DateTimeShortcuts.handleCalendarCallback(num));
        DateTimeShortcuts.calendars[num].drawCurrent();

        // calendar shortcuts
        var shortcuts = quickElement('div', cal_box, '');
        shortcuts.className = 'calendar-shortcuts';
        quickElement('a', shortcuts, 'Yesterday', 'href', 'javascript:DateTimeShortcuts.handleCalendarQuickLink(' + num + ', -1);');
        shortcuts.appendChild(document.createTextNode('\240|\240'));
        quickElement('a', shortcuts, 'Today', 'href', 'javascript:DateTimeShortcuts.handleCalendarQuickLink(' + num + ', 0);');
        shortcuts.appendChild(document.createTextNode('\240|\240'));
        quickElement('a', shortcuts, 'Tomorrow', 'href', 'javascript:DateTimeShortcuts.handleCalendarQuickLink(' + num + ', +1);');

        // cancel bar
        var cancel_p = quickElement('p', cal_box, '');
        cancel_p.className = 'calendar-cancel';
        quickElement('a', cancel_p, 'Cancel', 'href', 'javascript:DateTimeShortcuts.dismissCalendar(' + num + ');');
    },
    openCalendar: function(num) {
        document.getElementById(DateTimeShortcuts.calendarDivName1+num).style.display = 'block';
        addEvent(window, 'click', function() { DateTimeShortcuts.dismissCalendar(num); return true; });
    },
    dismissCalendar: function(num) {
        document.getElementById(DateTimeShortcuts.calendarDivName1+num).style.display = 'none';
    },
    drawPrev: function(num) {
        DateTimeShortcuts.calendars[num].drawPreviousMonth();
    },
    drawNext: function(num) {
        DateTimeShortcuts.calendars[num].drawNextMonth();
    },
    handleCalendarCallback: function(num) {
        return "function(y, m, d) { DateTimeShortcuts.calendarInputs["+num+"].value = y+'-'+m+'-'+d; document.getElementById(DateTimeShortcuts.calendarDivName1+"+num+").style.display='none';}";
    },
    handleCalendarQuickLink: function(num, offset) {
       var d = new Date();
       d.setDate(d.getDate() + offset)
       DateTimeShortcuts.calendarInputs[num].value = d.getISODate();
       DateTimeShortcuts.dismissCalendar(num);
    },
    cancelEventPropagation: function(e) {
        if (!e) var e = window.event;
        e.cancelBubble = true;
        if (e.stopPropagation) e.stopPropagation();
    }
}

addEvent(window, 'load', DateTimeShortcuts.init);
