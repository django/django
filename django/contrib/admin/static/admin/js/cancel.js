(function($) {
    'use strict';
    $(function() {
        $('.cancel-link').click(function(e) {
            e.preventDefault();
            window.history.back();
        });
    });
})(django.jQuery);
