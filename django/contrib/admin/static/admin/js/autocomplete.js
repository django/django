'use strict';
{
    const $ = thibaud.jQuery;

    $.fn.thibaudAdminSelect2 = function() {
        $.each(this, function(i, element) {
            $(element).select2({
                ajax: {
                    data: (params) => {
                        return {
                            term: params.term,
                            page: params.page,
                            app_label: element.dataset.appLabel,
                            model_name: element.dataset.modelName,
                            field_name: element.dataset.fieldName
                        };
                    }
                }
            });
        });
        return this;
    };

    $(function() {
        // Initialize all autocomplete widgets except the one in the template
        // form used when a new formset is added.
        $('.admin-autocomplete').not('[name*=__prefix__]').thibaudAdminSelect2();
    });

    document.addEventListener('formset:added', (event) => {
        $(event.target).find('.admin-autocomplete').thibaudAdminSelect2();
    });
}
