// BEFORE-UNLOAD WARNING

let blockUnload = false;

window.addEventListener("beforeunload", (event) => {
  if (blockUnload) {
    event.preventDefault();
    event.returnValue = ""; // required for Chrome
  }
});

// INJECT FILE INTO VUE COMPONENT'S <input type="file">

function injectFileIntoInput(fileInputEl, file) {
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  fileInputEl.files = dataTransfer.files;

  // Dispatch change event so Vue's v-model / @change handler picks it up
  fileInputEl.dispatchEvent(new Event("change", { bubbles: true }));
}

// CSRF HELPER

function getCsrfToken() {
  const input = document.querySelector("[name=csrfmiddlewaretoken]");
  if (!input) throw new Error("CSRF token input not found in DOM.");
  return input.value;
}

// MAIN DOWNLOAD + INJECT FLOW

async function fetchAndInjectTikTokData(fileInputEl, downloadUrl) {
  blockUnload = true;

  try {
    const response = await fetch(downloadUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    if (!response.ok) {

      if (response.status === 404) {
        const redirect_url = document.getElementById("fail-redirect-url")?.value;

        if (redirect_url) {
          window.location.href = redirect_url;
          return;
        }
      }
      // TODO: Handle other errors
      throw new Error(`Server error: ${response.status} ${response.statusText}`);
    }

    // Consume the chunked stream and collect into a single Blob
    const reader = response.body.getReader();
    const chunks = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }

    const blob = new Blob(chunks, { type: "application/zip" });
    const file = new File([blob], "tiktok_data.zip", { type: "application/zip" });

    // TODO: Enable to inspect received file.
    //  must be added to script block: <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    // const zip = await JSZip.loadAsync(blob);
    // for (const [filename, zipEntry] of Object.entries(zip.files)) {
    //   if (!zipEntry.dir) {
    //     const content = await zipEntry.async("string");
    //     console.log(`--- ${filename} ---`);
    //     console.log(JSON.parse(content)); // or just content if not JSON
    //   }
    // }

    injectFileIntoInput(fileInputEl, file);

  } catch (error) {
    console.error("TikTok data download failed:", error);
    // TODO
    throw error;
  } finally {
    // Only unblock navigation once Vue component has taken over
    blockUnload = false;
  }
}

// ENTRY POINT

function waitForFileInput(selector, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const el = document.querySelector(selector);
    if (el) return resolve(el);

    const observer = new MutationObserver(() => {
      const el = document.querySelector(selector);
      if (el) {
        observer.disconnect();
        resolve(el);
      }
    });

    observer.observe(document.getElementById("uapp"), {
      childList: true,
      subtree: true,
    });

    setTimeout(() => {
      observer.disconnect();
      reject(new Error("Timed out waiting for Vue file input to appear."));
    }, timeout);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  const DOWNLOAD_URL = document.getElementById("tiktok-download-url")?.value;
  if (!DOWNLOAD_URL) {
    console.error("Download URL not found in DOM.");
    return;
  }

  try {
    const fileInput = await waitForFileInput("#uapp input[type='file']");
    await fetchAndInjectTikTokData(fileInput, DOWNLOAD_URL);
  } catch (error) {
    console.error("TikTok auto-download failed:", error);
  }
});
