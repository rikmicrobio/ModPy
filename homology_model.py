"""
homology_model.py — Homology Modelling Backend
Hazra Group, IIT Roorkee

Usage (called by app.py):
    python homology_model.py --mode <mode> --query <fasta> --template <pdb> <chain>
                             --n-models <N> --n-loop-models <N>
                             --loop-start <res> --loop-end <res>
                             --output-dir <dir> --run

Modes:
    single  – build a single model (fastest)
    multi   – build multiple models and pick best DOPE score
    loop    – loop refinement only
    full    – multi-model build + loop refinement (recommended)

Dependencies:
    MODELLER  (https://salilab.org/modeller/)
    biopython (pip install biopython)
"""

import argparse
import os
import sys

# ── Standard one-letter amino acid codes ─────────────────────────────────────
THREE_TO_ONE = {
    'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C',
    'GLN':'Q','GLU':'E','GLY':'G','HIS':'H','ILE':'I',
    'LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P',
    'SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V',
    'SEC':'U','PYL':'O','ASX':'B','GLX':'Z','XLE':'J',
    'UNK':'X','MSE':'M',  # selenomethionine → M
}

# ── Try importing MODELLER ────────────────────────────────────────────────────
try:
    import modeller
    from modeller import Environ, Model, Alignment, Selection
    from modeller.automodel import AutoModel, LoopModel, assess
    MODELLER_AVAILABLE = True
except ImportError:
    MODELLER_AVAILABLE = False
    print("⚠  MODELLER not found. Running in DEMO mode — no real models will be built.")
    print("   Install MODELLER from https://salilab.org/modeller/ and set your licence key.")


# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Homology Modelling Pipeline")
    p.add_argument("--mode",          default="full",    choices=["single", "multi", "loop", "full"])
    p.add_argument("--query",         required=True,     help="Path to query FASTA file")
    p.add_argument("--template",      required=True,     help="Path to template PDB file")
    p.add_argument("template_chain",  nargs="?",         default="A", help="Template chain ID")
    p.add_argument("--n-models",      type=int,          default=5)
    p.add_argument("--n-loop-models", type=int,          default=4)
    p.add_argument("--loop-start",    type=int,          default=1)
    p.add_argument("--loop-end",      type=int,          default=10)
    p.add_argument("--output-dir",    default="results")
    p.add_argument("--run",           action="store_true")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
def read_fasta(path):
    """Return (id, sequence) from the first record in a FASTA file."""
    seq_id, seq = None, []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                seq_id = line[1:].split()[0]
            elif line:
                seq.append(line)
    return seq_id, "".join(seq)


def extract_pdb_sequence(pdb_path, chain):
    """Extract amino-acid sequence from ATOM records. Returns (first_resnum, last_resnum, seq)."""
    seen = {}
    order = []
    with open(pdb_path) as fh:
        for line in fh:
            if not line.startswith("ATOM"):
                continue
            atom_name = line[12:16].strip()
            if atom_name != "CA":
                continue
            if line[21] != chain:
                continue
            resname = line[17:20].strip()
            resnum  = line[22:27].strip()   # incl. insertion code
            if resnum not in seen:
                seen[resnum] = THREE_TO_ONE.get(resname, 'X')
                order.append(resnum)
    seq = "".join(seen[k] for k in order)
    first = order[0].strip() if order else "1"
    last  = order[-1].strip() if order else "1"
    return first, last, seq


def pairwise_align(query_seq, template_seq):
    """Global pairwise alignment; returns (aligned_query, aligned_template)."""
    try:
        from Bio.Align import PairwiseAligner
        aligner = PairwiseAligner()
        aligner.mode = 'global'
        aligner.match_score = 2
        aligner.mismatch_score = -1
        aligner.open_gap_score = -10
        aligner.extend_gap_score = -0.5
        aligner.end_insertion_score = 0.0
        aligner.end_deletion_score = 0.0
        alns = aligner.align(query_seq, template_seq)
        best = next(iter(alns))
        # Extract gapped sequences from the alignment
        aq = best[0]  # aligned query
        at = best[1]  # aligned target/template
        return aq, at
    except Exception as e:
        print(f"  BioPython alignment failed ({e}), using NW fallback…")

    # Pure-Python Needleman-Wunsch fallback
    GAP = -2; MATCH = 2; MM = -1
    n, m = len(query_seq), len(template_seq)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): dp[i][0] = i*GAP
    for j in range(m+1): dp[0][j] = j*GAP
    for i in range(1, n+1):
        for j in range(1, m+1):
            sc = MATCH if query_seq[i-1] == template_seq[j-1] else MM
            dp[i][j] = max(dp[i-1][j-1]+sc, dp[i-1][j]+GAP, dp[i][j-1]+GAP)
    aq, at = [], []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            sc = MATCH if query_seq[i-1] == template_seq[j-1] else MM
            if dp[i][j] == dp[i-1][j-1]+sc:
                aq.append(query_seq[i-1]); at.append(template_seq[j-1])
                i -= 1; j -= 1; continue
        if i > 0 and dp[i][j] == dp[i-1][j]+GAP:
            aq.append(query_seq[i-1]); at.append('-'); i -= 1
        else:
            aq.append('-'); at.append(template_seq[j-1]); j -= 1
    return "".join(reversed(aq)), "".join(reversed(at))


