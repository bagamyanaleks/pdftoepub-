import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdftoepub.cleaner import TextCleaner


class TestOCRRepairs(unittest.TestCase):
    def setUp(self):
        self.cleaner = TextCleaner()

    def test_target_paragraph_healing(self):
        raw_p = (
            "Şilteyi denk yaptık, üstündeki lekeleri gizlemek için de bir yatak örtüsüne sarıverdi. "
            "Babam ardından bütün eşyaların, tencerelerle tavaların toplanmasını istiyordu. "
            "Elena bunları çengallerinden çıkararak yanında taşıyabilmek için çamaşır teknelerinin içine koydu. "
            "Bu gecekondu mahallelıırinde, hep su darlığı olduğu için evde su biriktirecek bir süTü kap bulunduruyorduk. "
            "Araba tutmadan eşyaları kendimiz taşıdık. "
            "Yeni evimiz bir buçuk blok ötede olduğundan babam giysi dolabını bir hamala\nt<!Şlttl.\n"
            "Daha büyük ve sevimli bir <<Vecindadndı bu ve ilk kez ikl odalı bir evde oturuyorduk. "
            "Bu bende zengin olduğumuz izlenic mini uyandırdı, çok mutluydum. "
            "Evimiz üçüncü kattaydı, avluya bakan yerde de sadece ufak bir demir olduğu için babam aşağı düşmemizi önlemek amacıyla gerçek bir parmaklık taktırdı."
        )
        cleaned = self.cleaner.process_full_text(raw_p)
        paras = cleaned.split("\n\n")

        self.assertEqual(len(paras), 2, "Should reconstruct into two separate paragraphs")
        p1, p2 = paras[0], paras[1]

        self.assertIn("çengellerinden", p1)
        self.assertIn("mahallelerinde", p1)
        self.assertIn("bir sürü kap", p1)
        self.assertTrue(p1.endswith("bir hamala taşıttı."), f"P1 should end with 'bir hamala taşıttı.', got: {p1[-40:]}")

        self.assertTrue(p2.startswith('Daha büyük ve sevimli bir "Vecindad"dı bu'))
        self.assertIn("iki odalı", p2)
        self.assertIn("izlenimini uyandırdı", p2)

    def test_printer_slugline_stripping(self):
        raw = "hafta parasını içkiye yatırır, cumartesi gelince sançezin çocukları 81/6 de saklanacak delik arardı."
        cleaned = self.cleaner.clean_ocr_errors(raw)
        self.assertNotIn("81/6", cleaned)
        self.assertIn("cumartesi gelince de saklanacak delik arardı", cleaned)

        raw2 = "Kız olumlu saoçez'iD Çocukları 273/18 karşıladı bu sözlerimi."
        cleaned2 = self.cleaner.clean_ocr_errors(raw2)
        self.assertNotIn("273/18", cleaned2)
        self.assertIn("Kız olumlu karşıladı bu sözlerimi", cleaned2)

    def test_internal_caps_and_circumflex(self):
        raw = "batJm eve gelince tJaha da öte bütDn kötülDkleri duyJum dükkAnından silAh imkAnlı rüzgAr"
        cleaned = self.cleaner.clean_ocr_errors(raw)
        self.assertIn("babam eve gelince", cleaned)
        self.assertIn("daha da öte", cleaned)
        self.assertIn("bütün", cleaned)
        self.assertIn("kötülükleri", cleaned)
        self.assertIn("duydum", cleaned)
        self.assertIn("dükkânından", cleaned)
        self.assertIn("silâh", cleaned)
        self.assertIn("imkânlı", cleaned)
        self.assertIn("rüzgâr", cleaned)

    def test_broken_symbols(self):
        raw = "arı<adaşlarım dış<ırı kova!ardı o!du iç!erinde çal!ıuk şek!iıde"
        cleaned = self.cleaner.clean_ocr_errors(raw)
        self.assertIn("arkadaşlarım", cleaned)
        self.assertIn("dışarı", cleaned)
        self.assertIn("kovalardı", cleaned)
        self.assertIn("oldu", cleaned)
        self.assertIn("içlerinde", cleaned)
        self.assertIn("çabuk", cleaned)
        self.assertIn("şekilde", cleaned)

    def test_merged_sentence_boundary(self):
        raw = "boşaltıyordukUzun bir yolculuktan sonra yatabilirdiŞilteyi satmıştım"
        cleaned = self.cleaner.clean_ocr_errors(raw)
        self.assertIn("boşaltıyorduk. Uzun", cleaned)
        self.assertIn("yatabilirdi. Şilteyi", cleaned)

    def test_manuel_section_corruptions(self):
        sample = (
            'Böylece evlilik hayatımız başladı. Kira ödemiyorduk, yine de karıma yiyecek için günde beş peao veriyordum. '
            'Teyzem çok iyi bir insandı ama hep yoksuldu, hatta anamla HaHamtlan blle yoksul. '
            'Çamaşır yıkıyor, lokantada yamaklık ediyordu, eniştem de gazete satıyordu ama yine de aralarında topladıkları parayla ancak günde bir öğün yemek yiyebiliyorlardı\n'
            '"iyi, demek istediğföe eriştin sonunda hai\'"\n'
            'Babam kapıyı açtığı zaman benonu arkasından itefıyordum.\n\n'
            '"l: çari giin, dedi. YCizü" bir yargıcınki gibiydi, kendimi jürinin karşısında hissettim. \n'
            'O: hıasanm bir yanına, biz karşısıha oturduk. "fllç kurusu, demek evleınttin ha?>)\n\n'
            'Görsel\n'
            '"Şey, evet baba."\n'
            'Dayım hep karısının kendisine büyü yaptığından yakınıyordu, üstündeki kötülükleri kovmak için de o sıralardabir dM\'andero\'Ya gidiyordu. '
            '"Bu cabrona, i" dedi. "Beni yaaladı ve bırakmıyor, ihtiyar cadı. Ne zaman eve gitsem hep işi gücO otlar ve boktan büyücülük işleri. '
            'Beni de büyüledi. Bundan nasıl kurtulacağımı bilemiyorum." Dayım karısının kendisine bUyO yaptığını söylediği halde kadıncağızın vücudu ve gôzleri hep yedlği dayaklardan çürük içindeydi.\n'
            '"Evet efendim, hazırım." ce\\l.abını verdim. Bütün eşyam, içinde giysilerimin durduğu ufak bir kutuydu. Daha önce hiç bir yeri görmediğim için Mexico City\'ye gitmeyi çok istiyordum.\n'
            'Genellikle de bir cmachete" c·> ve bir halat alır, kuru odun toplamaya giderdim.'
        )
        cleaned = self.cleaner.process_full_text(sample)

        self.assertIn("beş peso", cleaned)
        self.assertIn("babamdan bile", cleaned)
        self.assertIn('"İyi, demek istediğine eriştin sonunda ha!"', cleaned)
        self.assertIn("ben onu arkasından itiyordum.", cleaned)
        self.assertIn('"İçeri girin," dedi.', cleaned)
        self.assertIn("Yüzü bir yargıcınki gibiydi", cleaned)
        self.assertIn("O masanın bir yanına, biz karşısına oturduk.", cleaned)
        self.assertIn('"Piç kurusu, demek evlendin ha?"', cleaned)
        self.assertNotIn("Görsel", cleaned)
        self.assertIn('"Şey, evet baba."', cleaned)
        self.assertIn("o sıralarda bir curandero'ya gidiyordu", cleaned)
        self.assertIn('"Bu cabrona," dedi.', cleaned)
        self.assertIn('"Beni yakaladı ve bırakmıyor, ihtiyar cadı.', cleaned)
        self.assertIn("işi gücü otlar", cleaned)
        self.assertIn("büyü yaptığını söylediği", cleaned)
        self.assertIn("gözleri hep yediği dayaklardan", cleaned)
        self.assertIn('"Evet efendim, hazırım," cevabını verdim.', cleaned)
        self.assertIn('"machete" (*)', cleaned)

    def test_ethiopic_unicode_font_healing(self):
        raw = "Bunun nedeni de\u1301di, di\u1305lerine ula\u12fb\u12e5\u12e3, ya\u1306alad\u12e3, \xe7\u1304nkü gi\u1302in\u1303 dedi."
        cleaned = self.cleaner.normalize_unicode(raw)
        self.assertIn("değildi", cleaned)
        self.assertIn("dizlerine", cleaned)
        self.assertIn("ulaştı", cleaned)
        self.assertIn("yakaladı", cleaned)
        self.assertIn("çünkü", cleaned)
        self.assertIn('girin,"', cleaned)


if __name__ == "__main__":
    unittest.main()

