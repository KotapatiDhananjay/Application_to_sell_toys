/**
 * ToyVerse - Main Application Logic
 * Vanilla JavaScript Single Page Application
 */

// ============================================================================
// Configuration & State
// ============================================================================

const CONFIG = {
  // Try port 8000 by default (standard Django runserver port)
  API_BASE_URL: window.location.port === '8000' 
    ? window.location.origin 
    : 'http://127.0.0.1:8000',
  FREE_SHIPPING_THRESHOLD: 50.00,
  SHIPPING_FEE: 5.99,
  CURRENCY: '$',
};

const state = {
  categories: [],
  products: [],
  totalProductsCount: 0,
  nextPageUrl: null,
  activeCategory: '',
  searchQuery: '',
  quickFilter: 'all',
  filters: {
    min_price: '',
    max_price: '',
    age: '',
    in_stock: false,
    on_sale: false,
    featured: false,
  },
  ordering: '-created_at',
  currentPage: 1,
  isLoading: false,

  // Stored in localStorage
  cart: JSON.parse(localStorage.getItem('toyverse_cart') || '[]'),
  wishlist: JSON.parse(localStorage.getItem('toyverse_wishlist') || '[]'),
  user: JSON.parse(localStorage.getItem('toyverse_user') || 'null'),
  token: localStorage.getItem('toyverse_token') || null,
  refreshToken: localStorage.getItem('toyverse_refresh') || null,
  addresses: [],

  // Active modal
  currentProductDetail: null,
};

// ============================================================================
// API Helper & Client
// ============================================================================

async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  try {
    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401 && state.refreshToken) {
      // Attempt token refresh
      const refreshed = await refreshAuthToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${state.token}`;
        return fetch(url, { ...options, headers }).then(r => r.json());
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(JSON.stringify(errorData));
    }

    return await response.json();
  } catch (err) {
    console.warn(`API request to ${endpoint} failed:`, err.message);
    throw err;
  }
}

async function refreshAuthToken() {
  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: state.refreshToken })
    });
    if (res.ok) {
      const data = await res.json();
      state.token = data.access;
      localStorage.setItem('toyverse_token', state.token);
      return true;
    }
  } catch (e) {
    console.error('Refresh token failed:', e);
  }
  logoutUser();
  return false;
}

// Fallback Mock Data in case backend is not yet started by user
const FALLBACK_PRODUCTS = [
  {
    id: 1,
    name: 'Coding Robot Starter Kit',
    slug: 'coding-robot-starter-kit',
    sku: 'ROB-001',
    brand: 'RoboKids',
    short_description: 'Programmable STEM robot with light sensors and obstacle avoidance.',
    category: { id: 1, name: 'STEM & Learning', slug: 'stem-learning' },
    price: '79.99',
    discount_percent: 15,
    discounted_price: '67.99',
    has_discount: true,
    stock: 14,
    in_stock: true,
    stock_status: 'in_stock',
    age_min: 6,
    age_max: 12,
    age_range: '6-12 years',
    is_featured: true,
    image: '/media/products/coding-robot-starter-kit.png',
    created_at: new Date().toISOString()
  },
  {
    id: 2,
    name: 'Marble Run Construction Set',
    slug: 'marble-run-construction-set',
    sku: 'BLD-004',
    brand: 'BrickWorks',
    short_description: '85-piece colorful marble maze with vortex chutes and gears.',
    category: { id: 2, name: 'Building Toys', slug: 'building-toys' },
    price: '36.99',
    discount_percent: 0,
    discounted_price: '36.99',
    has_discount: false,
    stock: 33,
    in_stock: true,
    stock_status: 'in_stock',
    age_min: 4,
    age_max: 10,
    age_range: '4-10 years',
    is_featured: true,
    image: '/media/products/marble-run-construction-set.png',
    created_at: new Date().toISOString()
  },
  {
    id: 3,
    name: 'Magnetic Tile Builder Set (60 Pcs)',
    slug: 'magnetic-tile-builder-set-60-pcs',
    sku: 'BLD-002',
    brand: 'MagnaPlay',
    short_description: 'Vibrant 3D magnetic building blocks for architectural imagination.',
    category: { id: 2, name: 'Building Toys', slug: 'building-toys' },
    price: '49.99',
    discount_percent: 20,
    discounted_price: '39.99',
    has_discount: true,
    stock: 8,
    in_stock: true,
    stock_status: 'in_stock',
    age_min: 3,
    age_max: 99,
    age_range: '3+ years',
    is_featured: true,
    image: '/media/products/magnetic-tile-builder-set-60-pcs.png',
    created_at: new Date().toISOString()
  },
  {
    id: 4,
    name: 'Galaxy Defender Action Figure',
    slug: 'galaxy-defender-figure',
    sku: 'ACT-001',
    brand: 'StarForce',
    short_description: 'Articulated space guardian with laser blaster and LED visor.',
    category: { id: 3, name: 'Action Figures', slug: 'action-figures' },
    price: '24.99',
    discount_percent: 0,
    discounted_price: '24.99',
    has_discount: false,
    stock: 4,
    in_stock: true,
    stock_status: 'low_stock',
    age_min: 5,
    age_max: 12,
    age_range: '5-12 years',
    is_featured: false,
    image: '/media/products/galaxy-defender-figure.png',
    created_at: new Date().toISOString()
  },
  {
    id: 5,
    name: 'Treasure Island Strategy Game',
    slug: 'treasure-island-strategy-game',
    sku: 'BRD-001',
    brand: 'FunQuest',
    short_description: 'Exciting cooperative treasure hunt adventure for 2-4 players.',
    category: { id: 4, name: 'Board Games & Puzzles', slug: 'board-games-puzzles' },
    price: '32.50',
    discount_percent: 10,
    discounted_price: '29.25',
    has_discount: true,
    stock: 22,
    in_stock: true,
    stock_status: 'in_stock',
    age_min: 7,
    age_max: 99,
    age_range: '7+ years',
    is_featured: true,
    image: '/media/products/treasure-island-strategy-game.png',
    created_at: new Date().toISOString()
  },
  {
    id: 6,
    name: 'Dream Dollhouse Playset',
    slug: 'dream-dollhouse',
    sku: 'DOL-001',
    brand: 'PetitePalace',
    short_description: '3-story furnished wooden mansion with 14 detailed accessories.',
    category: { id: 5, name: 'Dolls & Playsets', slug: 'dolls-playsets' },
    price: '89.00',
    discount_percent: 0,
    discounted_price: '89.00',
    has_discount: false,
    stock: 0,
    in_stock: false,
    stock_status: 'out_of_stock',
    age_min: 3,
    age_max: 9,
    age_range: '3-9 years',
    is_featured: false,
    image: '/media/products/dream-dollhouse.png',
    created_at: new Date().toISOString()
  }
];

// ============================================================================
// Notification / Toast System
// ============================================================================

function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconMap = {
    success: '🎉',
    error: '⚠️',
    info: '✨',
  };

  toast.innerHTML = `
    <span style="font-size: 1.2rem;">${iconMap[type] || '✨'}</span>
    <span style="flex: 1;">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'all 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(15px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ============================================================================
// Data Fetching: Categories & Products
// ============================================================================

async function fetchCategories() {
  try {
    const data = await apiRequest('/api/categories/');
    state.categories = Array.isArray(data) ? data : (data.results || []);
    renderCategoryChips();
  } catch (err) {
    console.info('Backend categories not reachable, using fallback.');
    state.categories = [
      { id: 1, name: 'Building Toys', slug: 'building-toys', product_count: 8 },
      { id: 2, name: 'STEM & Learning', slug: 'stem-learning', product_count: 5 },
      { id: 3, name: 'Action Figures', slug: 'action-figures', product_count: 4 },
      { id: 4, name: 'Board Games & Puzzles', slug: 'board-games-puzzles', product_count: 4 },
      { id: 5, name: 'Dolls & Playsets', slug: 'dolls-playsets', product_count: 4 },
    ];
    renderCategoryChips();
  }
}

async function fetchProducts(page = 1, append = false) {
  state.isLoading = true;
  state.currentPage = page;

  if (!append) {
    renderProductGridSkeleton();
  }

  // Construct Query String
  const params = new URLSearchParams();
  if (page > 1) params.append('page', page);
  if (state.activeCategory) params.append('category', state.activeCategory);
  if (state.searchQuery.trim()) params.append('search', state.searchQuery.trim());
  if (state.ordering) params.append('ordering', state.ordering);

  // Filter query parameters
  if (state.filters.min_price) params.append('min_price', state.filters.min_price);
  if (state.filters.max_price) params.append('max_price', state.filters.max_price);
  if (state.filters.age) params.append('age', state.filters.age);
  if (state.filters.in_stock) params.append('in_stock', 'true');
  if (state.filters.on_sale) params.append('on_sale', 'true');
  if (state.filters.featured) params.append('featured', 'true');

  try {
    const data = await apiRequest(`/api/products/?${params.toString()}`);
    const results = data.results || data;
    state.totalProductsCount = data.count !== undefined ? data.count : results.length;
    state.nextPageUrl = data.next || null;

    if (append) {
      state.products = [...state.products, ...results];
    } else {
      state.products = results;
    }

    renderProductsGrid();
    renderActiveFilterBadges();
    updatePaginationControls();
    updateTotalCountLabel();
  } catch (err) {
    console.info('Backend products fetch fallback applied.');
    let filtered = [...FALLBACK_PRODUCTS];

    if (state.activeCategory) {
      filtered = filtered.filter(p => p.category?.slug === state.activeCategory);
    }
    if (state.searchQuery.trim()) {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(q) || 
        p.short_description.toLowerCase().includes(q) ||
        p.brand.toLowerCase().includes(q)
      );
    }
    if (state.filters.on_sale) {
      filtered = filtered.filter(p => p.has_discount);
    }
    if (state.filters.featured) {
      filtered = filtered.filter(p => p.is_featured);
    }
    if (state.filters.in_stock) {
      filtered = filtered.filter(p => p.in_stock);
    }
    if (state.filters.min_price) {
      filtered = filtered.filter(p => parseFloat(p.discounted_price) >= parseFloat(state.filters.min_price));
    }
    if (state.filters.max_price) {
      filtered = filtered.filter(p => parseFloat(p.discounted_price) <= parseFloat(state.filters.max_price));
    }

    state.products = filtered;
    state.totalProductsCount = filtered.length;
    state.nextPageUrl = null;

    renderProductsGrid();
    renderActiveFilterBadges();
    updatePaginationControls();
    updateTotalCountLabel();
  } finally {
    state.isLoading = false;
  }
}

