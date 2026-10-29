#!/usr/bin/env python3
"""PetLife repeatable care workflows. Local files and Python standard library only."""
from __future__ import annotations

import argparse
import copy
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from petlife import analyze, day, fmt, ident, indexed, md, number, text, units


MAX_BYTES = 5_000_000
APPENDABLE = {'records', 'observations', 'completions'}


def load(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('Record file exceeds 5 MB')
    data = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('Input must be a JSON object')
    return data, hashlib.sha256(raw).hexdigest()


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False) + '\n'


def unique(rows, kind):
    if not isinstance(rows, list):
        raise ValueError(f'{kind} must be a list')
    result, seen = [], {}
    for row in rows:
        key = ident(row['id'])
        if key in seen:
            if row != seen[key]:
                raise ValueError(f'Conflicting {kind} ID {key}; reconcile explicitly')
            continue
        text(row['source'])
        seen[key] = row
        result.append(row)
    return result


def period(as_of, days):
    end = day(as_of)
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 90:
        raise ValueError('days must be an integer from 1 to 90')
    return end, [end + timedelta(days=n) for n in range(1, days + 1)]


def batch_report(data, as_of, days=7):
    end, dates = period(as_of, days)
    core = analyze(data, as_of)
    products = indexed(data.get('products', []), 'product')
    complete = data.get('batch_inventory_complete', False)
    if not isinstance(complete, bool):
        raise ValueError('batch_inventory_complete must be boolean')
    batches = []
    for row in unique(data.get('batches', []), 'batch'):
        p = products[row['product_id']]
        count = day(row['counted_on'])
        q = units(row['remaining'], row['unit'], p, positive=False)
        deadline = min([day(row[k]) for k in ('best_before', 'owner_use_by') if row.get(k)], default=None)
        opened = day(row['opened_on']) if row.get('opened_on') else None
        if opened and opened > count:
            raise ValueError('Opening date must not follow the physical count')
        if not isinstance(row.get('quality_hold', False), bool):
            raise ValueError('quality_hold must be boolean')
        if row.get('owner_use_by'):
            text(row['use_by_source'])
        if row.get('lot_code') is not None:
            text(row['lot_code'])
        reasons = []
        if count != end:
            reasons.append('盘点不是报告当天，先复核余量')
        if row.get('quality_hold'):
            reasons.append('主人标记有质量疑问，暂停纳入计划')
        if deadline and deadline < end:
            reasons.append('所录日期已过，需人工核对')
        if not deadline:
            reasons.append('缺少明确日期，暂不纳入日期约束计划')
        batches.append({'id': row['id'], 'product_id': p['id'], 'product': p['name'],
                        'lot_code': row.get('lot_code'), 'remaining': q, 'unit': p['base_unit'],
                        'counted_on': row['counted_on'], 'opened_on': row.get('opened_on'),
                        'deadline': deadline.isoformat() if deadline else None,
                        'storage_note': row.get('storage_note'), 'source': row['source'],
                        'use_by_source': row.get('use_by_source'),
                        'eligible_for_plan': not reasons, 'review': reasons})
    results = []
    for s in core['supplies']:
        selected = [b for b in batches if b['product_id'] == s['product_id']]
        if not selected:
            continue
        p = products[s['product_id']]
        remaining = {b['id']: b['remaining'] for b in selected if b['eligible_for_plan']}
        ordered = sorted((b for b in selected if b['eligible_for_plan']), key=lambda b: (b['deadline'], b['id']))
        allocations, shortfall = [], Decimal(0)
        first = None
        if s['daily_total'] is not None:
            for date_ in dates:
                need = s['daily_total']
                for b in ordered:
                    if day(b['deadline']) < date_:
                        continue
                    used = min(remaining[b['id']], need)
                    if used:
                        allocations.append({'date': date_.isoformat(), 'batch_id': b['id'], 'quantity': used})
                        remaining[b['id']] -= used
                        need -= used
                    if not need:
                        break
                if need:
                    shortfall += need
                    first = first or date_.isoformat()
        basis_complete = complete and all(b['eligible_for_plan'] for b in selected)
        packs = (shortfall / number(p['pack_size'], positive=True)).to_integral_value(rounding=ROUND_CEILING) if p.get('pack_size') and s['daily_total'] is not None else None
        results.append({'product_id': s['product_id'], 'product': p['name'], 'unit': p['base_unit'],
                        'daily_total': s['daily_total'], 'complete_confirmed_basis': basis_complete,
                        'first_shortfall': first, 'shortfall': shortfall if s['daily_total'] is not None else None,
                        'pack_equivalent': packs, 'pack_label': p.get('pack_label', 'pack'),
                        'allocations': allocations,
                        'remaining_at_end': remaining,
                        'deadline_surplus': [{'batch_id': b['id'], 'quantity': remaining[b['id']], 'deadline': b['deadline']}
                            for b in ordered if day(b['deadline']) <= dates[-1] and remaining[b['id']] > 0]})
    return {'as_of': as_of, 'days': days, 'batches': batches, 'products': results,
            'basis': 'Separate dated physical counts, not added to book inventory. Date-level planning only; no safety, recall, diet-suitability or actual-consumption verification.'}


