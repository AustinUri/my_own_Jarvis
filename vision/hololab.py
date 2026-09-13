from __future__ import annotations

import math
import time
from typing import Any

DENSITY_G_CM3 = {"aluminium": 2.70, "aluminum": 2.70, "titanium": 4.51,
                  "steel": 7.85, "abs": 1.04, "pla": 1.24, "polycarbonate": 1.20}

def _f(v: Any, default: float, lo: float, hi: float) -> float:
    try: return max(lo, min(hi, float(v)))
    except Exception: return default

def run_visual_tests(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    d=payload or {}; shape=str(d.get("shape") or "cube").lower(); material=str(d.get("material") or "aluminium").lower()
    w=_f(d.get("width_mm"),100,1,5000); h=_f(d.get("height_mm"),100,1,5000); dep=_f(d.get("depth_mm"),60,1,5000)
    hand=bool(d.get("hand_detected")); pinch=bool(d.get("pinch")); two=bool(d.get("two_hands"))
    if shape=="sphere":
        dia=(w+h+dep)/3; r=dia/2; vol=(4/3)*math.pi*r**3; area=4*math.pi*r*r; dims={"diameter_mm":round(dia,2)}
    elif shape=="ring":
        outer=max(w,h); minor=max(1,min(dep,outer*.42))/2; major=max(minor+1,outer/2-minor); vol=2*math.pi**2*major*minor**2; area=4*math.pi**2*major*minor; dims={"outer_mm":round(outer,2),"tube_diameter_mm":round(minor*2,2)}
    elif shape=="cylinder":
        r=w/2; vol=math.pi*r*r*h; area=2*math.pi*r*(r+h); dims={"diameter_mm":round(w,2),"height_mm":round(h,2)}
    elif shape=="gauntlet":
        vol=w*h*dep*.38; area=2*(w*h+w*dep+h*dep)*.72; dims={"width_mm":w,"height_mm":h,"depth_mm":dep}
    else:
        shape="cube"; vol=w*h*dep; area=2*(w*h+w*dep+h*dep); dims={"width_mm":w,"height_mm":h,"depth_mm":dep}
    density=DENSITY_G_CM3.get(material,1.0); volume_cm3=vol/1000; mass=volume_cm3*density
    diag=math.sqrt(w*w+h*h+dep*dep); drop=(mass/1000)*9.80665
    tests=[
      {"name":"visual_geometry","status":"pass","detail":f"{shape} primitive geometry calculated."},
      {"name":"palm_anchor","status":"pass" if hand else "waiting","detail":"Palm anchor active." if hand else "Show a hand to test anchoring."},
      {"name":"pinch_grab","status":"pass" if pinch else "ready","detail":"Pinch detected." if pinch else "Pinch thumb + index to grab."},
      {"name":"two_hand_transform","status":"pass" if two else "ready","detail":"Two-hand scale/rotation active." if two else "Use two hands to scale/rotate."},
      {"name":"bounding_envelope","status":"pass","detail":f"Bounding diagonal ≈ {diag:.1f} mm."},
      {"name":"mass_estimate","status":"estimate","detail":f"Primitive mass estimate ≈ {mass:.1f} g using {material} density."},
      {"name":"drop_energy_1m","status":"estimate","detail":f"Potential energy from 1 m ≈ {drop:.2f} J; not an impact-strength result."},
      {"name":"structural_solver","status":"not_run","detail":"No FEA claim: loads, constraints, mesh and real material properties are required."},
      {"name":"thermal_solver","status":"not_run","detail":"No thermal claim: boundary conditions and a proper solver are required."},
    ]
    return {"ok":True,"engine":"JARVIS HoloLab Beta","timestamp":time.time(),"shape":shape,"material":material,
            "dimensions":dims,"volume_cm3":round(volume_cm3,3),"surface_area_cm2":round(area/100,3),
            "estimated_mass_g":round(mass,2),"center_of_mass":[0,0,0],"tests":tests,
            "disclaimer":"Pre-CAD spatial/geometry sandbox. Structural, thermal, fatigue and manufacturability still require real engineering solvers."}
