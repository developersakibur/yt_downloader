document.addEventListener("DOMContentLoaded", () => {
  const ytForm = document.getElementById("youtube-form");
  const notYt = document.getElementById("not-youtube");
  const serverDown = document.getElementById("server-down");
  const status = document.getElementById("status");

  const checkServerStatus = async () => {
    try {
      const res = await fetch("http://yt_downloader.local/api/status");
      if (res.ok) {
        return true;
      }
    } catch (e) {}
    return false;
  };

  const showView = (view) => {
    [ytForm, notYt, serverDown].forEach((v) => v.classList.add("hidden"));
    view.classList.remove("hidden");
  };

  document.getElementById("startServerBtn").addEventListener("click", () => {
    chrome.runtime.sendNativeMessage(
      "com.sakib.ytdownloader",
      { action: "start_server" },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError);
          status.textContent = "❌ Native host error.";
          return;
        }
        if (response && response.server_url) {
          chrome.tabs.create({ url: response.server_url });
        }
        status.textContent = "✅ Server start signal sent. Please wait a moment and reopen the extension.";
      }
    );
  });

  checkServerStatus().then((isServerRunning) => {
    if (!isServerRunning) {
      showView(serverDown);
      return;
    }

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const currentUrl = tabs[0]?.url || "";
      const quantityRow = document.getElementById("quantity-row");
      const playlistRow = document.getElementById("playlist-row");

      if (currentUrl.includes("youtube.com")) {
        showView(ytForm);
        status.textContent = "Ready";

        if (currentUrl.includes("youtube.com/results?search_query=")) {
          quantityRow.classList.remove("hidden");
          playlistRow.classList.add("hidden");
        } else if (currentUrl.includes("watch?v=") && currentUrl.includes("list=")) {
          quantityRow.classList.add("hidden");
          playlistRow.classList.remove("hidden");
        } else {
          quantityRow.classList.add("hidden");
          playlistRow.classList.add("hidden");
        }
      } else {
        showView(notYt);
      }
    });
  });

  document.getElementById("downloadBtn").addEventListener("click", async () => {
    const format = document.querySelector("input[name='format']:checked").value;
    const quantity = document.querySelector("input[name='quantity']:checked").value;
    const playlist = document.querySelector("input[name='playlist']:checked").value;
    status.textContent = "Sending...";
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      const res = await fetch("http://yt_downloader.local/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: tabs[0].url, format, quantity, playlist})
      });
      const data = await res.json();
      if (data.ok) {
        status.textContent = "Sent";
      } else {
        status.textContent = "❌ " + (data.error || "server error");
      }
    } catch (e) {
      status.textContent = "❌ Cannot reach server";
    }
  });
}); 