# Sale Alert — Google Search → Cloudflare Feed Bridge

یہ **existing Android app کا replacement نہیں**۔ یہ missing central discovery step ہے۔ Search API کے نتائج خودبخود Verified Sales نہیں ہوتے۔

## 1. Google credentials (server only)
Google Programmable Search JSON API کی دستیابی، موجودہ billing اور آپ کے existing API/CX کی validity اپنے Google Cloud Console میں چیک کریں۔ اگر پرانی API بند ہو چکی ہے تو متبادل licensed search provider adapter درکار ہوگا؛ یہ code اس کے بغیر حقیقی results نہیں دے سکتا۔

Windows PowerShell میں (اسی session کے لیے):
```powershell
$env:GOOGLE_CSE_API_KEY="YOUR_EXISTING_KEY"
$env:GOOGLE_CSE_CX="YOUR_EXISTING_SEARCH_ENGINE_ID"
python google_discover.py --out review_candidates.csv --max-calls 10
```

## 2. Approval (ضروری)
`review_candidates.csv` کھولیں۔ ہر deal کی اصل merchant website کھول کر موجودہ offer، exact prices، category، expiry کی تصدیق کریں۔ `expiryTime` اور `verifiedAt` UNIX milliseconds میں، `evidenceNote` میں تصدیق لکھیں، اور صرف حقیقی confirmed deals پر `approval=approved` کریں۔ Search snippet کو خودبخود valid sale نہ سمجھیں۔

## 3. Publish Cloudflare Pages-ready feed
```powershell
python publish_reviewed_csv.py --csv review_candidates.csv --out public_feed
```
`public_feed/manifest.json` اور `public_feed/packs/` کو **ایک ساتھ** Cloudflare Pages پر deploy کریں۔ Cloudflare Pages dashboard میں existing `sale-alert-feed` project کی نئی production deployment کریں۔ Cloudflare خودکار publishing کیلئے deploy token اور CI/CD الگ configure کرنا ہوگا۔

## 4. Android
App میں `dealsCdnBaseUrl=https://sale-alert-feed.pages.dev` پہلے سے set ہے۔ نئے `manifest.json` کی deployment کے بعد Android WorkManager sync/refresh چلائیں۔ موجودہ worker کا schedule ہفتہ وار ہو سکتا ہے، لہٰذا فوری testing کیلئے explicit one-time sync invoke کریں۔

## Operational notes
- Existing crawler `python main.py` نہ چلائیں؛ وہ source authorization پر رک جاتا ہے۔
- یہ bridge Google Search API استعمال کرتا ہے، arbitrary web scraping نہیں۔
- Search API request count `--max-calls` سے محدود ہے؛ per-day/36h persistent quota کیلئے existing `search_budget.py` integrate کریں، یا provider quota Google Console میں لگائیں۔
- Search results empty یا unverified ہوں تو fake offers publish نہ کریں۔
- Cloudflare Pages hosting API crawler execution یا Google API billing خود نہیں سنبھالتا۔
- Google key یا CX فائلوں/Android app میں شامل نہ کریں۔
