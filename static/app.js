const $ = (id) => document.getElementById(id);
const drop = $("drop"), input = $("file"), dropText = $("dropText");
const go = $("go"), statusEl = $("status"), result = $("result");
const before = $("before"), after = $("after"), download = $("download");

const beforeWrap = $("beforeWrap");
const EXTS = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wma", ".aif", ".aiff",
  ".caf", ".amr", ".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".3gp"];

let file = null;
let strength = "medium";
let urls = [];

// Some formats (e.g. MKV, AVI, WMA) can't play in the browser: hide the "Original" player then.
before.addEventListener("error", () => { if (before.src) beforeWrap.hidden = true; });

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.classList.toggle("error", isError);
}

function pick(f) {
  if (!f) return;
  const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
  if (!EXTS.includes(ext)) {
    setStatus("That file type isn't supported. Try MP3, WAV, M4A, MP4 or MOV.", true);
    return;
  }
  file = f;
  dropText.innerHTML = "";
  const name = document.createElement("strong");
  name.textContent = f.name;
  dropText.append(name, ` · ${(f.size / 1024 / 1024).toFixed(1)} MB`);
  drop.classList.add("has-file");
  go.disabled = false;
  result.hidden = true;
  setStatus("");
}

input.addEventListener("change", () => pick(input.files[0]));

["dragenter", "dragover"].forEach((e) =>
  drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("over"); })
);
["dragleave", "drop"].forEach((e) =>
  drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove("over"); })
);
drop.addEventListener("drop", (ev) => pick(ev.dataTransfer.files[0]));

document.querySelectorAll(".seg button").forEach((btn) =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-checked", "false"));
    btn.setAttribute("aria-checked", "true");
    strength = btn.dataset.v;
  })
);

go.addEventListener("click", async () => {
  if (!file) return;
  go.disabled = true;
  go.innerHTML = '<span class="spinner"></span> Cleaning…';
  setStatus("");
  result.hidden = true;

  const body = new FormData();
  body.append("file", file);
  body.append("strength", strength);

  try {
    const res = await fetch("/api/clean", { method: "POST", body });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Something went wrong.");
    }
    const blob = await res.blob();

    urls.forEach(URL.revokeObjectURL);
    urls = [URL.createObjectURL(file), URL.createObjectURL(blob)];
    beforeWrap.hidden = false;
    before.src = urls[0];
    after.src = urls[1];
    download.href = urls[1];
    download.download = file.name.replace(/\.[^.]+$/, "") + "-clean.mp3";
    result.hidden = false;
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    go.disabled = false;
    go.textContent = "Clean audio";
  }
});
