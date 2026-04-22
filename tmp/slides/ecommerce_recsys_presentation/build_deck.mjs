// Node-oriented editable pro deck builder.
// Run this after editing SLIDES, SOURCES, and layout functions.
// The init script installs a sibling node_modules/@oai/artifact-tool package link
// and package.json with type=module for shell-run eval builders. Run with the
// Node executable from Codex workspace dependencies or the platform-appropriate
// command emitted by the init script.
// Do not use pnpm exec from the repo root or any Node binary whose module
// lookup cannot resolve the builder's sibling node_modules/@oai/artifact-tool.

const fs = await import("node:fs/promises");
const path = await import("node:path");
const { Presentation, PresentationFile } = await import("@oai/artifact-tool");

const W = 1280;
const H = 720;

const DECK_ID = "ecommerce_recsys_presentation";
const OUT_DIR = "C:\\Users\\DELL\\OneDrive\\Desktop\\Mlops_Projec\\ecommerce-recsys\\outputs\\presentation";
const REF_DIR = "C:\\Users\\DELL\\OneDrive\\Desktop\\Mlops_Projec\\ecommerce-recsys\\tmp\\slides\\ecommerce_recsys_presentation\\reference";
const SCRATCH_DIR = path.resolve(process.env.PPTX_SCRATCH_DIR || path.join("tmp", "slides", DECK_ID));
const PREVIEW_DIR = path.join(SCRATCH_DIR, "preview");
const VERIFICATION_DIR = path.join(SCRATCH_DIR, "verification");
const INSPECT_PATH = path.join(SCRATCH_DIR, "inspect.ndjson");
const MAX_RENDER_VERIFY_LOOPS = 3;

const INK = "#101214";
const GRAPHITE = "#30363A";
const MUTED = "#687076";
const PAPER = "#F7F4ED";
const PAPER_96 = "#F7F4EDF5";
const WHITE = "#FFFFFF";
const ACCENT = "#27C47D";
const ACCENT_DARK = "#116B49";
const GOLD = "#D7A83D";
const CORAL = "#E86F5B";
const TRANSPARENT = "#00000000";

const TITLE_FACE = "Arial";
const BODY_FACE = "Arial";
const MONO_FACE = "Consolas";

const FALLBACK_PLATE_DATA_URL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=";

const SOURCES = {
  project: "Local ecommerce-recsys repository documentation, DVC pipeline, MLflow runs, FastAPI, Kafka, and Prometheus configuration.",
};

