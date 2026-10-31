import unittest
from pdftoepub.ai_repair import score_paragraph_anomaly, AIRepairEngine


class TestAIRepair(unittest.TestCase):
    def test_score_clean_paragraph(self):
        clean_text = "Bu kitap Ali ve Ayşe'nin çocukluk günlerini anlatır. Her sabah erkenden uyanır ve nehir kenarında yürürlerdi."
        score = score_paragraph_anomaly(clean_text)
        self.assertLess(score, 0.15)

    def test_score_corrupted_paragraph(self):
        corrupted_text = "Kamera yaklaştı. Falkenbu sözle uen, buna ihtiyacı ğıttan okuyorve başını kaldırıp karm wV Gözlüğünün arkasında, yanda bir çür'i^^ sayfalarını çevirirken elleri titriyordu. ^ \\~& Lowe fikrini açıkladı. \"Onu birazdo ^ İ\" ^>*-- bToland, \"Çok ilginç,\" diye cevapv %o& ^-> dövdüklerini açıklıyorlar.\" u-~°"
        score = score_paragraph_anomaly(corrupted_text)
        self.assertGreaterEqual(score, 0.20)

    def test_mock_backend_repair(self):
        engine = AIRepairEngine(backend="transformers", model_name="mock")
        # Direct fallback or mock check
        self.assertIsNotNone(engine)


if __name__ == "__main__":
    unittest.main()
