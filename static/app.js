/**
 * EliteBabes.com Clone — Real-Time AI Image Enhancer Studio Frontend
 * Features:
 *  - Portrait Intelligence: Eye & Catchlight Pop, f/1.4 Bokeh Blur, Auto-Exposure/WB & Smart Framing
 *  - Synchronized Pan/Zoom, Dual 3x Inspection Loupe & 4-Way Quad-Preset Matrix View
 *  - Perceptual Hash (dHash) Burst Deduplication & Visual Similarity Search
 *  - Live RGB & Luminance Canvas Histograms + YCrCb Skin-Mask & Sharpness Telemetry
 *  - 3D .cube LUT Grading & Iterative Back-Projection (IBP) Super-Resolution
 *  - Persistent SQLite Metadata, 1-5 Star Ratings, Favorites & Custom Tags
 *  - Custom Preset Saving & Deletion + Autoplay 4K Slideshow
 *  - Multi-Folder Switcher, SSE Live Watcher & Batch 4K ZIP Exporter
 *  - Local Video Keyframe Scrubber, AI Best-Frame Auto-Scanner & 4K Animated WebP Loop Extractor
 *  - Boss-Key / Instant Privacy Disguise & Optional PIN Lock
 */

const state = {
  allImages: [],
  filteredImages: [],
  categories: [],
  models: [],
  presetConfigs: {},
  luts: [],
  activeQuery: "",
  activeCategory: "",
  activeModel: "",
  activeBoardId: "",
  boards: [],
  boardItems: {},
  activeColorFilter: "",
  activePinImageId: "",
  museTimer: null,
  currentMuseId: "",
  currentMuseItem: null,
  museSpinning: true,
  museActiveSlot: "current",
  museEnabled: localStorage.getItem("elitebabes_muse_enabled") !== "false",
  filtersCollapsed: localStorage.getItem("elitebabes_filters_collapsed") === "true",
  minRating: 0,
  onlyFavorites: false,
  onlyUploaded: false,
  deduplicate: false,
  similarTo: "",
  favorites: new Set(JSON.parse(localStorage.getItem("elitebabes_favs") || "[]")),
  enhancedSet: new Set(),
  uploadQueue: [],
  uploadObjectUrls: [],
  lastUploadedIds: [],
  currentModalIndex: -1,
  currentPreset: "ultra_hot_4k",
  currentViewMode: "side-by-side",
  matrixSet: "flagship",
  currentFormat: "jpg",
  histMode: "luma",
  lastHistograms: null,
  // Synchronized Zoom, Pan & Loupe state
  zoomLevel: 1,
  panX: 0,
  panY: 0,
  loupeEnabled: false,
  // Autoplay Slideshow state
  slideshowTimer: null,
  // Video Extractor state
  videos: [],
  activeVideo: null,
  videoTimestamp: 0,
  // Boss-Key Privacy state
  privacyLocked: false,
  originalTitle: document.title,
};

// Primary DOM References
const galleryGrid = document.getElementById("galleryGrid");
const emptyState = document.getElementById("emptyState");
const searchInput = document.getElementById("searchInput");
const searchClearBtn = document.getElementById("searchClearBtn");
const categoryChips = document.getElementById("categoryChips");
const modelChips = document.getElementById("modelChips");
const ratingChips = document.getElementById("ratingChips");
const clearSimilarityBtn = document.getElementById("clearSimilarityBtn");
const scanTelemetryPill = document.getElementById("scanTelemetryPill");
const sourceFolderBadge = document.getElementById("sourceFolderBadge");
const favCountBadge = document.getElementById("favCountBadge");
const uploadedCountBadge = document.getElementById("uploadedCountBadge");
const dedupCountBadge = document.getElementById("dedupCountBadge");
const dedupToggleBtn = document.getElementById("dedupToggleBtn");
const favoritesToggleBtn = document.getElementById("favoritesToggleBtn");
const uploadedToggleBtn = document.getElementById("uploadedToggleBtn");
const globalPresetSelect = document.getElementById("globalPresetSelect");
const galleryHeading = document.getElementById("galleryHeading");
const shuffleBtn = document.getElementById("shuffleBtn");
const openUploadBtn = document.getElementById("openUploadBtn");
const heroUploadBtn = document.getElementById("heroUploadBtn");
const emptyUploadBtn = document.getElementById("emptyUploadBtn");
const uploadModal = document.getElementById("uploadModal");
const uploadModalBackdrop = document.getElementById("uploadModalBackdrop");
const uploadModalCloseBtn = document.getElementById("uploadModalCloseBtn");
const cancelUploadModalBtn = document.getElementById("cancelUploadModalBtn");
const uploadDropzone = document.getElementById("uploadDropzone");
const browseFilesBtn = document.getElementById("browseFilesBtn");
const uploadStagedSection = document.getElementById("uploadStagedSection");
const uploadStagedCountLabel = document.getElementById("uploadStagedCountLabel");
const uploadPreviewGrid = document.getElementById("uploadPreviewGrid");
const clearUploadQueueBtn = document.getElementById("clearUploadQueueBtn");
const uploadModelInput = document.getElementById("uploadModelInput");
const uploadCategoryInput = document.getElementById("uploadCategoryInput");
const uploadTagsInput = document.getElementById("uploadTagsInput");
const uploadPresetSelect = document.getElementById("uploadPresetSelect");
const uploadAutoEnhanceCheck = document.getElementById("uploadAutoEnhanceCheck");
const uploadAutoOpenCheck = document.getElementById("uploadAutoOpenCheck");
const uploadProgressWrap = document.getElementById("uploadProgressWrap");
const uploadProgressBar = document.getElementById("uploadProgressBar");
const uploadStatusText = document.getElementById("uploadStatusText");
const startUploadBtn = document.getElementById("startUploadBtn");
const openBoardsBtn = document.getElementById("openBoardsBtn");
const boardsCountBadge = document.getElementById("boardsCountBadge");
const boardFilterChips = document.getElementById("boardFilterChips");
const paletteSwatchList = document.getElementById("paletteSwatchList");
const manualFileInput = document.getElementById("manualFileInput");
const boardsModal = document.getElementById("boardsModal");
const boardsModalBackdrop = document.getElementById("boardsModalBackdrop");
const boardsModalCloseBtn = document.getElementById("boardsModalCloseBtn");
const newBoardInput = document.getElementById("newBoardInput");
const createBoardBtn = document.getElementById("createBoardBtn");
const boardsListContainer = document.getElementById("boardsListContainer");
const pinModal = document.getElementById("pinModal");
const pinModalBackdrop = document.getElementById("pinModalBackdrop");
const pinModalCloseBtn = document.getElementById("pinModalCloseBtn");
const pinBoardsListContainer = document.getElementById("pinBoardsListContainer");
const modalAddToBoardBtn = document.getElementById("modalAddToBoardBtn");
const modalCompareLoopBtn = document.getElementById("modalCompareLoopBtn");
const scanScenesBtn = document.getElementById("scanScenesBtn");

// Rotating Left-Side 4K Muse DOM References
const museOrbitContainer = document.getElementById("museOrbitContainer");
const museStageWrap = document.getElementById("museStageWrap");
const museRotator = document.getElementById("museRotator");
const museImgCurrent = document.getElementById("museImgCurrent");
const museImgNext = document.getElementById("museImgNext");
const museCardMeta = document.getElementById("museCardMeta");
const museModelName = document.getElementById("museModelName");
const museCategoryTag = document.getElementById("museCategoryTag");
const museNextBtn = document.getElementById("museNextBtn");
const museToggleSpinBtn = document.getElementById("museToggleSpinBtn");
const museInspectBtn = document.getElementById("museInspectBtn");

// Modal DOM References
const enhancerModal = document.getElementById("enhancerModal");
const modalBackdrop = document.getElementById("modalBackdrop");
const modalCloseBtn = document.getElementById("modalCloseBtn");
const modalTitle = document.getElementById("modalTitle");
const modalFilename = document.getElementById("modalFilename");
const modalFavBtn = document.getElementById("modalFavBtn");
const modalFormatSelect = document.getElementById("modalFormatSelect");
const modalDownloadBtn = document.getElementById("modalDownloadBtn");
const aiProcessingOverlay = document.getElementById("aiProcessingOverlay");

const viewSideBySide = document.getElementById("viewSideBySide");
const viewSlider = document.getElementById("viewSlider");
const viewSingle = document.getElementById("viewSingle");
const viewQuadMatrix = document.getElementById("viewQuadMatrix");
const quadMatrixGrid = document.getElementById("quadMatrixGrid");

const sbsOrigWrap = document.getElementById("sbsOrigWrap");
const sbsEnhWrap = document.getElementById("sbsEnhWrap");
const sbsOrigImg = document.getElementById("sbsOrigImg");
const sbsEnhImg = document.getElementById("sbsEnhImg");
const loupeOrig = document.getElementById("loupeOrig");
const loupeEnh = document.getElementById("loupeEnh");
const origResTag = document.getElementById("origResTag");
const enhResTag = document.getElementById("enhResTag");

const sliderOrigImg = document.getElementById("sliderOrigImg");
const sliderEnhImg = document.getElementById("sliderEnhImg");
const sliderOrigClip = document.getElementById("sliderOrigClip");
const sliderHandle = document.getElementById("sliderHandle");
const splitSliderWrapper = document.getElementById("splitSliderWrapper");
const singleEnhImg = document.getElementById("singleEnhImg");

// Parameter Controls
const paramCropAspect = document.getElementById("paramCropAspect");
const paramUpscaleMode = document.getElementById("paramUpscaleMode");
const paramLutSelect = document.getElementById("paramLutSelect");
const paramSkinMask = document.getElementById("paramSkinMask");
const paramAutoWB = document.getElementById("paramAutoWB");
const paramMonochrome = document.getElementById("paramMonochrome");
const paramNeonPop = document.getElementById("paramNeonPop");
const paramPencilSketch = document.getElementById("paramPencilSketch");
const paramProPencilSketch = document.getElementById("paramProPencilSketch");
const paramTraumatized = document.getElementById("paramTraumatized");
const paramIntensity = document.getElementById("paramIntensity");
const paramFilmGrain = document.getElementById("paramFilmGrain");
const paramVignette = document.getElementById("paramVignette");
const paramBloom = document.getElementById("paramBloom");
const paramEye = document.getElementById("paramEye");
const paramBokeh = document.getElementById("paramBokeh");
const paramSharpen = document.getElementById("paramSharpen");
const paramSkin = document.getElementById("paramSkin");
const paramContrast = document.getElementById("paramContrast");
const paramShadows = document.getElementById("paramShadows");
const paramWarmth = document.getElementById("paramWarmth");
const paramVibrance = document.getElementById("paramVibrance");

const valIntensity = document.getElementById("valIntensity");
const valFilmGrain = document.getElementById("valFilmGrain");
const valVignette = document.getElementById("valVignette");
const valBloom = document.getElementById("valBloom");
const valEye = document.getElementById("valEye");
const valBokeh = document.getElementById("valBokeh");
const valSharpen = document.getElementById("valSharpen");
const valSkin = document.getElementById("valSkin");
const valContrast = document.getElementById("valContrast");
const valShadows = document.getElementById("valShadows");
const valWarmth = document.getElementById("valWarmth");
const valVibrance = document.getElementById("valVibrance");
const presetFilterChips = document.getElementById("presetFilterChips");

// Telemetry & Histogram DOM
const histogramCanvas = document.getElementById("histogramCanvas");
const telOrigRes = document.getElementById("telOrigRes");
const telEnhRes = document.getElementById("telEnhRes");
const telSkinCov = document.getElementById("telSkinCov");
const telSharpness = document.getElementById("telSharpness");
const telTime = document.getElementById("telTime");
const telSize = document.getElementById("telSize");
const telStages = document.getElementById("telStages");

// Metadata Editor DOM
const modalStarBar = document.getElementById("modalStarBar");
const metaModelInput = document.getElementById("metaModelInput");
const metaCategoryInput = document.getElementById("metaCategoryInput");
const metaTagsInput = document.getElementById("metaTagsInput");
const saveMetadataBtn = document.getElementById("saveMetadataBtn");

function saveFavoritesLocal() {
  localStorage.setItem("elitebabes_favs", JSON.stringify(Array.from(state.favorites)));
  favCountBadge.textContent = state.favorites.size;
}

/**
 * Fisher-Yates Dynamic Shuffle Algorithm
 * Ensures that on every page refresh or reload, all images shuffle
 * and their positions change dynamically across the Pinterest masonry grid.
 */
