// Sliding underline effect for navbar
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelector('.nav-links');
    const links = navLinks.querySelectorAll('a');
    const underline = document.createElement('div');
    
    // Create the sliding underline element
    underline.className = 'sliding-underline';
    navLinks.appendChild(underline);
    
    // Set current page as active
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    let activeLink = null;
    
    links.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === currentPage || 
            (currentPage === 'index.html' && href === 'index.html') ||
            (currentPage === '' && href === 'index.html')) {
            link.classList.add('active');
            activeLink = link;
        }
    });
    
    // Keep underline invisible initially
    underline.style.opacity = '0';
    
    // Add hover effects
    links.forEach(link => {
        link.addEventListener('mouseenter', () => {
            setUnderlinePosition(link);
            underline.style.opacity = '1';
        });
    });
    
    // Hide underline when mouse leaves navbar
    navLinks.addEventListener('mouseleave', () => {
        underline.style.opacity = '0';
    });
    
    function setUnderlinePosition(element) {
        const linkRect = element.getBoundingClientRect();
        const navRect = navLinks.getBoundingClientRect();
        
        underline.style.width = (linkRect.width - 16) + 'px'; // Subtract padding
        underline.style.left = (linkRect.left - navRect.left + 8) + 'px'; // Add padding offset
    }
});

// FAQ Accordion functionality
document.addEventListener('DOMContentLoaded', function() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', () => {
            // Close all other FAQ items
            faqItems.forEach(otherItem => {
                if (otherItem !== item && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });
            
            // Toggle current item
            item.classList.toggle('active');
        });
    });
});

