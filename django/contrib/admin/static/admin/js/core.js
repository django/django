// Core javascript helper functions

// basic browser identification & version
var isOpera = (navigator.userAgent.indexOf("Opera") >= 0) && parseFloat(navigator.appVersion);
var isIE = ((document.all) && (!isOpera)) && parseFloat(navigator.appVersion.split("MSIE ")[1].split(";")[0]);

// Cross-browser event handlers.
function addEvent(obj, evType, fn) {
    'use strict';
    if (obj.addEventListener) {
        obj.addEventListener(evType, fn, false);
        return true;
    } else if (obj.attachEvent) {
        var r = obj.attachEvent("on" + evType, fn);
        return r;
    } else {
        return false;
    }
}

function removeEvent(obj, evType, fn) {
    'use strict';
    if (obj.removeEventListener) {
        obj.removeEventListener(evType, fn, false);
        return true;
    } else if (obj.detachEvent) {
        obj.detachEvent("on" + evType, fn);
        return true;
    } else {
        return false;
    }
}

function cancelEventPropagation(e) {
    'use strict';
    if (!e) {
        e = window.event;
    }
    e.cancelBubble = true;
    if (e.stopPropagation) {
        e.stopPropagation();
    }
}

// quickElement(tagType, parentReference [, textInChildNode, attribute, attributeValue ...]);
function quickElement() {
    'use strict';
    var obj = document.createElement(arguments[0]);
    if (arguments[2]) {
        var textNode = document.createTextNode(arguments[2]);
        obj.appendChild(textNode);
    }
    var len = arguments.length;
    for (var i = 3; i < len; i += 2) {
        obj.setAttribute(arguments[i], arguments[i + 1]);
    }
    arguments[1].appendChild(obj);
    return obj;
}

// "a" is reference to an object
function removeChildren(a) {
    'use strict';
    while (a.hasChildNodes()) {
        a.removeChild(a.lastChild);
    }
}

// ----------------------------------------------------------------------------
// Cross-browser xmlhttp object
// from http://jibbering.com/2002/4/httprequest.html
// ----------------------------------------------------------------------------
var xmlhttp;
/*@cc_on @*/
/*@if (@_jscript_version >= 5)
    try {
        xmlhttp = new ActiveXObject("Msxml2.XMLHTTP");
    } catch (e) {
        try {
            xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
        } catch (E) {
            xmlhttp = false;
        }
    }
@else
    xmlhttp = false;
@end @*/
if (!xmlhttp && typeof XMLHttpRequest !== 'undefined') {
    xmlhttp = new XMLHttpRequest();
}

// ----------------------------------------------------------------------------
// Find-position functions by PPK
// See http://www.quirksmode.org/js/findpos.html
// ----------------------------------------------------------------------------
function findPosX(obj) {
    'use strict';
    var curleft = 0;
    if (obj.offsetParent) {
        while (obj.offsetParent) {
            curleft += obj.offsetLeft - ((isOpera) ? 0 : obj.scrollLeft);
            obj = obj.offsetParent;
        }
        // IE offsetParent does not include the top-level
        if (isIE && obj.parentElement) {
            curleft += obj.offsetLeft - obj.scrollLeft;
        }
    } else if (obj.x) {
        curleft += obj.x;
    }
    return curleft;
}

function findPosY(obj) {
    'use strict';
    var curtop = 0;
    if (obj.offsetParent) {
        while (obj.offsetParent) {
            curtop += obj.offsetTop - ((isOpera) ? 0 : obj.scrollTop);
            obj = obj.offsetParent;
        }
        // IE offsetParent does not include the top-level
        if (isIE && obj.parentElement) {
            curtop += obj.offsetTop - obj.scrollTop;
        }
    } else if (obj.y) {
        curtop += obj.y;
    }
    return curtop;
}

