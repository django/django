(function ($) {
    var setCookie = function (cname, cvalue, exdays) {
        var d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toGMTString();
        document.cookie = cname + "=" + cvalue + "; " + expires;
    };

    var getCookie = function (cname) {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i].trim();
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    };

    var toggleFilter = function (hideMsg, showMsg, expireDays) {
        var $filtersBox, $filtersHeader, $hiddenState, $filterResult;
        hideMsg = ' (' + hideMsg + ')';
        showMsg = ' (' + showMsg + ')';
        $filterResult = $('#changelist-form .results');
        $filtersBox = $('#changelist-filter');
        $filtersHeader = $filtersBox.find('h2:first');
        $filterResult.css('margin-right', $filtersBox.width());
        $hiddenState = $('<span class="hidden_state"> ' +
            showMsg + '</span>').appendTo($filtersHeader);
        $filtersBox.css(
                'overflow',
                'hidden'
            ).data(
                'visible-height',
                $filtersBox.height()
            ).data(
                'hidden-height',
                $filtersHeader.innerHeight()
            );
        $filtersHeader.css({
            cursor: 'pointer'
        }).click(function () {
            if ($(this).data('is-hidden')) {
                $filterResult.css('margin-right', $filtersBox.width());

                $filtersBox.animate({
                    height: $filtersBox.data('visible-height')
                }, 'fast', function () {
                    return $hiddenState.text(showMsg);
                });
                $(this).data('is-hidden', false);
                return setCookie('admin-filter-is-hidden', '', expireDays);
            } else {
                $filterResult.css('margin-right', '0px');
                $filtersBox.animate({
                    height: $filtersBox.data('hidden-height')
                }, 'fast', function () {
                    return $hiddenState.text(hideMsg);
                });
                $(this).data('is-hidden', true);
                return setCookie('admin-filter-is-hidden', true, expireDays);
            }
        });
        if (getCookie('admin-filter-is-hidden')) {
            return $filtersHeader.click();
        }
    };
    window.toggleFilter = toggleFilter;
})(django.jQuery);
