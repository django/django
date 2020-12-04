'use strict';
{
    const toggleNavSidebar = document.getElementById('toggle-nav-sidebar');
    if (toggleNavSidebar !== null) {
        const navLinks = document.querySelectorAll('#nav-sidebar a');
        function disableNavLinkTabbing() {
            for (const navLink of navLinks) {
                navLink.tabIndex = -1;
            }
        }
        function enableNavLinkTabbing() {
            for (const navLink of navLinks) {
                navLink.tabIndex = 0;
            }
        }

        const main = document.getElementById('main');
        let navSidebarIsOpen = localStorage.getItem('django.admin.navSidebarIsOpen');
        if (navSidebarIsOpen === null) {
            navSidebarIsOpen = 'true';
        }
        if (navSidebarIsOpen === 'false') {
            disableNavLinkTabbing();
        }
        main.classList.toggle('shifted', navSidebarIsOpen === 'true');

        toggleNavSidebar.addEventListener('click', function() {
            if (navSidebarIsOpen === 'true') {
                navSidebarIsOpen = 'false';
                disableNavLinkTabbing();
            } else {
                navSidebarIsOpen = 'true';
                enableNavLinkTabbing();
            }
            localStorage.setItem('django.admin.navSidebarIsOpen', navSidebarIsOpen);
            main.classList.toggle('shifted');
        });
    }

    // init quick filter
    (function() {
        const options = [];
        const navSidebar = document.getElementById('nav-sidebar');
        if (!navSidebar) { return; }
        navSidebar.querySelectorAll('th[scope=row] a').forEach((container) => {
            options.push({title: container.innerHTML, node: container});
        });

        function checkValue(e) {
            let v = e.target.value;
            if (v) { v = v.toLowerCase(); }
            if (e.key === 'Escape') { v = ''; e.target.value = ''; } // clear input
            for (const o of options) {
                // show/hide parent <TR>
                o.node.parentNode.parentNode.style.display =
                    (!v || o.title.toLowerCase().indexOf(v) !== -1) ? '' : 'none';
            }
        }

        const nav = document.getElementById('nav-filter');
        nav.addEventListener('change', checkValue, false);
        nav.addEventListener('keyup', checkValue, false);
    })();
}
