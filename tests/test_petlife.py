"""Observable bookkeeping and handoff behavior for the real-pet Skill."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT
sys.path.insert(0,str(SKILL/'scripts'))
import petlife


class PetLifeTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((SKILL/'assets/household.example.json').read_text(encoding='utf-8'))

    def report(self,data=None,**kwargs):
        return petlife.analyze(data or self.data,'2026-10-03',**kwargs)

    def test_shared_stock_and_receipt_deduplication(self):
        r=self.report()
        self.assertEqual(r['recorded_spending'],Decimal('209'))
        self.assertEqual(r['duplicates_ignored'],['R2-1'])
        dry,wet=r['supplies']
        self.assertEqual(dry['book_stock'],Decimal('2310'))
        self.assertEqual(dry['daily_total'],Decimal('90'))
        self.assertEqual(wet['days_covered'],Decimal('7'))
        self.assertEqual(r['priced_daily_subtotal'],Decimal('13.22'))

    def test_per_pet_trip_packing_is_separate(self):
        r=self.report(trip_days=3)
        self.assertEqual([p['trip_quantity'] for p in r['daily_plan']],
                         list(map(Decimal,['150','127.5','120','127.5'])))

    def test_unconfirmed_and_future_records_are_excluded(self):
        r=self.report()
        self.assertEqual(r['unconfirmed_excluded'],['R4-1'])
        self.assertEqual(r['future_excluded'],['R5-1'])
        self.assertFalse(r['spending_complete'])

    def test_calorie_unit_conversion_uses_label(self):
        dry,wet=self.report()['supplies']
        self.assertAlmostEqual(dry['cost_per_100kcal'],Decimal('1.526315789473684210526315789'))
        self.assertEqual(wet['cost_per_100kcal'],Decimal('10'))

    def test_conflicting_duplicate_stops_reconciliation(self):
        self.data['records'][2]['paid']=50
        with self.assertRaises(ValueError):self.report()

    def test_no_mass_volume_or_unsized_pack_guess(self):
        p=self.data['products'][0]
        for unit in ['ml','cup']:
            with self.subTest(unit=unit),self.assertRaises(ValueError):petlife.units(10,unit,p)
        del p['pack_size']
        with self.assertRaises(ValueError):petlife.units(1,'pack',p)

    def test_same_day_snapshot_already_includes_purchase(self):
        self.data['inventory'][0]['as_of']='2026-10-02'
        self.assertEqual(self.report()['supplies'][0]['book_stock'],Decimal('500'))

    def test_missing_stock_or_rate_stays_unknown(self):
        self.data['inventory']=[]
        self.assertTrue(all(s['days_covered'] is None for s in self.report()['supplies']))
        self.data['daily_plan']=[]
        self.assertTrue(all(s['days_covered'] is None for s in self.report()['supplies']))

    def test_negative_stock_is_visible_without_forecast(self):
        self.data['records'].append({'id':'use-more','kind':'use','date':'2026-10-03',
              'product_id':'dry','quantity':5000,'unit':'g','source':'test fixture'})
        s=self.report()['supplies'][0]
        self.assertLess(s['book_stock'],0)
        self.assertIsNone(s['days_covered'])

    def test_missing_price_is_unknown_not_free(self):
        del self.data['records'][0]['paid']
        r=self.report()
        self.assertFalse(r['daily_cost_complete'])
        self.assertIsNone(r['daily_plan'][0]['daily_cost'])
        self.assertEqual(r['recorded_spending'],Decimal('93'))

    def test_mixed_currency_and_ambiguous_plan_rejected(self):
        d=deepcopy(self.data);d['records'][0]['currency']='USD'
        with self.assertRaises(ValueError):self.report(d)
        self.data['daily_plan'].append(deepcopy(self.data['daily_plan'][0]))
        with self.assertRaises(ValueError):self.report()

    def test_nonfinite_bool_negative_are_not_amounts(self):
        for value in [True,None,'NaN','Infinity','-1','2kg']:
            with self.subTest(value=value),self.assertRaises(ValueError):petlife.number(value)

    def test_handoff_missing_contacts_remains_draft(self):
        r=self.report(trip_days=3)
        self.assertEqual(r['handoff_status'],'draft')
        self.assertIn('emergency_plan',r['handoff_gaps'])
        brief,card=petlife.documents(r)
        self.assertIn('草稿',card)
        self.assertIn('150.00 g',card)
        self.assertIn('账面',brief)

    def test_spending_window_does_not_erase_earlier_price(self):
        r=self.report(start='2026-10-03')
        self.assertEqual(r['recorded_spending'],Decimal('45'))
        self.assertEqual(r['priced_daily_subtotal'],Decimal('13.22'))

    def test_cli_outputs_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'household.json'
            source.write_text(json.dumps(self.data),encoding='utf-8')
            before=source.read_bytes()
            cmd=[sys.executable,str(SKILL/'scripts/petlife.py'),'build','--input',str(source),
                 '--as-of','2026-10-03','--trip-days','3','--out',str(root/'out')]
            result=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=20)
            self.assertEqual(json.loads(result.stdout)['duplicates_ignored'],1)
            self.assertEqual(source.read_bytes(),before)
            report=json.loads((root/'out/report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['recorded_spending'],'209')
            self.assertEqual({p.name for p in (root/'out').iterdir()},{'brief.md','care-card.md','report.json'})


if __name__=='__main__':unittest.main()
