import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from carekit import (apply_patch_file, batch_report, dumps, load, merged, render_care,
                     render_stock, render_visit, task_report, visit_report)
from petlife import analyze


class CareKitTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'assets/everyday.example.json').read_text(encoding='utf-8'))
        self.patch = json.loads((ROOT / 'assets/receipt-patch.example.json').read_text(encoding='utf-8'))

    def test_batch_dates_reveal_gap_hidden_by_book_coverage(self):
        core = analyze(self.data, '2026-10-03')
        self.assertEqual(next(x for x in core['supplies'] if x['product_id']=='wet')['days_covered'], 7)
        report = batch_report(self.data, '2026-10-03', 7)
        wet = next(x for x in report['products'] if x['product_id']=='wet')
        self.assertEqual(wet['first_shortfall'], '2026-10-10')
        self.assertEqual(wet['shortfall'], 85)
        self.assertEqual(wet['pack_equivalent'], 1)
        self.assertEqual(wet['deadline_surplus'][0]['quantity'], 85)
        self.assertTrue(wet['complete_confirmed_basis'])
        self.assertEqual([x['batch_id'] for x in wet['allocations']][:2], ['wet-near','wet-backup'])

    def test_opening_does_not_invent_shelf_life(self):
        b = self.data['batches'][0]
        del b['owner_use_by']; del b['use_by_source']
        b['best_before'] = '2026-11-01'
        report = batch_report(self.data, '2026-10-03')
        self.assertEqual(report['batches'][0]['deadline'], '2026-11-01')

    def test_unknown_dates_and_quality_holds_are_not_scheduled(self):
        del self.data['batches'][0]['best_before']; del self.data['batches'][0]['owner_use_by']
        self.data['batches'][1]['quality_hold'] = True
        r = batch_report(self.data, '2026-10-03')
        self.assertFalse(r['batches'][0]['eligible_for_plan'])
        self.assertFalse(r['batches'][1]['eligible_for_plan'])
        self.assertFalse(r['products'][0]['complete_confirmed_basis'])
        self.assertEqual(r['products'][0]['allocations'], [])

    def test_stale_or_incomplete_counts_do_not_imply_firm_purchase(self):
        self.data['batch_inventory_complete'] = False
        self.data['batches'][0]['counted_on'] = '2026-10-02'
        r = batch_report(self.data, '2026-10-03')
        self.assertFalse(r['batches'][0]['eligible_for_plan'])
        self.assertTrue(all(not p['complete_confirmed_basis'] for p in r['products']))

    def test_no_daily_amount_no_restock_prediction(self):
        self.data['daily_plan'] = []
        r = batch_report(self.data, '2026-10-03')
        self.assertTrue(all(p['shortfall'] is None and p['pack_equivalent'] is None for p in r['products']))

    def test_duplicate_batch_id_cannot_double_stock(self):
        a = batch_report(self.data, '2026-10-03')
        self.data['batches'].append(copy.deepcopy(self.data['batches'][0]))
        self.assertEqual(a, batch_report(self.data, '2026-10-03'))
        self.data['batches'][-1]['remaining'] = 999
        with self.assertRaises(ValueError): batch_report(self.data, '2026-10-03')

    def test_bad_dates_and_mixed_units_rejected(self):
        self.data['batches'][0]['opened_on'] = '2026-10-04'
        with self.assertRaises(ValueError): batch_report(self.data, '2026-10-03')
        self.data['batches'][0]['opened_on'] = '2026-10-01'
        self.data['batches'][0]['unit'] = 'ml'
        with self.assertRaises(ValueError): batch_report(self.data, '2026-10-03')

    def test_care_conflict_and_absent_logs_are_distinct(self):
        r = task_report(self.data, '2026-10-03', 3)
        today = {x['task_id']: x for x in r['rows'] if x['date']=='2026-10-03'}
        self.assertEqual(today['mochi-am']['state'], 'done')
        self.assertEqual(today['mochi-pm']['state'], 'conflict')
        self.assertEqual(today['bao-pm']['state'], 'not_recorded')
        self.assertTrue(all(x['state']=='planned' for x in r['rows'] if x['date']>'2026-10-03'))
        self.assertEqual(len(r['rows']), 16)

    def test_two_caregiver_reports_do_not_collapse_to_one_done(self):
        c = copy.deepcopy(self.data['completions'][0]); c.update(id='C5',actor='照顾者B')
        self.data['completions'].append(c)
        row = next(x for x in task_report(self.data,'2026-10-03')['rows'] if x['task_id']=='mochi-am' and x['date']=='2026-10-03')
        self.assertEqual(row['state'], 'multiple_reports_review')

    def test_replayed_completion_is_deduped_and_does_not_change_inventory(self):
        before = analyze(self.data, '2026-10-03')
        base = task_report(self.data, '2026-10-03')
        self.data['completions'].append(copy.deepcopy(self.data['completions'][0]))
        self.assertEqual(base, task_report(self.data,'2026-10-03'))
        self.assertEqual(before, analyze(self.data,'2026-10-03'))

    def test_future_checkin_cannot_be_a_completed_task(self):
        self.data['completions'][0]['date']='2026-10-04'
        r=task_report(self.data,'2026-10-03')
        row=next(x for x in r['rows'] if x['task_id']=='mochi-am' and x['date']=='2026-10-04')
        self.assertEqual(row['state'],'future_record_needs_review')

    def test_dog_walk_and_help_request_stay_literal(self):
        data=json.loads((ROOT/'assets/dog-walk.example.json').read_text(encoding='utf-8'))
        r=task_report(data,'2026-10-03',2)
        today=[x for x in r['rows'] if x['date']=='2026-10-03']
        self.assertEqual([x['state'] for x in today],['done','needs_help'])
        self.assertEqual(len(r['rows']),6)
        self.assertEqual(today[0]['instructions'],data['care_tasks'][0]['instructions'])
        self.assertTrue(all(x['pet']=='豆豆' for x in r['rows']))

    def test_invalid_time_and_unknown_pet_rejected(self):
        self.data['care_tasks'][0]['time']='24:00'
        with self.assertRaises(ValueError): task_report(self.data,'2026-10-03')
        self.data['care_tasks'][0]['time']='08:00'
        self.data['care_tasks'][0]['pet_id']='unknown'
        with self.assertRaises(ValueError): task_report(self.data,'2026-10-03')

    def test_visit_facts_pending_future_and_missing_day_kept_separate(self):
        future=copy.deepcopy(self.data['observations'][0]); future.update(id='V5',observed_on='2026-10-04')
        self.data['observations'].append(future)
        r=visit_report(self.data,'2026-10-03','2026-10-01')
        self.assertEqual(len(r['observations']),3)
        self.assertEqual(len(r['pending']),1)
        self.assertEqual(len(r['future_excluded']),1)
        self.assertNotIn('2026-10-02',{x['observed_on'] for x in r['observations']})
        self.assertEqual(r['current_therapies'],[])

    def test_observation_conflicting_ids_or_partial_measurement_rejected(self):
        bad=copy.deepcopy(self.data['observations'][0]); bad['text']='different'
        self.data['observations'].append(bad)
        with self.assertRaises(ValueError): visit_report(self.data,'2026-10-03')
        self.data['observations'].pop(); del self.data['observations'][2]['unit']
        with self.assertRaises(ValueError): visit_report(self.data,'2026-10-03')

    def test_receipt_merge_idempotent_across_replays(self):
        first, counts=merged(self.data,self.patch,'2026-10-03')
        second, replay=merged(first,self.patch,'2026-10-03')
        self.assertEqual(counts,{'records':1}); self.assertEqual(replay,{'records':0})
        self.assertEqual(first,second)
        self.assertEqual(analyze(first,'2026-10-03')['recorded_spending'],221)
        self.assertEqual(analyze(self.data,'2026-10-03')['recorded_spending'],209)

    def test_merge_rejects_conflicts_and_profile_overwrites(self):
        p={'records':[dict(self.data['records'][0],paid=999)]}
        with self.assertRaises(ValueError): merged(self.data,p,'2026-10-03')
        with self.assertRaises(ValueError): merged(self.data,{'pets':[]},'2026-10-03')

    def test_invalid_future_record_is_not_persisted(self):
        p={'records':[{'id':'BAD','kind':'expense','date':'2030-01-01','paid':-1,'category':'x','source':'S'}]}
        with self.assertRaises(ValueError): merged(self.data,p,'2026-10-03')

    def test_stale_and_conflicting_writes_leave_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'household.json'; path.write_text(dumps(self.data),encoding='utf-8')
            original=path.read_bytes()
            with self.assertRaises(ValueError): apply_patch_file(path,self.patch,'2026-10-03','0'*64)
            self.assertEqual(path.read_bytes(),original)
            bad={'records':[dict(self.data['records'][0],paid=999)]}
            with self.assertRaises(ValueError): apply_patch_file(path,bad,'2026-10-03',load(path)[1])
            self.assertEqual(path.read_bytes(),original)
            self.assertFalse(path.with_name(path.name+'.petlife.lock').exists())

    def test_busy_lock_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'h.json'; path.write_text(dumps(self.data),encoding='utf-8')
            lock=path.with_name(path.name+'.petlife.lock'); lock.write_text('another writer')
            with self.assertRaises(FileExistsError): apply_patch_file(path,self.patch,'2026-10-03',load(path)[1])
            self.assertEqual(lock.read_text(),'another writer')

    def test_successful_write_and_replay_preserve_hash(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'h.json'; path.write_text(dumps(self.data),encoding='utf-8')
            first=apply_patch_file(path,self.patch,'2026-10-03',load(path)[1])
            second=apply_patch_file(path,self.patch,'2026-10-03',first['sha256'])
            self.assertTrue(first['changed']); self.assertFalse(second['changed'])
            self.assertEqual(first['sha256'],second['sha256'])
            self.assertEqual(second['added']['records'],0)

    def test_markdown_escapes_user_cells(self):
        self.data['pets'][0]['name']='Cat | <img src=x>'
        self.data['batches'][0]['lot_code']='LOT|<b>'
        for value in [render_care(task_report(self.data,'2026-10-03')),
                      render_stock(batch_report(self.data,'2026-10-03')),
                      render_visit(visit_report(self.data,'2026-10-03'))]:
            self.assertNotIn('<img',value)
            self.assertNotIn('<b>',value)

    def test_cli_real_output_and_write_guard(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out'
            for command in ('stock','care','visit'):
                r=subprocess.run([sys.executable,str(ROOT/'scripts/carekit.py'),command,'--input',str(ROOT/'assets/everyday.example.json'),'--as-of','2026-10-03','--out',str(out)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'))
                self.assertTrue((out/(command+'.json')).is_file())
            r=subprocess.run([sys.executable,str(ROOT/'scripts/carekit.py'),'merge','--input',str(ROOT/'assets/everyday.example.json'),'--patch',str(ROOT/'assets/receipt-patch.example.json'),'--as-of','2026-10-03','--write'],capture_output=True)
            self.assertNotEqual(r.returncode,0)


if __name__=='__main__': unittest.main()
