// =========================================================================
// Lao Water Delivery Web App - Client Script (Pilot Cyber Neon Theme)
// =========================================================================

// --- Cart Management (LocalStorage) ---
const CART_KEY = "lao_water_cart_v1";

function getCart() {
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartBadges();
}

function bounceFloatingCart() {
  const fab = document.getElementById("floating-cart-fab");
  if (!fab) return;
  const btn = fab.querySelector("button");
  if (btn) {
    btn.classList.remove("animate-fab-bounce");
    void btn.offsetWidth; // trigger reflow
    btn.classList.add("animate-fab-bounce");
  }
}

function addToCart(item) {
  const cart = getCart();
  const existing = cart.find(x => x.id === item.id);
  if (existing) {
    existing.quantity += (item.quantity || 1);
  } else {
    cart.push({
      id: item.id,
      name: item.name,
      price: item.price,
      unit_label: item.unit_label || "ຕຸກ",
      image_url: item.image_url || "",
      quantity: item.quantity || 1
    });
  }
  saveCart(cart);
  showToast(`ເພີ່ມ "${item.name}" ໃສ່ກະຕ່າແລ້ວ!`, "success");
  bounceFloatingCart();
  renderCartDrawer();
}

function updateCartItemQty(productId, delta) {
  let cart = getCart();
  const item = cart.find(x => x.id === productId);
  if (item) {
    item.quantity += delta;
    if (item.quantity <= 0) {
      cart = cart.filter(x => x.id !== productId);
    }
    saveCart(cart);
    renderCartDrawer();
    renderCheckoutSummary();
  }
}

function removeCartItem(productId) {
  let cart = getCart();
  cart = cart.filter(x => x.id !== productId);
  saveCart(cart);
  renderCartDrawer();
  renderCheckoutSummary();
  showToast("ລຶບລາຍການອອກຈາກກະຕ່າແລ້ວ", "info");
}

function clearCart() {
  localStorage.removeItem(CART_KEY);
  updateCartBadges();
  renderCartDrawer();
  renderCheckoutSummary();
}

function getCartSummary() {
  const cart = getCart();
  const totalCount = cart.reduce((acc, x) => acc + x.quantity, 0);
  const totalAmount = cart.reduce((acc, x) => acc + (x.price * x.quantity), 0);
  return { cart, totalCount, totalAmount };
}

// --- Formatters ---
function formatKip(amount) {
  if (isNaN(amount)) return "0 ₭";
  return new Intl.NumberFormat("lo-LA").format(amount) + " ₭";
}

// --- UI Updates ---
function updateCartBadges() {
  const { totalCount, totalAmount } = getCartSummary();
  
  // Header badges
  document.querySelectorAll(".cart-count-badge").forEach(el => {
    el.textContent = totalCount;
    el.style.display = totalCount > 0 ? "inline-flex" : "none";
  });

  // Floating Bottom-Right Cart FAB (Desktop & Mobile)
  const fab = document.getElementById("floating-cart-fab");
  if (fab) {
    if (totalCount > 0) {
      fab.classList.remove("hidden");
      fab.classList.add("flex");
      const countEl = document.getElementById("floating-cart-count");
      const totalEl = document.getElementById("floating-cart-total");
      if (countEl) countEl.textContent = totalCount;
      if (totalEl) totalEl.textContent = formatKip(totalAmount);
    } else {
      fab.classList.add("hidden");
      fab.classList.remove("flex");
    }
  }

  // Floating Bottom Cart bar (Mobile fallback if present)
  const floatBar = document.getElementById("mobile-cart-bar");
  if (floatBar) {
    if (totalCount > 0) {
      floatBar.classList.remove("hidden");
      floatBar.classList.add("flex");
      const countEl = document.getElementById("mobile-cart-count");
      const totalEl = document.getElementById("mobile-cart-total");
      if (countEl) countEl.textContent = `${totalCount} ລາຍການ`;
      if (totalEl) totalEl.textContent = formatKip(totalAmount);
    } else {
      floatBar.classList.add("hidden");
      floatBar.classList.remove("flex");
    }
  }
}