// Post form functionality
document.addEventListener('DOMContentLoaded', function() {
    // File upload handling
    const fileInput = document.getElementById('photo');
    const fileInfo = document.getElementById('fileInfo');
    const allowedUploadExtensions = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'jfif', 'avif'];

    function getFileExtension(fileName) {
        if (!fileName || !fileName.includes('.')) {
            return '';
        }
        return fileName.split('.').pop().toLowerCase();
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const extension = getFileExtension(file.name);
                if (!allowedUploadExtensions.includes(extension)) {
                    fileInfo.textContent = `Unsupported file type (.${extension || 'unknown'}). Use: ${allowedUploadExtensions.join(', ')}`;
                    fileInfo.className = 'file-info error';
                    fileInput.value = '';
                    return;
                }

                fileInfo.className = 'file-info';
                fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            } else {
                fileInfo.textContent = '';
            }
        });
    }
    
    // Contact method handling
    const contactMethod = document.getElementById('contactMethod');
    const phoneGroup = document.getElementById('phoneGroup');
    
    if (contactMethod && phoneGroup) {
        contactMethod.addEventListener('change', function() {
            if (this.value === 'phone' || this.value === 'both') {
                phoneGroup.style.display = 'flex';
                phoneGroup.style.flexDirection = 'column';
                phoneGroup.style.gap = '0.5rem';
            } else {
                phoneGroup.style.display = 'none';
            }
        });
    }
    
    // Form submission handling
    const reportForm = document.getElementById('reportForm');
    
    if (reportForm) {
        reportForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Add loading state to submit button
            const submitBtn = this.querySelector('.submit-btn');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.classList.add('loading');
            submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Submitting...';

            let statusEl = this.querySelector('.report-submit-status');
            if (!statusEl) {
                statusEl = document.createElement('div');
                statusEl.className = 'report-submit-status';
                this.appendChild(statusEl);
            }

            function showReportStatus(message, type) {
                statusEl.textContent = message;
                statusEl.className = `report-submit-status ${type}`;
            }

            showReportStatus('', '');

            // Build multipart payload for photo upload support
            const formData = new FormData(this);
            const authToken = localStorage.getItem('authToken');
            let isSuccessFlow = false;

            if (!authToken) {
                showReportStatus('Please login first, then submit the report with photo.', 'error');
                submitBtn.classList.remove('loading');
                submitBtn.innerHTML = originalText;
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 900);
                return;
            }

            try {
                const response = await apiRequest('/items', {
                    method: 'POST',
                    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
                    body: formData
                });

                const result = await response.json();
                if (!response.ok || !result.success) {
                    if (response.status === 401) {
                        showReportStatus('Session expired. Please login again.', 'error');
                        localStorage.removeItem('authToken');
                        localStorage.removeItem('authUser');
                        setTimeout(() => {
                            window.location.href = 'login.html';
                        }, 900);
                        submitBtn.classList.remove('loading');
                        submitBtn.innerHTML = originalText;
                        return;
                    }

                    showReportStatus(result.message || 'Failed to submit report.', 'error');
                    submitBtn.classList.remove('loading');
                    submitBtn.innerHTML = originalText;
                    return;
                }

                const formContainer = document.querySelector('.form-container');
                formContainer.classList.add('success');
                showReportStatus('Report submitted successfully. Redirecting...', 'success');

                const itemTypeValue = (formData.get('itemType') || '').toLowerCase();
                const redirectPage = itemTypeValue === 'found' ? 'found.html' : 'lost.html';
                isSuccessFlow = true;

                setTimeout(() => {
                    window.location.href = redirectPage;
                }, 450);
            } catch (error) {
                showReportStatus('Could not connect to backend. Please start the API server.', 'error');
            } finally {
                if (!isSuccessFlow) {
                    submitBtn.classList.remove('loading');
                    submitBtn.innerHTML = originalText;
                }
            }
        });
    }
    
    // Form validation
    const formInputs = document.querySelectorAll('.form-input, .form-select, .form-textarea');
    
    formInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            // Remove error state when user starts typing
            if (this.classList.contains('error')) {
                this.classList.remove('error');
            }
        });
    });
    
    function validateField(field) {
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');
        
        // Remove previous validation classes
        field.classList.remove('error', 'success');
        
        if (isRequired && !value) {
            field.classList.add('error');
            return false;
        }
        
        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                field.classList.add('error');
                return false;
            }
        }
        
        // Success state for filled fields
        if (value) {
            field.classList.add('success');
        }
        
        return true;
    }
    
    // Set today's date as default
    const dateInput = document.getElementById('date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
    }
    
    // URL parameter handling for item type
    const urlParams = new URLSearchParams(window.location.search);
    const type = urlParams.get('type');
    const itemTypeSelect = document.getElementById('itemType');
    const postPageTitle = document.querySelector('.page-title');
    const postPageSubtitle = document.querySelector('.page-subtitle');
    const submitBtn = document.querySelector('.submit-btn');
    
    if (type && itemTypeSelect) {
        if (type === 'lost') {
            itemTypeSelect.value = 'lost';
            if (postPageTitle) postPageTitle.textContent = 'Report Lost Item';
            if (postPageSubtitle) postPageSubtitle.textContent = 'Fill in the details below to report an item you lost on campus.';
            if (submitBtn) submitBtn.innerHTML = '<span class="btn-icon">📋</span> Submit Lost Report';
        } else if (type === 'found') {
            itemTypeSelect.value = 'found';
            if (postPageTitle) postPageTitle.textContent = 'Report Found Item';
            if (postPageSubtitle) postPageSubtitle.textContent = 'Fill in the details below to report an item you found on campus.';
            if (submitBtn) submitBtn.innerHTML = '<span class="btn-icon">📋</span> Submit Found Report';
        }
    }
});