function shuffleArray(array) {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function hexToRgb(hex) {
  if (!hex) return { r: 0, g: 0, b: 0 };
  const clean = hex.replace("#", "");
  const num = parseInt(clean, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function matchesColorCategory(hex, category) {
  if (!hex || !category) return true;
  const { r, g, b } = hexToRgb(hex);
  const luma = 0.299 * r + 0.587 * g + 0.114 * b;
  if (category === "dark") return luma < 60;
  if (category === "ivory") return luma > 180;
  if (category === "gold") return r > 135 && g > 85 && b < 115 && r >= g;
  if (category === "rose") return r > 90 && r > g * 1.15;
  if (category === "blue") return b > r && b >= g;
  if (category === "warm") return r > g && g >= b && luma >= 50 && luma <= 180;
  return false;
}

async function loadBoards() {
  try {
    const res = await fetch("/api/boards");
    const data = await res.json();
    state.boards = data.boards || [];
    if (boardsCountBadge) boardsCountBadge.textContent = state.boards.length;
    renderBoardChips();
  } catch (err) {
    console.error("Failed to load boards:", err);
  }
}

function renderBoardChips() {
  if (!boardFilterChips) return;
  boardFilterChips.innerHTML = "";
  const allBtn = document.createElement("button");
  allBtn.className = `chip ${state.activeBoardId === "" ? "active" : ""}`;
  allBtn.textContent = "All Media";
  allBtn.onclick = () => {
    state.activeBoardId = "";
    scanAndLoadImages();
  };
  boardFilterChips.appendChild(allBtn);

  state.boards.forEach((b) => {
    const btn = document.createElement("button");
    btn.className = `chip ${state.activeBoardId === b.id ? "active" : ""}`;
    btn.textContent = `📌 ${b.name} (${b.item_count || 0})`;
    btn.onclick = async () => {
      if (state.activeBoardId === b.id) {
        state.activeBoardId = "";
      } else {
        state.activeBoardId = b.id;
        if (!state.boardItems[b.id]) {
          const res = await fetch(`/api/boards/${b.id}/items`);
          const d = await res.json();
          state.boardItems[b.id] = d.items || [];
        }
      }
      scanAndLoadImages();
    };
    boardFilterChips.appendChild(btn);
  });
}

function triggerDynamicShuffle() {
  if (state.filteredImages.length <= 1) return;
  galleryGrid.classList.add("shuffling");
  setTimeout(() => {
    state.filteredImages = shuffleArray(state.filteredImages);
    renderGallery();
    galleryGrid.classList.remove("shuffling");
    scanTelemetryPill.textContent = `🔀 Dynamically Shuffled ${state.filteredImages.length} images`;
  }, 120);
}

/**
 * Real-time Folder Scan & Query API Call
 */
async function scanAndLoadImages() {
  const t0 = performance.now();
  const params = new URLSearchParams();
  if (state.activeQuery) params.set("q", state.activeQuery);
  if (state.activeCategory) params.set("category", state.activeCategory);
  if (state.activeModel) params.set("model", state.activeModel);
  if (state.minRating > 0) params.set("min_rating", String(state.minRating));
  if (state.deduplicate) params.set("deduplicate", "1");
  if (state.onlyUploaded) params.set("uploaded", "1");
  if (state.similarTo) params.set("similar_to", state.similarTo);
  params.set("_t", String(Date.now()));

  const res = await fetch(`/api/images?${params.toString()}`);
  const data = await res.json();
  const elapsed = Math.round(performance.now() - t0);

  sourceFolderBadge.textContent = `Source: ${data.source_folder}${data.recursive ? " (Recursive)" : ""}`;
  scanTelemetryPill.textContent = `⚡ Scanned ${data.total_in_folder} local images (${elapsed}ms)`;
  if (dedupCountBadge) dedupCountBadge.textContent = data.dup_hidden_count ?? 0;
  if (uploadedCountBadge) uploadedCountBadge.textContent = data.uploaded_count ?? 0;
  if (clearSimilarityBtn) clearSimilarityBtn.hidden = !state.similarTo;

  state.categories = data.categories || [];
  state.models = data.models || [];
  state.presetConfigs = data.preset_configs || {};
  state.luts = data.luts || [];

  (data.images || []).forEach((img) => {
    if (img.favorite) state.favorites.add(img.id);
  });
  saveFavoritesLocal();

  let imgs = data.images || [];
  if (state.onlyFavorites) {
    imgs = imgs.filter((item) => state.favorites.has(item.id) || item.favorite);
  }
  if (state.onlyUploaded) {
    imgs = imgs.filter((item) => item.is_uploaded);
  }
  if (state.activeBoardId) {
    const bItems = state.boardItems[state.activeBoardId] || [];
    imgs = imgs.filter((item) => bItems.includes(item.id));
  }
  if (state.activeColorFilter) {
    imgs = imgs.filter((item) =>
      item.palette && item.palette.some((c) => matchesColorCategory(c, state.activeColorFilter))
    );
  }

  // DYNAMIC REFRESH SHUFFLE: Shuffle image positions whenever the website loads/refreshes,
  // while keeping newly uploaded images pinned at the top!
  if (state.onlyUploaded) {
    imgs.sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
  } else if (!state.similarTo) {
    imgs = shuffleArray(imgs);
  }

  if (state.lastUploadedIds.length > 0) {
    const recentSet = new Set(state.lastUploadedIds);
    const pinned = [];
    const rest = [];
    imgs.forEach((it) => {
      if (recentSet.has(it.id)) pinned.push(it);
      else rest.push(it);
    });
    imgs = [...pinned, ...rest];
  }
  state.filteredImages = imgs;

  renderPresetSelectors();
  renderLutOptions();
  renderFilterChips();
  renderBoardChips();
  renderGallery();
}

function renderPresetSelectors() {
  const keys = Object.keys(state.presetConfigs);
  if (keys.length === 0) return;

  const exportPresetSelect = document.getElementById("exportPresetSelect");
  const videoClipPresetSelect = document.getElementById("videoClipPresetSelect");
  [globalPresetSelect, exportPresetSelect, uploadPresetSelect, videoClipPresetSelect].forEach((sel) => {
    if (!sel) return;
    sel.innerHTML = "";
    keys.forEach((k) => {
      const cfg = state.presetConfigs[k];
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = `${cfg.icon || (cfg.builtin ? "⚡" : "★")} ${cfg.name}`;
      sel.appendChild(opt);
    });
    if (state.presetConfigs[state.currentPreset]) {
      sel.value = state.currentPreset;
    }
  });

  // Render quick-filter preset chips row
  if (presetFilterChips) {
    presetFilterChips.innerHTML = "";
    keys.forEach((k) => {
      const cfg = state.presetConfigs[k];
      const btn = document.createElement("button");
      btn.className = `chip ${state.currentPreset === k ? "active" : ""}`;
      btn.dataset.preset = k;
      btn.innerHTML = `<span>${cfg.icon || "⚡"}</span> ${cfg.name}`;
      btn.addEventListener("click", () => {
        state.currentPreset = k;
        if (globalPresetSelect) globalPresetSelect.value = k;
        document.querySelectorAll("#presetFilterChips .chip").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        renderGallery();
      });
      presetFilterChips.appendChild(btn);
    });
  }

  const container = document.getElementById("modalPresetCards");
  if (!container) return;
  container.innerHTML = "";
  keys.forEach((k) => {
    const cfg = state.presetConfigs[k];
    const card = document.createElement("div");
    card.className = `preset-card ${state.currentPreset === k ? "active" : ""}`;
    card.dataset.preset = k;
    card.innerHTML = `
      <div class="preset-card-top">
        <span class="preset-card-title">${cfg.icon || (cfg.builtin ? "🔥" : "★")} ${cfg.name}</span>
        ${cfg.category ? `<span class="preset-badge-tag">${cfg.category}</span>` : ""}
        ${
          !cfg.builtin
            ? `<button class="preset-del-btn" data-del-preset="${k}" title="Delete Custom Preset">&times;</button>`
            : ""
        }
      </div>
      <span class="preset-card-desc">${cfg.desc || "4K Super-Resolution & Optical Grading"}</span>
    `;
    card.addEventListener("click", (e) => {
      const delBtn = e.target.closest("[data-del-preset]");
      if (delBtn) {
        e.stopPropagation();
        deleteCustomPreset(delBtn.dataset.delPreset);
        return;
      }
      state.currentPreset = k;
      if (globalPresetSelect) globalPresetSelect.value = k;
      syncSlidersToPreset(k);
      triggerModalEnhancement(false);
    });
    container.appendChild(card);
  });
}

function renderLutOptions() {
  if (!paramLutSelect) return;
  const currentVal = paramLutSelect.value || "none";
  paramLutSelect.innerHTML = "";
  state.luts.forEach((lut) => {
    const opt = document.createElement("option");
    opt.value = lut.id;
    opt.textContent = lut.name;
    paramLutSelect.appendChild(opt);
  });
  if ([...paramLutSelect.options].some((o) => o.value === currentVal)) {
    paramLutSelect.value = currentVal;
  }
}

function renderFilterChips() {
  categoryChips.innerHTML = "";
  const allCatBtn = document.createElement("button");
  allCatBtn.className = `chip ${state.activeCategory === "" ? "active" : ""}`;
  allCatBtn.textContent = "All Galleries";
  allCatBtn.onclick = () => {
    state.activeCategory = "";
    scanAndLoadImages();
  };
  categoryChips.appendChild(allCatBtn);

  state.categories.forEach((cat) => {
    const btn = document.createElement("button");
    btn.className = `chip ${state.activeCategory === cat ? "active" : ""}`;
    btn.textContent = cat;
    btn.onclick = () => {
      state.activeCategory = state.activeCategory === cat ? "" : cat;
      scanAndLoadImages();
    };
    categoryChips.appendChild(btn);
  });

  modelChips.innerHTML = "";
  const allModBtn = document.createElement("button");
  allModBtn.className = `chip ${state.activeModel === "" ? "active" : ""}`;
  allModBtn.textContent = "All Babes";
  allModBtn.onclick = () => {
    state.activeModel = "";
    scanAndLoadImages();
  };
  modelChips.appendChild(allModBtn);

  state.models.forEach((mod) => {
    const btn = document.createElement("button");
    btn.className = `chip ${state.activeModel === mod ? "active" : ""}`;
    btn.textContent = `🔥 ${mod}`;
    btn.onclick = () => {
      state.activeModel = state.activeModel === mod ? "" : mod;
      scanAndLoadImages();
    };
    modelChips.appendChild(btn);
  });
}

function renderGallery() {
  favCountBadge.textContent = state.favorites.size;

  if (state.similarTo) {
    galleryHeading.textContent = `🔍 Visually Similar Shots (${state.filteredImages.length} Matches)`;
  } else if (state.activeQuery) {
    galleryHeading.textContent = `AI Search Results for "${state.activeQuery}" (${state.filteredImages.length})`;
  } else if (state.onlyUploaded) {
    galleryHeading.textContent = `📥 Your Uploaded Pictures (${state.filteredImages.length})`;
  } else if (state.onlyFavorites) {
    galleryHeading.textContent = `Your Favorite Babes (${state.filteredImages.length})`;
  } else if (state.activeModel || state.activeCategory || state.minRating > 0 || state.deduplicate) {
    const parts = [
      state.activeModel,
      state.activeCategory,
      state.minRating > 0 ? `★ ${state.minRating}+` : "",
      state.deduplicate ? "Sharpest Burst Frames" : "",
    ]
      .filter(Boolean)
      .join(" • ");
    galleryHeading.textContent = `${parts} (${state.filteredImages.length})`;
  } else {
    galleryHeading.textContent = `All Exclusive Galleries (${state.filteredImages.length})`;
  }

  if (state.filteredImages.length === 0) {
    galleryGrid.innerHTML = "";
    emptyState.hidden = false;
    return;
  }

  emptyState.hidden = true;
  galleryGrid.innerHTML = "";

  state.filteredImages.forEach((item, index) => {
    const isFav = state.favorites.has(item.id) || item.favorite;
    const isEnhanced = state.enhancedSet.has(item.id);
    const card = document.createElement("article");
    card.className = "gallery-card";

    const imgSrc = isEnhanced
      ? `/api/image/enhanced/${item.id}?preset=${encodeURIComponent(state.currentPreset)}`
      : `/api/resize/${item.id}?mode=exact_uploaded`;

    const starsHtml =
      item.rating > 0
        ? `<span class="card-stars">${"★".repeat(item.rating)}${"☆".repeat(5 - item.rating)}</span>`
        : "";

    let extraBadge = "";
    if (item.is_uploaded) {
      extraBadge += `<span class="badge-uploaded" title="User Uploaded Picture">⬆ UPLOADED</span>`;
    }
    if (item.similarity_pct != null) {
      extraBadge += `<span class="badge-sim">${item.similarity_pct}% Match</span>`;
    } else if (item.dup_count > 1) {
      extraBadge += `<span class="badge-burst" title="dHash Burst Group (${item.dup_count} frames)">${
        item.is_sharpest_in_group ? `⚡ Best of ${item.dup_count}` : `⧉ Burst (${item.dup_count})`
      }</span>`;
    }

    const modelInitial = (item.model || "P").charAt(0).toUpperCase();

    card.innerHTML = `
      <div class="card-thumb-wrap" data-index="${index}">
        <img
          class="card-thumb-img"
          id="card-img-${item.id}"
          src="${imgSrc}"
          alt="${item.title}"
          loading="lazy"
          decoding="async"
        />
        <div class="card-top-badges">
          <div class="pin-top-left-badges">
            <span class="${isEnhanced ? "badge-enhanced-live" : "badge-4k"}" id="card-badge-${item.id}">
              ${
                item.is_animated
                  ? "🎞️ 4K LOOP"
                  : isEnhanced
                  ? "⚡ 4K+ AI"
                  : `4K • ${item.enhanced_width}×${item.enhanced_height}`
              }
            </span>
            ${extraBadge}
          </div>
          <div class="pin-top-right-actions">
            <button class="pin-save-pill" data-pin-id="${item.id}" title="Save to Moodboard">
              Save
            </button>
            <button class="card-fav-btn ${isFav ? "is-fav" : ""}" data-fav-id="${item.id}" title="Favorite">
              ♥
            </button>
          </div>
        </div>
        <div class="card-hover-cta">
          <div class="hover-action-row">
            <button class="btn-card-enhance" data-enhance-index="${index}">
              ⚡ 4K Studio
            </button>
            <button class="btn-card-sbs" data-inline-id="${item.id}" title="Enhance card thumbnail in-place">
              ✨ Quick 4K
            </button>
            <button class="btn-card-sbs" data-sim-id="${item.id}" title="Find visually similar images">
              🔍
            </button>
          </div>
        </div>
      </div>
      <div class="card-info">
        <div class="card-title-row">
          <span class="card-title" title="${item.title}">${item.title}</span>
          <button class="pin-more-btn" data-more-index="${index}" title="Open in 4K Studio">•••</button>
        </div>
        <div class="card-meta-row">
          <span class="pin-creator-row">
            <span class="pin-avatar">${modelInitial}</span>
            <span class="card-model-pill">${item.model}</span>
            <span class="pin-cat-text">${item.category}</span>
            ${starsHtml}
          </span>
          <div class="card-palette-row">
            ${(item.palette || [])
              .slice(0, 4)
              .map((hex) => `<span class="mini-color-dot" style="background:${hex};" data-filter-hex="${hex}" title="Dominant Color ${hex}"></span>`)
              .join("")}
          </div>
        </div>
      </div>
    `;

    const thumbWrap = card.querySelector(".card-thumb-wrap");
    thumbWrap.addEventListener("click", (e) => {
      if (
        e.target.closest("[data-fav-id]") ||
        e.target.closest("[data-inline-id]") ||
        e.target.closest("[data-pin-id]") ||
        e.target.closest("[data-sim-id]")
      )
        return;
      openEnhancerModal(index);
    });

    const favBtn = card.querySelector("[data-fav-id]");
    favBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFavorite(item.id);
    });

    const pinBtns = card.querySelectorAll("[data-pin-id]");
    pinBtns.forEach((pinBtn) => {
      pinBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        openPinModal(item.id);
      });
    });

    const moreBtn = card.querySelector("[data-more-index]");
    if (moreBtn) {
      moreBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        openEnhancerModal(index);
      });
    }

    const inlineBtn = card.querySelector("[data-inline-id]");
    inlineBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      await enhanceCardInline(item, inlineBtn);
    });

    const simBtn = card.querySelector("[data-sim-id]");
    simBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      findSimilarImages(item.id);
    });

    card.querySelectorAll("[data-filter-hex]").forEach((dot) => {
      dot.addEventListener("click", (e) => {
        e.stopPropagation();
        const hex = dot.dataset.filterHex;
        const matchedCat = ["dark", "ivory", "gold", "rose", "blue", "warm"].find((cat) =>
          matchesColorCategory(hex, cat)
        );
        if (matchedCat) {
          state.activeColorFilter = state.activeColorFilter === matchedCat ? "" : matchedCat;
          document.querySelectorAll(".swatch-btn").forEach((s) => {
            s.classList.toggle("active", s.dataset.color === state.activeColorFilter);
          });
          scanAndLoadImages();
        }
      });
    });

    galleryGrid.appendChild(card);
  });
}

