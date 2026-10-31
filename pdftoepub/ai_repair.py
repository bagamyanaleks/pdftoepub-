"""
AI-Assisted In-Painting & Deep Literary Text Repair Module.
Uses lightweight local LLMs (such as Qwen 2.5 1.5B/3B) to reconstruct heavily corrupted,
physically cropped, or noisy text paragraphs that rule-based regex cannot fully restore.
"""

import re
import os
from typing import List, Tuple, Optional, Dict, Any


# Regex patterns indicating severe physical scan defects or printer noise
ANOMALY_PATTERNS = [
    r"[\^~°%&_>\*\-]{2,}",                        # Clustered noise symbols (^>*--, ~&, %o&, u-~°)
    r"\b[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]{2,}\s+[\^~°%&_>\*\-]+", # Word followed by trailing noise symbol
    r"[\^~°%&_>\*\-]+\s+[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]{1,3}\b", # Stray noise preceding fragment
    r"\bcevap\s*v\b",                             # Truncated common verbs (cevap v -> cevap verdi)
    r"\bbiraz\s*do\b",                            # Truncated words (biraz do -> biraz dövmüşler)
    r"\bçür['’]i",                                # Severely fragmented words
    r"_\s*,\s*ur\b",                              # Bottom margin tear artifacts
    r"\b[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]{2,}F,\s*ğimi\b",  # Broken syllables across tears
]


def score_paragraph_anomaly(paragraph: str) -> float:
    """
    Computes a corruption / anomaly score for a given paragraph (0.0 to 1.0+).
    High scores (> 0.20) indicate severe physical scan defects or heavy OCR noise.
    """
    if not paragraph or len(paragraph.strip()) < 20:
        return 0.0

    s = paragraph.strip()
    score = 0.0

    # 1. Match specific severe noise patterns
    for pat in ANOMALY_PATTERNS:
        matches = re.findall(pat, s)
        score += len(matches) * 0.15

    # 2. Count exotic noise symbols relative to letters
    noise_chars = len(re.findall(r"[\^~°%&_\\/<>]", s))
    letters = len(re.findall(r"[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]", s))
    if letters > 0:
        noise_ratio = noise_chars / letters
        score += noise_ratio * 2.0

    # 3. Fragmented single/double letter tokens surrounded by spaces or punctuation
    fragments = len(re.findall(r"(?<=\s)[b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]{1,2}(?=[\s\.,;\?!]|$)", s))
    if fragments >= 3:
        score += fragments * 0.05

    return score


class AIRepairEngine:
    """
    Selective AI Repair Engine for damaged book paragraphs.
    Only invokes LLM on isolated, high-anomaly paragraphs to guarantee
    maximum speed, zero hallucination on clean text, and literary fidelity.
    """

    def __init__(
        self,
        enabled: bool = False,
        backend: str = "transformers",  # "transformers", "openai_compatible", "ollama"
        model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        api_base: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
        temperature: float = 0.2,
        anomaly_threshold: float = 0.20
    ):
        self.enabled = enabled
        self.backend = backend
        self.model_name = model_name
        self.api_base = api_base
        self.api_key = api_key
        self.temperature = temperature
        self.anomaly_threshold = anomaly_threshold

        self._tokenizer = None
        self._model = None

    def _init_local_transformers(self):
        """Lazy-loads the local HuggingFace model only when repair is actually needed."""
        if self._model is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            print(f"[AIRepair] Local model yükleniyor: {self.model_name}...")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                dtype=torch.float32,
                device_map="cpu"
            )
            print("[AIRepair] Model başarıyla belleğe alındı.")

    def repair_paragraph(self, paragraph: str, context_before: str = "", context_after: str = "") -> str:
        """
        Repairs an isolated corrupted paragraph using contextual literary in-painting.
        """
        if not self.enabled:
            return paragraph

        system_prompt = (
            "Sen uzman bir Türk dili, edebiyatı ve kitap editörüsün. "
            "Sana verilen metin taranmış bir romandan alınmıştır. Tarama esnasında sayfanın yırtılması, "
            "katlanması veya sensör hatası nedeniyle bazı kelimelerin harfleri kopmuş ya da araya anlamsız "
            "tarama sembolleri (^, ~&, %o&, _, tireler) karışmıştır.\n\n"
            "GÖREVİN:\n"
            "1. Anlamsız çöp sembolleri temizle.\n"
            "2. Cümlenin gelişinden, dil bilgisi kurallarından ve edebi bağlamdan mantıklı şekilde eksik kalmış kelimeleri tamamla.\n"
            "3. Yazarın üslubunu, cümle yapısını, karakter isimlerini ve diyalogları ASLA değiştirme veya özetleme yapma.\n"
            "4. Açıklama, selamlama veya yorum yazma; SADECE ve SADECE onarılmış nihai Türkçe paragrafı döndür."
        )

        user_content = ""
        if context_before:
            user_content += f"Önceki bağlam:\n\"{context_before}\"\n\n"
        user_content += f"Hasarlı paragraf:\n\"{paragraph}\"\n\n"
        if context_after:
            user_content += f"Sonraki bağlam:\n\"{context_after}\"\n\n"
        user_content += "Onarılmış paragraf:"

        try:
            if self.backend == "transformers":
                self._init_local_transformers()
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
                text = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                model_inputs = self._tokenizer([text], return_tensors="pt").to("cpu")

                generated_ids = self._model.generate(
                    **model_inputs,
                    max_new_tokens=len(paragraph) + 120,
                    temperature=self.temperature,
                    top_p=0.85
                )
                generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]
                repaired = self._tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

            elif self.backend in ("openai_compatible", "ollama"):
                import urllib.request
                import json

                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": len(paragraph) + 120
                }
                req = urllib.request.Request(
                    f"{self.api_base}/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    repaired = data["choices"][0]["message"]["content"].strip()
            else:
                return paragraph

            # Guardrails: strip any meta text like 'Onarılmış paragraf:'
            repaired = re.sub(r'^(?:Onarılmış\s+paragraf|Düzeltilmiş\s+metin|İşte\s+düzeltme)[\s:]*', '', repaired, flags=re.IGNORECASE)
            repaired = repaired.strip('"`\n ')

            # Validation: Length should be reasonable (between 0.5x and 1.6x of original)
            if 0.5 <= len(repaired) / max(1, len(paragraph)) <= 1.6:
                return repaired
            return paragraph

        except Exception as e:
            print(f"[AIRepair] Paragraf onarımında hata oluştu ({e}), orijinal metin korunuyor.")
            return paragraph

    def repair_full_text(self, text: str) -> Tuple[str, int]:
        """
        Scans all paragraphs in text, identifies damaged ones, and repairs them selectively.
        Returns (repaired_text, repair_count).
        """
        if not self.enabled or not text:
            return text, 0

        paragraphs = text.split("\n\n")
        repaired_paragraphs = []
        repair_count = 0

        for idx, p in enumerate(paragraphs):
            score = score_paragraph_anomaly(p)
            if score >= self.anomaly_threshold:
                ctx_before = paragraphs[idx - 1] if idx > 0 else ""
                ctx_after = paragraphs[idx + 1] if idx < len(paragraphs) - 1 else ""

                print(f"[AIRepair] Hasarlı paragraf tespit edildi (Skor: {score:.2f}). AI Onarımı başlatılıyor...")
                repaired_p = self.repair_paragraph(p, context_before=ctx_before, context_after=ctx_after)
                repaired_paragraphs.append(repaired_p)
                repair_count += 1
            else:
                repaired_paragraphs.append(p)

        return "\n\n".join(repaired_paragraphs), repair_count
