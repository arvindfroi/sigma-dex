import base64, io, numpy as np
from PIL import Image
from inventory import *
def b64(im,scale=1,maxw=None):
    im=im.convert('RGBA')
    if maxw and im.width*scale>maxw: scale=max(1,maxw//im.width)
    if scale!=1: im=im.resize((im.width*scale,im.height*scale),Image.NEAREST)
    bf=io.BytesIO(); im.save(bf,'PNG'); return 'data:image/png;base64,'+base64.b64encode(bf.getvalue()).decode()
def shot(i,half=None):
    im=Image.open(f'shots_video/v{i:04d}.png').convert('RGB')
    if half=='top': im=im.crop((0,0,256,192))
    if half=='bot': im=im.crop((0,192,256,384))
    return im
def bgimg(n): 
    im=Image.open(f'inv/bg{n:03d}.png').convert('RGBA'); a=np.array(im)
    m=(a[...,:3]!=40).any(-1); ys,xs=np.where(m)
    return im.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1)) if len(xs) else im
def bginfo(n):
    w,h,e=nscr(n); pals=sorted(set(int(v>>12) for v in e)); im=bgimg(n)
    return f"{im.width}×{im.height} px synlig, {len(pals)} palett(er) à 15 farger"
def cell(name):
    return Image.open(f'inv/{name}.png')
def cellinfo(names):
    ims=[cell(n) for n in names]; w=max(i.width for i in ims); h=max(i.height for i in ims)
    return f"{len(names)} bilde(r), opptil {w}×{h} px, 15 farger"
SABER='shots_night/n121.png'
items=[]  # (scene, title, kind, status, images, info, note)
S=[]
def add(scene,title,kind,imgs,info,note,status='todo',files=''):
    S.append(dict(scene=scene,title=title,kind=kind,imgs=imgs,info=info,note=note,status=status,files=files))
sc1='1 · Tropisk natt (var: soloppgang)'
add(sc1,'Ho-Oh som flyr ut av solen','Pokémon',[b64(cell(f's24_c{k}'),1) for k in range(1,7)],'6 bilder, opptil 112×104 px, 15 farger',
    '<b>Byttet til Sabertann (3D-versjon, nattlys).</b> Egen 3D-modell med rigg i Blender, rendret til 15-farges pikselbilder: han seiler inn fra horisonten i månegata. Stor hatt med gullskalle og lysende kanonluker (inspirert av Kaptein Sabeltann og Den sorte dame). 8 bilder svømmeløkke, tre detaljnivåer, vugging og krenging. 778 av 1024 fliser.','done','23–26')
