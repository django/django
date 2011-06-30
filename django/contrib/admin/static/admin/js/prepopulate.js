(function($) {
    $.fn.prepopulate = function(dependencies, maxLength) {
        /*
            Depends on urlify.js
            Populates a selected field with the values of the dependent fields,
            URLifies and shortens the string. 
            dependencies - array of dependent fields id's 
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
                $.each(dependencies, function(i, field) {
                  if ($(field).val().length > 0) {
                      values.push($(field).val());
                  }
                })
                field.val(URLify(values.join(' '), maxLength));
            };

            $(dependencies.join(',')).keyup(populate).change(populate).focus(populate);
        });
    };
})(django.jQuery);