const SLIDES = [
  {
    kicker: "Ecommerce Recommendation System",
    title: "MLOps Pipeline for Real User Recommendations",
    subtitle: "A recommendation system built from Kaggle interaction data, manual API events, Kafka streaming, MLflow tracking, DVC versioning, FastAPI serving, Prometheus monitoring, and GitHub CI/CD.",
    moment: "Opening line: Real recommendation systems are hard because real user behavior is sparse, skewed, noisy, and constantly changing.",
    notes: "Start strong: We did not want a perfect synthetic dataset. We wanted the harder and more realistic problem: actual user interaction logs where most users do very little, a small set of items receives most activity, and the system must still learn useful top-5 recommendations.",
    sources: ["project"]
  },
  {
    kicker: "Problem",
    title: "Problem Statement",
    subtitle: "Build a production-style recommendation pipeline that can learn from historical ecommerce behavior and accept new user events through an API.",
    cards: [
      ["Goal", "Recommend relevant products for each user from implicit behavior, not from ratings or labels."],
      ["Challenge", "The data has no explicit target column and most users have very few events."],
      ["MLOps", "Track data, models, experiments, serving, streaming, monitoring, and CI/CD as one pipeline."]
    ],
    notes: "Explain that this is not a simple classification project. There is no label like buy or not buy for each item. We infer interest from user events and evaluate whether the model can recover held-out user interactions.",
    sources: ["project"]
  },
  {
    kicker: "Dataset Choice",
    title: "Why Kaggle Instead of Synthetic Data",
    subtitle: "Free ecommerce APIs usually expose product catalogs, but not rich user-item interaction histories.",
    metrics: [
      ["618K+", "Real ecommerce events after import", "Views, carts, purchases"],
      ["140K+", "Users in the interaction data", "Enough for user-level evaluation"],
      ["40K+", "Items in the raw dataset", "Real recommendation candidate space"]
    ],
    notes: "Say this clearly: A product API gives item details but not user behavior. Recommendation needs interactions. Synthetic data may produce nice metrics, but it hides sparsity and skew. Kaggle gave realistic user events, and manual FastAPI input lets us simulate live production events.",
    sources: ["project"]
  },
  {
    kicker: "Inputs",
    title: "Two Input Streams",
    subtitle: "The project combines offline historical data with live manual events from FastAPI.",
    cards: [
      ["Kaggle Data", "Historical user events are imported and normalized into the project schema."],
      ["Manual API", "A user can send events like view, addtocart, or transaction through /event."],
      ["Same Meaning", "Both represent user-item behavior, so the system can treat them as implicit feedback."]
    ],
    notes: "Explain that Kaggle is the training and evaluation base. Manual API events are for online demonstration and monitoring. They are not a replacement for retraining unless we later persist and schedule retraining.",
    sources: ["project"]
  },
  {
    kicker: "Architecture",
    title: "End-to-End Pipeline",
    subtitle: "Offline training and online serving are connected, but they have different responsibilities.",
    cards: [
      ["Offline", "Ingestion -> split -> features -> train -> evaluate -> compare -> track."],
      ["Online", "FastAPI receives requests, serves recommendations, and publishes events to Kafka."],
      ["Monitoring", "Prometheus scrapes API, model, and drift metrics from the /metrics endpoint."]
    ],
    notes: "Use this slide as the map for the rest of the presentation. Offline pipeline creates the model. Online pipeline uses the model and records new behavior. Monitoring checks whether the system is being used and whether drift signals are appearing.",
    sources: ["project"]
  },
  {
    kicker: "Ingestion",
    title: "Data Ingestion",
    subtitle: "Kaggle events are downloaded, cleaned, and saved in the same schema expected by the old project code.",
    metrics: [
      ["view", "Kept as view", "Low-strength signal"],
      ["cart", "Mapped to addtocart", "Medium-strength signal"],
      ["purchase", "Mapped to transaction", "High-strength signal"]
    ],
    notes: "Mention file: src/ingestion/import_kaggle_dataset.py. It imports the Kaggle electronics event dataset and writes data/raw/kaggle_events.csv with timestamp, visitorid, event, itemid, transactionid. This means downstream code can stay consistent.",
    sources: ["project"]
  },
  {
    kicker: "EDA",
    title: "EDA: Skewed User Behavior",
    subtitle: "The event distribution is highly skewed: many users interact once or twice, while a small number interact heavily.",
    cards: [
      ["Skew", "Most users have very low event counts, so profiles are weak."],
      ["Sparsity", "User-item matrix density is about 0.0044 percent."],
      ["Impact", "Top-5 recommendation is difficult when there are tens of thousands of items."]
    ],
    notes: "This is your defense for lower precision and recall. Say: The model is not failing because the code is simple. The task is hard because the data is sparse and skewed. A high score on synthetic balanced data would be less meaningful.",
    sources: ["project"]
  },
  {
    kicker: "Processing",
    title: "Data Processing",
    subtitle: "The raw events are filtered and split so users in test have enough history to evaluate recommendations.",
    cards: [
      ["Clean Schema", "Every event has user id, item id, event type, timestamp, and optional transaction id."],
      ["Minimum History", "Users need at least two unique items for train/test holdout."],
      ["Outputs", "Processed train and test event CSVs are produced by the DVC split stage."]
    ],
    notes: "Mention file: src/features/split_data.py. This step avoids evaluating users where there is no meaningful history. It also keeps the pipeline reproducible through DVC.",
    sources: ["project"]
  },
  {
    kicker: "Split",
    title: "Train-Test Split Without a Target Column",
    subtitle: "Recommendation evaluation uses a user-level time holdout instead of a normal supervised split.",
    metrics: [
      ["latest item", "Held out for testing", "What the model must recover"],
      ["older items", "Used for training", "User history signal"],
      ["top-5", "Recommendations evaluated", "Precision, recall, hit rate"]
    ],
    notes: "Important answer for professor: We do not split X and y because there is no label column. For each eligible user, the latest interacted item becomes the test item. Earlier interactions become training history. Then we recommend top 5 items and check whether the held-out item appears.",
    sources: ["project"]
  },
  {
    kicker: "Features",
    title: "Feature Engineering",
    subtitle: "Implicit feedback is converted into weighted user-item interactions and item-level signals.",
    cards: [
      ["Event Weight", "view = 1, addtocart = 3, transaction = 5."],
      ["Matrix", "Rows are users, columns are items, values are weighted interactions."],
      ["Item Features", "Popularity, trend, event rates, and category-like signals support hybrid scoring."]
    ],
    notes: "Mention file: src/features/build_features.py. Also mention that fixing the sparse matrix orientation was important because implicit models expect user rows and item columns for recommendation.",
    sources: ["project"]
  },
  {
    kicker: "Models",
    title: "Three Models Trained",
    subtitle: "We compared collaborative filtering models that are suitable for implicit user-event data.",
    cards: [
      ["ALS", "Alternating Least Squares learns latent user and item factors from implicit feedback."],
      ["BPR", "Bayesian Personalized Ranking optimizes item ranking from positive interactions."],
      ["LMF", "Logistic Matrix Factorization models interaction probability with latent factors."]
    ],
    notes: "Say: We tried more than one model because recommendation performance depends on the data shape. ALS became the main production model because it performed best on the offline evaluation.",
    sources: ["project"]
  },
  {
    kicker: "Model Detail",
    title: "ALS: Main Production Model",
    subtitle: "ALS factorizes the user-item matrix and works well for large sparse implicit-feedback data.",
    metrics: [
      ["32", "Latent factors", "User/item embedding size"],
      ["10", "Training iterations", "DVC production run"],
      ["alpha 20", "Confidence scaling", "Higher weight for observed events"]
    ],
    notes: "ALS alternates between solving user factors and item factors. It treats missing events as unknown, not negative labels. In this project, the saved model is models/als_model.joblib and it is used by the FastAPI prediction path.",
    sources: ["project"]
  },
  {
    kicker: "Model Detail",
    title: "BPR: Ranking-Based Model",
    subtitle: "BPR learns to rank interacted items above non-interacted items.",
    cards: [
      ["Objective", "Optimizes pairwise ranking instead of rating prediction."],
      ["Strength", "Useful when the main goal is item order in a recommendation list."],
      ["Result", "In this dataset it underperformed ALS because interactions are very sparse."]
    ],
    notes: "BPR is a good model to mention because recommendation is a ranking problem. It did not win here, but testing it shows model comparison and not just one fixed algorithm.",
    sources: ["project"]
  },
  {
    kicker: "Model Detail",
    title: "LMF: Logistic Matrix Factorization",
    subtitle: "LMF estimates interaction likelihood using latent factors and a logistic objective.",
    cards: [
      ["Idea", "Learns user and item vectors similar to ALS, but with a probability-style objective."],
      ["Tuning", "Factors, iterations, regularization, alpha, and learning rate affect ranking quality."],
      ["Use", "Included as a second matrix factorization baseline beyond ALS and BPR."]
    ],
    notes: "If asked about SVD++ or LightFM: SVD++ and LightFM are valid alternatives, but this implementation used implicit ALS, BPR, and LMF because they fit the existing sparse implicit-feedback pipeline and dependencies.",
    sources: ["project"]
  },
  {
    kicker: "Hybrid Ranker",
    title: "Hybrid Recommendation Score",
    subtitle: "The final ranking combines collaborative model scores with item and behavior signals.",
    metrics: [
      ["0.28", "Affinity weight", "Model/user interaction score"],
      ["0.24", "Category-like weight", "Item similarity signal"],
      ["0.16 + 0.12", "Popularity + trend", "Global and recent demand"]
    ],
    notes: "The recommendation score is not only the raw model output. It blends affinity, category/item similarity, popularity, trend, and item similarity. This makes recommendations more stable when the user profile is weak.",
    sources: ["project"]
  },
  {
    kicker: "Evaluation",
    title: "Offline Evaluation",
    subtitle: "The model recommends top-5 items for each test user and checks whether the held-out item appears.",
    cards: [
      ["Precision@5", "Out of 5 recommended items, how many were relevant."],
      ["Recall@5", "Out of the user's held-out relevant items, how many were recovered."],
      ["Hit Rate@5", "Whether at least one held-out item appeared in the top-5."]
    ],
    notes: "For this project each user usually has one held-out test item, so recall@5 and hit_rate@5 can be similar. Precision@5 is lower because only five items are recommended from a huge catalog.",
    sources: ["project"]
  },
  {
    kicker: "Results",
    title: "Testing Results",
    subtitle: "ALS performed best among the three trained models on top-5 offline evaluation.",
    cards: [
      ["ALS", "precision@5 = 0.02868, recall@5 = 0.1434, hit_rate@5 = 0.1434."],
      ["BPR", "precision@5 was around 0.001, much lower than ALS."],
      ["LMF", "precision@5 was around 0.0036, better than BPR but below ALS."]
    ],
    notes: "Add your actual screenshot or result table here if needed. Explain that 0.02868 precision@5 means about 2.868 percent of recommended positions match the held-out item. Recall@5 of 0.1434 means 14.34 percent of users had their held-out item recovered in the top 5.",
    sources: ["project"]
  },
  {
    kicker: "Why Metrics Are Low",
    title: "Why Precision Is Not Very High",
    subtitle: "The result reflects the real difficulty of sparse top-K recommendation, not a clean supervised classification task.",
    metrics: [
      ["140,900", "Training users", "Many users have little history"],
      ["35,682", "Training items", "Large candidate catalog"],
      ["0.0044%", "Matrix density", "Extremely sparse signal"]
    ],
    notes: "This is a key defense slide. Say: We are recommending only 5 items out of more than 35K possible items. Most users have very limited history. So the metric looks lower than classification accuracy, but it is realistic for sparse recommendation.",
    sources: ["project"]
  },
  {
    kicker: "MLflow",
    title: "MLflow Experiment Tracking",
    subtitle: "MLflow records model parameters, metrics, tags, and comparison runs for training and evaluation.",
    cards: [
      ["Runs", "als_hybrid_v1, bpr_hybrid_v1, lmf_hybrid_v1, offline_evaluation, model_comparison."],
      ["Compare", "MLflow compare view helps inspect metrics and parameters side by side."],
      ["Insert Screenshot", "Add MLflow run table, comparison view, or metric details here."]
    ],
    notes: "Explain that MLflow gives experiment history. It records parameters such as model_type, factors, iterations, regularization, alpha, and weights. It also stores metrics like precision_at_k, recall_at_k, and hit_rate_at_k.",
    sources: ["project"]
  },
  {
    kicker: "DVC",
    title: "DVC Data and Pipeline Versioning",
    subtitle: "DVC makes the data and model workflow reproducible without committing large CSV/model files to Git.",
    cards: [
      ["Tracked Data", "data/raw/kaggle_events.csv is referenced through a .dvc file."],
      ["Pipeline", "dvc.yaml defines split, features, train, evaluate, and compare stages."],
      ["Repro", "dvc repro reruns only stages affected by changed inputs or code."]
    ],
    notes: "Mention dvc.yaml and dvc.lock. Git tracks code and pipeline metadata. DVC tracks data/model artifacts. This is important for MLOps because another machine or CI can reproduce the same pipeline.",
    sources: ["project"]
  },
  {
    kicker: "Kafka",
    title: "Kafka Streaming Flow",
    subtitle: "Kafka decouples event producers from consumers so live events can move through the system reliably.",
    metrics: [
      ["Zookeeper", "Coordinates Kafka broker state", "Used by this Kafka image"],
      ["Kafka Broker", "Stores topic messages", "Topic: user-events"],
      ["Consumer", "Reads and applies events", "Updates live interaction state"]
    ],
    notes: "Explain sequence: FastAPI receives /event. The API producer sends a JSON event to Kafka topic user-events. Kafka stores it. A consumer can read events and update live_store. Zookeeper helps the Kafka broker coordinate metadata and broker registration in this setup.",
    sources: ["project"]
  },
  {
    kicker: "FastAPI",
    title: "FastAPI Serving Layer",
    subtitle: "FastAPI exposes model recommendations, trending items, manual event ingestion, health, dashboard, and metrics endpoints.",
    cards: [
      ["/recommend/{user}", "Loads the trained model and returns top-N recommendations."],
      ["/event", "Accepts manual user_id, item_id, event and sends it to Kafka when available."],
      ["/metrics", "Exposes Prometheus metrics for API, model, and drift monitoring."]
    ],
    notes: "Mention /docs for Swagger UI and /dashboard for the custom project result dashboard. Also explain that a 200 response from /event means the API accepted the event; checking Kafka consumer/logs confirms whether it was published and consumed.",
    sources: ["project"]
  },
  {
    kicker: "Monitoring",
    title: "Prometheus and Drift Monitoring",
    subtitle: "Prometheus scrapes FastAPI metrics; drift scripts compute signals and expose them as gauges.",
    cards: [
      ["Data Drift", "KS-style distribution comparison between training data and incoming/production data."],
      ["Model Drift", "Tracks whether model performance falls below the expected baseline."],
      ["Metrics", "data_drift_detected, drifted_features_count, model_drift_detected, precision_at_5."]
    ],
    notes: "Important wording: Prometheus does not create drift by itself. Our code computes drift and exposes metric values. Prometheus collects and graphs them over time from /metrics.",
    sources: ["project"]
  },
  {
    kicker: "Prometheus Graphs",
    title: "Metrics to Show in Prometheus",
    subtitle: "Use these queries during the demo or add screenshots of their graphs.",
    metrics: [
      ["precision_at_5", "Model quality metric", "Offline evaluation exposed to monitoring"],
      ["data_drift_detected", "0 or 1 drift flag", "1 means drift detected"],
      ["drifted_features_count", "Number of drifted features", "Higher means more distribution change"]
    ],
    notes: "Add screenshots of Prometheus graph pages here. If a graph is blank, first open FastAPI /metrics and confirm the metric exists, then check Prometheus Status -> Targets to ensure api:8000 is UP.",
    sources: ["project"]
  },
  {
    kicker: "CI/CD",
    title: "GitHub Actions CI/CD",
    subtitle: "The workflow checks code, reproduces the DVC evaluation path, builds Docker, and publishes the image.",
    cards: [
      ["Python Checks", "Install dependencies, compile src, and run tests if tests exist."],
      ["DVC Pipeline", "Pull/download data and run dvc repro evaluate_model."],
      ["Docker + GHCR", "Build API image and publish on push to main/master."]
    ],
    notes: "Mention workflow file: .github/workflows/ci.yml. Secrets used: KAGGLE_USERNAME and KAGGLE_KEY, unless a DVC remote is configured. The raw dataset is not committed to Git.",
    sources: ["project"]
  },
  {
    kicker: "Demo",
    title: "Project Dashboard and Demo Flow",
    subtitle: "The dashboard brings results, health, trending items, and recommendation examples into one place.",
    cards: [
      ["Dashboard", "Open /dashboard and show model results, API health, trending items, and recommendations."],
      ["Demo Input", "Send a manual /event request from Swagger UI and watch API/Kafka/metrics behavior."],
      ["Closing", "This project shows an end-to-end MLOps loop, not only a notebook model."]
    ],
    notes: "End by summarizing: We used real interaction data, trained and compared three recommenders, tracked experiments with MLflow, versioned the pipeline with DVC, served with FastAPI, streamed live events through Kafka, monitored with Prometheus, and automated checks through GitHub Actions.",
    sources: ["project"]
  }
];

