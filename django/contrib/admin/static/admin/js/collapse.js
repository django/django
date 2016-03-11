/*global gettext*/
(function($) {
    'use strict';
    $(document).ready(function() {
        // Add anchor tag for Show/Hide link
        $("fieldset.collapse").each(function(i, elem) {
            // Don't hide if fields in this fieldset have errors
            if ($(elem).find("div.errors").length === 0) {
            	if ($(elem).hasClass('no-initial-collapse')) {
					// If elem has class 'no-initital-collapse', don't collapse it and
					// set the toggle text to 'Hide'
					var toggleState = gettext("Hide");
            	} else {
            		// Else, collapse it and set the toggle text to show.
					$(elem).addClass("collapsed");
					var toggleState = gettext("Show");
				}
				// Add a tag for the Show/Hide toggle.
				$(elem).find("h2").first().append(' (<a id="fieldsetcollapser' +
						i + '" class="collapse-toggle" href="#">' + toggleState  +
						'</a>)');

            }
        });
        // Add toggle to anchor tag
        $("fieldset.collapse a.collapse-toggle").click(function(ev) {
            if ($(this).closest("fieldset").hasClass("collapsed")) {
                // Show
                $(this).text(gettext("Hide")).closest("fieldset").removeClass("collapsed").trigger("show.fieldset", [$(this).attr("id")]);
            } else {
                // Hide
                $(this).text(gettext("Show")).closest("fieldset").addClass("collapsed").trigger("hide.fieldset", [$(this).attr("id")]);
            }
            return false;
        });
    });
})(django.jQuery);

