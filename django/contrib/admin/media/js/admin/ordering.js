addEvent(window, 'load', reorder_init);

var lis;
var top = 0;
var left = 0;
var height = 30;

function reorder_init() {
    lis = document.getElementsBySelector('ul#orderthese li');
    var input = document.getElementsBySelector('input[name=order_]')[0];
    setOrder(input.value.split(','));
    input.disabled = true;
    draw();
    // Now initialise the dragging behaviour
    var limit = (lis.length - 1) * height;
    for (var i = 0; i < lis.length; i++) {
        var li = lis[i];
        var img = document.getElementById('handle'+li.id);
        li.style.zIndex = 1;
        Drag.init(img, li, left + 10, left + 10, top + 10, top + 10 + limit);
        li.onDragStart = startDrag;
        li.onDragEnd = endDrag;
        img.style.cursor = 'move';
    }
}

function submitOrderForm() {
    var inputOrder = document.getElementsBySelector('input[name=order_]')[0];
    inputOrder.value = getOrder();
    inputOrder.disabled=false;
}

function startDrag() {
    this.style.zIndex = '10';
    this.className = 'dragging';
}

function endDrag(x, y) {
    this.style.zIndex = '1';
    this.className = '';
    // Work out how far along it has been dropped, using x co-ordinate
    var oldIndex = this.index;
    var newIndex = Math.round((y - 10 - top) / height);
    // 'Snap' to the correct position
    this.style.top = (10 + top + newIndex * height) + 'px';
    this.index = newIndex;
    moveItem(oldIndex, newIndex);
}

function moveItem(oldIndex, newIndex) {
    // Swaps two items, adjusts the index and left co-ord for all others
    if (oldIndex == newIndex) {
        return; // Nothing to swap;
    }
    var direction, lo, hi;
    if (newIndex > oldIndex) {
        lo = oldIndex;
        hi = newIndex;
        direction = -1;
    } else {
        direction = 1;
        hi = oldIndex;
        lo = newIndex;
    }
    var lis2 = new Array(); // We will build the new order in this array
    for (var i = 0; i < lis.length; i++) {
        if (i < lo || i > hi) {
            // Position of items not between the indexes is unaffected
            lis2[i] = lis[i];
            continue;
        } else if (i == newIndex) {
            lis2[i] = lis[oldIndex];
            continue;
        } else {
            // Item is between the two indexes - move it along 1
            lis2[i] = lis[i - direction];
        }
    }
    // Re-index everything
    reIndex(lis2);
    lis = lis2;
    draw();
//    document.getElementById('hiddenOrder').value = getOrder();
    document.getElementsBySelector('input[name=order_]')[0].value = getOrder();
}

function reIndex(lis) {
    for (var i = 0; i < lis.length; i++) {
        lis[i].index = i;
    }
}

function draw() {
    for (var i = 0; i < lis.length; i++) {
        var li = lis[i];
        li.index = i;
        li.style.position = 'absolute';
        li.style.left = (10 + left) + 'px';
        li.style.top = (10 + top + (i * height)) + 'px';
    }
}

function getOrder() {
    var order = new Array(lis.length);
    for (var i = 0; i < lis.length; i++) {
        order[i] = lis[i].id.substring(1, 100);
    }
    return order.join(',');
}

function setOrder(id_list) {
    /* Set the current order to match the lsit of IDs */
    var temp_lis = new Array();
    for (var i = 0; i < id_list.length; i++) {
        var id = 'p' + id_list[i];
        temp_lis[temp_lis.length] = document.getElementById(id);
    }
    reIndex(temp_lis);
    lis = temp_lis;
    draw();
}

function addEvent(elm, evType, fn, useCapture)
// addEvent and removeEvent
// cross-browser event handling for IE5+,  NS6 and Mozilla
// By Scott Andrew
{
  if (elm.addEventListener){
    elm.addEventListener(evType, fn, useCapture);
    return true;
  } else if (elm.attachEvent){
    var r = elm.attachEvent("on"+evType, fn);
    return r;
  } else {
    elm['on'+evType] = fn;
  }
}