const inspectRecords = [];

async function pathExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  if (!bytes.byteLength) {
    throw new Error(`Image file is empty: ${imagePath}`);
  }
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function normalizeImageConfig(config) {
  if (!config.path) {
    return config;
  }
  const { path: imagePath, ...rest } = config;
  return {
    ...rest,
    blob: await readImageBlob(imagePath),
  };
}

async function ensureDirs() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const obsoleteFinalArtifacts = [
    "preview",
    "verification",
    "inspect.ndjson",
    ["presentation", "proto.json"].join("_"),
    ["quality", "report.json"].join("_"),
  ];
  for (const obsolete of obsoleteFinalArtifacts) {
    await fs.rm(path.join(OUT_DIR, obsolete), { recursive: true, force: true });
  }
  await fs.mkdir(SCRATCH_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(VERIFICATION_DIR, { recursive: true });
}

function lineConfig(fill = TRANSPARENT, width = 0) {
  return { style: "solid", fill, width };
}

function recordShape(slideNo, shape, role, shapeType, x, y, w, h) {
  if (!slideNo) return;
  inspectRecords.push({
    kind: "shape",
    slide: slideNo,
    id: shape?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    shapeType,
    bbox: [x, y, w, h],
  });
}

function addShape(slide, geometry, x, y, w, h, fill = TRANSPARENT, line = TRANSPARENT, lineWidth = 0, meta = {}) {
  const shape = slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineConfig(line, lineWidth),
  });
  recordShape(meta.slideNo, shape, meta.role || geometry, geometry, x, y, w, h);
  return shape;
}

