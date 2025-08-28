// static/app.js
async function api(path, opts={}){
  const res = await fetch("/api"+path, Object.assign({headers:{"Content-Type":"application/json"}}, opts));
  return res.json();
}

function getSelectedValue(name){
  const r = document.querySelector(`input[name='${name}']:checked`);
  return r ? r.value : null;
}

let progressInterval = null;

const videoUrlInput = document.getElementById('videoUrl');
const quantityContainer = document.getElementById('quantity-container');
const playlistRow = document.getElementById('playlistRow');

videoUrlInput.addEventListener('input', () => {
    const url = videoUrlInput.value.trim();
    if (url.includes('search_query')) {
        quantityContainer.style.display = 'block';
    } else {
        quantityContainer.style.display = 'none';
    }

    // Show/hide playlist row based on URL
    if (url.includes('watch') && url.includes('list')) {
        playlistRow.style.display = 'block';
    } else {
        playlistRow.style.display = 'none';
    }
});

// Trigger the event once on page load to set the initial state
videoUrlInput.dispatchEvent(new Event('input'));


document.getElementById("downloadBtn").addEventListener("click", async () =>{
  const url = videoUrlInput.value.trim();
  const downloadPath = document.getElementById("downloadPath").value.trim(); // Get download path
  const fmt = getSelectedValue("format");
  const quantity = getSelectedValue("quantity");
  const playlist = getSelectedValue("playlist") === "yes"; // Convert to boolean

  if(!url){ alert("Please enter URL"); return; }

  // Clear previous progress
  if (progressInterval) {
    clearInterval(progressInterval);
  }
  const progressBox = document.getElementById("progressBox");
  progressBox.textContent = "Starting download...";

  const res = await api("/download", {method:"POST", body:JSON.stringify({url, format: fmt, quantity: quantity, playlist: playlist, download_path: downloadPath})});
  if(res.ok){
    const jobId = res.job_id;
    progressInterval = setInterval(async () => {
      const jobs = await api("/jobs");
      const job = jobs[jobId];
      if (job) {
        const logs = await api(`/jobs/${jobId}/logs`);
        progressBox.textContent = logs.logs.join("\n");
        progressBox.scrollTop = progressBox.scrollHeight;

        if (job.status === "completed" || job.status === "failed" || job.status === "cancelled") {
          clearInterval(progressInterval);
          progressBox.textContent += `\n\nJob ${job.status}.`;
        }
      }
    }, 2000);
  } else {
    progressBox.textContent = "Error: " + res.error;
  }
});