add(sc1,'Solen','Bakgrunnsdetalj',[b64(cell('s24_c0'),1)],'64×64 px, deler fil med Ho-Oh','<b>Byttet til fullmåne</b> (egen tegning, 64 egne fliser i stedet for én speilet firedel). Stiger 31 px som sola gjorde.','done','24, 26')
add(sc1,'Himmel, hav og grantrær','Bakgrunn',[b64(bgimg(18),1,256),b64(bgimg(16),1,256),b64(bgimg(15),1,256)],'3 lag à 256×256 px, 2–5 paletter','<b>Tegnet om til tropisk natt</b>: stjernehimmel, månelys, skyer med sølvkant, øyer med små palmer og en havn med lykter, månegate på havet, palmer i stedet for grantrær. 809 + 221 fliser.','done','15–18, 6–7, 0–1')
add(sc1,'Game Freak og copyright','Tekst',[b64(bgimg(13),1,256),b64(bgimg(14),1,256)],'256×192 px','Bør beholdes, kanskje med egen kreditt-tekst i tillegg.','keep','13–14')
sc2='2 · Ethan og Lyra løper'
add(sc2,'Ethan og Lyra (løper, ansikt, kropp)','Person',[b64(cell(f's74_c{k}'),1) for k in range(7)],cellinfo([f's74_c{k}' for k in range(7)]),'Ett stillestående bilde per person, kuttet i 3 biter (hode, overkropp, bein). Kameraet ruller over bakgrunnen, figurene selv beveger seg ikke. Tegnes om når vi har egne hovedpersoner.','todo','73–76')
add(sc2,'Gress og blomster','Bakgrunnsdetalj',[b64(cell(f's78_c{k}'),1) for k in range(4)],cellinfo([f's78_c{k}' for k in range(4)]),'Kan beholdes.','keep','77–80')
add(sc2,'Gressmark, landsby med vindmøller og tre','Bakgrunn',[b64(bgimg(37),1,256),b64(bgimg(35),1,256),b64(bgimg(38),1,256)],'Opptil 512×512 px (rulles), 4 paletter','Ett stort bilde (512×512) som kameraet ruller over. <b>Beholdes.</b>','keep','31–38')
sc3='3 · Byer, rival og legender'
add(sc3,'Byene kameraet flyr over (3D)','3D-modell',[b64(shot(640,'top')),b64(shot(700,'top'))],'3 modeller (New Bark, Goldenrod, Ecruteak), 700–1400 polygoner hver, med små 2D-personer som teksturer','Mest arbeid. Kan beholdes (byene finnes i spillet uansett).','keep','97–105')
add(sc3,'Silver (rival) i rød trekant','Person',[b64(bgimg(46),1,200),b64(cell('s66_c0'),1),b64(bgimg(42),1,200)],bginfo(46)+'; silhuett 64×128 px','<b>Silver byttes</b> (portrett og silhuett). Trekantene beholdes, men fargen kan endres. Fargen er bare en palett, så det er en liten jobb.','todo','39–47, 65–68')
add(sc3,'Suicune, Entei og Raikou','Pokémon',[b64(bgimg(47),1,256),b64(bgimg(48),1,256),b64(bgimg(49),1,256)],'3 striper à 256×64 px, 1–2 paletter hver','<b>Byttes til hjortetrioen: Moosus, Felk og Rocketdeer.</b> Ett bilde per beist: en flat stripe med ansiktet tett på. Stripene glir inn og legger seg over hverandre.','todo','47–49')
add(sc3,'Eusine og Unown','Person + Pokémon',[b64(cell('s70_c0'),1),b64(cell('s70_c2'),1),b64(cell('s70_c3'),1),b64(cell('s70_c4'),1)],'Eusine 64×128 px; Unown 3 bilder à 64×64 px, 15 farger','<b>Unown byttes til sigmanske Unown.</b> Eusine byttes til den figuren som får rollen hans.','todo','69–72')
add(sc3,'Team Rocket-lederne og R-en','Person',[b64(bgimg(50),1,256),b64(bgimg(51),1,256),b64(bgimg(52),1,256)],'2 bilder à ~256×150 px, 3 paletter hver; R-logo','Archer, Ariana, Proton og Petrel. Byttes, men vi har ingen skurkegruppe ennå. Venter.','wait','41, 50–52')
sc4='4 · Starter-valget'
add(sc4,'Ethan og Lyra (portretter)','Person',[b64(bgimg(57),1,200),b64(bgimg(58),1,200)],'2 portretter à ca. 130×88 px, 2 paletter','Samme figurer som i scene 2.','todo','53–58')
add(sc4,'Chikorita, Totodile og Cyndaquil','Pokémon',[b64(cell('s86_c0'),2),b64(cell('s90_c0'),2),b64(cell('s94_c0'),2)],'3 bilder à 48×48 px, 15 farger (ett vises per gang)','Byttes til våre tre startere. Ikke animert: ett bilde hver, som spillet flytter og spretter (27 steg). Blad-, ild- og vanneffektene rundt er egne effekter.','todo','85–96')
add(sc4,'Hånd med Pokéball og glimt','Bakgrunnsdetalj',[b64(cell(f's82_c{k}'),1) for k in (1,2,5)],'Opptil 64×64 px','Kan beholdes.','keep','81–84')
add(sc4,'Fargestriper','Bakgrunn',[b64(bgimg(55),1,256),b64(bgimg(56),1,256)],'256×192 px','Kan beholdes.','keep','55–56')
sc5='5 · Havet'
add(sc5,'Suicune på havet','Pokémon',[b64(shot(1220,'bot')),b64(bgimg(62),2)],'Lite bilde på ca. 38×55 px i bakgrunnslaget','Ett stillestående bilde av Suicune på en stein nede i hjørnet. Kameraet glir opp mot himmelen og alt blir hvitt. Byttes til den hjorten som tar Suicune sin plass.','todo','60, 62')
add(sc5,'Himmel, hav og lysspor','Bakgrunn',[b64(bgimg(64),1,256),b64(bgimg(63),1,256)],'256×512 px (rulles)','Kan beholdes.','keep','59–64')
add('Lyd','Musikken (tittelmelodien)','Musikk',[],'Ett notestykke (SEQ_GS_TITLE, 17,8 KB) som spiller fra start til og med tittelskjermen. Origin har ikke endret det.',
    'Ikke bestemt. Samme stykke spiller videre på tittelskjermen, så et nytt stykke må dekke begge. Det lages fra MIDI, og vi må ha lov til å bruke det.','maybe','lydarkivet, sekvens 1004')