// ============================================================================
// Render Functions
// ============================================================================

function renderCategoryChips() {
  const container = document.getElementById('categoriesScrollList');
  if (!container) return;

  const totalAllCount = state.categories.reduce((sum, cat) => sum + (cat.product_count || 0), 0) || 25;
  document.getElementById('totalProductCount').textContent = totalAllCount;

  // Keep first "All Toys" button
  let html = `
    <button class="category-chip ${state.activeCategory === '' ? 'active' : ''}" data-category="">
      <span>🌟 All Toys</span>
      <span class="chip-count">${totalAllCount}</span>
    </button>
  `;

  state.categories.forEach(cat => {
    const isActive = state.activeCategory === cat.slug ? 'active' : '';
    html += `
      <button class="category-chip ${isActive}" data-category="${cat.slug}">
        <span>${cat.name}</span>
        ${cat.product_count !== undefined ? `<span class="chip-count">${cat.product_count}</span>` : ''}
      </button>
    `;
  });

  container.innerHTML = html;

  // Add event listeners to category buttons
  container.querySelectorAll('.category-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const slug = btn.getAttribute('data-category');
      setActiveCategory(slug);
    });
  });
}

function setActiveCategory(slug) {
  state.activeCategory = slug;
  renderCategoryChips();
  
  // Update section title
  const heading = document.getElementById('catalogHeading');
  const subtitle = document.getElementById('catalogSubtitle');
  if (slug === '') {
    heading.textContent = 'Explore All Toys';
    subtitle.textContent = 'Showing all magical toys, building sets, and STEM kits';
  } else {
    const cat = state.categories.find(c => c.slug === slug);
    heading.textContent = cat ? cat.name : 'Category Collection';
    subtitle.textContent = cat?.description || `Discover curated ${heading.textContent} for young builders`;
  }

  fetchProducts(1);
}