function findSimilarImages(imgId) {
  state.similarTo = imgId;
  if (!enhancerModal.hidden) closeEnhancerModal();
  scanAndLoadImages();
}

async function enhanceCardInline(item, btnEl) {
  const origText = btnEl.textContent;
  btnEl.textContent = "⏳ 4K...";
  btnEl.disabled = true;

  try {
    const res = await fetch(
      `/api/enhance/${item.id}?preset=${encodeURIComponent(state.currentPreset)}`
    );
    const data = await res.json();
    if (data.status === "enhanced") {
      state.enhancedSet.add(item.id);
      const imgEl = document.getElementById(`card-img-${item.id}`);
      const badgeEl = document.getElementById(`card-badge-${item.id}`);
      if (imgEl) imgEl.src = data.enhanced_image_url;
      if (badgeEl) {
        badgeEl.className = "badge-enhanced-live";
        badgeEl.textContent = `⚡ 4K ENHANCED (${data.report.enhanced_resolution})`;
      }
      btnEl.textContent = "✓ 4K Live";
    }
  } catch (err) {
    console.error("Inline enhancement error:", err);
    btnEl.textContent = origText;
  } finally {
    btnEl.disabled = false;
  }
}

async function toggleFavorite(imgId) {
  const isNowFav = !state.favorites.has(imgId);
  if (isNowFav) {
    state.favorites.add(imgId);
  } else {
    state.favorites.delete(imgId);
  }
  saveFavoritesLocal();

  try {
    await fetch(`/api/metadata/${imgId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ favorite: isNowFav }),
    });
  } catch (e) {
    console.warn("SQLite favorite sync warning:", e);
  }

  renderGallery();
  if (state.currentModalIndex >= 0) {
    const activeItem = state.filteredImages[state.currentModalIndex];
    if (activeItem && activeItem.id === imgId) {
      activeItem.favorite = isNowFav;
      modalFavBtn.classList.toggle("is-fav", isNowFav);
    }
  }
}

/**
 * Open AI Enhancer Modal & Instantly Run 4K+ Enhancement Engine
 */
async function openEnhancerModal(index) {
  if (index < 0 || index >= state.filteredImages.length) return;
  state.currentModalIndex = index;
  const item = state.filteredImages[index];

  enhancerModal.hidden = false;
  document.body.style.overflow = "hidden";

  resetZoomAndPan();
  populateModalMetadata(item);

  sbsOrigImg.src = item.original_url;
  sliderOrigImg.src = item.original_url;
  origResTag.textContent = `${item.width}×${item.height}`;
  telOrigRes.textContent = `${item.width}×${item.height} (${item.size_mb} MB)`;
  if (telSharpness) telSharpness.textContent = `${item.sharpness_score ?? "—"} (Laplacian)`;

  if (modalCompareLoopBtn) {
    modalCompareLoopBtn.href = `/api/image/compare-loop/${item.id}?preset=${encodeURIComponent(state.currentPreset)}&download=1`;
  }
  if (modalAddToBoardBtn) {
    modalAddToBoardBtn.onclick = () => openPinModal(item.id);
  }

  syncSlidersToPreset(state.currentPreset);
  await triggerModalEnhancement(false);

  if (state.currentViewMode === "quad-matrix") {
    renderQuadMatrix(item);
  }

  // Pre-fetch next image's 4K enhancement in background
  const nextIdx = (index + 1) % state.filteredImages.length;
  const nextItem = state.filteredImages[nextIdx];
  if (nextItem && nextItem.id !== item.id) {
    fetch(`/api/enhance/${nextItem.id}?preset=${encodeURIComponent(state.currentPreset)}`).catch(
      () => {}
    );
  }
}

function populateModalMetadata(item) {
  modalTitle.textContent = item.title;
  modalFilename.textContent = item.filename;
  modalFavBtn.classList.toggle("is-fav", state.favorites.has(item.id) || item.favorite);

  metaModelInput.value = item.model || "";
  metaCategoryInput.value = item.category || "";
  metaTagsInput.value = (item.tags || []).join(", ");
  renderModalStars(item.rating || 0);
}

function renderModalStars(rating) {
  modalStarBar.querySelectorAll(".star-btn").forEach((btn) => {
    const s = Number(btn.dataset.star);
    btn.classList.toggle("lit", s <= rating);
  });
  modalStarBar.dataset.currentRating = String(rating);
}

function syncSlidersToPreset(presetKey) {
  const cfg =
    state.presetConfigs[presetKey] ||
    state.presetConfigs.ultra_hot_4k || {
      detail_sharpen: 1.55,
      skin_smooth: 0.45,
      micro_contrast: 1.35,
      depth_shadows: 1.25,
      warmth: 1.12,
      vibrance: 1.22,
      eye_enhance: 0.45,
      bokeh_blur: 0.0,
      auto_exposure_wb: false,
      crop_aspect: "original",
      skin_mask_aware: true,
      upscale_mode: "lanczos_edge",
      lut_name: "none",
    };

  paramEye.value = cfg.eye_enhance ?? 0.45;
  paramBokeh.value = cfg.bokeh_blur ?? 0.0;
  paramSharpen.value = cfg.detail_sharpen ?? 1.55;
  paramSkin.value = cfg.skin_smooth ?? 0.45;
  paramContrast.value = cfg.micro_contrast ?? 1.35;
  paramShadows.value = cfg.depth_shadows ?? 1.25;
  paramWarmth.value = cfg.warmth ?? 1.12;
  paramVibrance.value = cfg.vibrance ?? 1.22;
  paramSkinMask.checked = cfg.skin_mask_aware !== false;
  paramAutoWB.checked = Boolean(cfg.auto_exposure_wb);
  if (paramMonochrome) paramMonochrome.checked = Boolean(cfg.is_monochrome);
  if (paramNeonPop) paramNeonPop.checked = Boolean(cfg.neon_pop);
  if (paramPencilSketch) paramPencilSketch.checked = Boolean(cfg.pencil_sketch);
  if (paramProPencilSketch) paramProPencilSketch.checked = Boolean(cfg.pro_pencil_sketch);
  if (paramTraumatized) paramTraumatized.checked = Boolean(cfg.traumatized_mode);
  if (paramIntensity) paramIntensity.value = cfg.preset_intensity ?? 1.0;
  if (paramFilmGrain) paramFilmGrain.value = cfg.film_grain ?? 0.0;
  if (paramVignette) paramVignette.value = cfg.vignette ?? 0.0;
  if (paramBloom) paramBloom.value = cfg.highlight_bloom ?? 0.15;
  paramCropAspect.value = cfg.crop_aspect || "original";
  paramUpscaleMode.value = cfg.upscale_mode || "lanczos_edge";
  if (cfg.lut_name && [...paramLutSelect.options].some((o) => o.value === cfg.lut_name)) {
    paramLutSelect.value = cfg.lut_name;
  } else {
    paramLutSelect.value = "none";
  }

  updateSliderLabels();
  document.querySelectorAll("#modalPresetCards .preset-card").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.preset === presetKey);
  });
}

function updateSliderLabels() {
  valEye.textContent = Number(paramEye.value).toFixed(2);
  valBokeh.textContent = Number(paramBokeh.value).toFixed(2);
  valSharpen.textContent = `${Number(paramSharpen.value).toFixed(2)}x`;
  valSkin.textContent = Number(paramSkin.value).toFixed(2);
  valContrast.textContent = `${Number(paramContrast.value).toFixed(2)}x`;
  valShadows.textContent = `${Number(paramShadows.value).toFixed(2)}x`;
  valWarmth.textContent = `${Number(paramWarmth.value).toFixed(2)}x`;
  valVibrance.textContent = `${Number(paramVibrance.value).toFixed(2)}x`;
  if (valIntensity && paramIntensity) valIntensity.textContent = `${Math.round(Number(paramIntensity.value) * 100)}%`;
  if (valFilmGrain && paramFilmGrain) valFilmGrain.textContent = Number(paramFilmGrain.value).toFixed(2);
  if (valVignette && paramVignette) valVignette.textContent = Number(paramVignette.value).toFixed(2);
  if (valBloom && paramBloom) valBloom.textContent = Number(paramBloom.value).toFixed(2);
}

async function triggerModalEnhancement(useCustomSliders = false) {
  const item = state.filteredImages[state.currentModalIndex];
  if (!item) return;

  aiProcessingOverlay.hidden = false;

  const qs = new URLSearchParams({
    preset: state.currentPreset,
    format: state.currentFormat,
  });

  if (useCustomSliders) {
    qs.set("eye_enhance", paramEye.value);
    qs.set("bokeh_blur", paramBokeh.value);
    qs.set("detail_sharpen", paramSharpen.value);
    qs.set("skin_smooth", paramSkin.value);
    qs.set("micro_contrast", paramContrast.value);
    qs.set("depth_shadows", paramShadows.value);
    qs.set("warmth", paramWarmth.value);
    qs.set("vibrance", paramVibrance.value);
    qs.set("skin_mask_aware", paramSkinMask.checked ? "1" : "0");
    qs.set("auto_exposure_wb", paramAutoWB.checked ? "1" : "0");
    if (paramMonochrome) qs.set("is_monochrome", paramMonochrome.checked ? "1" : "0");
    if (paramNeonPop) qs.set("neon_pop", paramNeonPop.checked ? "1" : "0");
    if (paramPencilSketch) qs.set("pencil_sketch", paramPencilSketch.checked ? "1" : "0");
    if (paramProPencilSketch) qs.set("pro_pencil_sketch", paramProPencilSketch.checked ? "1" : "0");
    if (paramTraumatized) qs.set("traumatized_mode", paramTraumatized.checked ? "1" : "0");
    if (paramIntensity) qs.set("preset_intensity", paramIntensity.value);
    if (paramFilmGrain) qs.set("film_grain", paramFilmGrain.value);
    if (paramVignette) qs.set("vignette", paramVignette.value);
    if (paramBloom) qs.set("highlight_bloom", paramBloom.value);
    qs.set("crop_aspect", paramCropAspect.value);
    qs.set("upscale_mode", paramUpscaleMode.value);
    qs.set("lut_name", paramLutSelect.value);
  }

  try {
    const res = await fetch(`/api/enhance/${item.id}?${qs.toString()}`);
    const data = await res.json();

    if (data.status === "enhanced") {
      state.enhancedSet.add(item.id);
      const enhUrl = data.enhanced_image_url;

      await new Promise((resolve) => {
        const loader = new Image();
        loader.onload = resolve;
        loader.onerror = resolve;
        loader.src = enhUrl;
      });

      sbsEnhImg.src = enhUrl;
      sliderEnhImg.src = enhUrl;
      singleEnhImg.src = enhUrl;

      enhResTag.textContent = data.report.enhanced_resolution;
      telEnhRes.textContent = `${data.report.enhanced_resolution} (4K+ AI)`;
      telSkinCov.textContent = `${data.report.skin_coverage_pct ?? 0}% (YCrCb Protected)`;
      telTime.textContent = `${data.report.elapsed_ms} ms ${
        data.report.cached ? "(Instant Cache)" : "(Live Compute)"
      }`;
      telSize.textContent = `${data.report.file_size_mb} MB (${state.currentFormat.toUpperCase()})`;

      modalDownloadBtn.href = data.download_url;

      telStages.innerHTML = (data.report.pipeline_stages || [])
        .map((st) => `<span class="pipeline-tag">✓ ${st}</span>`)
        .join("");

      state.lastHistograms = data.report.histograms || null;
      drawHistogramCanvas();

      const cardImg = document.getElementById(`card-img-${item.id}`);
      const cardBadge = document.getElementById(`card-badge-${item.id}`);
      if (cardImg) cardImg.src = enhUrl;
      if (cardBadge) {
        badgeClassUpdate(cardBadge, item);
      }
    }
  } catch (err) {
    console.error("Enhancement failed:", err);
  } finally {
    aiProcessingOverlay.hidden = true;
  }
}

function badgeClassUpdate(cardBadge, item) {
  if (item.is_animated) return;
  const cfg = state.presetConfigs[state.currentPreset] || {};
  cardBadge.className = "badge-enhanced-live";
  cardBadge.textContent = `${cfg.icon || "⚡"} 4K+ ${cfg.name || "AI ENHANCED"}`;
}

/**
 * Dynamic Multi-Preset Matrix View (4-Way, 6-Way or All 10 Presets)
 */
function renderQuadMatrix(item) {
  if (!quadMatrixGrid || !item) return;

  const mset = state.matrixSet || "flagship";
  let targetKeys = [];
  if (mset === "flagship") {
    targetKeys = ["ultra_hot_4k", "skin_perfection", "razor_sharp_hdr", "cinema_noir"];
  } else if (mset === "creative") {
    targetKeys = ["traumatized", "vintage_bw", "retro", "pro_realistic_pencil"];
  } else if (mset === "six") {
    targetKeys = [
      "ultra_hot_4k",
      "traumatized",
      "vintage_bw",
      "retro",
      "pro_realistic_pencil",
      "pencil_sketch_master",
    ];
  } else {
    targetKeys = Object.keys(state.presetConfigs);
  }

  quadMatrixGrid.className = `quad-grid ${mset === "six" ? "six-grid" : mset === "all" ? "all-grid" : ""}`;
  quadMatrixGrid.innerHTML = "";

  targetKeys.forEach((pKey) => {
    const cfg = state.presetConfigs[pKey] || {};
    const pLabel = `${cfg.icon || "⚡"} ${cfg.name || pKey}`;
    const cell = document.createElement("div");
    cell.className = `quad-cell ${state.currentPreset === pKey ? "active" : ""}`;
    const url = `/api/image/enhanced/${item.id}?preset=${encodeURIComponent(pKey)}`;
    cell.innerHTML = `
      <div class="quad-cell-header">
        <span>${pLabel}</span>
        <span class="res-tag gold">Click to Apply</span>
      </div>
      <div class="quad-cell-img-wrap">
        <img src="${url}" alt="${pLabel}" loading="lazy" decoding="async" />
      </div>
    `;
    cell.addEventListener("click", () => {
      state.currentPreset = pKey;
      if (globalPresetSelect) globalPresetSelect.value = pKey;
      syncSlidersToPreset(pKey);
      switchViewMode("side-by-side");
      triggerModalEnhancement(false);
    });
    quadMatrixGrid.appendChild(cell);
  });
}

/**
 * Render Live RGB / Luminance Comparison Histogram on Canvas
 */
function drawHistogramCanvas() {
  if (!histogramCanvas) return;
  const ctx = histogramCanvas.getContext("2d");
  const w = histogramCanvas.width;
  const h = histogramCanvas.height;
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.lineWidth = 1;
  for (let i = 1; i < 4; i++) {
    ctx.beginPath();
    ctx.moveTo(0, (h * i) / 4);
    ctx.lineTo(w, (h * i) / 4);
    ctx.stroke();
  }

  if (!state.lastHistograms || !state.lastHistograms.enhanced) return;
  const orig = state.lastHistograms.original || {};
  const enh = state.lastHistograms.enhanced || {};

  const drawCurve = (arr, strokeColor, fillColor) => {
    if (!arr || arr.length === 0) return;
    ctx.beginPath();
    ctx.moveTo(0, h);
    for (let i = 0; i < arr.length; i++) {
      const x = (i / (arr.length - 1)) * w;
      const y = h - Math.min(1, arr[i]) * (h - 8);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    if (fillColor) {
      ctx.fillStyle = fillColor;
      ctx.fill();
    }
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.6;
    ctx.stroke();
  };

  if (state.histMode === "luma") {
    drawCurve(orig.luma, "rgba(160, 160, 190, 0.75)", "rgba(160, 160, 190, 0.18)");
    drawCurve(enh.luma, "#ffd166", "rgba(245, 176, 65, 0.28)");
  } else {
    drawCurve(enh.b, "rgba(59, 130, 246, 0.9)", "rgba(59, 130, 246, 0.16)");
    drawCurve(enh.g, "rgba(16, 185, 129, 0.9)", "rgba(16, 185, 129, 0.16)");
    drawCurve(enh.r, "rgba(255, 46, 108, 0.9)", "rgba(255, 46, 108, 0.16)");
  }
}

/**
 * Synchronized Pan & Zoom + Dual 3x Inspection Loupe
 */
function applyZoomTransform() {
  const transformStr =
    state.zoomLevel === 1
      ? "translate(0px, 0px) scale(1)"
      : `translate(${state.panX}px, ${state.panY}px) scale(${state.zoomLevel})`;

  [sbsOrigImg, sbsEnhImg, singleEnhImg].forEach((img) => {
    if (img) img.style.transform = transformStr;
  });

  document.querySelectorAll(".zoom-toolbar .zoom-btn[data-zoom]").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.zoom) === state.zoomLevel);
  });
}

function resetZoomAndPan() {
  state.zoomLevel = 1;
  state.panX = 0;
  state.panY = 0;
  applyZoomTransform();
}

function initSyncZoomAndLoupe() {
  document.querySelectorAll(".zoom-toolbar .zoom-btn[data-zoom]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.zoomLevel = Number(btn.dataset.zoom);
      if (state.zoomLevel === 1) {
        state.panX = 0;
        state.panY = 0;
      }
      applyZoomTransform();
    });
  });

  document.getElementById("zoomResetBtn").addEventListener("click", resetZoomAndPan);

  const loupeToggleBtn = document.getElementById("loupeToggleBtn");
  loupeToggleBtn.addEventListener("click", () => {
    state.loupeEnabled = !state.loupeEnabled;
    loupeToggleBtn.classList.toggle("active", state.loupeEnabled);
    loupeToggleBtn.textContent = `🔬 3× Loupe: ${state.loupeEnabled ? "ON" : "OFF"}`;
    if (!state.loupeEnabled) {
      loupeOrig.hidden = true;
      loupeEnh.hidden = true;
    }
  });

  // Wheel zoom disabled by default to guarantee Exact 1:1 Uploaded Framing (no accidental zoom-in/zoom-out)
  let isPanning = false;
  let startX = 0;
  let startY = 0;

  const updateDualLoupes = (e, sourceWrap, sourceImg) => {
    if (!state.loupeEnabled || state.currentViewMode !== "side-by-side") {
      loupeOrig.hidden = true;
      loupeEnh.hidden = true;
      return;
    }
    const imgRect = sourceImg.getBoundingClientRect();
    if (
      e.clientX < imgRect.left ||
      e.clientX > imgRect.right ||
      e.clientY < imgRect.top ||
      e.clientY > imgRect.bottom
    ) {
      loupeOrig.hidden = true;
      loupeEnh.hidden = true;
      return;
    }

    const relX = (e.clientX - imgRect.left) / Math.max(1, imgRect.width);
    const relY = (e.clientY - imgRect.top) / Math.max(1, imgRect.height);

    const posPane = (loupeEl, targetImg, targetWrap) => {
      const tImgRect = targetImg.getBoundingClientRect();
      const tWrapRect = targetWrap.getBoundingClientRect();
      const lx = tImgRect.left - tWrapRect.left + relX * tImgRect.width;
      const ly = tImgRect.top - tWrapRect.top + relY * tImgRect.height;

      const zoomFactor = 3.2;
      const bgW = tImgRect.width * zoomFactor;
      const bgH = tImgRect.height * zoomFactor;
      const bgX = -(relX * bgW - 87.5);
      const bgY = -(relY * bgH - 87.5);

      loupeEl.hidden = false;
      loupeEl.style.left = `${lx}px`;
      loupeEl.style.top = `${ly}px`;
      loupeEl.style.backgroundImage = `url("${targetImg.src}")`;
      loupeEl.style.backgroundSize = `${bgW}px ${bgH}px`;
      loupeEl.style.backgroundPosition = `${bgX}px ${bgY}px`;
    };

    posPane(loupeOrig, sbsOrigImg, sbsOrigWrap);
    posPane(loupeEnh, sbsEnhImg, sbsEnhWrap);
  };

  [
    [sbsOrigWrap, sbsOrigImg],
    [sbsEnhWrap, sbsEnhImg],
  ].forEach(([wrapEl, imgEl]) => {
    wrapEl.addEventListener("mousedown", (e) => {
      if (state.zoomLevel <= 1) return;
      isPanning = true;
      startX = e.clientX - state.panX;
      startY = e.clientY - state.panY;
    });

    wrapEl.addEventListener("mousemove", (e) => {
      updateDualLoupes(e, wrapEl, imgEl);
      if (!isPanning) return;
      state.panX = e.clientX - startX;
      state.panY = e.clientY - startY;
      applyZoomTransform();
    });

    wrapEl.addEventListener("mouseleave", () => {
      loupeOrig.hidden = true;
      loupeEnh.hidden = true;
    });
  });

  window.addEventListener("mouseup", () => {
    isPanning = false;
  });
}

function closeEnhancerModal() {
  stopSlideshow();
  enhancerModal.hidden = true;
  document.body.style.overflow = "";
  state.currentModalIndex = -1;
  // Release decoded 4K RGBA bitmaps from browser RAM/GPU when modal closes
  [sbsOrigImg, sbsEnhImg, sliderOrigImg, sliderEnhImg, singleEnhImg].forEach((img) => {
    if (img) img.removeAttribute("src");
  });
  if (loupeOrig) loupeOrig.style.backgroundImage = "none";
  if (loupeEnh) loupeEnh.style.backgroundImage = "none";
  if (quadMatrixGrid) quadMatrixGrid.innerHTML = "";
}

function switchViewMode(mode) {
  state.currentViewMode = mode;
  document.querySelectorAll(".view-mode-tabs .mode-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });

  viewSideBySide.hidden = mode !== "side-by-side";
  viewSlider.hidden = mode !== "slider";
  viewSingle.hidden = mode !== "enhanced-only";
  if (viewQuadMatrix) viewQuadMatrix.hidden = mode !== "quad-matrix";

  if (mode === "quad-matrix" && state.currentModalIndex >= 0) {
    renderQuadMatrix(state.filteredImages[state.currentModalIndex]);
  } else if (quadMatrixGrid) {
    quadMatrixGrid.innerHTML = "";
  }
}

/**
 * Autoplay 4K Slideshow Mode
 */
function toggleSlideshow() {
  if (state.slideshowTimer) {
    stopSlideshow();
  } else {
    startSlideshow();
  }
}

function startSlideshow() {
  stopSlideshow();
  const btn = document.getElementById("slideshowToggleBtn");
  const intervalMs = Number(document.getElementById("slideshowIntervalSelect").value || 5000);
  btn.classList.add("active");
  btn.textContent = "⏸ Pause";
  state.slideshowTimer = setInterval(() => {
    if (enhancerModal.hidden || state.filteredImages.length === 0) {
      stopSlideshow();
      return;
    }
    const nextIdx = (state.currentModalIndex + 1) % state.filteredImages.length;
    openEnhancerModal(nextIdx);
  }, intervalMs);
}

function stopSlideshow() {
  if (state.slideshowTimer) {
    clearInterval(state.slideshowTimer);
    state.slideshowTimer = null;
  }
  const btn = document.getElementById("slideshowToggleBtn");
  if (btn) {
    btn.classList.remove("active");
    btn.textContent = "▶ Slideshow";
  }
}

/**
 * Custom Preset Creation & Deletion
 */
async function saveCustomPreset() {
  const nameInput = document.getElementById("customPresetNameInput");
  const name = nameInput.value.trim() || `Custom Studio ${Object.keys(state.presetConfigs).length + 1}`;
  const params = {
    eye_enhance: Number(paramEye.value),
    bokeh_blur: Number(paramBokeh.value),
    detail_sharpen: Number(paramSharpen.value),
    skin_smooth: Number(paramSkin.value),
    micro_contrast: Number(paramContrast.value),
    depth_shadows: Number(paramShadows.value),
    warmth: Number(paramWarmth.value),
    vibrance: Number(paramVibrance.value),
    skin_mask_aware: paramSkinMask.checked,
    auto_exposure_wb: paramAutoWB.checked,
    is_monochrome: paramMonochrome ? paramMonochrome.checked : false,
    neon_pop: paramNeonPop ? paramNeonPop.checked : false,
    pencil_sketch: paramPencilSketch ? paramPencilSketch.checked : false,
    pro_pencil_sketch: paramProPencilSketch ? paramProPencilSketch.checked : false,
    traumatized_mode: paramTraumatized ? paramTraumatized.checked : false,
    preset_intensity: paramIntensity ? Number(paramIntensity.value) : 1.0,
    film_grain: paramFilmGrain ? Number(paramFilmGrain.value) : 0.0,
    vignette: paramVignette ? Number(paramVignette.value) : 0.0,
    highlight_bloom: paramBloom ? Number(paramBloom.value) : 0.15,
    crop_aspect: paramCropAspect.value,
    upscale_mode: paramUpscaleMode.value,
    lut_name: paramLutSelect.value,
  };

  const res = await fetch("/api/presets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, params }),
  });
  const data = await res.json();
  if (data.status === "ok") {
    state.presetConfigs = data.preset_configs;
    state.currentPreset = data.preset_key;
    nameInput.value = "";
    renderPresetSelectors();
  }
}

async function deleteCustomPreset(presetKey) {
  const res = await fetch(`/api/presets/${encodeURIComponent(presetKey)}`, {
    method: "DELETE",
  });
  const data = await res.json();
  if (data.status === "ok") {
    state.presetConfigs = data.preset_configs;
    if (state.currentPreset === presetKey) {
      state.currentPreset = "ultra_hot_4k";
    }
    renderPresetSelectors();
    syncSlidersToPreset(state.currentPreset);
  }
}

/**
 * Save SQLite Metadata (Model, Category, Rating, Tags)
 */
async function saveCurrentImageMetadata() {
  const item = state.filteredImages[state.currentModalIndex];
  if (!item) return;

  const rating = Number(modalStarBar.dataset.currentRating || 0);
  const model = metaModelInput.value.trim() || item.model;
  const category = metaCategoryInput.value.trim() || item.category;
  const tags = metaTagsInput.value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const title = `${model} — ${category}${item.timestamp ? ` (${item.timestamp})` : ""}`;

  saveMetadataBtn.textContent = "⏳ Saving...";
  const res = await fetch(`/api/metadata/${item.id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      model,
      category,
      rating,
      tags,
      favorite: state.favorites.has(item.id),
    }),
  });
  const data = await res.json();
  if (data.status === "ok" && data.image) {
    state.filteredImages[state.currentModalIndex] = data.image;
    populateModalMetadata(data.image);
    saveMetadataBtn.textContent = "✓ Saved to SQLite!";
    await scanAndLoadImages();
    setTimeout(() => {
      saveMetadataBtn.textContent = "💾 Save Metadata to SQLite";
    }, 1500);
  }
}

