// تعريف وظيفة performSearch
function performSearch() {
    const searchTerm = document.getElementById('searchInput').value.trim();

    if (!searchTerm) {
        alert('يرجى إدخال كلمة البحث');
        return;
    }
    
    // إخفاء قائمة الاقتراحات التلقائية عند بدء البحث
    hideAutocomplete();
    
    // منع السلوك الافتراضي للنموذج إذا تم استدعاء الدالة من خلال حدث النموذج
    if (event && event.preventDefault) {
        event.preventDefault();
    }

    document.getElementById('loadingContainer').style.display = 'block';
    document.getElementById('resultsContainer').style.display = 'none';

    // إضافة معلمة لمنع التخزين المؤقت وتحسين الاتصال
    console.log('بدء البحث عن:', searchTerm);
    fetch('/api/search?_=' + new Date().getTime(), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            search_term: searchTerm
        }),
        credentials: 'same-origin'
    })
    .then(response => {
        // حفظ status code قبل تحويل الاستجابة إلى JSON
        const statusCode = response.status;
        return response.json().then(data => ({ data, statusCode }));
    })
    .then(({ data, statusCode }) => {
        document.getElementById('loadingContainer').style.display = 'none';

        if (data.error) {
            alert('خطأ: ' + data.error);
            return;
        }

        displayResults(data);
    })
    .catch(error => {
        console.error('Error during search:', error);
        document.getElementById('loadingContainer').style.display = 'none';
        
        // عرض رسالة خطأ أكثر ودية للمستخدم مع معلومات تشخيصية
        const resultsContainer = document.getElementById('resultsContainer');
        const resultsContent = document.getElementById('resultsContent');
        const resultsTitle = document.getElementById('resultsTitle');
        
        resultsTitle.innerHTML = `<i class="fas fa-exclamation-triangle me-2 text-warning"></i> حدث خطأ أثناء البحث`;
        
        // تحديد نوع الخطأ وعرض رسالة مناسبة
        let errorMessage = '';
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            errorMessage = 'فشل الاتصال بالخادم. يرجى التحقق من اتصالك بالإنترنت.';
        } else if (error.name === 'SyntaxError') {
            errorMessage = 'تم استلام بيانات غير صالحة من الخادم. قد تكون هناك مشكلة في معالجة الطلب.';
        } else {
            errorMessage = 'حدث خطأ غير متوقع أثناء البحث. يرجى المحاولة مرة أخرى.';
        }
        
        resultsContent.innerHTML = `
            <div class="alert alert-danger">
                <p><strong>لم نتمكن من إكمال عملية البحث</strong></p>
                <p>${errorMessage}</p>
                <div class="d-flex gap-2 mt-3">
                    <button class="btn btn-primary" onclick="performSearch()"><i class="fas fa-sync-alt me-2"></i> إعادة المحاولة</button>
                    <button class="btn btn-outline-secondary" onclick="window.location.reload()"><i class="fas fa-redo me-2"></i> تحديث الصفحة</button>
                </div>
            </div>
        `;
        resultsContainer.style.display = 'block';
    });
}

// تعريف وظيفة updateCounts
function updateCounts() {
    // تحديث العدادات في الصفحة
    document.querySelectorAll('.counter-value').forEach(counter => {
        const targetCount = parseFloat(counter.getAttribute('data-count'));
        const prefix = counter.getAttribute('data-prefix') || '';
        const suffix = counter.getAttribute('data-suffix') || '';
        const decimals = parseInt(counter.getAttribute('data-decimals') || '0');
        
        // استخدام قيمة البداية الحالية أو 0
        const startValue = parseFloat(counter.textContent.replace(/[^\d.-]/g, '') || '0');
        
        // حساب الزيادة لكل خطوة
        const increment = (targetCount - startValue) / 30;
        
        // تحديث القيمة تدريجياً
        let currentValue = startValue;
        const timer = setInterval(() => {
            currentValue += increment;
            
            // التحقق مما إذا وصلنا إلى القيمة المستهدفة أو تجاوزناها
            if ((increment >= 0 && currentValue >= targetCount) || 
                (increment < 0 && currentValue <= targetCount)) {
                clearInterval(timer);
                counter.textContent = prefix + targetCount.toFixed(decimals) + suffix;
            } else {
                counter.textContent = prefix + currentValue.toFixed(decimals) + suffix;
            }
        }, 30);
    });
}

// تعريف وظيفة animateCounters
function animateCounters() {
    // تنشيط العدادات
    updateCounts();
}

// تعريف وظيفة escapeHtml
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// تعريف وظيفة hideAutocomplete
function hideAutocomplete() {
    const autocompleteListEl = document.getElementById('autocompleteList');
    if (autocompleteListEl) {
        autocompleteListEl.style.display = 'none';
        autocompleteListEl.innerHTML = '';
    }
}

