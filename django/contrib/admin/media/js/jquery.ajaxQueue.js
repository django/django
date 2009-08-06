/**
 * Ajax Queue Plugin
 * 
 * Homepage: http://jquery.com/plugins/project/ajaxqueue
 * Documentation: http://docs.jquery.com/AjaxQueue
 */

/**

<script>
$(function(){
	jQuery.ajaxQueue({
		url: "test.php",
		success: function(html){ jQuery("ul").append(html); }
	});
	jQuery.ajaxQueue({
		url: "test.php",
		success: function(html){ jQuery("ul").append(html); }
	});
	jQuery.ajaxSync({
		url: "test.php",
		success: function(html){ jQuery("ul").append("<b>"+html+"</b>"); }
	});
	jQuery.ajaxSync({
		url: "test.php",
		success: function(html){ jQuery("ul").append("<b>"+html+"</b>"); }
	});
});
</script>
<ul style="position: absolute; top: 5px; right: 5px;"></ul>

 */
/*
 * Queued Ajax requests.
 * A new Ajax request won't be started until the previous queued 
 * request has finished.
 */

/*
 * Synced Ajax requests.
 * The Ajax request will happen as soon as you call this method, but
 * the callbacks (success/error/complete) won't fire until all previous
 * synced requests have been completed.
 */


(function($) {
	
	var ajax = $.ajax;
	
	var pendingRequests = {};
	
	var synced = [];
	var syncedData = [];
	
	$.ajax = function(settings) {
		// create settings for compatibility with ajaxSetup
		settings = jQuery.extend(settings, jQuery.extend({}, jQuery.ajaxSettings, settings));
		
		var port = settings.port;
		
		switch(settings.mode) {
		case "abort": 
			if ( pendingRequests[port] ) {
				pendingRequests[port].abort();
			}
			return pendingRequests[port] = ajax.apply(this, arguments);
		case "queue": 
			var _old = settings.complete;
			settings.complete = function(){
				if ( _old )
					_old.apply( this, arguments );
				jQuery([ajax]).dequeue("ajax" + port );;
			};
		
			jQuery([ ajax ]).queue("ajax" + port, function(){
				ajax( settings );
			});
			return;
		case "sync":
			var pos = synced.length;
	
			synced[ pos ] = {
				error: settings.error,
				success: settings.success,
				complete: settings.complete,
				done: false
			};
		
			syncedData[ pos ] = {
				error: [],
				success: [],
				complete: []
			};
		
			settings.error = function(){ syncedData[ pos ].error = arguments; };
			settings.success = function(){ syncedData[ pos ].success = arguments; };
			settings.complete = function(){
				syncedData[ pos ].complete = arguments;
				synced[ pos ].done = true;
		
				if ( pos == 0 || !synced[ pos-1 ] )
					for ( var i = pos; i < synced.length && synced[i].done; i++ ) {
						if ( synced[i].error ) synced[i].error.apply( jQuery, syncedData[i].error );
						if ( synced[i].success ) synced[i].success.apply( jQuery, syncedData[i].success );
						if ( synced[i].complete ) synced[i].complete.apply( jQuery, syncedData[i].complete );
		
						synced[i] = null;
						syncedData[i] = null;
					}
			};
		}
		return ajax.apply(this, arguments);
	};
	
})(jQuery);