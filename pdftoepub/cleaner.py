"""
Text cleaner and Turkish linguistic post-processor for PDF to EPUB/AZW3 conversion.
Handles de-hyphenation, header/footer removal, Turkish diacritics, OCR error correction,
dialogue formatting, and paragraph reconstruction.
"""

import re
import unicodedata
from typing import List, Dict, Optional, Tuple, Set


def turkish_lower(s: str) -> str:
    """Correct Turkish lowercase conversion (maps 'İ' -> 'i', 'I' -> 'ı' without combining dot artifacts)."""
    if not s:
        return ""
    return s.replace("İ", "i").replace("I", "ı").lower().replace("i\u0307", "i").replace("ı\u0307", "i")


def turkish_upper(s: str) -> str:
    """Correct Turkish uppercase conversion (maps 'i' -> 'İ', 'ı' -> 'I')."""
    if not s:
        return ""
    return s.replace("i", "İ").replace("ı", "I").upper()


# Common Turkish OCR misrecognitions
OCR_REPLACEMENTS = [
    # Ligatures
    (r"\ufb01", "fi"),
    (r"\ufb02", "fl"),
    (r"\ufb00", "ff"),
    (r"\ufb03", "ffi"),
    (r"\ufb04", "ffl"),
    
    # Numbers and symbols misread for whole common Turkish words (must run before generic mid-word rules)
    (r"\bb[1ı]r\b", "bir"),
    (r"\b1le\b", "ile"),
    (r"\b1ç[1ı]n\b", "için"),
    (r"\b1çin\b", "için"),
    (r"\bıle\b", "ile"),
    (r"\bg[1ı]b[1ı]\b", "gibi"),
    (r"\byada\b", "ya da"),

    # Common OCR letter confusions in Turkish
    (r"\bcl([a-zçğıöşüA-ZÇĞİÖŞÜ]+)", r"d\1"),    # clünya -> dünya, clar -> dar
    (r"\b1([a-zçğıöşü]{2,})", r"i\1"),          # 1çinde -> içinde, 1le -> ile
    (r"([a-zçğıöşü])1([a-zçğıöşü])", r"\1ı\2"),   # yap1lan -> yapılan

    # Turkish InDesign / publisher font corruption & glyph mapping fixes
    (r"['\"‘“]?\u0110([a-zçğıöşüA-ZÇĞİÖŞÜ])", r'"A\1'),   # 'Đdı -> "Adı, 'Đnladık -> "Anladık
    (r"\b\u0110([a-zçğıöşü]+)", r"A\1"),
    (r"\u0110", r'"A'),
    (r"[\.;:>\s]{0,2};>[\"”']?", '?"'),                     # ;>" or .;>" -> ?"
    (r"[\.;:>\s]{0,2};>", '?'),                             # ;> -> ?
    (r"\b([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s+[ıi]nı\?", r"\1 mı?"),   # O kadar ını? -> O kadar mı?
    (r"\b[ıi]nı\?", "mı?"),

    # Specific corrupted word / kerning artifacts from publisher PDF text layers
    (r"\bk\s*,\s*,\s*çı\s*ar\.?", " çıkar."),
    (r"[,„\s]{1,4}çı\s*kar\b", " çıkar"),
    (r"\bk\s*,\s*,\s*ıyıp\b", " kıyıp"),
    (r"[,„\s]{1,4}kıyıp\b", " kıyıp"),
    (r'["\'‘“]?M\s*k\s*;\s*>\s*["\'’”]?\s*a\s*as\.?', '"Makas?"'),
    (r'["\'‘“]?M\s*ak\s*as\s*[\.;>\?]+["\'’”]*', '"Makas?"'),
    (r'\bM\s*ak\s*as\b', "Makas"),
    (r'["\'‘“]?Yı\s*f["\'’”]?\s*usu\.?', '"Yusuf."'),
    (r'["\'‘“]?Yıusu\s*f[\.\"]*', '"Yusuf."'),
    (r'H\s*["\']ki\s*\.\s*d\s*["\']\s*er\s*ı\s*sı\s*e\s*\.{2,3}', 'Her ikisi de...'),
    (r'H\s*er\s*ı["\']ki\s*sı\s*d\s*e\s*\.{2,3}', 'Her ikisi de...'),
    (r'E\s*t\s*:\s*ve\s*[•\.]*', 'Evet.'),
    (r'b\s*\.\s*I["\']\s*arı\.?', 'bari.'),
    (r"\bN\s*e\s*den\s*[\.;>]+", 'Neden?"'),
    (r"\bYusufa\b", "Yusuf'a"),
    
    # Quotation & punctuation normalization
    (r"[«»]|<<|>>", '"'),                      # Guillemets and double angle brackets -> double quote
    (r"(?<=\s)<(?=[a-zçğıöşüA-ZÇĞİÖŞÜ])", '"'), # OCR '<kelime' -> '"kelime' (misread open quote)
    (r"(?<=[a-zçğıöşüA-ZÇĞİÖŞÜ])>(?=[\s\.,;:\?!]|$)", '"'), # OCR 'kelime>' -> 'kelime"' (misread close quote)
    (r"\s+[<>]\s+", " "),                       # Standalone stray < or > noise
    (r"''", '"'),                               # Double single quote -> double quote
    (r"[\u2018\u2019\u201A\u201B]", "'"),
    (r"[\u201C\u201D\u201E\u201F]", '"'),
    (r"[\u2013\u2014\u2015]", "—"),            # en-dash, em-dash, horizontal bar -> em-dash

    # OCR misread quotation marks (closing quotes read as '2)', '9)', '?)'; opening quotes as '((', 'K(', '(C'', 'c')
    (r"[,;:\.]*\s*[29]\)\s*(?=(?:dedi|diye|demi|sordu|fısıldadı|mırıldandı)\b)", '," '),
    (r"[\.;:\'\*\_]+\s*[29]\)\s*(?=[A-ZÇĞİÖŞÜ])", '." '),
    (r"([a-zçğıöşü])\s*[29]\)\s*(?=[A-ZÇĞİÖŞÜ])", r'\1." '),
    (r"[,;:]+\s*[29]\)", ',"'),
    (r"\s*[29]\)", '"'),
    (r"(\?+)\s*\)", r'\1"'),
    (r"\(\(\s*['\"]?", '"'),
    (r"K[\(<]\s*['\"]?", '"'),
    (r"\(C['\"]\s*", '"'),
    (r"\(6\s*(?=[0-9A-ZÇĞİÖŞÜ])", '"'),
    (r"(?<=\s)c(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+[\?!])", '"'),

    (r"\s*([,;:\.!?])", r"\1"),                # Remove space before punctuation
    (r"([,;:])([^\s\d\"'\)—])", r"\1 \2"),      # Ensure space after punctuation
    (r"\s+—\s+", " — "),                       # Normalize dash spacing
    (r"^[-–—]\s*", "— "),                      # Dialogue dash at line start
    (r"\s*\.\.\.\s*", "... "),                 # Normalize ellipsis spacing
    (r"\.\.\.\s+([\"”\'])", r"...\1"),
]

