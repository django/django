(function($) {
    function updateCount() {
        var $this = $(this);
        var remaining = parseInt($this.attr('maxlength'), 10) - $this.val().length;
        $this.next().find('.count').html(remaining);
    }

    var container = $(document);
    container.on('change', 'input[maxlength]', updateCount);
    container.on('keyup', 'input[maxlength]', updateCount);

})(django.jQuery);