function normalizeText(text) {
  if (Array.isArray(text)) {
    return text.map((item) => String(item ?? "")).join("\n");
  }
  return String(text ?? "");
}

function textLineCount(text) {
  const value = normalizeText(text);
  if (!value.trim()) {
    return 0;
  }
  return Math.max(1, value.split(/\n/).length);
}

function requiredTextHeight(text, fontSize, lineHeight = 1.18, minHeight = 8) {
  const lines = textLineCount(text);
  if (lines === 0) {
    return minHeight;
  }
  return Math.max(minHeight, lines * fontSize * lineHeight);
}

function assertTextFits(text, boxHeight, fontSize, role = "text") {
  const required = requiredTextHeight(text, fontSize);
  const tolerance = Math.max(2, fontSize * 0.08);
  if (normalizeText(text).trim() && boxHeight + tolerance < required) {
    throw new Error(
      `${role} text box is too short: height=${boxHeight.toFixed(1)}, required>=${required.toFixed(1)}, ` +
        `lines=${textLineCount(text)}, fontSize=${fontSize}, text=${JSON.stringify(normalizeText(text).slice(0, 90))}`,
    );
  }
}

function wrapText(text, widthChars) {
  const words = normalizeText(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > widthChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) {
    lines.push(current);
  }
  return lines.join("\n");
}

