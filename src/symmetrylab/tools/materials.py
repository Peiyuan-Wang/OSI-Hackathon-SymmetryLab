"""Offline research-direction framework with explicit external-adapter boundaries."""
from urllib.parse import quote
from symmetrylab.verifier.hall import PRESETS, check_linear_ahe


FAMILIES = {
    "Transport": ["Linear anomalous Hall", "Second-order nonlinear Hall", "Third-order nonlinear Hall", "In-plane anomalous Hall", "Planar Hall", "Nonreciprocal transport", "Magnetoresistance"],
    "Thermal and thermoelectric": ["Anomalous Nernst", "Thermal Hall", "Nonlinear Nernst", "Magneto-Seebeck"],
    "Spintronics": ["Spin Hall", "Spin Nernst", "Spin-orbit torque", "Tunneling magnetoresistance", "Tunneling anisotropic magnetoresistance", "Spin pumping"],
    "Magnetism": ["Altermagnetic order", "Noncollinear magnetic order", "Magnetic anisotropy", "Domain-wall transport", "Chiral magnetic textures"],
    "Electronic topology": ["Weyl or Dirac nodes", "Nodal lines", "Crystalline topology", "Higher-order topology", "Surface and edge states"],
    "Optics and photocurrents": ["Second-harmonic generation", "Magneto-optical Kerr", "Faraday rotation", "Shift current", "Circular photogalvanic effect", "Nonreciprocal optics"],
    "Coupled order": ["Magnetoelectric response", "Ferroelectricity", "Multiferroicity", "Piezoelectric response", "Strain control"],
    "Superconductivity and correlations": ["Pairing symmetry", "Superconducting diode response", "Topological superconductivity", "Metal-insulator transition", "Quantum criticality"],
    "Collective modes and interfaces": ["Magnon topology", "Magnon-phonon coupling", "Charge-density waves", "Electronic nematicity", "Excitonic order", "Layer and stacking control", "Proximity effects"],
}


class SSGAdapter:
    """Replace with the team's database adapter; labels alone are not operations."""
    def lookup(self, material, conditions):
        return {"status": "not_connected", "records": [], "message": "No material-to-magnetic-structure or SSG database is connected."}


class LiteratureAdapter:
    """Replace with a provider returning cited evidence, never synthetic citations."""
    def search(self, material, phenomenon):
        query = material + " " + phenomenon + " magnetic symmetry"
        return {"status": "not_connected", "papers": [], "search_url": "https://scholar.google.com/scholar?q=" + quote(query), "message": "Search link only; no papers have been retrieved or validated."}


def catalog():
    return {"families": FAMILIES, "presets": {key: value["label"] for key, value in PRESETS.items()},
            "capabilities": {"linear_ahe": "exact_for_supplied_operations", "material_lookup": "not_connected", "ssg": "not_connected", "literature": "not_connected", "model_planning": "not_connected"}}


def explore_material(request, ssg_adapter=None, literature_adapter=None):
    if not isinstance(request, dict):
        raise ValueError("Supply an input object.")
    material = request.get("material", "")
    if not isinstance(material, str) or not 1 <= len(material.strip()) <= 160:
        raise ValueError("Enter a material name or formula (1–160 characters).")
    conditions = request.get("conditions", "")
    if not isinstance(conditions, str) or len(conditions) > 1500:
        raise ValueError("Conditions must contain at most 1500 characters.")
    preset = request.get("preset", "unknown")
    if preset not in {"unknown", "custom", *PRESETS}:
        raise ValueError("Unknown symmetry input mode.")
    component = request.get("component", "z")
    if component not in ("x", "y", "z"):
        raise ValueError("Select a Hall-vector component.")
    labels = {}
    for key in ("space_group", "msg", "ssg"):
        value = request.get(key, "")
        if not isinstance(value, str) or len(value) > 120:
            raise ValueError("Group labels must be strings of at most 120 characters.")
        labels[key] = {"value": value.strip(), "status": "user_supplied_unverified" if value.strip() else "unknown"}
    hall = None
    if preset != "unknown":
        generators = request.get("generators") if preset == "custom" else PRESETS[preset]["generators"]
        hall = check_linear_ahe(generators, component)
        hall["input_origin"] = "user_supplied" if preset == "custom" else "illustrative_preset_not_material_assignment"
    structure = (ssg_adapter or SSGAdapter()).lookup(material.strip(), conditions)
    literature = literature_adapter or LiteratureAdapter()
    cards = []
    for family, phenomena in FAMILIES.items():
        for phenomenon in phenomena:
            checked = phenomenon == "Linear anomalous Hall" and hall is not None
            status = hall["status"] if checked else ("needs_magnetic_structure" if phenomenon == "Linear anomalous Hall" else "not_evaluated")
            requirement = "A reliable magnetic structure, relevant symmetry operations, and measurement geometry."
            if "Tunneling" in phenomenon:
                requirement = "Both electrodes, barrier, interfaces, transport direction and relative magnetic configurations."
            elif family == "Superconductivity and correlations":
                requirement = "Electronic structure, interactions, phase evidence and mechanism-specific calculations."
            elif "nonlinear Hall" in phenomenon:
                requirement = "Response order, mechanism, spatial/antiunitary transformation law and measurement geometry."
            source = literature.search(material.strip(), phenomenon)
            cards.append({"id": "direction-" + str(len(cards) + 1), "family": family, "phenomenon": phenomenon,
                          "status": status, "priority": "computed_check" if checked else "unranked_catalog_entry",
                          "hypothesis": f"Investigate {phenomenon} in {material.strip()} under the specified conditions.",
                          "requirements": requirement, "evidence": hall if checked else None, "literature": source,
                          "next_step": "Check symmetry-breaking perturbations and recompute the actual new group." if checked and status == "symmetry_forbidden" else "Confirm prerequisites, consult primary literature, and design mechanism-specific controls.",
                          "limitation": "A catalog entry is not a material-specific prediction or an experimentally established effect."})
    trace = [{"stage": "profile", "message": "Material text and group labels recorded; no magnetic group inferred from the formula."},
             {"stage": "hypothesis", "message": "Enumerated research directions from a transparent catalog; entries are not ranked by scientific promise."}]
    if hall:
        trace.append({"stage": "verification", "message": f"Linear Hall-vector h_{component}: {hall['status']} for the supplied operations; certificate checked."})
        trace.append({"stage": "revision", "message": "Restrict the conclusion to this response component and these supplied operations. A perturbation must be assigned a new physical symmetry before another calculation."})
    else:
        trace.append({"stage": "missing_information", "message": "No symmetry computation performed: supply a validated magnetic structure or explicit Cartesian generators."})
    return {"schema_version": "materials-0.1", "mode": "offline_framework", "material": material.strip(),
            "conditions": conditions, "groups": labels, "structure_lookup": structure,
            "cards": cards, "hall": hall, "trace": trace,
            "counts": {"directions": len(cards), "computed": int(hall is not None), "literature_verified": 0},
            "disclaimer": "No material discovery, automatic group identification, live literature retrieval or LLM planning was performed. Illustrative symmetry presets are not assignments to the entered material."}
