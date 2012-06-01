/**
 * Django admin DateTime shortcuts
 *
 * @requires jQuery 1.4.2 or later
 *
 * DateTimeShortcuts
 * -----------------
 *
 * Inserts shortcut buttons (clock and calendar) after all input:text fields
 * having the classes .vDateField and .vTimeField.
 *
 * The $("selector").datetimeshortcuts() plugin is intended to be applied on
 * fieldsets or whole forms which contain, or may later contain (inline
 * fieldsets) date or time fields.
 *
 * All options as defined in datetimeshortcuts.defaults can be overwritten by
 * passing them as array to the datetimeshortcuts() method.
 *
 */

(function($) {

    $.fn.datetimeshortcuts = function(options) {
        // variables set in base.html
        var datetimeshortcuts_defaults = $('body').data('datetimeshortcuts_defaults');

        // extend default settings with user options
        var o = $.extend({
                admin_media_prefix: $('body').data('admin_media_prefix')
            },
            $.fn.datetimeshortcuts.defaults,
            datetimeshortcuts_defaults,
            options);

        // Check admin_media_prefix setting:
        // usually set in admin/base.html template, but if that was overridden,
        // it might be missing. Set it to something clearly invalid so that
        // somebody might notice it.
        if (o.admin_media_prefix === undefined) {
            o.admin_media_prefix = '/missing-admin-media-prefix/';
        }


        /* --- utitity functions ------------------------------------------- */

        // month names
        var month_names = gettext('January February March April May June July August September October November December').split(' ');

        // weekday names
        var weekdays = gettext('S M T W T F S').split(' ');

        // first day of week
        var first_day_of_week = parseInt(get_format('FIRST_DAY_OF_WEEK'), 10);

        // find leap years
        var is_leap_year = function(year) {
            return new Date(year, 1, 29).getDate() == 29;
        };

        // number of days in month
        var get_days_in_month = function(year, month) {
            return 32 - new Date(year, month, 32).getDate();
        };


        /* --- initialization functions ------------------------------------ */

        // add shortcuts for date fields
        var add_calendar = function(element) {
            // insert span.datetimeshortcuts
            var shortcuts = $('<span class="'+o.class_shortcuts+'">').insertAfter(element);

            // insert today link
            if (o.enable_today) {
                shortcuts.append(' <a href="#" class="'+o.class_today+'">'+gettext('Today')+'</a>');
                if (o.enable_calendar) {
                    shortcuts.append(" | ");
                }
            }

            // insert calendar link
            if (o.enable_calendar) {
                $('<a href="#" class="'+o.class_calendar+'"></a>')
                    .appendTo(shortcuts)
                    .append('<img src="'+o.admin_media_prefix + 'img/icon_calendar.gif" alt="'+gettext('Calendar')+'" />');
            }
        };

        // add shortcuts for time fields
        var add_clock = function(element) {
            // insert span.datetimeshortcuts
            var shortcuts = $('<span class="'+o.class_shortcuts+'">').insertAfter(element);

            // insert now link
            if (o.enable_now) {
                shortcuts.append(' <a href="#" class="'+o.class_now+'">'+gettext('Now')+'</a>');
                if (o.enable_clock) {
                    shortcuts.append(" | ");
                }
            }

            // insert clock link
            if (o.enable_clock) {
                $('<a href="#" class="'+o.class_clock+'"></a>')
                    .appendTo(shortcuts)
                    .append('<img src="'+o.admin_media_prefix + 'img/icon_clock.gif" alt="'+gettext('Clock')+'" />');
            }
        };

        // draw a month calendar table
        var draw_calendar_table = function(selected, show) {
            var y_sel, m_sel, d_sel;
            // selected date (optional)
            if (selected !== null) {
                y_sel = selected.getFullYear();
                m_sel = selected.getMonth();
                d_sel = selected.getDate();
            }
            // month to show
            var y_show = show.getFullYear();
            var m_show = show.getMonth();
            // today
            var today = new Date();
            var y_tod = today.getFullYear();
            var m_tod = today.getMonth();
            var d_tod = today.getDate();

            // create table
            var cal = $('<table><caption>'+month_names[m_show]+' '+y_show+'</caption></table>');

            // add day-of-week headers
            var row = $('<tr>').appendTo(cal);
            for (var i = 0; i < 7; i++) {
                row.append('<th>'+weekdays[(i + first_day_of_week) % 7]+'</th>');
            }

            var start = new Date(y_show, m_show, 1 - first_day_of_week).getDay();
            var days = get_days_in_month(y_show, m_show);

            // draw blanks before 1st of month
            row = $('<tr>').appendTo(cal);
            for (i = 0; i < start; i++) {
                $('<td> </td>').appendTo(row).addClass('nonday');
            }

            // draw month days
            var current = 1;
            for (i = start; current <= days; i++) {
                if (i % 7 === 0 && current != 1) {
                    row = $('<tr>').appendTo(cal);
                }
                var today_class = '';
                // mark today
                if ((current == d_tod) && (m_show == m_tod) && (y_show == y_tod)) {
                    today_class = 'today';
                }
                // mark selected day
                if ((current == d_sel) && (m_show == m_sel) && (y_show == y_sel)) {
                    today_class = 'selected';
                }
                $('<td>').appendTo(row)
                    .addClass(today_class)
                    .append('<a href="#">'+current+'</a>')
                    .find('a')
                    .data('date', new Date(y_show, m_show, current++));
            }

            // draw blanks after last of month
            while(row.children('td').length < 7) {
                $('<td> </td>').appendTo(row).addClass('nonday');
            }

            return cal;
        };

        // init one calendar per fieldset
        var init_calendar_box = function(fieldset) {
            // insert calendar box if not there
            if (fieldset.find('.'+o.class_calendarbox).length === 0) {

                $('<div class="'+o.class_calendarbox+' module">'  +
                    '  <div>'+
                    '    <a href="#" class="calendarnav-previous"><</a>' +
                    '    <a href="#" class="calendarnav-next">></a>' +
                    '  </div>' +
                    '  <div class="calendar_table calendar"></div>' +
                    '  <div class="calendar-shortcuts">'+
                    '    <a href="#" class="'+o.class_today+' yesterday">'+gettext('Yesterday')+'</a> | <a href="#" class="'+o.class_today+'">'+gettext('Today')+'</a> | <a href="#" class="'+o.class_today+' tomorrow">'+gettext('Tomorrow')+'</a>' +
                    '  </div>' +
                    '  <p class="calendar-cancel"><a href="#">'+gettext('Cancel')+'</p>' +
                    '</div>')
                    .appendTo(fieldset).css('position', 'absolute').hide();

                // prev/next event handlers
                fieldset.find('.'+o.class_calendarbox)
                    .delegate('.calendarnav-previous, .calendarnav-next',
                              'click', function(event) {
                        var func = $(this).is('.calendarnav-next') ? 'calendar_next' : 'calendar_previous';
                        $(this).parents('.'+o.class_calendarbox).trigger(func);
                        event.preventDefault();
                        event.stopPropagation();
                    })
                    // days event handlers
                    .delegate('td a', 'click', function(event) {
                        fieldset.trigger('callback_calendar',
                                         $(event.target).data('date'));
                        event.preventDefault();
                        event.stopPropagation();
                    })
                    // cancel link
                    .find('.calendar-cancel').click(function(event) {
                        fieldset.trigger('hide_calendar');
                        event.preventDefault();
                        event.stopPropagation();
                    });
            }
        };

        // init one clock box per fieldset
        var init_clock_box = function(fieldset) {
            // insert clock box if not there
            if (fieldset.find('.'+o.class_clockbox).length === 0) {

                var timelist = $('<div class="'+o.class_clockbox+' module">'  +
                    '  <h2>'+gettext('Choose a time')+'</h2>' +
                    '  <ul class="timelist"></ul>' +
                    '  <p class="clock-cancel"><a href="#">'+gettext('Cancel')+'</p>' +
                    '</div>')
                    .appendTo(fieldset).css('position', 'absolute').hide()
                    .find('.timelist');

                timelist.append('<li><a href="#">'+gettext('Now')+'</a></li>').find('a:last').data('time', new Date());
                timelist.append('<li><a href="#">'+gettext('Midnight')+'</a></li>').find('a:last').data('time', new Date(1970,1,1,0,0));
                timelist.append('<li><a href="#">'+gettext('6 a.m.')+'</a></li>').find('a:last').data('time', new Date(1970,1,1,6,0));
                timelist.append('<li><a href="#">'+gettext('Noon')+'</a></li>').find('a:last').data('time', new Date(1970,1,1,12,0));

                // time links event handlers
                fieldset.find('.'+o.class_clockbox)
                    .delegate('li a', 'click', function(event) {
                        fieldset.trigger('callback_clock',
                                         $(event.target).data('time'));
                        event.preventDefault();
                        event.stopPropagation();
                    })
                    // cancel link
                    .find('.clock-cancel').click(function(event) {
                        fieldset.trigger('hide_clock');
                        event.preventDefault();
                        event.stopPropagation();
                    });
            }
        };

        return this.each(function() {
            var fieldset = $(this);

            /* --- setup datetimeshortcuts specific event handlers --------- */
            fieldset

            // show calendar
            .bind('show_calendar', function(event) {
                fieldset.trigger('hide_clock');
                fieldset.trigger('hide_calendar');

                var target = $(event.target);
                var calendar = fieldset.children('.'+o.class_calendarbox);
                var field = target
                    .parents('.'+o.class_shortcuts)
                    .prev(o.date_fields);

                // Check current field value for valid date
                // and open calendar with that date selected
                var date_sel = null;
                var date_show = new Date();
                if (field.val().length > 0) {
                    // only support specific date formats here for simplicity
                    // (jQueryUI.datepicker.dateParse could help here)
                    var regex = null, y, m, d;
                    if (o.date_input_format == '%Y-%m-%d') {
                        regex = /^(\d{4})-(\d{2})-(\d{2})$/;
                        y=1; m=2; d=3;
                    }
                    else if (o.date_input_format == '%m/%d/%Y') {
                        regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
                        y=3; m=1; d=2;
                    }
                    else if (o.date_input_format == '%m/%d/%y') {
                        regex = /^(\d{2})\/(\d{2})\/(\d{2})$/;
                        y=3; m=1; d=2;
                    }
                    else if (o.date_input_format == '%d.%m.%Y') {
                        regex = /^(\d{2})\.(\d{2})\.(\d{4})$/;
                        y=3; m=2; d=1;
                    }
                    else if (o.date_input_format == '%d.%m.%y') {
                        regex = /^(\d{2})\.(\d{2})\.(\d{2})$/;
                        y=3; m=2; d=1;
                    }

                    if (regex !== null) {
                        var match = regex.exec(field.val());
                        if (match !== null) {
                            year = match[y];
                            month = match[m];
                            day = match[d];
                            if (y.length == 2) {
                                year = '20'+year;
                            }
                            date_sel = new Date(year, month-1, day);
                            date_show = new Date(year, month-1, day);
                        }
                    }
                }

                // open calendar
                calendar
                    // remember field and date
                    .data('calendar_date_field', field)
                    .data('calendar_date_show', date_show)
                    .data('calendar_date_sel', date_sel)
                    // draw correct month
                    .find('.calendar_table').empty()
                    .append(draw_calendar_table(date_sel, date_show))
                    .end().show();

                // position based on LTR or RTL direction
                var target_pos = target.position();
                var dir = $('body').attr('direction');
                if (dir != 'rtl') {
                    calendar.css('left', target_pos.left + target.width() + 'px');
                }
                if (dir == 'rtl' ||
                    ((calendar.offset().left + calendar.width()) > $(window).width())) {
                    calendar.css('left',
                        target_pos.left - calendar.width() + 'px');
                }
                calendar.css('top',
                    Math.max(0, target_pos.top - calendar.height()/2) + 'px');

                // bind close handler to document
                $('body')
                    .bind('click.datetimeshortcuts', function() {
                        fieldset.trigger('hide_calendar');
                    })
                    .bind('keyup', function(event) {
                        // ESC closes calendar
                        if (event.which == 27) {
                            fieldset.trigger('hide_calendar');
                            event.preventDefault();
                        }
                    });
            })

            // show next month in calendar
            .bind('calendar_next', function(event) {
                var cal = $(event.target);
                var tbl = cal.find('.calendar_table').empty();
                var selected = cal.data('calendar_date_sel');
                var show = cal.data('calendar_date_show');
                var month = show.getMonth();
                var year = show.getFullYear();
                if (month == 11) {
                    month = 0;
                    year++;
                }
                else {
                    month++;
                }
                show.setFullYear(year, month, 1);
                cal.data('calendar_date_show', show);
                tbl.append(draw_calendar_table(selected, show));
            })

            // show previous month in calendar
            .bind('calendar_previous', function(event) {
                var cal = $(event.target);
                var tbl = cal.find('.calendar_table').empty();
                var selected = cal.data('calendar_date_sel');
                var show = cal.data('calendar_date_show');
                var month = show.getMonth();
                var year = show.getFullYear();
                if (month === 0) {
                    month = 11;
                    year--;
                }
                else {
                    month--;
                }
                show.setFullYear(year, month, 1);
                cal.data('calendar_date_show', show);
                tbl.append(draw_calendar_table(selected, show));
            })

            // hide calendar
            .bind('hide_calendar', function(event) {
                $(event.target)
                    .children('.'+o.class_calendarbox)
                    .removeData('calendar_date_field')
                    .removeData('calendar_date_sel')
                    .removeData('calendar_date_show')
                    .hide();
                $('document').unbind('.datetimeshortcuts');
            })

            // show clock
            .bind('show_clock', function(event) {
                fieldset.trigger('hide_clock');
                fieldset.trigger('hide_calendar');

                var target = $(event.target);
                var clock = fieldset.children('.'+o.class_clockbox);
                var field = target
                    .parents('.'+o.class_shortcuts)
                    .prev(o.time_fields);

                // open clock
                clock
                    .data('clock_time_field', field)
                    .show();

                // position based on LTR or RTL direction
                var target_pos = target.position();
                var dir = $('body').attr('direction');
                if (dir != 'rtl') {
                    clock.css('left', target_pos.left + target.width() + 'px');
                }
                if (dir == 'rtl' ||
                    ((clock.offset().left + clock.width()) > $(window).width())) {
                    clock.css('left', target_pos.left - clock.width() + 'px');
                }
                clock.css('top',
                    Math.max(0, target_pos.top - clock.height()/2) + 'px');

                // bind close handler to document
                $('body')
                    .bind('click.datetimeshortcuts', function() {
                        fieldset.trigger('hide_clock');
                    })
                    .bind('keyup', function(event) {
                        // ESC closes clock
                        if (event.which == 27) {
                            fieldset.trigger('hide_clock');
                            event.preventDefault();
                        }
                    });
            })

            // hide clock
            .bind('hide_clock', function(event) {
                $(event.target)
                    .children('.'+o.class_clockbox)
                    .removeData('clock_time_field')
                    .hide();
                $('document').unbind('.datetimeshortcuts');
            })

            // calendar callback
            .bind('callback_calendar', function(event, date) {
                $(event.target)
                    .find('.'+o.class_calendarbox)
                    .data('calendar_date_field')
                    .val(date.strftime(o.date_input_format))
                    .focus();
                fieldset.trigger('hide_calendar');
            })

            // today link callback
            .bind('callback_today', function(event, days_offset) {
                var d = new Date();
                d.setDate(d.getDate() + days_offset);
                $(event.target)
                   .val(d.strftime(o.date_input_format))
                   .focus();
            })

            // clock callback
            .bind('callback_clock', function(event, time) {
                $(event.target)
                    .find('.'+o.class_clockbox)
                    .data('clock_time_field')
                    .val(time.strftime(o.time_input_format))
                    .focus();
                fieldset.trigger('hide_clock');
            })

            // now link callback
            .bind('callback_now', function(event) {
                var d = new Date();
                $(event.target)
                    .val(d.strftime(o.time_input_format))
                    .focus();
            });


            /* --- add datetime shortcut widgets --------------------------- */

            // add shortcuts to date fields
            fieldset.find(o.date_fields).each(function() {
                add_calendar($(this));
            });
            // add shortcuts to time fields
            fieldset.find(o.time_fields).each(function() {
                add_clock($(this));
            });
            // create calendar and clock widgets
            init_calendar_box(fieldset);
            init_clock_box(fieldset);


            /* --- setup $(this)-wide event delegation --------------------- */
            fieldset

            // click on calendar
            .delegate("."+o.class_shortcuts+" ."+o.class_calendar,
                      "click", function(event) {
                $(event.target).trigger('show_calendar');
                // prevent following link
                event.preventDefault();
                event.stopPropagation();
            })

            // click on today link
            .delegate("."+o.class_shortcuts+" ."+o.class_today,
                      "click", function(event) {
                $(event.target)
                    // find .datetimeshortcuts span
                    .parents('.'+o.class_shortcuts)
                    .prev(o.date_fields)
                    // update field
                    .trigger('callback_today', 0);
                fieldset.trigger('hide_calendar');
                // prevent following link
                event.preventDefault();
                event.stopPropagation();
            })

            // click on yesterday/today/tomorrow links in calendar
            .delegate("."+o.class_calendarbox+" ."+o.class_today,
                      "click", function(event) {
                var target = $(event.target);
                var offset = 0;
                if (target.is('.yesterday')) {
                    offset = -1;
                }
                else if (target.is('.tomorrow')) {
                    offset = 1;
                }
                // find calendarbox
                target.parents('.'+o.class_calendarbox)
                    // target field is stored on calendar's data attribute
                    .data('calendar_date_field')
                    // update field
                    .trigger('callback_today', offset)
                    .focus();
                fieldset.trigger('hide_calendar');
                // prevent following link
                event.preventDefault();
                event.stopPropagation();
            })

            // click on clock
            .delegate("."+o.class_shortcuts+" ."+o.class_clock,
                      "click", function(event) {
                $(event.target).trigger('show_clock');
                // prevent following link
                event.preventDefault();
                event.stopPropagation();
            })

            // click on now link
            .delegate("."+o.class_shortcuts+" ."+o.class_now,
                      "click", function(event) {
                $(event.target)
                    // find .datetimeshortcuts span
                    .parents('.'+o.class_shortcuts)
                    .prev(o.time_fields)
                    // update field
                    .trigger('callback_now');
                fieldset.trigger('hide_clock');
                // prevent following link
                event.preventDefault();
                event.stopPropagation();
            });
        });
    };

    $.fn.datetimeshortcuts.defaults = {
        // classes (do not change - css depends on these)
        class_shortcuts: "datetimeshortcuts",
        class_today: "today",
        class_calendar: "calendar",
        class_now: "now",
        class_clock: "clock",
        class_calendarbox: "calendarbox",
        class_clockbox: "clockbox",
        // date and time format
        date_input_format: get_format('DATE_INPUT_FORMATS')[0],
        time_input_format: get_format('TIME_INPUT_FORMATS')[0],
        // selectors for date and time fields
        date_fields: "input:text.vDateField",
        time_fields: "input:text.vTimeField",
        // enable clock or calendar widgets
        enable_calendar: true,
        enable_today: true,
        enable_clock: true,
        enable_now: true
    };

    // by default, initialize on all fieldset.module elements
    // which hold any date or time fields
    $(document).ready(function() {
       $("fieldset.module").datetimeshortcuts();
    });

})(django.jQuery);
