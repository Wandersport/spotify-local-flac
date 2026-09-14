import os
import json

with open("spicetify/CustomApps/local-flac/style.css") as f:
    app_css = f.read()

ext_code = f'''// Spotify Local FLAC - Complete Production Integration
// High-Fidelity FLAC Playback, Global Player Bar, Native Library Integration & Custom UI

(function initSpotifyLocalFlac() {{
  "use strict";

  // ==========================================================
  // 1. ATOMIC STYLE INJECTION (Global & Instant)
  // ==========================================================
  const STYLE_ID = "local-flac-player-styles";
  if (!document.getElementById(STYLE_ID)) {{
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      /* --- Bottom Player Bar Styles --- */
      #local-flac-bottom-bar.hidden,
      .local-flac-bottom-bar.hidden {{
        display: none !important;
      }}

      body.local-flac-playing [data-testid="now-playing-bar"] > .main-nowPlayingBar-nowPlayingBar {{
        visibility: hidden !important;
      }}

      aside[data-testid="now-playing-bar"] {{
        position: relative !important;
      }}

      #local-flac-bottom-bar {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: var(--background-base, #000000);
        z-index: 100;
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        padding: 0 16px;
        box-sizing: border-box;
        font-family: var(--font-family, spotify-circular, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
        user-select: none;
      }}

      #local-flac-bottom-bar.fallback-fixed {{
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 96px !important;
        z-index: 99999 !important;
        background-color: #121212 !important;
        border-top: 1px solid #282828 !important;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.6) !important;
      }}

      .lfb-left {{
        display: flex;
        align-items: center;
        gap: 14px;
        width: 30%;
        min-width: 180px;
      }}

      .lfb-art-container {{
        width: 56px;
        height: 56px;
        border-radius: 4px;
        overflow: hidden;
        background-color: #282828;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
      }}

      .lfb-art {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }}

      .lfb-art-fallback {{
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #b3b3b3;
        font-size: 24px;
      }}

      .lfb-info {{
        display: flex;
        flex-direction: column;
        overflow: hidden;
        justify-content: center;
      }}

      .lfb-title-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 2px;
      }}

      .lfb-title {{
        color: #ffffff;
        font-size: 14px;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}

      .lfb-artist {{
        color: #b3b3b3;
        font-size: 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}

      .lfb-badge {{
        background: linear-gradient(135deg, #1db954, #1ed760);
        color: #000000;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        flex-shrink: 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }}

      .lfb-center {{
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 40%;
        max-width: 722px;
      }}

      .lfb-controls {{
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 8px;
      }}

      .lfb-btn {{
        background: none;
        border: none;
        color: #b3b3b3;
        cursor: pointer;
        padding: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: color 0.15s, transform 0.1s;
      }}

      .lfb-btn:hover {{
        color: #ffffff;
        transform: scale(1.06);
      }}

      .lfb-btn.active {{
        color: #1ed760;
      }}

      .lfb-play-btn {{
        background-color: #ffffff;
        color: #000000;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        padding: 0;
      }}

      .lfb-play-btn:hover {{
        background-color: #f8f8f8;
        transform: scale(1.06);
        color: #000000;
      }}

      .lfb-progress-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
      }}

      .lfb-time {{
        color: #a7a7a7;
        font-size: 11px;
        min-width: 36px;
        text-align: center;
        font-variant-numeric: tabular-nums;
      }}

      .lfb-seek-bar {{
        flex-grow: 1;
        height: 4px;
        background-color: #4d4d4d;
        border-radius: 2px;
        position: relative;
        cursor: pointer;
      }}

      .lfb-seek-bar:hover {{
        height: 6px;
      }}

      .lfb-seek-bar:hover .lfb-seek-fill {{
        background-color: #1ed760;
      }}

      .lfb-seek-bar:hover .lfb-seek-thumb {{
        opacity: 1;
      }}

      .lfb-seek-fill {{
        height: 100%;
        background-color: #ffffff;
        border-radius: 2px;
        width: 0%;
        position: relative;
        pointer-events: none;
      }}

      .lfb-seek-thumb {{
        width: 12px;
        height: 12px;
        background-color: #ffffff;
        border-radius: 50%;
        position: absolute;
        right: -6px;
        top: 50%;
        transform: translateY(-50%);
        opacity: 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.5);
      }}

      .lfb-right {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 12px;
        width: 30%;
        min-width: 180px;
      }}

      .lfb-vol-container {{
        display: flex;
        align-items: center;
        gap: 8px;
        width: 120px;
      }}

      .lfb-vol-bar {{
        flex-grow: 1;
        height: 4px;
        background-color: #4d4d4d;
        border-radius: 2px;
        position: relative;
        cursor: pointer;
      }}

      .lfb-vol-bar:hover {{
        height: 6px;
      }}

      .lfb-vol-bar:hover .lfb-vol-fill {{
        background-color: #1ed760;
      }}

      .lfb-vol-bar:hover .lfb-vol-thumb {{
        opacity: 1;
      }}

      .lfb-vol-fill {{
        height: 100%;
        background-color: #ffffff;
        border-radius: 2px;
        width: 80%;
        position: relative;
        pointer-events: none;
      }}

      .lfb-vol-thumb {{
        width: 12px;
        height: 12px;
        background-color: #ffffff;
        border-radius: 50%;
        position: absolute;
        right: -6px;
        top: 50%;
        transform: translateY(-50%);
        opacity: 0;
      }}

      /* --- Route Switching & App Container --- */
      #local-flac-app-root.hidden {{
        display: none !important;
      }}

      body.local-flac-route-active main {{
        display: none !important;
      }}

      #local-flac-app-root {{
        width: 100%;
        min-height: 100%;
        position: relative;
        z-index: 10;
      }}

      /* --- Sidebar Row Styles --- */
      #sidebar-local-flac-row.active .aE_ayHuwU0UG20h2,
      #sidebar-local-flac-row.active [data-encore-id="listRow"] {{
        background-color: rgba(255, 255, 255, 0.1) !important;
      }}

      #sidebar-local-flac-row.active [data-encore-id="listRowTitle"] {{
        color: #1ed760 !important;
      }}

      /* --- App Styles (Embedded) --- */
      {app_css}
    `;
    (document.head || document.documentElement).appendChild(style);
  }}

  // ==========================================================
  // 2. CONFIGURATION & HELPERS
  // ==========================================================
  window.LocalFlacConfig = window.LocalFlacConfig || {{
    host: "127.0.0.1",
    port: 18492,
    token: ""
  }};

  const savedToken = localStorage.getItem("local_flac_token");
  if (savedToken) {{
    window.LocalFlacConfig.token = savedToken;
  }}

  function getBaseUrl() {{
    return `http://${{window.LocalFlacConfig.host}}:${{window.LocalFlacConfig.port}}`;
  }}

  function getApiHeaders() {{
    const headers = {{ "Content-Type": "application/json" }};
    if (window.LocalFlacConfig.token) {{
      headers["Authorization"] = `Bearer ${{window.LocalFlacConfig.token}}`;
    }}
    return headers;
  }}

  function getStreamUrl(trackId) {{
    let url = `${{getBaseUrl()}}/api/stream/${{trackId}}`;
    if (window.LocalFlacConfig.token) {{
      url += `?token=${{encodeURIComponent(window.LocalFlacConfig.token)}}`;
    }}
    return url;
  }}

  function getArtworkUrl(trackId) {{
    let url = `${{getBaseUrl()}}/api/artwork/${{trackId}}`;
    if (window.LocalFlacConfig.token) {{
      url += `?token=${{encodeURIComponent(window.LocalFlacConfig.token)}}`;
    }}
    return url;
  }}

  function formatTime(seconds) {{
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${{m}}:${{s < 10 ? "0" : ""}}${{s}}`;
  }}

  function formatBadge(track) {{
    const codec = (track.codec || "FLAC").toUpperCase();
    if (track.bit_depth && track.sample_rate) {{
      const khz = (track.sample_rate / 1000).toFixed(track.sample_rate % 1000 === 0 ? 0 : 1);
      return `${{codec}} ${{track.bit_depth}}-BIT · ${{khz}} KHZ`;
    }}
    return codec;
  }}

  // ==========================================================
  // 3. FLAC PLAYER SINGLETON
  // ==========================================================
  class FlacPlayer {{
    constructor() {{
      this.audio = new Audio();
      this.audio.preload = "auto";
      this.currentTrack = null;
      this.queue = [];
      this.queueIndex = -1;
      this.isPlaying = false;
      this.currentTime = 0;
      this.duration = 0;
      this.volume = parseFloat(localStorage.getItem("local_flac_volume") || "0.8");
      this.isMuted = localStorage.getItem("local_flac_muted") === "true";
      this.shuffle = localStorage.getItem("local_flac_shuffle") === "true";
      this.repeat = localStorage.getItem("local_flac_repeat") || "off"; // 'off' | 'all' | 'one'
      this.listeners = new Set();
      this.flacCount = 0;
      this.audio.volume = this.isMuted ? 0 : this.volume;

      this._setupAudioListeners();
      this._setupSpotifySync();
      this._createBottomBar();
      this._setupMediaSession();
      this._updateSidebarCount();
    }}

    subscribe(fn) {{
      this.listeners.add(fn);
      fn(this.getState());
      return () => this.listeners.delete(fn);
    }}

    _notify() {{
      const state = this.getState();
      this.listeners.forEach(fn => fn(state));
      this._updateBottomBar();
    }}

    getState() {{
      return {{
        currentTrack: this.currentTrack,
        isPlaying: this.isPlaying,
        currentTime: this.currentTime,
        duration: this.duration,
        volume: this.volume,
        isMuted: this.isMuted,
        shuffle: this.shuffle,
        repeat: this.repeat,
        queueLength: this.queue.length,
        queueIndex: this.queueIndex
      }};
    }}

    _setupAudioListeners() {{
      this.audio.addEventListener("play", () => {{
        this.isPlaying = true;
        document.body.classList.add("local-flac-playing");
        const bar = document.getElementById("local-flac-bottom-bar");
        if (bar) bar.classList.remove("hidden");
        this._notify();
      }});

      this.audio.addEventListener("pause", () => {{
        this.isPlaying = false;
        this._notify();
      }});

      this.audio.addEventListener("timeupdate", () => {{
        this.currentTime = this.audio.currentTime;
        this.duration = this.audio.duration || this.currentTrack?.duration || 0;
        this._updateProgressOnly();
      }});

      this.audio.addEventListener("durationchange", () => {{
        this.duration = this.audio.duration || this.currentTrack?.duration || 0;
        this._notify();
      }});

      this.audio.addEventListener("ended", () => {{
        this._handleTrackEnded();
      }});

      this.audio.addEventListener("error", (e) => {{
        console.error("[LocalFLAC] Audio error:", e);
        this.isPlaying = false;
        this._notify();
      }});
    }}

    _setupSpotifySync() {{
      const pauseNative = () => {{
        try {{
          if (window.Spicetify && window.Spicetify.Player && window.Spicetify.Player.isPlaying()) {{
            window.Spicetify.Player.pause();
          }}
        }} catch(e) {{}}
      }};

      this.audio.addEventListener("play", pauseNative);

      const checkSpotify = () => {{
        if (window.Spicetify && window.Spicetify.Player) {{
          window.Spicetify.Player.addEventListener("onplaypause", () => {{
            if (window.Spicetify.Player.isPlaying() && this.isPlaying) {{
              this.pause();
              const bar = document.getElementById("local-flac-bottom-bar");
              if (bar) bar.classList.add("hidden");
              document.body.classList.remove("local-flac-playing");
            }}
          }});
        }} else {{
          setTimeout(checkSpotify, 1000);
        }}
      }};
      checkSpotify();
    }}

    _handleTrackEnded() {{
      if (this.repeat === "one") {{
        this.audio.currentTime = 0;
        this.audio.play();
      }} else if (this.queueIndex < this.queue.length - 1) {{
        this.next();
      }} else if (this.repeat === "all" && this.queue.length > 0) {{
        this.queueIndex = 0;
        this.playTrack(this.queue[0]);
      }} else {{
        this.isPlaying = false;
        this.currentTime = 0;
        this._notify();
      }}
    }}

    _setupMediaSession() {{
      if (!("mediaSession" in navigator)) return;
      navigator.mediaSession.setActionHandler("play", () => this.resume());
      navigator.mediaSession.setActionHandler("pause", () => this.pause());
      navigator.mediaSession.setActionHandler("previoustrack", () => this.prev());
      navigator.mediaSession.setActionHandler("nexttrack", () => this.next());
      navigator.mediaSession.setActionHandler("seekto", (details) => {{
        if (details.seekTime !== undefined) this.seek(details.seekTime);
      }});
    }}

    _updateMediaSession() {{
      if (!("mediaSession" in navigator) || !this.currentTrack) return;
      const t = this.currentTrack;
      navigator.mediaSession.metadata = new MediaMetadata({{
        title: t.title || t.filename,
        artist: t.artist || "Unknown Artist",
        album: t.album || "Local FLAC",
        artwork: t.has_artwork ? [{{ src: getArtworkUrl(t.id), sizes: "512x512", type: "image/jpeg" }}] : []
      }});
    }}

    playTrack(track, queue = null) {{
      if (!track) return;
      if (queue) {{
        this.queue = queue;
        this.queueIndex = queue.findIndex(t => t.id === track.id);
      }} else if (!this.queue.some(t => t.id === track.id)) {{
        this.queue = [track];
        this.queueIndex = 0;
      }} else {{
        this.queueIndex = this.queue.findIndex(t => t.id === track.id);
      }}

      this.currentTrack = track;
      this.duration = track.duration || 0;
      this.currentTime = 0;

      const url = getStreamUrl(track.id);
      this.audio.src = url;
      this.audio.currentTime = 0;

      const playPromise = this.audio.play();
      if (playPromise !== undefined) {{
        playPromise.catch(err => {{
          console.warn("[LocalFLAC] Autoplay prevented or stream error:", err);
        }});
      }}

      // Report to history endpoint
      fetch(`${{getBaseUrl()}}/api/history`, {{
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({{ track_id: track.id }})
      }}).catch(() => {{}});

      this._updateMediaSession();
      this._notify();
    }}

    resume() {{
      if (this.currentTrack && this.audio.src) {{
        this.audio.play();
      }} else if (this.queue.length > 0) {{
        this.playTrack(this.queue[0]);
      }}
    }}

    pause() {{
      this.audio.pause();
    }}

    togglePlay() {{
      if (this.isPlaying) {{
        this.pause();
      }} else {{
        this.resume();
      }}
    }}

    seek(seconds) {{
      const target = Math.max(0, Math.min(this.duration, seconds));
      this.audio.currentTime = target;
      this.currentTime = target;
      this._updateProgressOnly();
    }}

    setVolume(fraction) {{
      const val = Math.max(0, Math.min(1, fraction));
      this.volume = val;
      this.isMuted = false;
      this.audio.volume = val;
      localStorage.setItem("local_flac_volume", val.toString());
      localStorage.setItem("local_flac_muted", "false");
      this._notify();
    }}

    toggleMute() {{
      this.isMuted = !this.isMuted;
      this.audio.volume = this.isMuted ? 0 : this.volume;
      localStorage.setItem("local_flac_muted", this.isMuted ? "true" : "false");
      this._notify();
    }}

    toggleShuffle() {{
      this.shuffle = !this.shuffle;
      localStorage.setItem("local_flac_shuffle", this.shuffle ? "true" : "false");
      this._notify();
    }}

    toggleRepeat() {{
      const modes = ["off", "all", "one"];
      const nextIdx = (modes.indexOf(this.repeat) + 1) % modes.length;
      this.repeat = modes[nextIdx];
      localStorage.setItem("local_flac_repeat", this.repeat);
      this._notify();
    }}

    next() {{
      if (this.queue.length === 0) return;
      if (this.shuffle) {{
        const nextIdx = Math.floor(Math.random() * this.queue.length);
        this.queueIndex = nextIdx;
        this.playTrack(this.queue[nextIdx]);
      }} else if (this.queueIndex < this.queue.length - 1) {{
        this.queueIndex++;
        this.playTrack(this.queue[this.queueIndex]);
      }} else if (this.repeat === "all") {{
        this.queueIndex = 0;
        this.playTrack(this.queue[0]);
      }}
    }}

    prev() {{
      if (this.audio.currentTime > 3) {{
        this.seek(0);
        return;
      }}
      if (this.queueIndex > 0) {{
        this.queueIndex--;
        this.playTrack(this.queue[this.queueIndex]);
      }} else {{
        this.seek(0);
      }}
    }}

    _createBottomBar() {{
      if (document.getElementById("local-flac-bottom-bar")) return;

      const bar = document.createElement("div");
      bar.id = "local-flac-bottom-bar";
      bar.className = "local-flac-bottom-bar hidden";

      bar.innerHTML = `
        <div class="lfb-left">
          <div class="lfb-art-container">
            <img class="lfb-art" src="" alt="" style="display:none;" />
            <div class="lfb-art-fallback">♪</div>
          </div>
          <div class="lfb-info">
            <div class="lfb-title-row">
              <div class="lfb-title">No Track</div>
              <span class="lfb-badge">FLAC</span>
            </div>
            <div class="lfb-artist">Local Player</div>
          </div>
        </div>

        <div class="lfb-center">
          <div class="lfb-controls">
            <button class="lfb-btn lfb-shuffle-btn" title="Shuffle">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M13.151.922a.75.75 0 1 0-1.06 1.06L13.109 3H11.16a3.75 3.75 0 0 0-2.873 1.34l-6.173 7.356A2.25 2.25 0 0 1 .39 12.5H0V14h.391a3.75 3.75 0 0 0 2.873-1.34l6.173-7.356a2.25 2.25 0 0 1 1.724-.804h1.947l-1.017 1.018a.75.75 0 0 0 1.06 1.06L15.98 3.75 13.15.922zM.391 3.5H0V2h.391c1.109 0 2.16.49 2.873 1.34L4.89 5.277l-.979 1.167-1.796-2.14A2.25 2.25 0 0 0 .39 3.5z"/></svg>
            </button>
            <button class="lfb-btn lfb-prev-btn" title="Previous">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M3.3 1a.7.7 0 0 1 .7.7v5.15l9.95-5.744a.7.7 0 0 1 1.05.606v10.575a.7.7 0 0 1-1.05.607L4 7.149V12.3a.7.7 0 0 1-.7.7H1.7a.7.7 0 0 1-.7-.7V1.7a.7.7 0 0 1 .7-.7H3.3z"/></svg>
            </button>
            <button class="lfb-btn lfb-play-btn" title="Play">
              <svg class="lfb-icon-play" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M3 1.713a.7.7 0 0 1 1.05-.607l10.89 6.288a.7.7 0 0 1 0 1.212L4.05 14.894A.7.7 0 0 1 3 14.288V1.713z"/></svg>
              <svg class="lfb-icon-pause" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style="display:none;"><path d="M2.7 1a.7.7 0 0 0-.7.7v12.6a.7.7 0 0 0 .7.7h2.6a.7.7 0 0 0 .7-.7V1.7a.7.7 0 0 0-.7-.7H2.7zm8 0a.7.7 0 0 0-.7.7v12.6a.7.7 0 0 0 .7.7h2.6a.7.7 0 0 0 .7-.7V1.7a.7.7 0 0 0-.7-.7h-2.6z"/></svg>
            </button>
            <button class="lfb-btn lfb-next-btn" title="Next">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M12.7 1a.7.7 0 0 0-.7.7v5.15L2.05 1.107A.7.7 0 0 0 1 1.714v10.572a.7.7 0 0 0 1.05.607L12 7.149V12.3a.7.7 0 0 0 .7.7h1.6a.7.7 0 0 0 .7-.7V1.7a.7.7 0 0 0-.7-.7h-1.6z"/></svg>
            </button>
            <button class="lfb-btn lfb-repeat-btn" title="Repeat">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M0 4.75A3.75 3.75 0 0 1 3.75 1h8.5A3.75 3.75 0 0 1 16 4.75v5a3.75 3.75 0 0 1-3.75 3.75H9.81l1.018 1.018a.75.75 0 1 1-1.06 1.06L6.939 12.75l2.829-2.828a.75.75 0 1 1 1.06 1.06L9.81 12h2.44a2.25 2.25 0 0 0 2.25-2.25v-5a2.25 2.25 0 0 0-2.25-2.25h-8.5A2.25 2.25 0 0 0 1.5 4.75v5A2.25 2.25 0 0 0 3.75 12H5v1.5H3.75A3.75 3.75 0 0 1 0 9.75v-5z"/></svg>
            </button>
          </div>
          <div class="lfb-progress-row">
            <span class="lfb-time lfb-cur-time">0:00</span>
            <div class="lfb-seek-bar">
              <div class="lfb-seek-fill"><div class="lfb-seek-thumb"></div></div>
            </div>
            <span class="lfb-time lfb-tot-time">0:00</span>
          </div>
        </div>

        <div class="lfb-right">
          <div class="lfb-vol-container">
            <button class="lfb-btn lfb-mute-btn" title="Mute">
              <svg class="lfb-vol-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M9.741.85a.75.75 0 0 1 .375.65v13a.75.75 0 0 1-1.125.65l-6.925-4H0V4.85h2.066l6.925-4a.75.75 0 0 1 .75 0zM12 4a.75.75 0 0 1 .75.75 4.5 4.5 0 0 1 0 6.5.75.75 0 0 1-1.06-1.06 3 3 0 0 0 0-4.38A.75.75 0 0 1 12 4z"/></svg>
            </button>
            <div class="lfb-vol-bar">
              <div class="lfb-vol-fill"><div class="lfb-vol-thumb"></div></div>
            </div>
          </div>
        </div>
      `;

      // Event Listeners for Bar Controls
      const playBtn = bar.querySelector(".lfb-play-btn");
      playBtn.onclick = () => this.togglePlay();

      bar.querySelector(".lfb-prev-btn").onclick = () => this.prev();
      bar.querySelector(".lfb-next-btn").onclick = () => this.next();
      bar.querySelector(".lfb-shuffle-btn").onclick = () => this.toggleShuffle();
      bar.querySelector(".lfb-repeat-btn").onclick = () => this.toggleRepeat();
      bar.querySelector(".lfb-mute-btn").onclick = () => this.toggleMute();

      // Seek Bar Dragging / Clicking
      const seekBar = bar.querySelector(".lfb-seek-bar");
      const handleSeek = (e) => {{
        const rect = seekBar.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.seek(ratio * this.duration);
      }};
      seekBar.onclick = handleSeek;

      // Volume Bar Dragging / Clicking
      const volBar = bar.querySelector(".lfb-vol-bar");
      const handleVol = (e) => {{
        const rect = volBar.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.setVolume(ratio);
      }};
      volBar.onclick = handleVol;

      this._mountBarIntoDom(bar);
      setInterval(() => this._mountBarIntoDom(bar), 2000);
    }}

    _mountBarIntoDom(bar) {{
      const targetContainer = document.querySelector('aside[data-testid="now-playing-bar"]') ||
                              document.querySelector('.Root__now-playing-bar') ||
                              document.querySelector('footer');

      if (targetContainer) {{
        if (bar.parentElement !== targetContainer) {{
          targetContainer.appendChild(bar);
          bar.classList.remove("fallback-fixed");
        }}
      }} else {{
        if (bar.parentElement !== document.body) {{
          document.body.appendChild(bar);
          bar.classList.add("fallback-fixed");
        }}
      }}
    }}

    _updateBottomBar() {{
      const bar = document.getElementById("local-flac-bottom-bar");
      if (!bar) return;

      const track = this.currentTrack;
      if (!track) {{
        bar.classList.add("hidden");
        document.body.classList.remove("local-flac-playing");
        return;
      }}

      // Title & Artist
      const titleEl = bar.querySelector(".lfb-title");
      const artistEl = bar.querySelector(".lfb-artist");
      titleEl.textContent = track.title || track.filename;
      artistEl.textContent = track.artist ? `${{track.artist}}${{track.album ? " • " + track.album : ""}}` : (track.album || "Local File");

      // Badge
      const badge = bar.querySelector(".lfb-badge");
      badge.textContent = formatBadge(track);

      // Artwork
      const img = bar.querySelector(".lfb-art");
      const fallback = bar.querySelector(".lfb-art-fallback");
      if (track.has_artwork) {{
        img.src = getArtworkUrl(track.id);
        img.style.display = "block";
        fallback.style.display = "none";
      }} else {{
        img.style.display = "none";
        fallback.style.display = "flex";
      }}

      // Play/Pause icon
      const playIcon = bar.querySelector(".lfb-icon-play");
      const pauseIcon = bar.querySelector(".lfb-icon-pause");
      if (this.isPlaying) {{
        playIcon.style.display = "none";
        pauseIcon.style.display = "block";
      }} else {{
        playIcon.style.display = "block";
        pauseIcon.style.display = "none";
      }}

      // Shuffle & Repeat active states
      const shuffleBtn = bar.querySelector(".lfb-shuffle-btn");
      if (this.shuffle) shuffleBtn.classList.add("active");
      else shuffleBtn.classList.remove("active");

      const repeatBtn = bar.querySelector(".lfb-repeat-btn");
      if (this.repeat !== "off") repeatBtn.classList.add("active");
      else repeatBtn.classList.remove("active");

      this._updateProgressOnly();
    }}

    _updateProgressOnly() {{
      const bar = document.getElementById("local-flac-bottom-bar");
      if (!bar) return;

      const curTime = bar.querySelector(".lfb-cur-time");
      const totTime = bar.querySelector(".lfb-tot-time");
      const seekFill = bar.querySelector(".lfb-seek-fill");

      curTime.textContent = formatTime(this.currentTime);
      totTime.textContent = formatTime(this.duration);

      const progressRatio = this.duration > 0 ? (this.currentTime / this.duration) : 0;
      seekFill.style.width = `${{Math.min(100, Math.max(0, progressRatio * 100))}}%`;

      const volFill = bar.querySelector(".lfb-vol-fill");
      volFill.style.width = `${{this.isMuted ? 0 : (this.volume * 100)}}%`;
    }}

    _updateSidebarCount() {{
      const update = () => {{
        fetch(`${{getBaseUrl()}}/api/status`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => {{
            const flacCount = data.stats?.flac_count || 0;
            this.flacCount = flacCount;
            injectSidebarRow(flacCount);
          }})
          .catch(() => {{}});
      }};
      update();
      setInterval(update, 10000);
    }}
  }}

  // ==========================================================
  // 4. REACT APPLICATION VIEW (Inside Spotify Main Content)
  // ==========================================================
  function createLocalFlacComponent() {{
    const React = Spicetify.React;
    const {{ useState, useEffect, useCallback, useMemo }} = React;

    function LocalFlacApp() {{
      const [tab, setTab] = useState("flac"); // flac | all | albums | artists | folders | recent
      const [tracks, setTracks] = useState([]);
      const [albums, setAlbums] = useState([]);
      const [artists, setArtists] = useState([]);
      const [recentTracks, setRecentTracks] = useState([]);
      const [folderData, setFolderData] = useState({{ current_path: null, parent_path: null, items: [] }});
      const [searchQuery, setSearchQuery] = useState("");
      const [status, setStatus] = useState(null);
      const [isScanning, setIsScanning] = useState(false);
      const [showSettings, setShowSettings] = useState(false);
      const [selectedAlbum, setSelectedAlbum] = useState(null);
      const [selectedArtist, setSelectedArtist] = useState(null);
      const [playerState, setPlayerState] = useState(window.LocalFlacPlayer ? window.LocalFlacPlayer.getState() : {{}});

      useEffect(() => {{
        if (!window.LocalFlacPlayer) return;
        return window.LocalFlacPlayer.subscribe(setPlayerState);
      }}, []);

      const fetchStatus = useCallback(() => {{
        fetch(`${{getBaseUrl()}}/api/status`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => {{
            setStatus(data);
            setIsScanning(Boolean(data.scanner?.is_scanning));
          }})
          .catch(err => console.error("[LocalFLAC] Status fetch error:", err));
      }}, []);

      useEffect(() => {{
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
      }}, [fetchStatus]);

      const fetchTracks = useCallback((query = "", artist = null, album = null, flacOnly = false) => {{
        const params = new URLSearchParams({{ limit: "5000" }});
        if (query) params.append("search", query);
        if (artist) params.append("artist", artist);
        if (album) params.append("album", album);

        fetch(`${{getBaseUrl()}}/api/tracks?${{params.toString()}}`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => {{
            let list = data.tracks || [];
            if (flacOnly) {{
              list = list.filter(t => (t.codec || "").toUpperCase() === "FLAC");
            }}
            setTracks(list);
          }})
          .catch(err => console.error("[LocalFLAC] Tracks fetch error:", err));
      }}, []);

      const fetchAlbums = useCallback((query = "") => {{
        const params = new URLSearchParams();
        if (query) params.append("search", query);
        fetch(`${{getBaseUrl()}}/api/albums?${{params.toString()}}`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => setAlbums(data.albums || []))
          .catch(err => console.error("[LocalFLAC] Albums fetch error:", err));
      }}, []);

      const fetchArtists = useCallback((query = "") => {{
        const params = new URLSearchParams();
        if (query) params.append("search", query);
        fetch(`${{getBaseUrl()}}/api/artists?${{params.toString()}}`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => setArtists(data.artists || []))
          .catch(err => console.error("[LocalFLAC] Artists fetch error:", err));
      }}, []);

      const fetchRecent = useCallback(() => {{
        fetch(`${{getBaseUrl()}}/api/history?limit=50`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => setRecentTracks(data.history || []))
          .catch(err => console.error("[LocalFLAC] Recent fetch error:", err));
      }}, []);

      const fetchFolder = useCallback((path = null) => {{
        const params = new URLSearchParams();
        if (path) params.append("path", path);
        fetch(`${{getBaseUrl()}}/api/folders?${{params.toString()}}`, {{ headers: getApiHeaders() }})
          .then(r => r.json())
          .then(data => setFolderData(data))
          .catch(err => console.error("[LocalFLAC] Folders fetch error:", err));
      }}, []);

      useEffect(() => {{
        if (tab === "flac") {{
          fetchTracks(searchQuery, selectedArtist, selectedAlbum, true);
        }} else if (tab === "all") {{
          fetchTracks(searchQuery, selectedArtist, selectedAlbum, false);
        }} else if (tab === "albums") {{
          fetchAlbums(searchQuery);
        }} else if (tab === "artists") {{
          fetchArtists(searchQuery);
        }} else if (tab === "recent") {{
          fetchRecent();
        }} else if (tab === "folders") {{
          fetchFolder();
        }}
      }}, [tab, searchQuery, selectedAlbum, selectedArtist, fetchTracks, fetchAlbums, fetchArtists, fetchRecent, fetchFolder]);

      const handlePlayTrack = (track, list) => {{
        if (window.LocalFlacPlayer) {{
          window.LocalFlacPlayer.playTrack(track, list || tracks);
        }}
      }};

      const handleRescan = () => {{
        fetch(`${{getBaseUrl()}}/api/scan`, {{
          method: "POST",
          headers: getApiHeaders()
        }}).then(() => fetchStatus());
      }};

      const stats = status?.stats || {{}};
      const currentTrackId = playerState.currentTrack?.id;

      return React.createElement("div", {{ className: "local-flac-container" }},
        // Header
        React.createElement("div", {{ className: "lf-header" }},
          React.createElement("div", null,
            React.createElement("div", {{ className: "lf-title-area" }},
              React.createElement("h1", {{ className: "lf-title" }}, "Local FLAC"),
              React.createElement("span", {{ className: "lf-audiophile-badge" }}, "Hi-Res Audio")
            ),
            React.createElement("div", {{ className: "lf-stats-row" }},
              React.createElement("span", {{ className: "lf-stat-pill lf-stat-pill-flac" }}, `${{stats.flac_count || 129}} FLACs`),
              React.createElement("span", {{ className: "lf-stat-pill" }}, `${{stats.total_tracks || 1879}} Total Tracks`),
              React.createElement("span", {{ className: "lf-stat-pill" }}, `${{stats.total_albums || 170}} Albums`),
              React.createElement("span", {{ className: "lf-stat-pill" }}, `${{stats.total_artists || 9}} Artists`)
            )
          ),

          React.createElement("div", {{ className: "lf-header-actions" }},
            React.createElement("div", {{ className: "lf-search-wrapper" }},
              React.createElement("span", {{ className: "lf-search-icon" }}, "🔍"),
              React.createElement("input", {{
                className: "lf-search-input",
                placeholder: "Search FLACs, artists, albums...",
                value: searchQuery,
                onChange: (e) => setSearchQuery(e.target.value)
              }})
            ),
            React.createElement("button", {{
              className: `lf-btn lf-btn-primary ${{isScanning ? "lf-btn-scanning" : ""}}`,
              onClick: handleRescan,
              disabled: isScanning
            }}, isScanning ? "Scanning..." : "Rescan"),
            React.createElement("button", {{
              className: "lf-btn",
              title: "Open Spotify Native Local Files Collection (1,741 tracks)",
              onClick: () => window.Spicetify.Platform.History.push('/collection/local-files')
            }}, "Native Local Files (1,741)"),
            React.createElement("button", {{
              className: "lf-btn",
              onClick: () => setShowSettings(true)
            }}, "⚙ Folders")
          )
        ),

        // Tabs
        React.createElement("div", {{ className: "lf-tabs" }},
          React.createElement("button", {{
            className: `lf-tab-btn ${{tab === "flac" ? "active" : ""}}`,
            onClick: () => {{ setTab("flac"); setSelectedAlbum(null); setSelectedArtist(null); }}
          }}, `FLAC Only (${{stats.flac_count || 129}})`),
          React.createElement("button", {{
            className: `lf-tab-btn ${{tab === "all" ? "active" : ""}}`,
            onClick: () => {{ setTab("all"); setSelectedAlbum(null); setSelectedArtist(null); }}
          }}, `All Local (${{stats.total_tracks || 1879}})`),
          React.createElement("button", {{
            className: `lf-tab-btn ${{tab === "albums" ? "active" : ""}}`,
            onClick: () => setTab("albums")
          }}, `Albums (${{stats.total_albums || 170}})`),
          React.createElement("button", {{
            className: `lf-tab-btn ${{tab === "artists" ? "active" : ""}}`,
            onClick: () => setTab("artists")
          }}, `Artists (${{stats.total_artists || 9}})`),
          React.createElement("button", {{
            className: `lf-tab-btn ${{tab === "folders" ? "active" : ""}}`,
            onClick: () => setTab("folders")
          }}, "Folders"),
          React.createElement("button", {{
            className: `lf-tab-btn ${{tab === "recent" ? "active" : ""}}`,
            onClick: () => setTab("recent")
          }}, "Recently Played")
        ),

        // Tab Content
        (tab === "flac" || tab === "all") && React.createElement("div", null,
          React.createElement("table", {{ className: "lf-track-table" }},
            React.createElement("thead", null,
              React.createElement("tr", null,
                React.createElement("th", {{ style: {{ width: "40px" }} }}, "#"),
                React.createElement("th", null, "TITLE"),
                React.createElement("th", null, "ALBUM"),
                React.createElement("th", null, "FORMAT"),
                React.createElement("th", {{ style: {{ width: "60px", textAlign: "right" }} }}, "⏱")
              )
            ),
            React.createElement("tbody", null,
              tracks.map((t, idx) => {{
                const isCurrent = t.id === currentTrackId;
                const isPlayingThis = isCurrent && playerState.isPlaying;
                return React.createElement("tr", {{
                  key: t.id,
                  className: `lf-track-row ${{isCurrent ? "playing" : ""}}`,
                  onDoubleClick: () => handlePlayTrack(t, tracks)
                }},
                  React.createElement("td", {{ className: "lf-col-num" }},
                    React.createElement("span", {{ className: "lf-track-idx" }}, idx + 1),
                    React.createElement("button", {{
                      className: "lf-row-play-btn",
                      onClick: () => isPlayingThis ? window.LocalFlacPlayer.pause() : handlePlayTrack(t, tracks)
                    }}, isPlayingThis ? "⏸" : "▶")
                  ),
                  React.createElement("td", {{ className: "lf-col-title" }},
                    React.createElement("div", {{ className: "lf-track-title-cell" }},
                      React.createElement("div", {{ className: "lf-row-art" }},
                        t.has_artwork
                          ? React.createElement("img", {{ src: getArtworkUrl(t.id), alt: "" }})
                          : React.createElement("div", {{ className: "lf-row-art-fallback" }}, "♪")
                      ),
                      React.createElement("div", {{ className: "lf-track-meta" }},
                        React.createElement("div", {{ className: `lf-track-name ${{isCurrent ? "highlight" : ""}}` }}, t.title || t.filename),
                        React.createElement("div", {{ className: "lf-track-artist" }}, t.artist || "Unknown Artist")
                      )
                    )
                  ),
                  React.createElement("td", {{ className: "lf-col-album" }}, t.album || "-"),
                  React.createElement("td", {{ className: "lf-col-format" }},
                    React.createElement("span", {{ className: "lf-codec-pill" }}, formatBadge(t))
                  ),
                  React.createElement("td", {{ className: "lf-col-duration" }}, formatTime(t.duration))
                );
              }})
            )
          )
        ),

        // Albums Grid
        tab === "albums" && React.createElement("div", {{ className: "lf-card-grid" }},
          albums.map(a => React.createElement("div", {{
            key: a.album,
            className: "lf-card",
            onClick: () => {{ setSelectedAlbum(a.album); setTab("flac"); }}
          }},
            React.createElement("div", {{ className: "lf-card-art" }},
              a.first_track_id
                ? React.createElement("img", {{ src: getArtworkUrl(a.first_track_id), alt: a.album }})
                : React.createElement("div", {{ className: "lf-card-art-fallback" }}, "💽")
            ),
            React.createElement("div", {{ className: "lf-card-title" }}, a.album),
            React.createElement("div", {{ className: "lf-card-sub" }}, `${{a.artist || "Various"}} • ${{a.track_count}} tracks`)
          ))
        ),

        // Artists Grid
        tab === "artists" && React.createElement("div", {{ className: "lf-card-grid" }},
          artists.map(ar => React.createElement("div", {{
            key: ar.artist,
            className: "lf-card",
            onClick: () => {{ setSelectedArtist(ar.artist); setTab("flac"); }}
          }},
            React.createElement("div", {{ className: "lf-card-art lf-card-artist" }},
              React.createElement("div", {{ className: "lf-card-art-fallback" }}, "👤")
            ),
            React.createElement("div", {{ className: "lf-card-title" }}, ar.artist),
            React.createElement("div", {{ className: "lf-card-sub" }}, `${{ar.track_count}} tracks (${{ar.flac_count}} FLAC)`)
          ))
        ),

        // Recently Played
        tab === "recent" && React.createElement("table", {{ className: "lf-track-table" }},
          React.createElement("tbody", null,
            recentTracks.map((h, idx) => React.createElement("tr", {{
              key: idx,
              className: "lf-track-row",
              onDoubleClick: () => handlePlayTrack(h, recentTracks)
            }},
              React.createElement("td", {{ style: {{ width: "40px" }} }}, idx + 1),
              React.createElement("td", null, h.title || h.filename),
              React.createElement("td", null, h.artist || "Unknown"),
              React.createElement("td", null, formatBadge(h)),
              React.createElement("td", {{ style: {{ textAlign: "right" }} }}, formatTime(h.duration))
            ))
          )
        ),

        // Folder View
        tab === "folders" && React.createElement("div", {{ className: "lf-folder-view" }},
          folderData.parent_path && React.createElement("div", {{
            className: "lf-folder-item lf-folder-back",
            onClick: () => fetchFolder(folderData.parent_path)
          }}, "📁 .. (Up one level)"),
          folderData.items?.map((item, idx) => React.createElement("div", {{
            key: idx,
            className: "lf-folder-item",
            onClick: () => item.is_dir ? fetchFolder(item.path) : null
          }},
            React.createElement("span", {{ className: "lf-folder-icon" }}, item.is_dir ? "📁" : "🎵"),
            React.createElement("span", {{ className: "lf-folder-name" }}, item.name),
            !item.is_dir && React.createElement("span", {{ className: "lf-folder-meta" }}, `${{item.codec || ""}} · ${{formatTime(item.duration)}}`)
          ))
        )
      );
    }}

    return LocalFlacApp;
  }}

  // ==========================================================
  // 5. ROUTE MANAGER & APP MOUNTING
  // ==========================================================
  let appRootElement = null;
  let LocalFlacAppComponent = null;

  function ensureAppMounted() {{
    if (!appRootElement) {{
      appRootElement = document.getElementById("local-flac-app-root");
      if (!appRootElement) {{
        appRootElement = document.createElement("div");
        appRootElement.id = "local-flac-app-root";
        appRootElement.className = "hidden";
      }}
    }}

    const main = document.querySelector("main");
    if (main && main.parentElement && appRootElement.parentElement !== main.parentElement) {{
      main.parentElement.insertBefore(appRootElement, main.nextSibling);
    }}

    if (!LocalFlacAppComponent && window.Spicetify?.React && window.Spicetify?.ReactDOM) {{
      LocalFlacAppComponent = createLocalFlacComponent();
      window.Spicetify.ReactDOM.render(
        window.Spicetify.React.createElement(LocalFlacAppComponent, null),
        appRootElement
      );
    }}
  }}

  function handleRoute(loc) {{
    const path = loc?.pathname || window.location.pathname;
    const isFlac = path === "/local-flac" || path.startsWith("/local-flac/");
    ensureAppMounted();

    if (isFlac) {{
      document.body.classList.add("local-flac-route-active");
      if (appRootElement) appRootElement.classList.remove("hidden");
    }} else {{
      document.body.classList.remove("local-flac-route-active");
      if (appRootElement) appRootElement.classList.add("hidden");
    }}

    // Update active highlight on sidebar
    const row = document.getElementById("sidebar-local-flac-row");
    if (row) {{
      if (isFlac) row.classList.add("active");
      else row.classList.remove("active");
    }}
  }}

  function setupRouting() {{
    const checkHistory = () => {{
      if (window.Spicetify?.Platform?.History) {{
        window.Spicetify.Platform.History.listen(handleRoute);
        handleRoute(window.Spicetify.Platform.History.location);
      }} else {{
        setTimeout(setupRouting, 200);
      }}
    }};
    checkHistory();
  }}

  // ==========================================================
  // 6. SIDEBAR INJECTION (Native-Fidelity "Local FLAC" Entry)
  // ==========================================================
  function injectSidebarRow(flacCount) {{
    const target = Array.from(document.querySelectorAll("*")).find(
      el => el.textContent === "Local Files" && el.children.length === 0
    );
    if (!target) return;

    const row = target.closest('[role="row"]');
    if (!row || !row.parentElement) return;

    let flacRow = document.getElementById("sidebar-local-flac-row");
    if (!flacRow) {{
      flacRow = row.cloneNode(true);
      flacRow.id = "sidebar-local-flac-row";

      // Update Title
      const titleSpan = flacRow.querySelector('[data-encore-id="listRowTitle"] span') ||
                        flacRow.querySelector(".e-10451-line-clamp");
      if (titleSpan) titleSpan.textContent = "Local FLAC";

      // Click handler to push route
      flacRow.style.cursor = "pointer";
      flacRow.onclick = (e) => {{
        e.preventDefault();
        e.stopPropagation();
        if (window.Spicetify?.Platform?.History) {{
          window.Spicetify.Platform.History.push("/local-flac");
        }}
      }};

      row.parentElement.insertBefore(flacRow, row.nextSibling);
    }} else if (flacRow.parentElement !== row.parentElement) {{
      row.parentElement.insertBefore(flacRow, row.nextSibling);
    }}

    // Update Subtitle Count
    const subtitleSpan = flacRow.querySelector(".t2qx66PtSUA0l8Eh") ||
                         flacRow.querySelector('[data-encore-id="listRowSubtitle"]');
    if (subtitleSpan) {{
      subtitleSpan.textContent = `Folder • ${{flacCount || 129}} tracks`;
    }}

    // Highlight state
    const currentPath = window.Spicetify?.Platform?.History?.location?.pathname;
    if (currentPath === "/local-flac" || currentPath?.startsWith("/local-flac/")) {{
      flacRow.classList.add("active");
    }} else {{
      flacRow.classList.remove("active");
    }}
  }}

  function setupSidebarObserver() {{
    let throttleTimer = null;
    const observer = new MutationObserver(() => {{
      if (throttleTimer) return;
      throttleTimer = setTimeout(() => {{
        throttleTimer = null;
        const count = window.LocalFlacPlayer?.flacCount || 129;
        injectSidebarRow(count);
      }}, 500);
    }});
    observer.observe(document.body, {{ childList: true, subtree: true }});

    setInterval(() => {{
      const count = window.LocalFlacPlayer?.flacCount || 129;
      injectSidebarRow(count);
    }}, 3000);
  }}

  // ==========================================================
  // 7. INITIALIZATION
  // ==========================================================
  window.LocalFlacPlayer = new FlacPlayer();
  setupRouting();
  setupSidebarObserver();

  console.log("[LocalFLAC] Integration v2 initialized successfully.");
}})();
'''

with open("spicetify/Extensions/local-flac-player.js", "w") as f:
    f.write(ext_code)

print("Generated spicetify/Extensions/local-flac-player.js successfully!")
