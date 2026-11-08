package com.mfistudio.salealert.ui.screens

import android.app.Activity
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.functions.FirebaseFunctions
import com.mfistudio.salealert.merchant.MerchantBilling

/** Existing merchant workflow restored as an authenticated draft -> Play purchase -> moderation flow. */
@Composable
fun MerchantScreen(onClose: () -> Unit) {
    val activity = LocalContext.current as? Activity
    val auth = remember { FirebaseAuth.getInstance() }
    var user by remember { mutableStateOf(auth.currentUser) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var shop by remember { mutableStateOf("") }
    var title by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("Sialkot") }
    var category by remember { mutableStateOf("Clothing") }
    var url by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var selectedProduct by remember { mutableStateOf(MerchantBilling.PRODUCTS.first()) }
    var campaignId by remember { mutableStateOf<String?>(null) }
    var status by remember { mutableStateOf("Create a merchant campaign. Payment never guarantees publication.") }
    val billing = remember(activity) { activity?.let { MerchantBilling(it) { msg -> it.runOnUiThread { status = msg } } } }
    DisposableEffect(billing) {
        billing?.connect()
        onDispose { billing?.close() }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Merchant Promotions", style = MaterialTheme.typography.headlineSmall)
        Text("Verified Google Play payments · Human review before ads go live", style = MaterialTheme.typography.bodySmall)
        TextButton(onClick = onClose) { Text("Back to Profile") }
        if (user == null) {
            OutlinedTextField(email, { email = it }, label = { Text("Email") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(password, { password = it }, label = { Text("Password") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    auth.signInWithEmailAndPassword(email.trim(), password).addOnSuccessListener { user = auth.currentUser; status = "Signed in" }
                        .addOnFailureListener { status = it.localizedMessage ?: "Sign in failed" }
                }) { Text("Sign In") }
                OutlinedButton(onClick = {
                    auth.createUserWithEmailAndPassword(email.trim(), password).addOnSuccessListener { user = auth.currentUser; status = "Account created" }
                        .addOnFailureListener { status = it.localizedMessage ?: "Registration failed" }
                }) { Text("Register") }
            }
        } else {
            Text("Signed in: ${user?.email ?: "Merchant"}")
            OutlinedButton(onClick = { auth.signOut(); user = null; campaignId = null }) { Text("Sign Out") }
            OutlinedTextField(shop, { shop = it }, label = { Text("Shop name") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(title, { title = it }, label = { Text("Promotion title") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(city, { city = it }, label = { Text("City") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(category, { category = it }, label = { Text("Category") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(url, { url = it }, label = { Text("Official shop / offer HTTPS link") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(description, { description = it }, label = { Text("Offer details") }, modifier = Modifier.fillMaxWidth())
            Button(onClick = {
                val data = hashMapOf("shopName" to shop, "title" to title, "city" to city,
                    "category" to category, "sourceUrl" to url, "description" to description)
                FirebaseFunctions.getInstance().getHttpsCallable("createMerchantCampaign").call(data)
                    .addOnSuccessListener { response ->
                        val result = response.getData() as? Map<*, *>
                        campaignId = result?.get("campaignId") as? String
                        status = if (campaignId != null) "Draft created. Choose a Play package." else "Unexpected server response"
                    }.addOnFailureListener { status = "Cannot create campaign: ${it.localizedMessage}" }
            }, enabled = shop.isNotBlank() && title.isNotBlank() && url.startsWith("https://") && campaignId == null) {
                Text("Save Campaign Draft")
            }
            if (campaignId != null) {
                Text("Choose promotion duration", style = MaterialTheme.typography.titleMedium)
                MerchantBilling.PRODUCTS.forEach { product ->
                    Row {
                        RadioButton(selected = selectedProduct == product, onClick = { selectedProduct = product })
                        Text(product.removePrefix("merchant_promo_").uppercase(), modifier = Modifier.padding(top = 12.dp))
                    }
                }
                Button(onClick = { campaignId?.let { billing?.purchase(selectedProduct, it) } }) { Text("Pay with Google Play") }
                Text("Campaign will remain pending until payment verification and moderator approval.")
            }
        }
        Text(status, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyMedium)
    }
}
