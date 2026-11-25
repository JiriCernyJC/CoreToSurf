"""Optional one-time registration of the pip-installed package with PyMOL.

PyMOL only loads plugins from the directories on its plugin startup path, not
from site-packages. Registration writes a tiny loader module into a user plugin
directory (adding that directory to the startup path if necessary), so the
plugin shows up in the Plugin menu on every PyMOL start. The loader only
imports the installed package, so ``pip install -U coretosurf`` takes effect
without registering again.

This uses PyMOL's own ``pymol.plugins`` API, so it must run with the Python
environment that PyMOL uses.
"""

import os

STUB_NAME = "coretosurf.py"
STUB_MARKER = "# coretosurf-loader"
STUB_TEMPLATE = '''{marker}
# Loader for the pip-installed "coretosurf" package. Created by
# `coretosurf install-plugin`; remove with `coretosurf uninstall-plugin`.
from coretosurf import __init_plugin__  # noqa: F401
'''


def _plugins(load_prefs):
    from pymol import plugins
    if load_prefs and os.path.exists(plugins.PYMOLPLUGINSRC):
        # Outside a running PyMOL the saved plugin preferences (including
        # user startup paths) are not loaded yet. Load them so that saving
        # does not discard existing settings.
        from pymol import parsing
        parsing.run_file(plugins.PYMOLPLUGINSRC,
                         {"__script__": plugins.PYMOLPLUGINSRC}, {})
    return plugins


def _choose_plugdir(plugins, plugdir):
    from pymol.plugins import installation
    if plugdir:
        return os.path.abspath(os.path.expanduser(plugdir))
    for d in plugins.get_startup_path(True):
        if installation.is_writable(d):
            return d
    return installation.get_default_user_plugin_path()


def install_plugin(plugdir=None, load_prefs=False, quiet=False):
    """Register CoreToSurf in PyMOL's Plugin menu. Returns the stub path."""
    plugins = _plugins(load_prefs)
    plugdir = _choose_plugdir(plugins, plugdir)
    if not os.path.isdir(plugdir):
        os.makedirs(plugdir)

    stub = os.path.join(plugdir, STUB_NAME)
    if os.path.exists(stub):
        with open(stub) as f:
            if not f.read().startswith(STUB_MARKER):
                raise RuntimeError(
                    "%s exists and was not created by coretosurf; "
                    "not overwriting it." % stub)
    with open(stub, "w") as f:
        f.write(STUB_TEMPLATE.format(marker=STUB_MARKER))

    user_paths = plugins.get_startup_path(True)
    if plugdir not in user_paths:
        # Saves ~/.pymolpluginsrc.py
        plugins.set_startup_path([plugdir] + user_paths, autosave=False)
        plugins.pref_save(quiet=1)

    if not quiet:
        print(" CoreToSurf: plugin loader written to %s" % stub)
        print(" CoreToSurf: restart PyMOL to see 'Core Boundary Surface' "
              "in the Plugin menu.")
    return stub


def uninstall_plugin(load_prefs=False, quiet=False):
    """Remove loader stubs created by install_plugin. Returns removed paths."""
    plugins = _plugins(load_prefs)
    removed = []
    for d in plugins.get_startup_path():
        stub = os.path.join(d, STUB_NAME)
        if not os.path.isfile(stub):
            continue
        with open(stub) as f:
            if not f.read().startswith(STUB_MARKER):
                continue
        os.remove(stub)
        removed.append(stub)
    if not quiet:
        if removed:
            for stub in removed:
                print(" CoreToSurf: removed %s" % stub)
        else:
            print(" CoreToSurf: no plugin loader found")
    return removed