def write_pir_alignment(fasta_path, pdb_path, chain, out_pir, query_id, template_id):
    """
    Build a correct PIR alignment for MODELLER:
      1. Extract real residue sequence from PDB ATOM records (Calpha only)
      2. Perform global pairwise alignment (query vs template)
      3. Write PIR with correct first/last residue numbers from PDB
    """
    _, query_seq = read_fasta(fasta_path)
    first_res, last_res, tmpl_seq = extract_pdb_sequence(pdb_path, chain)

    print(f"  PDB chain {chain} : {len(tmpl_seq)} residues ({first_res}-{last_res})")
    print(f"  Query FASTA      : {len(query_seq)} residues")

    aln_query, aln_tmpl = pairwise_align(query_seq, tmpl_seq)

    matches = sum(a == b for a, b in zip(aln_query, aln_tmpl) if a != '-' and b != '-')
    total   = sum(1 for a, b in zip(aln_query, aln_tmpl) if a != '-' or b != '-')
    pct     = 100 * matches / total if total else 0
    print(f"  Sequence identity: {pct:.1f}%  ({matches}/{total} positions)")
    if pct < 30:
        print("  WARNING: low identity — alignment may be unreliable.")

    with open(out_pir, "w") as fh:
        fh.write(f">P1;{template_id}\n")
        fh.write(f"structure:{pdb_path}:{first_res}:{chain}:{last_res}:{chain}::::\n")
        fh.write(aln_tmpl + "*\n\n")
        fh.write(f">P1;{query_id}\n")
        fh.write(f"sequence:{query_id}::::::::\n")
        fh.write(aln_query + "*\n")

    print(f"  PIR alignment written -> {out_pir}")



# ─────────────────────────────────────────────────────────────────────────────
def run_single(env, query_id, template_id, aln_file, out_dir, n_models):
    print(f"\n[MODE: single]  building {n_models} model(s)…")
    a = AutoModel(env,
                  alnfile=aln_file,
                  knowns=template_id,
                  sequence=query_id,
                  assess_methods=(assess.DOPE,))
    a.starting_model = 1
    a.ending_model   = n_models
    a.make()
    _report_best(a.outputs, out_dir)


def run_multi(env, query_id, template_id, aln_file, out_dir, n_models):
    print(f"\n[MODE: multi]  building {n_models} model(s) with DOPE assessment…")
    a = AutoModel(env,
                  alnfile=aln_file,
                  knowns=template_id,
                  sequence=query_id,
                  assess_methods=(assess.DOPE, assess.GA341))
    a.starting_model = 1
    a.ending_model   = n_models
    a.make()
    _report_best(a.outputs, out_dir)


def run_loop(env, query_id, template_id, aln_file, out_dir,
             n_models, n_loop, loop_start, loop_end):
    print(f"\n[MODE: loop]  building {n_models} model(s) + loop refinement "
          f"(residues {loop_start}–{loop_end})…")
    class MyLoopModel(LoopModel):
        def select_loop_atoms(self):
            return Selection(self.residue_range(str(loop_start), str(loop_end)))

    a = MyLoopModel(env,
                    alnfile=aln_file,
                    knowns=template_id,
                    sequence=query_id,
                    loop_assess_methods=(assess.DOPE,))
    a.starting_model      = 1
    a.ending_model        = n_models
    a.loop.starting_model = 1
    a.loop.ending_model   = n_loop
    a.make()
    _report_best(a.outputs, out_dir)


