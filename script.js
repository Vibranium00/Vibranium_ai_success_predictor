/* ======================= SHORTCUT ======================= */
const el = (id) => document.getElementById(id);
let lastAnalysisId = null;

/* ======================= FIREBASE CONFIG ======================= */
const firebaseConfig = {
  apiKey: "AIzaSyDVwJCmDIEV4cIPDEEzxCLOnDF1f3m3YbA",
  authDomain: "success-predictor-fire.firebaseapp.com",
  projectId: "success-predictor-fire",
  storageBucket: "success-predictor-fire.firebasestorage.app",
  messagingSenderId: "448025715458",
  appId: "1:448025715458:web:6d6fbf4e426d66879c981b",
  measurementId: "G-QLE7M3PXP6"
};

if (!firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}
const auth = firebase.auth();

/* ======================= LOGIN ======================= */
async function handleGoogleLogin() {
  try {
    const provider = new firebase.auth.GoogleAuthProvider();
    const result = await auth.signInWithPopup(provider);
    const token = await result.user.getIdToken();

    await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ token })
    });

    updateAuthUI();
  } catch (e) {
    console.error(e);
    alert("Login failed");
  }
}

/* ======================= LOGOUT ======================= */
async function handleLogout() {
  try {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
    if (firebase.auth().currentUser) await firebase.auth().signOut();
    updateAuthUI();
  } catch (e) {
    alert("Logout failed");
  }
}

/* ======================= AUTH UI ======================= */
async function updateAuthUI() {
  const openGoogle = el("openGoogle");
  const userSection = el("userSection");
  const userPhoto = el("userPhoto");
  const userName = el("userName");
  const userEmail = el("userEmail");

  try {
    const res = await fetch("/api/me", { credentials: "include" });
    const j = await res.json();

    if (j.authenticated) {
      openGoogle?.classList.add("hidden");
      userSection?.classList.remove("hidden");
      if (userName) userName.textContent = j.name || "User";
      if (userEmail) userEmail.textContent = j.email || "";
      if (userPhoto) userPhoto.src = j.picture || "";
      if (el("openDeep")) el("openDeep").disabled = false;
    } else {
      openGoogle?.classList.remove("hidden");
      userSection?.classList.add("hidden");
      openGoogle && (openGoogle.onclick = handleGoogleLogin);
      if (el("openDeep")) el("openDeep").disabled = true;
    }
  } catch (e) {
    console.warn("Auth check failed");
  }
}
updateAuthUI();

/* ======================= DROPDOWN ======================= */
el("userSection")?.addEventListener("click", () => {
  el("userDropdown")?.classList.toggle("hidden");
});

document.addEventListener("click", (e) => {
  if (el("userSection") && !el("userSection").contains(e.target)) {
    el("userDropdown")?.classList.add("hidden");
  }
});

/* ======================= SCROLL ======================= */
document.querySelectorAll("#openFast, #openDeep").forEach(btn => {
  btn.addEventListener("click", () => {
    el("analysisSection")?.scrollIntoView({ behavior: "smooth" });
  });
});

/* ======================= MODAL ======================= */
function openModal(mode) {
  el("inputModal")?.classList.remove("hidden");
  if (el("modalTitle"))
    el("modalTitle").textContent =
      mode === "deep" ? "Start Deep Analysis" : "Start Fast Analysis";
  if (el("analyzeBtn")) el("analyzeBtn").dataset.mode = mode;
}

document.querySelectorAll(".start").forEach(b => {
  b.addEventListener("click", () => openModal(b.dataset.mode));
});

el("closeModal")?.addEventListener("click", () =>
  el("inputModal")?.classList.add("hidden")
);
el("cancelBtn")?.addEventListener("click", () =>
  el("inputModal")?.classList.add("hidden")
);

