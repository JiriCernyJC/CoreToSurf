"""Qt window for interactive core/boundary/surface selection."""

from pymol import cmd
from pymol.Qt import QtCore, QtWidgets

from . import sasa

Qt = QtCore.Qt

# Slider ranges per unit: (maximum, label)
UNIT_RANGE = {"abs": (250, "Å²"), "rel": (100, "%")}


class CoreToSurfWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CoreToSurfWindow, self).__init__(parent, Qt.Window)
        self.setWindowTitle("Core / Boundary / Surface")
        self.unit = "abs"
        # Remember cutoffs per unit so switching units restores them.
        self.cutoffs = {u: list(v) for u, v in sasa.DEFAULT_CUTOFFS.items()}
        self._build_ui()
        self.refresh_objects()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Object picker
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Object:"))
        self.obj_combo = QtWidgets.QComboBox()
        self.obj_combo.setMinimumWidth(160)
        row.addWidget(self.obj_combo, 1)
        btn = QtWidgets.QPushButton("Refresh list")
        btn.clicked.connect(self.refresh_objects)
        row.addWidget(btn)
        layout.addLayout(row)

        # Units
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("SASA units:"))
        self.abs_radio = QtWidgets.QRadioButton("Absolute (Å²)")
        self.rel_radio = QtWidgets.QRadioButton("Relative (% of max ASA)")
        self.abs_radio.setChecked(True)
        self.abs_radio.toggled.connect(self._on_unit_changed)
        row.addWidget(self.abs_radio)
        row.addWidget(self.rel_radio)
        row.addStretch(1)
        layout.addLayout(row)

        # Sliders
        grid = QtWidgets.QGridLayout()
        self.core_slider, self.core_label = self._make_slider()
        self.bound_slider, self.bound_label = self._make_slider()
        grid.addWidget(QtWidgets.QLabel("Core cutoff:"), 0, 0)
        grid.addWidget(self.core_slider, 0, 1)
        grid.addWidget(self.core_label, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Boundary cutoff:"), 1, 0)
        grid.addWidget(self.bound_slider, 1, 1)
        grid.addWidget(self.bound_label, 1, 2)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.core_slider.valueChanged.connect(self._on_core_changed)
        self.bound_slider.valueChanged.connect(self._on_bound_changed)
        self.core_slider.sliderReleased.connect(self.update_selection)
        self.bound_slider.sliderReleased.connect(self.update_selection)

        # Live update checkbox
        self.live_check = QtWidgets.QCheckBox(
            "Live update (update while dragging)")
        self.live_check.setChecked(True)
        self.live_check.toggled.connect(self._on_live_toggled)
        layout.addWidget(self.live_check)

        # Buttons
        row = QtWidgets.QHBoxLayout()
        apply_btn = QtWidgets.QPushButton("Apply")
        apply_btn.clicked.connect(self.update_selection)
        recompute_btn = QtWidgets.QPushButton("Recompute SASA")
        recompute_btn.clicked.connect(self.recompute)
        row.addWidget(apply_btn)
        row.addWidget(recompute_btn)
        layout.addLayout(row)

        # Status line
        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.obj_combo.currentIndexChanged.connect(
            lambda _i: self.update_selection())

        self._apply_unit_to_sliders()

    def _make_slider(self):
        slider = QtWidgets.QSlider(Qt.Horizontal)
        slider.setMinimumWidth(220)
        label = QtWidgets.QLabel()
        label.setMinimumWidth(60)
        return slider, label

    # ------------------------------------------------------------- helpers
    def _apply_unit_to_sliders(self):
        maximum, _ = UNIT_RANGE[self.unit]
        core, bound = self.cutoffs[self.unit]
        for slider, value in ((self.core_slider, core),
                              (self.bound_slider, bound)):
            slider.blockSignals(True)
            slider.setRange(0, maximum)
            slider.setValue(int(round(value)))
            slider.blockSignals(False)
        self._update_labels()

    def _update_labels(self):
        _, suffix = UNIT_RANGE[self.unit]
        self.core_label.setText("%d %s" % (self.core_slider.value(), suffix))
        self.bound_label.setText("%d %s" % (self.bound_slider.value(), suffix))

    def _maybe_update(self, slider):
        # With live update off, wait for the slider to be released. Changes
        # made with the keyboard or mouse wheel (slider not held down) still
        # apply immediately.
        if self.live_check.isChecked() or not slider.isSliderDown():
            self.update_selection()

    # -------------------------------------------------------------- slots
    def _on_core_changed(self, value):
        if value > self.bound_slider.value():
            self.bound_slider.blockSignals(True)
            self.bound_slider.setValue(value)
            self.bound_slider.blockSignals(False)
        self._store_cutoffs()
        self._maybe_update(self.core_slider)

    def _on_bound_changed(self, value):
        if value < self.core_slider.value():
            self.core_slider.blockSignals(True)
            self.core_slider.setValue(value)
            self.core_slider.blockSignals(False)
        self._store_cutoffs()
        self._maybe_update(self.bound_slider)

    def _store_cutoffs(self):
        self.cutoffs[self.unit] = [self.core_slider.value(),
                                   self.bound_slider.value()]
        self._update_labels()

    def _on_unit_changed(self, _checked):
        self.unit = "abs" if self.abs_radio.isChecked() else "rel"
        self._apply_unit_to_sliders()
        self.update_selection()

    def _on_live_toggled(self, _checked):
        self.update_selection()

    # ------------------------------------------------------------ actions
    def refresh_objects(self):
        current = self.obj_combo.currentText()
        names = [n for n in cmd.get_names("objects")
                 if cmd.get_type(n) == "object:molecule"]
        self.obj_combo.blockSignals(True)
        self.obj_combo.clear()
        self.obj_combo.addItems(names)
        if current in names:
            self.obj_combo.setCurrentIndex(names.index(current))
        self.obj_combo.blockSignals(False)
        self.update_selection()

    def recompute(self):
        obj = self.obj_combo.currentText()
        if obj:
            sasa.clear_cache(obj)
        self.update_selection()

    def update_selection(self):
        obj = self.obj_combo.currentText()
        if not obj:
            self.status.setText("No molecular object loaded. "
                                "Load one and press 'Refresh list'.")
            return
        if obj not in cmd.get_names("objects"):
            self.status.setText("Object '%s' no longer exists." % obj)
            return
        core, bound = self.cutoffs[self.unit]
        try:
            counts = sasa.apply_layers(obj, core, bound, self.unit)
        except Exception as e:  # report errors in the window, not a traceback
            self.status.setText("Error: %s" % e)
            return
        self.status.setText(
            "core: %(core)d   boundary: %(boundary)d   surface: %(surface)d "
            "residues" % counts)


_window = None


def show_window():
    global _window
    if _window is None:
        parent = None
        try:
            from pymol import gui
            parent = gui.get_qtwindow()
        except Exception:
            pass
        _window = CoreToSurfWindow(parent)
    else:
        _window.refresh_objects()
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