function recordText(slideNo, shape, role, text, x, y, w, h) {
  const value = normalizeText(text);
  inspectRecords.push({
    kind: "textbox",
    slide: slideNo,
    id: shape?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    text: value,
    textPreview: value.replace(/\n/g, " | ").slice(0, 180),
    textChars: value.length,
    textLines: textLineCount(value),
    bbox: [x, y, w, h],
  });
}

function recordImage(slideNo, image, role, imagePath, x, y, w, h) {
  inspectRecords.push({
    kind: "image",
    slide: slideNo,
    id: image?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    path: imagePath,
    bbox: [x, y, w, h],
  });
}

function applyTextStyle(box, text, size, color, bold, face, align, valign, autoFit, listStyle) {
  box.text = text;
  box.text.fontSize = size;
  box.text.color = color;
  box.text.bold = Boolean(bold);
  box.text.alignment = align;
  box.text.verticalAlignment = valign;
  box.text.typeface = face;
  box.text.insets = { left: 0, right: 0, top: 0, bottom: 0 };
  if (autoFit) {
    box.text.autoFit = autoFit;
  }
  if (listStyle) {
    box.text.style = "list";
  }
}

function addText(
  slide,
  slideNo,
  text,
  x,
  y,
  w,
  h,
  {
    size = 22,
    color = INK,
    bold = false,
    face = BODY_FACE,
    align = "left",
    valign = "top",
    fill = TRANSPARENT,
    line = TRANSPARENT,
    lineWidth = 0,
    autoFit = null,
    listStyle = false,
    checkFit = true,
    role = "text",
  } = {},
) {
  if (!checkFit && textLineCount(text) > 1) {
    throw new Error("checkFit=false is only allowed for single-line headers, footers, and captions.");
  }
  if (checkFit) {
    assertTextFits(text, h, size, role);
  }
  const box = addShape(slide, "rect", x, y, w, h, fill, line, lineWidth);
  applyTextStyle(box, text, size, color, bold, face, align, valign, autoFit, listStyle);
  recordText(slideNo, box, role, text, x, y, w, h);
  return box;
}

