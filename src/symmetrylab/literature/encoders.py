"""Fixed text encoders for the paper survey.

PhysBERT (a BERT model pretrained on arXiv physics papers) is used when it has been
prepared locally; otherwise a deterministic physics-lexicon encoder keeps the survey
working offline. Like the Newspaper project, models are never downloaded implicitly.
"""
import hashlib
import math
import os
import re
import threading

PHYSBERT = {'name': 'thellert/physbert_cased', 'revision': '2d8340bd3f93d5d7f66a34daa73531d701f143b2',
            'about': 'https://huggingface.co/thellert/physbert_cased'}
_lock = threading.Lock()
_cache = {}


def seed_text(keyword):
    """Short keywords embed poorly with mean pooling; a sentence frame improves matching."""
    return f'We study {keyword.strip().rstrip(".")}.'


class PhysBERTEncoder:
    kind = 'physbert'
    # Calibrated on condensed-matter abstracts: unrelated 0.1-0.2, same subfield 0.45-0.65.
    merge, match, floor, span = .75, .35, .30, .60

    def __init__(self, download=False):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(PHYSBERT['name'], revision=PHYSBERT['revision'], device='cpu',
                                         local_files_only=not download)
        size = getattr(self.model, 'get_embedding_dimension', None) or self.model.get_sentence_embedding_dimension
        self.dimension = size()
        self.version = f"physbert@{PHYSBERT['revision'][:12]}/mean-pool/{self.dimension}"

    def encode(self, texts):
        with _lock:
            rows = self.model.encode(list(texts), normalize_embeddings=True, batch_size=16, show_progress_bar=False)
        return [[round(float(x), 6) for x in row] for row in rows]


# Synonym groups map physics phrasing onto shared concept features.
CONCEPTS = {
    'antiferromagnet': ['antiferromagnet', 'antiferromagnetic', 'afm', 'neel order', 'compensated magnet'],
    'altermagnet': ['altermagnet', 'altermagnetic', 'altermagnetism', 'nonrelativistic spin splitting', 'spin-split antiferromagnet'],
    'neel_vector': ['neel vector', 'néel vector', 'staggered magnetization', 'neel axis', 'easy axis'],
    'spin_group': ['spin space group', 'spin-space group', 'spin group', 'spin point group', 'ssg'],
    'magnetic_group': ['magnetic space group', 'magnetic point group', 'msg', 'shubnikov', 'corepresentation'],
    'tmr': ['tunnel magnetoresistance', 'tunneling magnetoresistance', 'tmr', 'magnetic tunnel junction', 'mtj'],
    'spin_transport': ['spin current', 'spin polarization', 'spin conductivity', 'spin transport', 'spin hall', 'spin torque', 'spin-orbit torque'],
    'soc': ['spin-orbit coupling', 'spin orbit coupling', 'soc', 'rashba', 'dresselhaus'],
    'pt_symmetry': ['pt symmetry', 'pt-symmetric', 'parity-time', 'spin degenerate', 'kramers degeneracy'],
    'topology': ['topological', 'berry phase', 'berry curvature', 'chern', 'z2 invariant', 'weyl', 'dirac semimetal'],
    'anomalous_hall': ['anomalous hall', 'crystal hall', 'hall conductivity'],
    'dft': ['density functional', 'density-functional', 'first-principles', 'first principles', 'ab initio', 'dft'],
    'neutron': ['neutron diffraction', 'neutron scattering', 'magnetic structure factor', 'polarized neutron'],
    'xray_dichroism': ['xmld', 'xmcd', 'x-ray magnetic', 'dichroism'],
    'arpes': ['arpes', 'photoemission', 'band dispersion'],
    'superconductivity': ['superconduct', 'cooper pair', 'bcs', 'josephson', 'pairing symmetry'],
    'strongly_correlated': ['hubbard', 'mott', 'strongly correlated', 'kondo', 'heavy fermion'],
    'group_theory': ['representation theory', 'irreducible representation', 'projective representation', 'cohomology', 'group extension', 'nonsymmorphic'],
    'thin_film': ['thin film', 'epitaxial', 'heterostructure', 'interface', 'substrate', 'strain'],
    'magnon': ['magnon', 'spin wave', 'magnonic'],
    'quantum_information': ['qubit', 'quantum computing', 'entanglement', 'quantum error'],
    'astrophysics': ['galaxy', 'cosmolog', 'dark matter', 'stellar', 'black hole'],
}
STOP = set('a an the of for in on to and or with by is are was were be been can we our this that these those from as at into using under via its their it which than also both between show shows shown here present report study studies paper new based such may not no'.split())


def tokens(text):
    return [w.rstrip('s') if len(w) > 4 else w for w in re.findall(r'[a-z0-9][a-z0-9\-]+', text.lower()) if w not in STOP]


class LexiconEncoder:
    kind, version, dimension = 'lexicon', 'physics-lexicon-v1/1024', 1024
    merge, match, floor, span = .50, .08, .05, .50

    def feature(self, name):
        return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) % self.dimension

    def one(self, text):
        low = ' ' + re.sub(r'\s+', ' ', text.lower()) + ' '
        counts = {}
        for concept, phrases in CONCEPTS.items():
            hits = sum(low.count(' ' + p) for p in phrases)
            if hits:
                counts['c:' + concept] = counts.get('c:' + concept, 0) + 3 * hits
        words = tokens(text)
        for w in words:
            counts['w:' + w] = counts.get('w:' + w, 0) + 1
        for a, b in zip(words, words[1:]):
            counts['b:' + a + ' ' + b] = counts.get('b:' + a + ' ' + b, 0) + 1
        vector = [0.] * self.dimension
        for name, n in counts.items():
            vector[self.feature(name)] += 1 + math.log(n)
        length = math.sqrt(sum(v * v for v in vector)) or 1.
        return [round(v / length, 6) for v in vector]

    def encode(self, texts):
        return [self.one(t) for t in texts]


def physbert_ready():
    try:
        PhysBERTEncoder()
        return True
    except Exception:
        return False


def get_encoder(prefer=None):
    """Return a cached encoder. SYMMETRYLAB_ENCODER=lexicon forces the offline fallback."""
    prefer = prefer or os.environ.get('SYMMETRYLAB_ENCODER', 'physbert')
    with _lock:
        if prefer in _cache:
            return _cache[prefer]
    encoder = None
    if prefer == 'physbert':
        try:
            encoder = PhysBERTEncoder()
        except Exception:
            encoder = None
    encoder = encoder or LexiconEncoder()
    with _lock:
        _cache[prefer] = encoder
    return encoder


def prepare_physbert():
    """Explicit, user-initiated download of the pinned PhysBERT revision (about 440 MB)."""
    encoder = PhysBERTEncoder(download=True)
    with _lock:
        _cache['physbert'] = encoder
    return {'status': 'ready', 'version': encoder.version}


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--download']:
        print(prepare_physbert())
    else:
        print({'encoder': get_encoder().version})
