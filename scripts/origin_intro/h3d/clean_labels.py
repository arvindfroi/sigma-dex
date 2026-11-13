"""Steady-hand pass over the painted mesh (Arvind: "looks like someone with a very unsteady hand painted it").
Works on faces: each face gets the majority label of its corners, then
1. islands: a connected patch of one colour smaller than MIN_AREA joins the colour around it (blotches go)
2. smoothing: a face whose colour none or only one of its 3 neighbours shares takes the neighbours' colour
   (ragged, saw-tooth borders become smooth lines); thin designed lines (deck seams) are kept
python h3d/clean_labels.py MESH.npz LABELS.npy PARTS.npy OUT_PREFIX   -> OUT_PREFIX_flab.npy, OUT_PREFIX_fpart.npy"""
import sys, os, numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
mp, lp, pp, outp = sys.argv[1:5]
d = np.load(mp); V = d['V'].astype(float); F = d['F']
lab = np.load(lp); part = np.load(pp)
MIN_AREA = float(os.environ.get('MIN_AREA', 0.0006))
KEEP_LAB = {9}                     # deck seams: thin on purpose
KEEP_PART = {7, 12}                # the nose; dropped faces stay dropped
nf = len(F)
def maj(a, n):
    c = np.zeros((nf, n), int)
    for k in range(3): np.add.at(c, (np.arange(nf), a[F[:, k]]), 1)
    return c.argmax(1)
fl = maj(lab, lab.max() + 1)
fp = maj(part, part.max() + 1)
fp[(part[F] == 12).any(1)] = 12
area = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
# face adjacency through shared edges
E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); fid = np.tile(np.arange(nf), 3)
E.sort(1); key = E[:, 0].astype(np.int64) * (len(V) + 1) + E[:, 1]
o = np.argsort(key); ks = key[o]; same = ks[1:] == ks[:-1]
a_, b_ = fid[o][:-1][same], fid[o][1:][same]
nbrs = [[] for _ in range(nf)]
for a, b in zip(a_, b_): nbrs[a].append(b); nbrs[b].append(a)
protect = np.isin(fl, list(KEEP_LAB)) | np.isin(fp, list(KEEP_PART))
changed_isl = 0
for it in range(3):
    # components of equal (label, part)
    same_ab = (fl[a_] == fl[b_]) & (fp[a_] == fp[b_])
    G = coo_matrix((np.ones(same_ab.sum()), (a_[same_ab], b_[same_ab])), shape=(nf, nf))
    ncomp, comp = connected_components(G, directed=False)
    carea = np.bincount(comp, weights=area, minlength=ncomp)
    small = (carea[comp] < MIN_AREA) & ~protect
    if not small.any(): break
    # each small island takes the colour that borders it most (by face count) among non-small neighbours
    for c in np.unique(comp[small]):
        faces = np.where(comp == c)[0]
        votes = {}
        for f in faces:
            for g in nbrs[f]:
                if comp[g] != c: votes[(fl[g], fp[g])] = votes.get((fl[g], fp[g]), 0) + 1
        if votes:
            (L, P), _ = max(votes.items(), key=lambda kv: kv[1])
            fl[faces] = L; fp[faces] = P; changed_isl += len(faces)
changed_sm = 0
for it in range(int(os.environ.get('SMOOTH_IT', 3))):
    nl = fl.copy(); npp = fp.copy()
    for f in range(nf):
        if protect[f] or len(nbrs[f]) < 2: continue
        ln = [(fl[g], fp[g]) for g in nbrs[f]]
        if sum(1 for q in ln if q == (fl[f], fp[f])) >= 2: continue
        best = max(set(ln), key=ln.count)
        if ln.count(best) >= 2 and best[1] != 12: nl[f], npp[f] = best; changed_sm += 1
    fl, fp = nl, npp
np.save(outp + '_flab.npy', fl); np.save(outp + '_fpart.npy', fp)
print('faces', nf, 'island faces recoloured', changed_isl, 'smoothed', changed_sm)
