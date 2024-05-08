// S5 v1.1 slides.js -- released into the Public Domain
// Modified for Docutils (https://docutils.sourceforge.io) by David Goodger
//
// Please see http://www.meyerweb.com/eric/tools/s5/credits.html for
// information about all the wonderful and talented contributors to this code!

var undef;
var slideCSS = '';
var snum = 0;
var smax = 1;
var slideIDs = new Array();
var incpos = 0;
var number = undef;
var s5mode = true;
var defaultView = 'slideshow';
var controlVis = 'visible';

var isIE = navigator.appName == 'Microsoft Internet Explorer' ? 1 : 0;
var isOp = navigator.userAgent.indexOf('Opera') > -1 ? 1 : 0;
var isGe = navigator.userAgent.indexOf('Gecko') > -1 && navigator.userAgent.indexOf('Safari') < 1 ? 1 : 0;

function hasClass(object, className) {
	if (!object.className) return false;
	return (object.className.search('(^|\\s)' + className + '(\\s|$)') != -1);
}

function hasValue(object, value) {
	if (!object) return false;
	return (object.search('(^|\\s)' + value + '(\\s|$)') != -1);
}

function removeClass(object,className) {
	if (!object) return;
	object.className = object.className.replace(new RegExp('(^|\\s)'+className+'(\\s|$)'), RegExp.$1+RegExp.$2);
}

function addClass(object,className) {
	if (!object || hasClass(object, className)) return;
	if (object.className) {
		object.className += ' '+className;
	} else {
		object.className = className;
	}
}

function GetElementsWithClassName(elementName,className) {
	var allElements = document.getElementsByTagName(elementName);
	var elemColl = new Array();
	for (var i = 0; i< allElements.length; i++) {
		if (hasClass(allElements[i], className)) {
			elemColl[elemColl.length] = allElements[i];
		}
	}
	return elemColl;
}

function isParentOrSelf(element, id) {
	if (element == null || element.nodeName=='BODY') return false;
	else if (element.id == id) return true;
	else return isParentOrSelf(element.parentNode, id);
}

function nodeValue(node) {
	var result = "";
	if (node.nodeType == 1) {
		var children = node.childNodes;
		for (var i = 0; i < children.length; ++i) {
			result += nodeValue(children[i]);
		}
	}
	else if (node.nodeType == 3) {
		result = node.nodeValue;
	}
	return(result);
}

function slideLabel() {
	var slideColl = GetElementsWithClassName('*','slide');
	var list = document.getElementById('jumplist');
	smax = slideColl.length;
	for (var n = 0; n < smax; n++) {
		var obj = slideColl[n];

		var did = 'slide' + n.toString();
		if (obj.getAttribute('id')) {
			slideIDs[n] = obj.getAttribute('id');
		}
		else {
			obj.setAttribute('id',did);
			slideIDs[n] = did;
		}
		if (isOp) continue;

		var otext = '';
		var menu = obj.firstChild;
		if (!menu) continue; // to cope with empty slides
		while (menu && menu.nodeType == 3) {
			menu = menu.nextSibling;
		}
	 	if (!menu) continue; // to cope with slides with only text nodes

		var menunodes = menu.childNodes;
		for (var o = 0; o < menunodes.length; o++) {
			otext += nodeValue(menunodes[o]);
		}
		list.options[list.length] = new Option(n + ' : '  + otext, n);
	}
}

function currentSlide() {
	var cs;
	var footer_nodes;
	var vis = 'visible';
	if (document.getElementById) {
		cs = document.getElementById('currentSlide');
		footer_nodes = document.getElementById('footer').childNodes;
	} else {
		cs = document.currentSlide;
		footer = document.footer.childNodes;
	}
	cs.innerHTML = '<span id="csHere">' + snum + '<\/span> ' +
		'<span id="csSep">\/<\/span> ' +
		'<span id="csTotal">' + (smax-1) + '<\/span>';
	if (snum == 0) {
		vis = 'hidden';
	}
	cs.style.visibility = vis;
	for (var i = 0; i < footer_nodes.length; i++) {
		if (footer_nodes[i].nodeType == 1) {
			footer_nodes[i].style.visibility = vis;
		}
	}
}