//-----------------------------------------------------------------------------
// Date object extensions
// ----------------------------------------------------------------------------
(function() {
    'use strict';
    Date.prototype.getTwelveHours = function() {
        var hours = this.getHours();
        if (hours === 0) {
            return 12;
        }
        else {
            return hours <= 12 ? hours : hours - 12;
        }
    };

    Date.prototype.getTwoDigitMonth = function() {
        return (this.getMonth() < 9) ? '0' + (this.getMonth() + 1) : (this.getMonth() + 1);
    };

    Date.prototype.getTwoDigitDate = function() {
        return (this.getDate() < 10) ? '0' + this.getDate() : this.getDate();
    };

    Date.prototype.getTwoDigitTwelveHour = function() {
        return (this.getTwelveHours() < 10) ? '0' + this.getTwelveHours() : this.getTwelveHours();
    };

    Date.prototype.getTwoDigitHour = function() {
        return (this.getHours() < 10) ? '0' + this.getHours() : this.getHours();
    };

    Date.prototype.getTwoDigitMinute = function() {
        return (this.getMinutes() < 10) ? '0' + this.getMinutes() : this.getMinutes();
    };

    Date.prototype.getTwoDigitSecond = function() {
        return (this.getSeconds() < 10) ? '0' + this.getSeconds() : this.getSeconds();
    };

    Date.prototype.getHourMinute = function() {
        return this.getTwoDigitHour() + ':' + this.getTwoDigitMinute();
    };

    Date.prototype.getHourMinuteSecond = function() {
        return this.getTwoDigitHour() + ':' + this.getTwoDigitMinute() + ':' + this.getTwoDigitSecond();
    };

    Date.prototype.strftime = function(format) {
        var fields = {
            c: this.toString(),
            d: this.getTwoDigitDate(),
            H: this.getTwoDigitHour(),
            I: this.getTwoDigitTwelveHour(),
            m: this.getTwoDigitMonth(),
            M: this.getTwoDigitMinute(),
            p: (this.getHours() >= 12) ? 'PM' : 'AM',
            S: this.getTwoDigitSecond(),
            w: '0' + this.getDay(),
            x: this.toLocaleDateString(),
            X: this.toLocaleTimeString(),
            y: ('' + this.getFullYear()).substr(2, 4),
            Y: '' + this.getFullYear(),
            '%': '%'
        };
        var result = '', i = 0;
        while (i < format.length) {
            if (format.charAt(i) === '%') {
                result = result + fields[format.charAt(i + 1)];
                ++i;
            }
            else {
                result = result + format.charAt(i);
            }
            ++i;
        }
        return result;
    };

// ----------------------------------------------------------------------------
// String object extensions
// ----------------------------------------------------------------------------
    String.prototype.pad_left = function(pad_length, pad_string) {
        var new_string = this;
        for (var i = 0; new_string.length < pad_length; i++) {
            new_string = pad_string + new_string;
        }
        return new_string;
    };

    String.prototype.strptime = function(format) {
        var split_format = format.split(/[.\-/]/);
        var date = this.split(/[.\-/]/);
        var i = 0;
        var day, month, year;
        while (i < split_format.length) {
            switch (split_format[i]) {
                case "%d":
                    day = date[i];
                    break;
                case "%m":
                    month = date[i] - 1;
                    break;
                case "%Y":
                    year = date[i];
                    break;
                case "%y":
                    year = date[i];
                    break;
            }
            ++i;
        }
        return new Date(year, month, day);
    };

})();
// ----------------------------------------------------------------------------
// Get the computed style for and element
// ----------------------------------------------------------------------------
function getStyle(oElm, strCssRule) {
    'use strict';
    var strValue = "";
    if(document.defaultView && document.defaultView.getComputedStyle) {
        strValue = document.defaultView.getComputedStyle(oElm, "").getPropertyValue(strCssRule);
    }
    else if(oElm.currentStyle) {
        strCssRule = strCssRule.replace(/\-(\w)/g, function(strMatch, p1) {
            return p1.toUpperCase();
        });
        strValue = oElm.currentStyle[strCssRule];
    }
    return strValue;
}
