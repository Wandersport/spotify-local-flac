const fs = require('fs');

async function main() {
  console.log("==========================================================");
  console.log("  Live Spotify Folder Navigation & Playback Regression Test");
  console.log("==========================================================\n");

  const tabsRes = await fetch("http://127.0.0.1:9222/json");
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes("xpui.app.spotify.com")) || tabs[0];
  const wsUrl = pageTab.webSocketDebuggerUrl;
  console.log(`Connecting to CDP at ${wsUrl}...`);

  const ws = new WebSocket(wsUrl);
  await new Promise(r => ws.onopen = r);
  console.log("✔ Connected to Spotify CDP WebSocket\n");

  let reqId = 0;
  const pending = new Map();

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  };

  function send(method, params = {}) {
    return new Promise((resolve) => {
      reqId++;
      const id = reqId;
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async function evaluate(expression) {
    const res = await send("Runtime.evaluate", { expression, returnByValue: true });
    if (res.result?.exceptionDetails) {
      console.error("Eval Exception:", res.result.exceptionDetails);
    }
    return res.result?.result?.value;
  }

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  async function assertState(stepName) {
    const isFlacRoute = await evaluate(`document.body.classList.contains("local-flac-route-active")`);
    const appRootVisible = await evaluate(`!document.getElementById("local-flac-app-root")?.classList.contains("hidden")`);
    const sidebarActive = await evaluate(`document.getElementById("sidebar-local-flac-row")?.classList.contains("active")`);
    const isNativeVisible = await evaluate(`(() => {
      const main = document.querySelector("main");
      if (!main) return false;
      const style = window.getComputedStyle(main);
      return style.display !== "none";
    })()`);

    console.log(`  [State check: ${stepName}]`);
    console.log(`    - Route active class: ${isFlacRoute}`);
    console.log(`    - App root visible: ${appRootVisible}`);
    console.log(`    - Sidebar row active: ${sidebarActive}`);
    console.log(`    - Native Spotify main hidden: ${!isNativeVisible}`);

    if (!isFlacRoute || !appRootVisible || !sidebarActive || isNativeVisible) {
      throw new Error(`State assertion failed at "${stepName}"! Local FLAC UI lost or native content took over.`);
    }
  }

  // --- 1. Open /local-flac ---
  console.log("--- 1. Navigating to /local-flac ---");
  await evaluate(`window.Spicetify.Platform.History.push("/local-flac")`);
  await sleep(600);
  await assertState("Initial /local-flac load");

  // --- 2. Click Folders ---
  console.log("\n--- 2. Clicking Folders Tab ---");
  await evaluate(`(() => {
    const b = Array.from(document.querySelectorAll(".lf-tab-btn")).find(x => x.textContent.includes("Folders"));
    if (b) b.click();
  })()`);
  await sleep(600);
  await assertState("Folders tab view");

  const crumbsRoot = await evaluate(`Array.from(document.querySelectorAll(".lf-crumb-item")).map(x => x.textContent)`);
  const rootRows = await evaluate(`Array.from(document.querySelectorAll(".lf-folder-name")).map(x => x.textContent)`);
  console.log("  Breadcrumbs:", crumbsRoot);
  console.log("  Roots found:", rootRows);
  if (!crumbsRoot.some(c => c.includes("Library Roots"))) {
    throw new Error("Library Roots breadcrumb missing!");
  }

  // --- 3. Enter top-level folder ---
  console.log("\n--- 3. Entering Top-Level Folder [NEW MUSIC FOLDERS] ---");
  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("NEW MUSIC FOLDERS"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("Top-level folder [NEW MUSIC FOLDERS]");

  const crumbs1 = await evaluate(`Array.from(document.querySelectorAll(".lf-crumb-item")).map(x => x.textContent)`);
  console.log("  Breadcrumbs:", crumbs1);
  if (!crumbs1.some(c => c.includes("NEW MUSIC FOLDERS"))) {
    throw new Error("Breadcrumbs did not update to [NEW MUSIC FOLDERS]!");
  }

  // --- 4. Enter nested folder 1: [Gunna] ---
  console.log("\n--- 4. Entering Nested Folder [Gunna] ---");
  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("Gunna"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("Nested folder [Gunna]");

  const crumbs2 = await evaluate(`Array.from(document.querySelectorAll(".lf-crumb-item")).map(x => x.textContent)`);
  console.log("  Breadcrumbs:", crumbs2);

  // --- 5. Enter nested folder 2: ⭐ Best ---
  console.log("\n--- 5. Entering Nested Folder ⭐ Best ---");
  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("Best"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("Nested folder ⭐ Best");

  const crumbs3 = await evaluate(`Array.from(document.querySelectorAll(".lf-crumb-item")).map(x => x.textContent)`);
  console.log("  Breadcrumbs:", crumbs3);

  // --- 6. Enter nested album folder: 10 - Drip or Drown 2 ---
  console.log("\n--- 6. Entering Album Folder 10 - Drip or Drown 2 ---");
  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("Drip or Drown 2"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("Album folder 10 - Drip or Drown 2");

  const trackRowsCount = await evaluate(`document.querySelectorAll(".lf-folder-row-track").length`);
  console.log(`  Tracks in folder: ${trackRowsCount}`);
  if (trackRowsCount === 0) {
    throw new Error("No tracks displayed in 10 - Drip or Drown 2!");
  }

  // --- 7. Go back one level ---
  console.log("\n--- 7. Going Back One Level (via Up button) ---");
  await evaluate(`(() => {
    const btn = document.querySelector(".lf-folder-up-btn");
    if (btn) btn.click();
  })()`);
  await sleep(600);
  await assertState("Back to ⭐ Best");
  console.log("  Breadcrumbs:", await evaluate(`Array.from(document.querySelectorAll(".lf-crumb-item")).map(x => x.textContent)`));

  // --- 8. Return to Library Roots ---
  console.log("\n--- 8. Returning to Library Roots (via breadcrumb) ---");
  await evaluate(`(() => {
    const rootCrumb = Array.from(document.querySelectorAll(".lf-crumb-item")).find(x => x.textContent.includes("Library Roots"));
    if (rootCrumb) rootCrumb.click();
  })()`);
  await sleep(600);
  await assertState("Back to Library Roots");
  console.log("  Breadcrumbs:", await evaluate(`Array.from(document.querySelectorAll(".lf-crumb-item")).map(x => x.textContent)`));

  // --- 9. Repeat While a FLAC is Playing ---
  console.log("\n==========================================================");
  console.log("  9. REPEAT WHILE FLAC IS ACTIVELY PLAYING");
  console.log("==========================================================");

  // Start playing a FLAC track from FLAC Only tab
  console.log("\n  Switching to FLAC Only tab and starting playback...");
  await evaluate(`(() => {
    const b = Array.from(document.querySelectorAll(".lf-tab-btn")).find(x => x.textContent.includes("FLAC Only"));
    if (b) b.click();
  })()`);
  await sleep(600);

  await evaluate(`(() => {
    if (!window.LocalFlacPlayer?.isPlaying) {
      const firstTrackRow = document.querySelector(".lf-track-row");
      if (firstTrackRow) {
        firstTrackRow.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
      }
    }
  })()`);
  await sleep(1000);

  const isPlaying = await evaluate(`window.LocalFlacPlayer?.isPlaying && window.LocalFlacPlayer?.playbackOwner === "LOCAL_FLAC"`);
  const currentTitle = await evaluate(`window.LocalFlacPlayer?.currentTrack?.title`);
  console.log(`  Audio playback started: isPlaying=${isPlaying}, track="${currentTitle}"`);

  // Navigate Folders tab while playing
  console.log("\n  Clicking Folders tab while audio plays...");
  await evaluate(`(() => {
    const b = Array.from(document.querySelectorAll(".lf-tab-btn")).find(x => x.textContent.includes("Folders"));
    if (b) b.click();
  })()`);
  await sleep(600);
  await assertState("Folders tab during playback");

  let stillPlaying = await evaluate(`window.LocalFlacPlayer?.isPlaying && window.LocalFlacPlayer?.playbackOwner === "LOCAL_FLAC"`);
  console.log(`    - Audio still playing: ${stillPlaying}`);
  if (!stillPlaying) throw new Error("Playback was interrupted when clicking Folders tab!");

  // Drill into [NEW MUSIC FOLDERS]
  console.log("\n  Drilling into [NEW MUSIC FOLDERS] while playing...");
  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("NEW MUSIC FOLDERS"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("[NEW MUSIC FOLDERS] during playback");

  stillPlaying = await evaluate(`window.LocalFlacPlayer?.isPlaying && window.LocalFlacPlayer?.playbackOwner === "LOCAL_FLAC"`);
  console.log(`    - Audio still playing: ${stillPlaying}`);
  if (!stillPlaying) throw new Error("Playback was interrupted when opening folder!");

  // Drill into [Gunna] -> ⭐ Best -> 10 - Drip or Drown 2
  console.log("\n  Drilling into nested subfolders while playing...");
  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("Gunna"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("[Gunna] during playback");

  await evaluate(`(() => {
    const row = Array.from(document.querySelectorAll(".lf-folder-row")).find(x => x.textContent.includes("Best"));
    if (row) row.click();
  })()`);
  await sleep(600);
  await assertState("⭐ Best during playback");

  stillPlaying = await evaluate(`window.LocalFlacPlayer?.isPlaying && window.LocalFlacPlayer?.playbackOwner === "LOCAL_FLAC"`);
  console.log(`    - Audio still playing: ${stillPlaying}`);
  if (!stillPlaying) throw new Error("Playback was interrupted in nested folder!");

  // Return to Library Roots
  console.log("\n  Returning to Library Roots via breadcrumb while playing...");
  await evaluate(`(() => {
    const rootCrumb = Array.from(document.querySelectorAll(".lf-crumb-item")).find(x => x.textContent.includes("Library Roots"));
    if (rootCrumb) rootCrumb.click();
  })()`);
  await sleep(600);
  await assertState("Library Roots during playback");

  stillPlaying = await evaluate(`window.LocalFlacPlayer?.isPlaying && window.LocalFlacPlayer?.playbackOwner === "LOCAL_FLAC"`);
  console.log(`    - Audio still playing: ${stillPlaying}`);
  if (!stillPlaying) throw new Error("Playback was interrupted when returning to roots!");

  // --- 10. Test Spotify Native Takeover & Local FLAC Return ---
  console.log("\n--- 10. Testing Spotify Native Navigation & Return ---");
  await evaluate(`window.Spicetify.Platform.History.push("/")`);
  await sleep(600);
  const homeNativeVisible = await evaluate(`(() => {
    const main = document.querySelector("main");
    return main && window.getComputedStyle(main).display !== "none";
  })()`);
  const flacActiveOnHome = await evaluate(`document.body.classList.contains("local-flac-route-active")`);
  console.log(`  On Spotify Home (/): native main visible = ${homeNativeVisible}, local flac active = ${flacActiveOnHome}`);
  if (!homeNativeVisible || flacActiveOnHome) {
    throw new Error("Spotify native home route did not activate properly!");
  }

  // Return to /local-flac
  await evaluate(`window.Spicetify.Platform.History.push("/local-flac")`);
  await sleep(600);
  await assertState("Return to /local-flac from Spotify Home");

  console.log("\n==========================================================");
  console.log("  ✔ REGRESSION TEST COMPLETE: ALL CHECKS PASSED!");
  console.log("==========================================================");

  ws.close();
}

main().catch(err => {
  console.error("\n❌ TEST FAILED:", err.message);
  process.exit(1);
});
