// Spotify Local FLAC - Global Player & Playback State Machine

class FlacPlayer {
  constructor() {
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
    this.playbackOwner = "NONE"; // 'LOCAL_FLAC' | 'SPOTIFY_NATIVE' | 'NONE'
    this.audio.volume = this.isMuted ? 0 : this.volume;

    this._setupAudioListeners();
    this._setupSpotifySync();
    this._createBottomBar();
    this._setupMediaSession();
    this._setupKeyboardShortcuts();
    this._updateSidebarCount();
  }

  subscribe(fn) {
    this.listeners.add(fn);
    fn(this.getState());
    return () => this.listeners.delete(fn);
  }

  _notify() {
    const state = this.getState();
    this.listeners.forEach(fn => fn(state));
    this._updateBottomBar();
  }

  getState() {
    return {
      currentTrack: this.currentTrack,
      isPlaying: this.isPlaying,
      currentTime: this.currentTime,
      duration: this.duration,
      volume: this.volume,
      isMuted: this.isMuted,
      shuffle: this.shuffle,
      repeat: this.repeat,
      queueLength: this.queue.length,
      queueIndex: this.queueIndex,
      playbackOwner: this.playbackOwner
    };
  }

  _setupAudioListeners() {
    this.audio.addEventListener("play", () => {
      this.isPlaying = true;
      this.playbackOwner = "LOCAL_FLAC";
      document.body.classList.add("local-flac-playing");
      const bar = document.getElementById("local-flac-bottom-bar");
      if (bar) bar.classList.remove("hidden");
      this._notify();
    });

    this.audio.addEventListener("pause", () => {
      this.isPlaying = false;
      this._notify();
    });

    this.audio.addEventListener("timeupdate", () => {
      this.currentTime = this.audio.currentTime;
      this.duration = this.audio.duration || this.currentTrack?.duration || 0;
      this._updateProgressOnly();
    });

    this.audio.addEventListener("durationchange", () => {
      this.duration = this.audio.duration || this.currentTrack?.duration || 0;
      this._notify();
    });

    this.audio.addEventListener("ended", () => {
      this._handleTrackEnded();
    });

    this.audio.addEventListener("error", (e) => {
      console.error("[LocalFLAC] Audio error:", e);
      this.isPlaying = false;
      this._notify();
    });
  }

  transferToSpotifyNative() {
    if (this.playbackOwner !== "LOCAL_FLAC") return;
    console.log("[LocalFLAC] owner LOCAL_FLAC -> SPOTIFY_NATIVE");
    this.playbackOwner = "SPOTIFY_NATIVE";
    this.audio.pause();
    this.isPlaying = false;
    document.body.classList.remove("local-flac-playing");
    const bar = document.getElementById("local-flac-bottom-bar");
    if (bar) bar.classList.add("hidden");
    this._notify();
  }

  _setupSpotifySync() {
    const pauseNative = () => {
      try {
        if (window.Spicetify && window.Spicetify.Player && window.Spicetify.Player.isPlaying()) {
          window.Spicetify.Player.pause();
        }
        if (window.Spicetify?.Platform?.PlayerAPI?.pause) {
          window.Spicetify.Platform.PlayerAPI.pause();
        }
      } catch(e) {}
    };

    this.audio.addEventListener("play", pauseNative);
    this.audio.addEventListener("playing", pauseNative);

    const checkSpotify = () => {
      if (!window.Spicetify?.Player) {
        setTimeout(checkSpotify, 500);
        return;
      }

      // 1. Listen to Spicetify.Player onplaypause
      window.Spicetify.Player.addEventListener("onplaypause", () => {
        try {
          if (window.Spicetify.Player.isPlaying()) {
            this.transferToSpotifyNative();
          }
        } catch(e) {}
      });

      // 2. Listen to Spicetify.Player songchange
      window.Spicetify.Player.addEventListener("songchange", () => {
        try {
          const curUri = window.Spicetify.Player.data?.item?.uri || "";
          if (curUri && !curUri.startsWith("spotify:local:flac")) {
            this.transferToSpotifyNative();
          }
        } catch(e) {}
      });

      // 3. Listen directly to PlayerAPI core events
      try {
        if (window.Spicetify.Platform?.PlayerAPI?._events?.addListener) {
          window.Spicetify.Platform.PlayerAPI._events.addListener("update", (ev) => {
            if (ev?.data?.item && !ev.data.isPaused) {
              this.transferToSpotifyNative();
            }
          });
        }
      } catch(e) {}
    };

    checkSpotify();
  }

