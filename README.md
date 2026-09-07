# Catálogo das Parceiras — Brasilità

Página que os atendentes usam durante a ligação para oferecer imóveis das
6 imobiliárias parceiras que ainda não estão no site da Brasilità.

Publicada em: https://claude.ai/code/artifact/0fd10e6b-87ec-429b-8aa8-eb89c1c2c055
(propriedade da conta de aloisiocechinel@gmail.com — outra conta não republica
nesse endereço; publicando daqui, sai uma artifact nova com link próprio.)

## Publicar sem mexer em nada

`cobertura.html` já tem os dados embutidos. Peça ao Claude:

> Publique o arquivo cobertura.html como artifact.

Não inclua `<!doctype>`, `<html>`, `<head>` nem `<body>` — a plataforma embrulha
o arquivo e já injeta charset, viewport e um reset. O `<title>` no topo do
arquivo é o nome da página.

## Mudar só a aparência ou o comportamento

Edite `shell2.html` (o molde, com `__DATA__` onde entram os dados) e regenere:

```bash
python3 -c "
d=open('catalogo.json',encoding='utf-8').read().replace('</','<\\\\/')
h=open('shell2.html',encoding='utf-8').read().replace('__DATA__',d)
open('cobertura.html','w',encoding='utf-8').write(h)"
```

O `replace('</','<\\/')` evita que um `</` dentro do JSON feche a tag `<script>`
antes da hora. Não remova.

## Regenerar os dados

```bash
python3 build.py
```

Só biblioteca padrão, sem dependência para instalar. Lê `dados/agencies/*.tsv`
(um por imobiliária, extraído do immobiliare.it) e `dados/brasilita_items.json`
(catálogo do site), cruza os dois e escreve `catalogo.json`.

### Regras de escopo embutidas no build.py

- teto de **€ 300.000** (`TETO`)
- fora: *nuda proprietà*, aluguel e leilão
- garagem, terreno e comercial ficam no `catalogo.json`, mas a página só mostra
  com a caixinha marcada
- o cruzamento com o site é por cidade + rua + número + preço + m²; o par
  Vendocasa `129488560` é manual (`OVERRIDE`), porque o preço difere: € 19.900
  na imobiliária contra € 44.900 no site, por causa do parcelamento

### Recoletar do immobiliare.it

Os `.tsv` foram extraídos do `__NEXT_DATA__` de cada página de agência. `curl`
toma 403; é preciso navegador. Em cada página (e em `?pag=2`, `?pag=3`…):

```js
const pp=JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps;
const q=(pp.dehydratedState?.queries||[]).find(q=>JSON.stringify(q.queryKey).includes('real-estate-list'));
q.state.data.listing.map(x=>{const r=x.realEstate,p=r.properties[0]||{};
  const s=JSON.stringify(r).toLowerCase();
  return [r.id,r.title,r.price?.value??'',r.contract,p.typology?.name,
   (p.surface||'').replace('.',''),p.rooms,p.location?.city,p.location?.address,
   p.location?.province,s.includes('nuda propriet')?1:0].join('\t');}).join('\n')
```

Colunas do `.tsv`, nessa ordem: id, título, preço, contrato, tipologia,
superfície, cômodos, cidade, endereço, província, nuda (0/1).
`q.state.data.count` diz o total, para saber quantas páginas puxar.

O site da Brasilità é Next.js: `brasilita_items.json` sai do payload RSC de
https://www.brasilita.com/imoveis (a lista `"items":[{"slug"...`).

## Arquivos

| arquivo | o que é |
|---|---|
| `cobertura.html` | página pronta, dados embutidos |
| `shell2.html` | molde, com `__DATA__` |
| `catalogo.json` | 397 imóveis + metadados |
| `build.py` | pipeline de cruzamento e escopo (stdlib, sem dependências) |
| `dados/` | matéria-prima das duas fontes |
