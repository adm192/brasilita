import json,re,unicodedata,glob,os
BASE=os.path.dirname(os.path.abspath(__file__))

def norm(s):
    s=unicodedata.normalize('NFD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
GEN={'via','viale','corso','piazza','piazzale','strada','vicolo','frazione','localita','regione',
 'borgata','cantone','spalto','borgo','case','sparse','sp','apartamento','appartamento','venda',
 'com','para','di','del','della','dei','delle','centro','piemonte','italia','casa','imovel',
 'bilocale','trilocale','quadrilocale','mansarda','cobertura','terreo','terrea','amplo','comodos',
 'jardim','privativo','vista','panoramica','reformada','terraco','morar','pronto','mobiliado',
 'parcelado','sem','juros','varanda','bem','distribuido','tipico','piscina','na','em','de','da',
 'do','no','os','as','le','la','il','lo','a','e','o','cascina','cascine'}
STREETWORD=re.compile(r'\b(via|viale|corso|piazza|piazzale|strada|vicolo|largo)\b',re.I)
def toks(s): return [t for t in norm(s).split() if t not in GEN and len(t)>1 and not t.isdigit()]
def nums(s): return {t for t in norm(s).split() if t.isdigit()}
def cat(t):
    tl=(t or '').lower()
    for name,keys in [('Garagem',['garage','box']),('Terreno',['terreno']),
        ('Comercial',['negozi','locali commerciali','ufficio','capannone','magazzino','deposito','masseria']),
        ('Prédio',['palazzo','edificio'])]:
        if any(k in tl for k in keys): return name
    return 'Residencial'
DROP_CAT={'Garagem','Terreno','Comercial'}
OVERRIDE={  # pares conferidos manualmente (preco divergente impede o match automatico)
 'apartamento-parcelado-sem-juros-a-venda-em-asti-piemonte-asti-piemonte-piemonte-76CDD7D1':
   ('129488560','conferido manualmente — trilocale 56 m², térreo, affitto a riscatto; preço no site inclui o parcelamento sem juros'),
}

AG=[('441559_passione-casa','Passione Casa Immobiliare','441559/passione-casa-immobiliare'),
 ('229559_tempocasa','Tempocasa Alessandria','229559/tempocasa-alessandria'),
 ('414257_vendocasa','Vendocasa Asti Est','414257/vendocasa-asti-est'),
 ('9363_franco-nicola','Franco Nicola Moncalvo','9363/franco-nicola-moncalvo'),
 ('137721_la-ca','La Cà Nizza Monferrato','137721/la-ca-nizza-monferrato'),
 ('379813_lux-biella','Lux Biella','379813/lux-biella')]
AGN={k:(n,u) for k,n,u in AG}
COLS=['id','title','price','contract','typology','surface','rooms','city','addr','prov','nuda']
imm=[]
for f in sorted(glob.glob(os.path.join(BASE,'dados','agencies','*.tsv'))):
    k=os.path.basename(f)[:-4]
    for line in open(f,encoding='utf-8'):
        if not line.strip(): continue
        p=(line.rstrip('\n').split('\t')+['']*11)[:11]
        d=dict(zip(COLS,p)); d['key']=k; d['agency'],slug=AGN[k]
        d['agency_url']='https://www.immobiliare.it/agenzie-immobiliari/%s/'%slug
        d['url']='https://www.immobiliare.it/annunci/%s/'%d['id']
        d['price']=int(d['price']) if d['price'].strip() else None
        d['nuda']=d['nuda'].strip()=='1'
        d['sqm']=int(re.sub(r'\D','',d['surface']) or 0)
        d['stok']=set(toks(d['addr']))
        m=re.search(r'\b(\d{1,4})[a-zA-Z]?\s*,',d['title'])
        d['num']=nums(d['addr'])|({m.group(1)} if m else set())
        d['cat']=cat(d['typology']); d['bmatch']=None
        imm.append(d)

bras=json.load(open(os.path.join(BASE,'dados','brasilita_items.json'),encoding='utf-8'))
for b in bras:
    b['bcity']=b['city'].split(',')[0].strip()
    b['sqm']=int(re.sub(r'\D','',b.get('area') or '') or 0)
    b['url']='https://www.brasilita.com/imoveis/'+b['slug']
    b['stok']=set(toks(b['title']))-set(toks(b['bcity']))
    b['num']=nums(b['title'])
    b['hasstreet']=bool(STREETWORD.search(b['title']))

def ratio(a,b):
    if not a or not b: return 0
    return abs(a-b)/max(a,b)
def tierA(b,i):
    if norm(b['bcity'])!=norm(i['city']) or i['contract']!='sale': return None
    ov=b['stok']&i['stok']
    if not ov: return None
    if i['price'] and ratio(b['price'],i['price'])>0.35 and ratio(b['sqm'],i['sqm'])>0.25: return None
    s=len(ov)*5.0; why=['rua confere (%s)'%'+'.join(sorted(ov))]
    nov=b['num']&i['num']
    if nov: s+=5; why.append('nº %s'%'/'.join(sorted(nov)))
    elif b['num'] and i['num']: s-=6; why.append('nº diferente')
    if i['price'] is not None:
        d=abs(b['price']-i['price'])
        if d==0: s+=4; why.append('preço igual')
        else:
            s+= 1 if d<=5000 else -2
            why.append('preço difere €%s'%f'{d:,}'.replace(',','.'))
    if b['sqm'] and i['sqm']:
        d=abs(b['sqm']-i['sqm'])
        s+= 3 if d==0 else (1 if d<=5 else -2)
        if d>5: why.append('m² difere')
    return (s,'; '.join(why),i)
def tierB(b,i):
    if b['hasstreet']: return None
    if norm(b['bcity'])!=norm(i['city']) or i['contract']!='sale': return None
    if i['price'] is None or b['price']!=i['price']: return None
    s=10.0; why=['mesma cidade + preço idêntico']
    if b['sqm'] and i['sqm']:
        d=abs(b['sqm']-i['sqm'])
        s+= 3 if d==0 else (1 if d<=8 else -1.5)
        if d>8: why.append('m² difere')
    return (s,'; '.join(why),i)

for b in bras:
    ca=sorted([r for r in (tierA(b,i) for i in imm) if r],key=lambda x:-x[0])
    best=ca[0] if ca and ca[0][0]>=6 else None
    if not best:
        cb=sorted([r for r in (tierB(b,i) for i in imm) if r],key=lambda x:-x[0])
        if cb and cb[0][0]>=8 and (len(cb)==1 or cb[0][0]-cb[1][0]>=2): best=cb[0]
    if best:
        b['score'],b['why'],b['m']=best
        b['conf']='Alta' if best[0]>=12 else 'Média – conferir'
        best[2]['bmatch']=b
    else:
        b['score'],b['why'],b['m'],b['conf']=0,'',None,''
for b in bras:
    if b['slug'] in OVERRIDE:
        iid,why=OVERRIDE[b['slug']]
        tgt=next((i for i in imm if i['id']==iid),None)
        if tgt:
            if b['m'] is not None: b['m']['bmatch']=None
            b['m'],b['why'],b['conf'],b['score']=tgt,why,'Alta',99
            tgt['bmatch']=b

# ---- catalogo achatado para o atendente ----
SHORT={'Passione Casa Immobiliare':'Passione Casa','Tempocasa Alessandria':'Tempocasa',
 'Vendocasa Asti Est':'Vendocasa','Franco Nicola Moncalvo':'Franco Nicola',
 'La Cà Nizza Monferrato':'La Cà','Lux Biella':'Lux'}
def m2(s):
    n=re.sub(r'\D','',s or '')
    return int(n) if n else None
TETO=300000
cat=[]
for i in imm:
    if i['nuda'] or i['contract']!='sale' or i['price'] is None: continue
    if i['price']>TETO: continue
    b=i['bmatch']
    cat.append({'id':i['id'],'t':i['title'],'p':i['price'],'ty':i['typology'],'c':i['cat'],
      'm':m2(i['surface']),'r':(i['rooms'] or '').strip(),'city':i['city'],'prov':i['prov'],
      'ag':SHORT[i['agency']],'on':1 if b else 0,
      'ou':b['url'] if b else '','ot':b['title'] if b else '','op':b['price'] if b else None})
cat.sort(key=lambda x:x['p'])
meta={'n':len(cat),'gerado':'07/09/2026','teto':TETO,
 'provs':sorted({x['prov'] for x in cat}),
 'tipos':sorted({x['ty'] for x in cat}),
 'ags':[SHORT[n] for _,n,_ in AG],
 'agurl':{SHORT[n]:'https://www.immobiliare.it/agenzie-immobiliari/%s/'%s for _,n,s in AG}}
json.dump({'meta':meta,'itens':cat},open(os.path.join(BASE,'catalogo.json'),'w',encoding='utf-8'),ensure_ascii=False)
print('catalogo:',len(cat),'itens |',sum(1 for x in cat if x['on']),'com ficha nossa')
from collections import Counter
print('por categoria:',dict(Counter(x['c'] for x in cat)))
print('provincias:',meta['provs'])
print('faixa de preco: €%d a €%d'%(cat[0]['p'],cat[-1]['p']))
