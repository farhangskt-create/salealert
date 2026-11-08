'use strict';
const {onCall, HttpsError} = require('firebase-functions/v2/https');
const admin = require('firebase-admin');
const {google} = require('googleapis');
admin.initializeApp();
const db = admin.firestore();
const PACKAGE = 'com.mfistudio.salealert';
const DURATIONS = {merchant_promo_7d: 7, merchant_promo_15d: 15, merchant_promo_30d: 30};
const requireUser = req => {
  if (!req.auth || !req.auth.uid) throw new HttpsError('unauthenticated', 'Sign in required');
  return req.auth.uid;
};
const validText = (v, max) => typeof v === 'string' && v.trim().length > 0 && v.trim().length <= max;
exports.createMerchantCampaign = onCall(async req => {
  const uid = requireUser(req);
  const {shopName, title, city, category, sourceUrl, description} = req.data || {};
  if (![shopName, title, city, category].every(x => validText(x, 100)) || !validText(sourceUrl, 500))
    throw new HttpsError('invalid-argument', 'Required merchant fields missing');
  let url;
  try { url = new URL(sourceUrl); } catch { throw new HttpsError('invalid-argument', 'Invalid URL'); }
  if (url.protocol !== 'https:') throw new HttpsError('invalid-argument', 'HTTPS merchant URL required');
  const ref = db.collection('merchantCampaigns').doc();
  await ref.set({uid, shopName, title, city, category, sourceUrl, description: String(description || '').slice(0, 1000),
    status: 'awaiting_payment', paymentStatus: 'unpaid', createdAt: admin.firestore.FieldValue.serverTimestamp(),
    isSponsored: true, approved: false});
  return {campaignId: ref.id};
});
exports.verifyMerchantPromotion = onCall(async req => {
  const uid = requireUser(req);
  const {campaignId, productId, purchaseToken} = req.data || {};
  if (!validText(campaignId, 128) || !Object.hasOwn(DURATIONS, productId) || !validText(purchaseToken, 4096))
    throw new HttpsError('invalid-argument', 'Invalid purchase payload');
  const ref = db.collection('merchantCampaigns').doc(campaignId);
  const snap = await ref.get();
  if (!snap.exists || snap.data().uid !== uid) throw new HttpsError('permission-denied', 'Not your campaign');
  const auth = new google.auth.GoogleAuth({scopes: ['https://www.googleapis.com/auth/androidpublisher']});
  const publisher = google.androidpublisher({version: 'v3', auth});
  let purchase;
  try {
    const response = await publisher.purchases.products.get({packageName: PACKAGE, productId, token: purchaseToken});
    purchase = response.data;
  } catch (e) { throw new HttpsError('failed-precondition', 'Play purchase not verifiable'); }
  if (purchase.purchaseState !== 0) throw new HttpsError('failed-precondition', 'Purchase not completed');
  const tokenHash = require('crypto').createHash('sha256').update(purchaseToken).digest('hex');
  const tokenRef = db.collection('merchantPurchaseTokens').doc(tokenHash);
  await db.runTransaction(async tx => {
    const used = await tx.get(tokenRef);
    if (used.exists && used.data().campaignId !== campaignId) throw new HttpsError('already-exists', 'Token already assigned');
    const campaign = await tx.get(ref);
    if (!campaign.exists || campaign.data().uid !== uid) throw new HttpsError('permission-denied', 'Campaign owner changed');
    tx.set(tokenRef, {uid, campaignId, productId, orderId: purchase.orderId || null, verifiedAt: admin.firestore.FieldValue.serverTimestamp()}, {merge: true});
    tx.update(ref, {paymentStatus: 'verified', productId, durationDays: DURATIONS[productId],
      status: 'pending_moderation', approved: false, verifiedPaymentAt: admin.firestore.FieldValue.serverTimestamp()});
  });
  // Consumable one-time product: consume on the trusted backend so the same package
  // can be bought again. A token can only be attached to its original campaign.
  if (purchase.consumptionState !== 1) {
    try { await publisher.purchases.products.consume({packageName: PACKAGE, productId, token: purchaseToken}); }
    catch (e) { throw new HttpsError('unavailable', 'Verified purchase saved, but Play consumption must be retried'); }
  }
  // A moderator must explicitly approve the campaign; never auto-publish.
  return {status: 'pending_moderation'};
});