/**
 * Local Video Keyframe Extractor, AI Best-Frame Scanner & Loop Enhancer
 */
async function openVideoExtractorModal() {
  const modal = document.getElementById("videoExtractorModal");
  modal.hidden = false;
  document.body.style.overflow = "hidden";

  const listEl = document.getElementById("videoListContainer");
  listEl.innerHTML = `<div class="video-item-meta">Scanning /home/himanshu/Videos...</div>`;

  const res = await fetch("/api/videos");
  const data = await res.json();
  state.videos = data.videos || [];

  if (state.videos.length === 0) {
    listEl.innerHTML = `<div class="video-item-meta">No local videos found in /home/himanshu/Videos</div>`;
    return;
  }

  listEl.innerHTML = "";
  state.videos.forEach((vid, idx) => {
    const btn = document.createElement("button");
    btn.className = `video-item-btn ${idx === 0 ? "active" : ""}`;
    const resBadge = vid.res_label || `${Math.min(vid.width || 0, vid.height || 0)}p`;
    btn.innerHTML = `
      <span class="video-item-name">🎬 ${vid.name}</span>
      <span class="video-item-meta">${resBadge} • ${vid.width}×${vid.height} @ ${vid.fps || 24}fps • ${formatSeconds(
      vid.duration_sec
    )} (${vid.size_mb} MB)</span>
    `;
    btn.addEventListener("click", () => {
      listEl.querySelectorAll(".video-item-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("bestFramesStrip").hidden = true;
      selectVideoForScrubbing(vid);
    });
    listEl.appendChild(btn);
  });

  selectVideoForScrubbing(state.videos[0]);
}

function formatSeconds(sec) {
  const s = Math.max(0, Math.floor(sec || 0));
  const hh = String(Math.floor(s / 3600)).padStart(2, "0");
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function selectVideoForScrubbing(vid) {
  state.activeVideo = vid;
  const slider = document.getElementById("videoTimeSlider");
  const initialTs = Math.min(10, Math.max(1, (vid.duration_sec || 30) * 0.15));
  slider.max = String(vid.duration_sec || 120);
  slider.value = String(initialTs.toFixed(1));
  document.getElementById("videoTimeTotal").textContent = formatSeconds(vid.duration_sec);
  updateVideoPreviewFrame(initialTs);
}

function updateVideoPreviewFrame(ts) {
  if (!state.activeVideo) return;
  const maxDur = state.activeVideo.duration_sec || 120;
  const clamped = Math.max(0, Math.min(maxDur, Number(ts)));
  state.videoTimestamp = clamped;

  document.getElementById("videoTimeSlider").value = String(clamped);
  document.getElementById("videoTimeCurrent").textContent = formatSeconds(clamped);
  document.getElementById(
    "videoActiveBadge"
  ).textContent = `${state.activeVideo.name} @ ${formatSeconds(clamped)} (${state.activeVideo.width}×${
    state.activeVideo.height
  })`;

  const previewImg = document.getElementById("videoFramePreviewImg");
  previewImg.src = `/api/video/frame/${state.activeVideo.id}?t=${clamped.toFixed(2)}`;
}

async function scanBestVideoFrames() {
  if (!state.activeVideo) return;
  const btn = document.getElementById("scanBestFramesBtn");
  const strip = document.getElementById("bestFramesStrip");
  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "⏳ AI Scanning Sharpest Frames...";

  try {
    const res = await fetch(`/api/video/best-frames/${state.activeVideo.id}`);
    const data = await res.json();
    const frames = data.best_frames || [];
    strip.innerHTML = "";
    strip.hidden = frames.length === 0;

    frames.forEach((f) => {
      const card = document.createElement("div");
      card.className = "best-frame-card";
      card.innerHTML = `
        <img src="${f.preview_url}" alt="${f.time_str}" />
        <div class="best-frame-info">
          <span>${f.time_str}</span>
          <strong style="color:var(--accent-gold-bright)">⚡ ${f.ai_score}</strong>
        </div>
      `;
      card.addEventListener("click", () => {
        updateVideoPreviewFrame(f.timestamp);
      });
      strip.appendChild(card);
    });
    if (frames[0]) updateVideoPreviewFrame(frames[0].timestamp);
  } catch (e) {
    console.error("Best-frame scan error:", e);
  } finally {
    btn.textContent = origText;
    btn.disabled = false;
  }
}

async function extractCurrentVideoFrame() {
  if (!state.activeVideo) return;
  const btn = document.getElementById("extractVideoFrameBtn");
  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "⏳ Extracting & 4K Enhancing...";

  try {
    const res = await fetch("/api/video/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_id: state.activeVideo.id,
        timestamp: state.videoTimestamp,
        preset: state.currentPreset,
      }),
    });
    const data = await res.json();
    if (data.status === "ok" && data.image) {
      state.enhancedSet.add(data.image.id);
      btn.textContent = `✓ Extracted 4K (${data.image.filename})!`;
      await scanAndLoadImages();
      setTimeout(() => {
        btn.textContent = origText;
        btn.disabled = false;
      }, 2000);
    } else {
      btn.textContent = origText;
      btn.disabled = false;
    }
  } catch (e) {
    console.error("Video frame extraction error:", e);
    btn.textContent = origText;
    btn.disabled = false;
  }
}