/* ======================= ANALYZE ======================= */
el("analyzeBtn")?.addEventListener("click", async function () {
  const name = el("name")?.value.trim();
  const description = el("description")?.value.trim();
  if (!name || !description) {
  el("formStatus").textContent = "Startup name and description required.";
  return;
}




  const industry = Array.from(
    document.querySelectorAll('input[name="industry"]:checked')
  ).map(i => i.value).join(", ");

 el("formStatus").innerHTML = `
  <div class="loading">
    <span class="spinner"></span>
    <span>Running AI analysis...</span>
  </div>
`;


  const resp = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      name,
      description,
      industry,
      mode: this.dataset.mode
    })
  });

  const j = await resp.json();
  if (resp.ok) location.href = `/report.html?id=${j.id}`;
  else el("formStatus").textContent = j.error || "Error";
});

/* ======================= HISTORY ======================= */
async function fetchHistory() {
  const list = el("historyList");
  if (!list) return;

  list.innerHTML = `
  <div class="loading loading-center">
    <span class="spinner"></span>
    <span>Loading reports...</span>
  </div>
`;

  const r = await fetch("/api/history");
  const j = await r.json();

  list.innerHTML = "";
  if (!j.items || !j.items.length) {
    list.innerHTML = "<div class='muted'>No reports</div>";
    return;
  }

  j.items.forEach(it => {
    const d = document.createElement("div");
    d.className = "history-item";
   d.innerHTML = `
  <div class="history-row">
    <div class="history-info">
      <strong>${it.name || "Unnamed"}</strong>
      <span class="muted">(${it.industry || "General"})</span>
    </div>

    <div class="history-actions">
      <a
        href="/report.html?id=${it.id}"
        class="btn ghost small-btn"
      >
        👁 View
      </a>

      <a
        href="/api/pdf/${it.id}"
        target="_blank"
        class="btn primary small-btn"
      >
        📄 Download PDF
      </a>
    </div>
  </div>
`;

    list.appendChild(d);
  });
}
if (document.getElementById("historyList")) {
  fetchHistory();
}


/* ======================= LOGOUT BTN ======================= */
el("logoutBtn")?.addEventListener("click", handleLogout);

/* ======================= INDUSTRY DROPDOWNS (ALL) ======================= */
const glow = document.getElementById("cursor-glow");

let mouseX = 0, mouseY = 0;
let currentX = 0, currentY = 0;

const glowSize = 320;

// ✅ THIS WAS MISSING
document.addEventListener("pointermove", (e) => {
  mouseX = e.clientX;
  mouseY = e.clientY;
});

function animateGlow() {
  currentX += (mouseX - currentX) * 0.25;
  currentY += (mouseY - currentY) * 0.25;

  if (glow) {
    glow.style.transform = `translate(
      ${currentX - glowSize / 2}px,
      ${currentY - glowSize / 2}px
    )`;
  }

  requestAnimationFrame(animateGlow);
}

// ✅ start loop
requestAnimationFrame(animateGlow);
/* ======================= INDUSTRY DROPDOWNS ======================= */

document.querySelectorAll(".dropdown-toggle").forEach(toggle => {
  toggle.addEventListener("click", () => {
    const targetId = toggle.dataset.target;
    const target = document.getElementById(targetId);

    if (!target) return;

    // toggle visibility
    target.classList.toggle("hidden");

    // rotate arrow
    toggle.classList.toggle("open");
  });
});

/* ======================= INDUSTRY OTHER INPUT ======================= */
const otherCheck = document.getElementById("industryOtherCheck");
const otherInput = document.getElementById("industryOtherInput");

if (otherCheck && otherInput) {
  otherCheck.addEventListener("change", () => {
    if (otherCheck.checked) {
      otherInput.classList.remove("hidden");
      otherInput.focus();
    } else {
      otherInput.classList.add("hidden");
      otherInput.value = "";
    }
  });
}
/* ===== Force select text color to match inputs exactly ===== */
const stageSelect = document.getElementById("stage");

if (stageSelect) {
  const syncStageColor = () => {
    if (stageSelect.value === "") {
      stageSelect.style.color = "#9aa0a6"; // placeholder grey (same as inputs)
    } else {
      stageSelect.style.color = "#e9e9ea"; // input text white
    }
  };

  // run once on load
  syncStageColor();

  // update on change
  stageSelect.addEventListener("change", syncStageColor);
}
