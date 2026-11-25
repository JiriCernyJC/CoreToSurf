"""SASA calculation, caching and core/boundary/surface classification.

This module has no Qt dependency, so it can be used from scripts and from the
``coretosurf`` PyMOL command as well as from the GUI.
"""

from pymol import cmd

# Theoretical maximum ASA per residue (Å²), Tien et al. 2013, PLoS ONE 8:e80635.
MAX_ASA = {
    "ALA": 129.0, "ARG": 274.0, "ASN": 195.0, "ASP": 193.0, "CYS": 167.0,
    "GLN": 225.0, "GLU": 223.0, "GLY": 104.0, "HIS": 224.0, "ILE": 197.0,
    "LEU": 201.0, "LYS": 236.0, "MET": 224.0, "PHE": 240.0, "PRO": 159.0,
    "SER": 155.0, "THR": 172.0, "TRP": 285.0, "TYR": 263.0, "VAL": 174.0,
}
# Common non-standard / force-field residue names mapped to their parent.
ALIASES = {
    "MSE": "MET", "HID": "HIS", "HIE": "HIS", "HIP": "HIS", "HSD": "HIS",
    "HSE": "HIS", "HSP": "HIS", "CYX": "CYS", "CYM": "CYS", "ASH": "ASP",
    "GLH": "GLU", "LYN": "LYS", "SEP": "SER", "TPO": "THR", "PTR": "TYR",
}
DEFAULT_MAX_ASA = 200.0  # fallback for residues without a reference value

LAYERS = ("core", "boundary", "surface")
COLORS = {"core": "orange", "boundary": "green", "surface": "blue"}

# Default cutoffs per unit: (core, boundary).
# Absolute values follow Rosetta's LayerSelector SASA mode.
DEFAULT_CUTOFFS = {"abs": (20.0, 40.0), "rel": (20.0, 50.0)}

# Cache: (object, state) -> {"natoms": int, "residues": [Residue, ...]}
_cache = {}


class Residue(object):
    __slots__ = ("segi", "chain", "resi", "resn", "sasa", "rel")

    def __init__(self, segi, chain, resi, resn, sasa):
        self.segi, self.chain, self.resi, self.resn = segi, chain, resi, resn
        self.sasa = sasa
        ref = MAX_ASA.get(ALIASES.get(resn, resn), DEFAULT_MAX_ASA)
        self.rel = 100.0 * sasa / ref

    def value(self, unit):
        return self.rel if unit == "rel" else self.sasa


def _compute(obj, state):
    """Per-residue SASA of polymer residues in ``obj``.

    Waters and hydrogens are removed first. Ligands and other hetero atoms are
    kept so that they occlude the polymer, but only polymer residues are
    reported.
    """
    tmp = cmd.get_unused_name("_c2s_tmp")
    try:
        cmd.create(tmp, "(%s) and not solvent and not hydro" % obj,
                   source_state=state, target_state=1, zoom=0)
        cmd.set("dot_solvent", 1, tmp)
        cmd.set("dot_density", 3, tmp)
        cmd.get_area(tmp, state=1, load_b=1)

        sums = {}
        order = []

        def add(segi, chain, resi, resn, b):
            key = (segi, chain, resi)
            if key not in sums:
                sums[key] = [resn, 0.0]
                order.append(key)
            sums[key][1] += b

        cmd.iterate("%s and polymer" % tmp,
                    "add(segi, chain, resi, resn, b)",
                    space={"add": add})
    finally:
        cmd.delete(tmp)

    return [Residue(k[0], k[1], k[2], sums[k][0], sums[k][1]) for k in order]


def get_residues(obj, state=-1, force=False):
    """Return cached per-residue SASA for ``obj``, computing it if needed.

    The cache is invalidated automatically if the atom count of the object
    changes (e.g. atoms were added or removed).
    """
    if state in (-1, 0):
        state = cmd.get_state()
    key = (obj, state)
    natoms = cmd.count_atoms(obj)
    entry = _cache.get(key)
    if force or entry is None or entry["natoms"] != natoms:
        entry = {"natoms": natoms, "residues": _compute(obj, state)}
        _cache[key] = entry
    return entry["residues"]


def clear_cache(obj=None):
    if obj is None:
        _cache.clear()
    else:
        for key in [k for k in _cache if k[0] == obj]:
            del _cache[key]


def classify(residues, core_cut, boundary_cut, unit="abs"):
    """Split residues into layers. Returns {layer: [Residue, ...]}."""
    out = {name: [] for name in LAYERS}
    for r in residues:
        v = r.value(unit)
        if v < core_cut:
            out["core"].append(r)
        elif v < boundary_cut:
            out["boundary"].append(r)
        else:
            out["surface"].append(r)
    return out


def _escape_resi(resi):
    # A leading minus would be read as a range operator.
    return "\\" + resi if resi.startswith("-") else resi


def _selection_expr(obj, residues):
    """Build one compact selection expression for a list of residues."""
    if not residues:
        return "none"
    groups = {}
    for r in residues:
        groups.setdefault((r.segi, r.chain), []).append(_escape_resi(r.resi))
    parts = []
    for (segi, chain), resis in groups.items():
        parts.append("(segi '%s' and chain '%s' and resi %s)"
                     % (segi, chain, "+".join(resis)))
    return "(%s) and (%s)" % (obj, " or ".join(parts))


def apply_layers(obj, core_cut, boundary_cut, unit="abs", state=-1,
                 color=True, prefix=""):
    """Create the core/boundary/surface selections and color them.

    Returns a dict with the number of residues per layer.
    """
    residues = get_residues(obj, state)
    layers = classify(residues, core_cut, boundary_cut, unit)
    for name in LAYERS:
        sele = prefix + name
        cmd.select(sele, _selection_expr(obj, layers[name]), enable=0)
        if color:
            cmd.color(COLORS[name], "%s and elem C" % sele)
    return {name: len(layers[name]) for name in LAYERS}