async function extractCurrentVideoLoop() {
  if (!state.activeVideo) return;
  const btn = document.getElementById("extractVideoLoopBtn");
  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "⏳ Synthesizing 2.4s AI Loop...";

  try {
    const res = await fetch("/api/video/extract-loop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_id: state.activeVideo.id,
        timestamp: state.videoTimestamp,
        preset: state.currentPreset,
      }),
    });
    const data = await res.json();
    if (data.status === "ok" && data.image) {
      btn.textContent = `✓ Saved Loop (${data.image.filename})!`;
      await scanAndLoadImages();
      setTimeout(() => {
        btn.textContent = origText;
        btn.disabled = false;
      }, 2000);
    } else {
      btn.textContent = origText;
      btn.disabled = false;
    }
  } catch (e) {
    console.error("Video loop extraction error:", e);
    btn.textContent = origText;
    btn.disabled = false;
  }
}

/**
 * 10s–60s Video Clip AI Preset Converter & Custom Video Upload
 */
async function uploadVideoClipToStudio(file) {
  if (!file) return;
  const uploadBtn = document.getElementById("uploadVideoClipBtn");
  const origText = uploadBtn ? uploadBtn.textContent : "⬆ Upload Video Clip";
  if (uploadBtn) {
    uploadBtn.disabled = true;
    uploadBtn.textContent = "⏳ Uploading Video Clip...";
  }
  try {
    const res = await fetch("/api/video/upload", {
      method: "POST",
      headers: {
        "X-Filename": encodeURIComponent(file.name || `clip_${Date.now()}.mp4`),
        "Content-Type": file.type || "video/mp4",
      },
      body: file,
    });
    const data = await res.json();
    if (data.status === "ok" && data.video) {
      if (uploadBtn) uploadBtn.textContent = `✓ Loaded ${data.video.name}!`;
      await openVideoExtractorModal();
      const targetVid = (state.videos || []).find((v) => v.id === data.video.id) || data.video;
      selectVideoForScrubbing(targetVid);
    }
  } catch (err) {
    console.error("Video clip upload error:", err);
  } finally {
    setTimeout(() => {
      if (uploadBtn) {
        uploadBtn.textContent = origText;
        uploadBtn.disabled = false;
      }
    }, 1500);
  }
}

async function convertCurrentVideoClipToPreset() {
  if (!state.activeVideo) return;
  const btn = document.getElementById("convertVideoClipBtn");
  const presetSel = document.getElementById("videoClipPresetSelect");
  const durSel = document.getElementById("videoClipDurationSelect");
  const resSel = document.getElementById("videoClipResSelect");
  const fpsSel = document.getElementById("videoClipFpsSelect");
  const progWrap = document.getElementById("clipConvertProgressWrap");
  const progBar = document.getElementById("clipConvertProgressBar");
  const statusTxt = document.getElementById("clipConvertStatusText");
  const resultBox = document.getElementById("convertedClipResultBox");
  const player = document.getElementById("convertedClipVideoPlayer");
  const dlBtn = document.getElementById("downloadConvertedClipBtn");
  const titleBadge = document.getElementById("convertedClipTitleBadge");

  const presetKey = presetSel?.value || state.currentPreset;
  const durSec = Number(durSel?.value !== undefined ? durSel.value : 15);
  const isFullVideo = durSec <= 0;
  const resP = resSel && resSel.value !== "" ? Number(resSel.value) : 0;
  const fpsVal = fpsSel && fpsSel.value !== "" ? Number(fpsSel.value) : 0;
  const origBtnText = btn ? btn.textContent : "🎬 Enhance Video to Preset (.mp4)";
  const resText = resP <= 0 ? state.activeVideo.res_label || "Original Res" : `${resP}p`;
  const fpsText = fpsVal <= 0 ? `${state.activeVideo.fps || 24} FPS` : `${fpsVal} FPS`;
  const durLabel = isFullVideo ? "Full Video" : `${durSec}s`;
  const cancelBtn = document.getElementById("cancelVideoClipBtn");

  const formatEta = (sec) => {
    if (sec == null || isNaN(sec) || sec <= 0) return "—";
    const s = Math.round(sec);
    if (s >= 3600) {
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      return `${h}h ${m}m`;
    }
    if (s >= 60) {
      const m = Math.floor(s / 60);
      const rem = s % 60;
      return `${m}m ${rem}s`;
    }
    return `${s}s`;
  };

  if (btn) {
    btn.disabled = true;
    btn.textContent = `⏳ Enhancing ${durLabel}...`;
  }
  if (progWrap) progWrap.hidden = false;
  if (progBar) progBar.style.width = "3%";
  if (statusTxt) statusTxt.textContent = `Starting ${durLabel} AI preset conversion (${resText} @ ${fpsText})...`;

  try {
    const startRes = await fetch("/api/video/convert-clip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_id: state.activeVideo.id,
        timestamp: state.videoTimestamp,
        duration_sec: durSec,
        preset: presetKey,
        resolution_p: resP,
        fps: fpsVal,
      }),
    });
    const startData = await startRes.json();
    if (startData.status !== "ok" || !startData.job) {
      throw new Error(startData.error || "Could not start video conversion");
    }

    let job = startData.job;

    if (cancelBtn) {
      cancelBtn.hidden = false;
      cancelBtn.disabled = false;
      cancelBtn.textContent = "🛑 Cancel";
      cancelBtn.onclick = async () => {
        cancelBtn.disabled = true;
        cancelBtn.textContent = "Cancelling...";
        try {
          await fetch("/api/video/cancel-clip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ job_id: job.job_id }),
          });
        } catch (e) {
          console.error("Cancel failed:", e);
        }
      };
    }

    while (job.status === "running") {
      await new Promise((r) => setTimeout(r, 450));
      const pollRes = await fetch(`/api/video/clip-status/${job.job_id}`);
      const pollData = await pollRes.json();
      if (pollData.status !== "ok" || !pollData.job) break;
      job = pollData.job;
      if (progBar) progBar.style.width = `${job.progress_pct || 5}%`;
      if (statusTxt) {
        statusTxt.textContent = `⚡ Enhancing Frame ${job.done_frames}/${job.total_frames} (${job.progress_pct}%) • ${
          job.resolution_p >= 2000 ? "4K 2160p" : `${job.resolution_p}p`
        } @ ${job.fps_speed || "—"} FPS • ETA ${formatEta(job.eta_sec)}`;
      }
    }

    if (job.status === "completed") {
      const doneResTag = job.resolution_p >= 2000 ? "4K 2160p" : `${job.resolution_p}p`;
      if (progBar) progBar.style.width = "100%";
      if (statusTxt) {
        statusTxt.textContent = `✓ Completed ${job.duration_sec}s ${job.preset_name} Video (${doneResTag} @ ${job.fps} FPS • ${job.size_mb} MB)!`;
      }
      if (resultBox && player) {
        resultBox.hidden = false;
        player.src = `${job.video_url}?_t=${Date.now()}`;
        player.play().catch(() => {});
      }
      if (dlBtn) {
        dlBtn.href = job.download_url;
      }
      if (titleBadge) {
        titleBadge.textContent = `✨ ${job.preset_name} • ${job.duration_sec}s (${doneResTag} @ ${job.fps} FPS • ${job.size_mb} MB)`;
      }
      if (btn) btn.textContent = "✓ Video Ready Below!";
    } else if (job.status === "cancelled") {
      if (progBar) progBar.style.width = "0%";
      if (statusTxt) statusTxt.textContent = "🛑 Video enhancement was cancelled by user.";
    } else {
      if (statusTxt) statusTxt.textContent = `❌ Conversion error: ${job.error || "Unknown error"}`;
    }
  } catch (err) {
    console.error("Video preset conversion error:", err);
    if (statusTxt) statusTxt.textContent = `❌ Conversion failed: ${err.message || err}`;
  } finally {
    if (cancelBtn) cancelBtn.hidden = true;
    setTimeout(() => {
      if (btn) {
        btn.textContent = origBtnText;
        btn.disabled = false;
      }
    }, 1800);
  }
}