def task_report(data, as_of, days=3):
    end, dates = period(as_of, days)
    analyze(data, as_of)
    pets = indexed(data.get('pets', []), 'pet')
    tasks = unique(data.get('care_tasks', []), 'task')
    by_id = {}
    for t in tasks:
        if t['pet_id'] not in pets:
            raise ValueError('Unknown pet in care task')
        text(t['title']); text(t['instructions'])
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t['time']):
            raise ValueError('Task time must use HH:MM (00:00 to 23:59)')
        by_id[t['id']] = t
    logs = unique(data.get('completions', []), 'completion')
    grouped = {}
    for c in logs:
        if c['task_id'] not in by_id:
            raise ValueError('Unknown task in completion')
        day(c['date']); text(c['actor'])
        if c['status'] not in {'done', 'skipped', 'needs_help'}:
            raise ValueError('Completion status must be done, skipped or needs_help')
        grouped.setdefault((c['task_id'], c['date']), []).append(c)
    rows = []
    # Include the report day so existing handoff events can be reconciled, then the upcoming days.
    for date_ in [end] + dates:
        for t in sorted(tasks, key=lambda t: (t['time'], t['pet_id'], t['id'])):
            entries = grouped.get((t['id'], date_.isoformat()), [])
            if date_ > end and entries:
                state = 'future_record_needs_review'
            elif len({c['status'] for c in entries}) > 1:
                state = 'conflict'
            elif len(entries) > 1:
                state = 'multiple_reports_review'
            elif entries:
                state = entries[0]['status']
            else:
                state = 'not_recorded' if date_ == end else 'planned'
            rows.append({'date': date_.isoformat(), 'task_id': t['id'], 'pet': pets[t['pet_id']]['name'],
                         'time': t['time'], 'title': t['title'], 'instructions': t['instructions'],
                         'source': t['source'], 'state': state, 'reports': entries})
    return {'as_of': as_of, 'days_ahead': days, 'rows': rows,
            'basis': 'Check-ins are caregiver reports, not sensor proof. No log does not mean not fed. Marking done does not deduct inventory or trigger reminders.'}


