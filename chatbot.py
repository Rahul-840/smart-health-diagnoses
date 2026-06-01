import re
from typing import Dict, List, Optional
import numpy as np

SYNONYMS: Dict[str, List[str]] = {
    "sugar": ["sugar", "glucose", "blood sugar", "fbs", "rbs", "hba1c"],
    "cholesterol": ["cholesterol", "ldl", "hdl", "triglycerides", "lipid"],
    "thyroid": ["thyroid", "tsh", "t3", "t4"],
    "platelet": ["platelet", "platelets", "plt"],
    "hemoglobin": ["hemoglobin", "haemoglobin", "hb"],
    "wbc": ["wbc", "white blood", "tlc", "leukocyte", "leucocyte"],
    "rbc": ["rbc", "red blood"],
    "liver": ["liver", "sgpt", "sgot", "alt", "ast", "bilirubin"],
    "kidney": ["kidney", "creatinine", "urea"],
}


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += max(1, chunk_size - overlap)
    return chunks


def expand_question_terms(question: str) -> List[str]:
    q = (question or "").lower()
    words = set(re.findall(r"[a-zA-Z0-9]+", q))
    for group, terms in SYNONYMS.items():
        if any(term in q for term in terms):
            words.update(re.findall(r"[a-zA-Z0-9]+", " ".join(terms)))
    return list(words)


def keyword_retrieve(question: str, chunks: List[str], top_k: int = 3) -> List[str]:
    q_words = set(expand_question_terms(question))
    scored = []
    for ch in chunks:
        c_words = set(re.findall(r"[a-zA-Z0-9]+", ch.lower()))
        score = len(q_words & c_words)
        # Add phrase bonus.
        lower = ch.lower()
        for term in q_words:
            if len(term) > 3 and term in lower:
                score += 0.25
        scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [c for score, c in scored[:top_k] if score > 0]
    return selected or chunks[:top_k]


def get_relevant_context(question: str, report_text: str, embedder=None, top_k: int = 3) -> str:
    chunks = chunk_text(report_text)
    if not chunks:
        return ""
    if embedder is None:
        return "\n\n".join(keyword_retrieve(question, chunks, top_k))
    try:
        c_emb = embedder.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
        q_emb = embedder.encode([question], convert_to_numpy=True, normalize_embeddings=True)[0]
        scores = np.dot(c_emb, q_emb)
        # Blend semantic and keyword results for safer report grounding.
        sem_idxs = list(np.argsort(scores)[::-1][:top_k])
        sem_chunks = [chunks[i] for i in sem_idxs]
        key_chunks = keyword_retrieve(question, chunks, top_k)
        merged: List[str] = []
        for ch in key_chunks + sem_chunks:
            if ch not in merged:
                merged.append(ch)
        return "\n\n".join(merged[:top_k])
    except Exception:
        return "\n\n".join(keyword_retrieve(question, chunks, top_k))


def load_minilm_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        return None


def local_answer(question: str, analysis: Dict, context: str = "") -> str:
    q = (question or "").lower()
    values = analysis.get("detected_values", []) or []

    def matching_values() -> List[Dict]:
        terms = expand_question_terms(q)
        out = []
        for v in values:
            hay = f"{v.get('test', '')} {v.get('key', '')} {v.get('meaning', '')}".lower()
            if any(t in hay for t in terms if len(t) > 1):
                out.append(v)
        return out

    matches = matching_values()
    if matches:
        lines = ["Report values related to your question:"]
        for v in matches[:8]:
            lines.append(f"- {v.get('test')}: {v.get('value')} | Status: {v.get('status')} | Range: {v.get('normal_range')}")
        lines.append("Please confirm final interpretation with a doctor.")
        return "\n".join(lines)

    if any(word in q for word in ["risk", "problem", "issue", "abnormal", "wrong"]):
        risks = analysis.get("risk_factors", []) or []
        return "Possible risk indicators:\n" + "\n".join(f"- {r}" for r in risks)
    if any(word in q for word in ["diet", "food", "eat"]):
        return analysis.get("diet", "Diet guidance is not available for this report.")
    if any(word in q for word in ["summary", "summarize", "report"]):
        return analysis.get("summary", "Summary is not available.")
    if context:
        return "Relevant report context:\n\n" + context[:1400] + "\n\nPlease confirm final interpretation with a doctor."
    return "I could not find this information clearly in the uploaded report. Please ask about a value shown in the report table."
