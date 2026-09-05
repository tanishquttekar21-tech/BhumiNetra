// Global BhumiNetra Application State
let selectedPresetId = "maharashtra_712";
let currentRecord = null;
let gisMap = null;
let gisPolygon = null;
let gisMarker = null;
let outcomeChartInstance = null;
let languageChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    initGisMap();
    initCharts();
    loadDatabaseRecords();
    // Auto process initial preset
    runPipelineProcess();
});

// Initialize Leaflet GIS Map
function initGisMap() {
    const mapElement = document.getElementById("gisMap");
    if (!mapElement) return;
    
    gisMap = L.map('gisMap').setView([18.5793, 73.9806], 15);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap | BhumiNetra Spatial Cadastral Engine'
    }).addTo(gisMap);
}

// Select Preset Document Card
function selectPreset(presetId) {
    selectedPresetId = presetId;
    document.querySelectorAll(".preset-card").forEach(c => c.classList.remove("active"));
    const card = document.getElementById(`preset-${presetId}`);
    if (card) card.classList.add("active");
    
    runPipelineProcess();
}

// Handle Custom File Upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);
    
    showLoader(true);
    fetch("/api/process", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        showLoader(false);
        if (data.status === "success") {
            renderPipelineOutput(data.record);
        } else {
            alert("Error processing document: " + data.message);
        }
    })
    .catch(err => {
        showLoader(false);
        console.error(err);
    });
}

// Run BhumiNetra Pipeline Processing
function runPipelineProcess() {
    showLoader(true);
    
    fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset_id: selectedPresetId })
    })
    .then(res => res.json())
    .then(data => {
        showLoader(false);
        if (data.status === "success") {
            renderPipelineOutput(data.record);
        } else {
            alert("Pipeline error: " + data.message);
        }
    })
    .catch(err => {
        showLoader(false);
        console.error(err);
    });
}

function showLoader(isLoading) {
    const spinner = document.getElementById("loaderSpinner");
    const stageImg = document.getElementById("stageImg");
    const ocrCanvasContainer = document.getElementById("ocrCanvasContainer");
    
    if (isLoading) {
        if (spinner) spinner.style.display = "block";
        if (stageImg) stageImg.style.display = "none";
        if (ocrCanvasContainer) ocrCanvasContainer.style.display = "none";
    } else {
        if (spinner) spinner.style.display = "none";
    }
}

// Render complete pipeline output
function renderPipelineOutput(record) {
    currentRecord = record;
    
    // Update Stepper Active State
    updateStepperFlow(record.status);
    
    // 1. OpenCV Stage Switcher
    switchStage("raw");
    
    // 2. Render AI Extracted Fields Table
    renderExtractedFields(record);
    
    // 3. Render Validation Rules Audit
    renderValidationAudit(record.validation);
    
    // 4. Update Decision Engine Banner
    renderDecisionBanner(record);
    
    // 5. Update Human-in-the-Loop Workbench if needed
    if (record.status === "PENDING_HUMAN_REVIEW") {
        setupHitlWorkbench(record);
    } else {
        document.getElementById("hitlWorkbench").style.display = "none";
    }
    
    // 6. Update GIS Map Boundary & Centroid
    updateGisMap(record.gis, record);
    
    // 7. Refresh Analytics Database Table
    loadDatabaseRecords();
}

// Update Stepper Flow UI
function updateStepperFlow(status) {
    document.querySelectorAll(".step-node").forEach(n => n.classList.remove("active", "completed"));
    
    for (let i = 1; i <= 6; i++) {
        const node = document.getElementById(`step-node-${i}`);
        if (node) node.classList.add("completed");
    }
    
    const step7 = document.getElementById("step-node-7");
    if (step7) step7.classList.add("active");
    
    const step8 = document.getElementById("step-node-8");
    if (step8) step8.classList.add("completed");
    
    const step9 = document.getElementById("step-node-9");
    if (step9) step9.classList.add("completed");
}