// Lost/Found listing pages: fetch and render live items
document.addEventListener('DOMContentLoaded', function() {
    const isFoundPage = document.querySelector('.found-items-page');
    const isLostPage = document.querySelector('.lost-items-page');

    if (!isFoundPage && !isLostPage) {
        return;
    }

    const itemType = isFoundPage ? 'found' : 'lost';
    const itemsGrid = document.getElementById('itemsGrid');
    const itemsCount = document.getElementById('itemsCount');
    const loadInfo = document.getElementById('loadInfo');
    const searchInput = document.querySelector('.search-input-field');
    const searchBtn = document.querySelector('.search-btn');
    const itemsSection = document.querySelector(itemType === 'found' ? '.found-items-grid' : '.lost-items-grid');
    const locationFilter = document.getElementById('location-filter');
    const categoryFilter = document.getElementById('category-filter');
    const dateFilter = document.getElementById('date-filter');
    const clearFiltersBtn = document.querySelector('.clear-filters-btn');
    const cacheKey = `cachedItems:${itemType}`;

    let allItems = [];

    function getCachedItems() {
        try {
            const raw = localStorage.getItem(cacheKey);
            if (!raw) {
                return [];
            }
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            return [];
        }
    }

    function setCachedItems(items) {
        try {
            localStorage.setItem(cacheKey, JSON.stringify(Array.isArray(items) ? items : []));
        } catch (error) {
            // Ignore storage errors; live data rendering should continue.
        }
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getItemEmoji(category) {
        const categoryMap = {
            electronics: '📱',
            clothing: '👕',
            accessories: '🕶️',
            documents: '📄',
            bags: '🎒',
            keys: '🔑'
        };
        return categoryMap[(category || '').toLowerCase()] || '📦';
    }

    function getApiOrigin() {
        try {
            return new URL(getApiBaseUrl()).origin;
        } catch (error) {
            return 'http://127.0.0.1:5000';
        }
    }

    function resolveImageUrl(imageUrl) {
        if (!imageUrl) {
            return '';
        }

        if (/^https?:\/\//i.test(imageUrl)) {
            return imageUrl;
        }

        const normalizedPath = imageUrl.startsWith('/') ? imageUrl : `/${imageUrl}`;
        return `${getApiOrigin()}${normalizedPath}`;
    }

    function getDateLabel(dateValue) {
        if (!dateValue) {
            return itemType === 'found' ? 'Found date not provided' : 'Lost date not provided';
        }

        const itemDate = new Date(dateValue);
        if (Number.isNaN(itemDate.getTime())) {
            return itemType === 'found' ? `Found on ${dateValue}` : `Lost on ${dateValue}`;
        }

        const now = new Date();
        const diffMs = now - itemDate;
        const dayMs = 24 * 60 * 60 * 1000;
        const days = Math.floor(diffMs / dayMs);

        if (days <= 0) {
            return itemType === 'found' ? 'Found today' : 'Lost today';
        }
        if (days === 1) {
            return itemType === 'found' ? 'Found 1 day ago' : 'Lost 1 day ago';
        }
        return itemType === 'found' ? `Found ${days} days ago` : `Lost ${days} days ago`;
    }

    function renderItemCard(item) {
        const normalizedStatus = (item.status || '').toLowerCase();
        const itemEmoji = getItemEmoji(item.category);
        const imageUrl = resolveImageUrl(item.image_url);
        const statusClass = itemType === 'found'
            ? (normalizedStatus === 'resolved' ? 'claimed' : (normalizedStatus === 'pending' ? 'pending' : 'available'))
            : (normalizedStatus === 'pending' ? 'medium' : (normalizedStatus === 'resolved' ? 'low' : 'high'));

        const statusText = itemType === 'found'
            ? (normalizedStatus === 'resolved' ? 'Claimed' : (normalizedStatus === 'pending' ? 'Pending Claim' : 'Available'))
            : (normalizedStatus === 'pending' ? 'Important' : (normalizedStatus === 'resolved' ? 'Normal' : 'Urgent'));

        return `
            <div class="${itemType}-item-card">
                <div class="item-image-container">
                    ${imageUrl ? `<img class="item-photo" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(item.item_name || 'Item photo')}" loading="lazy" onerror="this.remove(); this.parentElement.querySelector('.item-placeholder-image').classList.remove('hidden-fallback');">` : ''}
                    <div class="item-placeholder-image ${imageUrl ? 'hidden-fallback' : ''}">${itemEmoji}</div>
                    <span class="${itemType === 'found' ? 'item-status' : 'item-urgency'} ${statusClass}">${escapeHtml(statusText)}</span>
                </div>
                <div class="item-details">
                    <h3 class="item-name">${escapeHtml(item.item_name || 'Unnamed Item')}</h3>
                    <p class="item-location">📍 ${escapeHtml(item.location_text || 'Location not provided')}</p>
                    <p class="item-date">🕐 ${escapeHtml(getDateLabel(item.date_value))}</p>
                    <p class="item-description">${escapeHtml(item.description_text || 'No description provided.')}</p>
                    <button class="view-details-btn" data-item-id="${item.id}">View Details</button>
                </div>
            </div>
        `;
    }

    function matchesDateFilter(itemDateValue, selectedDateFilter) {
        if (!selectedDateFilter || !itemDateValue) {
            return true;
        }

        const itemDate = new Date(itemDateValue);
        if (Number.isNaN(itemDate.getTime())) {
            return false;
        }

        const now = new Date();
        const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const diffDays = Math.floor((startOfToday - new Date(itemDate.getFullYear(), itemDate.getMonth(), itemDate.getDate())) / (24 * 60 * 60 * 1000));

        if (selectedDateFilter === 'today') {
            return diffDays === 0;
        }
        if (selectedDateFilter === 'week') {
            return diffDays >= 0 && diffDays <= 7;
        }
        if (selectedDateFilter === 'month') {
            return diffDays >= 0 && diffDays <= 30;
        }
        if (selectedDateFilter === 'older') {
            return diffDays > 30;
        }

        return true;
    }

    function applyClientFilters() {
        const searchText = (searchInput ? searchInput.value : '').trim().toLowerCase();
        const selectedLocation = (locationFilter ? locationFilter.value : '').trim().toLowerCase();
        const selectedCategory = (categoryFilter ? categoryFilter.value : '').trim().toLowerCase();
        const selectedDate = (dateFilter ? dateFilter.value : '').trim().toLowerCase();

        const filtered = allItems.filter(item => {
            const name = (item.item_name || '').toLowerCase();
            const description = (item.description_text || '').toLowerCase();
            const location = (item.location_text || '').toLowerCase();
            const category = (item.category || '').toLowerCase();

            const searchMatch = !searchText || name.includes(searchText) || description.includes(searchText) || location.includes(searchText);
            const locationMatch = !selectedLocation || location.includes(selectedLocation.replace('-', ' '));
            const categoryMatch = !selectedCategory || category === selectedCategory;
            const dateMatch = matchesDateFilter(item.date_value, selectedDate);

            return searchMatch && locationMatch && categoryMatch && dateMatch;
        });

        if (!filtered.length) {
            itemsGrid.innerHTML = `<p class="load-info">No ${itemType} items match your filters.</p>`;
            itemsCount.textContent = `Showing 0 of ${allItems.length} ${itemType} items`;
            loadInfo.textContent = 'Showing 0 items';
            return;
        }

        itemsGrid.innerHTML = filtered.map(renderItemCard).join('');
        itemsCount.textContent = `Showing ${filtered.length} of ${allItems.length} ${itemType} items`;
        loadInfo.textContent = `Showing ${filtered.length} items`;
    }

    function scrollToResults() {
        if (!itemsSection) {
            return;
        }

        itemsSection.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }

    async function loadItems() {
        itemsGrid.innerHTML = '<p class="load-info">Loading items...</p>';
        itemsCount.textContent = `Loading ${itemType} items...`;

        const params = new URLSearchParams({
            type: itemType,
            limit: '100',
            offset: '0'
        });

        try {
            const response = await apiRequest(`/items?${params.toString()}`);
            let result = null;

            try {
                result = await response.json();
            } catch (parseError) {
                if (!response.ok) {
                    throw new Error(`Server error (${response.status}).`);
                }
                throw new Error('Received an invalid response from server.');
            }

            if (!response.ok || !result.success) {
                throw new Error(result.message || `Failed to fetch items (${response.status}).`);
            }

            allItems = Array.isArray(result.data) ? result.data : [];
            setCachedItems(allItems);
            applyClientFilters();
        } catch (error) {
            const cachedItems = getCachedItems();
            if (cachedItems.length > 0) {
                allItems = cachedItems;
                applyClientFilters();
                itemsCount.textContent = `Showing cached ${itemType} items (backend offline)`;
                return;
            }

            const errorMessage = (error && error.message) ? error.message : 'Could not load items.';
            itemsGrid.innerHTML = `<p class="load-info">Could not load items: ${escapeHtml(errorMessage)}. Start backend at backend/app.py.</p>`;
            itemsCount.textContent = `Showing 0 ${itemType} items`;
            loadInfo.textContent = 'Showing 0 items';
        }
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', function(event) {
            event.preventDefault();
            applyClientFilters();
            scrollToResults();
        });
    }

    if (searchInput) {
        searchInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                applyClientFilters();
                scrollToResults();
            }
        });
    }

    [locationFilter, categoryFilter, dateFilter].forEach(control => {
        if (control) {
            control.addEventListener('change', applyClientFilters);
        }
    });

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            if (searchInput) searchInput.value = '';
            if (locationFilter) locationFilter.value = '';
            if (categoryFilter) categoryFilter.value = '';
            if (dateFilter) dateFilter.value = '';
            applyClientFilters();
        });
    }

    if (itemsGrid) {
        itemsGrid.addEventListener('click', function(event) {
            const detailsButton = event.target.closest('.view-details-btn');
            if (!detailsButton) {
                return;
            }

            const itemId = detailsButton.getAttribute('data-item-id');
            if (itemId) {
                window.location.href = `../item-detail.html?id=${itemId}`;
            }
        });
    }

    loadItems();
});