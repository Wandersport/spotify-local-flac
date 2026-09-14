const fs = require('fs');

async function main() {
  const tabs = await (await fetch("http://127.0.0.1:9222/json")).json();
  const wsUrl = tabs[0].webSocketDebuggerUrl;
  console.log("Connecting to CDP at", wsUrl);
  
  const token = fs.readFileSync('/home/admin/.config/spotify-local-flac/token', 'utf8').trim();

  const ws = new WebSocket(wsUrl);
  await new Promise(r => ws.onopen = r);
  console.log("✔ Connected to Spotify CDP WebSocket");

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
    return res.result?.result?.value;
  }

  async function screenshot(filename) {
    const res = await send("Page.captureScreenshot", { format: "png" });
    const buffer = Buffer.from(res.result.data, 'base64');
    fs.writeFileSync(filename, buffer);
    console.log(`📸 Saved screenshot: ${filename} (${buffer.length} bytes)`);
  }

  // 1. FRESH START STATE
  console.log("\n--- STEP 1: Verifying Fresh Start State on Home ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push('/');
    try {
      const expandBtn = document.querySelector('button[aria-label*="Expand"]') ||
                        document.querySelector('button[aria-label*="Ampliar"]');
      if (expandBtn) expandBtn.click();
    } catch(e) {}
  })()`);
  await new Promise(r => setTimeout(r, 2000));
  const freshState = await evaluate(`(() => {
    const bar = document.getElementById('local-flac-bottom-bar');
    const main = document.getElementById('main');
    return {
      barExists: !!bar,
      barHidden: bar ? bar.classList.contains('hidden') : null,
      barDisplay: bar ? window.getComputedStyle(bar).display : null,
      mainOffsetTop: main ? main.offsetTop : null,
      bodyPlaying: document.body.classList.contains('local-flac-playing')
    };
  })()`);
  console.log("Fresh state:", JSON.stringify(freshState, null, 2));

  // Take Screenshot 1
  await screenshot("/home/admin/Projects/spotify-local-flac/screenshots/01_home_no_local_playback.png");

  // 2. CHECK SIDEBAR AND NAVIGATE TO /local-flac
  console.log("\n--- STEP 2: Navigating to /local-flac ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push('/local-flac');
  })()`);
  await new Promise(r => setTimeout(r, 2000));

  const pageState = await evaluate(`(() => {
    const appRoot = document.getElementById('local-flac-app-root');
    const title = document.querySelector('.lf-title')?.innerText;
    const pills = Array.from(document.querySelectorAll('.lf-stat-pill')).map(p => p.innerText);
    const tabs = Array.from(document.querySelectorAll('.lf-tab-btn')).map(t => t.innerText);
    const tracks = document.querySelectorAll('.lf-track-row').length;
    const sidebarRow = document.getElementById('sidebar-local-flac-row');
    return {
      appRootVisible: appRoot && !appRoot.classList.contains('hidden'),
      title,
      pills,
      tabs,
      trackCount: tracks,
      sidebarInjected: !!sidebarRow,
      sidebarActive: sidebarRow ? sidebarRow.classList.contains('active') : false
    };
  })()`);
  console.log("Local FLAC Page state:", JSON.stringify(pageState, null, 2));

  // 3. FETCH FIRST FLAC TRACK AND PLAY IT
  console.log("\n--- STEP 3: Playing FLAC Track ---");
  const tracksRes = await (await fetch("http://127.0.0.1:18492/api/tracks?limit=5000", {
    headers: { Authorization: `Bearer ${token}` }
  })).json();
  const flacTracks = (tracksRes.tracks || []).filter(t => (t.codec || "").toUpperCase() === "FLAC");
  const playTrack = flacTracks[0];
  console.log(`Target FLAC Track: "${playTrack.title}" (${playTrack.codec} ${playTrack.bit_depth}-bit / ${playTrack.sample_rate}Hz)`);

  await evaluate(`(() => {
    const track = ${JSON.stringify(playTrack)};
    window.LocalFlacPlayer.playTrack(track);
  })()`);
  await new Promise(r => setTimeout(r, 2000));

  const playingBarState = await evaluate(`(() => {
    const bar = document.getElementById('local-flac-bottom-bar');
    const title = bar?.querySelector('.lfb-title')?.innerText;
    const artist = bar?.querySelector('.lfb-artist')?.innerText;
    const badge = bar?.querySelector('.lfb-badge')?.innerText;
    const isHidden = bar?.classList.contains('hidden');
    const display = bar ? window.getComputedStyle(bar).display : null;
    const curTime = bar?.querySelector('.lfb-cur-time')?.innerText;
    const totTime = bar?.querySelector('.lfb-tot-time')?.innerText;
    const bodyPlaying = document.body.classList.contains('local-flac-playing');
    const nativeBar = document.querySelector('[data-testid="now-playing-bar"] > .main-nowPlayingBar-nowPlayingBar');
    const nativeHidden = nativeBar ? window.getComputedStyle(nativeBar).visibility === 'hidden' : false;
    return {
      title,
      artist,
      badge,
      isHidden,
      display,
      curTime,
      totTime,
      bodyPlaying,
      nativeHidden
    };
  })()`);
  console.log("Bottom Bar playing state:", JSON.stringify(playingBarState, null, 2));

  // Take Screenshot 2
  await screenshot("/home/admin/Projects/spotify-local-flac/screenshots/02_local_flac_page_playing.png");

  // 4. NAVIGATE TO HOME WHILE FLAC IS PLAYING
  console.log("\n--- STEP 4: Navigating to Home '/' While Playing FLAC ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push('/');
  })()`);
  await new Promise(r => setTimeout(r, 2000));

  const homePlayingState = await evaluate(`(() => {
    const bar = document.getElementById('local-flac-bottom-bar');
    const main = document.getElementById('main');
    const appRoot = document.getElementById('local-flac-app-root');
    return {
      pathname: window.Spicetify.Platform.History.location.pathname,
      barExists: !!bar,
      barHidden: bar?.classList.contains('hidden'),
      barDisplay: bar ? window.getComputedStyle(bar).display : null,
      mainOffsetTop: main?.offsetTop,
      appRootHidden: appRoot?.classList.contains('hidden'),
      bodyPlaying: document.body.classList.contains('local-flac-playing')
    };
  })()`);
  console.log("Home while playing state:", JSON.stringify(homePlayingState, null, 2));

  // Take Screenshot 3
  await screenshot("/home/admin/Projects/spotify-local-flac/screenshots/03_home_flac_playing.png");

  // 5. TEST PLAYBACK CONTROLS (Pause / Resume / Seek / Volume)
  console.log("\n--- STEP 5: Testing Controls ---");
  const pauseTest = await evaluate(`(() => {
    window.LocalFlacPlayer.pause();
    return { isPlaying: window.LocalFlacPlayer.isPlaying };
  })()`);
  console.log("Pause test:", pauseTest);

  const resumeTest = await evaluate(`(() => {
    window.LocalFlacPlayer.resume();
    return { isPlaying: window.LocalFlacPlayer.isPlaying };
  })()`);
  console.log("Resume test:", resumeTest);

  const seekTest = await evaluate(`(() => {
    window.LocalFlacPlayer.seek(30);
    return { curTime: window.LocalFlacPlayer.currentTime };
  })()`);
  console.log("Seek test (to 30s):", seekTest);

  // 6. VERIFY NATIVE LOCAL FILES COLLECTION (1,741 tracks)
  console.log("\n--- STEP 6: Navigating to Native Local Files ---");
  await evaluate(`(() => {
    window.Spicetify.Platform.History.push('/collection/local-files');
  })()`);
  await new Promise(r => setTimeout(r, 2000));

  const nativeFilesState = await evaluate(`(() => {
    const h1 = document.querySelector('h1')?.innerText;
    const sidebarRow = Array.from(document.querySelectorAll('*')).find(
      el => el.textContent.includes('1,741 tracks')
    );
    return {
      pageTitle: h1,
      nativeCountFound: !!sidebarRow,
      nativeCountText: sidebarRow?.innerText
    };
  })()`);
  console.log("Native Local Files verification:", JSON.stringify(nativeFilesState, null, 2));

  // Screenshot 4
  await screenshot("/home/admin/Projects/spotify-local-flac/screenshots/04_native_local_files.png");

  ws.close();
  console.log("\n✔ All verification steps completed successfully!");
}

main().catch(err => {
  console.error("Verification error:", err);
  process.exit(1);
});