def visit_report(data, as_of, start=None):
    end = day(as_of)
    first = day(start) if start else end - timedelta(days=13)
    if first > end:
        raise ValueError('start must not follow as-of')
    core = analyze(data, as_of)
    pets = indexed(data.get('pets', []), 'pet')
    observations = unique(data.get('observations', []), 'observation')
    confirmed, pending, future = [], [], []
    for o in observations:
        if o['pet_id'] not in pets:
            raise ValueError('Unknown pet in observation')
        date_ = day(o['observed_on'])
        text(o['category']); text(o['text'])
        if not isinstance(o.get('confirmed', True), bool):
            raise ValueError('confirmed must be boolean')
        if ('value' in o) != ('unit' in o):
            raise ValueError('Observation value and unit must be supplied together')
        if 'value' in o:
            number(o['value']); text(o['unit'])
        row = dict(o, pet=pets[o['pet_id']]['name'])
        if date_ > end:
            future.append(row)
        elif date_ >= first:
            (pending if o.get('confirmed') is False else confirmed).append(row)
    confirmed.sort(key=lambda o: (o['observed_on'], o['id']))
    therapies = []
    for t in unique(data.get('current_therapies', []), 'therapy'):
        if t['pet_id'] not in pets:
            raise ValueError('Unknown pet in current therapy')
        text(t['text'])
        therapies.append(dict(t, pet=pets[t['pet_id']]['name']))
    return {'as_of': as_of, 'start': first.isoformat(), 'pets': core['pets'],
            'observations': confirmed, 'pending': pending, 'future_excluded': future,
            'current_therapies': therapies, 'daily_plan': core['daily_plan'],
            'handoff': core['handoff'],
            'basis': 'Owner-reported observations only. Gaps do not establish symptom duration or absence. No diagnosis, dose recommendation or health score.'}


def render_stock(r):
    lines = [f'# 先翻哪袋粮？· {r["as_of"]}', '',
             f'按主人现有日用量，规划接下来 {r["days"]} 天。批次盘点独立于购买账本，不能再加一次。', '',
             '| 用品 / 批次 | 实盘余量 | 所录日期上限 | 需核对 | 来源 |', '| --- | ---: | --- | --- | --- |']
    for b in r['batches']:
        lines.append(f'| {md(b["product"])} / {md(b["lot_code"] or b["id"])} | {fmt(b["remaining"])} {b["unit"]} | {b["deadline"] or "未知"} | {md("；".join(b["review"]) or "已纳入计划，仍需检查储存与状态")} | {md(b["source"])} |')
    for p in r['products']:
        lines += ['', f'## {md(p["product"])}', '']
        lines += [f'- 日期与数量口径：'+('主人确认批次完整，且全部为当天盘点并有日期。' if p['complete_confirmed_basis'] else '批次或日期信息不全；缺口仅为已确认部分的规划差额，先核库存再采购。')]
        if p['daily_total'] is None:
            lines.append('- 缺少主人现有日用量，未预测消耗或补货量。')
        else:
            lines.append(f'- 每日合计 {fmt(p["daily_total"])} {p["unit"]}；首个规划缺口：{p["first_shortfall"] or "本窗口未出现"}；累计差额 {fmt(p["shortfall"])} {p["unit"]}。')
            if p['pack_equivalent'] is not None:
                lines.append(f'- 差额折合 {fmt(p["pack_equivalent"],0)} {md(p["pack_label"])}（按包装向上取整；新购产品的日期、适配与实物状态另行核对）。')
            schedule = [f'{x["date"]} 用 {x["batch_id"]} {fmt(x["quantity"])}{p["unit"]}' for x in p['allocations']]
            lines.append('- 同一产品内的先到日期先用顺序：' + (md('；'.join(schedule)) if schedule else '暂无可排批次。'))
            for b in p['deadline_surplus']:
                lines.append(f'- 提醒核对：{md(b["batch_id"])} 在所录日期 {b["deadline"]} 前预计仍余 {fmt(b["quantity"])} {p["unit"]}；不以清库存为由加量或换食。')
    lines += ['', '日期仅来自标签/主人明确提供的日期，不推算“开封后一律N天”。纳入计划不代表食品安全；本工具未查询召回。若标签含小时级要求，需另按原文处理，不用日期表替代。']
    return '\n'.join(lines) + '\n'


STATES = {'done': '照顾者报告完成', 'skipped': '照顾者报告未做', 'needs_help': '需要协助',
          'not_recorded': '未记录，待确认', 'planned': '计划', 'conflict': '报告冲突，待确认',
          'multiple_reports_review': '多次报告，需核对是否重复照顾', 'future_record_needs_review': '未来日期打卡，需核对'}