function go(step) {
	if (document.getElementById('slideProj').disabled || step == 0) return;
	var jl = document.getElementById('jumplist');
	var cid = slideIDs[snum];
	var ce = document.getElementById(cid);
	if (incrementals[snum].length > 0) {
		for (var i = 0; i < incrementals[snum].length; i++) {
			removeClass(incrementals[snum][i], 'current');
			removeClass(incrementals[snum][i], 'incremental');
		}
	}
	if (step != 'j') {
		snum += step;
		lmax = smax - 1;
		if (snum > lmax) snum = lmax;
		if (snum < 0) snum = 0;
	} else
		snum = parseInt(jl.value);
	var nid = slideIDs[snum];
	var ne = document.getElementById(nid);
	if (!ne) {
		ne = document.getElementById(slideIDs[0]);
		snum = 0;
	}
	if (step < 0) {incpos = incrementals[snum].length} else {incpos = 0;}
	if (incrementals[snum].length > 0 && incpos == 0) {
		for (var i = 0; i < incrementals[snum].length; i++) {
			if (hasClass(incrementals[snum][i], 'current'))
				incpos = i + 1;
			else
				addClass(incrementals[snum][i], 'incremental');
		}
	}
	if (incrementals[snum].length > 0 && incpos > 0)
		addClass(incrementals[snum][incpos - 1], 'current');
	ce.style.visibility = 'hidden';
	ne.style.visibility = 'visible';
	jl.selectedIndex = snum;
	currentSlide();
	number = 0;
}

function goTo(target) {
	if (target >= smax || target == snum) return;
	go(target - snum);
}

function subgo(step) {
	if (step > 0) {
		removeClass(incrementals[snum][incpos - 1],'current');
		removeClass(incrementals[snum][incpos], 'incremental');
		addClass(incrementals[snum][incpos],'current');
		incpos++;
	} else {
		incpos--;
		removeClass(incrementals[snum][incpos],'current');
		addClass(incrementals[snum][incpos], 'incremental');
		addClass(incrementals[snum][incpos - 1],'current');
	}
}

function toggle() {
	var slideColl = GetElementsWithClassName('*','slide');
	var slides = document.getElementById('slideProj');
	var outline = document.getElementById('outlineStyle');
	if (!slides.disabled) {
		slides.disabled = true;
		outline.disabled = false;
		s5mode = false;
		fontSize('1em');
		for (var n = 0; n < smax; n++) {
			var slide = slideColl[n];
			slide.style.visibility = 'visible';
		}
	} else {
		slides.disabled = false;
		outline.disabled = true;
		s5mode = true;
		fontScale();
		for (var n = 0; n < smax; n++) {
			var slide = slideColl[n];
			slide.style.visibility = 'hidden';
		}
		slideColl[snum].style.visibility = 'visible';
	}
}

function showHide(action) {
	var obj = GetElementsWithClassName('*','hideme')[0];
	switch (action) {
	case 's': obj.style.visibility = 'visible'; break;
	case 'h': obj.style.visibility = 'hidden'; break;
	case 'k':
		if (obj.style.visibility != 'visible') {
			obj.style.visibility = 'visible';
		} else {
			obj.style.visibility = 'hidden';
		}
	break;
	}
}

// 'keys' code adapted from MozPoint (http://mozpoint.mozdev.org/)
function keys(key) {
	if (!key) {
		key = event;
		key.which = key.keyCode;
	}
	if (key.which == 84) {
		toggle();
		return;
	}
	if (s5mode) {
		switch (key.which) {
			case 10: // return
			case 13: // enter
				if (window.event && isParentOrSelf(window.event.srcElement, 'controls')) return;
				if (key.target && isParentOrSelf(key.target, 'controls')) return;
				if(number != undef) {
					goTo(number);
					break;
				}
			case 32: // spacebar
			case 34: // page down
			case 39: // rightkey
			case 40: // downkey
				if(number != undef) {
					go(number);
				} else if (!incrementals[snum] || incpos >= incrementals[snum].length) {
					go(1);
				} else {
					subgo(1);
				}
				break;
			case 33: // page up
			case 37: // leftkey
			case 38: // upkey
				if(number != undef) {
					go(-1 * number);
				} else if (!incrementals[snum] || incpos <= 0) {
					go(-1);
				} else {
					subgo(-1);
				}
				break;
			case 36: // home
				goTo(0);
				break;
			case 35: // end
				goTo(smax-1);
				break;
			case 67: // c
				showHide('k');
				break;
		}
		if (key.which < 48 || key.which > 57) {
			number = undef;
		} else {
			if (window.event && isParentOrSelf(window.event.srcElement, 'controls')) return;
			if (key.target && isParentOrSelf(key.target, 'controls')) return;
			number = (((number != undef) ? number : 0) * 10) + (key.which - 48);
		}
	}
	return false;
}

