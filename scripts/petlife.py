#!/usr/bin/env python3
"""Real-pet bookkeeping and sitter handoffs. Standard library only; no network."""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import html
import json
from pathlib import Path
import re


def number(value, *, positive=False):
    if isinstance(value, bool) or value is None:
        raise ValueError('Expected an explicit numeric amount')
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Invalid numeric amount') from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError('Amount must be finite and non-negative (positive for quantities)')
    return result


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', value):
        raise ValueError('Use stable alphanumeric IDs (letters, digits, _, . or -)')
    return value


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing required text or source')
    return value


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError('Dates must use YYYY-MM-DD')
    return date.fromisoformat(value)


def units(value, unit, product, *, positive=True):
    amount = number(value, positive=positive)
    base = product['base_unit']
    if unit == base:
        return amount
    if (unit, base) in {('kg','g'),('l','ml')}:
        return amount * 1000
    if unit == 'pack' and product.get('pack_size') is not None:
        return amount * number(product['pack_size'], positive=True)
    raise ValueError(f'Unknown or incompatible unit {unit!r} for product {product["id"]}')


def indexed(rows, kind):
    result = {}
    for row in rows:
        key = ident(row['id'])
        if key in result:
            raise ValueError(f'Duplicate {kind} ID: {key}')
        text(row['name'])
        result[key] = row
    return result


def unique_records(rows):
    result, seen, duplicates = [], {}, []
    for row in rows:
        key = ident(row['id'])
        if key in seen:
            if row != seen[key]:
                raise ValueError(f'Conflicting contents for record ID {key}; reconcile first')
            duplicates.append(key)
            continue
        seen[key] = row
        day(row['date']); text(row['source'])
        if 'confirmed' in row and not isinstance(row['confirmed'], bool):
            raise ValueError('confirmed must be a boolean')
        result.append(row)
    # Same-day records retain their input order; ambiguous physical counts belong in snapshots.
    return sorted(result,key=lambda r:r['date']), duplicates