function renderCartDrawer() {
  const container = document.getElementById("cart-drawer-items");
  const totalEl = document.getElementById("cart-drawer-total");
  const emptyEl = document.getElementById("cart-drawer-empty");
  const footerEl = document.getElementById("cart-drawer-footer");
  if (!container) return;

  const { cart, totalCount, totalAmount } = getCartSummary();

  if (cart.length === 0) {
    container.innerHTML = "";
    if (emptyEl) emptyEl.classList.remove("hidden");
    if (footerEl) footerEl.classList.add("hidden");
    return;
  }

  if (emptyEl) emptyEl.classList.add("hidden");
  if (footerEl) footerEl.classList.remove("hidden");
  if (totalEl) totalEl.textContent = formatKip(totalAmount);

  container.innerHTML = cart.map(item => `
    <div class="flex items-center gap-3 p-3 bg-[#19102c] rounded-2xl border border-purple-900/50 text-white shadow-sm">
      <img src="${item.image_url || '/static/img/tom_bottle.svg'}" class="w-14 h-14 object-contain bg-[#0e081c] rounded-xl p-1 border border-purple-900/60 shrink-0" />
      <div class="flex-1 min-w-0">
        <h4 class="font-bold text-white text-sm truncate">${item.name}</h4>
        <p class="text-xs text-amber-400 font-mono font-bold">${formatKip(item.price)} / ${item.unit_label}</p>
        <div class="flex items-center gap-2 mt-2">
          <button onclick="updateCartItemQty(${item.id}, -1)" class="w-6 h-6 rounded-lg bg-purple-950/80 border border-purple-800/60 text-purple-200 font-bold hover:bg-purple-900 flex items-center justify-center text-xs transition">-</button>
          <span class="text-sm font-bold text-white px-1 font-mono">${item.quantity}</span>
          <button onclick="updateCartItemQty(${item.id}, 1)" class="w-6 h-6 rounded-lg bg-purple-950/80 border border-purple-800/60 text-purple-200 font-bold hover:bg-purple-900 flex items-center justify-center text-xs transition">+</button>
        </div>
      </div>
      <div class="text-right shrink-0">
        <div class="font-black text-amber-400 font-mono text-sm">${formatKip(item.price * item.quantity)}</div>
        <button onclick="removeCartItem(${item.id})" class="text-xs text-rose-400 hover:text-rose-300 font-bold mt-2 transition">ລຶບ</button>
      </div>
    </div>
  `).join("");
}

function renderCheckoutSummary() {
  const container = document.getElementById("checkout-items-list");
  const totalEl = document.getElementById("checkout-total-amount");
  const qrTotalEl = document.getElementById("qr-total-amount");
  if (!container) return;

  const { cart, totalAmount } = getCartSummary();

  if (cart.length === 0) {
    container.innerHTML = `<div class="p-6 text-center text-purple-400/60">ບໍ່ມີສິນຄ້າໃນກະຕ່າ <br><a href="/" class="text-amber-400 font-bold underline mt-2 inline-block">ກັບໄປເລືອກຊື້ສິນຄ້າ</a></div>`;
    if (totalEl) totalEl.textContent = "0 ₭";
    if (qrTotalEl) qrTotalEl.textContent = "0 ₭";
    const submitBtn = document.getElementById("submit-order-btn");
    if (submitBtn) submitBtn.disabled = true;
    return;
  }

  const submitBtn = document.getElementById("submit-order-btn");
  if (submitBtn) submitBtn.disabled = false;

  container.innerHTML = cart.map(item => `
    <div class="flex items-center justify-between py-2.5 border-b border-purple-900/30 text-sm">
      <div class="flex items-center gap-2">
        <span class="font-bold text-amber-400 font-mono">${item.quantity}x</span>
        <span class="text-purple-200 font-medium">${item.name}</span>
      </div>
      <span class="font-black text-amber-400 font-mono">${formatKip(item.price * item.quantity)}</span>
    </div>
  `).join("");

  if (totalEl) totalEl.textContent = formatKip(totalAmount);
  if (qrTotalEl) qrTotalEl.textContent = formatKip(totalAmount);
}

// --- Toast Helper ---
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Drawer Toggle Helpers
function openCartDrawer() {
  const drawer = document.getElementById("cart-drawer");
  const overlay = document.getElementById("cart-overlay");
  if (drawer && overlay) {
    renderCartDrawer();
    drawer.classList.remove("translate-x-full");
    overlay.classList.remove("hidden");
  }
}

function closeCartDrawer() {
  const drawer = document.getElementById("cart-drawer");
  const overlay = document.getElementById("cart-overlay");
  if (drawer && overlay) {
    drawer.classList.add("translate-x-full");
    overlay.classList.add("hidden");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateCartBadges();
});
