// =========================================================
// ========== HELPER FUNCTIONS (Runs on all pages) ==========
// =========================================================

// Helper to create and display custom AJAX flash messages
function displayFlash(message, category) {
  const flashContainer = document.querySelector(".flash-container");
  if (!flashContainer) return;

  // Remove old AJAX flashes to clean up
  document.querySelectorAll(".flash-ajax").forEach((f) => f.remove());

  const flashDiv = document.createElement("div");
  flashDiv.className = `flash flash-${category} flash-ajax`;
  flashDiv.textContent = message;
  flashContainer.prepend(flashDiv); // Add to the top

  // Auto-hide after 3 seconds
  setTimeout(() => {
    flashDiv.style.opacity = 0;
    setTimeout(() => flashDiv.remove(), 500); // Remove after fade out
  }, 3000);
}

// Password toggle (Used in login.html)
function togglePassword() {
  const pwd = document.getElementById("password");
  if (pwd) {
    pwd.type = pwd.type === "password" ? "text" : "password";
  }
}

// =========================================================
// ========== 1. DASHBOARD SPECIFIC LOGIC ==========
//    (Only runs if the path includes "dashboard.html")
// =========================================================
if (window.location.pathname.includes("dashboard")) {
  // Simplified check for 'dashboard'
  const userName = document.getElementById("userName");
  const dailySales = document.getElementById("dailySales");
  const weeklySales = document.getElementById("weeklySales");
  const topProducts = document.getElementById("topProducts");

  // Live date & time
  setInterval(() => {
    document.getElementById("datetime").textContent =
      new Date().toLocaleString();
  }, 1000);

  // Fetch user info and initial AI data
  fetch("/current-user")
    .then((res) => res.json())
    .then((data) => {
      userName.textContent = data.user.name;
      document.getElementById("aiInsightsText").textContent = data.ai_summary;
    })
    .catch((error) => console.error("Error fetching user info:", error));

  // Fetch reports data
  async function loadReports() {
    try {
      const daily = await (await fetch("/reports/daily")).json();
      const weekly = await (await fetch("/reports/weekly")).json();
      const top = await (await fetch("/reports/top-products")).json();

      dailySales.textContent = `₹${daily.total_sales}`;
      weeklySales.textContent = `₹${weekly.total_sales}`;
      topProducts.innerHTML = top.top_products
        .map((p) => `<li>${p.product} (${p.sold})</li>`)
        .join("");

      // Chart
      const ctx = document.getElementById("salesChart").getContext("2d");
      // Assuming Chart is a global object (e.g., Chart.js is loaded)
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: ["Daily", "Weekly"],
          datasets: [
            {
              label: "Sales (₹)",
              data: [daily.total_sales, weekly.total_sales],
              backgroundColor: ["#3b82f6", "#06b6d4"],
            },
          ],
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: "#e2e8f0" } } },
          scales: {
            x: { ticks: { color: "#e2e8f0" } },
            y: { ticks: { color: "#e2e8f0" } },
          },
        },
      });
    } catch (error) {
      console.error("Error loading reports:", error);
    }
  }
  loadReports();

  // AI Assistant Query Handler
  document.getElementById("aiAskBtn").addEventListener("click", async () => {
    const prompt = document.getElementById("aiPrompt").value.trim();
    if (!prompt) return alert("Enter a question!");

    const res = await fetch("/ai/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const data = await res.json();
    document.getElementById("aiResponse").textContent = data.response;
  });

  // Logout Handler
  document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
    e.preventDefault();
    window.location.href = "/logout";
  });
}

// =========================================================
// ========== 2. GENERAL LOGIC (Runs on all pages) ==========
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
  // --- Auto-hide standard Flask flash messages ---
  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((f) => {
    setTimeout(() => {
      f.style.opacity = 0;
      setTimeout(() => f.remove(), 500);
    }, 3000);
  });

  // --- AJAX LOGIN FORM HANDLER (NEW LOGIC) ---
  const loginForm = document.getElementById("login-form");
  const loginBtn = document.getElementById("login-btn");

  if (loginForm) {
    // We must ensure login.html has id="login-form" on the form
    // and id="login-btn" on the submit button.

    loginForm.addEventListener("submit", async function (e) {
      e.preventDefault(); // Stop the default synchronous form submission

      loginBtn.disabled = true;
      loginBtn.textContent = "Logging in...";

      const formData = new FormData(loginForm);
      const data = Object.fromEntries(formData.entries());

      try {
        const response = await fetch(loginForm.action, {
          method: "POST",
          headers: {
            "Content-Type": "application/json", // Send JSON
            Accept: "application/json", // Expect JSON
          },
          body: JSON.stringify(data),
        });

        const result = await response.json();

        if (response.ok) {
          // Status 200-299 is success

          // Show success message on the current page using the helper
          displayFlash(
            `Login successful! Welcome, ${result.username}!`,
            "success"
          );

          // Delay the redirect to allow user to see the message
          setTimeout(() => {
            window.location.href = result.redirect_url;
          }, 1500); // Redirect after 1.5 seconds
        } else {
          // Handle server-side errors (e.g., 401 Unauthorized)
          displayFlash(
            result.message || "An unknown error occurred.",
            "danger"
          );
          loginBtn.textContent = "Login";
          loginBtn.disabled = false;
        }
      } catch (error) {
        console.error("Login Error:", error);
        displayFlash("Network error. Please try again.", "danger");
        loginBtn.textContent = "Login";
        loginBtn.disabled = false;
      }
    });
  }

  // Sidebar toggle for mobile (existing logic)
  const sidebar = document.querySelector(".sidebar");
  const toggleBtn = document.createElement("button");
  toggleBtn.classList.add("toggle-btn");
  // Ensure you have a way to display this font awesome icon (e.g., Font Awesome library loaded)
  toggleBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';

  const topBar = document.querySelector(".top-bar");
  if (topBar) topBar.prepend(toggleBtn);

  toggleBtn.addEventListener("click", () => {
    if (sidebar) sidebar.classList.toggle("active");
  });
});

// Adds soft glow effect when focusing inputs (existing logic)
document.querySelectorAll("input").forEach((input) => {
  input.addEventListener("focus", () => {
    input.style.boxShadow = "0 0 10px rgba(0,255, 255, 0.5)";
  });
  input.addEventListener("blur", () => {
    input.style.boxShadow = "none";
  });
});
