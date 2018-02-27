(function($) {
    'use strict';
    $(function() {
        $('.cancel-link').on('click', function(e) {
            e.preventDefault();
            window.history.back();
        });
    });
})(django.jQuery);
