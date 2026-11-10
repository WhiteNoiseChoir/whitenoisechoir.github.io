#!/usr/bin/env python3
"""C6C two-second DSP smoke tests: catches NaN, clipping and identical tracks."""
from __future__ import annotations
import importlib.util,hashlib,json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("render_c6c",root/"scripts/c6c_render_ten_original_synth.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
items=json.loads((root/"catalog/c6c-ten-synthetic-review.json").read_text())["items"]
assert len(items)==10
signatures=[]
for i,row in enumerate(items):
 r=mod.Renderer(row["algorithm"],0x6C6C2026+i*19997)
 data=r.create(0,mod.SR*2)
 assert data.shape==(mod.SR*2,2)
 assert np.isfinite(data).all()
 assert np.max(np.abs(data))<mod.LIMIT
 rms=float(np.sqrt(np.mean(np.square(data,dtype=np.float64))))
 assert 0.004<rms<0.08,(row["id"],rms)
 key=hashlib.sha256(data.tobytes()).hexdigest()
 signatures.append(key)
 print("C6C_DSP_2S_SMOKE",json.dumps({"id":row["id"],"algorithm":row["algorithm"],"rms":round(rms,5),"sha256":key}),flush=True)
assert len(set(signatures))==10,"DSP audition IDs must have distinct PCM"
print("C6C_TEN_ORIGINAL_DSP_SMOKE_PASS")
