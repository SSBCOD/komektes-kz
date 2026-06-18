document.addEventListener('DOMContentLoaded', () => {
    const burger = document.querySelector('.burger-menu');
    const nav = document.querySelector('.nav-menu');

    if (burger && nav) {
        burger.addEventListener('click', () => {
            nav.classList.toggle('active');
        });
    }

    function setupNavIndicator(menu) {
        if (!menu) return;
        const links = Array.from(menu.querySelectorAll('.nav-link'));
        if (!links.length) return;

        let indicator = menu.querySelector('.nav-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.className = 'nav-indicator';
            menu.prepend(indicator);
        }

        function isMobileMenu() {
            return window.matchMedia('(max-width: 1100px)').matches;
        }

        function update() {
            if (isMobileMenu() || getComputedStyle(menu).display === 'none') {
                indicator.style.width = '0px';
                indicator.style.transform = 'translate3d(0, -50%, 0)';
                return;
            }

            const active = menu.querySelector('.nav-link.active') || links[0];
            const menuRect = menu.getBoundingClientRect();
            const rect = active.getBoundingClientRect();
            const left = rect.left - menuRect.left;
            indicator.style.width = rect.width + 'px';
            indicator.style.transform = `translate3d(${left}px, -50%, 0)`;
        }

        links.forEach((link) => {
            link.addEventListener('click', (e) => {
                if (e.defaultPrevented) return;
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
                const href = link.getAttribute('href') || '';
                if (!href || href.startsWith('#')) return;

                const isSameOrigin = href.startsWith('/') || href.startsWith(window.location.origin);
                if (!isSameOrigin) return;

                e.preventDefault();
                links.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
                update();
                setTimeout(() => {
                    window.location.href = href;
                }, 180);
            });
        });

        window.addEventListener('resize', update);
        update();
        requestAnimationFrame(() => {
            indicator.classList.add('is-ready');
        });
    }

    document.querySelectorAll('.nav-menu').forEach(setupNavIndicator);

    const searchForm = document.getElementById('searchForm');

    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            const input = searchForm.querySelector('input');
            if (input && input.value.trim() === "") {
                e.preventDefault();
                input.style.borderColor = "red";
                setTimeout(() => {
                    input.style.borderColor = "";
                }, 800);
            }
        });
    }
});
