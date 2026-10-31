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


# Common Turkish abbreviations where period before lowercase is expected
TURKISH_ABBREVIATIONS = {
    "vb", "vs", "bkz", "dr", "prof", "av", "sn", "st", "jr", "mr", "mrs", "ms",
    "sf", "s", "no", "mad", "cad", "sok", "apt", "bl", "böl"
}


# Common Turkish OCR misrecognitions
OCR_REPLACEMENTS = [
    # Ligatures
    (r"\ufb01", "fi"),
    (r"\ufb02", "fl"),
    (r"\ufb00", "ff"),
    (r"\ufb03", "ffi"),
    (r"\ufb04", "ffl"),
    
    # Numbers and symbols misread for whole common Turkish words
    (r"\bb[1ı]r\b", "bir"),
    (r"\b1le\b", "ile"),
    (r"\b1ç[1ı]n\b", "için"),
    (r"\b1çin\b", "için"),
    (r"\bıle\b", "ile"),
    (r"\bg[1ı]b[1ı]\b", "gibi"),
    (r"\byada\b", "ya da"),

    # Middle dots and bullets appearing as dirt inside or around words
    (r"(?<=[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])[ \t]*[·•][ \t]*(?=[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])", ""),
    (r"[·•]\s*([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]+)", r"\1"),

    # In-word periods from dust/scan noise (e.g. 'Mex.ico' -> 'Mexico', 'Gr.aciela' -> 'Graciela')
    (r"(?<=[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]{2})\.(?=[a-zçğıöşü]{2,}\b)", ""),

    # Double/stray quotes inside words (e.g. 'dünya"y"ıgözlerimizin' -> 'dünyayı gözlerimizin')
    (r'([a-zçğıöşüA-ZÇĞİÖŞÜ])["”\']([a-zçğıöşüA-ZÇĞİÖŞÜ])["”\']([a-zçğıöşüA-ZÇĞİÖŞÜ])\s*', r'\1\2\3 '),
    (r'(?<=[a-zçğıöşü])"(?=[a-zçğıöşü])', ""),
    (r'\b[1ı]{2}(?=[A-ZÇĞİÖŞÜ])', '"'),  # '11En iyi' / 'ııEn iyi' -> '"En iyi'

    # Ampersand misrecognitions inside words & standard expressions
    (r"\bbu\s+ar&\s+da\s+da\b", "bu arada da"),
    (r"\bar&\s+da\s+da\b", "arada da"),
    (r"\bar&\s+da\b", "arada"),
    (r"\bd&vam\b", "devam"),
    (r"\bOys&\b", "Oysa"),
    (r"\boyn&\b", "oyna"),
    (r"([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])&([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])", r"\1a\2"),

    # Digit '7' misread for question mark '?'
    (r"(\b(?:mı|mi|mu|mü|misin|misiniz|musun|musunuz|miydi|mıydı|miymiş|mıymış|miyim|mıyım))7\b", r"\1?"),
    (r"([a-zçğıöşüA-ZÇĞİÖŞÜ]{3,})7\b(?=[\s\"”'\)—\.\?!]|$)", r"\1?"),
    (r"(\bm[ıi]|\bmu|\bmü):(?=\?)", r"\1"),
    (r":+\?", "?"),

    # Common OCR letter confusions in Turkish
    (r"\bcl([a-zçğıöşüA-ZÇĞİÖŞÜ]+)", r"d\1"),    # clünya -> dünya, clar -> dar
    (r"\b[ı1]([aeiouöüAEIİOUÖÜ][a-zçğıöşü]{2,})\b", r"\1"),  # Leading stray dotless-ı/1 before vowel (1istediğim -> istediğim)
    (r"\b1([a-zçğıöşü]{2,})", r"i\1"),          # 1çinde -> içinde, 1le -> ile
    (r"([a-zçğıöşü])1([a-zçğıöşü])", r"\1ı\2"),   # yap1lan -> yapılan

    # Specific corrupted author, character, and title names
    (r"\bOscar\s+[ıIİi1]?[lL]ew[li]s\b", "Oscar Lewis"),
    (r"\b[ıIİi1][lL]ew[li]s\b", "Lewis"),
    (r"\böldüSünde\b", "öldüğünde"),
    (r"\bbaS\b", "bağ"),
    (r"\bteşekkOr\b", "teşekkür"),
    (r"\bÇOnkü\b", "Çünkü"),
    (r"\bçOnkü\b", "çünkü"),
    (r"\b[lL][1ıli]{2}tin\b", "Latin"),
    (r"\b[lıhI][1ıli]{1,3}nois\b", "Illinois"),
    (r"\bb['’]otçluyum\b", "borçluyum"),
    (r"\bpro\s*tok['’]?olleri\b", "protokolleri"),
    (r"\bçBzümleme[^\s]*\b", "çözümlemeler"),
    (r"\byardıiııci\b", "yardımcı"),
    (r"\boldu(?:ouiçin|ॗuiçin|u\s*için)\b", "olduğu için"),
    (r"\bte\s*şekkür\b", "teşekkür"),
    (r"\bTe['’]st\b", "Test"),
    (r"\bAy['’]nı\b", "Aynı"),
    (r"\bMek['’]sika\b", "Meksika"),
    (r"\bMek['’]sika'", "Meksika'"),
    (r"\bÇocukla['’]rı['’]nda\b", "Çocukları'nda"),
    (r"\banlayıx\b", "anlayış"),
    (r"\b([a-zçğıöşü]+)[ıi]x\b", r"\1ış"),
    (r"\bCQCUKLARI\b", "ÇOCUKLARI"),
    (r"\bCQCUK\b", "ÇOCUK"),
    (r"\bSANCEZ\b", "SANÇEZ"),
    (r"\banlcıtılan\b", "anlatılan"),
    (r"\bdavrcınışla\b", "davranışla"),
    (r"\bde-?\s*vcım\b", "devam"),
    (r"\bdcı\b", "da"),
    (r"\bVecindacl\b", "Vecindad"),
    (r"\bvecindacl\b", "vecindad"),
    (r"\bVecinclad\b", "Vecindad"),
    (r"\bVect[ıi]dad\b", "Vecindad"),
    (r"\blııaldeki\b", "haldeki"),
    (r"\bhIaldeki\b", "haldeki"),
    (r"\bU\s+lan\b", "Ulan"),
    (r"\bEllt\s+altı\b", "Elli altı"),
    (r"\byuzu\s+gozu\b", "yüzü gözü"),

    # Book-specific OCR distortions and internal colon/character misrecognitions
    (r"\botw:\s*anların\b", "oturanların"),
    (r"\bPa:\s*[ıi1]w\b", "Pazar"),
    (r"\bgizlfliği([a-zçğıöşü]*)\b", r"gizliliği\1"),
    (r"\bCompaclre\b", "Compadre"),
    (r"\b([A-Za-zçğıöşü]+)clre\b", r"\1dre"),
    (r"\bekraba\b", "akraba"),
    (r"\b[ı1]evine\b", "evine"),
    (r"\b[ı1]([aeiouöü][a-zçğıöşü]{2,})\b", r"\1"),  # Leading stray dotless-ı/1 before vowel
    (r"\b([a-zçğıöşüA-ZÇĞİÖŞÜ]+)ıe(ri|re|r|k|n|ce|cek|di|miş|mez)\b", r"\1le\2"),  # ödemeıeri -> ödemeleri
    (r"\bGua['’]dalupe\b", "Guadalupe"),
    (r"\bol[ıi1]?v[ıi1]ağı\b", "olanağı"),
    (r"\bBunlarkısa\b", "Bunlar kısa"),
    (r"\bTaca\s*\([o0]{2,3}\)", "Taco (*)"),
    (r"\bPulq['’]ue\b", "Pulque"),
    (r"\bSablrtıt['’]?uyla\b", "Sabır otuyla"),
    (r"\bhe[\.\s•]*[ıi]?,?\s*le\s*ne\s*rak\b", "haşlanarak"),
    (r"\blahme\.?eun\b", "lahmacun"),
    (r"\bTal[ıi]:\s*o:\s*", "Taco: "),
    (r"\bkültürü\s+[ıi1]\s+içinde\b", "kültürü içinde"),
    (r"\b([A-Za-zçğıöşü]+)cl\b", r"\1d"),  # Word-final 'cl' misread for 'd'
    (r"\bclemiştim\b", "demiştim"),
    (r"\bmukavvadanclı\b", "mukavvadandı"),
    (r"\bcenclzeyle\b", "cenazeyle"),
    (r"\bGraclela\b", "Graciela"),
    (r"\bgeJ:irlerini\b", "gelirlerini"),
    (r"\bçocui:jU\b", "çocuğu"),
    (r"\btutıH:ağını\b", "tutacağını"),
    (r"\bhc:lt\b", "halt"),
    (r"\bso:ğnüyorum\b", "söylüyorum"),
    (r"\bso:rdu\b", "sordu"),
    (r"\bgide:k\b", "gidecek"),
    (r"\bolmc:dı\b", "olmadı"),
    (r"\bz:aman\b", "zaman"),
    (r"\bnıyordu:n\b", "nıyordun"),
    (r"\bipli:k\b", "iplik"),
    (r"\bCe[\.re]{3,6}mbe\.?\b", "Caramba"),
    (r"\bChnlto\b", "Chinito"),
    (r"\bmanatinas\b", "mañanitas"),
    (r"\bceatav'o\b", "centavo"),
    (r"\bNovl[ıi1]\.?\b", "Novia"),
    (r"\bNovlo\b", "Novio"),
    (r"\bTortille\.?\b", "Tortilla"),
    (r"\bAl:,\s*al:,\s*ak\b", "Agüita, agüita, agua"),
    (r"([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]+)\s*[\.,;:>]+\s*:", r"\1:"),  # Strip stray period/comma before colon in definition terms
    (r"\.\.(?!\.)", "."),  # Double periods to single period

    # OCR noise: underscores inside words (e.g. ye_dim -> yedim, etm_ek -> etmek)
    (r"([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])_([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])", r"\1\2"),

    # OCR noise: \J or \j inside words (e.g. Man\Jel -> Manuel, yokt\Jr -> yoktur)
    (r"\bMan\\?Jel\b", "Manuel"),
    (r"([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])\\[Jj]([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])", r"\1u\2"),
    (r"\bbüyuk\b", "büyük"),

    # Digits misread for letters or punctuation inside Turkish words
    (r"\b1Vecindadn\b", '"Vecindad"'),
    (r"\bcccompadre1\b", '"compadre"'),
    (r"\bAllah1\b", "Allah!"),
    (r"\b(ha|o|ki|ya|ne|mi|mı|mu|mü|bu|şu|kim|sen|ben|biz|siz|nerede|nasıl|niçin|neden)7\b", r"\1?"),
    (r"\b8ir\b", "bir"),
    (r"\bp2ra\b", "para"),
    (r"\by3tak", "yatak"),
    (r"\b([a-zçğıöşü]+)l8\b", r"\1li"),
    (r"\bg6r([a-zçğıöşü]*)", r"gör\1"),
    (r"\b9([a-zçğıöşü]{2,})", r"g\1"),
    (r"([a-zçğıöşü])9([a-zçğıöşü])", r"\1g\2"),

    # Trailing roman numerals at the end of preface paragraphs
    (r",\s*[ivxlcdmı1u]{1,6}\s*[·•\.]*$", "."),

    # Stray apostrophes splitting common lowercase words (birey'cilik -> bireycilik, şük'ran -> şükran)
    (r"\b([a-zçğıöşü]{2,})['’]([a-zçğıöşü]{2,})\b", r"\1\2"),

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

    # Target paragraph fixes and associated OCR distortions
    (r"\bt<\![\?ŞşsSl1ıt]{3,8}\.?", "taşıttı."),
    (r"\bmahallelıırinde\b", "mahallelerinde"),
    (r"([a-zçğıöşüA-ZÇĞİÖŞÜ]+)lııri([a-zçğıöşü]*)", r"\1leri\2"),
    (r"\b(?:bir\s+)?süTü\b", "bir sürü"),
    (r"[«\"“<]{0,2}[Vv]ecindadn?dı\b", '"Vecindad"dı'),
    (r"\bikl\b(?=\s+[a-zçğıöşü]+)", "iki"),
    (r"\bizlenic\s+mini\b", "izlenimini"),
    (r"\bçengal([a-zçğıöşü]*)\b", r"çengel\1"),
    (r"\bEh\.\s*babam\b", "Eh, babam"),
    (r"\bHem\s*:\s*sonra\b", "Hem sonra"),
    (r"\bihaneye\s+uğra", "ihanete uğra"),

    # Strip leaked printer sheet forma signatures inside text (e.g. "sançezin çocukları 81/6", "saoçezio ocokları 225/15", "17/2")
    (r"\b[sSşŞ][a-zA-ZçğıöşüA-ZÇĞİÖŞÜ'’\s]{3,22}\s+\d{1,4}\s*[\/\\]\s*\d{1,3}\b\.?", ""),

    # General 'lıı' OCR distortions across the book
    (r"\bPaulıı\b", "Paula"),
    (r"\bNovlıı\b", "Novia"),
    (r"\balıırak\b", "alarak"),
    (r"\borı\s+larlıı\b", "onlarla"),
    (r"\btoplıımaya\b", "toplamaya"),
    (r"\bonlıırla\b", "onlarla"),
    (r"\bşarlıı([a-zçğıöşü]*)\b", r"şarkı\1"),
    (r"\bmutlıı\s*olacak\b", "mutlu olacak"),
    (r"\b(?:lıııcı|illlcı)\b", "ilacı"),
    (r"\blıabama\b", "babama"),
    (r"\bçıkl\!ıırdı\b", "çıkardı"),

    # Publisher font artifacts: capital 'A' for Turkish circumflex 'â'
    (r"\b(dükk|nik|sil|imk|fedak|rüzg|hik|ihtil|il|tel|şik)A([a-zçğıöşü]*)\b", r"\1â\2"),
    (r"\bplAtform([a-zçğıöşü]*)\b", r"platform\1"),
    (r"\bpilAv\b", "pilav"),
    (r"\bfanilA([a-zçğıöşü]*)\b", r"fanila\1"),

    # Internal uppercase letters in common words
    (r"\bbatJm\b", "babam"),
    (r"\btJaha\b", "daha"),
    (r"\bduyJum\b", "duydum"),
    (r"\bbütDn\b", "bütün"),
    (r"\bbüyDk\b", "büyük"),
    (r"\bkötülDkleri\b", "kötülükleri"),
    (r"\bkenQlmizi\b", "kendimizi"),
    (r"\bmahkQm([a-zçğıöşü]*)\b", r"mahkûm\1"),
    (r"\bşükQr\b", "şükür"),
    (r"\bhükCımet\b", "hükümet"),
    (r"\bdeğHdim\b", "değildim"),
    (r"\buzatabiHyorduk\b", "uzatabiliyorduk"),
    (r"\bolabiHr\b", "olabilir"),
    (r"\bgiriŞtim\b", "giriştim"),
    (r"\bkoŞuyorlardı\b", "koşuyorlardı"),
    (r"\bhoŞtu\b", "hoştu"),
    (r"\bgeÇirdi\b", "geçirdi"),
    (r"\bseYdiğini\b", "sevdiğini"),
    (r"\btutPrak\b", "tutarak"),
    (r"\bsöylPrdi\b", "söylerdi"),
    (r"\bsöylQyordu\b", "söylüyordu"),
    (r"\bbeklPdik\b", "bekledik"),
    (r"\bgelmEsine\b", "gelmesine"),
    (r"\bkirlePir\b", "kirletir"),
    (r"\byernPği\b", "yemeği"),
    (r"\bkötüIük([a-zçğıöşü]*)\b", r"kötülük\1"),
    (r"\b(çocuk|insan|birlik)I([a-zçğıöşü]+)\b", r"\1l\2"),

    # Spanish loan words & quotation normalization
    (r"\bcc([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:n|nn)?)\b", r'"\1"'),
    (r"\bccvecindacb>a?", '"vecindad"a '),
    (r"\bccvecindadJ[\"']?\s*", '"vecindad" '),
    (r"\bctCompadre[\"']?", '"Compadre"'),
    (r"\bccAmor\b", '"Amor'),
    (r"\bccCabronn\b", '"Cabrón"'),
    (r"\bccPinche\b", '"Pinche'),
    (r"\bccUlan\b", '"Ulan'),

    # Words split/corrupted with exclamation mark and angle brackets
    (r"\bi<adar\b", "kadar"),
    (r"\barı<adaşlarım\b", "arkadaşlarım"),
    (r"\basr<erle\b", "askerle"),
    (r"\bbecerebil<irsin\b", "becerebilirsin"),
    (r"\bb<ıbamı\b", "babamı"),
    (r"\bduyam<ıdım\b", "duyamadım"),
    (r"\binandırm<ımız\b", "inandırmamız"),
    (r"\buzatm<ık\b", "uzatmak"),
    (r"\bkurtulm<ık\b", "kurtulmak"),
    (r"\bdış<ırı\b", "dışarı"),
    (r"\bharel<et\b", "hareket"),
    (r"\bterl<etmişti\b", "terk etmişti"),
    (r"\bçıl<armadan\b", "çıkarmadan"),
    (r"\böfl<ebelirtisi\b", "öfke belirtisi"),
    (r"\bı<onuşacağını\b", "konuşacağını"),
    (r"\bl<im\b", "kim"),
    (r"\bfarJ<lı\b", "farklı"),
    (r"\byal<aladığı\b", "yakaladığı"),
    (r"\bAvluc\!a\b", "Avluya"),
    (r"\bBöy\!ece\b", "Böylece"),
    (r"\badım\!arımı\b", "adımlarımı"),
    (r"\bbek\!erken\b", "beklerken"),
    (r"\bbit\!tin\b", "bittin"),
    (r"\bbu\!uşrnu\b", "buluşmuş"),
    (r"\bçal\!ıuk\b", "çabuk"),
    (r"\bdol\!rusu\b", "doğrusu"),
    (r"\bdönd\!lğü\b", "döndüğü"),
    (r"\bekme\!ti\b", "ekmekti"),
    (r"\bg\!llmezler\b", "gülmezler"),
    (r"\bh\!lla\b", "hâlâ"),
    (r"\biç\!erinde\b", "içlerinde"),
    (r"\bkarşılı\!jında\b", "karşılığında"),
    (r"\bkavl\!aederdik\b", "kavga ederdik"),
    (r"\bkaydo\!dum\b", "kaydoldum"),
    (r"\bkova\!ardı\b", "kovalardı"),
    (r"\bo\!du\b", "oldu"),
    (r"\bo\!ılan\b", "oğlan"),
    (r"\bon\!ar\b", "onlar"),
    (r"\bşek\!iıde\b", "şekilde"),
    (r"\bödememi\!sterdi\b", "ödememi isterdi"),
    (r"\bşi\!ymiş\b", "şeymiş"),
    (r"\bşiki\!ıyet\b", "şikâyet"),
    (r"\bya\!an\b", "yalan"),
    (r"\byer\!erse\b", "yerlerse"),
    (r"\byatal\!ileceğimizi\b", "yatabileceğimizi"),
    (r"\bpli\!ınlamayı\b", "planlamayı"),
    (r"\bKi\!ır\b", "Kâr"),
    (r"\bda\!Jlar\b", "dağlar"),
    (r"\boralf\!rın\b", "oraların"),
    (r"\bl\!Zatmayalım\b", "uzatmayalım"),

    # Underscores at start or end of words
    (r"(?<=\s)_([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]+)", r"\1"),
    (r"([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]+)_(?=[\s\.,;:\?!]|$)", r"\1"),
    
    # Quotation & punctuation normalization
    (r"[«»]|<<|>>", '"'),                      # Guillemets and double angle brackets -> double quote
    (r"(?<=\s)<(?=[a-zçğıöşüA-ZÇĞİÖŞÜ])", '"'), # OCR '<kelime' -> '"kelime' (misread open quote)
    (r"(?<=[a-zçğıöşüA-ZÇĞİÖŞÜ])>(?=[\s\.,;:\?!]|$)", '"'), # OCR 'kelime>' -> 'kelime"' (misread close quote)
    (r"\s+[<>]\s+", " "),                       # Standalone stray < or > noise
    (r"''", '"'),                               # Double single quote -> double quote
    (r"[\u2018\u2019\u201A\u201B]", "'"),
    (r"[\u201C\u201D\u201E\u201F]", '"'),
    (r"[\u2013\u2014\u2015]", "—"),            # en-dash, em-dash, horizontal bar -> em-dash

    # OCR misread quotation marks
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
    (r"\bHAS\s+R\s+ET\b", "HASRET"),
    (r"\bE\s+LVE\s+DA\b", "ELVEDA"),
    (r"\bVATAN\s+I\s+M\b", "VATANIM"),
    (r"\bAYR\s+I\s+LI\s+K\b", "AYRILIK"),
    (r"\bY\s+[İIıi]\s+N\s+E\b", "YİNE"),
    (r"\bZ\s+[VÜüUu]\s+R\s+[İIıi]\s+H\s*['’]?\s*TE\b", "ZÜRİH'TE"),
    (r"\bZ\s+[VÜüUu]\s+R\s+[İIıi]\s+H\b", "ZÜRİH"),
    (r"\bZAMAN\s+1\b", "ZAMANI"),
    (r"\bAYYILDIZLl\b", "AYYILDIZLI"),
    (r"\bCONSUE\s+LO\b", "CONSUELO"),
    (r"\bConsue\s+lo\b", "Consuelo"),
    (r"\bizlenic\s+mini\b", "izlenimini"),
    (r"\bBir\s*\n\s*Pazar\s+günü\b", "Bir Pazar günü"),
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
        """Normalizes Unicode characters into standard NFC form and fixes decomposed diacritics & non-Latin OCR glyphs."""
        if not text:
            return ""
        # 1. Map specific OCR glyph corruptions from exotic scripts to Turkish characters
        text = text.replace("\u0957", "ğ")  # Devanagari gravity mark used as ğ (olduॗu -> olduğu)
        text = re.sub(r"[\u0A00-\u0A7F]", "Ğ", text)  # Gurmukhi letters used for Ğ (ÇOCUKLUਲ਼UM -> ÇOCUKLUĞUM)

        # 2. Strip exotic non-Latin noise characters (All Indic scripts \u0900-\u0DFF, Tibetan, Ethiopic, Khmer, etc.)
        text = re.sub(r"[\u0900-\u0DFF\u0530-\u058F\u0F00-\u109F\u1200-\u137F\u1780-\u17FF\u0250-\u02AF\u036E\u036F\u25A0-\u27BF]", "", text)

        # 3. NFC normalizes combining accents like s + ¸ into ş
        text = unicodedata.normalize("NFC", text)
        return text

    def clean_ocr_errors(self, text: str) -> str:
        """Fixes common OCR recognition artifacts, ligatures, and Turkish vowel harmony distortions."""
        for pattern, replacement in OCR_REPLACEMENTS:
            text = re.sub(pattern, replacement, text)

        # Capital 'O' in lowercase words (Turkish vowel harmony correction)
        # e.g., 'teşekkOr' -> 'teşekkür', 'ÇOnkü' -> 'Çünkü', 'sOrer' -> 'sürer', 'mahkOm' -> 'mahkûm'
        def fix_capital_o(m):
            word = m.group(0)
            idx = word.find("O")
            before = word[:idx]
            front_vowels = set("eiöüEİÖÜ")
            has_front = any(c in front_vowels for c in before)
            if word.lower().startswith("mahk"):
                rep = "û"
            elif word.lower().startswith("hük"):
                rep = "ü"
            else:
                rep = "ü" if has_front else "u"
            return word.replace("O", rep)

        text = re.sub(r"\b[a-zçğıöşüA-ZÇĞİÖŞÜ]+O[a-zçğıöşü]+\b", fix_capital_o, text)

        # Comma misread as period in non-sentence lists / sequences
        # e.g., 'şiddet. ölüm, acı çekme' -> 'şiddet, ölüm, acı çekme'
        def fix_period_as_comma(m):
            w1 = m.group(1)
            w2 = m.group(2)
            if w1.lower() in TURKISH_ABBREVIATIONS:
                return m.group(0)
            # If followed by lowercase word without verb/sentence break
            return f"{w1}, {w2}"

        text = re.sub(r"\b([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]{2,})\.\s+([a-zçğıöşü]{3,})\b", fix_period_as_comma, text)

        # Period misread as comma after finite verbs before a capitalized sentence starter
        # e.g., 'gelenekselleşmiştir, Bazı kişiler' -> 'gelenekselleşmiştir. Bazı kişiler'
        finite_verb_suffix = re.compile(
            r"(?:miştir|mıştır|muştur|müştür|di|dı|du|dü|ti|tı|tu|tü|mektedir|maktadır|cektir|caktır|yordu|yormuş|malıydı|meliydi)$",
            re.IGNORECASE
        )
        def fix_comma_before_capital(m):
            w_before = m.group(1)
            w_after = m.group(2)
            if finite_verb_suffix.search(w_before):
                return f"{w_before}. {w_after}"
            return m.group(0)

        text = re.sub(r"\b([a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]{3,}),\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,})\b", fix_comma_before_capital, text)

        # Repair merged sentence boundaries where a verb is fused with the following capitalized word without a period
        # e.g., 'boşaltıyordukUzun' -> 'boşaltıyorduk. Uzun', 'yatabilirdiŞilteyi' -> 'yatabilirdi. Şilteyi', 'ediyorlarEh' -> 'ediyorlar. Eh'
        verb_boundary_pattern = re.compile(
            r"\b((?:[a-zçğıöşüA-ZÇĞİÖŞÜ]{2,}?(?:"
            r"yorduk|yordular|yordu|yormuş|yorsunuz|yorsanız|yordum|"
            r"mıştı|mişti|muştu|müştü|mıştık|miştik|muştuk|müştük|"
            r"caktır|cektir|maktadır|mektedir|acaktır|ecektir|"
            r"irdim|erdim|ırdım|urdum|ürdüm|irdi|erdi|ırdı|urdu|ürdü|irdiler|erdiler|"
            r"dim|dım|dum|düm|tim|tım|tum|tüm|"
            r"dik|dık|duk|dük|tik|tık|tuk|tük|"
            r"di|dı|du|dü|ti|tı|tu|tü|"
            r"iyorlar|ıyorlar|üyorlar|uyorlar|diler|dılar|dular|düler|"
            r"iyor|ıyor|üyor|uyor|arlar|erler|"
            r"erse|arsa|mezse|mazsa|miş|mış|muş|müş|"
            r"erkekti)|doğrusu|tabii|böyle))([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,})\b"
        )
        text = verb_boundary_pattern.sub(r"\1. \2", text)

        # Collapse any multiple spaces introduced by stripped noise/sluglines
        text = re.sub(r"[ \t]{2,}", " ", text)

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

        # Step 1: Broken hyphen with spaces around it: e.g. 'son - raki' -> 'sonraki', 'baş · ladım' -> 'başladım'
        text = re.sub(r"(?<=[a-zçğıöşüA-ZÇĞİÖŞÜ])[ \t]*[-–—\xad·•][ \t]+([a-zçğıöşüA-ZÇĞİÖŞÜ]+)", r"\1", text)

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
        """Determines if a single line is just a page number (e.g. '14', '- 25 -', '[ 42 ]', 'vuı ·', 'Vll', 'xı', 'x')."""
        s = line.strip()
        if not s:
            return False
        # Matches numbers with optional dashes, underscores, dots, or brackets
        if re.match(r"^[-–—_=\*•~·\[\(\s]*\d{1,4}[-–—_=\*•~·\]\)\.\s]*$", s):
            return True
        # Roman numerals e.g. 'iv', 'VII', 'Vll', 'IX', 'x', 'xı', 'vuı ·'
        # Normalizes Turkish dotless ı -> i, lowercase l / 1 -> i, u -> ii, strips middle dots & ornaments
        s_roman = s.lower().replace("·", "").replace("•", "").replace("ı", "i").replace("l", "i").replace("1", "i").replace("u", "ii").replace(" ", "").replace("-", "")
        if re.match(r"^[ivxcdm]+$", s_roman) and 1 <= len(s_roman) <= 8:
            return True
        return False

    def is_likely_header_footer(self, line: str, book_title: Optional[str] = None, author: Optional[str] = None) -> bool:
        """Determines if a line is a running header or footer that shouldn't appear in body text."""
        s = line.strip()
        if not s or len(s) > 100:
            return False

        if self.is_likely_page_number(s):
            return True

        # Publisher forma signatures at bottom of print sheets (e.g. "Sançez'in Çocukları 81/6", "saoçezio ocokları 225/15", "sançezln çocuklan 389/24", "17/2")
        if re.search(r"\b\d{1,4}\s*[\/\\]\s*\d{1,3}\b", s) and len(s) < 55:
            return True

        # Footer lines like author signature or author + roman numeral at page bottom e.g. 'Oscar Lewis vuı ·'
        if author:
            auth_lower = turkish_lower(author).strip()
            s_lower_raw = turkish_lower(s).strip()
            if auth_lower and auth_lower in s_lower_raw and len(s_lower_raw) <= len(auth_lower) + 12:
                # If followed by roman numeral or dot
                rem = s_lower_raw.replace(auth_lower, "").strip()
                if not rem or self.is_likely_page_number(rem):
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

        return False

    def is_likely_garbage_line(self, line: str) -> bool:
        """
        Detects OCR noise lines typically caused by illustrations, diagrams, publisher imprint noise,
        or decorative graphics (e.g. '!A\x06\x07i vıc: ni:: eyayınlarıiB.....tb', 'QR\\S. ,.;- \"\" -.:3\'').
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

        # Printer metadata / scan batch separation marks e.g. "s20 ' xxxı = 552"
        if re.search(r"\bxxx[ivxlcdmı1u]*\s*=", s, re.IGNORECASE) or re.match(r"^s?\d+\s*['\"]\s*[ivxlcdmı1u\s=]+\d+$", s, re.IGNORECASE):
            return True

        # Standalone single letters on their own line (e.g. stray 'k', 'l', 'v')
        if len(s) == 1 and not s.isdigit():
            return True

        # Publisher imprint scanned noise lines e.g. '!A\x06\x07i', 'vıc: ni:: eyayınlarıiB'
        if re.match(r"^[\!A-Za-z0-9\s]{0,5}[\x00-\x1f]", s):
            return True

        letters = re.findall(r"[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ]", s)
        total_len = len(s)

        # 1. Pure symbol / punctuation noise without any letters
        if len(letters) == 0:
            return True

        # 2. Extreme symbol ratio (symbols / punctuation far outweighing letters)
        ratio = len(letters) / total_len
        if total_len >= 3 and ratio < 0.40:
            if re.search(r"[\\/_;:,\.]{2,}|[\\/]|--\.\.|:\s*[A-Z]", s) or len(letters) <= 2:
                return True

        # 3. Short nonsense noise snippets (<= 15 chars with <= 2 letters and mixed symbols)
        if total_len <= 15 and len(letters) <= 2 and re.search(r"[-–—_=\\/\.:;,\'\"!§\*~]", s):
            return True

        # 4. Stray OCR consonant codes / words with no vowels
        has_vowel = bool(re.search(r"[aeıioöuüAEIİOÖUÜ]", s))
        if not has_vowel and len(letters) >= 3 and not (s.isupper() and len(letters) <= 4):
            return True

        return False

    def dehyphenate(self, text: str) -> str:
        """
        Reconstructs words broken across line wraps by a hyphen, soft-hyphen (\xad), or middle dot (·/•).
        Example: 'öğren-\n ciler' -> 'öğrenciler', 'baş·\n ladım' -> 'başladım', 'son - raki' -> 'sonraki'
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

        # Match word ending with hyphen, soft-hyphen, or middle dot across newline
        pattern_nl = r"([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s*[-–—\xad·•]\s*\n\s*([a-zçğıöşüA-ZÇĞİÖŞÜ]+)"
        text = re.sub(pattern_nl, merge_hyphen, text)

        # Match word ending with hyphen, soft-hyphen, or middle dot across any whitespace
        pattern_ws = r"([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s*[-–—\xad·•]\s+([a-zçğıöşüA-ZÇĞİÖŞÜ]+)"
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
                # Clean any ornament dashes inside or around heading
                clean_heading = re.sub(r"[-–—_]{2,}", " ", stripped)
                clean_heading = re.sub(r"\s+", " ", clean_heading).strip()
                if not clean_heading:
                    continue

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
            # Strip trailing stray roman numerals or page numbers
            p = re.sub(r",\s*[ivxlcdmı1u]{1,6}\s*[·•\.]*$", ".", p, flags=re.IGNORECASE)
            # Ensure paragraph does not end with a trailing comma
            p = re.sub(r",\s*$", ".", p)
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

    def extract_page_footnotes(self, raw_text: str) -> Tuple[str, List[str]]:
        """
        Detects footnotes located at the bottom of a page, strips them from the body text lines,
        cleans them linguistically, and returns (body_text_without_footnotes, cleaned_footnotes).
        This prevents bottom-of-page footnotes from breaking hyphenated words or disrupting cross-page paragraphs.
        """
        if not raw_text:
            return "", []

        lines = raw_text.split("\n")
        footnote_pattern = re.compile(
            r"^(?:[\(\<\[][\s•\*~·\d\w\?O]{1,5}[\)\>\]]|,?\s*\.{2,}\s*>)\s*(?:[A-Za-zçğıöşüA-ZÇĞİÖŞÜ\s']{1,25}:|[A-Za-zçğıöşüA-ZÇĞİÖŞÜ]{2,})|"
            r"^(?:Vecindad|Pulqueria|Pulque|Taco|Talı|Compadre|Compadrazgo|Avocado|Tortilla|Chinito|Chino|Novia|Novio|Caramba|Madre|Hombre|Tequila|Baro|Mañanitas)\s*:",
            re.IGNORECASE
        )

        footnote_start_idx = -1
        # In books, footnotes appear near the bottom (among the last 14 lines)
        start_search = max(0, len(lines) - 14)
        for idx in range(start_search, len(lines)):
            l_str = lines[idx].strip()
            if not l_str:
                continue
            if footnote_pattern.match(l_str):
                footnote_start_idx = idx
                break

        if footnote_start_idx == -1:
            return raw_text, []

        body_lines = lines[:footnote_start_idx]
        fn_lines_raw = lines[footnote_start_idx:]

        clean_fn = []
        current_fn = []

        for l in fn_lines_raw:
            s = l.strip()
            if not s:
                continue
            if self.is_likely_page_number(s):
                continue
            if footnote_pattern.match(s):
                if current_fn:
                    clean_fn.append(" ".join(current_fn))
                    current_fn = []
                # Clean leading brackets/bullet symbols: e.g. '( • ) ', '< • > '
                s_clean = re.sub(r"^(?:[\(\<\[][\s•\*~·\d\w\?O]{1,5}[\)\>\]]|,?\s*\.{2,}\s*>)\s*", "", s)
                current_fn.append(s_clean)
            else:
                current_fn.append(s)

        if current_fn:
            clean_fn.append(" ".join(current_fn))

        # Apply unicode normalization and OCR cleanups on footnotes
        processed_fn = []
        for fn in clean_fn:
            fn_clean = self.normalize_unicode(fn)
            fn_clean = self.clean_ocr_errors(fn_clean)
            fn_clean = self.heal_split_words(fn_clean)
            fn_clean = re.sub(r"\s+", " ", fn_clean).strip()
            if fn_clean:
                processed_fn.append(fn_clean)

        return "\n".join(body_lines), processed_fn