# Common Turkish words split by stray spaces or bad line breaks
KNOWN_WORD_SPLITS = [
    (r"\bbu\s+landırır\b", "bulandırır"),
    (r"\bdaya\s+namaz\b", "dayanamaz"),
    (r"\bse\s+kiz\b", "sekiz"),
    (r"\byüzü\s+nü\b", "yüzünü"),
    (r"\byük\s+seltti\b", "yükseltti"),
    (r"\bhallede\s+yim\b", "halledeyim"),
    (r"\bmaka\s+sı\b", "makası"),
    (r"\bsey\s+reltti\b", "seyreltti"),
    (r"\bşaşı\s+rarak\b", "şaşırarak"),
    (r"\bbirleş\s+tirdi\b", "birleştirdi"),
    (r"\bmilletve\s+kili\b", "milletvekili"),
    (r"\bistifa\s+sını\b", "istifasını"),
    (r"\bhayıfla\s+nan\b", "hayıflanan"),
    (r"\bbakı\s+açısı\b", "bakış açısı"),
    (r"\bHAS\s*R\s*ET\b", "HASRET"),
    (r"\bE\s*LVE\s*DA\b", "ELVEDA"),
    (r"\bVATAN\s*I\s*M\b", "VATANIM"),
    (r"\bAYR\s*I\s*LI\s*K\b", "AYRILIK"),
    (r"\bY\s*[İIıi]\s*N\s*E\b", "YİNE"),
    (r"\bZ\s*[VÜüUu]\s*R\s*[İIıi]\s*H\s*['’]?\s*TE\b", "ZÜRİH'TE"),
    (r"\bZ\s*[VÜüUu]\s*R\s*[İIıi]\s*H\b", "ZÜRİH"),
    (r"\bZAMAN\s*1\b", "ZAMANI"),
    (r"\bAYYILDIZLl\b", "AYYILDIZLI"),
]

