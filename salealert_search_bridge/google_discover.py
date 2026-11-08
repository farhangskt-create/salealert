"""Google Programmable Search JSON API -> review queue; no fabricated deals.
Loads credentials securely from environment variables or server-side config/credentials.json.
Search results are unverified leads, NEVER auto-published.
"""
import argparse,csv,hashlib,json,os,re,time,urllib.parse,urllib.request
from pathlib import Path

FIELDS=['dealId','merchant','title','categoryId','cityId','description','sourceUrl','originalPrice','salePrice','currency','expiryTime','verifiedAt','sourceType','approval','evidenceNote','imageUrl','address','latitude','longitude']
DEFAULT_QUERIES=['site:daraz.pk sale discount Pakistan','site:khaadi.com sale Pakistan','site:ideas.com.pk sale','site:sapphireonline.pk sale','site:limelight.pk sale','site:outfitters.com.pk sale','site:servis.pk sale','site:stylo.pk sale','site:breakout.com.pk sale','site:bonanzasatrangi.com sale']

def load_credentials():
    key = os.getenv('GOOGLE_CSE_API_KEY')
    cx = os.getenv('GOOGLE_CSE_CX')
    if not key or not cx:
        cred_path = Path(__file__).resolve().parent.parent / 'sale-alert-scraper' / 'config' / 'credentials.json'
        if cred_path.exists():
            try:
                data = json.loads(cred_path.read_text(encoding='utf-8'))
                key = key or data.get('GOOGLE_CSE_API_KEY')
                cx = cx or data.get('GOOGLE_CSE_CX')
            except Exception:
                pass
    return key, cx

def search(query,key,cx):
    params=urllib.parse.urlencode({'key':key,'cx':cx,'q':query,'num':10})
    req=urllib.request.Request('https://www.googleapis.com/customsearch/v1?'+params,headers={'User-Agent':'SaleAlertDiscovery/1.0'})
    with urllib.request.urlopen(req,timeout=25) as response:
        return json.load(response).get('items',[])

def collect(queries,output,key,cx,max_calls=10):
    if not key or not cx:
        key, cx = load_credentials()
    if not key or not cx:
        raise ValueError('Set GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX in environment variables or config/credentials.json; do not put credentials in Android or Cloudflare public files.')
    if not 1<=max_calls<=100: raise ValueError('max_calls must be 1..100')
    seen=set(); rows=[]; calls=0
    for q in queries[:max_calls]:
        items=search(q,key,cx);calls+=1
        for item in items:
            url=item.get('link','').strip(); parsed=urllib.parse.urlsplit(url)
            if parsed.scheme!='https' or not parsed.hostname:continue
            url=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,parsed.path,parsed.query,''))
            if url in seen:continue
            seen.add(url)
            title=re.sub(r'\s+',' ',item.get('title','')).strip()[:180]
            snippet=re.sub(r'\s+',' ',item.get('snippet','')).strip()[:500]
            if not title:continue
            dealid='search-'+hashlib.sha256(url.encode()).hexdigest()[:20]
            rows.append(dict(dealId=dealid,merchant=parsed.hostname,title=title,categoryId='general',cityId='',description=snippet,sourceUrl=url,originalPrice='',salePrice='',currency='',expiryTime='',verifiedAt='',sourceType='merchant',approval='pending',evidenceNote='DISCOVERY ONLY — manually confirm live offer, merchant, prices, expiry and verification time before approval',imageUrl='',address='',latitude='',longitude=''))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    existing={}
    if output.exists():
        with output.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):existing[row['sourceUrl']]=row
    for row in rows:existing.setdefault(row['sourceUrl'],row)
    with output.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(existing.values())
    return calls,len(rows),len(existing)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='review_candidates.csv');p.add_argument('--max-calls',type=int,default=10);p.add_argument('--queries-file');args=p.parse_args()
    queries=[x.strip() for x in Path(args.queries_file).read_text(encoding='utf-8').splitlines() if x.strip() and not x.lstrip().startswith('#')] if args.queries_file else DEFAULT_QUERIES
    try:
        key_val, cx_val = load_credentials()
        calls,found,total=collect(queries,args.out,key_val,cx_val,args.max_calls)
        print(f'Google API requests: {calls}; new search leads: {found}; review queue rows: {total}. NO deals automatically approved or published.')
    except (ValueError,urllib.error.HTTPError,urllib.error.URLError) as e:p.exit(1,f'ERROR: {e}\n')
