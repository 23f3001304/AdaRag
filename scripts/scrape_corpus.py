"""Build a local web corpus for eval: fetch plain-text Wikipedia extracts (stdlib only, no deps).

Saves each article to evaluation/corpus/web_<slug>.txt (gitignored test data). Section headers are
converted to markdown so longer articles profile as papers and exercise section chunking.

Run: python scripts/scrape_corpus.py
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evaluation" / "corpus"
API = "https://en.wikipedia.org/w/api.php"
UA = "AdaRag-corpus-builder/0.1 (local eval corpus)"

TITLES = [
    "Information retrieval",
    "Vector space model",
    "Tf–idf",
    "Okapi BM25",
    "Word embedding",
    "Sentence embeddings",
    "Transformer (deep learning architecture)",
    "Attention (machine learning)",
    "Language model",
    "Large language model",
    "Question answering",
    "Cosine similarity",
    "Nearest neighbor search",
    "Locality-sensitive hashing",
    "Precision and recall",
    "Latent semantic analysis",
    "Named-entity recognition",
    "Retrieval-augmented generation",
    "Semantic search",
    "Knowledge graph",
]

_TRAIL = re.compile(
    r"\n#+ (?:See also|References|Notes|Citations|External links"
    r"|Further reading|Bibliography|Sources)\b"
)


def _to_markdown(text: str) -> str:
    """Wikitext section headers (== X ==) -> markdown (## X)."""
    return re.sub(
        r"^(=+)\s*(.+?)\s*=+\s*$",
        lambda m: "#" * len(m.group(1)) + " " + m.group(2).strip(),
        text,
        flags=re.M,
    )


def _slug(title: str) -> str:
    return "web_" + re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") + ".txt"


def fetch(title: str) -> str:
    params = {
        "format": "json",
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "redirects": "1",
        "titles": title,
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return next(iter(data["query"]["pages"].values())).get("extract", "")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for title in TITLES:
        try:
            text = fetch(title)
        except Exception as exc:  # network / HTTP failure: skip, keep going
            print(f"FAIL  {title}: {exc}")
            continue
        if len(text) < 500:
            print(f"SKIP  {title}: short/empty ({len(text)} chars)")
            continue
        text = _TRAIL.split(_to_markdown(text))[0].strip() + "\n"
        (OUT / _slug(title)).write_text(text, encoding="utf-8")
        total += len(text)
        print(f"OK    {_slug(title):42} {len(text):>7} chars")
    print(f"--\ntotal {total} chars")


if __name__ == "__main__":
    main()
