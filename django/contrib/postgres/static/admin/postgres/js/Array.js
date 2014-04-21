django.jQuery(function($) {
    $('.arrayfield .addlink').click(function() {
        var toCopy = $(this).parent('.arrayfield').find('.arrayfield-inner:last');
        var newRow = toCopy.clone();
        newRow.find(':input').each(function() {
            var oldName = $(this).attr('name');
            // hoplessly naive for now - need to handle nested multi widget styles and also ids
            parts = oldName.split('_');
            prefix = parts[0];
            number = parseInt(parts[1]);
            $(this).attr('name', prefix + '_' + (number + 1));
            $(this).val('');
        });
        toCopy.after(newRow);
    });
});