/**
 * Folder Switcher & Batch 4K ZIP Export Modals
 */
async function openFolderSwitcherModal() {
  const modal = document.getElementById("utilityModal");
  document.getElementById("utilityModalBadge").textContent = "📂 SOURCE DIRECTORY";
  document.getElementById("utilityModalTitle").textContent = "Switch Local Image Folder";
  document.getElementById("folderSwitcherBody").hidden = false;
  document.getElementById("batchExportBody").hidden = true;
  modal.hidden = false;

  const res = await fetch("/api/folders");
  const data = await res.json();
  document.getElementById("customFolderInput").value = data.active_folder || "";
  document.getElementById("recursiveFolderCheck").checked = Boolean(data.recursive);

  const listEl = document.getElementById("folderListContainer");
  listEl.innerHTML = "";
  (data.folders || []).forEach((f) => {
    const btn = document.createElement("button");
    btn.className = `folder-option-btn ${f.active ? "active" : ""}`;
    btn.innerHTML = `
      <span>📁 <strong>${f.name}</strong> <small style="color:var(--text-muted)">(${f.path})</small></span>
      <span class="res-tag gold">${f.image_count} imgs</span>
    `;
    btn.addEventListener("click", async () => {
      await applySourceFolder(f.path, document.getElementById("recursiveFolderCheck").checked);
    });
    listEl.appendChild(btn);
  });
}

async function applySourceFolder(pathStr, recursive) {
  const res = await fetch("/api/source-folder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: pathStr, recursive }),
  });
  const data = await res.json();
  if (data.status === "ok") {
    document.getElementById("utilityModal").hidden = true;
    await scanAndLoadImages();
  }
}

function openBatchExportModal() {
  const modal = document.getElementById("utilityModal");
  document.getElementById("utilityModalBadge").textContent = "📦 BATCH 4K ARCHIVE";
  document.getElementById("utilityModalTitle").textContent = "Export Batch 4K+ Enhanced ZIP";
  document.getElementById("folderSwitcherBody").hidden = true;
  document.getElementById("batchExportBody").hidden = false;
  modal.hidden = false;
}

/**
 * Moodboards & Collections Management
 */
function openBoardsModal() {
  boardsListContainer.innerHTML = "";
  if (state.boards.length === 0) {
    boardsListContainer.innerHTML = `<div class="utility-desc">No boards yet. Type a name above and click '+ Create Board' to create your first collection.</div>`;
  } else {
    state.boards.forEach((b) => {
      const itemRow = document.createElement("div");
      itemRow.className = "folder-item";
      itemRow.innerHTML = `
        <div class="folder-item-info">
          <div class="folder-item-name">📌 ${b.name}</div>
          <div class="folder-item-path">${b.item_count || 0} pinned media items</div>
        </div>
        <div style="display:flex; gap:6px;">
          <button class="btn-secondary-sm" data-view-board="${b.id}">View Gallery</button>
          <button class="preset-del-btn" data-del-board="${b.id}" title="Delete Moodboard">&times;</button>
        </div>
      `;
      itemRow.querySelector("[data-view-board]").addEventListener("click", async () => {
        state.activeBoardId = b.id;
        if (!state.boardItems[b.id]) {
          const res = await fetch(`/api/boards/${b.id}/items`);
          const d = await res.json();
          state.boardItems[b.id] = d.items || [];
        }
        boardsModal.hidden = true;
        scanAndLoadImages();
      });
      itemRow.querySelector("[data-del-board]").addEventListener("click", async () => {
        if (!confirm(`Delete moodboard "${b.name}"?`)) return;
        await fetch(`/api/boards/${b.id}`, { method: "DELETE" });
        if (state.activeBoardId === b.id) state.activeBoardId = "";
        delete state.boardItems[b.id];
        await loadBoards();
        openBoardsModal();
      });
      boardsListContainer.appendChild(itemRow);
    });
  }
  boardsModal.hidden = false;
}

function openPinModal(imgId) {
  state.activePinImageId = imgId;
  pinBoardsListContainer.innerHTML = "";
  if (state.boards.length === 0) {
    pinBoardsListContainer.innerHTML = `
      <p class="utility-desc">No moodboards created yet.</p>
      <button class="nav-pill-btn accent-btn" id="pinCreateFirstBoardBtn">+ Create Moodboard First</button>
    `;
    document.getElementById("pinCreateFirstBoardBtn")?.addEventListener("click", () => {
      pinModal.hidden = true;
      openBoardsModal();
    });
  } else {
    state.boards.forEach((b) => {
      const itemRow = document.createElement("div");
      itemRow.className = "folder-item";
      itemRow.innerHTML = `
        <div class="folder-item-info">
          <div class="folder-item-name">📌 ${b.name}</div>
          <div class="folder-item-path">${b.item_count || 0} pinned items</div>
        </div>
        <button class="nav-pill-btn accent-btn" data-pin-board="${b.id}">Pin Here</button>
      `;
      itemRow.querySelector("[data-pin-board]").addEventListener("click", async () => {
        await fetch(`/api/boards/${b.id}/items`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ img_id: state.activePinImageId }),
        });
        delete state.boardItems[b.id];
        await loadBoards();
        pinModal.hidden = true;
        scanTelemetryPill.textContent = `📌 Pinned image to ${b.name}`;
      });
      pinBoardsListContainer.appendChild(itemRow);
    });
  }
  pinModal.hidden = false;
}

/**
 * Picture Upload Studio Modal & Direct Ingestion Engine
 */
function openUploadModal(initialFiles = null) {
  if (!uploadModal) {
    manualFileInput?.click();
    return;
  }
  if (uploadPresetSelect && state.presetConfigs[state.currentPreset]) {
    uploadPresetSelect.value = state.currentPreset;
  }
  if (uploadProgressWrap) uploadProgressWrap.hidden = true;
  if (uploadProgressBar) uploadProgressBar.style.width = "0%";
  uploadModal.hidden = false;
  document.body.style.overflow = "hidden";

  if (initialFiles && initialFiles.length > 0) {
    stageFilesForUpload(initialFiles);
  } else {
    renderUploadQueue();
  }
}

function closeUploadModal() {
  if (!uploadModal) return;
  uploadModal.hidden = true;
  if (enhancerModal.hidden) {
    document.body.style.overflow = "";
  }
  clearUploadQueue();
}

function clearUploadQueue() {
  (state.uploadObjectUrls || []).forEach((u) => {
    try {
      URL.revokeObjectURL(u);
    } catch (_) {}
  });
  state.uploadObjectUrls = [];
  state.uploadQueue = [];
  renderUploadQueue();
}

function stageFilesForUpload(fileList) {
  if (!fileList || fileList.length === 0) return;
  for (let i = 0; i < fileList.length; i++) {
    const f = fileList[i];
    if (!f) continue;
    const isImage =
      (f.type && f.type.startsWith("image/")) ||
      /\.(jpe?g|png|webp|bmp|tiff?)$/i.test(f.name || "");
    if (!isImage) continue;
    const objUrl = URL.createObjectURL(f);
    state.uploadObjectUrls.push(objUrl);
    state.uploadQueue.push({ file: f, previewUrl: objUrl });
  }
  renderUploadQueue();
}

function renderUploadQueue() {
  if (!uploadStagedSection || !uploadPreviewGrid || !startUploadBtn) return;
  const count = state.uploadQueue.length;
  uploadStagedSection.hidden = count === 0;
  startUploadBtn.disabled = count === 0;

  if (uploadStagedCountLabel) {
    uploadStagedCountLabel.textContent = `${count} Picture${count === 1 ? "" : "s"} Ready to Upload`;
  }
  startUploadBtn.textContent =
    count > 0
      ? `⬆ Upload & Process ${count} Picture${count === 1 ? "" : "s"}`
      : "⬆ Upload & Enhance Selected Pictures";

  uploadPreviewGrid.innerHTML = "";
  state.uploadQueue.forEach((entry, idx) => {
    const sizeKb = Math.max(1, Math.round(entry.file.size / 1024));
    const sizeLabel = sizeKb >= 1024 ? `${(sizeKb / 1024).toFixed(1)} MB` : `${sizeKb} KB`;
    const card = document.createElement("div");
    card.className = "upload-preview-card";
    card.innerHTML = `
      <img src="${entry.previewUrl}" alt="${entry.file.name}" decoding="async" />
      <button type="button" class="upload-preview-remove" data-rm-idx="${idx}" title="Remove">&times;</button>
      <div class="upload-preview-meta" title="${entry.file.name}">${entry.file.name} (${sizeLabel})</div>
    `;
    card.querySelector("[data-rm-idx]").addEventListener("click", (e) => {
      e.stopPropagation();
      const rmItem = state.uploadQueue.splice(idx, 1)[0];
      if (rmItem && rmItem.previewUrl) {
        try {
          URL.revokeObjectURL(rmItem.previewUrl);
        } catch (_) {}
      }
      renderUploadQueue();
    });
    uploadPreviewGrid.appendChild(card);
  });
}

function uploadSingleFileXHR(file, opts, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload", true);
    xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name || `upload_${Date.now()}.jpg`));
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    if (opts.model) xhr.setRequestHeader("X-Model", encodeURIComponent(opts.model));
    if (opts.category) xhr.setRequestHeader("X-Category", encodeURIComponent(opts.category));
    if (opts.tags) xhr.setRequestHeader("X-Tags", encodeURIComponent(opts.tags));
    if (opts.preset) xhr.setRequestHeader("X-Preset", encodeURIComponent(opts.preset));
    xhr.setRequestHeader("X-Auto-Enhance", opts.autoEnhance ? "1" : "0");

    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable && onProgress) {
        onProgress(evt.loaded / evt.total);
      }
    };
    xhr.onload = () => {
      try {
        const res = JSON.parse(xhr.responseText || "{}");
        if (xhr.status >= 200 && xhr.status < 300 && res.status === "ok") {
          resolve(res);
        } else {
          reject(new Error(res.error || `Upload failed (${xhr.status})`));
        }
      } catch (err) {
        reject(err);
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(file);
  });
}

async function executeStagedUploads() {
  if (state.uploadQueue.length === 0) return;
  const total = state.uploadQueue.length;
  const modelVal = (uploadModelInput?.value || "").trim();
  const catVal = (uploadCategoryInput?.value || "Uploaded").trim() || "Uploaded";
  const tagsVal = (uploadTagsInput?.value || "").trim();
  const presetVal = uploadPresetSelect?.value || state.currentPreset;
  const autoEnhance = uploadAutoEnhanceCheck ? uploadAutoEnhanceCheck.checked : true;
  const autoOpen = uploadAutoOpenCheck ? uploadAutoOpenCheck.checked : true;

  if (startUploadBtn) startUploadBtn.disabled = true;
  if (uploadProgressWrap) uploadProgressWrap.hidden = false;
  if (uploadProgressBar) uploadProgressBar.style.width = "4%";

  const uploadedIds = [];
  let errors = 0;

  for (let i = 0; i < total; i++) {
    const { file } = state.uploadQueue[i];
    if (uploadStatusText) {
      uploadStatusText.textContent = `Uploading (${i + 1}/${total}): ${file.name}${
        autoEnhance ? " + 4K AI Enhancing..." : "..."
      }`;
    }
    try {
      const res = await uploadSingleFileXHR(
        file,
        {
          model: modelVal,
          category: catVal,
          tags: tagsVal,
          preset: presetVal,
          autoEnhance,
        },
        (fileRatio) => {
          const overallPct = Math.min(99, Math.round(((i + fileRatio * 0.85) / total) * 100));
          if (uploadProgressBar) uploadProgressBar.style.width = `${overallPct}%`;
        }
      );
      if (res && res.id) {
        uploadedIds.push(res.id);
        if (autoEnhance) {
          state.enhancedSet.add(res.id);
        }
      }
    } catch (err) {
      console.error("Upload error:", err);
      errors++;
    }
  }

  if (uploadProgressBar) uploadProgressBar.style.width = "100%";

  if (uploadedIds.length > 0) {
    state.currentPreset = presetVal;
    if (globalPresetSelect) globalPresetSelect.value = presetVal;
    state.lastUploadedIds = [...uploadedIds, ...state.lastUploadedIds].slice(0, 20);
    scanTelemetryPill.textContent = `✅ Uploaded ${uploadedIds.length} picture${
      uploadedIds.length === 1 ? "" : "s"
    }${autoEnhance ? " & Enhanced in 4K" : ""}`;

    if (uploadStatusText) {
      uploadStatusText.textContent = `✓ Successfully uploaded ${uploadedIds.length} picture${
        uploadedIds.length === 1 ? "" : "s"
      }!`;
    }

    await scanAndLoadImages();
    closeUploadModal();

    if (autoOpen) {
      const firstId = uploadedIds[0];
      const targetIdx = state.filteredImages.findIndex((it) => it.id === firstId);
      if (targetIdx >= 0) {
        openEnhancerModal(targetIdx);
      }
    }
  } else {
    if (uploadStatusText) {
      uploadStatusText.textContent = `❌ Upload failed (${errors} error${errors === 1 ? "" : "s"}). Please choose a valid JPG/PNG/WebP image.`;
    }
    if (startUploadBtn) startUploadBtn.disabled = false;
  }
}

async function uploadFiles(fileList) {
  if (!fileList || fileList.length === 0) return;
  openUploadModal(fileList);
}

/**
 * Video Scene Cut Scanner
 */
