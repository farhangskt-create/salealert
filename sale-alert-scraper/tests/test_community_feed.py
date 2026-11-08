import csv, gzip, hashlib, json, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'community'))
from publish_reviewed_csv import FIELDS, build

class CommunityFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.csv=Path(self.tmp.name)/'deals.csv';self.out=Path(self.tmp.name)/'public'
        now=int(time.time()*1000)
        self.row=dict.fromkeys(FIELDS,'')
        self.row.update(dealId='real-1',merchant='Verified Merchant',title='Verified Offer',categoryId='fashion',sourceUrl='https://shop.test/offer',expiryTime=str(now+86400000),verifiedAt=str(now),sourceType='merchant',approval='approved',evidenceNote='Reviewed directly by admin')
    def write(self):
        with self.csv.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerow(self.row)
    def test_valid_pack_matches_android_schema(self):
        self.write();self.assertEqual(build(self.csv,self.out),1)
        m=json.loads((self.out/'manifest.json').read_text());spec=m['packs'][0]
        raw=(self.out/spec['url']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),spec['sha256'])
        deal=json.loads(gzip.decompress(raw))['deals'][0]
        self.assertEqual(deal['status'],'active')
    def test_pending_cannot_publish(self):
        self.row['approval']='pending';self.write()
        with self.assertRaises(ValueError):build(self.csv,self.out)
        self.assertFalse((self.out/'manifest.json').exists())
    def test_expired_cannot_publish(self):
        self.row['expiryTime']=str(int(time.time()*1000)-1);self.write()
        with self.assertRaises(ValueError):build(self.csv,self.out)
    def test_missing_evidence_rejected(self):
        self.row['evidenceNote']='';self.write()
        with self.assertRaises(ValueError):build(self.csv,self.out)
if __name__=='__main__':unittest.main()
