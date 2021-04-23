'use strict';
{
    const $ = django.jQuery;
    const init = function($element, options) {
        let userData = function(params) {};
        if (options.ajax && options.ajax.data) {
            userData = options.ajax.data;
            delete options.ajax.data;
        }

        const settings = $.extend(true, {
            ajax: {
                data: function(params) {
                    const defaultData = {
                        term: params.term,
                        page: params.page,
                        app_label: $element.data('app-label'),
                        model_name: $element.data('model-name'),
                        field_name: $element.data('field-name')
                    };
                    return $.extend(defaultData, userData(params));
                }
            }
        }, options);
        $element.select2(settings);
    };

    $.fn.djangoAdminSelect2 = function(options) {
        const settings = $.extend({}, options);
        $.each(this, function(i, element) {
            const $element = $(element);
            init($element, settings);
        });
        return this;
    };

    $(function() {
        // Initialize all autocomplete widgets except the one in the template
        // form used when a new formset is added.
        $('.admin-autocomplete').not('[name*=__prefix__]').djangoAdminSelect2();
    });

    $(document).on('formset:added', (function() {
        return function(event, $newFormset) {
            return $newFormset.find('.admin-autocomplete').djangoAdminSelect2();
        };
    })(this));
}
