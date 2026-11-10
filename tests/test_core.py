import unittest
from xuanheng.games import validate_record
from xuanheng.analysis import build_candidate

class CoreTests(unittest.TestCase):
    def test_pl3_validation(self):
        r = validate_record("pl3", {"issue":"1","d1":"0","d2":"2","d3":"7"})
        self.assertEqual(r["d1"], "00")
    def test_dlt_validation(self):
        r = validate_record("dlt", {"issue":"1","front":"01 05 12 23 34","back":"02 11"})
        self.assertEqual(r["front"], "01 05 12 23 34")
    def test_candidate_frequency_ranking_full_range(self):
        rows = [{"issue":str(i),"d1":"07","d2":"04","d3":"09"} for i in range(30,15,-1)]
        rows += [{"issue":str(i),"d1":"01","d2":"02","d3":"03"} for i in range(15,10,-1)]
        c = build_candidate("pl3", rows, 20)
        self.assertEqual(c["fields"]["d1"], "07")
        self.assertEqual(c["fields"]["d2"], "04")
        self.assertEqual(c["fields"]["d3"], "09")

if __name__ == "__main__":
    unittest.main()