sc6='6 · Tittelskjermen'
add(sc6,'Logoen','Logo',[b64(shot(1400,'top').crop((0,0,256,130)),2)],'Ca. 220×110 px øverst på skjermen','Origin bruker den kinesiske logoen (口袋妖怪 起源心金) med «Origin HeartGold» under. Byttes til vår egen logo.','todo','title')
add(sc6,'Red og Kanto-starterne','Bilde',[b64(shot(1400,'bot')),b64(shot(1590,'bot'))],'3 bilder på nederste skjerm, ca. 256×190 px, tones inn og ut ett om gangen','Origin sitt eget bilde av Red med Charizard, Blastoise og Venusaur. Byttes til noe av vårt, for eksempel hovedpersonen med våre startere.','todo','title')
add(sc6,'PUSH START BUTTON og Game Freak-linja','Tekst',[b64(shot(1400,'top').crop((0,150,256,192)),2),b64(shot(1400,'bot').crop((0,170,256,192)),2)],'Tekstbilder','Kan beholdes, eller oversettes til norsk senere.','keep','title')
scenes_shots={sc6:[1400,1520],sc1:[440],sc2:[560],sc3:[640,760,840,1020],sc4:[1080,1120],sc5:[1220]}
ST={'wait':('Venter','wait'),'done':('Ferdig','ok'),'todo':('Bør byttes','todo'),'maybe':('Valgfritt','maybe'),'keep':('Kan beholdes','keep')}
html=['''<!doctype html><html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Introen: alt som kan byttes</title><style>
:root{--bg:#f6f5fb;--card:#fff;--ink:#1d1b26;--mut:#6b6880;--line:#e3e0ee;--acc:#7b3fbf;--ok:#1f8a4c;--todo:#c0392b;--maybe:#b7791f;--keep:#5b6b80;--pix:#9cc3ea}
@media (prefers-color-scheme:dark){:root{--bg:#15141b;--card:#1f1e28;--ink:#ecebf3;--mut:#a5a2b8;--line:#33313f;--acc:#c49bff;--pix:#2b3f55}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 60px}h1{font-size:26px;margin:0 0 6px}h2{font-size:19px;margin:36px 0 10px;border-bottom:2px solid var(--line);padding-bottom:6px}
.lead{color:var(--mut);max-width:760px}.legend{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
.tag{display:inline-block;font-size:12px;font-weight:600;padding:2px 9px;border-radius:99px;color:#fff}.ok{background:var(--ok)}.todo{background:var(--todo)}.maybe{background:var(--maybe)}.keep{background:var(--keep)}.wait{background:#7a5bb5}
.shots{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.shots img{width:128px;image-rendering:pixelated;border-radius:6px;border:1px solid var(--line)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0;display:grid;grid-template-columns:1fr 1.25fr;gap:14px}
@media (max-width:720px){.card{grid-template-columns:1fr}}
.pics{display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;background:var(--pix);border-radius:8px;padding:8px;min-height:60px}
.pics img{image-rendering:pixelated;max-width:100%}.kind{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
h3{margin:2px 0 6px;font-size:16px}.info{font-size:13px;color:var(--mut)}.files{font-size:12px;color:var(--mut);margin-top:6px;font-family:ui-monospace,Menlo,monospace}
table{border-collapse:collapse;width:100%;margin-top:8px;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
</style></head><body><main>
<h1>Introen i Origin HeartGold: alt som kan byttes</h1>
<p class="lead">Introen er ikke en videofil. Den tegnes mens den spilles, av bilder, sprites og tre små 3D-byer. Hver del under kan byttes for seg uten at resten endres, og banen og tempoet blir som før. Alle bildene er hentet rett fra spillet (EN-patch rc8). Grensene (størrelse og farger) er det en ny tegning må holde seg innenfor for å få samme ytelse.</p>
<div class="legend"><span class="tag ok">Ferdig</span><span class="tag todo">Bør byttes</span><span class="tag maybe">Valgfritt</span><span class="tag keep">Kan beholdes</span><span class="tag wait">Venter</span></div>
<table><tr><th>Hva</th><th>Antall</th></tr>''']
from collections import Counter
cnt=Counter(s['status'] for s in S)
for k in ('done','todo','maybe','keep','wait'): html.append(f'<tr><td><span class="tag {ST[k][1]}">{ST[k][0]}</span></td><td>{cnt[k]}</td></tr>')
html.append('</table>')
cur=None
for s in S:
    if s['scene']!=cur:
        cur=s['scene']; html.append(f'<h2>Scene {cur}</h2>' if cur[0].isdigit() else f'<h2>{cur}</h2>')
        if cur in scenes_shots:
            html.append('<div class="shots">'+''.join(f'<img src="{b64(shot(i))}" alt="Skjermbilde fra scenen">' for i in scenes_shots[cur])+'</div>')
    pics=''.join(f'<img src="{u}" alt="{s["title"]}">' for u in s['imgs'])
    if s['files']=='23–26': pics+=f'<img src="{b64(Image.open(SABER).crop((0,192,256,384)))}" alt="Sabertann i spillet" style="width:192px">'
    t,c=ST[s['status']]
    html.append(f'<div class="card"><div class="pics">{pics or "<span class=info>(lyd)</span>"}</div><div><div class="kind">{s["kind"]} <span class="tag {c}">{t}</span></div><h3>{s["title"]}</h3><div>{s["note"]}</div><div class="info">Grense: {s["info"]}</div><div class="files">{"Filer i a/2/6/2: "+s["files"] if s["files"]!="title" else "Tittelskjermens egne filer (kartlegges når vi starter)"}</div></div></div>')
html.append('<p class="info" style="margin-top:30px">Laget 12. november 2026 fra spillets egne filer (EN-patch rc8). Inneholder spillets originale grafikk, så siden bør bare deles i gruppen og ikke legges ut offentlig.</p></main></body></html>')
open('/Users/arvind/Sigma pokemon pc port attempt/intro_oversikt.html','w').write('\n'.join(html))
print('ok',cnt)
