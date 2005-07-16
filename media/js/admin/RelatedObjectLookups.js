// Handles related-objects functionality: lookup link for raw_id_admin=True
// and Add Another links.

function showRelatedObjectLookupPopup(triggeringLink) {
    var name = triggeringLink.id.replace(/^lookup_/, '');
    var win = window.open(triggeringLink.href + '?pop=1', name, 'height=500,width=740,resizable=yes,scrollbars=yes');
    win.focus();
    return false;
}

function dismissRelatedLookupPopup(win, chosenId) {
    document.getElementById(win.name).value = chosenId;
    win.close();
}

function showAddAnotherPopup(triggeringLink) {
    var name = triggeringLink.id.replace(/^add_/, '');
    var win = window.open(triggeringLink.href + '?_popup=1', name, 'height=500,width=800,resizable=yes,scrollbars=yes');
    win.focus();
    return false;
}

function dismissAddAnotherPopup(win, newId, newRepr) {
    var elem = document.getElementById(win.name);
    if (elem.nodeName == 'SELECT') {
        var o = new Option(newRepr, newId);
        elem.appendChild(o);
        elem.selectedIndex = elem.length - 1;
    } else if (elem.nodeName == 'INPUT') {
        elem.value = newId;
    }
    win.close();
}