async function addImage(slide, slideNo, config, position, role, sourcePath = null) {
  const image = slide.images.add(await normalizeImageConfig(config));
  image.position = position;
  recordImage(slideNo, image, role, sourcePath || config.path || config.uri || "inline-data-url", position.left, position.top, position.width, position.height);
  return image;
}

async function addPlate(slide, slideNo, opacityPanel = false) {
  slide.background.fill = PAPER;
  const platePath = path.join(REF_DIR, `slide-${String(slideNo).padStart(2, "0")}.png`);
  if (await pathExists(platePath)) {
    await addImage(
      slide,
      slideNo,
      { path: platePath, fit: "cover", alt: `Text-free art-direction plate for slide ${slideNo}` },
      { left: 0, top: 0, width: W, height: H },
      "art plate",
      platePath,
    );
  } else {
    await addImage(
      slide,
      slideNo,
      { dataUrl: FALLBACK_PLATE_DATA_URL, fit: "cover", alt: `Fallback blank art plate for slide ${slideNo}` },
      { left: 0, top: 0, width: W, height: H },
      "fallback art plate",
      "fallback-data-url",
    );
  }
  if (opacityPanel) {
    addShape(slide, "rect", 0, 0, W, H, "#FFFFFFB8", TRANSPARENT, 0, { slideNo, role: "plate readability overlay" });
  }
}

function addHeader(slide, slideNo, kicker, idx, total) {
  addText(slide, slideNo, String(kicker || "").toUpperCase(), 64, 34, 430, 24, {
    size: 13,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    checkFit: false,
    role: "header",
  });
  addText(slide, slideNo, `${String(idx).padStart(2, "0")} / ${String(total).padStart(2, "0")}`, 1114, 34, 104, 24, {
    size: 13,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    align: "right",
    checkFit: false,
    role: "header",
  });
  addShape(slide, "rect", 64, 64, 1152, 2, INK, TRANSPARENT, 0, { slideNo, role: "header rule" });
  addShape(slide, "ellipse", 57, 57, 16, 16, ACCENT, INK, 2, { slideNo, role: "header marker" });
}

function addTitleBlock(slide, slideNo, title, subtitle = null, x = 64, y = 86, w = 780, dark = false) {
  const titleColor = dark ? PAPER : INK;
  const bodyColor = dark ? PAPER : GRAPHITE;
  addText(slide, slideNo, title, x, y, w, 142, {
    size: 40,
    color: titleColor,
    bold: true,
    face: TITLE_FACE,
    role: "title",
  });
  if (subtitle) {
    addText(slide, slideNo, subtitle, x + 2, y + 148, Math.min(w, 720), 70, {
      size: 19,
      color: bodyColor,
      face: BODY_FACE,
      role: "subtitle",
    });
  }
}