function clicker(e) {
	number = undef;
	var target;
	if (window.event) {
		target = window.event.srcElement;
		e = window.event;
	} else target = e.target;
    if (target.href != null || hasValue(target.rel, 'external') || isParentOrSelf(target, 'controls') || isParentOrSelf(target,'embed') || isParentOrSelf(target, 'object')) return true;
	if (!e.which || e.which == 1) {
		if (!incrementals[snum] || incpos >= incrementals[snum].length) {
			go(1);
		} else {
			subgo(1);
		}
	}
}

function findSlide(hash) {
	var target = document.getElementById(hash);
	if (target) {
		for (var i = 0; i < slideIDs.length; i++) {
			if (target.id == slideIDs[i]) return i;
		}
	}
	return null;
}

function slideJump() {
	if (window.location.hash == null || window.location.hash == '') {
		currentSlide();
		return;
	}
	if (window.location.hash == null) return;
	var dest = null;
	dest = findSlide(window.location.hash.slice(1));
	if (dest == null) {
		dest = 0;
	}
	go(dest - snum);
}

function fixLinks() {
	var thisUri = window.location.href;
	thisUri = thisUri.slice(0, thisUri.length - window.location.hash.length);
	var aelements = document.getElementsByTagName('A');
	for (var i = 0; i < aelements.length; i++) {
		var a = aelements[i].href;
		var slideID = a.match('\#.+');
		if ((slideID) && (slideID[0].slice(0,1) == '#')) {
			var dest = findSlide(slideID[0].slice(1));
			if (dest != null) {
				if (aelements[i].addEventListener) {
					aelements[i].addEventListener("click", new Function("e",
						"if (document.getElementById('slideProj').disabled) return;" +
						"go("+dest+" - snum); " +
						"if (e.preventDefault) e.preventDefault();"), true);
				} else if (aelements[i].attachEvent) {
					aelements[i].attachEvent("onclick", new Function("",
						"if (document.getElementById('slideProj').disabled) return;" +
						"go("+dest+" - snum); " +
						"event.returnValue = false;"));
				}
			}
		}
	}
}

function externalLinks() {
	if (!document.getElementsByTagName) return;
	var anchors = document.getElementsByTagName('a');
	for (var i=0; i<anchors.length; i++) {
		var anchor = anchors[i];
		if (anchor.getAttribute('href') && hasValue(anchor.rel, 'external')) {
			anchor.target = '_blank';
			addClass(anchor,'external');
		}
	}
}

function createControls() {
	var controlsDiv = document.getElementById("controls");
	if (!controlsDiv) return;
	var hider = ' onmouseover="showHide(\'s\');" onmouseout="showHide(\'h\');"';
	var hideDiv, hideList = '';
	if (controlVis == 'hidden') {
		hideDiv = hider;
	} else {
		hideList = hider;
	}
	controlsDiv.innerHTML = '<form action="#" id="controlForm"' + hideDiv + '>' +
	'<div id="navLinks">' +
	'<a accesskey="t" id="toggle" href="javascript:toggle();">&#216;<\/a>' +
	'<a accesskey="z" id="prev" href="javascript:go(-1);">&laquo;<\/a>' +
	'<a accesskey="x" id="next" href="javascript:go(1);">&raquo;<\/a>' +
	'<div id="navList"' + hideList + '><select id="jumplist" onchange="go(\'j\');"><\/select><\/div>' +
	'<\/div><\/form>';
	if (controlVis == 'hidden') {
		var hidden = document.getElementById('navLinks');
	} else {
		var hidden = document.getElementById('jumplist');
	}
	addClass(hidden,'hideme');
}

function fontScale() {  // causes layout problems in FireFox that get fixed if browser's Reload is used; same may be true of other Gecko-based browsers
	if (!s5mode) return false;
	var vScale = 22;  // both yield 32 (after rounding) at 1024x768
	var hScale = 32;  // perhaps should auto-calculate based on theme's declared value?
	if (window.innerHeight) {
		var vSize = window.innerHeight;
		var hSize = window.innerWidth;
	} else if (document.documentElement.clientHeight) {
		var vSize = document.documentElement.clientHeight;
		var hSize = document.documentElement.clientWidth;
	} else if (document.body.clientHeight) {
		var vSize = document.body.clientHeight;
		var hSize = document.body.clientWidth;
	} else {
		var vSize = 700;  // assuming 1024x768, minus chrome and such
		var hSize = 1024; // these do not account for kiosk mode or Opera Show
	}
	var newSize = Math.min(Math.round(vSize/vScale),Math.round(hSize/hScale));
	fontSize(newSize + 'px');
	if (isGe) {  // hack to counter incremental reflow bugs
		var obj = document.getElementsByTagName('body')[0];
		obj.style.display = 'none';
		obj.style.display = 'block';
	}
}

