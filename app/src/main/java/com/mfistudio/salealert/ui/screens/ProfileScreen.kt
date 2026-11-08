package com.mfistudio.salealert.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import android.content.Intent
import android.net.Uri
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mfistudio.salealert.BuildConfig

@Composable
fun ProfileScreen(
    currentCity: String,
    onCitySelected: (String) -> Unit
) {
    val context = LocalContext.current
    var expanded by remember { mutableStateOf(false) }
    var merchantOpen by remember { mutableStateOf(false) }
    if (merchantOpen) {
        MerchantScreen(onClose = { merchantOpen = false })
        return
    }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "Profile & Settings",
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Selected City", fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(4.dp))
                Text(currentCity, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
                Box {
                    TextButton(onClick = { expanded = true }) { Text("Change city") }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        listOf("Sialkot", "Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta").forEach { city ->
                            DropdownMenuItem(text = { Text(city) }, onClick = {
                                onCitySelected(city)
                                expanded = false
                            })
                        }
                    }
                }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Rate Sale Alert", fontWeight = FontWeight.Bold)
                Text("Share your feedback on Google Play. Reviews are optional and never rewarded.")
                TextButton(onClick = {
                    val market = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=${context.packageName}"))
                    try { context.startActivity(market) } catch (_: Exception) {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=${context.packageName}")))
                    }
                }) { Text("Rate on Google Play") }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Merchant Registration", fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Create your promotion, pay through Google Play, and submit it for review.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Button(onClick = { merchantOpen = true }) { Text("Merchant Dashboard") }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("About Sale Alert", fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(4.dp))
                Text("Version ${BuildConfig.VERSION_NAME} (Build ${BuildConfig.VERSION_CODE})\nPakistan's Premier Shopping & Discount Discovery Platform", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
