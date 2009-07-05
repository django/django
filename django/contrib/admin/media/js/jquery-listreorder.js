/*
Copyright (c) 2009 Jordan Bach, http://www.utdallas.edu/~jrb048000/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/

/*
List Reorder	 <http://www.utdallas.edu/~jrb048000/ListReorder/>

Enables drag-and-drop reordering of list items for any simple ordered <ol> or unordered <li> list.

Author: Jordan Bach
Version: 0.1
Created: January 1, 2009
License: MIT License

Constructor
	$(expr).ListOrder(options)

Methods:
	makeDefaultOrder - sets the current list order to [0, 1, 2, ...]
	restoreOrder - returns the list to its original order

Events:
	listorderchanged - Fired after a list item is dropped. The 2nd argument
		is a jQuery object representing the list that fired the event. 
		The 3rd argument is an array where the values represent
		the original index of each list item.

Options:
	itemHoverClass : 'itemHover',
	dragTargetClass : 'dragTarget',
	dropTargetClass : 'dropTarget',
	dragHandleClass : 'dragHandle'

*/

(function($){

$.fn.ListReorder = function (options) {
	
	$.fn.ListReorder.defaults = {
		itemHoverClass : 'itemHover',
		dragTargetClass : 'dragTarget',
		dropTargetClass : 'dropTarget',
		dragHandleClass : 'dragHandle',
		useDefaultDragHandle : false
	};

	var opts = $.extend({}, $.fn.ListReorder.defaults, options);
	
	return this.each(function() {
		var theList = $(this),   // The list (<ul>|<ol>)
			theItems = $('li', theList), // All <li> elements in the list
			dragActive = false,          // Are we currently dragging an item?
			dropTarget = null,           // The list placeholder
			dragTarget = null,           // The element currently being dragged
			dropIndex = -1,           	 // The list index of the dropTarget
			offset = {},				 // Positions the mouse in the dragTarget
			listOrder = [],				 // Keeps track of order relative to original order
			ref = this;
	
		theList.mouseout(ul_mouseout);
		
		// Create the drag target
		dragTarget = $('<div></div>');
		dragTarget.insertAfter(theList);
		dragTarget.hide();
		dragTarget.css('position', 'absolute');
		dragTarget.addClass(opts.dragTargetClass);
		
		for (var i = 0; i < theItems.length; i++)
			listOrder.push(i);
		
		resetList();
	
		function resetList() {	
			theItems = $('li', theList),
			
			// For each <li> in the list
			theItems.each(function() {
				var li = $(this);
				
				var dragHandle = $('<span></span>');
				dragHandle.addClass(opts.dragHandleClass)
					.mouseover(li_mouseover)
					.mousedown(dragHandle_mousedown);
				
				if (opts.useDefaultDragHandle)
					dragHandle.css({
						'display' : 'block',
						'float' : 'right',
						'width' : '10px',
						'height' : '10px',
						'border' : '2px solid #333',
						'background' : '#ccc',
						'cursor' : 'move'
					});
					
				$('.' + opts.dragHandleClass, li).remove();
				li.prepend(dragHandle);
			});
			
			clearListItemStyles();
		}
		
		// Return all list items to their default state
		function clearListItemStyles() {
			theItems.each(function() {
				var li = $(this);
				li.removeClass(opts.itemHoverClass);
				li.removeClass(opts.dropTargetClass);
			});
		}
		
		// Handle any cleanup when the mouse leaves the list
		function ul_mouseout() {
			if (!dragActive)
				clearListItemStyles();
		}
		
		// Add a hover class to a list item on mouseover
		function li_mouseover() {
			if (!dragActive) {
				clearListItemStyles();
				$(this).parent().addClass(opts.itemHoverClass);
			}
		}
		
		// Prepare the list for dragging an item
		function dragHandle_mousedown(e) {
			var li = $(this).parent();
			
			dragActive = true;
			dropIndex = theItems.index(li);
			
			// Show the drag target
			dragTarget.html(li.html());
			dragTarget.css('display', 'block');
			offset.top = e.pageY - li.offset().top;
			offset.left = e.pageX - li.offset().left;
			updateDragTargetPos(e);
			
			// Insert the placeholder
			dropTarget = li;
			dropTarget.html('');
			dropTarget.css('height', dragTarget.css('height'));
			dragTarget.css('width', dropTarget.width() + 'px');
			dropTarget.addClass(opts.dropTargetClass);
			
			// Disable Text and DOM selection
			$(document).disableTextSelect();
			
			$(document).mouseup(dragHandle_mouseup);
			$(document).mousemove(document_mousemove);	
		}
		
		// If this were on the element, we could lose the drag on the element 
		// if we move the mouse too fast
		function document_mousemove(e) {
			if (dragActive) {
				// drag target follows mouse cursor
				updateDragTargetPos(e);
				
				// Don't do mess with drop index if we are above or below the list
				if (y_mid(dragTarget) > y_bot(theList) 
					|| y_mid(dragTarget) < y_top(theList)) {
					return;
				}
				
				// detect position of drag target relative to list items
				// and swap drop target and neighboring item if necessary
				if (y_mid(dragTarget) + 5 < y_top(dropTarget)) {
					swapListItems(dropIndex, --dropIndex);
				} else if (y_mid(dragTarget) - 5 > y_bot(dropTarget)) {
					swapListItems(dropIndex, ++dropIndex);
				}
			}
		}
		
		function dragHandle_mouseup() {
			// Restore the drop target
			dropTarget.html(dragTarget.html());
			dropTarget.removeClass(opts.dragTargetClass);
			dropTarget = null;
			
			// Hide the drag target
			dragTarget.css('display', 'none');
			
			dragActive = false;
			dragTarget.unbind('mouseup', dragHandle_mouseup);
			$(document).unbind('mousemove', document_mousemove);
			resetList();
			
			theList.trigger('listorderchanged', [theList, listOrder]);
			
			// Re-enable text selection
			$(document).enableTextSelect();
			$(document).unbind('mouseup', dragHandle_mouseup);
		}
		
		function updateDragTargetPos(e) {
			dragTarget.css({ 
				'top' : e.pageY - offset.top + 'px',
				'left' : e.pageX - offset.left + 'px'
			});
		}
		
		// Change the order of two list items
		function swapListItems(oldDropIndex, newDropIndex) {
			// keep indices in bounds
			if (dropIndex < 0) {
				dropIndex = 0;
				return;
			} else if (dropIndex >= theItems.length) {
				dropIndex = theItems.length - 1;
				return;
			}
			
			var t = listOrder[oldDropIndex];
			listOrder[oldDropIndex] = listOrder[newDropIndex];
			listOrder[newDropIndex] = t;
			
			// swap list items
			var oldDropTarget = theItems.get(oldDropIndex),
				newDropTarget = theItems.get(newDropIndex),
				temp1 = $(oldDropTarget).clone(true);
				temp2 = $(newDropTarget).clone(true);
				
			$(oldDropTarget).replaceWith(temp2)
				.mouseover(li_mouseover)
				.mousedown(dragHandle_mousedown);
			$(newDropTarget).replaceWith(temp1)
				.mouseover(li_mouseover)
				.mousedown(dragHandle_mousedown);
			
			// reset so it is valid on next use
			theItems = $('li', theList);
			dropTarget = $(theItems.get(newDropIndex));
		}
		
		function y_top(jq) {
			return jq.offset().top;
		}
		
		function y_mid(jq) {
			return (y_top(jq) + y_bot(jq)) / 2
		}
		
		function y_bot(jq) {
			return jq.offset().top + jq.outerHeight();
		}
		
		this.makeDefaultOrder = function() {
			for (var i = 0; i < listOrder.length; i++)
				listOrder[i] = i;
		}
		
		this.restoreOrder = function() { 
			for (var i = 0; i < theItems.length; i++) {
				if (i != listOrder[i]) {
					var k = 0;
					for (; k < listOrder.length; k++)
						if (listOrder[k] == i)
							break;
					swapListItems(i, k);
				}
			}
			theList.trigger('listorderchanged', [theList, listOrder]);
		}
	});
}
})(jQuery);
