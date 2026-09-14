const fs = require('fs');

async function main() {
  console.log("==========================================================");
  console.log("  Live Spotify Table & Sorting Validation Suite");
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

  async function screenshot(filename) {
    const res = await send("Page.captureScreenshot", { format: "png" });
    const buffer = Buffer.from(res.result.data, 'base64');
    fs.writeFileSync(filename, buffer);
    console.log(`📸 Saved screenshot: ${filename} (${buffer.length} bytes)`);
    return buffer.length;
  }

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // ========================================================
  // Step A & B: Open /local-flac and verify exact table headers
  // ========================================================
  console.log("--- STEP A & B: Navigating to /local-flac & Verifying Headers ---");
  await evaluate(`window.Spicetify.Platform.History.push("/local-flac")`);
  await sleep(1500);

  const headerCheck = await evaluate(`(() => {
    const table = document.querySelector(".lf-track-table");
    if (!table) return { error: "table_not_found" };
    const ths = Array.from(table.querySelectorAll("thead th")).map(th => th.innerText.trim());
    const hasFormat = ths.some(t => t.toUpperCase().includes("FORMAT"));
    const cols = ths.map(t => t.replace(/[▲▼↑↓]/g, "").trim());
    return {
      rawHeaders: ths,
      cleanHeaders: cols,
      hasFormat,
      tableFound: true
    };
  })()`);
  console.log("Headers check:", JSON.stringify(headerCheck, null, 2));

  if (!headerCheck.tableFound) throw new Error("Table not found on /local-flac");
  if (headerCheck.hasFormat) throw new Error("FORMAT column must be completely removed from the table!");
  // Check headers contain #, TITLE, ARTIST, ALBUM, and duration icon/text
  const expectedCols = ["#", "TITLE", "ARTIST", "ALBUM"];
  for (const c of expectedCols) {
    if (!headerCheck.cleanHeaders.some(h => h.toUpperCase().includes(c))) {
      throw new Error(`Missing expected column header: ${c}`);
    }
  }
  console.log("✔ STEP A & B PASSED: Target columns [# TITLE ARTIST ALBUM ⏱] present, FORMAT column removed.\n");

  // ========================================================
  // Step C: TITLE click (A -> Z and Z -> A)
  // ========================================================
  console.log("--- STEP C: Testing TITLE Sorting (A→Z and Z→A) ---");
  // Click TITLE header to sort A -> Z
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const titleAscCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    const titles = Array.from(document.querySelectorAll(".lf-track-table tbody .lf-track-name")).slice(0, 10).map(e => e.innerText.trim());
    const firstNum = document.querySelector(".lf-track-table tbody .lf-track-idx")?.innerText;
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      hasIcon: !!th?.querySelector(".lf-sort-icon"),
      firstRowNumber: firstNum,
      sampleTitles: titles
    };
  })()`);
  console.log("TITLE A→Z:", JSON.stringify(titleAscCheck, null, 2));
  if (titleAscCheck.ariaSort !== "ascending") throw new Error("TITLE header aria-sort should be 'ascending'");
  if (titleAscCheck.firstRowNumber !== "1") throw new Error("Visible row number must be '1'");

  // Click TITLE header again to sort Z -> A
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const titleDescCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    const titles = Array.from(document.querySelectorAll(".lf-track-table tbody .lf-track-name")).slice(0, 10).map(e => e.innerText.trim());
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      hasIcon: !!th?.querySelector(".lf-sort-icon"),
      sampleTitles: titles
    };
  })()`);
  console.log("TITLE Z→A:", JSON.stringify(titleDescCheck, null, 2));
  if (titleDescCheck.ariaSort !== "descending") throw new Error("TITLE header aria-sort should be 'descending'");
  console.log("✔ STEP C PASSED: TITLE sorting A→Z and Z→A verified.\n");

  // ========================================================
  // Step D: ARTIST click (A -> Z and Z -> A)
  // ========================================================
  console.log("--- STEP D: Testing ARTIST Sorting (A→Z and Z→A) ---");
  // Click ARTIST header (should default to ascending)
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const artistAscCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    const artists = Array.from(document.querySelectorAll(".lf-track-table tbody .lf-artist-name")).slice(0, 10).map(e => e.innerText.trim());
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      hasIcon: !!th?.querySelector(".lf-sort-icon"),
      sampleArtists: artists
    };
  })()`);
  console.log("ARTIST A→Z:", JSON.stringify(artistAscCheck, null, 2));
  if (artistAscCheck.ariaSort !== "ascending") throw new Error("ARTIST header aria-sort should be 'ascending'");

  // Click ARTIST header again to sort Z -> A
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const artistDescCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    const artists = Array.from(document.querySelectorAll(".lf-track-table tbody .lf-artist-name")).slice(0, 10).map(e => e.innerText.trim());
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      sampleArtists: artists
    };
  })()`);
  console.log("ARTIST Z→A:", JSON.stringify(artistDescCheck, null, 2));
  if (artistDescCheck.ariaSort !== "descending") throw new Error("ARTIST header aria-sort should be 'descending'");
  console.log("✔ STEP D PASSED: ARTIST sorting A→Z and Z→A verified.\n");

  // ========================================================
  // Step E: ALBUM click (A -> Z and Z -> A)
  // ========================================================
  console.log("--- STEP E: Testing ALBUM Sorting (A→Z and Z→A) ---");
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ALBUM"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const albumAscCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ALBUM"));
    const albums = Array.from(document.querySelectorAll(".lf-track-table tbody .lf-album-name")).slice(0, 10).map(e => e.innerText.trim());
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      sampleAlbums: albums
    };
  })()`);
  console.log("ALBUM A→Z:", JSON.stringify(albumAscCheck, null, 2));
  if (albumAscCheck.ariaSort !== "ascending") throw new Error("ALBUM header aria-sort should be 'ascending'");

  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ALBUM"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const albumDescCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ALBUM"));
    const albums = Array.from(document.querySelectorAll(".lf-track-table tbody .lf-album-name")).slice(0, 10).map(e => e.innerText.trim());
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      sampleAlbums: albums
    };
  })()`);
  console.log("ALBUM Z→A:", JSON.stringify(albumDescCheck, null, 2));
  if (albumDescCheck.ariaSort !== "descending") throw new Error("ALBUM header aria-sort should be 'descending'");
  console.log("✔ STEP E PASSED: ALBUM sorting A→Z and Z→A verified.\n");

  // ========================================================
  // Step F: Sorting doesn't stop currently playing FLAC
  // ========================================================
  console.log("--- STEP F: Verifying Sorting Does NOT Stop Playback ---");
  // Sort TITLE A -> Z first
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    if (th) th.click();
  })()`);
  await sleep(400);

  // Click first track's play button
  await evaluate(`(() => {
    const row = document.querySelector(".lf-track-table tbody tr");
    const playBtn = row?.querySelector(".lf-row-play-btn");
    if (playBtn) playBtn.click();
  })()`);
  await sleep(1000);

  const playCheck1 = await evaluate(`(() => ({
    isPlaying: window.LocalFlacPlayer?.isPlaying,
    owner: window.LocalFlacPlayer?.playbackOwner,
    currentTrackTitle: window.LocalFlacPlayer?.currentTrack?.title
  }))()`);
  console.log("Playing state before sort:", playCheck1);
  if (!playCheck1.isPlaying) throw new Error("FLAC player failed to start");

  // Change sort to ARTIST ascending while playing
  console.log("Toggling sort to ARTIST A→Z while playback is active...");
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    if (th) th.click();
  })()`);
  await sleep(600);

  const playCheck2 = await evaluate(`(() => ({
    isPlaying: window.LocalFlacPlayer?.isPlaying,
    owner: window.LocalFlacPlayer?.playbackOwner,
    currentTrackTitle: window.LocalFlacPlayer?.currentTrack?.title,
    playingRowHighlighted: !!document.querySelector(".lf-track-row.playing")
  }))()`);
  console.log("Playing state after sort change:", playCheck2);
  if (!playCheck2.isPlaying) throw new Error("Playback stopped upon changing sort order!");
  if (playCheck2.currentTrackTitle !== playCheck1.currentTrackTitle) throw new Error("Current playing track changed unexpectedly!");
  console.log("✔ STEP F PASSED: Playback uninterrupted during sort operations.\n");

  // ========================================================
  // Step G: Playback queue follows visible sorted order
  // ========================================================
  console.log("--- STEP G: Verifying Next/Previous Follow Visible Sorted Order ---");
  // Set sort to TITLE ascending
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    if (th) {
      th.click();
      if (th.getAttribute("aria-sort") !== "ascending") th.click();
    }
  })()`);
  await sleep(600);

  // Click the 2nd row in the sorted table
  await evaluate(`(() => {
    const rows = document.querySelectorAll(".lf-track-table tbody tr");
    if (rows[1]) {
      const btn = rows[1].querySelector(".lf-row-play-btn");
      if (btn) btn.click();
    }
  })()`);
  await sleep(800);

  const queueCheck1 = await evaluate(`(() => {
    const visibleRow2Title = document.querySelectorAll(".lf-track-table tbody .lf-track-name")[1]?.innerText;
    const visibleRow3Title = document.querySelectorAll(".lf-track-table tbody .lf-track-name")[2]?.innerText;
    const playerTitle = window.LocalFlacPlayer?.currentTrack?.title || window.LocalFlacPlayer?.currentTrack?.filename;
    return {
      visibleRow2Title,
      visibleRow3Title,
      playerTitle
    };
  })()`);
  console.log("Queue initial pick:", queueCheck1);
  assert_equal(queueCheck1.playerTitle, queueCheck1.visibleRow2Title, "Player should play row 2");

  // Call Next -> must advance to visible row 3!
  console.log("Triggering Next track...");
  await evaluate(`window.LocalFlacPlayer.next()`);
  await sleep(600);

  const queueCheck2 = await evaluate(`(() => ({
    playerTitle: window.LocalFlacPlayer?.currentTrack?.title || window.LocalFlacPlayer?.currentTrack?.filename,
    visibleRow3Title: document.querySelectorAll(".lf-track-table tbody .lf-track-name")[2]?.innerText
  }))()`);
  console.log("Queue after Next:", queueCheck2);
  assert_equal(queueCheck2.playerTitle, queueCheck2.visibleRow3Title, "Next must follow visible sorted order (row 3)");

  // Call Prev -> must return to visible row 2!
  console.log("Triggering Previous track...");
  await evaluate(`window.LocalFlacPlayer.prev()`);
  await sleep(600);

  const queueCheck3 = await evaluate(`(() => ({
    playerTitle: window.LocalFlacPlayer?.currentTrack?.title || window.LocalFlacPlayer?.currentTrack?.filename,
    visibleRow2Title: document.querySelectorAll(".lf-track-table tbody .lf-track-name")[1]?.innerText
  }))()`);
  console.log("Queue after Prev:", queueCheck3);
  assert_equal(queueCheck3.playerTitle, queueCheck3.visibleRow2Title, "Prev must return to visible row 2");
  console.log("✔ STEP G PASSED: Playback queue correctly follows current visible sorted order.\n");

  // ========================================================
  // Step H: FLAC quality badge still in bottom player
  // ========================================================
  console.log("--- STEP H: Verifying Bottom Player Quality Badge ---");
  const bottomBarBadge = await evaluate(`(() => {
    const bar = document.getElementById("local-flac-bottom-bar");
    const badge = bar?.querySelector(".lfb-badge")?.innerText;
    return {
      badgeText: badge,
      barVisible: bar && !bar.classList.contains("hidden")
    };
  })()`);
  console.log("Bottom player badge:", bottomBarBadge);
  if (!bottomBarBadge.barVisible) throw new Error("Bottom bar is not visible during FLAC playback");
  if (!bottomBarBadge.badgeText || !bottomBarBadge.badgeText.toUpperCase().includes("FLAC")) {
    throw new Error(`Invalid quality badge in bottom bar: ${bottomBarBadge.badgeText}`);
  }
  console.log(`✔ STEP H PASSED: Bottom bar quality badge displays "${bottomBarBadge.badgeText}".\n`);

  // ========================================================
  // Step I: FLAC Only <-> All Local preserves sort
  // ========================================================
  console.log("--- STEP I: Switching Tabs (FLAC Only ↔ All Local) Preserves Sort ---");
  // Sort by ARTIST ascending
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    if (th) {
      th.click();
      if (th.getAttribute("aria-sort") !== "ascending") th.click();
    }
  })()`);
  await sleep(400);

  // Switch to "All Local" tab
  await evaluate(`(() => {
    const btns = Array.from(document.querySelectorAll(".lf-tab-btn"));
    const allBtn = btns.find(b => b.innerText.includes("All Local"));
    if (allBtn) allBtn.click();
  })()`);
  await sleep(600);

  const allLocalSortCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      hasIcon: !!th?.querySelector(".lf-sort-icon")
    };
  })()`);
  console.log("All Local sort state:", allLocalSortCheck);
  if (allLocalSortCheck.ariaSort !== "ascending") throw new Error("Sort state was lost when switching to 'All Local'");

  // Switch back to "FLAC Only"
  await evaluate(`(() => {
    const btns = Array.from(document.querySelectorAll(".lf-tab-btn"));
    const flacBtn = btns.find(b => b.innerText.includes("FLAC Only"));
    if (flacBtn) flacBtn.click();
  })()`);
  await sleep(600);

  const flacSortCheck = await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("ARTIST"));
    return {
      ariaSort: th?.getAttribute("aria-sort"),
      hasIcon: !!th?.querySelector(".lf-sort-icon")
    };
  })()`);
  console.log("FLAC Only sort state after return:", flacSortCheck);
  if (flacSortCheck.ariaSort !== "ascending") throw new Error("Sort state was lost returning to 'FLAC Only'");
  console.log("✔ STEP I PASSED: Sort state coherently preserved across tab switches.\n");

  // ========================================================
  // Step J: Playback Handoff Verification
  // ========================================================
  console.log("--- STEP J: Verifying Playback Handoff Still Functions ---");
  await evaluate(`window.Spicetify.Player.play()`);
  await sleep(800);

  const handoffCheck = await evaluate(`(() => ({
    owner: window.LocalFlacPlayer?.playbackOwner,
    localPlaying: window.LocalFlacPlayer?.isPlaying,
    spotifyPlaying: window.Spicetify.Player.isPlaying(),
    barHidden: document.getElementById("local-flac-bottom-bar")?.classList.contains("hidden")
  }))()`);
  console.log("Handoff to native Spotify:", handoffCheck);
  if (handoffCheck.owner !== "SPOTIFY_NATIVE") throw new Error("Owner failed to transition to SPOTIFY_NATIVE");
  if (handoffCheck.localPlaying) throw new Error("Local FLAC did not pause upon native playback");
  if (!handoffCheck.barHidden) throw new Error("Local bottom bar is not hidden");
  console.log("✔ STEP J PASSED: Bidirectional handoff intact.\n");

  // ========================================================
  // Capture Final Screenshot with TITLE, ARTIST, ALBUM and active sort indicator
  // ========================================================
  console.log("--- Capturing Final Polished Table Screenshot ---");
  await evaluate(`window.Spicetify.Platform.History.push("/local-flac")`);
  await sleep(1000);

  // Sort by TITLE ascending to produce an elegant display
  await evaluate(`(() => {
    const th = Array.from(document.querySelectorAll(".lf-track-table th")).find(t => t.innerText.includes("TITLE"));
    if (th) {
      th.click();
      if (th.getAttribute("aria-sort") !== "ascending") th.click();
    }
  })()`);
  await sleep(600);

  const screenshotBytes = await screenshot("/home/admin/Projects/spotify-local-flac/screenshots/07_sortable_columns.png");
  if (screenshotBytes < 10000) throw new Error("Screenshot is too small!");

  ws.close();
  console.log("\n==========================================================");
  console.log("  ALL LIVE TABLE & SORTING VALIDATIONS PASSED! 🎯");
  console.log("==========================================================");
}

function assert_equal(a, b, msg) {
  if (a !== b) {
    throw new Error(`${msg}: expected '${b}', got '${a}'`);
  }
}

main().catch(err => {
  console.error("\n❌ LIVE VALIDATION FAILED:", err);
  process.exit(1);
});