async function scanVideoScenes(vidId) {
  if (!vidId) return;
  scanScenesBtn.textContent = "🎬 Scanning cuts...";
  scanScenesBtn.disabled = true;
  try {
    const res = await fetch(`/api/video/scenes/${vidId}`);
    const data = await res.json();
    const scenes = data.scenes || [];
    const container = document.getElementById("bestFramesStrip");
    container.hidden = false;
    container.innerHTML = "";
    if (scenes.length === 0) {
      container.innerHTML = `<span style="font-size:12px;color:var(--text-muted);padding:8px;">No major scene cuts detected.</span>`;
    } else {
      scenes.forEach((sc) => {
        const card = document.createElement("div");
        card.className = "best-frame-card";
        card.innerHTML = `
          <img src="${sc.preview_url}" alt="Scene cut at ${sc.time_str}" />
          <div class="best-frame-info">
            <span>🎬 ${sc.time_str}</span>
            <span>Cut Δ${sc.diff}</span>
          </div>
        `;
        card.addEventListener("click", () => {
          updateVideoPreviewFrame(sc.timestamp);
          const slider = document.getElementById("videoTimeSlider");
          if (slider) slider.value = sc.timestamp;
        });
        container.appendChild(card);
      });
    }
  } catch (err) {
    console.error("Scene scan error:", err);
  } finally {
    scanScenesBtn.textContent = "🎬 Detect Scene Cuts";
    scanScenesBtn.disabled = false;
  }
}

/**
 * Continuously Running Rotating 4K Subject Muse
 * Selects random image every 10 seconds, extracts clean transparent subject,
 * continuously rotates clockwise without interruption, and cross-fades smoothly.
 */
async function fetchRandomNobgSubject(excludeId = "") {
  try {
    const res = await fetch(`/api/image/nobg-random?exclude=${encodeURIComponent(excludeId)}`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.subject || null;
  } catch (err) {
    console.warn("[Muse] Failed to fetch random subject:", err);
    return null;
  }
}

async function rotateToNextMuse() {
  const nextSubject = await fetchRandomNobgSubject(state.currentMuseId);
  if (!nextSubject || !nextSubject.nobg_url) return;

  // Preload image in memory first to ensure instantaneous, seamless cross-fade
  const loader = new Image();
  loader.src = nextSubject.nobg_url;
  await new Promise((resolve) => {
    loader.onload = resolve;
    loader.onerror = resolve;
  });

  const imgIn = state.museActiveSlot === "current" ? museImgNext : museImgCurrent;
  const imgOut = state.museActiveSlot === "current" ? museImgCurrent : museImgNext;

  if (imgIn && imgOut) {
    imgIn.src = nextSubject.nobg_url;
    imgIn.alt = nextSubject.title || "4K Rotating Muse";

    // Smooth dissolve while clockwise rotation continues uninterrupted
    imgIn.classList.add("active");
    imgOut.classList.remove("active");

    state.museActiveSlot = state.museActiveSlot === "current" ? "next" : "current";
    state.currentMuseId = nextSubject.id;
    state.currentMuseItem = nextSubject;

    if (museModelName) museModelName.textContent = nextSubject.model || "Featured Muse";
    if (museCategoryTag) museCategoryTag.textContent = nextSubject.category || "Exclusive Studio";
  }
}

function setMuseEnabled(enabled) {
  state.museEnabled = enabled;
  localStorage.setItem("elitebabes_muse_enabled", String(enabled));
  const container = document.getElementById("museOrbitContainer");
  const toggleBtn = document.getElementById("museToggleFeatureBtn");
  if (container) {
    container.classList.toggle("disabled", !enabled);
  }
  document.body.classList.toggle("muse-disabled", !enabled);
  if (toggleBtn) {
    toggleBtn.classList.toggle("off", !enabled);
    toggleBtn.textContent = enabled ? "🌀 3D Muse: ON" : "🌀 3D Muse: OFF";
  }
  if (enabled) {
    if (!state.currentMuseItem) rotateToNextMuse();
    clearInterval(state.museTimer);
    state.museTimer = setInterval(rotateToNextMuse, 10000);
  } else {
    clearInterval(state.museTimer);
    state.museTimer = null;
  }
}

function setFiltersCollapsed(collapsed) {
  state.filtersCollapsed = collapsed;
  localStorage.setItem("elitebabes_filters_collapsed", String(collapsed));
  const drawer = document.getElementById("filterBarsContainer");
  const toggleBtn = document.getElementById("toggleFiltersBtn");
  if (drawer) {
    drawer.classList.toggle("collapsed", collapsed);
  }
  if (toggleBtn) {
    toggleBtn.textContent = collapsed ? "🎛️ Filters ▾" : "🎛️ Filters ▴";
  }
}

function initRotatingMuse() {
  if (!museRotator) return;

  // Close / Disable Button on Widget
  const closeBtn = document.getElementById("museCloseBtn");
  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      setMuseEnabled(false);
    });
  }

  // Topbar Muse Feature Toggle Button
  const museToggleBtn = document.getElementById("museToggleFeatureBtn");
  if (museToggleBtn) {
    museToggleBtn.addEventListener("click", () => {
      setMuseEnabled(!state.museEnabled);
    });
  }

  // Initialize muse state
  setMuseEnabled(state.museEnabled);

  // Quick Controls
  if (museNextBtn) {
    museNextBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      clearInterval(state.museTimer);
      rotateToNextMuse();
      if (state.museEnabled) {
        state.museTimer = setInterval(rotateToNextMuse, 10000);
      }
    });
  }

  if (museToggleSpinBtn) {
    museToggleSpinBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      state.museSpinning = !state.museSpinning;
      museRotator.classList.toggle("paused", !state.museSpinning);
      museToggleSpinBtn.textContent = state.museSpinning ? "⏸" : "▶";
    });
  }

  const launchInspect = () => {
    if (!state.currentMuseId) return;
    const idx = state.filteredImages.findIndex((it) => it.id === state.currentMuseId);
    if (idx >= 0) {
      openEnhancerModal(idx);
    } else if (state.filteredImages.length > 0) {
      openEnhancerModal(0);
    }
  };

  if (museInspectBtn) museInspectBtn.addEventListener("click", launchInspect);
  if (museCardMeta) museCardMeta.addEventListener("click", launchInspect);
  if (museStageWrap) museStageWrap.addEventListener("click", launchInspect);
}

/**
 * Boss-Key / Instant Privacy Disguise & Optional PIN Lock
 */
function toggleBossKey() {
  const overlay = document.getElementById("privacyLockOverlay");
  const savedPin = localStorage.getItem("elitebabes_pin") || "";

  if (!state.privacyLocked) {
    stopSlideshow();
    state.privacyLocked = true;
    overlay.hidden = false;
    document.title = "System Telemetry Monitor — 127.0.0.1:8765";
    document.getElementById("privacyPinInput").value = "";
  } else {
    const enteredPin = document.getElementById("privacyPinInput").value;
    if (savedPin && enteredPin !== savedPin) {
      document.getElementById("privacyPinInput").style.borderColor = "#ff2e6c";
      document.getElementById("privacyPinInput").focus();
      return;
    }
    state.privacyLocked = false;
    overlay.hidden = true;
    document.title = state.originalTitle;
  }
}

/**
 * Server-Sent Events (SSE) Live Folder Watcher
 */
function initLiveWatcherSSE() {
  try {
    const es = new EventSource("/api/events");
    es.addEventListener("folder_changed", () => {
      const statusEl = document.getElementById("liveWatchStatus");
      if (statusEl) statusEl.textContent = "SYNCING NEW FILES...";
      scanAndLoadImages().then(() => {
        if (statusEl) statusEl.textContent = "ONLINE & WATCHING";
      });
    });
  } catch (e) {
    console.warn("SSE watcher fallback:", e);
  }
}

// Interactive Split-Slider Dragging Logic
function initSplitSlider() {
  let isDragging = false;

  const updateSliderPos = (clientX) => {
    const rect = splitSliderWrapper.getBoundingClientRect();
    if (!rect.width) return;
    let pct = ((clientX - rect.left) / rect.width) * 100;
    pct = Math.max(2, Math.min(98, pct));
    sliderOrigClip.style.width = `${pct}%`;
    sliderHandle.style.left = `${pct}%`;
    sliderOrigImg.style.width = `${rect.width}px`;
  };

  splitSliderWrapper.addEventListener("mousedown", (e) => {
    isDragging = true;
    updateSliderPos(e.clientX);
  });

  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    updateSliderPos(e.clientX);
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
  });

  splitSliderWrapper.addEventListener(
    "touchstart",
    (e) => {
      isDragging = true;
      if (e.touches[0]) updateSliderPos(e.touches[0].clientX);
    },
    { passive: true }
  );

  window.addEventListener(
    "touchmove",
    (e) => {
      if (!isDragging || !e.touches[0]) return;
      updateSliderPos(e.touches[0].clientX);
    },
    { passive: true }
  );

  window.addEventListener("touchend", () => {
    isDragging = false;
  });
}