def render_care(r):
    lines = [f'# 谁照顾过了？· {r["as_of"]}', '',
             '**未记录 ≠ 没喂；打卡 ≠ 已确认吃下。** 当天为日终口径；未来任务只列计划，不替任何人打卡。', '',
             '| 日期 | 时间 | 宠物 / 任务 | 状态 | 报告人 / 来源 |', '| --- | --- | --- | --- | --- |']
    for x in r['rows']:
        sources = '；'.join(c['actor'] + ' / ' + c['source'] for c in x['reports']) or x['source']
        lines.append(f'| {x["date"]} | {x["time"]} | {md(x["pet"])} / {md(x["title"])} | {STATES[x["state"]]} | {md(sources)} |')
    if not r['rows']:
        lines += ['', '尚未录入明确的照顾任务。可先交付基础托管单，再补任务与时间。']
    seen = set()
    lines += ['', '## 主人原有安排', '']
    for x in r['rows']:
        if x['task_id'] not in seen:
            lines.append(f'- {md(x["pet"])} {x["time"]}：{md(x["instructions"])}（{md(x["source"])}）')
            seen.add(x['task_id'])
    lines += ['', '本单不自动提醒、发送消息或扣减库存。出现冲突先联系照顾者核实，不能据此直接再喂一次。']
    return '\n'.join(lines) + '\n'


def render_visit(r):
    lines = [f'# 给兽医看的观察摘要 · {r["start"]} — {r["as_of"]}', '',
             '以下为主人提供的观察记录及来源，不是诊断。没有记录的日期不表示症状不存在，也不据此认定连续持续时长。']
    for p in r['pets']:
        lines += ['', f'## {md(p["name"])}', '', '### 已记录事实', '']
        obs = [o for o in r['observations'] if o['pet_id'] == p['id']]
        for o in obs:
            lines.append(f'- {o["observed_on"]} · {md(o["category"])}：{md(o["text"])}（{md(o["source"])}）')
        if not obs:
            lines.append('- 本窗口没有已确认观察，不作健康结论。')
        for o in r['pending']:
            if o['pet_id'] == p['id']:
                lines.append(f'- **待确认** {o["observed_on"]}：{md(o["text"])}（{md(o["source"])}）；未并入已确认事实。')
        lines += ['', '### 现有照顾与治疗说明', '']
        for x in r['daily_plan']:
            if x['pet_id'] == p['id']:
                lines.append(f'- 现有用量：{md(x["product"])} {fmt(x["display_daily_quantity"])} {md(x["display_unit"])} / 天（{md(x["source"])}）。')
        therapies = [t for t in r['current_therapies'] if t['pet_id'] == p['id']]
        lines.extend('- '+md(t['text'])+'（'+md(t['source'])+'）' for t in therapies)
        if not therapies:
            lines.append('- 当前治疗/补充剂信息未提供；不能写成“未使用”。')
        lines += ['', '### 就诊前可补齐 / 想问医生的事', '',
                  '- 具体开始时间、频次、与平时相比的变化；照片/视频、饮水和排泄情况可按已有资料补充。',
                  '- 如有包装、药物或既往检查，请带原件；由兽医决定需要哪些进一步检查和处置。']
    lines += ['', f'未来日期记录未并入本摘要：{len(r["future_excluded"])} 条。不要因本摘要缺少记录而延误寻求兽医帮助。']
    return '\n'.join(lines) + '\n'


def validate(data, as_of):
    # Validate even future/uncertain purchase rows before persisting, without adopting them as confirmed facts.
    check = copy.deepcopy(data)
    for r in check.get('records', []):
        r['confirmed'] = True
    latest = max([as_of] + [r['date'] for r in check.get('records', [])])
    analyze(check, latest)
    batch_report(data, as_of)
    task_report(data, as_of)
    visit_report(data, as_of)