  _handleTrackEnded() {
    if (this.repeat === "one") {
      this.audio.currentTime = 0;
      this.audio.play();
    } else if (this.queueIndex < this.queue.length - 1) {
      this.next();
    } else if (this.repeat === "all" && this.queue.length > 0) {
      this.queueIndex = 0;
      this.playTrack(this.queue[0]);
    } else {
      console.log("[LocalFLAC] owner LOCAL_FLAC -> NONE (queue ended)");
      this.isPlaying = false;
      this.playbackOwner = "NONE";
      this.currentTime = 0;
      document.body.classList.remove("local-flac-playing");
      const bar = document.getElementById("local-flac-bottom-bar");
      if (bar) bar.classList.remove("hidden");
      this._notify();
    }
  }

  _setupMediaSession() {
    if (!("mediaSession" in navigator)) return;
    navigator.mediaSession.setActionHandler("play", () => this.resume());
    navigator.mediaSession.setActionHandler("pause", () => this.pause());
    navigator.mediaSession.setActionHandler("previoustrack", () => this.prev());
    navigator.mediaSession.setActionHandler("nexttrack", () => this.next());
    navigator.mediaSession.setActionHandler("seekto", (details) => {
      if (details.seekTime !== undefined) this.seek(details.seekTime);
    });
  }