function renderProductGridSkeleton() {
  const grid = document.getElementById('productGrid');
  if (!grid) return;

  grid.innerHTML = `
    <div class="state-container">
      <div class="spinner"></div>
      <h3>Finding the best toys for you...</h3>
      <p>Loading magical adventures from our inventory!</p>
    </div>
  `;
}

function renderProductsGrid() {
  const grid = document.getElementById('productGrid');
  if (!grid) return;

  if (state.products.length === 0) {
    grid.innerHTML = `
      <div class="state-container">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <h3>No toys found matching your search</h3>
        <p>Try clearing some filters or searching for something else like "robot", "lego", or "doll".</p>
        <button type="button" class="btn-hero-secondary" onclick="resetAllFilters()">Reset All Filters</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = state.products.map(prod => createProductCardHtml(prod)).join('');

  // Attach card event listeners
  grid.querySelectorAll('.product-card').forEach(card => {
    const slug = card.getAttribute('data-slug');
    const prod = state.products.find(p => p.slug === slug);
    if (!prod) return;

    // Click card title or image to open details modal
    card.querySelectorAll('.card-title, .card-media-wrapper').forEach(el => {
      el.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-wishlist-card') && !e.target.closest('.btn-add-cart')) {
          openProductDetailModal(slug);
        }
      });
    });

    // Wishlist toggle
    const wishlistBtn = card.querySelector('.btn-wishlist-card');
    if (wishlistBtn) {
      wishlistBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleWishlist(prod);
      });
    }

    // Add to cart
    const addCartBtn = card.querySelector('.btn-add-cart');
    if (addCartBtn) {
      addCartBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        addToCart(prod, 1);
      });
    }
  });
}

function resolveProductImage(imgUrl) {
  if (!imgUrl) return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 24 24" fill="none" stroke="%23CBD5E1" stroke-width="1"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>';
  if (imgUrl.startsWith('http')) return imgUrl;
  if (imgUrl.startsWith('/')) return `${CONFIG.API_BASE_URL}${imgUrl}`;
  return `${CONFIG.API_BASE_URL}/${imgUrl}`;
}

function createProductCardHtml(prod) {
  const isWishlisted = state.wishlist.some(w => w.id === prod.id);
  const formattedDiscountPrice = `${CONFIG.CURRENCY}${parseFloat(prod.discounted_price || prod.price).toFixed(2)}`;
  const formattedOriginalPrice = `${CONFIG.CURRENCY}${parseFloat(prod.price).toFixed(2)}`;
  const imgSrc = resolveProductImage(prod.image);

  let stockStatusLabel = 'In Stock';
  let stockClass = 'in_stock';
  if (!prod.in_stock || prod.stock <= 0) {
    stockStatusLabel = 'Out of Stock';
    stockClass = 'out_of_stock';
  } else if (prod.stock_status === 'low_stock' || prod.stock <= 5) {
    stockStatusLabel = `Low Stock (${prod.stock} left)`;
    stockClass = 'low_stock';
  }

  return `
    <article class="product-card" data-slug="${prod.slug}" data-id="${prod.id}">
      <div class="card-media-wrapper">
        <div class="card-badges">
          ${prod.has_discount ? `<span class="badge badge-discount">-${prod.discount_percent}% OFF</span>` : ''}
          ${prod.is_featured ? `<span class="badge badge-featured">Featured</span>` : ''}
          ${prod.age_range ? `<span class="badge badge-age">${prod.age_range}</span>` : ''}
        </div>

        <button type="button" class="btn-wishlist-card ${isWishlisted ? 'active' : ''}" title="Add to Wishlist" aria-label="Toggle Wishlist">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
          </svg>
        </button>

        <img src="${imgSrc}" alt="${prod.name}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'%23CBD5E1\\' stroke-width=\\'1\\'><rect width=\\'18\\' height=\\'18\\' x=\\'3\\' y=\\'3\\' rx=\\'2\\'/><circle cx=\\'9\\' cy=\\'9\\' r=\\'2\\'/><path d=\\'m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21\\'/></svg>'">
      </div>

      <div class="card-body">
        <div class="card-category-brand">
          <span class="card-category">${prod.category?.name || 'Toys'}</span>
          <span>${prod.brand || ''}</span>
        </div>

        <h3 class="card-title" title="${prod.name}">${prod.name}</h3>
        <p class="card-desc">${prod.short_description || ''}</p>

        <div class="stock-status-pill ${stockClass}">
          <span class="status-dot"></span>
          <span>${stockStatusLabel}</span>
        </div>

        <div class="card-footer">
          <div class="price-box">
            <span class="final-price">${formattedDiscountPrice}</span>
            ${prod.has_discount ? `<span class="original-price">${formattedOriginalPrice}</span>` : ''}
          </div>

          <button type="button" class="btn-add-cart" ${!prod.in_stock ? 'disabled' : ''} title="${prod.in_stock ? 'Add to Cart' : 'Out of Stock'}" aria-label="Add to cart">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>
      </div>
    </article>
  `;
}

function renderActiveFilterBadges() {
  const container = document.getElementById('activeFiltersBar');
  if (!container) return;

  const badges = [];

  if (state.searchQuery) {
    badges.push(`Search: "${state.searchQuery}" <button onclick="clearSearchFilter()">&times;</button>`);
  }
  if (state.filters.min_price || state.filters.max_price) {
    badges.push(`Price: $${state.filters.min_price || '0'} - $${state.filters.max_price || '∞'} <button onclick="clearPriceFilter()">&times;</button>`);
  }
  if (state.filters.age) {
    badges.push(`Age: ${state.filters.age}+ yrs <button onclick="clearAgeFilter()">&times;</button>`);
  }
  if (state.filters.on_sale) {
    badges.push(`On Sale <button onclick="toggleFilter('on_sale', false)">&times;</button>`);
  }
  if (state.filters.featured) {
    badges.push(`Featured <button onclick="toggleFilter('featured', false)">&times;</button>`);
  }
  if (state.filters.in_stock) {
    badges.push(`In Stock <button onclick="toggleFilter('in_stock', false)">&times;</button>`);
  }

  if (badges.length > 0) {
    container.style.display = 'flex';
    container.innerHTML = `
      <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted);">Active Filters:</span>
      ${badges.map(b => `<span class="active-filter-badge">${b}</span>`).join('')}
      <button type="button" class="btn-clear-all" onclick="resetAllFilters()">Clear All</button>
    `;
  } else {
    container.style.display = 'none';
  }
}

function updatePaginationControls() {
  const container = document.getElementById('paginationContainer');
  if (!container) return;

  if (state.nextPageUrl) {
    container.style.display = 'block';
  } else {
    container.style.display = 'none';
  }
}

function updateTotalCountLabel() {
  const label = document.getElementById('catalogSubtitle');
  if (label && state.totalProductsCount !== undefined) {
    label.textContent = `Showing ${state.products.length} of ${state.totalProductsCount} toys available`;
  }
}

// ============================================================================
// Product Detail Modal
// ============================================================================

async function openProductDetailModal(slug) {
  const modal = document.getElementById('productDetailModal');
  const content = document.getElementById('productDetailContent');
  if (!modal || !content) return;

  modal.classList.add('open');
  content.innerHTML = `
    <div style="text-align: center; padding: 4rem 1rem;">
      <div class="spinner"></div>
      <p>Loading toy details...</p>
    </div>
  `;

  let prod = null;
  try {
    prod = await apiRequest(`/api/products/${slug}/`);
  } catch (e) {
    prod = state.products.find(p => p.slug === slug);
  }

  if (!prod) {
    content.innerHTML = `<p>Failed to load product details. Please try again.</p>`;
    return;
  }

  state.currentProductDetail = prod;

  const images = prod.images && prod.images.length > 0 
    ? prod.images.map(img => resolveProductImage(img.url))
    : [resolveProductImage(prod.image)];

  const formattedDiscountPrice = `${CONFIG.CURRENCY}${parseFloat(prod.discounted_price || prod.price).toFixed(2)}`;
  const formattedOriginalPrice = `${CONFIG.CURRENCY}${parseFloat(prod.price).toFixed(2)}`;

  let stockStatusLabel = 'In Stock';
  let stockColor = 'var(--success)';
  if (!prod.in_stock || prod.stock <= 0) {
    stockStatusLabel = 'Out of Stock';
    stockColor = 'var(--danger)';
  } else if (prod.stock_status === 'low_stock' || prod.stock <= 5) {
    stockStatusLabel = `Only ${prod.stock} units remaining!`;
    stockColor = 'var(--warning)';
  }

  content.innerHTML = `
    <div class="detail-layout">
      <!-- Gallery Column -->
      <div class="detail-gallery">
        <div class="detail-main-image">
          <img id="detailMainImg" src="${images[0]}" alt="${prod.name}">
        </div>
        ${images.length > 1 ? `
          <div class="detail-thumbnails">
            ${images.map((img, idx) => `
              <div class="thumbnail-item ${idx === 0 ? 'active' : ''}" data-src="${img}">
                <img src="${img}" alt="Thumbnail ${idx + 1}">
              </div>
            `).join('')}
          </div>
        ` : ''}
      </div>

      <!-- Info Column -->
      <div class="detail-info">
        <div class="detail-meta-row">
          <span>${prod.category?.name || 'Toys'}</span>
          <span>•</span>
          <span>SKU: ${prod.sku || 'N/A'}</span>
          ${prod.brand ? `<span>•</span><span>Brand: ${prod.brand}</span>` : ''}
        </div>

        <h2 class="detail-title">${prod.name}</h2>

        <div class="detail-price-row">
          <span class="final-price">${formattedDiscountPrice}</span>
          ${prod.has_discount ? `<span class="original-price" style="font-size: 1.1rem;">${formattedOriginalPrice}</span>` : ''}
          ${prod.has_discount ? `<span class="badge badge-discount">Save ${prod.discount_percent}%</span>` : ''}
        </div>

        <div class="detail-attributes">
          <div class="attr-item">
            <span>Recommended Age</span>
            <span>${prod.age_range || (prod.age_min ? `${prod.age_min}+ years` : 'All ages')}</span>
          </div>
          <div class="attr-item">
            <span>Availability</span>
            <span style="color: ${stockColor}; font-weight: 700;">${stockStatusLabel}</span>
          </div>
        </div>

        <div class="detail-description">
          <p>${prod.description || prod.short_description || 'A wonderfully engaging toy designed for fun, play, and exploration.'}</p>
        </div>

        <div class="detail-actions-row">
          <div class="quantity-control">
            <button type="button" class="qty-btn" id="detailQtyMinus">-</button>
            <span class="qty-display" id="detailQtyVal">1</span>
            <button type="button" class="qty-btn" id="detailQtyPlus">+</button>
          </div>

          <button type="button" class="btn-add-detail" id="detailAddCartBtn" ${!prod.in_stock ? 'disabled' : ''}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="8" cy="21" r="1"/>
              <circle cx="19" cy="21" r="1"/>
              <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>
            </svg>
            <span>${prod.in_stock ? 'Add to Cart' : 'Out of Stock'}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Related Products -->
    ${prod.related_products && prod.related_products.length > 0 ? `
      <div class="detail-related-section">
        <h4>You May Also Like</h4>
        <div class="related-grid">
          ${prod.related_products.map(rel => `
            <div class="related-card" onclick="openProductDetailModal('${rel.slug}')">
              <img src="${resolveProductImage(rel.image)}" alt="${rel.name}">
              <h5>${rel.name}</h5>
              <p>${CONFIG.CURRENCY}${parseFloat(rel.discounted_price || rel.price).toFixed(2)}</p>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}
  `;

  // Gallery thumbnail switching
  content.querySelectorAll('.thumbnail-item').forEach(th => {
    th.addEventListener('click', () => {
      content.querySelectorAll('.thumbnail-item').forEach(t => t.classList.remove('active'));
      th.classList.add('active');
      document.getElementById('detailMainImg').src = th.getAttribute('data-src');
    });
  });

  // Quantity controls
  let qty = 1;
  const maxStock = prod.stock || 99;
  const qtyVal = document.getElementById('detailQtyVal');
  document.getElementById('detailQtyMinus')?.addEventListener('click', () => {
    if (qty > 1) {
      qty--;
      qtyVal.textContent = qty;
    }
  });
  document.getElementById('detailQtyPlus')?.addEventListener('click', () => {
    if (qty < maxStock) {
      qty++;
      qtyVal.textContent = qty;
    } else {
      showToast(`Only ${maxStock} items available in stock!`, 'info');
    }
  });

  // Add to cart from modal
  document.getElementById('detailAddCartBtn')?.addEventListener('click', () => {
    addToCart(prod, qty);
    closeAllModals();
    openCartDrawer();
  });
}

// ============================================================================
// Shopping Cart Operations
// ============================================================================

function saveCart() {
  localStorage.setItem('toyverse_cart', JSON.stringify(state.cart));
  updateCartBadge();
  renderCartDrawer();
}

function updateCartBadge() {
  const count = state.cart.reduce((total, item) => total + item.quantity, 0);
  const badge = document.getElementById('cartBadgeCount');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'flex' : 'none';
  }
}

function addToCart(product, quantity = 1) {
  if (!product.in_stock && product.stock <= 0) {
    showToast(`Sorry, "${product.name}" is currently out of stock!`, 'error');
    return;
  }

  const existing = state.cart.find(item => item.product.id === product.id);
  const maxStock = product.stock || 99;

  if (existing) {
    if (existing.quantity + quantity > maxStock) {
      showToast(`Maximum stock limit (${maxStock}) reached for this item.`, 'info');
      existing.quantity = maxStock;
    } else {
      existing.quantity += quantity;
      showToast(`Added ${quantity} more to your cart! 🛍️`, 'success');
    }
  } else {
    state.cart.push({
      id: product.id,
      product: product,
      quantity: Math.min(quantity, maxStock)
    });
    showToast(`"${product.name}" added to cart! 🛍️`, 'success');
  }

  saveCart();
}

function updateCartItemQuantity(productId, delta) {
  const item = state.cart.find(i => i.product.id === productId);
  if (!item) return;

  const newQty = item.quantity + delta;
  const maxStock = item.product.stock || 99;

  if (newQty <= 0) {
    removeCartItem(productId);
  } else if (newQty > maxStock) {
    showToast(`Only ${maxStock} units available in stock.`, 'info');
  } else {
    item.quantity = newQty;
    saveCart();
  }
}

function removeCartItem(productId) {
  state.cart = state.cart.filter(i => i.product.id !== productId);
  showToast('Item removed from cart.', 'info');
  saveCart();
}

function renderCartDrawer() {
  const list = document.getElementById('cartItemsList');
  const countLabel = document.getElementById('cartItemCountLabel');
  const subtotalEl = document.getElementById('cartSubtotal');
  const shippingEl = document.getElementById('cartShipping');
  const totalEl = document.getElementById('cartTotal');
  const trackerText = document.getElementById('shippingTrackerText');
  const progressFill = document.getElementById('shippingProgressFill');

  if (!list) return;

  const totalItems = state.cart.reduce((acc, i) => acc + i.quantity, 0);
  if (countLabel) countLabel.textContent = `${totalItems} item${totalItems === 1 ? '' : 's'}`;

  if (state.cart.length === 0) {
    list.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-light)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 1rem;">
          <circle cx="8" cy="21" r="1"/>
          <circle cx="19" cy="21" r="1"/>
          <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>
        </svg>
        <h4 style="font-weight: 700; margin-bottom: 0.5rem;">Your cart is empty</h4>
        <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 1.5rem;">Looks like you haven't added any fun toys yet!</p>
        <button type="button" class="btn-hero-primary" onclick="closeCartDrawer()" style="margin: 0 auto;">Start Shopping</button>
      </div>
    `;

    if (subtotalEl) subtotalEl.textContent = '$0.00';
    if (shippingEl) shippingEl.textContent = '$0.00';
    if (totalEl) totalEl.textContent = '$0.00';
    if (trackerText) trackerText.innerHTML = `Add $50.00 more for <strong>FREE shipping!</strong> 🚚`;
    if (progressFill) progressFill.style.width = '0%';
    return;
  }

  let subtotal = 0;

  list.innerHTML = state.cart.map(item => {
    const p = item.product;
    const price = parseFloat(p.discounted_price || p.price);
    const itemTotal = price * item.quantity;
    subtotal += itemTotal;

    return `
      <div class="cart-item">
        <div class="cart-item-img">
          <img src="${resolveProductImage(p.image)}" alt="${p.name}">
        </div>
        <div class="cart-item-details">
          <div class="cart-item-title">${p.name}</div>
          <div class="cart-item-price">${CONFIG.CURRENCY}${price.toFixed(2)}</div>
          <div class="cart-item-actions">
            <div class="cart-qty-mini">
              <button type="button" onclick="updateCartItemQuantity(${p.id}, -1)">-</button>
              <span>${item.quantity}</span>
              <button type="button" onclick="updateCartItemQuantity(${p.id}, 1)">+</button>
            </div>
            <button type="button" class="btn-remove-item" onclick="removeCartItem(${p.id})" title="Remove item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Shipping calculation
  const isFreeShipping = subtotal >= CONFIG.FREE_SHIPPING_THRESHOLD;
  const shipping = isFreeShipping ? 0 : CONFIG.SHIPPING_FEE;
  const total = subtotal + shipping;

  if (subtotalEl) subtotalEl.textContent = `${CONFIG.CURRENCY}${subtotal.toFixed(2)}`;
  if (shippingEl) shippingEl.textContent = isFreeShipping ? 'FREE' : `${CONFIG.CURRENCY}${shipping.toFixed(2)}`;
  if (totalEl) totalEl.textContent = `${CONFIG.CURRENCY}${total.toFixed(2)}`;

  // Shipping progress bar
  if (trackerText && progressFill) {
    if (isFreeShipping) {
      trackerText.innerHTML = `🎉 Congratulations! You unlocked <strong>FREE Shipping!</strong>`;
      progressFill.style.width = '100%';
    } else {
      const remaining = CONFIG.FREE_SHIPPING_THRESHOLD - subtotal;
      const pct = Math.min(100, Math.round((subtotal / CONFIG.FREE_SHIPPING_THRESHOLD) * 100));
      trackerText.innerHTML = `Add <strong>${CONFIG.CURRENCY}${remaining.toFixed(2)}</strong> more for <strong>FREE shipping!</strong> 🚚`;
      progressFill.style.width = `${pct}%`;
    }
  }
}

function openCartDrawer() {
  renderCartDrawer();
  const drawer = document.getElementById('cartDrawerOverlay');
  if (drawer) drawer.classList.add('open');
}

function closeCartDrawer() {
  const drawer = document.getElementById('cartDrawerOverlay');
  if (drawer) drawer.classList.remove('open');
}

// ============================================================================
// Wishlist Operations
// ============================================================================

function toggleWishlist(product) {
  const index = state.wishlist.findIndex(item => item.id === product.id);
  if (index >= 0) {
    state.wishlist.splice(index, 1);
    showToast(`Removed from your wishlist.`, 'info');
  } else {
    state.wishlist.push(product);
    showToast(`Added to your wishlist! ❤️`, 'success');
  }

  localStorage.setItem('toyverse_wishlist', JSON.stringify(state.wishlist));
  updateWishlistBadge();
  renderProductsGrid();
  renderWishlistDrawer();
}

function updateWishlistBadge() {
  const badge = document.getElementById('wishlistBadgeCount');
  if (badge) {
    badge.textContent = state.wishlist.length;
    badge.style.display = state.wishlist.length > 0 ? 'flex' : 'none';
  }
}

function openWishlistDrawer() {
  renderWishlistDrawer();
  const drawer = document.getElementById('wishlistDrawerOverlay');
  if (drawer) drawer.classList.add('open');
}

function closeWishlistDrawer() {
  const drawer = document.getElementById('wishlistDrawerOverlay');
  if (drawer) drawer.classList.remove('open');
}

function renderWishlistDrawer() {
  const list = document.getElementById('wishlistItemsList');
  if (!list) return;

  if (state.wishlist.length === 0) {
    list.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-light)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 1rem;">
          <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
        </svg>
        <h4 style="font-weight: 700; margin-bottom: 0.5rem;">Your wishlist is empty</h4>
        <p style="font-size: 0.88rem; color: var(--text-muted);">Tap the heart icon on any toy to save it for later!</p>
      </div>
    `;
    return;
  }

  list.innerHTML = state.wishlist.map(p => `
    <div class="cart-item">
      <div class="cart-item-img">
        <img src="${resolveProductImage(p.image)}" alt="${p.name}">
      </div>
      <div class="cart-item-details">
        <div class="cart-item-title">${p.name}</div>
        <div class="cart-item-price">${CONFIG.CURRENCY}${parseFloat(p.discounted_price || p.price).toFixed(2)}</div>
        <div class="cart-item-actions" style="gap: 0.5rem;">
          <button type="button" class="btn-hero-primary" style="padding: 0.35rem 0.8rem; font-size: 0.8rem;" onclick="moveToCartFromWishlist(${p.id})">
            Move to Cart
          </button>
          <button type="button" class="btn-remove-item" onclick="removeFromWishlist(${p.id})">
            Remove
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

function removeFromWishlist(id) {
  state.wishlist = state.wishlist.filter(p => p.id !== id);
  localStorage.setItem('toyverse_wishlist', JSON.stringify(state.wishlist));
  updateWishlistBadge();
  renderProductsGrid();
  renderWishlistDrawer();
}

function moveToCartFromWishlist(id) {
  const prod = state.wishlist.find(p => p.id === id);
  if (prod) {
    addToCart(prod, 1);
    removeFromWishlist(id);
    closeWishlistDrawer();
    openCartDrawer();
  }
}

// ============================================================================
// Authentication & User Profile
// ============================================================================

function openAuthModal() {
  const modal = document.getElementById('authModal');
  if (!modal) return;

  modal.classList.add('open');

  const tabsContainer = document.getElementById('authTabsContainer');
  const profileContainer = document.getElementById('profileContainer');

  if (state.token && state.user) {
    tabsContainer.style.display = 'none';
    profileContainer.style.display = 'block';
    renderUserProfile();
    fetchUserAddresses();
  } else {
    tabsContainer.style.display = 'block';
    profileContainer.style.display = 'none';
  }
}

function renderUserProfile() {
  const u = state.user;
  if (!u) return;

  document.getElementById('profileFullName').textContent = `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'Valued Customer';
  document.getElementById('profileEmailAddress').textContent = u.email;
  document.getElementById('profileAvatar').textContent = (u.first_name?.[0] || u.email?.[0] || 'U').toUpperCase();
}

function updateHeaderAuthButton() {
  const container = document.getElementById('authHeaderContainer');
  if (!container) return;

  if (state.token && state.user) {
    const initial = (state.user.first_name?.[0] || state.user.email?.[0] || 'U').toUpperCase();
    const name = state.user.first_name || state.user.email.split('@')[0];
    container.innerHTML = `
      <button type="button" class="user-menu-btn" id="userProfileBtn" title="Your Account">
        <div class="user-avatar-mini">${initial}</div>
        <span>${name}</span>
      </button>
    `;
    document.getElementById('userProfileBtn').addEventListener('click', openAuthModal);
  } else {
    container.innerHTML = `
      <button type="button" class="btn-login" id="loginBtn">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
        <span>Sign In</span>
      </button>
    `;
    document.getElementById('loginBtn').addEventListener('click', openAuthModal);
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const submitBtn = document.getElementById('loginSubmitBtn');

  submitBtn.disabled = true;
  submitBtn.textContent = 'Signing In...';

  try {
    const data = await apiRequest('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    state.token = data.access;
    state.refreshToken = data.refresh;
    state.user = data.user;

    localStorage.setItem('toyverse_token', state.token);
    localStorage.setItem('toyverse_refresh', state.refreshToken);
    localStorage.setItem('toyverse_user', JSON.stringify(state.user));

    showToast(`Welcome back, ${state.user.first_name || 'friend'}! ✨`, 'success');
    closeAllModals();
    updateHeaderAuthButton();
  } catch (err) {
    showToast('Invalid email or password. Please try again.', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Sign In to ToyVerse';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const firstName = document.getElementById('regFirstName').value;
  const lastName = document.getElementById('regLastName').value;
  const email = document.getElementById('regEmail').value;
  const phone = document.getElementById('regPhone').value;
  const password = document.getElementById('regPassword').value;
  const passwordConfirm = document.getElementById('regPasswordConfirm').value;
  const submitBtn = document.getElementById('registerSubmitBtn');

  if (password !== passwordConfirm) {
    showToast('Passwords do not match!', 'error');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Creating Account...';

  try {
    const data = await apiRequest('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email,
        phone,
        password,
        password_confirm: passwordConfirm,
      })
    });

    state.token = data.access;
    state.refreshToken = data.refresh;
    state.user = data.user;

    localStorage.setItem('toyverse_token', state.token);
    localStorage.setItem('toyverse_refresh', state.refreshToken);
    localStorage.setItem('toyverse_user', JSON.stringify(state.user));

    showToast('Account created successfully! Welcome to ToyVerse! 🚀', 'success');
    closeAllModals();
    updateHeaderAuthButton();
  } catch (err) {
    showToast('Registration failed. Email might already exist or password is too simple.', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Create Account';
  }
}

function logoutUser() {
  state.token = null;
  state.refreshToken = null;
  state.user = null;
  state.addresses = [];

  localStorage.removeItem('toyverse_token');
  localStorage.removeItem('toyverse_refresh');
  localStorage.removeItem('toyverse_user');

  updateHeaderAuthButton();
  closeAllModals();
  showToast('You have been signed out.', 'info');
}

// Address Management
async function fetchUserAddresses() {
  const listContainer = document.getElementById('addressesListContainer');
  if (!listContainer || !state.token) return;

  try {
    const addresses = await apiRequest('/api/addresses/');
    state.addresses = addresses;
    renderAddressesList();
  } catch (err) {
    console.error('Failed to fetch addresses:', err);
  }
}

function renderAddressesList() {
  const container = document.getElementById('addressesListContainer');
  if (!container) return;

  if (state.addresses.length === 0) {
    container.innerHTML = `<p style="font-size: 0.88rem; color: var(--text-muted);">No shipping addresses saved yet.</p>`;
    return;
  }

  container.innerHTML = state.addresses.map(addr => `
    <div class="address-item">
      <div>
        <div style="font-weight: 700; font-size: 0.9rem;">
          ${addr.full_name} 
          <span style="font-size: 0.72rem; padding: 0.15rem 0.5rem; background: ${addr.is_default ? 'var(--primary-light)' : 'var(--border-light)'}; color: ${addr.is_default ? 'var(--primary)' : 'var(--text-main)'}; border-radius: var(--radius-full); margin-left: 0.4rem; text-transform: uppercase;">${addr.label} ${addr.is_default ? '• Default' : ''}</span>
        </div>
        <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.2rem;">
          ${addr.line1}${addr.line2 ? `, ${addr.line2}` : ''}, ${addr.city}, ${addr.state} ${addr.postal_code}
        </div>
      </div>
      <button type="button" class="btn-remove-item" onclick="deleteAddress(${addr.id})" title="Delete address">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  `).join('');
}

async function handleSaveAddress(e) {
  e.preventDefault();
  const label = document.getElementById('addrLabel').value;
  const fullName = document.getElementById('addrFullName').value;
  const phone = document.getElementById('addrPhone').value;
  const line1 = document.getElementById('addrLine1').value;
  const city = document.getElementById('addrCity').value;
  const addrState = document.getElementById('addrState').value;
  const postal = document.getElementById('addrPostal').value;
  const country = document.getElementById('addrCountry').value;

  try {
    await apiRequest('/api/addresses/', {
      method: 'POST',
      body: JSON.stringify({
        label,
        full_name: fullName,
        phone,
        line1,
        city,
        state: addrState,
        postal_code: postal,
        country
      })
    });

    showToast('Shipping address saved!', 'success');
    document.getElementById('newAddressForm').reset();
    document.getElementById('newAddressForm').style.display = 'none';
    fetchUserAddresses();
  } catch (err) {
    showToast('Failed to save address. Please check fields.', 'error');
  }
}

async function deleteAddress(id) {
  try {
    await apiRequest(`/api/addresses/${id}/`, { method: 'DELETE' });
    showToast('Address deleted.', 'info');
    fetchUserAddresses();
  } catch (err) {
    showToast('Failed to delete address.', 'error');
  }
}

// ============================================================================
// Filter & Search Controls
// ============================================================================

let searchDebounceTimeout = null;

function setupSearchListeners() {
  const input = document.getElementById('searchInput');
  const clearBtn = document.getElementById('searchClearBtn');

  if (!input) return;

  input.addEventListener('input', (e) => {
    const val = e.target.value;
    clearBtn.style.display = val ? 'flex' : 'none';

    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(() => {
      state.searchQuery = val;
      fetchProducts(1);
    }, 350);
  });

  clearBtn?.addEventListener('click', () => {
    input.value = '';
    clearBtn.style.display = 'none';
    state.searchQuery = '';
    fetchProducts(1);
  });
}

function clearSearchFilter() {
  const input = document.getElementById('searchInput');
  if (input) input.value = '';
  document.getElementById('searchClearBtn').style.display = 'none';
  state.searchQuery = '';
  fetchProducts(1);
}

function clearPriceFilter() {
  state.filters.min_price = '';
  state.filters.max_price = '';
  document.getElementById('minPriceInput').value = '';
  document.getElementById('maxPriceInput').value = '';
  fetchProducts(1);
}

function clearAgeFilter() {
  state.filters.age = '';
  document.getElementById('ageFilterSelect').value = '';
  fetchProducts(1);
}

function toggleFilter(key, val) {
  state.filters[key] = val;
  if (key === 'on_sale') document.getElementById('filterOnSaleCheckbox').checked = val;
  if (key === 'featured') document.getElementById('filterFeaturedCheckbox').checked = val;
  if (key === 'in_stock') document.getElementById('filterInStockCheckbox').checked = val;
  fetchProducts(1);
}

function resetAllFilters() {
  state.searchQuery = '';
  state.activeCategory = '';
  state.quickFilter = 'all';
  state.filters = {
    min_price: '',
    max_price: '',
    age: '',
    in_stock: false,
    on_sale: false,
    featured: false,
  };

  const searchInput = document.getElementById('searchInput');
  if (searchInput) searchInput.value = '';
  document.getElementById('searchClearBtn').style.display = 'none';

  document.getElementById('minPriceInput').value = '';
  document.getElementById('maxPriceInput').value = '';
  document.getElementById('ageFilterSelect').value = '';
  document.getElementById('filterInStockCheckbox').checked = false;
  document.getElementById('filterOnSaleCheckbox').checked = false;
  document.getElementById('filterFeaturedCheckbox').checked = false;

  document.querySelectorAll('.quick-filter-tag').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-filter') === 'all');
  });

  renderCategoryChips();
  fetchProducts(1);
}

function setupFilterPanel() {
  const toggleBtn = document.getElementById('filterToggleBtn');
  const panel = document.getElementById('filterPanel');

  toggleBtn?.addEventListener('click', () => {
    panel.classList.toggle('open');
    toggleBtn.classList.toggle('active');
  });

  document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
    state.filters.min_price = document.getElementById('minPriceInput').value;
    state.filters.max_price = document.getElementById('maxPriceInput').value;
    state.filters.age = document.getElementById('ageFilterSelect').value;
    state.filters.in_stock = document.getElementById('filterInStockCheckbox').checked;
    state.filters.on_sale = document.getElementById('filterOnSaleCheckbox').checked;
    state.filters.featured = document.getElementById('filterFeaturedCheckbox').checked;
    fetchProducts(1);
  });

  document.getElementById('resetFiltersBtn')?.addEventListener('click', resetAllFilters);

  // Quick filter tags
  document.querySelectorAll('.quick-filter-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      document.querySelectorAll('.quick-filter-tag').forEach(t => t.classList.remove('active'));
      tag.classList.add('active');

      const filterType = tag.getAttribute('data-filter');
      state.quickFilter = filterType;

      // Reset specific boolean filters first
      state.filters.on_sale = false;
      state.filters.featured = false;
      state.filters.in_stock = false;
      state.filters.min_price = '';
      state.filters.max_price = '';

      if (filterType === 'on_sale') state.filters.on_sale = true;
      if (filterType === 'featured') state.filters.featured = true;
      if (filterType === 'in_stock') state.filters.in_stock = true;
      if (filterType === 'under_25') state.filters.max_price = '25';
      if (filterType === 'under_50') state.filters.max_price = '50';

      fetchProducts(1);
    });
  });

  // Sorting
  document.getElementById('sortSelect')?.addEventListener('change', (e) => {
    state.ordering = e.target.value;
    fetchProducts(1);
  });
}