function fontSize(value) {
	if (!(s5ss = document.getElementById('s5ss'))) {
		if (!isIE) {
			document.getElementsByTagName('head')[0].appendChild(s5ss = document.createElement('style'));
			s5ss.setAttribute('media','screen, projection');
			s5ss.setAttribute('id','s5ss');
		} else {
			document.createStyleSheet();
			document.s5ss = document.styleSheets[document.styleSheets.length - 1];
		}
	}
	if (!isIE) {
		while (s5ss.lastChild) s5ss.removeChild(s5ss.lastChild);
		s5ss.appendChild(document.createTextNode('body {font-size: ' + value + ' !important;}'));
	} else {
		document.s5ss.addRule('body','font-size: ' + value + ' !important;');
	}
}

function notOperaFix() {
	slideCSS = document.getElementById('slideProj').href;
	var slides = document.getElementById('slideProj');
	var outline = document.getElementById('outlineStyle');
	slides.setAttribute('media','screen');
	outline.disabled = true;
	if (isGe) {
		slides.setAttribute('href','null');   // Gecko fix
		slides.setAttribute('href',slideCSS); // Gecko fix
	}
	if (isIE && document.styleSheets && document.styleSheets[0]) {
		document.styleSheets[0].addRule('img', 'behavior: url(ui/default/iepngfix.htc)');
		document.styleSheets[0].addRule('div', 'behavior: url(ui/default/iepngfix.htc)');
		document.styleSheets[0].addRule('.slide', 'behavior: url(ui/default/iepngfix.htc)');
	}
}

function getIncrementals(obj) {
	var incrementals = new Array();
	if (!obj)
		return incrementals;
	var children = obj.childNodes;
	for (var i = 0; i < children.length; i++) {
		var child = children[i];
		if (hasClass(child, 'incremental')) {
			if (child.nodeName == 'OL' || child.nodeName == 'UL') {
				removeClass(child, 'incremental');
				for (var j = 0; j < child.childNodes.length; j++) {
					if (child.childNodes[j].nodeType == 1) {
						addClass(child.childNodes[j], 'incremental');
					}
				}
			} else {
				incrementals[incrementals.length] = child;
				removeClass(child,'incremental');
			}
		}
		if (hasClass(child, 'show-first')) {
			if (child.nodeName == 'OL' || child.nodeName == 'UL') {
				removeClass(child, 'show-first');
				if (child.childNodes[isGe].nodeType == 1) {
					removeClass(child.childNodes[isGe], 'incremental');
				}
			} else {
				incrementals[incrementals.length] = child;
			}
		}
		incrementals = incrementals.concat(getIncrementals(child));
	}
	return incrementals;
}

function createIncrementals() {
	var incrementals = new Array();
	for (var i = 0; i < smax; i++) {
		incrementals[i] = getIncrementals(document.getElementById(slideIDs[i]));
	}
	return incrementals;
}

function defaultCheck() {
	var allMetas = document.getElementsByTagName('meta');
	for (var i = 0; i< allMetas.length; i++) {
		if (allMetas[i].name == 'defaultView') {
			defaultView = allMetas[i].content;
		}
		if (allMetas[i].name == 'controlVis') {
			controlVis = allMetas[i].content;
		}
	}
}

// Key trap fix, new function body for trap()
function trap(e) {
	if (!e) {
		e = event;
		e.which = e.keyCode;
	}
	try {
		modifierKey = e.ctrlKey || e.altKey || e.metaKey;
	}
	catch(e) {
		modifierKey = false;
	}
	return modifierKey || e.which == 0;
}

function startup() {
	defaultCheck();
	if (!isOp) createControls();
	slideLabel();
	fixLinks();
	externalLinks();
	fontScale();
	if (!isOp) {
		notOperaFix();
		incrementals = createIncrementals();
		slideJump();
		if (defaultView == 'outline') {
			toggle();
		}
		document.onkeyup = keys;
		document.onkeypress = trap;
		document.onclick = clicker;
	}
}

window.onload = startup;
window.onresize = function(){setTimeout('fontScale()', 50);}
