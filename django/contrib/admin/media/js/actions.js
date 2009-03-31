var Actions = {
    init: function() {
        var selectAll = document.getElementById('action-toggle');
        if (selectAll) {
            selectAll.style.display = 'inline';
            addEvent(selectAll, 'click', function() {
                Actions.checker(selectAll.checked);
            });
        }
        var changelistTable = document.getElementsBySelector('#changelist table')[0];
        addEvent(changelistTable, 'click', function(e) {
            if (!e) { var e = window.event; }
            var target = e.target ? e.target : e.srcElement;
            if (target.nodeType == 3) { target = target.parentNode; }
            if (target.className == 'action-select') {
                var tr = target.parentNode.parentNode;
                Actions.toggleRow(tr, target.checked);
            }
        });
    },
    toggleRow: function(tr, checked) {
        if (checked && tr.className.indexOf('selected') == -1) {
            tr.className += ' selected';
        } else if (!checked) {
            tr.className = tr.className.replace(' selected', '');
        }  
    },
    checker: function(checked) {
        var actionCheckboxes = document.getElementsBySelector('tr input.action-select');
        for(var i = 0; i < actionCheckboxes.length; i++) {
            actionCheckboxes[i].checked = checked;
            Actions.toggleRow(actionCheckboxes[i].parentNode.parentNode, checked);
        }
    }
};

addEvent(window, 'load', Actions.init);