def merged(data, patch, as_of):
    if not isinstance(patch, dict) or not patch or set(patch) - APPENDABLE:
        raise ValueError('Patch may only append records, observations and completions')
    result = copy.deepcopy(data)
    counts = {}
    for collection, incoming in patch.items():
        existing = unique(result.get(collection, []), collection)
        known = {r['id']: r for r in existing}
        fresh = unique(incoming, collection)
        added = 0
        for row in fresh:
            if row['id'] in known:
                if known[row['id']] != row:
                    raise ValueError(f'Conflicting {collection} ID {row["id"]}; no overwrite allowed')
            else:
                existing.append(row); known[row['id']] = row; added += 1
        result[collection] = existing
        counts[collection] = added
    validate(result, as_of)
    return result, counts


def apply_patch_file(input_path, patch, as_of, expected):
    input_path = Path(input_path)
    lock = input_path.with_name(input_path.name + '.petlife.lock')
    temp = None
    # Only this process's own lock/temp are removed. A busy/stale lock is not silently broken.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        data, current = load(input_path)
        if current != expected:
            raise ValueError('Record changed since inspect; re-read and reconcile before writing')
        result, counts = merged(data, patch, as_of)
        if result == data:
            return {'added': counts, 'sha256': current, 'changed': False}
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=input_path.parent,
                                         prefix='.petlife-', suffix='.tmp', delete=False) as f:
            temp = Path(f.name)
            f.write(dumps(result)); f.flush(); os.fsync(f.fileno())
        if load(input_path)[1] != current:
            raise ValueError('Record changed during merge; no write performed')
        os.replace(temp, input_path); temp = None
        return {'added': counts, 'sha256': load(input_path)[1], 'changed': True}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('stock', 'care', 'visit', 'inspect', 'merge'):
        p = subs.add_parser(name)
        p.add_argument('--input', type=Path, required=True)
        if name != 'inspect':
            p.add_argument('--as-of', required=True)
        if name in ('stock', 'care'):
            p.add_argument('--days', type=int, default=7 if name == 'stock' else 3)
        if name == 'visit':
            p.add_argument('--start')
        if name in ('stock', 'care', 'visit'):
            p.add_argument('--out', type=Path, required=True)
        if name == 'merge':
            p.add_argument('--patch', type=Path, required=True)
            p.add_argument('--expect-sha256')
            group = p.add_mutually_exclusive_group(required=True)
            group.add_argument('--write', action='store_true')
            group.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        data, sha = load(args.input)
        if args.command == 'inspect':
            print(dumps({'sha256': sha, 'counts': {k: len(data.get(k, [])) for k in sorted(APPENDABLE)}}))
            return
        if args.command == 'merge':
            patch, _ = load(args.patch)
            if args.write:
                if not args.expect_sha256 or not re.fullmatch('[a-f0-9]{64}', args.expect_sha256):
                    raise ValueError('--write requires the SHA-256 returned by inspect')
                result = apply_patch_file(args.input, patch, args.as_of, args.expect_sha256)
            else:
                value, counts = merged(data, patch, args.as_of)
                if args.out.resolve() in {args.input.resolve(), args.patch.resolve()}:
                    raise ValueError('Preview may not overwrite input or patch')
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(dumps(value), encoding='utf-8')
                result = {'added': counts, 'preview_only': True, 'input_sha256': sha}
            print(dumps(result)); return
        if args.command == 'stock':
            report = batch_report(data, args.as_of, args.days); rendered = render_stock(report)
        elif args.command == 'care':
            report = task_report(data, args.as_of, args.days); rendered = render_care(report)
        else:
            report = visit_report(data, args.as_of, args.start); rendered = render_visit(report)
        targets = [args.out / (args.command + suffix) for suffix in ('.md', '.json')]
        if args.input.resolve() in {p.resolve() for p in targets}:
            raise ValueError('Output would overwrite the input record')
        args.out.mkdir(parents=True, exist_ok=True)
        targets[0].write_text(rendered, encoding='utf-8')
        targets[1].write_text(dumps(report), encoding='utf-8')
        print(dumps({'files': [p.name for p in targets]}))
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
