"""Compare the newest snapshot with the one before it and write CHANGES.md inside the newest.

    python scripts/change_report.py

For each file in the manifest: same hash as last time, or changed. For the three tables that
grow, what changed: FRED and FEMA gain rows (how many, and the newest date); Zillow gains a
month as a new column and also revises past months (how many cells changed, and the largest
revision). A revised past value is the vintage lesson: the file you pulled last month and the
file you pull today disagree about the same month.

When only one snapshot exists, the baseline is the course's raw/ folder (the 7 October 2026
snapshot), which holds the same FRED, Zillow, and FEMA files under their older names.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_NAMES = {"fred_mortgage30us.csv": "fred_mortgage30us.csv",
             "zillow_zori_county.csv": "zillow_zori_county.csv",
             "fema_disaster_declarations.csv": "fema_disaster_declarations.csv"}


def snapshot_folders():
    folders = sorted(p for p in (ROOT / "snapshots").iterdir() if p.is_dir() and (p / "manifest.csv").exists())
    return folders


def table_report(name, old_path, new_path, lines):
    old = pd.read_csv(old_path)
    new = pd.read_csv(new_path)
    lines.append("")
    lines.append("### %s" % name)
    lines.append("")
    lines.append("- Rows: %s before, %s now (%+d)." % (f"{len(old):,}", f"{len(new):,}", len(new) - len(old)))
    lines.append("- Columns: %d before, %d now." % (old.shape[1], new.shape[1]))
    if name.startswith("fred"):
        lines.append("- Newest date: %s before, %s now." % (old.iloc[-1, 0], new.iloc[-1, 0]))
        added = new[~new["observation_date"].isin(old["observation_date"])]
        for _, r in added.iterrows():
            lines.append("- Added: %s at %s." % (r.iloc[0], r.iloc[1]))
    elif name.startswith("fema"):
        lines.append("- Newest declaration date: %s before, %s now."
                     % (old["declarationDate"].max()[:10], new["declarationDate"].max()[:10]))
    elif name.startswith("zillow"):
        new_cols = [c for c in new.columns if c not in old.columns]
        lines.append("- New columns: %s." % (", ".join(new_cols) if new_cols else "none"))
        shared_months = [c for c in old.columns if c in new.columns and c[:2] == "20"]
        o = old.set_index("RegionID")[shared_months]
        n = new.set_index("RegionID").reindex(o.index)[shared_months]
        diff = (o - n).abs()
        changed = int(((diff > 0.005) & o.notna() & n.notna()).sum().sum())
        lines.append("- Past months revised: %s cells changed out of %s shared; largest revision $%.0f."
                     % (f"{changed:,}", f"{int(o.notna().sum().sum()):,}", diff.max().max() if changed else 0))
        newly_filled = int((o.isna() & n.notna()).sum().sum())
        newly_blank = int((o.notna() & n.isna()).sum().sum())
        lines.append("- Cells filled in since last time: %d; cells blanked: %d." % (newly_filled, newly_blank))


def main():
    folders = snapshot_folders()
    newest = folders[-1]
    manifest_new = pd.read_csv(newest / "manifest.csv").set_index("file")
    if len(folders) >= 2:
        previous = folders[-2]
        manifest_old = pd.read_csv(previous / "manifest.csv").set_index("file")
        baseline = "snapshot %s" % previous.name
        old_path = lambda f: previous / f  # noqa: E731
        old_hash = lambda f: manifest_old["sha256"].get(f)  # noqa: E731
    else:
        previous = ROOT / "raw"
        baseline = "the raw/ folder (course snapshot of 7 October 2026)"
        old_path = lambda f: previous / RAW_NAMES.get(f, f)  # noqa: E731
        old_hash = lambda f: None  # noqa: E731

    lines = ["# What changed: %s against %s" % (newest.name, baseline), ""]
    lines.append("| File | Rows | Same bytes as before? |")
    lines.append("|---|---|---|")
    for f, r in manifest_new.iterrows():
        before = old_hash(f)
        same = "no baseline" if before is None else ("yes" if before == r["sha256"] else "no, changed")
        rows = "" if pd.isna(r["rows"]) else f"{int(r['rows']):,}"
        lines.append("| %s | %s | %s |" % (f, rows, same))
    for f in RAW_NAMES:
        if (newest / f).exists() and old_path(f).exists():
            table_report(f, old_path(f), newest / f, lines)
    (newest / "CHANGES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
