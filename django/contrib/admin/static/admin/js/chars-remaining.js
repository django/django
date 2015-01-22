(function($) {
    function toggleVisibility() {
        $(this).next().toggle();
    }

    function updateCount() {
        var $this = $(this);
        var remaining = parseInt($this.attr('maxlength'), 10) - $this.val().length;
        $this.next().find('.count').html(remaining);
    }

    var container = $(document);
    container.on('focusin', 'input[maxlength]', toggleVisibility);
    container.on('focusout', 'input[maxlength]', toggleVisibility);
    container.on('change', 'input[maxlength]', updateCount);
    container.on('keyup', 'input[maxlength]', updateCount);

})(django.jQuery);
