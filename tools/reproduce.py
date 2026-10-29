#!/usr/bin/env python3
"""Reproduce synthetic PetLife outputs and a two-session receipt replay; no Agent/API needed."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(script, *args):
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(ROOT/'scripts'/script), *map(str,args)],
                            check=True, capture_output=True, encoding='utf-8')
    return json.loads(result.stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'work/demo')
    args=parser.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    fixture=ROOT/'assets/everyday.example.json'
    run('petlife.py','build','--input',fixture,'--as-of','2026-10-03','--trip-days',3,'--out',out)
    for command in ['stock','care','visit']:
        run('carekit.py',command,'--input',fixture,'--as-of','2026-10-03','--out',out)
    run('carekit.py','care','--input',ROOT/'assets/dog-walk.example.json','--as-of','2026-10-03','--days',2,'--out',out/'dog')
    ledger=out/'ledger.demo.json'; shutil.copyfile(fixture,ledger)
    before=json.loads((out/'report.json').read_text(encoding='utf-8'))['recorded_spending']
    first_hash=run('carekit.py','inspect','--input',ledger)['sha256']
    first=run('carekit.py','merge','--input',ledger,'--patch',ROOT/'assets/receipt-patch.example.json',
              '--as-of','2026-10-03','--write','--expect-sha256',first_hash)
    run('petlife.py','build','--input',ledger,'--as-of','2026-10-03','--out',out/'after-first')
    after=json.loads((out/'after-first/report.json').read_text(encoding='utf-8'))['recorded_spending']
    second=run('carekit.py','merge','--input',ledger,'--patch',ROOT/'assets/receipt-patch.example.json',
               '--as-of','2026-10-03','--write','--expect-sha256',first['sha256'])
    run('petlife.py','build','--input',ledger,'--as-of','2026-10-03','--out',out/'after-replay')
    replayed=json.loads((out/'after-replay/report.json').read_text(encoding='utf-8'))['recorded_spending']
    result={'example':'SYNTHETIC; actual helper execution, not an Agent benchmark',
            'before':before,'after_first_merge':after,'after_replay':replayed,
            'first_added':first['added'],'replay_added':second['added'],
            'replay_bytes_unchanged':first['sha256']==second['sha256']}
    (out/'replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'replay.md').write_text(f'''# 隔天又发了一遍小票，账会多算吗？

合成示例，实际运行 Python 工具生成；不是模型问答效果对比。

| 阶段 | 已记录支出 CNY | 新增记录 |
| --- | ---: | ---: |
| 原账本 | {before} | — |
| 加入12元逗猫棒小票 E2 | {after} | {first['added']['records']} |
| 另一次调用重放同一 E2 | {replayed} | {second['added']['records']} |

重放后文件字节保持一致：{result['replay_bytes_unchanged']}。

依据是稳定记录 ID 与内容一致性校验，不是看两张小票总价一样就合并。同 ID 改价格会拒绝写入；不同的真实购买必须给不同 ID。过期的文件哈希也会阻止覆盖，Agent 需要重新读取和核对。

这次复现只证明记录合并工具的行为。照片识别、同一小票的身份判断和抽取质量取决于宿主 Agent 与原始资料，不能由此宣称“绝不重复记账”。
''',encoding='utf-8')
    print(json.dumps({'output':str(out),'replay':result},ensure_ascii=False))


if __name__=='__main__': main()
