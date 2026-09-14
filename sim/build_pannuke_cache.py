"""Build a stratified PanNuke cell-layout cache for Phase-1 experiments."""

import time
from collections import Counter

import numpy as np
from datasets import load_dataset

import pannuke_load as pl


def main(per_fold: int = 700):
    t0 = time.time()
    ds = load_dataset("Angelou0516/PanNuke")
    rows = []
    rng = np.random.default_rng(0)
    for sname in ("fold1", "fold2", "fold3"):
        split = ds[sname]
        n = len(split)
        take = min(per_fold, n)
        idxs = rng.choice(n, size=take, replace=False)
        print(f"{sname}: extracting {take}/{n} ...")
        for j, i in enumerate(idxs):
            row = split[int(i)]
            inst = pl._pil_or_arr(row["inst_map"])
            typ = pl._pil_or_arr(row["type_map"])
            pts, attrs = pl._centroids_from_instance_maps(inst, typ)
            if len(pts) < 8:
                continue
            tissue = row.get("tissue_name", "unknown")
            rows.append(
                {
                    "sample_id": str(row.get("sample_id", f"{sname}_{i}")),
                    "fold": int(row.get("fold", 0)),
                    "tissue": str(tissue),
                    "points_um": pts * pl.UM_PER_PX,
                    "attrs": attrs,
                    "n_cells": len(pts),
                }
            )
            if (j + 1) % 150 == 0:
                print(f"  {j+1}/{take} kept={len(rows)}")
    print(f"usable: {len(rows)} in {time.time()-t0:.1f}s")
    print("tissues:", Counter(r["tissue"] for r in rows).most_common(6))
    ns = np.array([r["n_cells"] for r in rows])
    print(f"n_cells mean/median/max: {ns.mean():.1f}/{np.median(ns):.0f}/{ns.max()}")
    path = pl.save_compact_cache(rows)
    print("wrote", path)


if __name__ == "__main__":
    main()