function jumpToStep(stepNum) {
    document.querySelectorAll(".step-node").forEach(n => n.classList.remove("active"));
    const target = document.getElementById(`step-node-${stepNum}`);
    if (target) target.classList.add("active");
}

// Switch OpenCV Image Processing Stage
function switchStage(stageKey) {
    if (!currentRecord) return;
    
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    const btn = document.getElementById(`tab-${stageKey}`);
    if (btn) btn.classList.add("active");
    
    const stageImg = document.getElementById("stageImg");
    const ocrCanvasContainer = document.getElementById("ocrCanvasContainer");
    const metaBadge = document.getElementById("stageMetadata");
    
    if (stageKey === "ocr") {
        stageImg.style.display = "none";
        ocrCanvasContainer.style.display = "block";
        renderOcrOverlay(currentRecord.ocr, currentRecord.stages.raw);
        if (metaBadge) metaBadge.innerHTML = `OCR Script: ${currentRecord.ocr.script} (${currentRecord.ocr.confidence_percentage}% Conf)`;
    } else {
        ocrCanvasContainer.style.display = "none";
        stageImg.style.display = "block";
        if (currentRecord.stages && currentRecord.stages[stageKey]) {
            stageImg.src = currentRecord.stages[stageKey];
        }
        if (metaBadge) {
            const meta = currentRecord.opencv_meta || {};
            metaBadge.innerHTML = `OpenCV ${stageKey.toUpperCase()} | Skew: ${meta.skew_angle || 0}° | ROIs: ${meta.roi_count || 0}`;
        }
    }
}

// Render Multilingual OCR Overlay
function renderOcrOverlay(ocrData, rawImgB64) {
    const ocrBaseImg = document.getElementById("ocrBaseImg");
    const overlay = document.getElementById("ocrBoxesOverlay");
    
    ocrBaseImg.src = rawImgB64;
    overlay.innerHTML = "";
    
    if (!ocrData || !ocrData.blocks) return;
    
    // Standard reference width/height for bounding box scaling
    const refW = 900;
    const refH = 1200;
    
    ocrData.blocks.forEach(block => {
        const [x, y, w, h] = block.bbox;
        const boxDiv = document.createElement("div");
        boxDiv.className = `ocr-box ${block.conf < 0.85 ? 'low-conf' : ''}`;
        
        boxDiv.style.left = `${(x / refW) * 100}%`;
        boxDiv.style.top = `${(y / refH) * 100}%`;
        boxDiv.style.width = `${(w / refW) * 100}%`;
        boxDiv.style.height = `${(h / refH) * 100}%`;
        
        boxDiv.title = `[${block.lang}] "${block.text}" (Conf: ${(block.conf * 100).toFixed(0)}%)`;
        overlay.appendChild(boxDiv);
    });
}

