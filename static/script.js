// -------------------- Real-time clock --------------------
function updateDateTime() {
  const el = document.getElementById("datetime");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}
setInterval(updateDateTime, 1000);
updateDateTime();

// -------------------- Roses animation --------------------
// Use a default rose image or emoji fallback.
const ROSE_SRC = "/static/img/rose.png"; // Ensure this file exists in static/img/
function spawnRose() {
  const container = document.querySelector(".animated-roses");
  if (!container) return;
  const r = document.createElement("img");
  r.className = "rose";
  r.onerror = function () {
    r.style.width = "28px";
    r.src = "data:image/svg+xml;utf8," + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'><text x='0' y='48' font-size='48'>🌹</text></svg>`);
  };
  r.src = ROSE_SRC;
  r.style.left = Math.random() * 100 + "vw";
  r.style.animationDuration = (6 + Math.random() * 6) + "s";
  r.style.transform = `scale(${0.6 + Math.random() * 1.0}) rotate(${Math.random() * 60 - 30}deg)`;
  container.appendChild(r);
  setTimeout(() => { r.remove(); }, 12000);
}
setInterval(spawnRose, 1400);

// -------------------- Image preview on upload --------------------
function previewLocal(input) {
  const file = input.files && input.files[0];
  const preview = document.getElementById("preview");
  if (!file || !preview) return;
  const url = URL.createObjectURL(file);
  preview.src = url;
  preview.style.display = "block";
}

// -------------------- Modal image viewer (client-side enhancement) --------------------
document.addEventListener("click", (e) => {
  const target = e.target;
  if (target.tagName === "IMG" && target.closest(".gallery")) {
    openImageModal(target.src);
  }
});

function openImageModal(src) {
  let modal = document.getElementById("image-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "image-modal";
    modal.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:9999;";
    modal.innerHTML = `<div style="max-width:95%;max-height:95%"><img id="image-modal-img" style="max-width:100%;max-height:100%;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,0.5)"></div>`;
    modal.addEventListener("click", () => modal.remove());
    document.body.appendChild(modal);
  }
  document.getElementById("image-modal-img").src = src;
}

// -------------------- Deletion Debugging --------------------
document.addEventListener("submit", (e) => {
  if (e.target.matches(".delete-form")) {
    console.log("Delete form submitted for index:", e.target.action.match(/delete_image\/(\d+)/)[1]);
    e.target.querySelector(".delete-btn").disabled = true;
    e.target.querySelector(".loading-spinner").style.display = "inline-block";
    e.target.querySelector(".btn-text").style.display = "none";
  }
});