// Event Listeners Setup
function initEvents() {
  // Dynamic Image Shuffle
  if (shuffleBtn) {
    shuffleBtn.addEventListener("click", triggerDynamicShuffle);
  }

  // Upload Studio Modal, Browse, Drag-and-Drop & Clipboard Paste (Ctrl+V)
  [openUploadBtn, heroUploadBtn, emptyUploadBtn].filter(Boolean).forEach((btn) => {
    btn.addEventListener("click", () => openUploadModal());
  });

  if (browseFilesBtn) {
    browseFilesBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      manualFileInput?.click();
    });
  }
  if (uploadDropzone) {
    uploadDropzone.addEventListener("click", (e) => {
      if (e.target.closest("#browseFilesBtn")) return;
      manualFileInput?.click();
    });
    uploadDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadDropzone.classList.add("drag-over");
    });
    uploadDropzone.addEventListener("dragleave", () => {
      uploadDropzone.classList.remove("drag-over");
    });
    uploadDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadDropzone.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        stageFilesForUpload(e.dataTransfer.files);
      }
    });
  }

  if (manualFileInput) {
    manualFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        if (uploadModal && !uploadModal.hidden) {
          stageFilesForUpload(e.target.files);
        } else {
          openUploadModal(e.target.files);
        }
      }
      manualFileInput.value = "";
    });
  }

  [uploadModalCloseBtn, cancelUploadModalBtn, uploadModalBackdrop].filter(Boolean).forEach((el) => {
    el.addEventListener("click", closeUploadModal);
  });
  if (clearUploadQueueBtn) {
    clearUploadQueueBtn.addEventListener("click", clearUploadQueue);
  }
  if (startUploadBtn) {
    startUploadBtn.addEventListener("click", executeStagedUploads);
  }

  window.addEventListener("dragover", (e) => {
    e.preventDefault();
  });
  window.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      openUploadModal(e.dataTransfer.files);
    }
  });

  // Global Clipboard Image Paste (Ctrl+V)
  window.addEventListener("paste", (e) => {
    if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    const pastedFiles = [];
    for (let i = 0; i < items.length; i++) {
      if (items[i].type && items[i].type.startsWith("image/")) {
        const blob = items[i].getAsFile();
        if (blob) {
          const ext = blob.type.split("/")[1] || "png";
          const namedFile = new File([blob], `pasted_image_${Date.now()}.${ext}`, { type: blob.type });
          pastedFiles.push(namedFile);
        }
      }
    }
    if (pastedFiles.length > 0) {
      e.preventDefault();
      openUploadModal(pastedFiles);
    }
  });

  // Moodboards Modal & Creation
  if (openBoardsBtn) {
    openBoardsBtn.addEventListener("click", openBoardsModal);
  }
  if (boardsModalCloseBtn) {
    boardsModalCloseBtn.addEventListener("click", () => (boardsModal.hidden = true));
  }
  if (boardsModalBackdrop) {
    boardsModalBackdrop.addEventListener("click", () => (boardsModal.hidden = true));
  }
  if (createBoardBtn) {
    createBoardBtn.addEventListener("click", async () => {
      const name = (newBoardInput.value || "").trim();
      if (!name) return;
      createBoardBtn.disabled = true;
      try {
        await fetch("/api/boards", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        });
        newBoardInput.value = "";
        await loadBoards();
        openBoardsModal();
      } finally {
        createBoardBtn.disabled = false;
      }
    });
  }

  // Pin Modal Close
  if (pinModalCloseBtn) {
    pinModalCloseBtn.addEventListener("click", () => (pinModal.hidden = true));
  }
  if (pinModalBackdrop) {
    pinModalBackdrop.addEventListener("click", () => (pinModal.hidden = true));
  }

  // Palette Swatch Buttons Filter
  document.querySelectorAll(".palette-swatch-list .swatch-btn").forEach((sBtn) => {
    sBtn.addEventListener("click", () => {
      document
        .querySelectorAll(".palette-swatch-list .swatch-btn")
        .forEach((b) => b.classList.remove("active"));
      sBtn.classList.add("active");
      state.activeColorFilter = sBtn.dataset.color || "";
      scanAndLoadImages();
    });
  });

  // Video Scene Cuts Scanner
  if (scanScenesBtn) {
    scanScenesBtn.addEventListener("click", () => {
      if (state.activeVideo) scanVideoScenes(state.activeVideo.id);
    });
  }

  // Real-Time Search Bar
  let searchTimer = null;
  searchInput.addEventListener("input", () => {
    const val = searchInput.value;
    searchClearBtn.hidden = !val;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.activeQuery = val;
      scanAndLoadImages();
    }, 120);
  });

  searchClearBtn.addEventListener("click", () => {
    searchInput.value = "";
    searchClearBtn.hidden = true;
    state.activeQuery = "";
    scanAndLoadImages();
  });

  // Rating Filter Chips
  ratingChips.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      ratingChips.querySelectorAll(".chip").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.minRating = Number(btn.dataset.rating || 0);
      scanAndLoadImages();
    });
  });

  // Deduplicate Bursts & Clear Similarity
  dedupToggleBtn.addEventListener("click", () => {
    state.deduplicate = !state.deduplicate;
    dedupToggleBtn.classList.toggle("active", state.deduplicate);
    scanAndLoadImages();
  });

  clearSimilarityBtn.addEventListener("click", () => {
    state.similarTo = "";
    scanAndLoadImages();
  });

  // Boss-Key Privacy Lock Events
  document.getElementById("bossKeyBtn").addEventListener("click", toggleBossKey);
  document.getElementById("privacyUnlockBtn").addEventListener("click", toggleBossKey);
  document.getElementById("savePinBtn").addEventListener("click", () => {
    const pin = document.getElementById("newPinInput").value.trim();
    localStorage.setItem("elitebabes_pin", pin);
    document.getElementById("newPinInput").value = "";
    document.getElementById("savePinBtn").textContent = pin ? "✓ PIN Saved" : "✓ PIN Cleared";
  });

  // Rescan Folder Button
  document.getElementById("rescanBtn").addEventListener("click", () => {
    scanAndLoadImages();
  });

  // Folder Switcher & Batch Export Header Buttons
  document.getElementById("openFolderModalBtn").addEventListener("click", openFolderSwitcherModal);
  document.getElementById("openBatchExportBtn").addEventListener("click", openBatchExportModal);
  document.getElementById("openVideoExtractorBtn").addEventListener("click", openVideoExtractorModal);

  document.getElementById("utilityModalCloseBtn").addEventListener("click", () => {
    document.getElementById("utilityModal").hidden = true;
  });
  document.getElementById("utilityModalBackdrop").addEventListener("click", () => {
    document.getElementById("utilityModal").hidden = true;
  });

  document.getElementById("applyCustomFolderBtn").addEventListener("click", () => {
    const pathStr = document.getElementById("customFolderInput").value.trim();
    const rec = document.getElementById("recursiveFolderCheck").checked;
    if (pathStr) applySourceFolder(pathStr, rec);
  });

  document.getElementById("startBatchZipBtn").addEventListener("click", () => {
    const scope = document.getElementById("exportScopeSelect").value;
    const preset = document.getElementById("exportPresetSelect").value || state.currentPreset;
    const fmt = document.getElementById("exportFormatSelect").value || "jpg";

    let items = state.filteredImages;
    if (scope === "favorites") {
      items = state.filteredImages.filter((it) => state.favorites.has(it.id) || it.favorite);
    }
    const ids = items.map((it) => it.id).join(",");
    window.location.href = `/api/export-zip?ids=${encodeURIComponent(ids)}&preset=${encodeURIComponent(
      preset
    )}&format=${encodeURIComponent(fmt)}`;
    document.getElementById("utilityModal").hidden = true;
  });

  // Video Extractor Events
  const stopConvertedClipPlayer = () => {
    const player = document.getElementById("convertedClipVideoPlayer");
    if (player) {
      player.pause();
      player.removeAttribute("src");
      player.load();
    }
    const resultBox = document.getElementById("convertedClipResultBox");
    if (resultBox) resultBox.hidden = true;
  };

  document.getElementById("videoModalCloseBtn").addEventListener("click", () => {
    stopConvertedClipPlayer();
    document.getElementById("videoExtractorModal").hidden = true;
    document.body.style.overflow = "";
  });
  document.getElementById("videoModalBackdrop").addEventListener("click", () => {
    stopConvertedClipPlayer();
    document.getElementById("videoExtractorModal").hidden = true;
    document.body.style.overflow = "";
  });
  document.getElementById("closeConvertedClipBtn")?.addEventListener("click", stopConvertedClipPlayer);

  const uploadVideoClipBtn = document.getElementById("uploadVideoClipBtn");
  const manualVideoInput = document.getElementById("manualVideoInput");
  if (uploadVideoClipBtn && manualVideoInput) {
    uploadVideoClipBtn.addEventListener("click", () => manualVideoInput.click());
    manualVideoInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        uploadVideoClipToStudio(e.target.files[0]);
      }
      manualVideoInput.value = "";
    });
  }

  document.getElementById("convertVideoClipBtn")?.addEventListener("click", convertCurrentVideoClipToPreset);

  let scrubTimer = null;
  document.getElementById("videoTimeSlider").addEventListener("input", (e) => {
    const val = Number(e.target.value);
    document.getElementById("videoTimeCurrent").textContent = formatSeconds(val);
    clearTimeout(scrubTimer);
    scrubTimer = setTimeout(() => updateVideoPreviewFrame(val), 90);
  });

  document.querySelectorAll(".video-step-actions [data-step]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const delta = Number(btn.dataset.step);
      updateVideoPreviewFrame(state.videoTimestamp + delta);
    });
  });

  document.getElementById("scanBestFramesBtn").addEventListener("click", scanBestVideoFrames);
  document.getElementById("extractVideoFrameBtn").addEventListener("click", extractCurrentVideoFrame);
  document.getElementById("extractVideoLoopBtn").addEventListener("click", extractCurrentVideoLoop);

  // Logo Reset
  document.getElementById("logoReset").addEventListener("click", (e) => {
    e.preventDefault();
    state.activeQuery = "";
    state.activeCategory = "";
    state.activeModel = "";
    state.minRating = 0;
    state.onlyFavorites = false;
    state.onlyUploaded = false;
    state.deduplicate = false;
    state.similarTo = "";
    searchInput.value = "";
    searchClearBtn.hidden = true;
    favoritesToggleBtn.classList.remove("active");
    if (uploadedToggleBtn) uploadedToggleBtn.classList.remove("active");
    dedupToggleBtn.classList.remove("active");
    ratingChips.querySelectorAll(".chip").forEach((b, i) => b.classList.toggle("active", i === 0));
    scanAndLoadImages();
  });

  document.getElementById("resetFiltersBtn").addEventListener("click", () => {
    document.getElementById("logoReset").click();
  });

  // Uploaded Pictures Filter Button
  if (uploadedToggleBtn) {
    uploadedToggleBtn.addEventListener("click", () => {
      state.onlyUploaded = !state.onlyUploaded;
      uploadedToggleBtn.classList.toggle("active", state.onlyUploaded);
      scanAndLoadImages();
    });
  }

  // Favorites Filter Button
  favoritesToggleBtn.addEventListener("click", () => {
    state.onlyFavorites = !state.onlyFavorites;
    favoritesToggleBtn.classList.toggle("active", state.onlyFavorites);
    scanAndLoadImages();
  });

  // Global Preset Select
  globalPresetSelect.addEventListener("change", () => {
    state.currentPreset = globalPresetSelect.value;
  });

  // Enhance All Visible (4K) Button (with high-speed concurrent batch API)
  const enhanceAllBtn = document.getElementById("enhanceAllBtn");
  enhanceAllBtn.addEventListener("click", async () => {
    enhanceAllBtn.disabled = true;
    const total = state.filteredImages.length;
    enhanceAllBtn.textContent = `⚡ Batch Enhancing ${total} Images to 4K...`;
    try {
      const ids = state.filteredImages.map((it) => it.id);
      const res = await fetch("/api/batch/enhance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_ids: ids,
          preset: state.currentPreset,
        }),
      });
      const data = await res.json();
      ids.forEach((id) => state.enhancedSet.add(id));
      enhanceAllBtn.textContent = `✓ All ${data.result?.enhanced_count || total} Enhanced in 4K!`;
      renderGallery();
    } catch (err) {
      console.error("Batch enhance error:", err);
      enhanceAllBtn.textContent = "Error in Batch";
    }
    setTimeout(() => {
      enhanceAllBtn.textContent = "⚡ Enhance All Visible (4K)";
      enhanceAllBtn.disabled = false;
    }, 2800);
  });

  // Toggle Collapsible Filter Bars Drawer
  const toggleFiltersBtn = document.getElementById("toggleFiltersBtn");
  if (toggleFiltersBtn) {
    toggleFiltersBtn.addEventListener("click", () => {
      setFiltersCollapsed(!state.filtersCollapsed);
    });
  }
  setFiltersCollapsed(state.filtersCollapsed);

  // Multi-Preset Matrix Set Toggle Buttons
  document.querySelectorAll(".matrix-set-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".matrix-set-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.matrixSet = btn.dataset.mset;
      const item = state.filteredImages[state.currentModalIndex];
      renderQuadMatrix(item);
    });
  });

  // Grid Size Toggle
  document.querySelectorAll(".grid-size-toggle .grid-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".grid-size-toggle .grid-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      galleryGrid.classList.toggle("large-grid", btn.dataset.cols === "large");
    });
  });

  // Modal Close, Slideshow, Similar & Format Selection
  modalCloseBtn.addEventListener("click", closeEnhancerModal);
  modalBackdrop.addEventListener("click", closeEnhancerModal);
  document.getElementById("slideshowToggleBtn").addEventListener("click", toggleSlideshow);
  document.getElementById("slideshowIntervalSelect").addEventListener("change", () => {
    if (state.slideshowTimer) startSlideshow();
  });
  document.getElementById("modalFindSimilarBtn").addEventListener("click", () => {
    const item = state.filteredImages[state.currentModalIndex];
    if (item) findSimilarImages(item.id);
  });

  modalFormatSelect.addEventListener("change", () => {
    state.currentFormat = modalFormatSelect.value;
    triggerModalEnhancement(true);
  });

  document.getElementById("modalPrevBtn").addEventListener("click", () => {
    if (state.filteredImages.length === 0) return;
    const prevIdx =
      (state.currentModalIndex - 1 + state.filteredImages.length) % state.filteredImages.length;
    openEnhancerModal(prevIdx);
  });

  document.getElementById("modalNextBtn").addEventListener("click", () => {
    if (state.filteredImages.length === 0) return;
    const nextIdx = (state.currentModalIndex + 1) % state.filteredImages.length;
    openEnhancerModal(nextIdx);
  });

  modalFavBtn.addEventListener("click", () => {
    const item = state.filteredImages[state.currentModalIndex];
    if (item) toggleFavorite(item.id);
  });

  // View Mode Tabs
  document.querySelectorAll(".view-mode-tabs .mode-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      switchViewMode(tab.dataset.mode);
      if (tab.dataset.mode === "slider") {
        setTimeout(() => {
          const rect = splitSliderWrapper.getBoundingClientRect();
          if (rect.width) sliderOrigImg.style.width = `${rect.width}px`;
        }, 50);
      }
    });
  });

  // Parameter Sliders & Selects
  [
    paramEye,
    paramBokeh,
    paramSharpen,
    paramSkin,
    paramContrast,
    paramShadows,
    paramWarmth,
    paramVibrance,
    paramIntensity,
    paramFilmGrain,
    paramVignette,
    paramBloom,
  ]
    .filter(Boolean)
    .forEach((slider) => {
      slider.addEventListener("input", updateSliderLabels);
    });

  [paramCropAspect, paramUpscaleMode, paramLutSelect, paramSkinMask, paramAutoWB, paramMonochrome, paramNeonPop, paramPencilSketch, paramProPencilSketch, paramTraumatized]
    .filter(Boolean)
    .forEach((ctrl) => {
      ctrl.addEventListener("change", () => triggerModalEnhancement(true));
    });

  document.getElementById("resetSlidersBtn").addEventListener("click", () => {
    syncSlidersToPreset(state.currentPreset);
    triggerModalEnhancement(false);
  });

  document.getElementById("applyCustomEnhanceBtn").addEventListener("click", () => {
    triggerModalEnhancement(true);
  });

  document.getElementById("saveCustomPresetBtn").addEventListener("click", saveCustomPreset);

  // Histogram Mode Toggle
  document.querySelectorAll(".hist-mode-btns .hist-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".hist-mode-btns .hist-mode-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.histMode = btn.dataset.hmode;
      drawHistogramCanvas();
    });
  });

  // Star Rating & Metadata Save
  modalStarBar.querySelectorAll(".star-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      renderModalStars(Number(btn.dataset.star));
    });
  });

  saveMetadataBtn.addEventListener("click", saveCurrentImageMetadata);

  // Mobile Bottom Navigation Dock Actions (Pinterest Native App Feel)
  const setMobActive = (btnId) => {
    document.querySelectorAll(".mobile-bottom-nav .mob-nav-item").forEach((b) => {
      b.classList.toggle("active", b.id === btnId);
    });
  };
  document.getElementById("mobNavHome")?.addEventListener("click", () => {
    setMobActive("mobNavHome");
    document.getElementById("logoReset")?.click();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.getElementById("mobNavFilters")?.addEventListener("click", () => {
    setMobActive("mobNavFilters");
    setFiltersCollapsed(!state.filtersCollapsed);
    if (!state.filtersCollapsed) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
  document.getElementById("mobNavUpload")?.addEventListener("click", () => {
    openUploadModal();
  });
  document.getElementById("mobNavVideo")?.addEventListener("click", () => {
    setMobActive("mobNavVideo");
    openVideoExtractorModal();
  });
  document.getElementById("mobNavSaved")?.addEventListener("click", () => {
    setMobActive("mobNavSaved");
    openBoardsModal();
  });
  document.getElementById("mobNavShuffle")?.addEventListener("click", () => {
    setMobActive("mobNavShuffle");
    triggerDynamicShuffle();
  });

  // Keep Split Slider overlay width synced on mobile orientation/viewport resize
  window.addEventListener("resize", () => {
    if (state.currentViewMode === "slider" && splitSliderWrapper) {
      const rect = splitSliderWrapper.getBoundingClientRect();
      if (rect.width) sliderOrigImg.style.width = `${rect.width}px`;
    }
  });

  // Global Keyboard Shortcuts (Boss Key 'B' / 'F9', Modal Navigation)
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") {
      if (e.key === "Enter" && e.target.id === "privacyPinInput") {
        toggleBossKey();
      }
      return;
    }
    if (e.key === "b" || e.key === "B" || e.key === "F9") {
      e.preventDefault();
      toggleBossKey();
      return;
    }
    if (enhancerModal.hidden) return;
    if (e.key === "Escape") closeEnhancerModal();
    if (e.key === "ArrowLeft") document.getElementById("modalPrevBtn").click();
    if (e.key === "ArrowRight") document.getElementById("modalNextBtn").click();
    if (e.key === " ") {
      e.preventDefault();
      toggleSlideshow();
    }
  });
}

// Initialize App
initEvents();
initSplitSlider();
initSyncZoomAndLoupe();
initLiveWatcherSSE();
loadBoards();
scanAndLoadImages();
initRotatingMuse();
