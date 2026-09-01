from nicegui import ui


def base_layout():
    """ Applies background and header """
    ui.query('body').classes('bg-primary')

    with ui.header().classes("bg-secondary text-accent w-full p-4 transition-transform duration-300 transform").props('id="app-header"'):
        with ui.row().classes("w-full items-center justify-between gap-2"):
            ui.label("Oasis").classes("text-accent text-2xl text-bold").on('click', lambda: ui.navigate.to("/home"))
            with ui.dropdown_button(icon="menu").classes("rounded text-accent").props(
                    'flat content-style="background-color: var(--q-primary); color: var(--q-accent); font-size: 0.75rem; border: 1px solid var(--q-secondary)"'):
                ui.item("Home", on_click=lambda: ui.navigate.to("/home"))
                ui.item("Bookmarks", on_click=lambda: ui.navigate.to("/view/bookmarks"))
                ui.item("Local", on_click=lambda: ui.navigate.to("/view/local"))
                ui.item("Scraper", on_click=lambda: ui.navigate.to("/scraper"))
                ui.item("Settings", on_click=lambda: ui.navigate.to("/settings"))

    # Scrolling header
    ui.run_javascript('''
        (function() {
            let lastScrollY = window.scrollY;
            const header = document.getElementById("app-header");

            if (!header) return;

            window.onscroll = () => {
                const currentScrollY = window.scrollY;

                if (currentScrollY > lastScrollY && currentScrollY > 50) {
                    // Scrolling Down -> Hide Header
                    header.classList.add("-translate-y-full");
                } else {
                    // Scrolling Up -> Show Header
                    header.classList.remove("-translate-y-full");
                }

                lastScrollY = currentScrollY;
            };
        })();
    ''')