// ============================================================================
// Modals & Overlay Handlers
// ============================================================================

function closeAllModals() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
  closeCartDrawer();
  closeWishlistDrawer();
}

function setupModalEventListeners() {
  // Product Detail Modal
  document.getElementById('closeDetailModalBtn')?.addEventListener('click', () => {
    document.getElementById('productDetailModal').classList.remove('open');
  });

  // Auth Modal
  document.getElementById('closeAuthModalBtn')?.addEventListener('click', () => {
    document.getElementById('authModal').classList.remove('open');
  });

  // Tab switching inside Auth Modal
  const tabLoginBtn = document.getElementById('tabLoginBtn');
  const tabRegisterBtn = document.getElementById('tabRegisterBtn');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  tabLoginBtn?.addEventListener('click', () => {
    tabLoginBtn.classList.add('active');
    tabRegisterBtn.classList.remove('active');
    loginForm.style.display = 'flex';
    registerForm.style.display = 'none';
  });

  tabRegisterBtn?.addEventListener('click', () => {
    tabRegisterBtn.classList.add('active');
    tabLoginBtn.classList.remove('active');
    registerForm.style.display = 'flex';
    loginForm.style.display = 'none';
  });

  // Forms
  loginForm?.addEventListener('submit', handleLogin);
  registerForm?.addEventListener('submit', handleRegister);
  document.getElementById('logoutBtn')?.addEventListener('click', logoutUser);

  // Address form toggle
  document.getElementById('addAddressToggleBtn')?.addEventListener('click', () => {
    const form = document.getElementById('newAddressForm');
    form.style.display = form.style.display === 'none' ? 'flex' : 'none';
  });
  document.getElementById('newAddressForm')?.addEventListener('submit', handleSaveAddress);

  // Header Drawers
  document.getElementById('cartHeaderBtn')?.addEventListener('click', openCartDrawer);
  document.getElementById('closeCartBtn')?.addEventListener('click', closeCartDrawer);
  document.getElementById('cartDrawerOverlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'cartDrawerOverlay') closeCartDrawer();
  });

  document.getElementById('wishlistHeaderBtn')?.addEventListener('click', openWishlistDrawer);
  document.getElementById('closeWishlistBtn')?.addEventListener('click', closeWishlistDrawer);
  document.getElementById('wishlistDrawerOverlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'wishlistDrawerOverlay') closeWishlistDrawer();
  });

  // Backdrop click for modals
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('open');
      }
    });
  });

  // Checkout Button
  document.getElementById('checkoutBtn')?.addEventListener('click', () => {
    if (state.cart.length === 0) return;
    
    showToast('🎉 Order simulated! Thank you for purchasing from ToyVerse!', 'success', 5000);
    state.cart = [];
    saveCart();
    closeCartDrawer();
  });

  // Load More Button
  document.getElementById('loadMoreBtn')?.addEventListener('click', () => {
    if (state.nextPageUrl) {
      fetchProducts(state.currentPage + 1, true);
    }
  });

  // Hero Specials button
  document.getElementById('heroSaleBtn')?.addEventListener('click', () => {
    toggleFilter('on_sale', true);
    document.getElementById('catalogAnchor').scrollIntoView({ behavior: 'smooth' });
  });

  // Sticky header shadow on scroll
  window.addEventListener('scroll', () => {
    const header = document.getElementById('siteHeader');
    if (window.scrollY > 20) {
      header?.classList.add('scrolled');
    } else {
      header?.classList.remove('scrolled');
    }
  });
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  updateHeaderAuthButton();
  updateCartBadge();
  updateWishlistBadge();

  setupSearchListeners();
  setupFilterPanel();
  setupModalEventListeners();

  // Load initial data
  fetchCategories();
  fetchProducts(1);
});
