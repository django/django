'use strict';
{
    const toggleNavSidebar = document.getElementById('toggle-nav-sidebar');
    if (toggleNavSidebar !== null) {
        const navSidebar = document.getElementById('nav-sidebar');
        const main = document.getElementById('main');
        let navSidebarIsOpen = localStorage.getItem('django.admin.navSidebarIsOpen');
        if (navSidebarIsOpen === null) {
            navSidebarIsOpen = 'true';
        }
        main.classList.toggle('shifted', navSidebarIsOpen === 'true');
        navSidebar.setAttribute('aria-expanded', navSidebarIsOpen);

        toggleNavSidebar.addEventListener('click', function() {
            if (navSidebarIsOpen === 'true') {
                navSidebarIsOpen = 'false';
            } else {
                navSidebarIsOpen = 'true';
            }
            localStorage.setItem('django.admin.navSidebarIsOpen', navSidebarIsOpen);
            main.classList.toggle('shifted');
            navSidebar.setAttribute('aria-expanded', navSidebarIsOpen);
        });
    }

    const mediaQuery = window.matchMedia('(max-width: 767px)');
    let filterSidebarToggleRegistered = false;
    function handleViewportChange(e) {
        const toggleFilterSidebar = document.getElementById('toggle-filter-sidebar');
        const filterSidebar = document.getElementById('changelist-filter');
        if (e.matches) {
            // Mobile
            if (toggleFilterSidebar !== null) {
                let filterSidebarIsOpen = localStorage.getItem('django.admin.filterSidebarIsOpen');
                if (filterSidebarIsOpen === null) {
                    filterSidebarIsOpen = 'true';
                }
                localStorage.setItem('django.admin.filterSidebarIsOpen', filterSidebarIsOpen);
                filterSidebar.classList.toggle('shifted', filterSidebarIsOpen === 'true');
                filterSidebar.setAttribute('aria-expanded', filterSidebarIsOpen);
                toggleFilterSidebar.setAttribute('aria-pressed', filterSidebarIsOpen);

                if (!filterSidebarToggleRegistered) {
                    toggleFilterSidebar.addEventListener('click', function() {
                        if (filterSidebarIsOpen === 'true') {
                            filterSidebarIsOpen = 'false';
                        } else {
                            filterSidebarIsOpen = 'true';
                        }
                        localStorage.setItem('django.admin.filterSidebarIsOpen', filterSidebarIsOpen);
                        filterSidebar.classList.toggle('shifted');
                        filterSidebar.setAttribute('aria-expanded', filterSidebarIsOpen);
                        toggleFilterSidebar.setAttribute('aria-pressed', filterSidebarIsOpen);
                    });
                    filterSidebarToggleRegistered = true;
                }
            }
        } else {
            // Tablet, Desktop
            filterSidebar.removeAttribute('aria-expanded');
        }
    }
    handleViewportChange(mediaQuery);
    mediaQuery.addEventListener('change', handleViewportChange);

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
}
