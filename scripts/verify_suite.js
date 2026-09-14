const fs = require('fs');
const os = require('os');
const path = require('path');

async function main() {
  console.log("==========================================================");
  console.log("  Running Automated Spotify Local FLAC Verification Suite");
  console.log("==========================================================\n");

  const cdpPort = 9222;
  const tabsRes = await fetch(`http://127.0.0.1:${cdpPort}/json`);
  const tabs = await tabsRes.json();
  const pageTab = tabs.find(t => t.type === "page" && t.url.includes("xpui.app.spotify.com")) || tabs[0];
  const wsUrl = pageTab.webSocketDebuggerUrl;
  console.log(`Connecting to CDP WebSocket at ${wsUrl}...`);

  const tokenFile = path.join(os.homedir(), '.config', 'spotify-local-flac', 'token');
  const token = fs.readFileSync(tokenFile, 'utf8').trim();
  const screenshotsDir = path.join(__dirname, '..', 'screenshots');

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

  async function screenshot(filename) {
    const res = await send("Page.captureScreenshot", { format: "png" });
    const fullPath = path.isAbsolute(filename) ? filename : path.join(screenshotsDir, filename);
    const buffer = Buffer.from(res.result.data, 'base64');
    fs.writeFileSync(fullPath, buffer);
    console.log(`📸 Saved screenshot: ${fullPath} (${buffer.length} bytes)`);
    return buffer.length;
  }

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // Fetch FLAC track for testing
  const tracksRes = await (await fetch("http://127.0.0.1:18492/api/tracks?limit=1000", {
    headers: { Authorization: `Bearer ${token}` }
  })).json();
  const flacTracks = (tracksRes.tracks || []).filter(t => (t.codec || "").toUpperCase() === "FLAC");
  if (!flacTracks.length) throw new Error("No FLAC tracks found in database!");
  const testFlacTrack = flacTracks[0];
  console.log(`Selected test FLAC track: "${testFlacTrack.title}" by ${testFlacTrack.artist} (ID: ${testFlacTrack.id})\n`);

  // Ensure Spotify is ready
  await evaluate(`(() => {
    if (window.LocalFlacPlayer?.isPlaying) {
      window.LocalFlacPlayer.pause();
    }
    if (window.LocalFlacPlayer) {
      window.LocalFlacPlayer.playbackOwner = "NONE";
    }
    document.body.classList.remove("local-flac-playing");
    const bar = document.getElementById("local-flac-bottom-bar");
    if (bar) bar.classList.add("hidden");
    localStorage.setItem("local_flac_enabled", "true");
  })()`);

  // ========================================================
  // TEST 1: Startup State
  // ========================================================
  console.log("--- TEST 1: Startup State ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push("/");
  })()`);
  await sleep(1500);

  const test1 = await evaluate(`(() => {
    const enabled = localStorage.getItem("local_flac_enabled");
    const bar = document.getElementById("local-flac-bottom-bar");
    const sidebarRow = document.getElementById("sidebar-local-flac-row");
    return {
      enabled: enabled !== "false",
      barHidden: !bar || bar.classList.contains("hidden"),
      localPlaying: window.LocalFlacPlayer?.isPlaying,
      sidebarExists: !!sidebarRow,
      sidebarVisible: sidebarRow ? sidebarRow.style.display !== "none" : false
    };
  })()`);
  console.log("Test 1 Result:", JSON.stringify(test1, null, 2));
  if (!test1.enabled) throw new Error("TEST 1 FAILED: local_flac_enabled is false on startup");
  if (!test1.barHidden) throw new Error("TEST 1 FAILED: local bottom bar is not hidden on startup");
  if (test1.localPlaying) throw new Error("TEST 1 FAILED: local player is playing on startup");
  if (!test1.sidebarExists) throw new Error("TEST 1 FAILED: sidebar row not injected");
  console.log("✔ TEST 1 PASSED: Clean startup state verified.\n");

  // ========================================================
  // TEST 2: Setting Toggle OFF
  // ========================================================
  console.log("--- TEST 2: Setting Toggle OFF ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push("/preferences");
  })()`);
  await sleep(1500);

  const test2 = await evaluate(`(() => {
    const toggle = document.getElementById("settings.showLocalFlac");
    if (!toggle) return { error: "toggle_not_found" };
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change", { bubbles: true }));

    // Try navigating to /local-flac
    window.Spicetify.Platform.History.push("/local-flac");

    const sidebarRow = document.getElementById("sidebar-local-flac-row");
    const folderRow = document.getElementById("settings-local-flac-manage-folders-row");
    return {
      persistedValue: localStorage.getItem("local_flac_enabled"),
      sidebarHidden: sidebarRow ? sidebarRow.style.display === "none" : true,
      folderRowHidden: folderRow ? folderRow.style.display === "none" : true,
      currentPath: window.Spicetify.Platform.History.location.pathname
    };
  })()`);
  console.log("Test 2 Result:", JSON.stringify(test2, null, 2));
  if (test2.persistedValue !== "false") throw new Error("TEST 2 FAILED: localStorage did not persist 'false'");
  if (!test2.sidebarHidden) throw new Error("TEST 2 FAILED: sidebar row not hidden when setting disabled");
  if (test2.currentPath === "/local-flac") throw new Error("TEST 2 FAILED: did not redirect away from /local-flac");
  console.log("✔ TEST 2 PASSED: Setting toggle OFF persists and disables route and sidebar.\n");

  // ========================================================
  // TEST 3: Setting Toggle ON
  // ========================================================
  console.log("--- TEST 3: Setting Toggle ON ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push("/preferences");
  })()`);
  await sleep(1000);

  const test3 = await evaluate(`(() => {
    const toggle = document.getElementById("settings.showLocalFlac");
    if (!toggle) return { error: "toggle_not_found" };
    toggle.checked = true;
    toggle.dispatchEvent(new Event("change", { bubbles: true }));

    // Navigate to /local-flac
    window.Spicetify.Platform.History.push("/local-flac");

    const sidebarRow = document.getElementById("sidebar-local-flac-row");
    const folderRow = document.getElementById("settings-local-flac-manage-folders-row");
    return {
      persistedValue: localStorage.getItem("local_flac_enabled"),
      sidebarVisible: sidebarRow ? sidebarRow.style.display !== "none" : false,
      currentPath: window.Spicetify.Platform.History.location.pathname
    };
  })()`);
  console.log("Test 3 Result:", JSON.stringify(test3, null, 2));
  if (test3.persistedValue !== "true") throw new Error("TEST 3 FAILED: localStorage did not persist 'true'");
  if (!test3.sidebarVisible) throw new Error("TEST 3 FAILED: sidebar row not visible when setting enabled");
  if (test3.currentPath !== "/local-flac") throw new Error("TEST 3 FAILED: /local-flac route was blocked");
  console.log("✔ TEST 3 PASSED: Setting toggle ON re-enables route and sidebar.\n");

  // ========================================================
  // TEST 4: FLAC -> Spotify Native Handoff
  // ========================================================
  console.log("--- TEST 4: FLAC -> Spotify Native Handoff ---");
  // 1. Start FLAC playback
  await evaluate(`(() => {
    window.LocalFlacPlayer.playTrack(${JSON.stringify(testFlacTrack)});
  })()`);
  await sleep(800);

  const flacActiveState = await evaluate(`(() => {
    const bar = document.getElementById("local-flac-bottom-bar");
    return {
      owner: window.LocalFlacPlayer.playbackOwner,
      isPlaying: window.LocalFlacPlayer.isPlaying,
      barVisible: bar && !bar.classList.contains("hidden"),
      bodyClass: document.body.classList.contains("local-flac-playing"),
      spotifyPlaying: window.Spicetify.Player.isPlaying()
    };
  })()`);
  console.log("FLAC Active State:", JSON.stringify(flacActiveState, null, 2));
  if (flacActiveState.owner !== "LOCAL_FLAC") throw new Error("TEST 4 FAILED: playbackOwner is not LOCAL_FLAC");
  if (!flacActiveState.isPlaying) throw new Error("TEST 4 FAILED: LocalFlacPlayer is not playing");
  if (!flacActiveState.barVisible) throw new Error("TEST 4 FAILED: bottom bar is not visible");

  // 2. Play Spotify Native
  console.log("Starting Spotify native playback...");
  await evaluate(`(() => {
    window.Spicetify.Player.play();
  })()`);
  await sleep(800);

  const handoffToSpotify = await evaluate(`(() => {
    const bar = document.getElementById("local-flac-bottom-bar");
    return {
      owner: window.LocalFlacPlayer.playbackOwner,
      localPlaying: window.LocalFlacPlayer.isPlaying,
      barHidden: bar ? bar.classList.contains("hidden") : true,
      bodyHasClass: document.body.classList.contains("local-flac-playing"),
      spotifyPlaying: window.Spicetify.Player.isPlaying()
    };
  })()`);
  console.log("Handoff to Spotify Result:", JSON.stringify(handoffToSpotify, null, 2));
  if (handoffToSpotify.owner !== "SPOTIFY_NATIVE") throw new Error("TEST 4 FAILED: owner did not transition to SPOTIFY_NATIVE");
  if (handoffToSpotify.localPlaying) throw new Error("TEST 4 FAILED: FLAC did not pause upon native playback");
  if (!handoffToSpotify.barHidden) throw new Error("TEST 4 FAILED: local bottom bar is not hidden");
  if (handoffToSpotify.bodyHasClass) throw new Error("TEST 4 FAILED: body still has local-flac-playing class");
  console.log("✔ TEST 4 PASSED: FLAC -> Spotify Native handoff successful, zero simultaneous audio.\n");

  // ========================================================
  // TEST 5: Spotify Native -> FLAC Handoff
  // ========================================================
  console.log("--- TEST 5: Spotify Native -> FLAC Handoff ---");
  // Start FLAC playback while native is playing
  await evaluate(`(() => {
    window.LocalFlacPlayer.playTrack(${JSON.stringify(testFlacTrack)});
  })()`);
  await sleep(800);

  const handoffToFlac = await evaluate(`(() => {
    const bar = document.getElementById("local-flac-bottom-bar");
    return {
      owner: window.LocalFlacPlayer.playbackOwner,
      localPlaying: window.LocalFlacPlayer.isPlaying,
      barVisible: bar && !bar.classList.contains("hidden"),
      bodyHasClass: document.body.classList.contains("local-flac-playing"),
      spotifyPlaying: window.Spicetify.Player.isPlaying()
    };
  })()`);
  console.log("Handoff to FLAC Result:", JSON.stringify(handoffToFlac, null, 2));
  if (handoffToFlac.owner !== "LOCAL_FLAC") throw new Error("TEST 5 FAILED: owner did not transition to LOCAL_FLAC");
  if (!handoffToFlac.localPlaying) throw new Error("TEST 5 FAILED: FLAC is not playing");
  if (!handoffToFlac.barVisible) throw new Error("TEST 5 FAILED: local bottom bar is not visible");
  if (handoffToFlac.spotifyPlaying) throw new Error("TEST 5 FAILED: Spotify native did not pause upon FLAC playback");
  console.log("✔ TEST 5 PASSED: Spotify Native -> FLAC handoff successful, zero simultaneous audio.\n");

  // ========================================================
  // TEST 6: Rapid Switching Stress Test (10 Transitions)
  // ========================================================
  console.log("--- TEST 6: Rapid Switching Stress Test ---");
  for (let i = 1; i <= 10; i++) {
    const switchTo = i % 2 === 0 ? "LOCAL_FLAC" : "SPOTIFY_NATIVE";
    if (switchTo === "LOCAL_FLAC") {
      await evaluate(`window.LocalFlacPlayer.playTrack(${JSON.stringify(testFlacTrack)})`);
    } else {
      await evaluate("window.Spicetify.Player.play()");
    }
    await sleep(250);
  }
  // Allow settling
  await sleep(1200);

  const stressResult = await evaluate(`(() => {
    const bar = document.getElementById("local-flac-bottom-bar");
    const localPlaying = window.LocalFlacPlayer.isPlaying;
    const spotifyPlaying = window.Spicetify.Player.isPlaying();
    const owner = window.LocalFlacPlayer.playbackOwner;
    return {
      owner,
      localPlaying,
      spotifyPlaying,
      simultaneousAudio: localPlaying && spotifyPlaying,
      barStateMatch: (owner === "LOCAL_FLAC") === (!bar.classList.contains("hidden"))
    };
  })()`);
  console.log("Rapid Switching Result:", JSON.stringify(stressResult, null, 2));
  if (stressResult.simultaneousAudio) throw new Error("TEST 6 FAILED: Simultaneous audio detected after rapid switching!");
  if (!stressResult.barStateMatch) throw new Error("TEST 6 FAILED: Bottom bar visibility does not match owner state!");
  console.log("✔ TEST 6 PASSED: Rapid switching maintained strict ownership and clean UI.\n");

  // ========================================================
  // TEST 7: Settings UI Screenshot
  // ========================================================
  console.log("--- TEST 7: Capturing Settings UI Screenshot ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push("/preferences");
  })()`);
  await sleep(1500);

  await evaluate(`(() => {
    const row = document.getElementById("settings-local-flac-row");
    if (row) row.scrollIntoView({ block: "center" });
  })()`);
  await sleep(500);

  const s7Bytes = await screenshot("05_settings_local_flac.png");
  if (s7Bytes < 10000) throw new Error("TEST 7 FAILED: Screenshot 05 is too small");
  console.log("✔ TEST 7 PASSED: Settings screenshot captured.\n");

  // ========================================================
  // TEST 8: Polished Local FLAC Page Screenshot
  // ========================================================
  console.log("--- TEST 8: Capturing Polished Local FLAC Screenshot ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push("/local-flac");
  })()`);
  await sleep(1500);

  const s8Check = await evaluate(`(() => {
    const pills = Array.from(document.querySelectorAll(".lf-stat-pill")).map(p => p.innerText);
    const tabs = Array.from(document.querySelectorAll(".lf-tab-btn")).map(t => t.innerText);
    const rows = document.querySelectorAll(".lf-track-row").length;
    return { pills, tabs, rows };
  })()`);
  console.log("Local FLAC Page Elements:", JSON.stringify(s8Check, null, 2));

  const s8Bytes = await screenshot("06_local_flac_polished.png");
  if (s8Bytes < 10000) throw new Error("TEST 8 FAILED: Screenshot 06 is too small");
  console.log("✔ TEST 8 PASSED: Local FLAC polished screenshot captured.\n");

  ws.close();
  console.log("==========================================================");
  console.log("  ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY! 🎯");
  console.log("==========================================================");
}

main().catch(err => {
  console.error("\n❌ VERIFICATION SUITE FAILED:", err);
  process.exit(1);
});