def analyze(data, as_of, *, start=None, trip_days=1):
    end = day(as_of)
    start_date = day(start) if start else end.replace(day=1)
    if start_date > end:
        raise ValueError('Spending start must not follow as-of date')
    if isinstance(trip_days,bool) or not isinstance(trip_days,int) or not 1 <= trip_days <= 365:
        raise ValueError('trip-days must be an integer from 1 to 365')
    currency = data['currency']
    if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):
        raise ValueError('An explicit three-letter household currency is required')
    pets = indexed(data.get('pets',[]),'pet')
    products = indexed(data.get('products',[]),'product')
    for pet in pets.values():
        if pet.get('species') not in {'cat','dog'}:
            raise ValueError('This record format currently supports cats and dogs')
        if not isinstance(pet.get('routine',[]),list) or any(not isinstance(x,str) for x in pet.get('routine',[])):
            raise ValueError('Pet routine must be a list of owner-supplied strings')
    calories = {}
    for pid,p in products.items():
        if p.get('base_unit') not in {'g','ml','piece'}:
            raise ValueError('Product base unit must be g, ml or piece')
        if p.get('pack_size') is not None:
            number(p['pack_size'],positive=True)
        c=p.get('calories')
        calories[pid]=None
        if c:
            text(c['source'])
            calories[pid]=number(c['kcal'],positive=True)/units(c['per_quantity'],c['unit'],p)
    records,duplicates = unique_records(data.get('records',[]))
    warnings,unconfirmed,future = [],[],[]
    valid=[]
    for r in records:
        if day(r['date'])>end:
            future.append(r['id']); continue
        if r.get('confirmed') is False:
            unconfirmed.append(r['id']); continue
        if r.get('currency',currency)!=currency:
            raise ValueError('Mixed currencies require separate records and reports')
        if r['kind'] in {'purchase','use'}:
            p=products[r['product_id']]
            units(r['quantity'],r['unit'],p)
            if r.get('pet_id') is not None and r['pet_id'] not in pets:
                raise ValueError('Unknown pet on a usage record')
            if r.get('paid') is not None:number(r['paid'])
        elif r['kind']=='expense':
            number(r['paid']);text(r['category'])
        elif r['kind']=='note':
            if r['pet_id'] not in pets:raise ValueError('Unknown pet on a note')
            text(r['text'])
        else:
            raise ValueError('Record kind must be purchase, use, expense or note')
        valid.append(r)
    stock,stock_sources,snapshot_dates = {},{},{}
    snapshot_seen=set()
    for row in data.get('inventory',[]):
        pid=row['product_id'];p=products[pid]
        if pid in snapshot_seen:raise ValueError('Keep one explicit stock snapshot per product')
        snapshot_seen.add(pid);text(row['source'])
        snap_day=day(row['as_of'])
        if snap_day>end:
            warnings.append(f'未来日期的库存盘点未采用：{p["name"]}');continue
        stock[pid]=units(row['quantity'],row['unit'],p,positive=False)
        stock_sources[pid]=[row['source']];snapshot_dates[pid]=row['as_of']
    latest_price={}
    for r in valid:
        if r['kind'] not in {'purchase','use'}:continue
        pid=r['product_id'];q=units(r['quantity'],r['unit'],products[pid])
        if r['kind']=='purchase' and r.get('paid') is not None:
            latest_price[pid]={'per_base_unit':number(r['paid'])/q,'date':r['date'],'source':r['source']}
        if pid in stock and r['date']>snapshot_dates[pid]:
            stock[pid]+=q if r['kind']=='purchase' else -q
            stock_sources[pid].append(r['source'])
    rates={};plan=[];plan_seen=set()
    for row in data.get('daily_plan',[]):
        pet_id,pid=row['pet_id'],row['product_id']
        if pet_id not in pets:raise ValueError('Unknown pet in daily plan')
        p=products[pid];text(row['source'])
        if (pet_id,pid) in plan_seen:raise ValueError('Combine duplicate pet/product daily plan rows first')
        plan_seen.add((pet_id,pid))
        q=units(row['quantity'],row['unit'],p);rates[pid]=rates.get(pid,Decimal(0))+q
        price=latest_price.get(pid)
        plan.append({'pet_id':pet_id,'pet':pets[pet_id]['name'],'product_id':pid,'product':p['name'],
                     'daily_quantity':q,'unit':p['base_unit'],'trip_quantity':q*trip_days,
                     'display_daily_quantity':number(row['quantity']),
                     'display_unit':p.get('pack_label','pack') if row['unit']=='pack' else row['unit'],
                     'daily_cost':price['per_base_unit']*q if price else None,
                     'plan_kcal':calories[pid]*q if calories[pid] is not None else None,
                     'source':row['source'],'price_source':price['source'] if price else None})
    supplies=[]
    for pid,p in products.items():
        balance=stock.get(pid);rate=rates.get(pid);price=latest_price.get(pid)
        negative=balance is not None and balance<0
        if negative:warnings.append(f'{p["name"]}的账面库存为负，需核对漏记或单位，暂不预测天数。')
        supplies.append({'product_id':pid,'product':p['name'],'unit':p['base_unit'],
                         'book_stock':balance,'last_stock_count':snapshot_dates.get(pid),
                         'sources':stock_sources.get(pid,[]),'daily_total':rate,
                         'days_covered':balance/rate if balance is not None and not negative and rate else None,
                         'latest_price':price,
                         'calorie_source':p['calories']['source'] if p.get('calories') else None,
                         'cost_per_100kcal':price['per_base_unit']*100/calories[pid]
                            if price and calories[pid] is not None else None})
    spending={};unpriced=[]
    for r in valid:
        if not start_date<=day(r['date'])<=end or r['kind'] not in {'purchase','expense'}:continue
        if r.get('paid') is None:
            unpriced.append(r['id']);continue
        category=r.get('category',products[r['product_id']].get('category','supplies')) if r['kind']=='purchase' else r['category']
        spending[category]=spending.get(category,Decimal(0))+number(r['paid'])
    if unconfirmed:warnings.append('以下记录尚未确认，未计入库存和支出：'+', '.join(unconfirmed))
    if unpriced:warnings.append('以下购买记录缺少实付价格，未当成免费：'+', '.join(unpriced))
    handoff=data.get('handoff',{})
    if not isinstance(handoff,dict):raise ValueError('handoff must be an object')
    for field in ['feeding_times','separation','emergency_plan']:
        if handoff.get(field) is not None:text(handoff[field])
    gaps=[field for field in ['feeding_times','separation','emergency_plan'] if not handoff.get(field)]
    if not pets:gaps.append('pets')
    for pid in pets:
        if not any(r['pet_id']==pid for r in plan):gaps.append(f'daily_plan:{pid}')
        if not pets[pid].get('routine'):gaps.append(f'routine:{pid}')
    return {'schema_version':1,'as_of':as_of,'period_start':start_date.isoformat(),'currency':currency,
            'supplies':supplies,'daily_plan':plan,'trip_days':trip_days,
            'spending':spending,'recorded_spending':sum(spending.values(),Decimal(0)),
            'spending_complete':not unpriced and not unconfirmed,
            'priced_daily_subtotal':sum((r['daily_cost'] for r in plan if r['daily_cost'] is not None),Decimal(0)),
            'daily_cost_complete':bool(plan) and all(r['daily_cost'] is not None for r in plan),
            'pets':[{'id':p['id'],'name':p['name'],'species':p['species'],'routine':p.get('routine',[]),
                     'care_source':p.get('care_source','Owner notes; source unspecified')} for p in pets.values()],
            'notes':[{'date':r['date'],'pet':pets[r['pet_id']]['name'],'text':r['text'],'source':r['source']}
                     for r in valid if r['kind']=='note' and day(r['date'])>=start_date],
            'handoff':handoff,'handoff_gaps':gaps,'handoff_status':'draft' if gaps else 'ready_from_supplied_instructions',
            'duplicates_ignored':duplicates,'unconfirmed_excluded':unconfirmed,'future_excluded':future,
            'warnings':warnings,
            'basis':'Book stock only; recorded cash spending differs from projected daily cost. Daily quantities are owner-supplied, not new feeding advice.'}


