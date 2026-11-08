"""Publish admin-reviewed deals as an Android-compatible Cloudflare Pages feed.
No API key, scraping or automatic approval. Evidence must be manually verified.
"""
import argparse, csv, gzip, hashlib, io, json, os, re, tempfile, time
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = ['dealId','merchant','title','categoryId','cityId','description','sourceUrl','originalPrice','salePrice','currency','expiryTime','verifiedAt','sourceType','approval','evidenceNote','imageUrl','address','latitude','longitude']

def build(csv_path, output, now=None):
    now = int(time.time()*1000) if now is None else now
    deals=[]; seen=set()
    with open(csv_path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []): raise ValueError('CSV template columns missing')
        for line,r in enumerate(reader,2):
            if r['approval'].strip().lower()!='approved': continue
            for k in ['dealId','merchant','title','categoryId','sourceUrl','expiryTime','verifiedAt','evidenceNote']:
                if not r[k].strip(): raise ValueError(f'Row {line}: {k} missing')
            did=r['dealId'].strip()
            if not re.fullmatch(r'[A-Za-z0-9._-]{1,80}',did) or did in seen: raise ValueError(f'Row {line}: invalid/duplicate ID')
            seen.add(did)
            u=urlsplit(r['sourceUrl'].strip())
            if u.scheme!='https' or not u.hostname or u.hostname in ('example.com','localhost'): raise ValueError(f'Row {line}: genuine HTTPS source URL required')
            expiry=int(r['expiryTime']); verified=int(r['verifiedAt'])
            if expiry <= now: continue
            if verified>now+300000 or now-verified>7*86400000: raise ValueError(f'Row {line}: verification too old or future')
            kind=r['sourceType'].strip() or 'merchant'
            if kind not in ('merchant','brand','publisher','affiliate'): raise ValueError(f'Row {line}: invalid source type')
            op=r['originalPrice'].strip(); sp=r['salePrice'].strip()
            if bool(op)!=bool(sp): raise ValueError(f'Row {line}: both prices required')
            original=float(op) if op else None; sale=float(sp) if sp else None
            if original is not None and not original>sale>0: raise ValueError(f'Row {line}: invalid prices')
            def coord(k,lo,hi):
                if not r[k].strip():return None
                v=float(r[k]);
                if not lo<=v<=hi:raise ValueError(f'Row {line}: invalid {k}')
                return v
            deals.append(dict(dealId=did,merchant=r['merchant'].strip(),title=r['title'].strip(),categoryId=r['categoryId'].strip(),cityId=r['cityId'].strip() or None,description=r['description'].strip() or None,sourceUrl=r['sourceUrl'].strip(),originalPrice=original,salePrice=sale,currency=(r['currency'].strip() or 'PKR') if op else None,expiryTime=expiry,verifiedAt=verified,lastUpdated=now,sourceType=kind,status='active',isSponsored=False,imageUrl=r['imageUrl'].strip() or None,address=r['address'].strip() or None,latitude=coord('latitude',-90,90),longitude=coord('longitude',-180,180)))
    if not deals:raise ValueError('No approved active deals: previous feed remains untouched')
    deals.sort(key=lambda x:x['dealId'])
    payload=json.dumps({'schemaVersion':1,'deals':deals},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    buf=io.BytesIO()
    with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as z:z.write(payload)
    compressed=buf.getvalue(); digest=hashlib.sha256(compressed).hexdigest(); version=int(digest[:13],16)
    name=f'community-{digest[:16]}.json.gz'
    output=Path(output); (output/'packs').mkdir(parents=True,exist_ok=True)
    (output/'packs'/name).write_bytes(compressed)
    manifest={'schemaVersion':1,'dataVersion':version,'generatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now/1000)),'packs':[{'id':'community','version':version,'url':'packs/'+name,'sha256':digest,'sizeBytes':len(compressed)}]}
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=output,delete=False) as f:
        json.dump(manifest,f,indent=2); temp=f.name
    os.replace(temp,output/'manifest.json')
    return len(deals)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--csv',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    try:print('Published',build(args.csv,args.out),'approved active deals')
    except (ValueError,OSError) as e:ap.exit(1,f'ERROR: {e}\n')