// Render AI Extracted Fields Table
function renderExtractedFields(record) {
    const container = document.getElementById("fieldExtractionContainer");
    const confBadge = document.getElementById("extractionConfBadge");
    
    if (confBadge) {
        confBadge.innerHTML = `Confidence: ${record.overall_confidence}%`;
        confBadge.style.display = "inline-block";
        confBadge.className = record.overall_confidence >= 85 ? "rule-status-pass" : "rule-status-fail";
    }
    
    const ext = record.extracted || {};
    const owners = record.owners || [];
    
    let ownersHtml = owners.map(o => `
        <div style="font-size: 13px; color: #fff; margin-bottom: 4px;">
            • <b>${o.name}</b> (${o.relation}) - Share: <span style="color: var(--cyan);">${o.share_percent}</span> [Area: ${o.area_allocated}]
        </div>
    `).join("");
    
    container.innerHTML = `
        <table class="field-table">
            <tr>
                <td class="field-label">Document Type</td>
                <td class="field-value">${record.doc_type}</td>
            </tr>
            <tr>
                <td class="field-label">State / District</td>
                <td class="field-value">${record.state} / ${record.district} (Taluka: ${record.taluka}, Village: ${record.village})</td>
            </tr>
            <tr>
                <td class="field-label">Survey / Khasra No.</td>
                <td class="field-value" style="color: var(--primary); font-size: 16px;">${record.survey_no}</td>
            </tr>
            <tr>
                <td class="field-label">Khata Account No.</td>
                <td class="field-value" style="color: var(--cyan); font-size: 16px;">${record.khata_no}</td>
            </tr>
            <tr>
                <td class="field-label">Land Owners & Shares</td>
                <td>${ownersHtml}</td>
            </tr>
            <tr>
                <td class="field-label">Total Land Area</td>
                <td class="field-value">${record.total_area_acres} Acres (${record.total_area_hectares} Hectares)</td>
            </tr>
            <tr>
                <td class="field-label">Land Classification</td>
                <td class="field-value">${ext.land_classification || 'Agricultural'}</td>
            </tr>
            <tr>
                <td class="field-label">Encumbrance / Lien Remarks</td>
                <td class="field-value">${(record.encumbrances && record.encumbrances.length > 0) ? `<span style="color: var(--amber);">${record.encumbrances.join('<br>')}</span>` : '<span style="color: var(--primary);">Clear Title (No Active Liens)</span>'}</td>
            </tr>
            <tr>
                <td class="field-label">Mutation Reference</td>
                <td class="field-value">${record.mutation_ref || 'N/A'}</td>
            </tr>
            <tr>
                <td class="field-label">Digital Hash (SHA256)</td>
                <td class="field-value" style="font-family: monospace; font-size: 11px; color: var(--text-dim);">${record.digital_hash}</td>
            </tr>
        </table>
    `;
}

// Render Validation Audit Log
function renderValidationAudit(valData) {
    const list = document.getElementById("validationRulesList");
    if (!valData || !valData.rules_evaluated) return;
    
    list.innerHTML = valData.rules_evaluated.map(r => `
        <div class="rule-item">
            <div>
                <div style="font-size: 13px; font-weight: 700; color: #fff;">${r.rule_id}: ${r.name}</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">${r.details}</div>
            </div>
            <span class="${r.pass ? 'rule-status-pass' : 'rule-status-fail'}">
                ${r.pass ? '<i class="fa-solid fa-check"></i> PASS' : '<i class="fa-solid fa-triangle-exclamation"></i> FLAG'}
            </span>
        </div>
    `).join("");
}

// Render Decision Engine Banner
function renderDecisionBanner(record) {
    const bannerSection = document.getElementById("decisionBannerSection");
    const banner = document.getElementById("decisionBanner");
    const scoreCircle = document.getElementById("decisionScoreCircle");
    const title = document.getElementById("decisionTitle");
    const subtitle = document.getElementById("decisionSubtitle");
    const actionArea = document.getElementById("decisionActionArea");
    
    bannerSection.style.display = "block";
    scoreCircle.innerHTML = `${record.overall_confidence}%`;
    
    if (record.status === "AUTO_ACCEPTED" || record.status === "MANUALLY_APPROVED") {
        banner.className = "decision-banner auto-accept";
        title.innerHTML = record.status === "MANUALLY_APPROVED" ? "MANUALLY APPROVED RECORD" : "AUTO ACCEPTED RECORD";
        subtitle.innerHTML = `High Confidence score (${record.overall_confidence}%). Verified & stored in GIS spatial cadastral layer.`;
        actionArea.innerHTML = `
            <button class="btn-primary" onclick="downloadCertificate('${record.id}')" style="width: auto;">
                <i class="fa-solid fa-file-contract"></i> Download Audit Certificate
            </button>
        `;
    } else {
        banner.className = "decision-banner human-review";
        title.innerHTML = "HUMAN REVIEW REQUIRED (HITL)";
        subtitle.innerHTML = `Record confidence score (${record.overall_confidence}%) is below 85% threshold or failed rule validation. Routed to Inspector Desk.`;
        actionArea.innerHTML = `
            <button class="btn-primary" onclick="scrollToHitl()" style="width: auto; background: var(--amber); color: #000;">
                <i class="fa-solid fa-user-pen"></i> Open Review Workbench
            </button>
        `;
    }
}

