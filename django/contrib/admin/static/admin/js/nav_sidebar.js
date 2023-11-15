'use strict';
{
    function handleSidebarToggle(toggleElementId, sidebarID, storeProperty) {
        const toggleNode = document.getElementById(toggleElementId);
        if (toggleNode === null) {
            return;
        }

        const toggleClass = `${sidebarID}-expanded`;
        let sidebarIsOpen = localStorage.getItem(storeProperty) !== 'false';

        const mainNode = document.getElementById('main');
        mainNode.classList.toggle(toggleClass, sidebarIsOpen);

        const sidebarNode = document.getElementById(sidebarID);
        sidebarNode.setAttribute('aria-expanded', sidebarIsOpen);

        toggleNode.addEventListener('click', function () {
            sidebarIsOpen = !sidebarIsOpen;
            localStorage.setItem(storeProperty, sidebarIsOpen);
            mainNode.classList.toggle(toggleClass);
            sidebarNode.setAttribute('aria-expanded', sidebarIsOpen);
        });
    }

    function initSidebarQuickFilter() {
        const options = [];
        const navSidebar = document.getElementById('nav-sidebar');
        if (!navSidebar) {
            return;
        }
        navSidebar.querySelectorAll('th[scope=row] a').forEach((container) => {
            options.push({title: container.innerHTML, node: container});
        });

        function checkValue(event) {
            let filterValue = event.target.value;
            if (filterValue) {
                filterValue = filterValue.toLowerCase();
            }
            if (event.key === 'Escape') {
                filterValue = '';
                event.target.value = ''; // clear input
            }
            let matches = false;
            for (const o of options) {
                let displayValue = '';
                if (filterValue) {
                    if (o.title.toLowerCase().indexOf(filterValue) === -1) {
                        displayValue = 'none';
                    } else {
                        matches = true;
                    }
                }
                // show/hide parent <TR>
                o.node.parentNode.parentNode.style.display = displayValue;
            }
            if (!filterValue || matches) {
                event.target.classList.remove('no-results');
            } else {
                event.target.classList.add('no-results');
            }
            sessionStorage.setItem('django.admin.navSidebarFilterValue', filterValue);
        }

        const nav = document.getElementById('nav-filter');
        nav.addEventListener('change', checkValue, false);
        nav.addEventListener('input', checkValue, false);
        nav.addEventListener('keyup', checkValue, false);

        const storedValue = sessionStorage.getItem('django.admin.navSidebarFilterValue');
        if (storedValue) {
            nav.value = storedValue;
            checkValue({target: nav, key: ''});
        }
    }
    window.initSidebarQuickFilter = initSidebarQuickFilter;
    initSidebarQuickFilter();

    // right sidebar (filter)
    handleSidebarToggle(
        'toggle-filter-sidebar',
        'changelist-filter',
        'django.admin.filterSidebarIsOpen',
    );

    // left sidebar (nav)
    handleSidebarToggle(
        'toggle-nav-sidebar',
        'nav-sidebar',
        'django.admin.navSidebarIsOpen',
    );

}
