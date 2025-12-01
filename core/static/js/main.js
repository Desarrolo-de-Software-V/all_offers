// ==================== CONFIGURACIÓN GLOBAL ====================
const API_BASE = window.location.origin;

// ==================== CSRF TOKEN ====================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// ==================== LIKES ====================
function toggleLike(offerId) {
    fetch(`/api/offers/${offerId}/like/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        const likeBtn = document.querySelector(`[data-offer-id="${offerId}"]`);
        const likeCount = document.querySelector(`#like-count-${offerId}`);
        
        if (likeBtn) {
            if (data.liked) {
                likeBtn.classList.add('liked');
                likeBtn.innerHTML = '<i class="fas fa-heart"></i>';
            } else {
                likeBtn.classList.remove('liked');
                likeBtn.innerHTML = '<i class="far fa-heart"></i>';
            }
        }
        
        if (likeCount) {
            likeCount.textContent = data.likes_count;
        }
    })
    .catch(error => console.error('Error:', error));
}

// ==================== SEGUIR EMPRESA ====================
function toggleFollowBusiness(businessId) {
    fetch(`/api/business/${businessId}/follow/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        const followBtn = document.querySelector(`#follow-btn-${businessId}`);
        const followCount = document.querySelector(`#followers-count-${businessId}`);
        
        if (followBtn) {
            if (data.following) {
                followBtn.innerHTML = '<i class="fas fa-check"></i> Siguiendo';
                followBtn.classList.remove('btn-primary');
                followBtn.classList.add('btn-secondary');
            } else {
                followBtn.innerHTML = '<i class="fas fa-plus"></i> Seguir';
                followBtn.classList.remove('btn-secondary');
                followBtn.classList.add('btn-primary');
            }
        }
        
        if (followCount) {
            followCount.textContent = data.followers_count;
        }
    })
    .catch(error => console.error('Error:', error));
}

// ==================== SEGUIR CATEGORÍA ====================
function toggleFollowCategory(categoryId) {
    fetch(`/api/category/${categoryId}/follow/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        const followBtn = document.querySelector(`#follow-cat-${categoryId}`);
        
        if (followBtn) {
            if (data.following) {
                followBtn.innerHTML = '<i class="fas fa-check"></i> Siguiendo';
                followBtn.classList.remove('btn-outline-primary');
                followBtn.classList.add('btn-primary');
            } else {
                followBtn.innerHTML = '<i class="fas fa-plus"></i> Seguir';
                followBtn.classList.remove('btn-primary');
                followBtn.classList.add('btn-outline-primary');
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// ==================== NOTIFICACIONES ====================
function updateNotificationsCount() {
    fetch('/api/notifications/unread-count/')
        .then(response => response.json())
        .then(data => {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count > 99 ? '99+' : data.count;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('Error:', error));
}

function markNotificationRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        },
    })
    .then(() => {
        updateNotificationsCount();
    })
    .catch(error => console.error('Error:', error));
}

// ==================== BÚSQUEDA ====================
let searchTimeout;
function initializeSearch() {
    const searchInput = document.querySelector('#search-input');
    const searchResults = document.querySelector('#search-results');
    
    if (!searchInput || !searchResults) return;
    
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            searchResults.innerHTML = '';
            searchResults.style.display = 'none';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            fetch(`/api/search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.results.length > 0) {
                        let html = '<div class="list-group">';
                        data.results.forEach(result => {
                            const icon = result.type === 'offer' ? 'tag' : 'store';
                            html += `
                                <a href="${result.url}" class="list-group-item list-group-item-action">
                                    <i class="fas fa-${icon} me-2"></i>
                                    <strong>${result.title}</strong>
                                    ${result.business ? `<br><small class="text-muted">${result.business}</small>` : ''}
                                    ${result.description ? `<br><small class="text-muted">${result.description}</small>` : ''}
                                </a>
                            `;
                        });
                        html += '</div>';
                        searchResults.innerHTML = html;
                        searchResults.style.display = 'block';
                    } else {
                        searchResults.innerHTML = '<div class="p-3 text-muted">No se encontraron resultados</div>';
                        searchResults.style.display = 'block';
                    }
                })
                .catch(error => console.error('Error:', error));
        }, 300);
    });
    
    // Cerrar resultados al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
}

// ==================== SIDEBAR ====================
function initializeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    const dashboardContent = document.querySelector('.dashboard-content');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            if (dashboardContent) {
                dashboardContent.classList.toggle('sidebar-collapsed');
            }
            
            // Guardar estado en localStorage
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });
    }
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('mobile-open');
            sidebarOverlay.classList.toggle('active');
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('active');
        });
    }
    
    // Restaurar estado del sidebar
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarCollapsed && sidebar) {
        sidebar.classList.add('collapsed');
        if (dashboardContent) {
            dashboardContent.classList.add('sidebar-collapsed');
        }
    }
}

// ==================== CONFIRMACIONES ====================
function confirmDelete(message) {
    return confirm(message || '¿Estás seguro de que quieres eliminar esto?');
}

// ==================== CONTADOR DE TIEMPO ====================
function updateExpireCountdowns() {
    document.querySelectorAll('[data-expires-at]').forEach(element => {
        const expiresAt = new Date(element.dataset.expiresAt);
        const now = new Date();
        const diff = expiresAt - now;
        
        if (diff <= 0) {
            element.textContent = 'Expirada';
            element.classList.add('text-danger');
        } else {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            
            if (days > 0) {
                element.textContent = `${days}d ${hours}h`;
            } else {
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                element.textContent = `${hours}h ${minutes}m`;
            }
            
            if (days < 1) {
                element.classList.add('text-warning');
            }
        }
    });
}

// ==================== TOOLTIPS Y POPOVERS ====================
function initializeBootstrapComponents() {
    // Inicializar tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// ==================== ANIMACIONES AL SCROLL ====================
function initializeScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.card, .stat-card').forEach(el => {
        observer.observe(el);
    });
}

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeSidebar();
    initializeSearch();
    initializeBootstrapComponents();
    initializeScrollAnimations();
    
    // Actualizar notificaciones cada 30 segundos
    if (document.querySelector('.notification-badge')) {
        updateNotificationsCount();
        setInterval(updateNotificationsCount, 30000);
    }
    
    // Actualizar contadores de tiempo cada minuto
    if (document.querySelector('[data-expires-at]')) {
        updateExpireCountdowns();
        setInterval(updateExpireCountdowns, 60000);
    }
    
    // Mensajes flash auto-dismiss
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    });
});

// ==================== EXPORTAR FUNCIONES ====================
window.toggleLike = toggleLike;
window.toggleFollowBusiness = toggleFollowBusiness;
window.toggleFollowCategory = toggleFollowCategory;
window.markNotificationRead = markNotificationRead;
window.confirmDelete = confirmDelete;