"""Small-corpus BM25 signal to complement the existing anchored semantic score."""
from collections import Counter
import math
from .encoders import tokens


def lexical_scores(query, papers):
    query_terms = set(tokens(query))
    docs = [Counter(tokens(p['title'] + '. ' + p.get('abstract', ''))) for p in papers]
    if not docs or not query_terms:
        return {p['id']: 0. for p in papers}
    lengths = [sum(d.values()) for d in docs]
    average = sum(lengths) / len(docs) or 1.
    frequency = Counter(term for d in docs for term in d)
    scores = {}
    for paper, doc, length in zip(papers, docs, lengths):
        score = 0.
        for term in query_terms:
            count = doc[term]
            if count:
                idf = math.log(1 + (len(docs) - frequency[term] + .5) / (frequency[term] + .5))
                score += idf * count * 2.2 / (count + 1.2 * (.25 + .75 * length / average))
        scores[paper['id']] = score
    return scores
