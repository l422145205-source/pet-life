#!/usr/bin/env python3
"""Contributor-only media renderer (Pillow). Runtime Skill scripts remain stdlib-only.

Draws synthetic fixtures and actual helper results; these are not Agent screenshots.
Usage: python tools/render_showcase.py --font <CJK-font> [--bold-font <font>]
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
BG='#F8F5EC'; INK='#203F36'; GREEN='#337864'; MUTED='#66786D'
LINE='#DADFD2'; WHITE='#FFFFFF'; GOLD='#F1C666'; PALE='#EAF1E8'; RED='#A45D49'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font',required=True,type=Path)
    parser.add_argument('--bold-font',type=Path)
    args=parser.parse_args()
    def font(size,bold=False):
        return ImageFont.truetype(str(args.bold_font if bold and args.bold_font else args.font),size)
    def canvas(h):
        im=Image.new('RGB',(1500,h),BG)
        return im,ImageDraw.Draw(im)
    def txt(d,xy,value,size=27,fill=INK,bold=False):
        d.text(xy,str(value),font=font(size,bold),fill=fill)
    def wrap(d,x,y,value,width,size=27,fill=INK,gap=12):
        line=''
        for char in value:
            if char=='\n' or d.textlength(line+char,font=font(size))>width:
                txt(d,(x,y),line,size,fill); y+=size+gap; line='' if char=='\n' else char
            else: line+=char
        if line: txt(d,(x,y),line,size,fill); y+=size+gap
        return y
    def card(d,box,fill=WHITE):
        d.rounded_rectangle(box,radius=28,fill=fill,outline=LINE,width=2)
    def pill(d,x,y,label,fill=PALE):
        width=int(d.textlength(label,font=font(23)))+36
        d.rounded_rectangle((x,y,x+width,y+43),radius=21,fill=fill)
        txt(d,(x+18,y+4),label,23)
        return x+width+12
    def cat(d,x,y,scale=1,color=GOLD):
        # Original simple line-art mascot: real-pet context, no game interactions.
        s=scale
        pts=[(x-65*s,y-22*s),(x-66*s,y-82*s),(x-24*s,y-54*s),(x+24*s,y-54*s),(x+66*s,y-82*s),(x+65*s,y-22*s)]
        d.polygon(pts,fill=color)
        d.ellipse((x-73*s,y-62*s,x+73*s,y+62*s),fill=color)
        for ex in (x-28*s,x+28*s):
            d.arc((ex-9*s,y-13*s,ex+9*s,y+6*s),0,180,fill=INK,width=max(2,int(4*s)))
        d.polygon([(x-6*s,y+10*s),(x+6*s,y+10*s),(x,y+18*s)],fill=INK)
        d.arc((x-16*s,y+10*s,x,y+31*s),0,90,fill=INK,width=3)
        d.arc((x,y+10*s,x+16*s,y+31*s),90,180,fill=INK,width=3)
    reports={name:json.loads((ROOT/'examples/everyday'/f'{name}.json').read_text(encoding='utf-8')) for name in ['stock','care','visit','replay']}
    wet=next(p for p in reports['stock']['products'] if p['product_id']=='wet')
    base=json.loads((ROOT/'examples/report.json').read_text(encoding='utf-8'))
    cash=reports['replay']
    today=[r for r in reports['care']['rows'] if r['date']=='2026-10-03']
    conflicts=sum(r['state']=='conflict' for r in today)
    absent=sum(r['state']=='not_recorded' for r in today)
    media=ROOT/'media'; media.mkdir(exist_ok=True)

    im,d=canvas(700)
    txt(d,(70,49),'PetLife',73,bold=True)
    pill(d,380,76,'REAL PETS · AGENT SKILL',GOLD)
    txt(d,(70,182),'少翻聊天记录，',58,bold=True)
    txt(d,(70,264),'多陪它一会儿。',58,bold=True)
    wrap(d,74,365,'粮袋、小票、照顾留言与观察笔记，\n变成下一次还能接着用的本地记录。',780,29)
    x=74
    for label in ['猫咪 & 狗狗','有来源的算术','跨会话接着做']:
        x=pill(d,x,501,label)
    txt(d,(74,619),'从日常囤粮，到出门交接、就诊准备。',25,MUTED)
    card(d,(968,60,1430,622),PALE)
    cat(d,1198,185,1.05)
    txt(d,(1010,285),'今天的铲屎官待办',30,bold=True)
    for n,(title,sub) in enumerate([('先看批次，再算余量','7天总量，也可能有日期缺口'),('先核实，再补打卡','未记录，不等于还没喂'),('留下原话与时间','观察摘要交给兽医判断')]):
        yy=345+n*83
        d.ellipse((1008,yy+8,1023,yy+23),fill=GREEN)
        txt(d,(1036,yy),title,27,bold=True)
        txt(d,(1036,yy+35),sub,20,MUTED)
    im.save(media/'petlife-life.png',optimize=True)

    im,d=canvas(1110)
    txt(d,(60,34),'一户两猫，四件连续的小事',48,bold=True)
    txt(d,(63,108),'合成资料 · 下列数字来自仓库中真实执行的工具输出',24,MUTED)
    panels=[
        ('01','先翻哪批粮？','囤了7罐，真的能按计划吃7天吗？',
         f'规划差额 {int(Decimal(wet["pack_equivalent"]))} 罐',
         f'首个缺口 {wet["first_shortfall"]}\n同一产品内先到日期先用；不靠加量清库存。','stock.json'),
        ('02','谁照顾过了？','两个人的留言对不上，先别再喂一次。',
         f'{conflicts} 个报告冲突 · {absent} 个未记录',
         '当天情况分开核对，未来任务只列计划。\n每只宠物、每个时段各自留记录。','care.json'),
        ('03','看诊前，少靠回忆','两天的观察，中间没记，不补成三天连续。',
         f'{len(reports["visit"]["observations"])} 条事实 + {len(reports["visit"]["pending"])} 条待确认',
         '观察原话、时间、当前照顾与治疗信息。\n不把整理记录包装成诊断。','visit.json'),
        ('04','隔天接着记','这张12元小票，昨天已经发过一遍。',
         f'{cash["before"]} → {cash["after_first_merge"]} → {cash["after_replay"]} 元',
         '第二次调用：新增0条，文件字节未变化。\n有冲突的ID或过期文件哈希拒绝写入。','replay.json')]
    for i,(n,title,question,big,detail,source) in enumerate(panels):
        x=60+(i%2)*710; y=178+(i//2)*423
        card(d,(x,y,x+670,y+388))
        pill(d,x+28,y+25,n,GOLD)
        txt(d,(x+102,y+25),title,34,bold=True)
        wrap(d,x+30,y+92,question,610,24,fill=MUTED)
        txt(d,(x+30,y+151),big,39,GREEN,True)
        wrap(d,x+30,y+225,detail,612,25,gap=13)
        txt(d,(x+30,y+344),'实际产物 / examples/everyday/'+source,18,MUTED)
    txt(d,(63,1054),'可复现的示例，不是临床验证、真实住户资料或 Agent 性能成绩。',23,MUTED)
    im.save(media/'everyday-results.png',optimize=True)

    # Show the actual allocation as food cans and a calendar, rather than another text list.
    im,d=canvas(700)
    txt(d,(60,34),'数一数有7罐，排一排却差1罐',46,bold=True)
    txt(d,(64,108),'合成示例：主人既定总用量1罐/天，规划10月4日至10月10日。',25,MUTED)
    card(d,(60,172,1440,368))
    txt(d,(92,194),'当晚实盘',28,bold=True)
    def can(x,y,color):
        d.rounded_rectangle((x,y+7,x+67,y+80),radius=11,fill=color,outline=INK,width=2)
        d.ellipse((x,y,x+67,y+20),fill=color,outline=INK,width=2)
        d.ellipse((x+24,y+5,x+43,y+13),outline=INK,width=2)
        d.line((x+12,y+55,x+55,y+55),fill=INK,width=2)
    for i in range(7):
        xx=342+i*133
        can(xx,203,GOLD if i<2 else '#A8CDB4')
    txt(d,(342,307),'2罐：所录日期10/04',24)
    txt(d,(706,307),'5罐：所录日期10/31',24)
    txt(d,(63,400),'按日期与既定用量排到日历上',29,bold=True)
    for i in range(7):
        x=60+i*198
        card(d,(x,453,x+181,615),PALE if i<6 else '#F5E1D8')
        txt(d,(x+42,468),f'10/{i+4:02}',25,bold=True)
        if i<6:
            can(x+56,512,GOLD if i==0 else '#A8CDB4')
        else:
            txt(d,(x+49,522),'+1罐',33,RED,True)
            txt(d,(x+26,570),'需核对安排',22,RED)
    txt(d,(63,650),'近日期批次有1罐未能排入既定用量；不靠加餐清库存。日期图不代表食品安全。',23,MUTED)
    im.save(media/'batch-calendar.png',optimize=True)

    steps=[
        ('给它现有资料','不必先填完整表，先说你想解决的事。',
         ['小票 R6：逗猫棒，实付12元','照顾留言：有人说喂了，有人说没喂','包装批次、日期与当晚实盘','观察笔记：10月1日、10月3日有记录']),
        ('Agent 核对事实','宿主负责识图与理解；Skill 提供任务规则。',
         ['分清宠物、产品、单位和来源','不清晰的转述单列待确认','稳定事件ID留在本地记录中','不把观察空白补成连续症状']),
        ('运行可复用工具','算术、日期与合并行为可以独立复现。',
         ['carekit stock / care / visit','merge：核对当前文件哈希','相同事件重放不新增记录','冲突和陈旧写入失败时保留原文件']),
        ('下次接着做','结果可读，记录可继续更新。',
         [f'粮食日期约束：规划差额 {int(Decimal(wet["pack_equivalent"]))} 罐',f'照顾日志：{conflicts}个冲突、{absent}个未记录',
          f'看诊摘要：{len(reports["visit"]["observations"])}条事实、{len(reports["visit"]["pending"])}条待确认',
          f'小票重放：{cash["before"]} → {cash["after_first_merge"]} → {cash["after_replay"]} 元'])]
    frames=[]
    for active,(title,subtitle,bullets) in enumerate(steps):
        im,d=canvas(750)
        txt(d,(60,34),'PetLife / 从一句话，到能接着做的记录',42,bold=True)
        for i,label in enumerate(['现有资料','核对事实','执行工具','留下结果']):
            x=60+i*355
            d.rounded_rectangle((x,130,x+315,192),radius=23,fill=GREEN if i==active else PALE)
            txt(d,(x+33,141),f'{i+1:02}  {label}',27,WHITE if i==active else INK,bold=True)
            if i<3:txt(d,(x+326,140),'→',28,MUTED)
        card(d,(60,230,1440,646))
        txt(d,(98,266),title,44,bold=True)
        txt(d,(99,331),subtitle,27,MUTED)
        for i,item in enumerate(bullets):
            d.ellipse((103,401+i*51,114,412+i*51),fill=GREEN)
            txt(d,(135,388+i*51),item,29)
        txt(d,(62,691),'流程动画 · 合成资料与真实工具输出，不是 Agent 操作录屏。',23,MUTED)
        frames.append(im)
    frames[0].save(media/'workflow.gif',save_all=True,append_images=frames[1:],duration=[1800,2100,2200,3300],loop=0,optimize=False)
    print(json.dumps({'media':[p.name for p in media.glob('*') if p.suffix in {'.png','.gif'}],
                      'basis':'Synthetic fixtures and actual helper outputs; original Pillow artwork.'}))


if __name__=='__main__': main()
