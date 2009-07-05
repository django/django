/**
 * .disableTextSelect - Disable Text Select Plugin
 *
 * Version: 1.1
 * Updated: 2007-11-28
 *
 * Used to stop users from selecting text
 *
 * Copyright (c) 2007 James Dempster (letssurf@gmail.com, http://www.jdempster.com/category/jquery/disabletextselect/)
 *
 * Dual licensed under the MIT (MIT-LICENSE.txt)
 * and GPL (GPL-LICENSE.txt) licenses.
 **/

/**
 * Requirements:
 * - jQuery (John Resig, http://www.jquery.com/)
 **/
(function($){if($.browser.mozilla){$.fn.disableTextSelect=function(){return this.each(function(){$(this).css({"MozUserSelect":"none"})})};$.fn.enableTextSelect=function(){return this.each(function(){$(this).css({"MozUserSelect":""})})}}else{if($.browser.msie){$.fn.disableTextSelect=function(){return this.each(function(){$(this).bind("selectstart.disableTextSelect",function(){return false})})};$.fn.enableTextSelect=function(){return this.each(function(){$(this).unbind("selectstart.disableTextSelect")})}}else{$.fn.disableTextSelect=function(){return this.each(function(){$(this).bind("mousedown.disableTextSelect",function(){return false})})};$.fn.enableTextSelect=function(){return this.each(function(){$(this).unbind("mousedown.disableTextSelect")})}}}})(jQuery)