def fmt(value, places=2):
    if value is None:return '待补充'
    return format(value.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP),'f')


def md(value):
    return html.escape(str(value)).replace('|','\\|').replace('\n',' ').replace('\r',' ')


def documents(report):
    r=report;currency=r['currency']
    brief=[f'# 宠物生活账本 · {r["as_of"]}', '',
           f'已记录支出：**{currency} {fmt(r["recorded_spending"])}**（{r["period_start"]} 至 {r["as_of"]}，未录入的消费不在其中）。',
           f'按最近小票估算的日常用量成本：**{currency} {fmt(r["priced_daily_subtotal"])} / 天**'+
           ('。' if r['daily_cost_complete'] else '（仅已知价格部分，并非完整合计）。'),'',
           '## 粮和用品还能撑多久？','',
           '| 用品 | 账面余量 | 最近盘点 | 每日合计用量 | 可用天数 |','| --- | ---: | --- | ---: | ---: |']
    for s in r['supplies']:
        brief.append(f'| {md(s["product"])} | {fmt(s["book_stock"])} {s["unit"]} | {s["last_stock_count"] or "待补充"} | {fmt(s["daily_total"])} {s["unit"]} | {fmt(s["days_covered"],1)} |')
    brief+=['','余量为“盘点 + 后续已记入库 − 已记消耗”。漏记消耗会高估库存；天数按主人提供的现有日用量预测，不是实物检测或新喂养建议。',
            '', '## 钱花在哪里？','']
    brief += [f'- {md(k)}：{currency} {fmt(v)}' for k,v in r['spending'].items()]
    brief += ['','## 每只宠物的既定日用量','']
    for p in r['daily_plan']:
        brief.append(f'- {md(p["pet"])} / {md(p["product"])}：{fmt(p["daily_quantity"])} {p["unit"]}/天；'
                     f'按小票估算 {currency} {fmt(p["daily_cost"])}/天；既定用量对应 {fmt(p["plan_kcal"],1)} kcal。'
                     f'依据：{md(p["source"])}；价格：{md(p["price_source"] or "未知")}。')
    brief += ['','## 标签与小票的价格换算','']
    for s in r['supplies']:
        if s['cost_per_100kcal'] is not None:
            brief.append(f'- {md(s["product"])}：{currency} {fmt(s["cost_per_100kcal"])} / 100 kcal；小票 {md(s["latest_price"]["source"])}，标签 {md(s["calorie_source"])}。这不代表营养适合程度。')
    brief += ['','## 主人的生活记录','']
    brief += [f'- {n["date"]} · {md(n["pet"])}：{md(n["text"])}（{md(n["source"])}）' for n in r['notes']]
    if not r['notes']:brief.append('- 本期没有录入生活观察。')
    brief += ['',f'已忽略 {len(r["duplicates_ignored"])} 条同 ID 重复记录；排除 {len(r["unconfirmed_excluded"])} 条待确认记录、{len(r["future_excluded"])} 条未来记录。']
    if r['warnings']:brief+=['','## 需核对','']+['- '+md(w) for w in r['warnings']]
    card=[f'# 宠物托管交接单 · {r["trip_days"]} 天','',
          '状态：'+('草稿，以下信息仍需补齐。' if r['handoff_gaps'] else '已按主人提供的信息整理，交接前请主人复核。'), '']
    def gap_label(g):
        labels={'feeding_times':'喂食时间','separation':'分开喂食安排','emergency_plan':'紧急联系与处理安排','pets':'宠物信息'}
        if g in labels:return labels[g]
        kind,_,pid=g.partition(':')
        pet_name=next((p['name'] for p in r['pets'] if p['id']==pid),pid)
        return str(pet_name)+('的既定日用量' if kind=='daily_plan' else '的日常照顾说明')
    if r['handoff_gaps']:card+=['待补充：'+', '.join(md(gap_label(g)) for g in r['handoff_gaps']), '']
    for pet in r['pets']:
        card += [f'## {md(pet["name"])} · '+{'cat':'猫','dog':'狗'}[pet['species']],'']
        for p in r['daily_plan']:
            if p['pet_id']==pet['id']:
                q=p['display_daily_quantity'];u=md(p['display_unit'])
                card.append(f'- {md(p["product"])}：每天 {fmt(q)} {u}；'
                            f'{r["trip_days"]} 天准备 {fmt(q*r["trip_days"])} {u}（共 {fmt(p["trip_quantity"])} {p["unit"]}；{md(p["source"])}）。')
        card += ['- '+md(line) for line in pet['routine']]
        card += [f'- 日常照顾信息来源：{md(pet["care_source"])}。','']
    labels={'feeding_times':'喂食时间','separation':'分开照顾/防抢食','emergency_plan':'紧急联系与处理安排'}
    card+=['## 共用安排','']+[f'- {label}：{md(r["handoff"].get(key) or "待主人补充")}' for key,label in labels.items()]
    card+=['','数量仅按现有日用量乘以天数；药物、治疗和临时换粮需另行明确指示。此文件不会自动发送给任何人。']
    return '\n'.join(brief)+'\n','\n'.join(card)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build')
    build.add_argument('--input',type=Path,required=True)
    build.add_argument('--as-of',required=True)
    build.add_argument('--start')
    build.add_argument('--trip-days',type=int,default=1)
    build.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.input.stat().st_size>5_000_000:raise ValueError('Record file exceeds 5 MB')
        data=json.loads(args.input.read_text(encoding='utf-8-sig'),parse_float=Decimal)
        report=analyze(data,args.as_of,start=args.start,trip_days=args.trip_days)
        brief,card=documents(report)
        targets=[args.out/name for name in ['brief.md','care-card.md','report.json']]
        if args.input.resolve() in [p.resolve() for p in targets]:
            raise ValueError('Output would overwrite the input record')
        args.out.mkdir(parents=True,exist_ok=True)
        for target,value in zip(targets,[brief,card,json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n']):
            target.write_text(value,encoding='utf-8')
    except (ValueError,KeyError,TypeError,OSError,InvalidOperation) as error:
        parser.error(str(error))
    print(json.dumps({'files':['brief.md','care-card.md','report.json'],'handoff_status':report['handoff_status'],
                      'duplicates_ignored':len(report['duplicates_ignored'])}))


if __name__=='__main__':main()