def run_full(env, query_id, template_id, aln_file, out_dir,
             n_models, n_loop, loop_start, loop_end):
    print(f"\n[MODE: full]  building {n_models} model(s) + full loop refinement…")
    run_loop(env, query_id, template_id, aln_file, out_dir,
             n_models, n_loop, loop_start, loop_end)


def _report_best(outputs, out_dir):
    import shutil
    ok = [o for o in outputs if o["failure"] is None]
    if not ok:
        print("  ❌ All models failed.")
        return
    best = min(ok, key=lambda o: o["DOPE score"])
    src = os.path.abspath(best["name"])
    print(f"\n  ✅ Best model : {src}")
    print(f"     DOPE score : {best['DOPE score']:.4f}")
    abs_out = os.path.abspath(out_dir)
    dest = os.path.join(abs_out, os.path.basename(src))
    if src != os.path.abspath(dest):
        shutil.copy(src, dest)
    print(f"     Saved to   : {dest}")


# ─────────────────────────────────────────────────────────────────────────────
def demo_mode(args):
    """Simulate a run when MODELLER is not installed."""
    print(f"\n{'='*60}")
    print(f"  DEMO MODE — MODELLER not installed")
    print(f"{'='*60}")
    print(f"  Query    : {args.query}")
    print(f"  Template : {args.template}  (chain {args.template_chain})")
    print(f"  Mode     : {args.mode}")
    print(f"  N Models : {args.n_models}")
    if args.mode in ("loop", "full"):
        print(f"  Loop     : residues {args.loop_start}–{args.loop_end}  ({args.n_loop_models} loop models)")
    print(f"  Output   : {os.path.abspath(args.output_dir)}")
    print(f"\n  Install MODELLER to run real homology modelling.")
    print(f"  https://salilab.org/modeller/")
    print(f"\n✅ Demo completed successfully.\n")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    print(f"\n{'='*60}")
    print(f"  ModPy — Homology Modelling Pipeline")
    print(f"  Hazra Group, IIT Roorkee")
    print(f"{'='*60}")

    if not args.run:
        print("  Pass --run to execute the pipeline.")
        sys.exit(0)

    os.makedirs(args.output_dir, exist_ok=True)

    if not MODELLER_AVAILABLE:
        demo_mode(args)
        return

    # ── Real MODELLER run ────────────────────────────────────────────────────
    query_id    = os.path.splitext(os.path.basename(args.query))[0]
    template_id = os.path.splitext(os.path.basename(args.template))[0]

    # Resolve ALL paths to absolute BEFORE any chdir — this is critical.
    # After os.chdir(output_dir), relative paths like "results/foo.pir" break.
    abs_output_dir  = os.path.abspath(args.output_dir)
    abs_query       = os.path.abspath(args.query)
    abs_template    = os.path.abspath(args.template)
    abs_template_dir = os.path.dirname(abs_template)
    aln_file        = os.path.join(abs_output_dir, f"{query_id}_alignment.pir")

    env = Environ()
    # Absolute paths ensure MODELLER finds the PDB regardless of cwd
    env.io.atom_files_directory = [abs_output_dir, abs_template_dir, '.']

    print(f"\n  Query id   : {query_id}")
    print(f"  Template id: {template_id}  (chain {args.template_chain})")
    print(f"  Mode       : {args.mode}")

    write_pir_alignment(abs_query, abs_template, args.template_chain,
                        aln_file, query_id, template_id)

    # Change to output dir so MODELLER writes its output files there
    orig_dir = os.getcwd()
    os.chdir(abs_output_dir)

    try:
        if args.mode == "single":
            run_single(env, query_id, template_id, aln_file,
                       abs_output_dir, args.n_models)
        elif args.mode == "multi":
            run_multi(env, query_id, template_id, aln_file,
                      abs_output_dir, args.n_models)
        elif args.mode == "loop":
            run_loop(env, query_id, template_id, aln_file,
                     abs_output_dir, args.n_models,
                     args.n_loop_models, args.loop_start, args.loop_end)
        else:   # full
            run_full(env, query_id, template_id, aln_file,
                     abs_output_dir, args.n_models,
                     args.n_loop_models, args.loop_start, args.loop_end)
    finally:
        os.chdir(orig_dir)

    print(f"\n✅ Pipeline complete. Results in: {os.path.abspath(args.output_dir)}\n")


if __name__ == "__main__":
    main()
