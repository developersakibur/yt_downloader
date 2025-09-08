document.addEventListener("DOMContentLoaded", () => {
  const urlInput = document.getElementById("videoUrl");
  const quantityRow = document.getElementById("quantity-row");
  const playlistRow = document.getElementById("playlist-row");
  const downloadBtn = document.getElementById("download-btn");

  function updateUI(url) {
    if (!url.includes("youtube.com")) {
      quantityRow.classList.add("hidden");
      playlistRow.classList.add("hidden");
      downloadBtn.disabled = true; // disable if not valid
      return;
    }
    downloadBtn.disabled = false; // enable only if valid YT link
    if (url.includes("youtube.com/results?search_query=")) {
      quantityRow.classList.remove("hidden");
      playlistRow.classList.add("hidden");
    } else if (url.includes("watch?v=") && url.includes("list=")) {
      quantityRow.classList.add("hidden");
      playlistRow.classList.remove("hidden");
    } else {
      quantityRow.classList.add("hidden");
      playlistRow.classList.add("hidden");
    }
  }

  // update on every input change
  urlInput.addEventListener("input", (e) => {
    updateUI(e.target.value.trim());
  });

  downloadBtn.addEventListener("click", async () => {
    const body = JSON.stringify({
      urlInput: videoUrlInput.value.trim(),
      format: document.querySelector("input[name='format']:checked")?.value,
      quantity: document.querySelector("input[name='quantity']:checked")?.value,
      playlist: document.querySelector("input[name='playlist']:checked")?.value,
    });

    await fetch("http://yt_downloader.local/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
  });
});