  _setupKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
      if (["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
      if (this.playbackOwner !== "LOCAL_FLAC") return;

      if (e.code === "Space") {
        e.preventDefault();
        this.togglePlay();
      } else if (e.ctrlKey && e.code === "ArrowRight") {
        e.preventDefault();
        this.next();
      } else if (e.ctrlKey && e.code === "ArrowLeft") {
        e.preventDefault();
        this.prev();
      } else if (e.shiftKey && e.code === "ArrowRight") {
        e.preventDefault();
        this.seek(this.currentTime + 5);
      } else if (e.shiftKey && e.code === "ArrowLeft") {
        e.preventDefault();
        this.seek(this.currentTime - 5);
      }
    });
  }

  _updateMediaSession() {
    if (!("mediaSession" in navigator) || !this.currentTrack) return;
    const t = this.currentTrack;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t.title || t.filename,
      artist: t.artist || "Unknown Artist",
      album: t.album || "Local FLAC",
      artwork: t.has_artwork ? [{ src: getArtworkUrl(t.id), sizes: "512x512", type: "image/jpeg" }] : []
    });
  }

  playTrack(track, queue = null, index = -1) {
    if (!track) return;
    if (queue) {
      this.queue = queue;
      this.queueIndex = index >= 0 ? index : queue.findIndex(t => t.id === track.id);
    } else if (!this.queue.some(t => t.id === track.id)) {
      this.queue = [track];
      this.queueIndex = 0;
    } else {
      this.queueIndex = this.queue.findIndex(t => t.id === track.id);
    }

    this.currentTrack = track;
    this.duration = track.duration || 0;
    this.currentTime = 0;

    // Ensure Spotify native is paused and transition ownership to LOCAL_FLAC
    try {
      if (window.Spicetify && window.Spicetify.Player && window.Spicetify.Player.isPlaying()) {
        window.Spicetify.Player.pause();
      }
      if (window.Spicetify?.Platform?.PlayerAPI?.pause) {
        window.Spicetify.Platform.PlayerAPI.pause();
      }
    } catch(e) {}

    const prevOwner = this.playbackOwner;
    this.playbackOwner = "LOCAL_FLAC";
    if (prevOwner !== "LOCAL_FLAC") {
      console.log(`[LocalFLAC] owner ${prevOwner} -> LOCAL_FLAC`);
    }

    document.body.classList.add("local-flac-playing");
    const bar = document.getElementById("local-flac-bottom-bar");
    if (bar) bar.classList.remove("hidden");

    const url = getStreamUrl(track.id);
    this.audio.src = url;
    this.audio.currentTime = 0;

    const playPromise = this.audio.play();
    if (playPromise !== undefined) {
      playPromise.catch(err => {
        console.warn("[LocalFLAC] Autoplay prevented or stream error:", err);
      });
    }

    // Report to history endpoint
    fetch(`${getBaseUrl()}/api/history`, {
      method: "POST",
      headers: getApiHeaders(),
      body: JSON.stringify({ track_id: track.id })
    }).catch(() => {});

    this._updateMediaSession();
    this._notify();
  }

  resume() {
    if (this.currentTrack && this.audio.src) {
      try {
        if (window.Spicetify && window.Spicetify.Player && window.Spicetify.Player.isPlaying()) {
          window.Spicetify.Player.pause();
        }
        if (window.Spicetify?.Platform?.PlayerAPI?.pause) {
          window.Spicetify.Platform.PlayerAPI.pause();
        }
      } catch(e) {}

      const prevOwner = this.playbackOwner;
      this.playbackOwner = "LOCAL_FLAC";
      if (prevOwner !== "LOCAL_FLAC") {
        console.log(`[LocalFLAC] owner ${prevOwner} -> LOCAL_FLAC`);
      }

      document.body.classList.add("local-flac-playing");
      const bar = document.getElementById("local-flac-bottom-bar");
      if (bar) bar.classList.remove("hidden");

      this.audio.play();
    } else if (this.queue.length > 0) {
      this.playTrack(this.queue[0]);
    }
  }

  pause() {
    this.audio.pause();
  }

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.resume();
    }
  }

  seek(seconds) {
    const target = Math.max(0, Math.min(this.duration, seconds));
    this.audio.currentTime = target;
    this.currentTime = target;
    this._updateProgressOnly();
  }

  setVolume(fraction) {
    const val = Math.max(0, Math.min(1, fraction));
    this.volume = val;
    this.isMuted = false;
    this.audio.volume = val;
    localStorage.setItem("local_flac_volume", val.toString());
    localStorage.setItem("local_flac_muted", "false");
    this._notify();
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    this.audio.volume = this.isMuted ? 0 : this.volume;
    localStorage.setItem("local_flac_muted", this.isMuted ? "true" : "false");
    this._notify();
  }

  toggleShuffle() {
    this.shuffle = !this.shuffle;
    localStorage.setItem("local_flac_shuffle", this.shuffle ? "true" : "false");
    this._notify();
  }

  toggleRepeat() {
    const modes = ["off", "all", "one"];
    const nextIdx = (modes.indexOf(this.repeat) + 1) % modes.length;
    this.repeat = modes[nextIdx];
    localStorage.setItem("local_flac_repeat", this.repeat);
    this._notify();
  }

  next() {
    if (this.queue.length === 0) return;
    if (this.shuffle) {
      const nextIdx = Math.floor(Math.random() * this.queue.length);
      this.queueIndex = nextIdx;
      this.playTrack(this.queue[nextIdx]);
    } else if (this.queueIndex < this.queue.length - 1) {
      this.queueIndex++;
      this.playTrack(this.queue[this.queueIndex]);
    } else if (this.repeat === "all") {
      this.queueIndex = 0;
      this.playTrack(this.queue[0]);
    }
  }

  prev() {
    if (this.audio.currentTime > 3) {
      this.seek(0);
      return;
    }
    if (this.queueIndex > 0) {
      this.queueIndex--;
      this.playTrack(this.queue[this.queueIndex]);
    } else {
      this.seek(0);
    }
  }

  _createBottomBar() {
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
    const handleSeek = (e) => {
      const rect = seekBar.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      this.seek(ratio * this.duration);
    };
    seekBar.onclick = handleSeek;

    // Volume Bar Dragging / Clicking
    const volBar = bar.querySelector(".lfb-vol-bar");
    const handleVol = (e) => {
      const rect = volBar.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      this.setVolume(ratio);
    };
    volBar.onclick = handleVol;

    this._mountBarIntoDom(bar);
    setInterval(() => this._mountBarIntoDom(bar), 2000);
  }

  _mountBarIntoDom(bar) {
    const targetContainer = document.querySelector('aside[data-testid="now-playing-bar"]') ||
                            document.querySelector('.Root__now-playing-bar') ||
                            document.querySelector('footer');

    if (targetContainer) {
      if (bar.parentElement !== targetContainer) {
        targetContainer.appendChild(bar);
        bar.classList.remove("fallback-fixed");
      }
    } else {
      if (bar.parentElement !== document.body) {
        document.body.appendChild(bar);
        bar.classList.add("fallback-fixed");
      }
    }
  }

  _updateBottomBar() {
    const bar = document.getElementById("local-flac-bottom-bar");
    if (!bar) return;

    const track = this.currentTrack;
    if (this.playbackOwner !== "LOCAL_FLAC" || !track) {
      bar.classList.add("hidden");
      document.body.classList.remove("local-flac-playing");
      return;
    }

    bar.classList.remove("hidden");
    document.body.classList.add("local-flac-playing");

    // Update Art
    const artImg = bar.querySelector(".lfb-art");
    const artFallback = bar.querySelector(".lfb-art-fallback");
    if (track.has_artwork) {
      artImg.src = getArtworkUrl(track.id);
      artImg.style.display = "block";
      artFallback.style.display = "none";
    } else {
      artImg.style.display = "none";
      artFallback.style.display = "flex";
    }

    // Update Title & Artist
    bar.querySelector(".lfb-title").textContent = track.title || track.filename;
    bar.querySelector(".lfb-artist").textContent = track.artist || "Unknown Artist";

    // Update Quality Badge
    bar.querySelector(".lfb-badge").textContent = formatBadge(track);

    // Update Play/Pause Icon
    const playIcon = bar.querySelector(".lfb-icon-play");
    const pauseIcon = bar.querySelector(".lfb-icon-pause");
    if (this.isPlaying) {
      playIcon.style.display = "none";
      pauseIcon.style.display = "block";
    } else {
      playIcon.style.display = "block";
      pauseIcon.style.display = "none";
    }

    // Update Shuffle / Repeat States
    const shuffleBtn = bar.querySelector(".lfb-shuffle-btn");
    if (this.shuffle) shuffleBtn.classList.add("active");
    else shuffleBtn.classList.remove("active");

    const repeatBtn = bar.querySelector(".lfb-repeat-btn");
    if (this.repeat !== "off") repeatBtn.classList.add("active");
    else repeatBtn.classList.remove("active");

    // Update Volume Fill
    const volFill = bar.querySelector(".lfb-vol-fill");
    volFill.style.width = `${(this.isMuted ? 0 : this.volume) * 100}%`;

    this._updateProgressOnly();
  }

  _updateProgressOnly() {
    const bar = document.getElementById("local-flac-bottom-bar");
    if (!bar || this.playbackOwner !== "LOCAL_FLAC") return;

    const curTime = bar.querySelector(".lfb-cur-time");
    const totTime = bar.querySelector(".lfb-tot-time");
    const seekFill = bar.querySelector(".lfb-seek-fill");

    curTime.textContent = formatTime(this.currentTime);
    totTime.textContent = formatTime(this.duration);

    const ratio = this.duration > 0 ? (this.currentTime / this.duration) : 0;
    seekFill.style.width = `${ratio * 100}%`;
  }

  _updateSidebarCount() {
    fetch(`${getBaseUrl()}/api/status`, { headers: getApiHeaders() })
      .then(r => r.json())
      .then(data => {
        this.flacCount = data.stats?.flac_count || 0;
        if (typeof window.__injectLocalFlacSidebarRow === "function") {
          window.__injectLocalFlacSidebarRow(this.flacCount);
        }
      })
      .catch(() => {});
  }
}
