package com.mfistudio.salealert.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.mfistudio.salealert.Deal
import com.mfistudio.salealert.data.local.SaleAlertDatabase
import com.mfistudio.salealert.data.repository.DealRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

/**
 * Robust ViewModel for BachatBazaar managing offline-first deal loading,
 * category filtering (Fashion, Footwear, Groceries, Food), and search queries.
 */
class DealViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = DealRepository(SaleAlertDatabase.getInstance(application))

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _selectedCategory = MutableStateFlow("All")
    val selectedCategory: StateFlow<String> = _selectedCategory.asStateFlow()

    private val _selectedCity = MutableStateFlow("All")
    val selectedCity: StateFlow<String> = _selectedCity.asStateFlow()

    private val _deals = MutableStateFlow<List<Deal>>(emptyList())
    val deals: StateFlow<List<Deal>> = _deals.asStateFlow()

    init {
        loadDeals()
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
        loadDeals()
    }

    fun setCategory(category: String) {
        _selectedCategory.value = category
        loadDeals()
    }

    fun setCity(city: String) {
        _selectedCity.value = city
        loadDeals()
    }

    fun loadDeals() {
        viewModelScope.launch {
            val cat = if (_selectedCategory.value == "All") null else _selectedCategory.value
            val city = if (_selectedCity.value == "All") null else _selectedCity.value
            repository.observeDeals(
                query = _searchQuery.value,
                category = cat,
                city = city,
                isBrand = null
            ).collect { list ->
                _deals.value = list
            }
        }
    }
}
