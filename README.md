# CoreToSurf

A PyMOL 3 plugin for interactive classification of residues into **core**
(orange), **boundary** (green) and **surface** (blue) based on solvent
accessible surface area (SASA).

## Installation

Install with the **same Python environment that PyMOL uses**. PyMOL itself is
not a pip dependency (it is installed with conda or the Schrödinger installer).

```
# from a clone of this repository
python -m pip install .
# or straight from git
python -m pip install git+https://github.com/ajasja/CoreToSurf.git
```

For a conda install of PyMOL, activate its environment first, or call its
Python directly, e.g. `C:\path\to\conda\envs\pymol\python -m pip install .`.
For development use `pip install -e .`.

### Using it

**Option A: load on demand.** At the PyMOL prompt (or in `~/.pymolrc`):

```
import coretosurf
coretosurf          # opens the window
```

**Option B: add it to the Plugin menu (one time).** Register the plugin once:

```
coretosurf install-plugin           # from a shell
python -m coretosurf install-plugin # same, if the Scripts dir is not on PATH
```

or, at the PyMOL prompt, `import coretosurf; coretosurf.install_plugin()`.
This writes a small loader (`coretosurf.py`) into PyMOL's user plugin
directory (`%APPDATA%\pymol\startup` on Windows, `~/.pymol/startup`
elsewhere, or the first writable directory already on PyMOL's plugin path)
and adds that directory to PyMOL's plugin path. *Plugin → Core Boundary
Surface* is then available on every start. Because the loader only imports the
installed package, upgrading with pip does not require registering again.
Remove it with `coretosurf uninstall-plugin`.

**Option C: classic plugin install without pip.** *Plugin → Plugin Manager →
Install New Plugin* and choose a zip of the `src/coretosurf` folder.

## Window

- **Object**: the molecular object to classify (*Refresh list* after loading new ones).
- **SASA units**: absolute (Å², 0–250) or relative (% of the theoretical
  maximum ASA from Tien et al. 2013, 0–100). Each unit remembers its own cutoffs.
- **Core cutoff**: residues with SASA below this value are core.
- **Boundary cutoff**: residues with SASA from the core cutoff up to this value are
  boundary. Residues at or above it are surface. The two sliders are kept so that core ≤ boundary.
- **Live update**: when checked, the selections update while a slider is dragged;
  when unchecked, they update when the slider is released.
- **Recompute SASA**: discard the cached SASA and recalculate.
- **Format** + **Print + copy to clipboard**: print the three layers to the
  PyMOL log and copy them to the clipboard, using PDB residue numbers and chains:
  - *PyMOL selection* (default), ready to paste back into PyMOL:
    `select core, (chain A and resi 1-5+9) or (chain B and resi 3+5)`
  - *Rosetta ResidueIndexSelector* (`resnums` format):
    `core: 1A-5A,9A,3B,5B`.
    This format cannot express residues with insertion codes, negative residue numbers or
    blank or multi-letter chain ids. Such residues are omitted, and a warning
    in the PyMOL log lists them.

The plugin creates three selections named `core`, `boundary` and `surface`, and
colors their carbon atoms. The representation is not changed.

Default cutoffs: 20 / 40 Å² (Rosetta LayerSelector SASA mode) and 20 / 50 %.

## PyMOL command

```
coretosurf                      # open the GUI
coretosurf 1ubq, 20, 40         # absolute Å²
coretosurf 1ubq, 20, 50, rel    # relative %
coretosurf 1ubq, recompute=1    # force SASA recalculation
coretosurf_print                # print + copy last result (PyMOL format)
coretosurf_print rosetta        # ... as Rosetta ResidueIndexSelector
coretosurf_print copy=0         # print only
```

## How SASA is computed

- Whole-residue SASA is calculated once per object and state with `get_area`
  (`dot_solvent=1`, `dot_density=3`) on a temporary copy of the object.
- Waters and hydrogens are removed before the calculation. Ligands and other
  hetero atoms are kept so they occlude the polymer, but only polymer residues
  are classified.
- The result is cached. Moving a slider only reclassifies the cached values.
- The cache is invalidated automatically when the object's atom count changes.
  After other edits, such as moving atoms, changing coordinates or renumbering
  residues, press *Recompute SASA*.
