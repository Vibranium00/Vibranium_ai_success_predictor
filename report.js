const params = new URLSearchParams(window.location.search);
const id = params.get("id");

if (!id) {
  alert("Invalid report");
  location.href = "/";
}
// 🔗 Bind analysis ID to feedback form
const analysisIdInput = document.getElementById("analysisId");
if (analysisIdInput) {
  analysisIdInput.value = id;
}


async function loadReport() {
  const reportEl = document.getElementById("reportContent");

  // ✅ 1. SHOW LOADER FIRST
  reportEl.innerHTML = `
    <div class="loading loading-center">
      <span class="spinner"></span>
      <span>Loading report...</span>
    </div>
  `;

  // small delay to allow paint (important)
  await new Promise(r => setTimeout(r, 50));

  // ✅ 2. FETCH REPORT
  const res = await fetch(`/api/report/${id}`, {
    credentials: "include"
  });

  if (!res.ok) {
    reportEl.innerHTML = "<p class='muted'>Failed to load report.</p>";
    return;
  }

  const data = await res.json();

  // header info (unchanged)
  document.getElementById("startupName").innerText =
    data.name || "Startup Analysis";

  document.getElementById("metaInfo").innerText =
    `Industry: ${data.industry || "General"} • Mode: ${data.mode || "N/A"}`;

  // ✅ 3. REPLACE LOADER WITH REPORT
  renderScores(data.result);
  reportEl.innerHTML = data.result
    ? marked.parse(data.result)
    : "<p class='muted'>No analysis found.</p>";

  // emoji logic (unchanged)
  reportEl.querySelectorAll("h1, h2, h3").forEach(h => {
    const text = h.textContent.toLowerCase();
    if (text.includes("overall")) h.prepend("🌟 ");
    else if (text.includes("strength")) h.prepend("💪 ");
    else if (text.includes("weakness")) h.prepend("⚠️ ");
    else if (text.includes("risk")) h.prepend("🚨 ");
    else if (text.includes("recommendation")) h.prepend("📈 ");
    else if (text.includes("score")) h.prepend("📊 ");
  });

  document.getElementById("pdfBtn").href = `/api/pdf/${data.id}`;
}

loadReport();
/* ======================= FEEDBACK ======================= */
async function submitFeedback() {
  const rating = document.getElementById("rating").value;
  const helpful = document.getElementById("helpful").value === "true";
  const comment = document.getElementById("comment").value;

  try {
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        analysis_id: id,
        rating,
        helpful,
        comment
      })
    });

    const data = await res.json();

    document.getElementById("feedbackStatus").innerText =
      res.ok
        ? "✅ Feedback submitted. Thank you!"
        : (data.error || "❌ Failed to submit feedback");

  } catch (e) {
    document.getElementById("feedbackStatus").innerText =
      "❌ Network error. Please try again.";
  }
}
// ==============Render score================//
function renderScores(markdown) {
  if (!markdown) return;

  const scoreSection = document.getElementById("scoreSection");
  const barsContainer = document.getElementById("scoreBars");
  const overallEl = document.getElementById("overallScore");

  // Extract overall score
  const overallMatch = markdown.match(/Score:\s*(\d+)\s*\/\s*100/i);
  if (overallMatch) {
    const score = parseInt(overallMatch[1]);
    overallEl.innerHTML = `
      <div class="overall-number">${score}</div>
      <div class="overall-label">Overall Score</div>
    `;
  }

  // Extract table rows
  const rowRegex = /\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|/g;
  let match;
  barsContainer.innerHTML = "";

  while ((match = rowRegex.exec(markdown)) !== null) {
    const label = match[1];
    const value = parseInt(match[2]);

    barsContainer.innerHTML += `
      <div class="score-bar">
        <div class="score-label">${label}</div>
        <div class="bar-bg">
          <div class="bar-fill" style="width:${value}%"></div>
        </div>
        <div class="score-value">${value}</div>
      </div>
    `;
  }

  scoreSection.classList.remove("hidden");
}


