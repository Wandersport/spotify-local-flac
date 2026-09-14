// Spotify Local FLAC - Extension Glue & Integration
// Injects styles, manages routing, sidebar item, and settings toggle.

(function initSpotifyLocalFlacExtension() {
  "use strict";

  // 1. Style Injection (Global)
  const STYLE_ID = "local-flac-styles";
  function injectStyles(cssContent) {
    let style = document.getElementById(STYLE_ID);
    if (!style) {
      style = document.createElement("style");
      style.id = STYLE_ID;
      document.head.appendChild(style);
    }
    if (cssContent && style.textContent !== cssContent) {
      style.textContent = cssContent;
    }
  }

  // Fallback inline styles if not passed during build
  if (typeof __LOCAL_FLAC_CSS__ !== "undefined") {
    injectStyles(__LOCAL_FLAC_CSS__);
  }

  // 2. App Mounting & Route Management
  let appRootElement = null;
  let LocalFlacAppComponent = null;

  function ensureAppMounted() {
    if (!appRootElement) {
      appRootElement = document.getElementById("local-flac-app-root");
      if (!appRootElement) {
        appRootElement = document.createElement("div");
        appRootElement.id = "local-flac-app-root";
        appRootElement.className = "hidden";
      }
    }

    const main = document.querySelector("main");
    if (main && main.parentElement && appRootElement.parentElement !== main.parentElement) {
      main.parentElement.insertBefore(appRootElement, main.nextSibling);
    }

    if ((!LocalFlacAppComponent || !appRootElement.firstElementChild) && window.Spicetify?.React && window.Spicetify?.ReactDOM) {
      if (!LocalFlacAppComponent && typeof createLocalFlacComponent === "function") {
        LocalFlacAppComponent = createLocalFlacComponent();
      }
      if (LocalFlacAppComponent) {
        window.Spicetify.ReactDOM.render(
          window.Spicetify.React.createElement(LocalFlacAppComponent, null),
          appRootElement
        );
      }
    }
  }

  function handleRoute(loc) {
    const path = loc?.pathname || window.location.pathname;
    const isFlac = path === "/local-flac" || path.startsWith("/local-flac/");

    if (isFlac && !isLocalFlacEnabled()) {
      window.Spicetify?.Platform?.History?.push("/");
      return;
    }

    ensureAppMounted();

    if (isFlac) {
      document.body.classList.add("local-flac-route-active");
      if (appRootElement) appRootElement.classList.remove("hidden");
    } else {
      document.body.classList.remove("local-flac-route-active");
      if (appRootElement) appRootElement.classList.add("hidden");
    }

    // Ensure sidebar row is injected and has proper active state
    injectSidebarRow(window.LocalFlacPlayer?.flacCount || 0);

    if (path === "/preferences" || path.startsWith("/preferences")) {
      setTimeout(injectSettingsToggle, 200);
    }
  }

  function setupRouting() {
    const checkHistory = () => {
      if (window.Spicetify?.Platform?.History) {
        window.Spicetify.Platform.History.listen(handleRoute);
        handleRoute(window.Spicetify.Platform.History.location);
      } else {
        setTimeout(setupRouting, 200);
      }
    };
    checkHistory();
  }

  // 3. Native Sidebar Row Injection
  function injectSidebarRow(flacCount) {
    const target = Array.from(document.querySelectorAll("*")).find(
      el => el.textContent === "Local Files" && el.children.length === 0
    );
    if (!target) return;

    const row = target.closest('[role="row"]');
    if (!row || !row.parentElement) return;

    const enabled = isLocalFlacEnabled();
    let flacRow = document.getElementById("sidebar-local-flac-row");
    if (!flacRow) {
      flacRow = row.cloneNode(true);
      flacRow.id = "sidebar-local-flac-row";

      // Update Title
      const titleSpan = flacRow.querySelector('[data-encore-id="listRowTitle"] span') ||
                        flacRow.querySelector(".e-10451-line-clamp");
      if (titleSpan) titleSpan.textContent = "Local FLAC";

      // Click handler to push route
      flacRow.style.cursor = "pointer";
      flacRow.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!isLocalFlacEnabled()) return;
        if (window.Spicetify?.Platform?.History) {
          window.Spicetify.Platform.History.push("/local-flac");
        }
      };

      row.parentElement.insertBefore(flacRow, row.nextSibling);
    } else if (flacRow.parentElement !== row.parentElement) {
      row.parentElement.insertBefore(flacRow, row.nextSibling);
    }

    flacRow.style.display = enabled ? "" : "none";

    // Update Subtitle Count
    const subtitleSpan = flacRow.querySelector(".t2qx66PtSUA0l8Eh") ||
                         flacRow.querySelector('[data-encore-id="listRowSubtitle"]');
    if (subtitleSpan) {
      subtitleSpan.textContent = `Folder • ${(flacCount || 0).toLocaleString()} tracks`;
    }

    // Highlight state
    const currentPath = window.Spicetify?.Platform?.History?.location?.pathname;
    if (currentPath === "/local-flac" || currentPath?.startsWith("/local-flac/")) {
      flacRow.classList.add("active");
    } else {
      flacRow.classList.remove("active");
    }
  }

  // 4. Settings Toggle Injection in /preferences
  function injectSettingsToggle() {
    const currentPath = window.Spicetify?.Platform?.History?.location?.pathname || window.location.pathname;
    if (currentPath !== "/preferences" && !currentPath.startsWith("/preferences")) return;

    if (document.getElementById("settings-local-flac-row")) return;

    const localFilesInput = document.getElementById("settings.showLocalFiles");
    let targetRow = localFilesInput ? localFilesInput.closest(".x-settings-row") : null;

    if (!targetRow) {
      const labels = Array.from(document.querySelectorAll(".x-settings-row label, .x-settings-firstColumn label"));
      const found = labels.find(l => {
        const text = (l.innerText || "").toLowerCase();
        return text.includes("local files") || text.includes("archivos locales");
      });
      if (found) targetRow = found.closest(".x-settings-row");
    }

    if (!targetRow || !targetRow.parentElement) return;

    const isEnabled = isLocalFlacEnabled();

    // 1. Show Local FLAC Toggle Row
    const flacRow = document.createElement("div");
    flacRow.className = "x-settings-row";
    flacRow.id = "settings-local-flac-row";
    flacRow.innerHTML = `
      <div class="x-settings-firstColumn">
        <label class="e-10451-text encore-text-body-small encore-internal-color-text-subdued" data-encore-id="text" for="settings.showLocalFlac">Show Local FLAC</label>
      </div>
      <div class="x-settings-secondColumn">
        <label class="x-toggle-wrapper">
          <input id="settings.showLocalFlac" class="x-toggle-input" type="checkbox" ${isEnabled ? "checked" : ""}>
          <span class="x-toggle-indicatorWrapper"><span class="x-toggle-indicator"></span></span>
        </label>
      </div>
    `;

    // 2. Manage Folders Button Row
    const folderRow = document.createElement("div");
    folderRow.className = "x-settings-row";
    folderRow.id = "settings-local-flac-manage-folders-row";
    if (!isEnabled) folderRow.style.display = "none";
    folderRow.innerHTML = `
      <div class="x-settings-firstColumn">
        <label class="e-10451-text encore-text-body-small encore-internal-color-text-subdued" data-encore-id="text">Local FLAC Folders</label>
      </div>
      <div class="x-settings-secondColumn">
        <button class="encore-text-body-small-bold e-10451-legacy-button--small e-10451-legacy-button-secondary--text-base encore-internal-color-text-base e-10451-legacy-button e-10451-legacy-button-secondary e-10451-overflow-wrap-anywhere" id="btn-manage-flac-folders" data-encore-id="buttonSecondary">Manage Local FLAC folders</button>
      </div>
    `;

    targetRow.parentElement.insertBefore(flacRow, targetRow.nextSibling);
    flacRow.parentElement.insertBefore(folderRow, flacRow.nextSibling);

    const toggleInput = flacRow.querySelector("#settings\\.showLocalFlac") || flacRow.querySelector("input[type='checkbox']");
    if (toggleInput) {
      toggleInput.onchange = (e) => {
        const checked = e.target.checked;
        localStorage.setItem("local_flac_enabled", checked ? "true" : "false");
        folderRow.style.display = checked ? "" : "none";

        const sidebarRow = document.getElementById("sidebar-local-flac-row");
        if (sidebarRow) {
          sidebarRow.style.display = checked ? "" : "none";
        }

        const curPath = window.Spicetify?.Platform?.History?.location?.pathname || window.location.pathname;
        if (!checked && (curPath === "/local-flac" || curPath?.startsWith("/local-flac/"))) {
          window.Spicetify.Platform.History.push("/");
        }

        console.log("[LocalFLAC] Setting Show Local FLAC toggled:", checked);
      };
    }

    const folderBtn = folderRow.querySelector("#btn-manage-flac-folders");
    if (folderBtn) {
      folderBtn.onclick = () => {
        if (window.Spicetify?.Platform?.History) {
          window.Spicetify.Platform.History.push("/local-flac");
          setTimeout(() => {
            const btns = Array.from(document.querySelectorAll(".lf-header-actions button, button"));
            const folderModalBtn = btns.find(b => (b.innerText || "").includes("Folders"));
            if (folderModalBtn) folderModalBtn.click();
          }, 400);
        }
      };
    }
  }

  function setupSidebarObserver() {
    let throttleTimer = null;
    const observer = new MutationObserver(() => {
      if (throttleTimer) return;
      throttleTimer = setTimeout(() => {
        throttleTimer = null;
        const count = window.LocalFlacPlayer?.flacCount || 0;
        injectSidebarRow(count);
        injectSettingsToggle();
      }, 500);
    });
    observer.observe(document.body, { childList: true, subtree: true });

    setInterval(() => {
      const count = window.LocalFlacPlayer?.flacCount || 0;
      injectSidebarRow(count);
      injectSettingsToggle();
    }, 2000);
  }

  // 5. Player and Integration Initialization
  if (typeof FlacPlayer === "function") {
    window.LocalFlacPlayer = new FlacPlayer();
  }
  setupRouting();
  setupSidebarObserver();

  console.log("[LocalFLAC] Extension initialized successfully.");
})();