// تعريف وظيفة displayResults
function displayResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsContent = document.getElementById('resultsContent');
    const suggestionsContainer = document.getElementById('suggestionsContainer');
    const suggestionsList = document.getElementById('suggestionsList');

    // إضافة تأثير ظهور تدريجي للنتائج
    resultsContainer.style.opacity = '0';
    resultsContainer.style.transform = 'translateY(20px)';
    resultsContainer.style.transition = 'opacity 0.5s ease, transform 0.5s ease';

    resultsTitle.innerHTML = `
        <i class="fas fa-list me-2"></i>
        نتائج البحث عن "${escapeHtml(data.search_term)}" (<span class="counter-value" data-count="${data.count}">0</span> نتيجة)
    `;

    animateCounters();

    if (data.count === 0) {
        resultsContent.innerHTML = `
            <div class="text-center p-4">
                <i class="fas fa-search" style="font-size: 3rem; color: #6c757d; opacity: 0.5;"></i>
                <h5 class="mt-3 text-muted">لا توجد نتائج</h5>
                <p class="text-muted">لم يتم العثور على أي أصناف تحتوي على "${escapeHtml(data.search_term)}"</p>
            </div>
        `;
    } else {
        let html = '';
        data.results.forEach((result, index) => {
            const productName = String(result.name || '');
            const quantity = String(result.quantity || 'غير محدد');
            const price = String(result.price || 'غير محدد');

            html += `
                <div class="result-item" data-product-index="${index}">
                    <div>
                        <h6 class="mb-1">${escapeHtml(productName)}</h6>
                        <p class="mb-0 text-muted">الكمية: <strong>${buildAnimatedQuantityMarkup(quantity)}</strong> | السعر: <strong>${escapeHtml(price)}</strong></p>
                    </div>
                    <div class="result-actions">
                        <button class="btn btn-sm btn-success btn-add-to-my-products"
                                onclick="openAddProductModal('${escapeHtml(productName)}', '${escapeHtml(quantity)}', '${escapeHtml(price)}')">
                            <i class="fas fa-plus-circle me-1"></i> إضافة لأصنافي
                        </button>
                        <button class="btn btn-sm btn-warning btn-remember-quantity ms-2"
                                onclick="rememberProductQuantity('${escapeHtml(productName)}', '${escapeHtml(quantity)}', '${escapeHtml(price)}')">
                            <i class="fas fa-bookmark me-1"></i> تذكر العدد
                        </button>
                        <button class="btn btn-sm btn-info btn-request-update ms-2 text-white"
                                onclick="requestUpdateReport('${escapeHtml(productName)}')">
                            <i class="fas fa-clipboard-list me-1"></i> طلب تقرير
                        </button>
                    </div>
                </div>
            `;
        });
        resultsContent.innerHTML = html;
        animateCounters();
    }

    suggestionsList.innerHTML = '';
    if (data.suggestions && data.suggestions.length > 0) {
        suggestionsContainer.style.display = 'block';
        data.suggestions.forEach(suggestion => {
            const suggestionLink = document.createElement('a');
            suggestionLink.href = "#";
            suggestionLink.className = "btn btn-outline-info btn-sm me-2 mb-2 suggestion-btn"; /* Added custom class */
            suggestionLink.textContent = suggestion;
            suggestionLink.onclick = (e) => {
                e.preventDefault();
                document.getElementById('searchInput').value = suggestion;
                performSearch();
            };
            suggestionsList.appendChild(suggestionLink);
        });
    } else {
        suggestionsContainer.style.display = 'none';
    }

    // إظهار النتائج مع تأثير حركي
    resultsContainer.style.display = 'block';

    // تطبيق تأثير الظهور التدريجي بعد عرض النتائج
    setTimeout(() => {
        resultsContainer.style.opacity = '1';
        resultsContainer.style.transform = 'translateY(0)';
    }, 100);

    // فحص الأصناف المتذكرة وعرض الـ hints
    if (typeof checkRememberedProducts === 'function') {
        checkRememberedProducts(data.results);
    }
}

// وظيفة طلب تقرير آخر تحديث
function requestUpdateReport(productName) {
    // التحقق من وجود كائن المستخدم (الذي تم حقنه في search.html)
    if (!window.currentUser) {
        // Fallback for testing if not injected
        console.warn('User info not found, using guest mode');
        window.currentUser = { id: 'guest', name: 'زائر', isPremium: false };
    }

    const user = window.currentUser;
    const userId = user.id;
    const isPremium = user.isPremium;
    const limit = isPremium ? 10 : 2;

    // الحصول على الشهر الحالي
    const date = new Date();
    const currentMonth = date.getFullYear() + '-' + (date.getMonth() + 1).toString().padStart(2, '0');
    
    // مفتاح التخزين في localStorage
    const usageKey = `update_req_usage_${userId}_${currentMonth}`;
    let usageCount = parseInt(localStorage.getItem(usageKey) || '0');

    // التحقق من الرصيد
    if (usageCount >= limit) {
        const msg = isPremium 
            ? 'لقد استهلكت رصيدك الشهري (10 طلبات). سيتم تجديد الرصيد الشهر القادم.'
            : 'لقد استهلكت رصيدك المجاني (طلبان شهرياً). يرجى الاشتراك في الباقة المميزة (Premium) للحصول على 10 طلبات شهرياً.';
        alert(msg);
        return;
    }

    // خصم الرصيد (زيادة العداد)
    usageCount++;
    localStorage.setItem(usageKey, usageCount);

    // تسجيل الإشعار للإدارة
    const notification = {
        id: Date.now(),
        type: 'item_update_request',
        user_name: user.name,
        item_name: productName,
        date: new Date().toLocaleString('ar-EG'),
        timestamp: Date.now(),
        is_read: false
    };

    let notifications = JSON.parse(localStorage.getItem('admin_item_requests') || '[]');
    notifications.push(notification);
    localStorage.setItem('admin_item_requests', JSON.stringify(notifications));

    // رسالة تأكيد للمستخدم
    alert('سيتم الرد على سيادتكم عن طريق نظام المراسلات الداخلى بخصوص الصنف المذكور (' + productName + ')');
}