function addIconBadge(slide, slideNo, x, y, accent = ACCENT, kind = "signal") {
  addShape(slide, "ellipse", x, y, 54, 54, PAPER_96, INK, 1.2, { slideNo, role: "icon badge" });
  if (kind === "flow") {
    addShape(slide, "ellipse", x + 13, y + 18, 10, 10, accent, INK, 1, { slideNo, role: "icon glyph" });
    addShape(slide, "ellipse", x + 31, y + 27, 10, 10, accent, INK, 1, { slideNo, role: "icon glyph" });
    addShape(slide, "rect", x + 22, y + 25, 19, 3, INK, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
  } else if (kind === "layers") {
    addShape(slide, "roundRect", x + 13, y + 15, 26, 13, accent, INK, 1, { slideNo, role: "icon glyph" });
    addShape(slide, "roundRect", x + 18, y + 24, 26, 13, GOLD, INK, 1, { slideNo, role: "icon glyph" });
    addShape(slide, "roundRect", x + 23, y + 33, 20, 10, CORAL, INK, 1, { slideNo, role: "icon glyph" });
  } else {
    addShape(slide, "rect", x + 16, y + 29, 6, 12, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "rect", x + 25, y + 21, 6, 20, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "rect", x + 34, y + 14, 6, 27, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
  }
}

function addCard(slide, slideNo, x, y, w, h, label, body, { accent = ACCENT, fill = PAPER_96, line = INK, iconKind = "signal" } = {}) {
  if (h < 156) {
    throw new Error(`Card is too short for editable pro-deck copy: height=${h.toFixed(1)}, minimum=156.`);
  }
  addShape(slide, "roundRect", x, y, w, h, fill, line, 1.2, { slideNo, role: `card panel: ${label}` });
  addShape(slide, "rect", x, y, 8, h, accent, TRANSPARENT, 0, { slideNo, role: `card accent: ${label}` });
  addIconBadge(slide, slideNo, x + 22, y + 24, accent, iconKind);
  addText(slide, slideNo, label, x + 88, y + 22, w - 108, 28, {
    size: 15,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    role: "card label",
  });
  const wrapped = wrapText(body, Math.max(28, Math.floor(w / 13)));
  const bodyY = y + 86;
  const bodyH = h - (bodyY - y) - 22;
  if (bodyH < 54) {
    throw new Error(`Card body area is too short: height=${bodyH.toFixed(1)}, cardHeight=${h.toFixed(1)}, label=${JSON.stringify(label)}.`);
  }
  addText(slide, slideNo, wrapped, x + 24, bodyY, w - 48, bodyH, {
    size: 17,
    color: INK,
    face: BODY_FACE,
    role: `card body: ${label}`,
  });
}

function addMetricCard(slide, slideNo, x, y, w, h, metric, label, note = null, accent = ACCENT) {
  if (h < 132) {
    throw new Error(`Metric card is too short for editable pro-deck copy: height=${h.toFixed(1)}, minimum=132.`);
  }
  addShape(slide, "roundRect", x, y, w, h, PAPER_96, INK, 1.2, { slideNo, role: `metric panel: ${label}` });
  addShape(slide, "rect", x, y, w, 7, accent, TRANSPARENT, 0, { slideNo, role: `metric accent: ${label}` });
  addText(slide, slideNo, metric, x + 22, y + 24, w - 44, 54, {
    size: 34,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "metric value",
  });
  addText(slide, slideNo, label, x + 24, y + 82, w - 48, 38, {
    size: 16,
    color: GRAPHITE,
    face: BODY_FACE,
    role: "metric label",
  });
  if (note) {
    addText(slide, slideNo, note, x + 24, y + h - 42, w - 48, 22, {
      size: 10,
      color: MUTED,
      face: BODY_FACE,
      role: "metric note",
    });
  }
}

function addNotes(slide, body, sourceKeys) {
  const sourceLines = (sourceKeys || []).map((key) => `- ${SOURCES[key] || key}`).join("\n");
  slide.speakerNotes.setText(`${body || ""}\n\n[Sources]\n${sourceLines}`);
}

function addReferenceCaption(slide, slideNo) {
  addText(
    slide,
    slideNo,
    "Ecommerce Recommender MLOps: Kaggle data, DVC, MLflow, Kafka, FastAPI, Prometheus, and GitHub Actions.",
    64,
    674,
    980,
    22,
    {
      size: 10,
      color: MUTED,
      face: BODY_FACE,
      checkFit: false,
      role: "caption",
    },
  );
}

async function slideCover(presentation) {
  const slideNo = 1;
  const data = SLIDES[0];
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo);
  addShape(slide, "rect", 0, 0, W, H, "#FFFFFFCC", TRANSPARENT, 0, { slideNo, role: "cover contrast overlay" });
  addShape(slide, "rect", 64, 86, 7, 455, ACCENT, TRANSPARENT, 0, { slideNo, role: "cover accent rule" });
  addText(slide, slideNo, data.kicker, 86, 88, 520, 26, {
    size: 13,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    role: "kicker",
  });
  addText(slide, slideNo, data.title, 82, 130, 785, 184, {
    size: 48,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "cover title",
  });
  addText(slide, slideNo, data.subtitle, 86, 326, 610, 86, {
    size: 20,
    color: GRAPHITE,
    face: BODY_FACE,
    role: "cover subtitle",
  });
  addShape(slide, "roundRect", 86, 444, 500, 148, PAPER_96, INK, 1.2, { slideNo, role: "cover moment panel" });
  addText(slide, slideNo, data.moment || "Replace with core idea", 112, 466, 448, 104, {
    size: 18,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "cover moment",
  });
  addReferenceCaption(slide, slideNo);
  addNotes(slide, data.notes, data.sources);
}

async function slideCards(presentation, idx) {
  const data = SLIDES[idx - 1];
  const slide = presentation.slides.add();
  await addPlate(slide, idx);
  addShape(slide, "rect", 0, 0, W, H, "#FFFFFFB8", TRANSPARENT, 0, { slideNo: idx, role: "content contrast overlay" });
  addHeader(slide, idx, data.kicker, idx, SLIDES.length);
  addTitleBlock(slide, idx, data.title, data.subtitle, 64, 86, 760);
  const cards = data.cards?.length
    ? data.cards
    : [
        ["Replace", "Add a specific, sourced point for this slide."],
        ["Author", "Use native PowerPoint chart objects for charts; use deterministic geometry for cards and callouts."],
        ["Verify", "Render previews, inspect them at readable size, and fix actionable layout issues within 3 total render loops."],
      ];
  const cols = Math.min(3, cards.length);
  const cardW = (1114 - (cols - 1) * 24) / cols;
  const iconKinds = ["signal", "flow", "layers"];
  for (let cardIdx = 0; cardIdx < cols; cardIdx += 1) {
    const [label, body] = cards[cardIdx];
    const x = 84 + cardIdx * (cardW + 24);
    addCard(slide, idx, x, 386, cardW, 230, label, body, { iconKind: iconKinds[cardIdx % iconKinds.length] });
  }
  addReferenceCaption(slide, idx);
  addNotes(slide, data.notes, data.sources);
}

async function slideMetrics(presentation, idx) {
  const data = SLIDES[idx - 1];
  const slide = presentation.slides.add();
  await addPlate(slide, idx);
  addShape(slide, "rect", 0, 0, W, H, "#FFFFFFBD", TRANSPARENT, 0, { slideNo: idx, role: "metrics contrast overlay" });
  addHeader(slide, idx, data.kicker, idx, SLIDES.length);
  addTitleBlock(slide, idx, data.title, data.subtitle, 64, 86, 700);
  const metrics = data.metrics || [
    ["00", "Replace metric", "Source"],
    ["00", "Replace metric", "Source"],
    ["00", "Replace metric", "Source"],
  ];
  const accents = [ACCENT, GOLD, CORAL];
  for (let metricIdx = 0; metricIdx < Math.min(3, metrics.length); metricIdx += 1) {
    const [metric, label, note] = metrics[metricIdx];
    addMetricCard(slide, idx, 92 + metricIdx * 370, 404, 330, 174, metric, label, note, accents[metricIdx % accents.length]);
  }
  addReferenceCaption(slide, idx);
  addNotes(slide, data.notes, data.sources);
}

async function createDeck() {
  await ensureDirs();
  if (!SLIDES.length) {
    throw new Error("SLIDES must contain at least one slide.");
  }
  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  await slideCover(presentation);
  for (let idx = 2; idx <= SLIDES.length; idx += 1) {
    const data = SLIDES[idx - 1];
    if (data.metrics) {
      await slideMetrics(presentation, idx);
    } else {
      await slideCards(presentation, idx);
    }
  }
  return presentation;
}

async function saveBlobToFile(blob, filePath) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  await fs.writeFile(filePath, bytes);
}

