var Actions = {
    init: function() {
        counterSpans = document.getElementsBySelector('span._acnt');
        counterContainer = document.getElementsBySelector('span.action_counter');
        actionCheckboxes = document.getElementsBySelector('tr input.action-select');
        selectAll = document.getElementById('action-toggle');
        lastChecked = null;
        for(var i = 0; i < counterContainer.length; i++) {
            counterContainer[i].style.display = 'inline';
        }
        if (selectAll) {
            selectAll.style.display = 'inline';
            addEvent(selectAll, 'click', function() {
                Actions.checker(selectAll.checked);
                Actions.counter();
            });
        }
        for(var i = 0; i < actionCheckboxes.length; i++) {
            addEvent(actionCheckboxes[i], 'click', function(e) {
                if (!e) { var e = window.event; }
                var target = e.target ? e.target : e.srcElement;
                if (lastChecked && lastChecked != target && e.shiftKey == true) {
                    var inrange = false;
                    lastChecked.checked = target.checked;
                    Actions.toggleRow(lastChecked.parentNode.parentNode, target.checked);
                    for (var i = 0; i < actionCheckboxes.length; i++) {
                        if (actionCheckboxes[i] == lastChecked || actionCheckboxes[i] == target) {
                            inrange = (inrange) ? false : true;
                        }
                        if (inrange) {
                            actionCheckboxes[i].checked = target.checked;
                            Actions.toggleRow(actionCheckboxes[i].parentNode.parentNode, target.checked);
                        }
                    }
                }
                lastChecked = target;
                Actions.counter();
            });
        }
        var changelistTable = document.getElementsBySelector('#changelist table')[0];
        if (changelistTable) {
            addEvent(changelistTable, 'click', function(e) {
                if (!e) { var e = window.event; }
                var target = e.target ? e.target : e.srcElement;
                if (target.nodeType == 3) { target = target.parentNode; }
                if (target.className == 'action-select') {
                    var tr = target.parentNode.parentNode;
                    Actions.toggleRow(tr, target.checked);
                }
            });
        }
    },
    toggleRow: function(tr, checked) {
        if (checked && tr.className.indexOf('selected') == -1) {
            tr.className += ' selected';
        } else if (!checked) {
            tr.className = tr.className.replace(' selected', '');
        }  
    },
    checked: function() {
        selectAll.checked = false;
    },
    checker: function(checked) {
        for(var i = 0; i < actionCheckboxes.length; i++) {
            actionCheckboxes[i].checked = checked;
            Actions.toggleRow(actionCheckboxes[i].parentNode.parentNode, checked);
        }
    },
    counter: function() {
        counter = 0;
        for(var i = 0; i < actionCheckboxes.length; i++) {
            if(actionCheckboxes[i].checked){
                counter++;
            }
        }
        for(var i = 0; i < counterSpans.length; i++) {
            counterSpans[i].innerHTML = counter;
        }
        selectAll.checked = (counter == actionCheckboxes.length);
    }
};

addEvent(window, 'load', Actions.init);