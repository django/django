// Finds all <input type="text" class="vDateField"> and inserts a calendar after them

// quickElement(tagType, parentReference, textInChildNode, [, attribute, attributeValue ...]);
function quickElement() {
	var obj = document.createElement(arguments[0]);
	if (arguments[2] != '' && arguments[2] != null) {
		var textNode = document.createTextNode(arguments[2]);
		obj.appendChild(textNode);
	}
	for (var i = 3; i < arguments.length; i += 2) {
		obj.setAttribute(arguments[i], arguments[i+1]);
	}
	arguments[1].appendChild(obj);
	return obj;
}

// findPosX / findPosY: see http://www.quirksmode.org/js/findpos.html
function findPosX(obj)
{
	var curleft = 0;
	if (obj.offsetParent)
	{
		while (obj.offsetParent)
		{
			curleft += obj.offsetLeft
			obj = obj.offsetParent;
		}
	}
	else if (obj.x)
		curleft += obj.x;
	return curleft;
}

function findPosY(obj)
{
	var curtop = 0;
	if (obj.offsetParent)
	{
		while (obj.offsetParent)
		{
			curtop += obj.offsetTop
			obj = obj.offsetParent;
		}
	}
	else if (obj.y)
		curtop += obj.y;
	return curtop;
}

var AddCal = {
	cals: [],
	inps: [],
	divname1: 'calendarbox', // name of <div> that gets toggled
	divname2: 'calendarin',  // name of <div> that contains calendar
	init: function() {
		var inputs = document.getElementsByTagName('input');
		for (var i=0; i < inputs.length; i++) {
			var inp = inputs[i];
			if (inp.getAttribute('type') == 'text' && inp.className.match(/vDateField/)) {
				var num = AddCal.cals.length;

				AddCal.inps[num] = inp;

				// <a href="javascript:AddCal.toggle()">Calendar</a>
				var cal_link = document.createElement('a');
				cal_link.setAttribute('href', 'javascript:AddCal.toggle(' + num + ');');
				quickElement('img', cal_link, '', 'src', 'http://media.ljworld.com/img/admin/icon_calendar.gif', 'alt', 'Calendar');
				inp.parentNode.insertBefore(cal_link, inp.nextSibling);

				// Markup looks like:
				//
                // <div id="calendarbox3" class="calendarbox module">
                //     <h2>
                //           <a href="#" class="link-previous">&lsaquo;</a>
                //           <a href="#" class="link-next">&rsaquo;</a> February 2003
                //     </h2>
                //     <div class="calendar" id="calendarin3">
                //         <!-- (cal) -->
                //     </div>
                //     <div class="calendar-shortcuts">
                //          <a href="#">Yesterday</a> | <a href="#">Today</a> | <a href="#">Tomorrow</a>
                //     </div>
                //     <p class="calendar-cancel"><a href="#">Cancel</a></p>
                // </div>
				var cal_box = document.createElement('div');
				cal_box.style.display = 'none';
				cal_box.style.position = 'absolute';
				cal_box.style.left = findPosX(cal_link) + 17 + 'px';
				cal_box.style.top = findPosY(cal_link) - 75 + 'px';
				cal_box.className = 'calendarbox module';
				cal_box.setAttribute('id', AddCal.divname1 + num);
				
				// next-prev links
				var cal_nav = quickElement('div', cal_box, '');
		        quickElement('a', cal_nav, '<', 'class', 'calendarnav-previous', 'href', 'javascript:AddCal.drawPrev('+num+');');
		        quickElement('a', cal_nav, '>', 'class', 'calendarnav-next',     'href', 'javascript:AddCal.drawNext('+num+');');
				cal_box.appendChild(cal_nav);
               
                // main box                
				var cal_main = quickElement('div', cal_box, '', 'id', AddCal.divname2 + num);
				cal_main.className = 'calendar';
				document.body.appendChild(cal_box);
				AddCal.cals[num] = new Calendar(AddCal.divname2 + num, AddCal.handleCallback(num));
				AddCal.cals[num].drawCurrent();
                
                // calendar shortcuts
                var shortcuts = quickElement('div', cal_box, '', 'class', 'calendar-shortcuts');
                quickElement('a', shortcuts, 'Yesterday', 'href', 'javascript:AddCal.handleQuickLink(' + num + ', -1);');
                shortcuts.appendChild(document.createTextNode('\240|\240'));
                quickElement('a', shortcuts, 'Today', 'href', 'javascript:AddCal.handleQuickLink(' + num + ', 0);');
                shortcuts.appendChild(document.createTextNode('\240|\240'));
                quickElement('a', shortcuts, 'Tomorrow', 'href', 'javascript:AddCal.handleQuickLink(' + num + ', +1);');
                
                // cancel bar
                var cancel_p = quickElement('p', cal_box, '', 'class', 'calendar-cancel');
                quickElement('a', cancel_p, 'Cancel', 'href', 'javascript:AddCal.toggle(' + num + ');');
				
				
			}
		}
	},
	toggle: function(num) {
		var box = document.getElementById(AddCal.divname1+num);
		box.style.display = (box.style.display == 'none') ? 'block' : 'none';
		/*
		if (box.style.display = 'block') {
            var x = 0;
            var y = 0;
            if (!e) var e = window.event;
            if (e.pageX || e.pageY) {
                x = e.pageX;
                y = e.pageY;
            } else if (e.clientX || e.clientY) {
                x = e.clientX + document.body.scrollLeft;
                y = e.clientY + document.body.scrollTop;
            }
            box.style.left = x;
            box.style.top = y;
		}
		*/
	},
	drawPrev: function(num) {
		AddCal.cals[num].drawPreviousMonth();
	},
	drawNext: function(num) {
		AddCal.cals[num].drawNextMonth();
	},
	handleCallback: function(num) {
		return "function(y, m, d) { AddCal.inps["+num+"].value = y+'-'+m+'-'+d; document.getElementById(AddCal.divname1+"+num+").style.display='none';}";
	},
	handleQuickLink: function(num, offset) {
	   var d = new Date();
	   d.setDate(d.getDate() + offset)
	   AddCal.inps[num].value = d.getISODate();
	   AddCal.toggle(num);
	}
}
addEvent(window, 'load', AddCal.init);
