"""
PanNuke loader: instance masks -> centroids + coarse cell-type attributes.

Expects either:
  (A) HuggingFace cache via datasets (preferred in this repo), or
  (B) Official Warwick layout under data/pannuke/fold{1,2,3}/...

Attribute alphabet q=5 matches Assumption 1 (no intensity / morphology features):
  0 neoplastic, 1 inflammatory, 2 connective, 3 dead, 4 epithelial
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "pannuke"

CLASS_NAMES = ("neoplastic", "inflammatory", "connective", "dead", "epithelial")
Q = len(CLASS_NAMES)

# Pixel size at 40x for PanNuke is commonly treated as ~0.25 um/px.
UM_PER_PX = 0.25


def _centroids_from_instance_maps(
    inst_map: np.ndarray,
    type_map: np.ndarray,
    min_area: int = 4,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (centroids_xy float[N,2] in pixels, attrs int[N])."""
    from scipy import ndimage

    inst = inst_map.astype(np.int32)
    typ = type_map.astype(np.int32)
    ids = np.unique(inst)
    ids = ids[ids > 0]
    if ids.size == 0:
        return np.zeros((0, 2), dtype=float), np.zeros((0,), dtype=int)

    # centers of mass for all labels in one pass
    # index 0 is background; ndimage expects labels 0..max
    centers = ndimage.center_of_mass(np.ones_like(inst, dtype=float), labels=inst, index=ids)
    pts, attrs = [], []
    for iid, (cy, cx) in zip(ids, centers):
        m = inst == iid
        area = int(m.sum())
        if area < min_area:
            continue
        vals = typ[m]
        vals = vals[vals > 0]
        if vals.size == 0:
            # some HF maps use 0..4 inclusive for class
            vals = typ[m]
            if vals.size == 0:
                continue
            cls = int(np.bincount(vals).argmax())
        else:
            cls = int(np.bincount(vals).argmax())
            if cls >= 1 and vals.min() >= 1:
                cls = cls - 1
        cls = int(np.clip(cls, 0, Q - 1))
        pts.append([cx, cy])
        attrs.append(cls)
    if not pts:
        return np.zeros((0, 2), dtype=float), np.zeros((0,), dtype=int)
    return np.asarray(pts, dtype=float), np.asarray(attrs, dtype=int)


def _pil_or_arr(x) -> np.ndarray:
    arr = np.array(x)
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr


def _load_from_hf(max_samples: Optional[int] = None) -> List[Dict]:
    from datasets import load_dataset

    ds = load_dataset("Angelou0516/PanNuke")
    split_names = list(ds.keys()) if hasattr(ds, "keys") else ["train"]
    out: List[Dict] = []
    i = 0
    for sname in split_names:
        split = ds[sname]
        for row in split:
            inst = _pil_or_arr(row["inst_map"])
            typ = _pil_or_arr(row["type_map"])
            pts, attrs = _centroids_from_instance_maps(inst, typ)
            if len(pts) < 8:
                i += 1
                continue
            tissue = row.get("tissue_name", row.get("tissue", "unknown"))
            if isinstance(tissue, (int, np.integer)):
                tissue = str(int(tissue))
            fold = int(row.get("fold", 0))
            sid = str(row.get("sample_id", f"hf_{i}"))
            out.append(
                {
                    "sample_id": sid,
                    "fold": fold,
                    "tissue": tissue,
                    "points_px": pts,
                    "points_um": pts * UM_PER_PX,
                    "attrs": attrs,
                    "n_cells": len(pts),
                }
            )
            i += 1
            if max_samples is not None and len(out) >= max_samples:
                return out
    return out