function scrollToHitl() {
    const hitl = document.getElementById("hitlWorkbench");
    if (hitl) {
        hitl.style.display = "block";
        hitl.scrollIntoView({ behavior: 'smooth' });
    }
}

// Setup Human-in-the-Loop Workbench Inputs
function setupHitlWorkbench(record) {
    const hitl = document.getElementById("hitlWorkbench");
    const cropImg = document.getElementById("hitlCropImg");
    
    hitl.style.display = "block";
    if (record.stages && record.stages.roi_overlay) {
        cropImg.src = record.stages.roi_overlay;
    } else if (record.stages && record.stages.raw) {
        cropImg.src = record.stages.raw;
    }
    
    document.getElementById("hitlSurveyNo").value = record.survey_no || "";
    document.getElementById("hitlKhataNo").value = record.khata_no || "";
    const primaryOwner = record.owners && record.owners[0] ? record.owners[0].name : "";
    document.getElementById("hitlOwnerName").value = primaryOwner;
    document.getElementById("hitlComments").value = record.validation.warnings ? record.validation.warnings.join("; ") : "";
}

// Submit Human Review Action
function submitHitlAction(actionStatus) {
    if (!currentRecord) return;
    
    const surveyNo = document.getElementById("hitlSurveyNo").value;
    const khataNo = document.getElementById("hitlKhataNo").value;
    const comments = document.getElementById("hitlComments").value;
    
    fetch("/api/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            record_id: currentRecord.id,
            action: actionStatus,
            comments: comments,
            updated_fields: {
                survey_no: surveyNo,
                khata_no: khataNo
            }
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            alert(`Record ${currentRecord.id} successfully updated to: ${actionStatus}`);
            currentRecord.status = actionStatus;
            currentRecord.survey_no = surveyNo;
            currentRecord.khata_no = khataNo;
            renderDecisionBanner(currentRecord);
            document.getElementById("hitlWorkbench").style.display = "none";
            loadDatabaseRecords();
        } else {
            alert("Review submission failed: " + data.message);
        }
    });
}

// Update Leaflet GIS Spatial Map
function updateGisMap(gisData, record) {
    if (!gisMap || !gisData) return;
    
    const centroid = gisData.centroid || { lat: 18.5793, lng: 73.9806 };
    const polyCoords = gisData.polygon_latlngs || [];
    
    gisMap.setView([centroid.lat, centroid.lng], 16);
    
    // Remove previous polygon/marker
    if (gisPolygon) gisMap.removeLayer(gisPolygon);
    if (gisMarker) gisMap.removeLayer(gisMarker);
    
    // Color code parcel polygon: Green if Accepted, Amber if Review
    const isAccepted = record.status === "AUTO_ACCEPTED" || record.status === "MANUALLY_APPROVED";
    const polygonColor = isAccepted ? "#10b981" : "#f59e0b";
    
    gisPolygon = L.polygon(polyCoords, {
        color: polygonColor,
        fillColor: polygonColor,
        fillOpacity: 0.35,
        weight: 3
    }).addTo(gisMap);
    
    gisMarker = L.marker([centroid.lat, centroid.lng]).addTo(gisMap);
    
    const popupContent = `
        <div style="font-family: sans-serif; padding: 4px;">
            <b style="color: #0f172a; font-size: 14px;">Land Parcel: ${record.survey_no}</b><br>
            <span style="font-size: 12px; color: #475569;">Khata No: ${record.khata_no} | ${record.village}, ${record.district}</span><br>
            <span style="font-size: 12px; font-weight: bold; color: ${polygonColor};">Status: ${record.status}</span><br>
            <span style="font-size: 11px; color: #64748b;">Area: ${record.total_area_acres} Acres</span>
        </div>
    `;
    gisMarker.bindPopup(popupContent).openPopup();
    
    const badge = document.getElementById("gisCoordinatesBadge");
    if (badge) badge.innerHTML = `Lat: ${centroid.lat.toFixed(4)}, Lng: ${centroid.lng.toFixed(4)} (Parcel: ${record.survey_no})`;
}

