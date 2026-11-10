import unittest
from xuanheng.games import validate_record
from xuanheng.analysis import build_candidate, bias_report, chi_square_p

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
    def test_bias_uniform_chi_square(self):
        # 100 期，每位 0-9 各出现 10 次，卡方应为 0，p 值应大于 0.05
        rows = [{"issue":str(100-i),"d1":f"{i%10:02d}","d2":f"{i%10:02d}","d3":f"{i%10:02d}"} for i in range(100)]
        r = bias_report("pl3", rows, 100)
        for pos in r["positions"]:
            self.assertGreater(pos["chi2_p"], 0.05)
    def test_bias_skewed_chi_square(self):
        # 百位 7 占 55%，其余数字各 5%，卡方 p 值应小于 0.05
        rows = []
        for i in range(100):
            d1 = 7 if i < 50 else (i - 50) % 10
            rows.append({"issue":str(100-i),"d1":f"{d1:02d}","d2":"02","d3":"03"})
        r = bias_report("pl3", rows, 100)
        self.assertLess(r["positions"][0]["chi2_p"], 0.05)
        self.assertEqual(r["positions"][0]["conclusion"], "偏离均匀")
    def test_bias_runs_alternating(self):
        # 百位奇偶交替 1,2,1,2……，游程数远超随机期望，游程检验应显著
        rows = [{"issue":str(100-i),"d1":f"{1 if i%2==0 else 2:02d}","d2":"02","d3":"03"} for i in range(100)]
        r = bias_report("pl3", rows, 100)
        self.assertIsNotNone(r["positions"][0]["runs_p"])
        self.assertLess(r["positions"][0]["runs_p"], 0.05)
    def test_chi_square_p_known_values(self):
        # 卡方分布 5% 临界值：3.84（自由度 1）、9.488（自由度 4）
        self.assertAlmostEqual(chi_square_p(3.84, 1), 0.05, delta=0.002)
        self.assertAlmostEqual(chi_square_p(9.488, 4), 0.05, delta=0.002)

if __name__ == "__main__":
    unittest.main()