def _parse_official_masks(masks: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Official PanNuke masks.npy shape: (N, 256, 256, 6)
    channels 0..4 = instance ids per class, channel 5 = type map in some releases,
    or channels are per-class instance maps. Common layout:
      masks[..., c] for c in 0..4 are instance IDs for that class (nonoverlap),
      masks[..., 5] sometimes unused / type.
    """
    if masks.ndim != 3:
        raise ValueError(f"expected HxWxC mask, got {masks.shape}")
    h, w, c = masks.shape
    inst = np.zeros((h, w), dtype=np.int32)
    typ = np.zeros((h, w), dtype=np.int32)
    next_id = 1
    n_cls = min(5, c)
    for cls in range(n_cls):
        ch = masks[..., cls].astype(np.int32)
        for iid in np.unique(ch):
            if iid == 0:
                continue
            m = ch == iid
            inst[m] = next_id
            typ[m] = cls + 1  # 1..5 then remapped in centroid fn
            next_id += 1
    return inst, typ


def _load_from_official(max_samples: Optional[int] = None) -> List[Dict]:
    out: List[Dict] = []
    for fold in (1, 2, 3):
        candidates = [
            DATA_DIR / f"fold{fold}",
            DATA_DIR / f"Fold {fold}",
            DATA_DIR / f"fold_{fold}",
            DATA_DIR / f"Fold_{fold}",
        ]
        base = next((p for p in candidates if p.exists()), None)
        if base is None:
            continue
        # find images.npy / masks.npy / types.npy recursively
        img_files = list(base.rglob("images.npy"))
        mask_files = list(base.rglob("masks.npy"))
        type_files = list(base.rglob("types.npy"))
        if not mask_files:
            continue
        masks_all = np.load(mask_files[0], mmap_mode="r")
        types_all = np.load(type_files[0]) if type_files else None
        n = masks_all.shape[0]
        for i in range(n):
            inst, typ = _parse_official_masks(np.array(masks_all[i]))
            pts, attrs = _centroids_from_instance_maps(inst, typ)
            if len(pts) < 8:
                continue
            tissue = "unknown"
            if types_all is not None:
                t = types_all[i]
                tissue = t.decode() if isinstance(t, bytes) else str(t)
            out.append(
                {
                    "sample_id": f"fold{fold}_{i:05d}",
                    "fold": fold,
                    "tissue": tissue,
                    "points_px": pts,
                    "points_um": pts * UM_PER_PX,
                    "attrs": attrs,
                    "n_cells": len(pts),
                }
            )
            if max_samples is not None and len(out) >= max_samples:
                return out
    return out


def load_pannuke(max_samples: Optional[int] = None, prefer: str = "auto") -> List[Dict]:
    """
    Load PanNuke patches as cell layouts.

    prefer: 'hf' | 'official' | 'auto'
    """
    cache = DATA_DIR / "processed_cells.npz"
    # always allow fresh load; optional disk cache of compact form
    if prefer in ("auto", "official"):
        try:
            rows = _load_from_official(max_samples=max_samples)
            if rows:
                return rows
        except Exception as exc:
            if prefer == "official":
                raise RuntimeError(f"official PanNuke load failed: {exc}") from exc
    if prefer in ("auto", "hf"):
        rows = _load_from_hf(max_samples=max_samples)
        if rows:
            return rows
    raise FileNotFoundError(
        "PanNuke not found. Download folds into data/pannuke/ or ensure "
        "HuggingFace dataset Angelou0516/PanNuke is reachable."
    )


def save_compact_cache(rows: List[Dict], path: Optional[Path] = None) -> Path:
    path = path or (DATA_DIR / "processed_cells.npz")
    path.parent.mkdir(parents=True, exist_ok=True)
    # ragged store via object arrays
    np.savez_compressed(
        path,
        sample_id=np.array([r["sample_id"] for r in rows], dtype=object),
        fold=np.array([r["fold"] for r in rows]),
        tissue=np.array([r["tissue"] for r in rows], dtype=object),
        points_um=np.array([r["points_um"] for r in rows], dtype=object),
        attrs=np.array([r["attrs"] for r in rows], dtype=object),
        n_cells=np.array([r["n_cells"] for r in rows]),
    )
    return path


def load_compact_cache(path: Optional[Path] = None) -> List[Dict]:
    path = path or (DATA_DIR / "processed_cells.npz")
    z = np.load(path, allow_pickle=True)
    rows = []
    for i in range(len(z["sample_id"])):
        rows.append(
            {
                "sample_id": str(z["sample_id"][i]),
                "fold": int(z["fold"][i]),
                "tissue": str(z["tissue"][i]),
                "points_um": np.asarray(z["points_um"][i], dtype=float),
                "attrs": np.asarray(z["attrs"][i], dtype=int),
                "n_cells": int(z["n_cells"][i]),
            }
        )
    return rows


if __name__ == "__main__":
    print("Loading PanNuke (this may download on first run)...")
    rows = load_pannuke(max_samples=50)
    print(f"loaded {len(rows)} patches (capped demo)")
    print("example:", rows[0]["sample_id"], rows[0]["tissue"], rows[0]["n_cells"])
    p = save_compact_cache(load_pannuke(max_samples=None) if len(rows) >= 50 else rows)
    print("cache:", p)