// Load Database Records & KPI Stats
function loadDatabaseRecords() {
    fetch("/api/records")
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            renderDatabaseTable(data.records);
        }
    });
    
    fetch("/api/stats")
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            updateDashboardKPIs(data.stats);
        }
    });
}

function renderDatabaseTable(records) {
    const tbody = document.getElementById("dbTableBody");
    const countBadge = document.getElementById("navTotalProcessed");
    if (countBadge) countBadge.innerHTML = `${records.length} Records Digitized`;
    
    if (!records || records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-dim);">No land records digitized yet. Execute pipeline above.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = records.map(r => `
        <tr>
            <td style="font-family: monospace; font-size: 12px; color: var(--cyan);">${r.id}</td>
            <td style="font-weight: 600;">${r.doc_type || 'Land Record'}</td>
            <td>${r.state} / ${r.village}</td>
            <td style="color: var(--primary); font-weight: 700;">${r.survey_no}</td>
            <td>${r.khata_no}</td>
            <td>${r.total_area_acres}</td>
            <td><span class="${r.overall_confidence >= 85 ? 'rule-status-pass' : 'rule-status-fail'}">${r.overall_confidence}%</span></td>
            <td><span class="preset-badge ${r.status.includes('ACCEPTED') || r.status.includes('APPROVED') ? 'badge-clean' : 'badge-warning'}">${r.status}</span></td>
            <td style="font-family: monospace; font-size: 10px; color: var(--text-dim);">${(r.digital_hash || '').substring(0, 16)}...</td>
            <td>
                <button onclick="downloadCertificate('${r.id}')" style="background: rgba(6, 182, 212, 0.2); border: 1px solid var(--cyan); color: var(--cyan); padding: 4px 8px; border-radius: 6px; cursor: pointer; font-size: 11px;">
                    <i class="fa-solid fa-download"></i> Cert
                </button>
            </td>
        </tr>
    `).join("");
}

function updateDashboardKPIs(stats) {
    document.getElementById("kpiTotalDocs").innerHTML = stats.total_docs;
    document.getElementById("kpiAutoAcceptRate").innerHTML = `${stats.auto_accept_rate}%`;
    document.getElementById("kpiPendingQueue").innerHTML = stats.pending_review;
    document.getElementById("kpiAvgSpeed").innerHTML = `${stats.avg_processing_time_ms} ms`;
    
    updateCharts(stats);
}

// Initialize Chart.js
function initCharts() {
    const outcomeCtx = document.getElementById("outcomeChart")?.getContext("2d");
    if (outcomeCtx) {
        outcomeChartInstance = new Chart(outcomeCtx, {
            type: 'doughnut',
            data: {
                labels: ['Auto Accepted', 'Pending Review', 'Manually Approved', 'Rejected'],
                datasets: [{
                    data: [1, 0, 0, 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#06b6d4', '#f43f5e']
                }]
            },
            options: {
                plugins: { legend: { labels: { color: '#94a3b8' } } }
            }
        });
    }
    
    const langCtx = document.getElementById("languageChart")?.getContext("2d");
    if (langCtx) {
        languageChartInstance = new Chart(langCtx, {
            type: 'bar',
            data: {
                labels: ['Marathi', 'Kannada', 'Hindi', 'English'],
                datasets: [{
                    label: 'Digitized Records',
                    data: [1, 1, 1, 0],
                    backgroundColor: '#6366f1'
                }]
            },
            options: {
                scales: {
                    x: { ticks: { color: '#94a3b8' } },
                    y: { ticks: { color: '#94a3b8' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

function updateCharts(stats) {
    if (outcomeChartInstance) {
        outcomeChartInstance.data.datasets[0].data = [
            stats.auto_accepted,
            stats.pending_review,
            stats.manually_approved,
            stats.rejected
        ];
        outcomeChartInstance.update();
    }
}

// Simulate Certificate Download
function downloadCertificate(recId) {
    alert(`Generating Official BhumiNetra Digitally Signed Land Record Audit Certificate for Record ID: ${recId}\n\nSHA256 Stamp & QR Verification attached.`);
}