# Patterns for compound hyphenated words that should PRESERVE hyphens
COMPOUND_PREFIXES = {
    "sosyo", "psiko", "fiziko", "biyo", "morfo", "etno", "makro", "mikro",
    "oto", "tele", "antrop", "termo", "aristo", "türk", "islam", "osmanlı",
    "arap", "avrupa", "asya", "batı", "doğu", "kuzey", "güney"
}


class TextCleaner:
    def __init__(self):
        self.repeated_headers: Set[str] = set()

    def normalize_unicode(self, text: str) -> str:
        """Normalizes Unicode characters into standard NFC form and fixes decomposed diacritics."""
        if not text:
            return ""
        # NFC normalizes combining accents like s + ¸ into ş
        text = unicodedata.normalize("NFC", text)
        return text

    def clean_ocr_errors(self, text: str) -> str:
        """Fixes common OCR recognition artifacts and ligatures."""
        for pattern, replacement in OCR_REPLACEMENTS:
            text = re.sub(pattern, replacement, text)
        return text

    def heal_split_words(self, text: str) -> str:
        """
        Repairs Turkish words split by unintended whitespace, faulty font kerning, or broken line-wraps.
        e.g., 'bu landırır' -> 'bulandırır', 'se kiz' -> 'sekiz', 'yüzü nü' -> 'yüzünü'
        """
        if not text:
            return ""

        # Step 0: Normalize whitespace around apostrophes so possessive suffixes attach cleanly
        text = re.sub(r"(?<=[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])[ \t]*['’][ \t]*([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]+)", r"'\1", text)
        text = re.sub(r"\b(['’])[ \t]*([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]+)", r"\1\2", text)

        # Step 1: Broken hyphen with spaces around it: e.g. 'son - raki' -> 'sonraki'
        text = re.sub(r"(?<=[a-zçğıöşüA-ZÇĞİÖŞÜ])[ \t]*[-–—\xad][ \t]+([a-zçğıöşüA-ZÇĞİÖŞÜ]+)", r"\1", text)

        # Step 2: Specific known splits
        for pattern, rep in KNOWN_WORD_SPLITS:
            text = re.sub(pattern, rep, text, flags=re.IGNORECASE)

        # Step 3: General rule for runs of 3+ single letters (any case):
        # e.g. 'Y İ N E' -> 'YİNE', 'B Ö L Ü M' -> 'BÖLÜM', 'i l k' -> 'ilk', 'g e l' -> 'gel'
        def merge_single_letters(m):
            return "".join(m.group(0).split())
        text = re.sub(r"\b[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ](?:[ \t]+[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]){2,}\b", merge_single_letters, text)

        # Step 4: Impossible standalone Turkish suffixes when detached from preceding root
        # e.g., 'istifa sını' -> 'istifasını', 'birleş tirdi' -> 'birleştirdi'
        text = re.sub(r"\b([a-zçğıöşüA-ZÇĞİÖŞÜ]{3,})[ \t]+(sını|sini|tirdi|türdü|tırdı|turdu|seltti|reltti|rarak|rerek)\b", r"\1\2", text)

        # Step 5: General rule for single letters stranded before word (excluding 'o'/'O' which is a Turkish pronoun):
        # e.g. 'E sra'm' -> 'Esra'm', 'k ader' -> 'kader', 'ç are' -> 'çare'
        text = re.sub(r"(?<!['’])\b([a-np-zA-NP-ZçğıöşüÇĞİÖŞÜ])[ \t]+([a-zçğıöşü]{2,})\b", r"\1\2", text)

        # Step 6: General rule for single consonants stranded inside words:
        # e.g. 'HAS R ET' -> 'HASRET'
        text = re.sub(r"\b([a-zçğıöşüA-ZÇĞİÖŞÜ]{2,})[ \t]+([bcçdfgğhjklmnprsştvyzBCÇDFGĞHJKLMNPRSŞTVYZ])[ \t]+([a-zçğıöşüA-ZÇĞİÖŞÜ]{2,})\b", r"\1\2\3", text)

        # Step 7: Trailing 1st/2nd/3rd person possessive/case single letters:
        # e.g. 'VATAN I M' -> 'VATANIM', 'nerdes i n' -> 'nerdesin'
        text = re.sub(r"\b([a-zçğıöşüA-ZÇĞİÖŞÜ]{3,})[ \t]+([IİıiUÜuü])[ \t]+([mMkKnN])\b", r"\1\2\3", text)

        # Step 8: Trailing verbal suffixes e.g. 'açmamalıydı m' -> 'açmamalıydım'
        text = re.sub(r"\b([a-zçğıöşüA-ZÇĞİÖŞÜ]{3,}d[ıiueü]|malıy[ıi]|meliy[iı])[ \t]+([mnk])\b", r"\1\2", text)

        # Step 9: Strip accidental whitespace before punctuation:
        text = re.sub(r"[ \t]+([,\.;:!\?])", r"\1", text)
        text = re.sub(r"[ \t]{2,}", " ", text)

        return text

    def is_likely_page_number(self, line: str) -> bool:
        """Determines if a single line is just a page number (e.g. '14', '- 25 -', '[ 42 ]', '139_')."""
        s = line.strip()
        if not s:
            return False
        # Matches numbers with optional dashes, underscores, dots, or brackets
        if re.match(r"^[-–—_=\*•~·\[\(\s]*\d{1,4}[-–—_=\*•~·\]\)\.\s]*$", s):
            return True
        # Roman numerals e.g. 'iv', 'VII'
        if re.match(r"^[ivxlcdmIVXLCDM]{1,6}$", s):
            return True
        return False

    def is_likely_header_footer(self, line: str, book_title: Optional[str] = None, author: Optional[str] = None) -> bool:
        """Determines if a line is a running header or footer that shouldn't appear in body text."""
        s = line.strip()
        if len(s) < 2 or len(s) > 100:
            return False

        if self.is_likely_page_number(s):
            return True

        s_lower = turkish_lower(s)
        s_clean = re.sub(r"[^\w\s]", "", s_lower).strip()

        if book_title:
            bt_clean = re.sub(r"[^\w\s]", "", turkish_lower(book_title)).strip()
            if bt_clean and bt_clean in s_clean and len(s_clean) < len(bt_clean) + 15:
                return True

        if author:
            auth_clean = re.sub(r"[^\w\s]", "", turkish_lower(author)).strip()
            if auth_clean and auth_clean in s_clean and len(s_clean) < len(auth_clean) + 15:
                return True

    def is_likely_garbage_line(self, line: str) -> bool:
        """
        Detects OCR noise lines typically caused by illustrations, diagrams, or decorative graphics
        (e.g. ')).• c •., ;; :. >l\'., , ☐- Ò -; ·J/ /.; ___-', 'QR\\S. ,.;- \"\" -.:3\'', '— -..: CĈ').
        """
        s = line.strip()
        if not s:
            return False

        # Page numbers and TOC dot leaders are not garbage
        if self.is_likely_page_number(s):
            return False
        if re.search(r"\.{3,}\s*\d+$", s):
            return False

        # Standalone ornament lines (§, •, *, ~, ---, quotes)
        if re.match(r"^[\s§\*•~♦—\-_=\'\"]{1,10}$", s):
            return True

        # Standalone single letters on their own line (e.g. stray 'k', 'l')
        if len(s) == 1 and not s.isdigit():
            return True

        letters = re.findall(r"[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]", s)
        total_len = len(s)

        # 1. Pure symbol / punctuation noise without any letters
        if len(letters) == 0:
            return True

        # 2. Extreme symbol ratio (symbols / punctuation far outweighing letters)
        # Often occurs when OCR scans drawings, banners, or ornaments
        ratio = len(letters) / total_len
        if total_len >= 3 and ratio < 0.40:
            # Check for characteristic OCR noise patterns (slashes, repeated punctuation, underscores)
            if re.search(r"[\\/_;:,\.]{2,}|[\\/]|--\.\.|:\s*[A-Z]", s) or len(letters) <= 2:
                return True

        # 3. Short nonsense noise snippets (<= 15 chars with <= 2 letters and mixed symbols)
        if total_len <= 15 and len(letters) <= 2 and re.search(r"[-–—_=\\/\.:;,\'\"!§\*~]", s):
            return True

        # 4. Stray OCR consonant codes / words with no vowels (e.g. 'DVrTV', 'D VrTV -')
        has_vowel = bool(re.search(r"[aeıioöuüAEIİOÖUÜ]", s))
        if not has_vowel and len(letters) >= 3 and not (s.isupper() and len(letters) <= 4):
            return True

        return False

    def dehyphenate(self, text: str) -> str:
        """
        Reconstructs words broken across line wraps by a hyphen or soft-hyphen (\xad).
        Example: 'öğren-\n ciler' -> 'öğrenciler', 'son - raki' -> 'sonraki'
        Preserves true compound words like 'Türk-\n İslam' -> 'Türk-İslam'
        """
        def merge_hyphen(match):
            word1 = match.group(1)
            word2 = match.group(2)
            
            # Check if this is a compound word that should keep its hyphen
            if word1.lower() in COMPOUND_PREFIXES:
                return f"{word1}-{word2}"
            if word1.isupper() and word2.isupper() and len(word1) > 1 and len(word2) > 1:
                return f"{word1}-{word2}"
            if word1[0].isupper() and word2[0].isupper():
                return f"{word1}-{word2}"
                
            # Normal word broken across line: merge without hyphen
            return f"{word1}{word2}"

        # Match word ending with hyphen or soft-hyphen across newline
        pattern_nl = r"([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s*[-–—\xad]\s*\n\s*([a-zçğıöşüA-ZÇĞİÖŞÜ]+)"
        text = re.sub(pattern_nl, merge_hyphen, text)

        # Match word ending with hyphen or soft-hyphen across any whitespace (e.g. 'son - raki')
        pattern_ws = r"([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s*[-–—\xad]\s+([a-zçğıöşüA-ZÇĞİÖŞÜ]+)"
        text = re.sub(pattern_ws, merge_hyphen, text)

        # Remove any lingering standalone soft hyphens
        text = text.replace("\xad", "")
        return text

    def reconstruct_paragraphs(self, lines: List[str]) -> List[str]:
        """
        Takes raw lines from a page or chapter and reconstructs flowing paragraphs.
        Distinguishes between paragraph continuation and new paragraphs (dialogue, headings, etc.).
        """
        paragraphs: List[str] = []
        current_p: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_p:
                    paragraphs.append(" ".join(current_p))
                    current_p = []
                continue

            # Check if this line is a page number
            if self.is_likely_page_number(stripped):
                continue

            # Filter out illustration OCR garbage noise and standalone ornament lines
            if self.is_likely_garbage_line(stripped):
                if current_p:
                    paragraphs.append(" ".join(current_p))
                    current_p = []
                continue

            # Detect short standalone heading / title lines (e.g. 'SEVDA', 'BÖLÜM 1', 'YUSUF')
            upper_chars = len([c for c in stripped if c.isupper()])
            lower_chars = len([c for c in stripped if c.islower()])
            is_standalone_heading = (
                (upper_chars >= 3 and lower_chars <= 2 and len(stripped) <= 60)
                or re.match(r"^(?:bölüm|kısım|\d+\.|\w+\s+günü)\b", stripped, re.IGNORECASE)
            ) and not re.search(r"[\.!\?,;:]$", stripped)

            is_dialogue = stripped.startswith("—") or stripped.startswith("- ")
            
            if is_standalone_heading:
                if current_p:
                    paragraphs.append(" ".join(current_p))
                    current_p = []
                # Clean any ornament dashes inside or around heading (e.g. '------ ZAMAN' -> 'ZAMAN')
                clean_heading = re.sub(r"[-–—_]{2,}", " ", stripped)
                clean_heading = re.sub(r"\s+", " ", clean_heading).strip()
                if not clean_heading:
                    continue

                # If previous paragraph was also a short standalone heading, merge them:
                # e.g. 'ELVEDA' + 'VATANIM' -> 'ELVEDA VATANIM'
                # e.g. 'YİNE' + 'HASRET' -> 'YİNE HASRET'
                # e.g. 'ZÜRİH'TE' + 'ZAMAN' -> 'ZÜRİH'TE ZAMAN'
                # Do NOT merge if either line contains numbers or commas (e.g. 'MART 1933, FRANKFURT')
                can_merge = (
                    paragraphs and
                    len(paragraphs[-1]) <= 35 and
                    paragraphs[-1].isupper() and
                    not re.search(r"[\.!\?,;:]$", paragraphs[-1]) and
                    not re.search(r"[\d,]", stripped) and
                    not re.search(r"[\d,]", paragraphs[-1])
                )
                if can_merge:
                    paragraphs[-1] = f"{paragraphs[-1]} {clean_heading}"
                else:
                    paragraphs.append(clean_heading)
            elif is_dialogue:
                if current_p:
                    paragraphs.append(" ".join(current_p))
                    current_p = []
                current_p.append(stripped)
            elif not current_p:
                current_p.append(stripped)
            else:
                prev_text = current_p[-1].strip()
                prev_upper = len([c for c in prev_text if c.isupper()]) >= 3 and len([c for c in prev_text if c.islower()]) <= 2
                ends_with_terminal = bool(re.search(r"[\.!\?…\"”']$", prev_text))
                is_dialogue_start = stripped.startswith('"') or stripped.startswith('“') or stripped.startswith("—") or stripped.startswith("- ")
                
                if (ends_with_terminal or prev_upper) and (stripped[0].isupper() or stripped[0].isdigit() or is_dialogue_start):
                    # Likely new paragraph
                    paragraphs.append(" ".join(current_p))
                    current_p = [stripped]
                else:
                    # Paragraph continuation: join with a space
                    current_p.append(stripped)

        if current_p:
            paragraphs.append(" ".join(current_p))

        # Final cleanup for each paragraph
        cleaned_paragraphs = []
        for p in paragraphs:
            p = re.sub(r"\s+", " ", p).strip()
            p = self.dehyphenate(p)
            p = self.clean_ocr_errors(p)
            p = self.heal_split_words(p)
            if p:
                cleaned_paragraphs.append(p)

        return cleaned_paragraphs

    def process_full_text(self, text: str, book_title: Optional[str] = None, author: Optional[str] = None) -> str:
        """Runs the complete cleaning pipeline on raw text."""
        text = self.normalize_unicode(text)
        text = self.clean_ocr_errors(text)

        lines = text.split("\n")
        filtered_lines = [
            l for l in lines 
            if not self.is_likely_header_footer(l, book_title=book_title, author=author)
            and not self.is_likely_garbage_line(l)
        ]

        cleaned_lines = [self.heal_split_words(l) for l in filtered_lines]
        joined = "\n".join(cleaned_lines)
        joined = self.dehyphenate(joined)

        paragraphs = self.reconstruct_paragraphs(joined.split("\n"))
        return "\n\n".join(paragraphs)
