(function($) {
    var settings = {
        'name': '',
        'verboseName': '',
        'stacked': 0,
        refresh_icons: function(selector) {
            var available = selector.data('available');
            var chosen = selector.data('chosen');
            var is_from_selected = available.children().filter(':selected').length > 0;
            var is_to_selected = chosen.children().filter(':selected').length > 0;
            // Active if at least one item is selected
            selector.find('.selector-add').toggleClass('active', is_from_selected);
            selector.find('.selector-remove').toggleClass('active', is_to_selected);
            // Active if the corresponding box isn't empty
            selector.find('.selector-chooseall').toggleClass('active', available.find('option').length > 0);
            selector.find('.selector-clearall').toggleClass('active', chosen.find('option').length > 0);
        },
        refresh_state: function(selector) {
            settings.refresh_icons(selector);
            var available = selector.data('available');
            var chosen = selector.data('chosen');

            // Re-generate the content of the actual, hidden, box.
            var actualBox = selector.data('actualBox');
            var actualOptions = actualBox.children();

            // De-select all options.
            available.children().each(function(){
                var option = actualOptions[$(this).attr('data-index')];
                option.selected = false;
            });

            // Select all the same options as those from the 'to' box.
            chosen.children().each(function(){
                var option = actualOptions[$(this).attr('data-index')];
                option.selected = true;
            });
        },
        move: function(from, to, all) {
            var selector = from.data('selector');
            var available = selector.data('available');

            var options;
            if (all) {
                options = from.children();
            }
            else {
                options = from.children().filter(':selected');
            }

            if (from == available) {
                options.each(function() {
                    var moved_option = $(this);
                    available.data('cache').each(function(index, option) {
                        var cached_option = $(option);
                        if (moved_option.val() == cached_option.val()) {
                            available.data('cache').splice(index, 1);
                        }
                    });
                });
            }
            else {
                options.each(function() {
                    available.data('cache').push($(this).clone()[0]);
                });
            }

            to.append(options);
            to.children().removeAttr('selected');
            settings.refresh_state(from.data('selector'));
        }
    };

    var methods = {
        init: function(options) {
            $.extend(settings, options);

            var actualBox = this;
            var stack_class = settings.stacked ? 'selector stacked' : 'selector';
            var selector = $('<div>').addClass(stack_class)
                                     .attr('id', actualBox.attr('id') + '_selector')
                                     .appendTo(actualBox.parent());

            actualBox.parent().find('p').each(function(){
                if ($(this).hasClass('info')) {
                    // Remove <p class="info">, because it just gets in the way.
                    $(this).remove();
                }
                else if ($(this).hasClass('help')) {
                    // Move help text up to the top so it isn't below the select
                    // boxes or wrapped off on the side to the right of the add
                    // button.
                    actualBox.parent().prepend($(this));
                }
            });

            var available = $('<select>').addClass('filtered').attr({
                'id': 'id_' + settings.name + '_from',
                'multiple': 'multiple',
                'name': settings.name + '_from'
            });

            actualBox.children().each(function(index, original){
                var copy = $('<option>').attr({
                    'value': $(original).val(),
                    'title': $(original).text(),
                    'data-index': index
                });
                copy.text($(original).text());
                copy[0].selected = original.selected;
                available.append(copy);
            });
            actualBox.hide();
            available.insertBefore(actualBox);
            available.show();

            var search = $('<input>').attr({
                'id': 'id_' + settings.name + '_input',
                'type': 'text'
            });

            var searchContainer = $('<p>').addClass('selector-filter')
                                          .append(
                                              $('<label>').attr('for', search.attr('id')).css({'width': "16px", 'padding': "2px"})
                                                  .append(
                                                      $('<span>').attr({
                                                          title: interpolate(
                                                              gettext("Type into this box to filter down the list of available %s."),
                                                              [settings.verboseName]
                                                          )
                                                      }).addClass('help-tooltip search-label-icon')
                                                  )
                                          )
                                          .append(search);

            var availableHeader = $('<h2>').text(gettext('Available ') + settings.verboseName)
                                           .append('&nbsp;')
                                           .append(
                                               $('<span>').attr({
                                                   title: interpolate(
                                                       gettext(
                                                           'This is the list of available %s. You may choose some by ' +
                                                           'selecting them in the box below and then clicking the ' +
                                                           '"Choose" arrow between the two boxes.'
                                                       ),
                                                       [settings.verboseName]
                                                   )
                                               }).addClass('help help-tooltip help-icon')
                                           );

            var chosenHeader = $('<h2>').text(gettext('Chosen ') + settings.verboseName)
                                           .append('&nbsp;')
                                           .append(
                                               $('<span>').attr({
                                                   title: interpolate(
                                                       gettext(
                                                           'This is the list of chosen %s. You may remove some by ' +
                                                           'selecting them in the box below and then clicking the ' +
                                                           '"Remove" arrow between the two boxes.'
                                                       ),
                                                       [settings.verboseName]
                                                   )
                                               }).addClass('help help-tooltip help-icon')
                                           );

            $('<div>').addClass('selector-available')
                .append(availableHeader)
                .append(searchContainer)
                .append(available)
                .append($('<a>').addClass('selector-chooseall').text(gettext('Choose all')).attr('href', '#'))
                .appendTo(selector);

            $('<ul>').addClass('selector-chooser')
                .append($('<li>')
                    .append($('<a>').addClass('selector-add').text(gettext('Choose')).attr('title', gettext('Choose')))
                )
                .append($('<li>')
                    .append($('<a>').addClass('selector-remove').text(gettext('Remove')).attr('title', gettext('Remove')))
                )
                .appendTo(selector);

            var chosen = $('<select>').addClass('filtered').attr({
                'id': 'id_' + settings.name + '_to',
                'multiple': 'multiple',
                'name': settings.name + '_to'
            });

            $('<div>').addClass('selector-chosen')
                .append(chosenHeader)
                .append(chosen)
                .append(
                    $('<a>').addClass('selector-clearall')
                        .text(gettext('Clear all'))
                        .attr('href', '#')
                ).appendTo(selector);

            // Cross-referencing
            available.data('selector', selector);
            chosen.data('selector', selector);
            selector.data('available', available);
            selector.data('chosen', chosen);
            selector.data('actualBox', actualBox);

            // Initialize the filter cache
            available.data('cache', available.children());

            // If this is a saved instance, move the already selected options across
            // to the chosen list.
            settings.move(available, chosen);

            // Resizing
            if (!settings.stacked) {
                // In horizontal mode, give the same height to the two boxes.
                var resize_filters = function() {
                    chosen.height($(searchContainer).outerHeight() + available.outerHeight());
                };
                if (available.outerHeight() > 0) {
                    resize_filters(); // This fieldset is already open. Resize now.
                } else {
                    // This fieldset is probably collapsed. Wait for its 'show' event.
                    chosen.closest('fieldset').one('show.fieldset', resize_filters);
                }
            }

            // Hook up selection events.
            $(search).keypress(function(event) {
                // Don't submit form if user pressed Enter.
                if ((event.which && event.which == 13) || (event.keyCode && event.keyCode == 13)) {
                    if (!available.children().filter(':selected').length)
                        available.children().first().attr('selected', true);
                    settings.move(available, chosen);
                    event.preventDefault();
                    return false;
                }
            });

            $(search).keyup(function(event) {
                available.children().removeAttr('selected');
                var text = $(this).val();
                if ($.trim(text)) {
                    var tokens = text.toLowerCase().split(/\s+/);
                    var token;
                    available.empty();
                    available.data('cache').each(function() {
                        // Redisplay the HTML select box, displaying only the choices
                        // containing ALL the words in text. (It's an AND search.)
                        for (var j = 0; (token = tokens[j]); j++) {
                            if (this.text.toLowerCase().indexOf(token) != -1) {
                                available.append($(this).clone());
                            }
                        }
                    });
                }
                else {
                    available.html(available.data('cache').clone());
                }
                return true;
            });

            selector.find('.selector-chooseall').click(function() {
                settings.move(available, chosen, true);
                return false;
            });

            selector.find('.selector-clearall').click(function() {
                settings.move(chosen, available, true);
                return false;
            });

            selector.find('.selector-add').click(function() {
                settings.move(available, chosen);
                return false;
            });

            selector.find('.selector-remove').click(function() {
                settings.move(chosen, available);
                return false;
            });

            available.dblclick(function() {
                settings.move(available, chosen);
            });

            available.change(function() {
                settings.refresh_icons(selector);
            });

            chosen.change(function() {
                settings.refresh_icons(selector);
            });

            chosen.dblclick(function() {
                settings.move(chosen, available);
            });

            available.keydown(function(event) {
                event.which = event.which ? event.which : event.keyCode;
                switch(event.which) {
                    case 13:
                        // Enter pressed - don't submit the form but move the current selection.
                        settings.move(available, chosen);
                        this.selectedIndex = (this.selectedIndex == this.length) ? this.length - 1 : this.selectedIndex;
                        return false;
                    case 39:
                        // Right arrow - move across (only when horizontal)
                        if (!settings.stacked) {
                            settings.move(available, chosen);
                            this.selectedIndex = (this.selectedIndex == this.length) ? this.length - 1 : this.selectedIndex;
                            return false;
                        }
                }
                return true;
            });

            chosen.keydown(function(event) {
                event.which = event.which ? event.which : event.keyCode;
                switch(event.which) {
                    case 13:
                        // Enter pressed - don't submit the form but move the current selection.
                        settings.move(chosen, available);
                        this.selectedIndex = (this.selectedIndex == this.length) ? this.length - 1 : this.selectedIndex;
                        return false;
                    case 37:
                        // Left arrow - move across (only when horizontal)
                        if (!settings.stacked) {
                            settings.move(chosen, available);
                            this.selectedIndex = (this.selectedIndex == this.length) ? this.length - 1 : this.selectedIndex;
                            return false;
                        }
                }
                return true;
            });
        }
    };

    $.fn.selectFilter = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method ) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.selectFilter');
        }
    };
})(django.jQuery);
