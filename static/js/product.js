document.addEventListener("DOMContentLoaded", () => {
  const tbody = document.querySelector("#productsTable tbody");
  const searchInput = document.getElementById("searchInput");
  const sortSelect = document.getElementById("sortSelect");
  const btnAdd = document.getElementById("btnAdd");
  const modal = document.getElementById("modal");
  const modalTitle = document.getElementById("modalTitle");
  const modalCancel = document.getElementById("modalCancel");
  const modalSave = document.getElementById("modalSave");
  const selectAll = document.getElementById("selectAll");

  const bulkBar = document.getElementById("bulkBar");
  const selectedCount = document.getElementById("selectedCount");
  const bulkDelete = document.getElementById("bulkDelete");
  const bulkRestock = document.getElementById("bulkRestock");

  const pName = document.getElementById("pName");
  const pCategory = document.getElementById("pCategory");
  const pPrice = document.getElementById("pPrice");
  const pStock = document.getElementById("pStock");
  const pGst = document.getElementById("pGst");

  let productsCache = [];
  let editingId = null;

  async function loadProducts() {
    const q = encodeURIComponent(searchInput.value || "");
    const sort = encodeURIComponent(sortSelect.value || "name");
    const res = await fetch(`/products/api?q=${q}&sort=${sort}`);
    const j = await res.json();
    productsCache = j.products || [];
    render();
  }

  function render() {
    tbody.innerHTML = "";
    productsCache.forEach((p) => {
      const tr = document.createElement("tr");
      if (p.stock < 5) tr.classList.add("low");
      tr.innerHTML = `
        <td><input type="checkbox" class="row-check" data-id="${p.id}"></td>
        <td>${p.id}</td>
        <td>${p.name}</td>
        <td>${p.category || ""}</td>
        <td>₹${Number(p.price).toFixed(2)}</td>
        <td>${p.stock}</td>
        <td>${p.gst != null ? p.gst * 100 + "%" : "-"}</td>
        <td class="actions">
          <button onclick="editProduct(${p.id})">Edit</button>
          <button onclick="deleteProduct(${p.id})" style="background:#ff6b6b;color:#fff">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    bindCheckboxes();
  }

  function bindCheckboxes() {
    const checks = document.querySelectorAll(".row-check");
    checks.forEach((c) => c.addEventListener("change", updateBulkBar));
  }

  function updateBulkBar() {
    const checked = document.querySelectorAll(".row-check:checked");
    selectedCount.textContent = `${checked.length} selected`;
    bulkBar.classList.toggle("active", checked.length > 0);
    selectAll.checked =
      checked.length &&
      checked.length === document.querySelectorAll(".row-check").length;
  }

  selectAll.addEventListener("change", () => {
    document
      .querySelectorAll(".row-check")
      .forEach((c) => (c.checked = selectAll.checked));
    updateBulkBar();
  });

  bulkDelete.addEventListener("click", async () => {
    if (!confirm("Delete selected products?")) return;
    const ids = [...document.querySelectorAll(".row-check:checked")].map(
      (c) => c.dataset.id,
    );
    for (const id of ids)
      await fetch(`/products/api/${id}`, { method: "DELETE" });
    loadProducts();
  });

  bulkRestock.addEventListener("click", async () => {
    const qty = prompt("Add stock quantity:");
    if (!qty) return;
    const ids = [...document.querySelectorAll(".row-check:checked")].map(
      (c) => c.dataset.id,
    );
    for (const id of ids) {
      const p = productsCache.find((x) => x.id == id);
      await fetch(`/products/api/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stock: p.stock + parseInt(qty) }),
      });
    }
    loadProducts();
  });

  btnAdd.onclick = () => {
    editingId = null;
    modalTitle.textContent = "Add Product";
    pName.value =
      pCategory.value =
      pPrice.value =
      pStock.value =
      pGst.value =
        "";
    modal.classList.add("open");
  };

  modalCancel.onclick = () => modal.classList.remove("open");

  modalSave.onclick = async () => {
    const payload = {
      name: pName.value,
      category: pCategory.value,
      price: parseFloat(pPrice.value),
      stock: parseInt(pStock.value),
      gst: pGst.value ? parseFloat(pGst.value) / 100 : null,
    };
    const url = editingId ? `/products/api/${editingId}` : "/products/api";
    await fetch(url, {
      method: editingId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    modal.classList.remove("open");
    loadProducts();
  };

  window.editProduct = (id) => {
    const p = productsCache.find((x) => x.id === id);
    editingId = id;
    modalTitle.textContent = "Edit Product";
    pName.value = p.name;
    pCategory.value = p.category || "";
    pPrice.value = p.price;
    pStock.value = p.stock;
    pGst.value = p.gst ? p.gst * 100 : "";
    modal.classList.add("open");
  };

  window.deleteProduct = async (id) => {
    if (!confirm("Delete product?")) return;
    await fetch(`/products/api/${id}`, { method: "DELETE" });
    loadProducts();
  };

  searchInput.oninput = loadProducts;
  sortSelect.onchange = loadProducts;
  loadProducts();
});
