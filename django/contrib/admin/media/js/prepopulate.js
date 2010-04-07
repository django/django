(function($) {
    $.fn.prepopulate = function(dependencies, maxLength) {
        /*
            Depends on urlify.js
            Populates a selected field with the values of the dependent fields,
            URLifies and shortens the string. 
            dependencies - selected jQuery object of dependent fields
            maxLength - maximum length of the URLify'd string 
        */
        return this.each(function() {
            var field = $(this);

            field.data('_changed', false);
            field.change(function() {
                field.data('_changed', true);
            });

            var populate = function () {
                // Bail if the fields value has changed
                if (field.data('_changed') == true) return;
 
                var values = [];
                dependencies.each(function() {
                    if ($(this).val().length > 0) {
                        values.push($(this).val());
                    }
                });
                field.val(URLify(values.join(' '), maxLength));
            };

            dependencies.keyup(populate).change(populate).focus(populate);
        });
    };
})(jQuery.noConflict());
