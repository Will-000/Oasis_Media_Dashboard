from nicegui import ui


def setup_history_listener(view_container):
    ui.on('popstate_event', lambda e: handle_popstate(e, view_container))
    ui.run_javascript('''
        window.onpopstate = function(event) {
            emitEvent('popstate_event', { path: window.location.pathname });
        };
    ''')


def handle_popstate(e, view_container):
    path = e.args.get('path', '')

    if not path.startswith('/view/'):
        view_container.clear()
        view_container.classes(remove='w-screen h-screen fixed inset-0 z-50 bg-black/85 flex flex-col justify-between overflow-hidden p-0 m-0')