async function writeInspectArtifact(presentation) {
  inspectRecords.unshift({
    kind: "deck",
    id: DECK_ID,
    slideCount: presentation.slides.count,
    slideSize: { width: W, height: H },
  });
  presentation.slides.items.forEach((slide, index) => {
    inspectRecords.splice(index + 1, 0, {
      kind: "slide",
      slide: index + 1,
      id: slide?.id || `slide-${index + 1}`,
    });
  });
  const lines = inspectRecords.map((record) => JSON.stringify(record)).join("\n") + "\n";
  await fs.writeFile(INSPECT_PATH, lines, "utf8");
}

async function currentRenderLoopCount() {
  const logPath = path.join(VERIFICATION_DIR, "render_verify_loops.ndjson");
  if (!(await pathExists(logPath))) return 0;
  const previous = await fs.readFile(logPath, "utf8");
  return previous.split(/\r?\n/).filter((line) => line.trim()).length;
}

async function nextRenderLoopNumber() {
  return (await currentRenderLoopCount()) + 1;
}

async function appendRenderVerifyLoop(presentation, previewPaths, pptxPath) {
  const logPath = path.join(VERIFICATION_DIR, "render_verify_loops.ndjson");
  const priorCount = await currentRenderLoopCount();
  const record = {
    kind: "render_verify_loop",
    deckId: DECK_ID,
    loop: priorCount + 1,
    maxLoops: MAX_RENDER_VERIFY_LOOPS,
    capReached: priorCount + 1 >= MAX_RENDER_VERIFY_LOOPS,
    timestamp: new Date().toISOString(),
    slideCount: presentation.slides.count,
    previewCount: previewPaths.length,
    previewDir: PREVIEW_DIR,
    inspectPath: INSPECT_PATH,
    pptxPath,
  };
  await fs.appendFile(logPath, JSON.stringify(record) + "\n", "utf8");
  return record;
}

async function verifyAndExport(presentation) {
  await ensureDirs();
  const nextLoop = await nextRenderLoopNumber();
  if (nextLoop > MAX_RENDER_VERIFY_LOOPS) {
    throw new Error(
      `Render/verify/fix loop cap reached: ${MAX_RENDER_VERIFY_LOOPS} total renders are allowed. ` +
        "Do not rerender; note any remaining visual issues in the final response.",
    );
  }
  await writeInspectArtifact(presentation);
  const previewPaths = [];
  for (let idx = 0; idx < presentation.slides.items.length; idx += 1) {
    const slide = presentation.slides.items[idx];
    const preview = await presentation.export({ slide, format: "png", scale: 1 });
    const previewPath = path.join(PREVIEW_DIR, `slide-${String(idx + 1).padStart(2, "0")}.png`);
    await saveBlobToFile(preview, previewPath);
    previewPaths.push(previewPath);
  }
  const pptxBlob = await PresentationFile.exportPptx(presentation);
  const pptxPath = path.join(OUT_DIR, "output.pptx");
  await pptxBlob.save(pptxPath);
  const loopRecord = await appendRenderVerifyLoop(presentation, previewPaths, pptxPath);
  return { pptxPath, loopRecord };
}

const presentation = await createDeck();
const result = await verifyAndExport(presentation);
console.log(result.pptxPath);
