/*global Calendar, CalendarNamespace, findPosX, findPosY, get_format, gettext, gettext_noop, interpolate, ngettext, quickElement*/
// Inserts shortcut buttons after all of the following:
//     <input type="text" class="vDateField">
//     <input type="text" class="vTimeField">
"use strict";
{
    const DateTimeShortcuts = {
        calendars: [],
        calendarInputs: [],
        clockInputs: [],
        clockHours: {
            default_: [
                [gettext_noop("Now"), -1],
                [gettext_noop("Midnight"), 0],
                [gettext_noop("6 a.m."), 6],
                [gettext_noop("Noon"), 12],
                [gettext_noop("6 p.m."), 18],
            ],
        },
        dismissClockFunc: [],
        dismissCalendarFunc: [],
        calendarDivName1: "calendarbox", // name of calendar <div> that gets toggled
        calendarDivName2: "calendarin", // name of <div> that contains calendar
        calendarLinkName: "calendarlink", // name of the link that is used to toggle
        clockDivName: "clockbox", // name of clock <div> that gets toggled
        clockLinkName: "clocklink", // name of the link that is used to toggle
        shortCutsClass: "datetimeshortcuts", // class of the clock and cal shortcuts
        timezoneWarningClass: "timezonewarning", // class of the warning for timezone mismatch
        timezoneOffset: 0,
        init: function () {
            const serverOffset = document.body.dataset.adminUtcOffset;
            if (serverOffset) {
                const localOffset = new Date().getTimezoneOffset() * -60;
                DateTimeShortcuts.timezoneOffset = localOffset - serverOffset;
            }

            for (const inp of document.getElementsByTagName("input")) {
                if (
                    inp.type === "text" &&
                    inp.classList.contains("vTimeField")
                ) {
                    DateTimeShortcuts.addClock(inp);
                    DateTimeShortcuts.addTimezoneWarning(inp);
                } else if (
                    inp.type === "text" &&
                    inp.classList.contains("vDateField")
                ) {
                    DateTimeShortcuts.addCalendar(inp);
                    DateTimeShortcuts.addTimezoneWarning(inp);
                }
            }
        },
        // Return the current time while accounting for the server timezone.
        now: function () {
            const serverOffset = document.body.dataset.adminUtcOffset;
            if (serverOffset) {
                const localNow = new Date();
                const localOffset = localNow.getTimezoneOffset() * -60;
                localNow.setTime(
                    localNow.getTime() + 1000 * (serverOffset - localOffset),
                );
                return localNow;
            } else {
                return new Date();
            }
        },
        // Add a warning when the time zone in the browser and backend do not match.
        addTimezoneWarning: function (inp) {
            const warningClass = DateTimeShortcuts.timezoneWarningClass;
            let timezoneOffset = DateTimeShortcuts.timezoneOffset / 3600;

            // Only warn if there is a time zone mismatch.
            if (!timezoneOffset) {
                return;
            }

            // Check if warning is already there.
            if (
                inp.parentNode.parentNode.querySelectorAll("." + warningClass)
                    .length
            ) {
                return;
            }

            const serverTimezone =
                document.body.dataset.adminServerTimezone || gettext("server");
            let message;
            if (timezoneOffset > 0) {
                message = ngettext(
                    "Note: Enter times in the %(timezone)s timezone. " +
                        "(You are %(offset)s hour ahead.)",
                    "Note: Enter times in the %(timezone)s timezone. " +
                        "(You are %(offset)s hours ahead.)",
                    timezoneOffset,
                );
            } else {
                timezoneOffset *= -1;
                message = ngettext(
                    "Note: Enter times in the %(timezone)s timezone. " +
                        "(You are %(offset)s hour behind.)",
                    "Note: Enter times in the %(timezone)s timezone. " +
                        "(You are %(offset)s hours behind.)",
                    timezoneOffset,
                );
            }
            message = interpolate(
                message,
                { timezone: serverTimezone, offset: timezoneOffset },
                true,
            );

            const warning = document.createElement("div");
            const id = inp.id;
            const field_id = inp.closest("p.datetime")
                ? id.slice(0, id.lastIndexOf("_"))
                : id;
            warning.classList.add("help", warningClass);
            warning.id = `${field_id}_timezone_warning_helptext`;
            warning.textContent = message;
            const errorList =
                inp.parentNode.parentNode.querySelector("ul.errorlist");
            if (errorList) {
                errorList.before(warning);
            } else {
                inp.parentNode.before(warning);
            }
        },
        // Add clock widget to a given field
        addClock: function (inp) {
            const num = DateTimeShortcuts.clockInputs.length;
            DateTimeShortcuts.clockInputs[num] = inp;
            DateTimeShortcuts.dismissClockFunc[num] = function () {
                DateTimeShortcuts.dismissClock(num);
                return true;
            };

            // Shortcut links (clock icon and "Now" link)
            const shortcuts_span = document.createElement("span");
            shortcuts_span.className = DateTimeShortcuts.shortCutsClass;
            inp.parentNode.insertBefore(shortcuts_span, inp.nextSibling);
            const now_link = document.createElement("a");
            now_link.href = "#";
            now_link.textContent = gettext("Now");
            now_link.role = "button";
            now_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.handleClockQuicklink(num, -1);
            });
            const clock_link = document.createElement("a");
            clock_link.href = "#";
            clock_link.id = DateTimeShortcuts.clockLinkName + num;
            clock_link.addEventListener("click", function (e) {
                e.preventDefault();
                // avoid triggering the document click handler to dismiss the clock
                e.stopPropagation();
                DateTimeShortcuts.openClock(num);
            });

            const clockIconId = DateTimeShortcuts.clockLinkName + num + "_icon";
            quickElement(
                "span",
                clock_link,
                "",
                "id",
                clockIconId,
                "class",
                "clock-icon",
                "title",
                gettext("Choose a Time"),
            );
            clock_link.setAttribute("aria-labelledby", clockIconId);
            shortcuts_span.appendChild(document.createTextNode("\u00A0"));
            shortcuts_span.appendChild(now_link);
            shortcuts_span.appendChild(
                document.createTextNode("\u00A0|\u00A0"),
            );
            shortcuts_span.appendChild(clock_link);

            // Create clock link div
            //
            // Markup looks like:
            // <div id="clockbox1" class="clockbox module" role="dialog"
            //     aria-label="Choose a time">
            //     <h2>Choose a time</h2>
            //     <ul class="timelist">
            //         <li><a href="#" role="button">Now</a></li>
            //         <li><a href="#" role="button">Midnight</a></li>
            //         <li><a href="#" role="button">6 a.m.</a></li>
            //         <li><a href="#" role="button">Noon</a></li>
            //         <li><a href="#" role="button">6 p.m.</a></li>
            //     </ul>
            //     <p class="calendar-cancel">
            //         <a href="#" role="button" aria-label="Close Clock">Cancel</a>
            //     </p>
            // </div>

            const clock_box = document.createElement("div");
            clock_box.style.display = "none";
            clock_box.style.position = "absolute";
            clock_box.className = "clockbox module";
            clock_box.id = DateTimeShortcuts.clockDivName + num;
            clock_box.setAttribute("role", "dialog");
            clock_box.setAttribute("aria-labelledby", clockIconId);
            document.body.appendChild(clock_box);
            clock_box.addEventListener("click", function (e) {
                e.stopPropagation();
            });

            quickElement("h2", clock_box, gettext("Choose a time"));
            const time_list = quickElement("ul", clock_box);
            time_list.className = "timelist";
            // The list of choices can be overridden in JavaScript like this:
            // DateTimeShortcuts.clockHours.name = [['3 a.m.', 3]];
            // where name is the name attribute of the <input>.
            const name =
                typeof DateTimeShortcuts.clockHours[inp.name] === "undefined"
                    ? "default_"
                    : inp.name;
            DateTimeShortcuts.clockHours[name].forEach(function (element) {
                const time_link = quickElement(
                    "a",
                    quickElement("li", time_list),
                    gettext(element[0]),
                    "role",
                    "button",
                    "href",
                    "#",
                );
                time_link.addEventListener("click", function (e) {
                    e.preventDefault();
                    DateTimeShortcuts.handleClockQuicklink(num, element[1]);
                });
            });

            const cancel_p = quickElement("p", clock_box);
            cancel_p.className = "calendar-cancel";
            const cancel_link = quickElement(
                "a",
                cancel_p,
                gettext("Cancel"),
                "role",
                "button",
                "href",
                "#",
            );
            cancel_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.dismissClock(num);
            });

            document.addEventListener("keyup", function (event) {
                if (event.which === 27) {
                    // ESC key closes popup
                    DateTimeShortcuts.dismissClock(num);
                    event.preventDefault();
                }
            });
        },
        openClock: function (num) {
            const clock_box = document.getElementById(
                DateTimeShortcuts.clockDivName + num,
            );
            const clock_link = document.getElementById(
                DateTimeShortcuts.clockLinkName + num,
            );

            // Recalculate the clockbox position
            // is it left-to-right or right-to-left layout ?
            if (window.getComputedStyle(document.body).direction !== "rtl") {
                clock_box.style.left = findPosX(clock_link) + 17 + "px";
            } else {
                // since style's width is in em, it'd be tough to calculate
                // px value of it. let's use an estimated px for now
                clock_box.style.left = findPosX(clock_link) - 110 + "px";
            }
            clock_box.style.top = Math.max(0, findPosY(clock_link) - 30) + "px";

            // Show the clock box
            clock_box.style.display = "block";
            document.addEventListener(
                "click",
                DateTimeShortcuts.dismissClockFunc[num],
            );
        },
        dismissClock: function (num) {
            document.getElementById(
                DateTimeShortcuts.clockDivName + num,
            ).style.display = "none";
            document.removeEventListener(
                "click",
                DateTimeShortcuts.dismissClockFunc[num],
            );
        },
        handleClockQuicklink: function (num, val) {
            let d;
            if (val === -1) {
                d = DateTimeShortcuts.now();
            } else {
                d = new Date(1970, 1, 1, val, 0, 0, 0);
            }
            DateTimeShortcuts.clockInputs[num].value = d.strftime(
                get_format("TIME_INPUT_FORMATS")[0],
            );
            DateTimeShortcuts.clockInputs[num].focus();
            DateTimeShortcuts.dismissClock(num);
        },
        // Add calendar widget to a given field.
        addCalendar: function (inp) {
            const num = DateTimeShortcuts.calendars.length;

            DateTimeShortcuts.calendarInputs[num] = inp;
            DateTimeShortcuts.dismissCalendarFunc[num] = function () {
                DateTimeShortcuts.dismissCalendar(num);
                return true;
            };

            function getFormattedDate(offset) {
                const d = DateTimeShortcuts.now();
                d.setDate(d.getDate() + offset);
                return CalendarNamespace.formatDate(
                    d.getDate(),
                    d.getMonth() + 1,
                    d.getFullYear(),
                );
            }
            // Shortcut links (calendar icon and "Today" link)
            const shortcuts_span = document.createElement("span");
            shortcuts_span.className = DateTimeShortcuts.shortCutsClass;
            inp.parentNode.insertBefore(shortcuts_span, inp.nextSibling);
            const today_link = document.createElement("a");
            today_link.href = "#";
            today_link.role = "button";
            today_link.appendChild(document.createTextNode(gettext("Today")));
            today_link.setAttribute(
                "aria-label",
                interpolate(
                    gettext("Today (%(date)s)"),
                    { date: getFormattedDate(0) },
                    true,
                ),
            );
            today_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.handleCalendarQuickLink(num, 0);
            });
            const cal_link = document.createElement("a");
            cal_link.href = "#";
            cal_link.id = DateTimeShortcuts.calendarLinkName + num;
            cal_link.addEventListener("click", function (e) {
                e.preventDefault();
                // avoid triggering the document click handler to dismiss the calendar
                e.stopPropagation();
                DateTimeShortcuts.openCalendar(num);
            });
            const calIconId =
                DateTimeShortcuts.calendarLinkName + num + "_icon";
            quickElement(
                "span",
                cal_link,
                "",
                "id",
                calIconId,
                "class",
                "date-icon",
                "title",
                gettext("Choose a Date"),
            );
            cal_link.setAttribute("aria-labelledby", calIconId);
            shortcuts_span.appendChild(document.createTextNode("\u00A0"));
            shortcuts_span.appendChild(today_link);
            shortcuts_span.appendChild(
                document.createTextNode("\u00A0|\u00A0"),
            );
            shortcuts_span.appendChild(cal_link);

            // Create calendarbox div.
            //
            // Markup looks like:
            //
            // <div id="calendarbox3" class="calendarbox module"
            //      role="dialog" aria-label="Choose a Date">
            //     <div>
            //         <a href="#" class="calendarnav-previous"
            //            aria-label="Previous May">&lsaquo;</a>
            //         <a href="#" class="calendarnav-next"
            //            aria-label="Next July">&rsaquo;</a>
            //     </div>
            //     <div class="calendar" id="calendarin3">
            //         <!-- (cal) -->
            //     </div>
            //     <div class="calendar-shortcuts">
            //         <a href="#" role="button"
            //            aria-label="Yesterday (June 14, 2025)">Yesterday</a>
            //         |
            //         <a href="#" role="button"
            //            aria-label="Today (June 15, 2025)">Today</a>
            //         |
            //         <a href="#" role="button"
            //            aria-label="Tomorrow (June 16, 2025)">Tomorrow</a>
            //     </div>
            //     <p class="calendar-cancel">
            //         <a href="#" role="button" aria-label="Close Calendar">Cancel</a>
            //     </p>
            // </div>
            const cal_box = document.createElement("div");
            cal_box.style.display = "none";
            cal_box.style.position = "absolute";
            cal_box.className = "calendarbox module";
            cal_box.id = DateTimeShortcuts.calendarDivName1 + num;
            cal_box.setAttribute("role", "dialog");
            cal_box.setAttribute("aria-labelledby", calIconId);
            document.body.appendChild(cal_box);
            cal_box.addEventListener("click", function (e) {
                e.stopPropagation();
            });

            // next-prev links
            const cal_nav = quickElement("div", cal_box);
            const cal_nav_prev = quickElement("a", cal_nav, "<", "href", "#");
            cal_nav_prev.className = "calendarnav-previous";
            cal_nav_prev.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.drawPrev(num);
            });

            const cal_nav_next = quickElement("a", cal_nav, ">", "href", "#");
            cal_nav_next.className = "calendarnav-next";
            cal_nav_next.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.drawNext(num);
            });

            // main box
            const cal_main = quickElement(
                "div",
                cal_box,
                "",
                "id",
                DateTimeShortcuts.calendarDivName2 + num,
            );
            cal_main.className = "calendar";
            DateTimeShortcuts.calendars[num] = new Calendar(
                DateTimeShortcuts.calendarDivName2 + num,
                DateTimeShortcuts.handleCalendarCallback(num),
            );
            DateTimeShortcuts.calendars[num].drawCurrent();

            // calendar shortcuts
            const shortcuts = quickElement("div", cal_box);
            shortcuts.className = "calendar-shortcuts";
            let day_link = quickElement(
                "a",
                shortcuts,
                gettext("Yesterday"),
                "role",
                "button",
                "href",
                "#",
            );
            day_link.setAttribute(
                "aria-label",
                interpolate(
                    gettext("Yesterday (%(date)s)"),
                    { date: getFormattedDate(-1) },
                    true,
                ),
            );
            day_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.handleCalendarQuickLink(num, -1);
            });
            shortcuts.appendChild(document.createTextNode("\u00A0|\u00A0"));
            day_link = quickElement(
                "a",
                shortcuts,
                gettext("Today"),
                "role",
                "button",
                "href",
                "#",
            );
            day_link.setAttribute(
                "aria-label",
                interpolate(
                    gettext("Today (%(date)s)"),
                    { date: getFormattedDate(0) },
                    true,
                ),
            );
            day_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.handleCalendarQuickLink(num, 0);
            });
            shortcuts.appendChild(document.createTextNode("\u00A0|\u00A0"));
            day_link = quickElement(
                "a",
                shortcuts,
                gettext("Tomorrow"),
                "role",
                "button",
                "href",
                "#",
            );
            day_link.setAttribute(
                "aria-label",
                interpolate(
                    gettext("Tomorrow (%(date)s)"),
                    { date: getFormattedDate(1) },
                    true,
                ),
            );
            day_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.handleCalendarQuickLink(num, +1);
            });

            // cancel bar
            const cancel_p = quickElement("p", cal_box);
            cancel_p.className = "calendar-cancel";
            const cancel_link = quickElement(
                "a",
                cancel_p,
                gettext("Cancel"),
                "role",
                "button",
                "href",
                "#",
            );
            cancel_link.addEventListener("click", function (e) {
                e.preventDefault();
                DateTimeShortcuts.dismissCalendar(num);
            });
            document.addEventListener("keyup", function (event) {
                if (event.which === 27) {
                    // ESC key closes popup
                    DateTimeShortcuts.dismissCalendar(num);
                    event.preventDefault();
                }
            });
        },
        updateNavAriaLabels: function (num) {
            const cal = DateTimeShortcuts.calendars[num];
            const cal_box = document.getElementById(
                DateTimeShortcuts.calendarDivName1 + num,
            );
            const prevMonth =
                CalendarNamespace.monthsOfYear[(cal.currentMonth + 10) % 12];
            const prevYear =
                cal.currentMonth === 1 ? cal.currentYear - 1 : cal.currentYear;
            cal_box
                .querySelector(".calendarnav-previous")
                .setAttribute(
                    "aria-label",
                    interpolate(
                        gettext("Previous (%(month)s %(year)s)"),
                        { month: prevMonth, year: prevYear },
                        true,
                    ),
                );

            const nextMonth =
                CalendarNamespace.monthsOfYear[cal.currentMonth % 12];
            const nextYear =
                cal.currentMonth === 12 ? cal.currentYear + 1 : cal.currentYear;
            cal_box
                .querySelector(".calendarnav-next")
                .setAttribute(
                    "aria-label",
                    interpolate(
                        gettext("Next (%(month)s %(year)s)"),
                        { month: nextMonth, year: nextYear },
                        true,
                    ),
                );
        },
        openCalendar: function (num) {
            const cal_box = document.getElementById(
                DateTimeShortcuts.calendarDivName1 + num,
            );
            const cal_link = document.getElementById(
                DateTimeShortcuts.calendarLinkName + num,
            );
            const inp = DateTimeShortcuts.calendarInputs[num];

            // Determine if the current value in the input has a valid date.
            // If so, draw the calendar with that date's year and month.
            if (inp.value) {
                const format = get_format("DATE_INPUT_FORMATS")[0];
                const selected = inp.value.strptime(format);
                const year = selected.getUTCFullYear();
                const month = selected.getUTCMonth() + 1;
                const re = /\d{4}/;
                if (re.test(year.toString()) && month >= 1 && month <= 12) {
                    DateTimeShortcuts.calendars[num].drawDate(
                        month,
                        year,
                        selected,
                    );
                }
            }

            // Recalculate the clockbox position
            // is it left-to-right or right-to-left layout ?
            if (window.getComputedStyle(document.body).direction !== "rtl") {
                cal_box.style.left = findPosX(cal_link) + 17 + "px";
            } else {
                // since style's width is in em, it'd be tough to calculate
                // px value of it. let's use an estimated px for now
                cal_box.style.left = findPosX(cal_link) - 180 + "px";
            }
            cal_box.style.top = Math.max(0, findPosY(cal_link) - 75) + "px";

            cal_box.style.display = "block";
            DateTimeShortcuts.updateNavAriaLabels(num);
            document.addEventListener(
                "click",
                DateTimeShortcuts.dismissCalendarFunc[num],
            );
        },
        dismissCalendar: function (num) {
            document.getElementById(
                DateTimeShortcuts.calendarDivName1 + num,
            ).style.display = "none";
            document.removeEventListener(
                "click",
                DateTimeShortcuts.dismissCalendarFunc[num],
            );
        },
        drawPrev: function (num) {
            DateTimeShortcuts.calendars[num].drawPreviousMonth();
            DateTimeShortcuts.updateNavAriaLabels(num);
        },
        drawNext: function (num) {
            DateTimeShortcuts.calendars[num].drawNextMonth();
            DateTimeShortcuts.updateNavAriaLabels(num);
        },
        handleCalendarCallback: function (num) {
            const format = get_format("DATE_INPUT_FORMATS")[0];
            return function (y, m, d) {
                DateTimeShortcuts.calendarInputs[num].value = new Date(
                    y,
                    m - 1,
                    d,
                ).strftime(format);
                DateTimeShortcuts.calendarInputs[num].focus();
                DateTimeShortcuts.dismissCalendar(num);
            };
        },
        handleCalendarQuickLink: function (num, offset) {
            const d = DateTimeShortcuts.now();
            d.setDate(d.getDate() + offset);
            DateTimeShortcuts.calendarInputs[num].value = d.strftime(
                get_format("DATE_INPUT_FORMATS")[0],
            );
            DateTimeShortcuts.calendarInputs[num].focus();
            DateTimeShortcuts.dismissCalendar(num);
        },
    };

    window.addEventListener("load", DateTimeShortcuts.init);
    window.DateTimeShortcuts = DateTimeShortcuts;
}
