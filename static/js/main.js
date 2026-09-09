// Global BhumiNetra Application State
let selectedPresetId = "maharashtra_712";
let currentRecord = null;
let gisMap = null;
let gisPolygon = null;
let gisMarker = null;
let outcomeChartInstance = null;
let languageChartInstance = null;
let allDatabaseRecords = [];
let activeStatusFilter = "ALL";

document.addEventListener("DOMContentLoaded", () => {
    initGisMap();
    initCharts();
    initDropzoneDrag();
    loadDatabaseRecords();
    // Auto process initial preset
    runPipelineProcess();
});

// Scroll to Section Helper
function scrollToSection(sectionId) {
    const target = document.getElementById(sectionId);
    if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
    }
}

// Initialize Drag and Drop on Upload Container
function initDropzoneDrag() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('drag-over');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            const input = document.getElementById('fileInput');
            if (input) {
                input.files = files;
                handleFileUpload({ target: { files: files } });
            }
        }
    });
}

// Active Nav link highlight
function setActiveNav(el) {
    document.querySelectorAll(".nav-link").forEach(n => n.classList.remove("active"));
    if (el) el.classList.add("active");
}

// Notifications Modal Toggle
function toggleNotificationsModal() {
    const modal = document.getElementById("notificationsModal");
    if (modal) {
        modal.style.display = modal.style.display === "flex" ? "none" : "flex";
    }
}

// Initialize Leaflet GIS Map
function initGisMap() {
    const mapElement = document.getElementById("gisMap");
    if (!mapElement) return;
    
    gisMap = L.map('gisMap').setView([18.5793, 73.9806], 15);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap | Bhumi Netra Spatial Cadastral Engine'
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

// Confidence Label Helper matching land-verifier-buddy reference
function getConfidenceLabel(confScore) {
    if (confScore >= 90) return `<span class="rule-status-pass" style="font-size: 11px;"><i class="fa-solid fa-circle-check"></i> Read clearly</span>`;
    if (confScore >= 75) return `<span class="status-pill status-queued" style="font-size: 11px;"><i class="fa-solid fa-eye"></i> Fairly clear</span>`;
    return `<span class="rule-status-fail" style="font-size: 11px;"><i class="fa-solid fa-triangle-exclamation"></i> Please check this</span>`;
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
        <div style="font-size: 13px; color: var(--foreground); margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
            <span>• <b>${o.name}</b> (${o.relation}) - Share: <span style="color: var(--primary); font-weight: 700;">${o.share_percent}</span></span>
            <span style="font-size: 11px; color: var(--muted-foreground);">[Area: ${o.area_allocated}]</span>
        </div>
    `).join("");
    
    container.innerHTML = `
        <table class="field-table">
            <tr>
                <td class="field-label">Document Type</td>
                <td class="field-value">${record.doc_type}</td>
                <td style="text-align: right;">${getConfidenceLabel(record.ocr_confidence)}</td>
            </tr>
            <tr>
                <td class="field-label">State / District</td>
                <td class="field-value">${record.state} / ${record.district} (Taluka: ${record.taluka}, Village: ${record.village})</td>
                <td style="text-align: right;">${getConfidenceLabel(95)}</td>
            </tr>
            <tr>
                <td class="field-label">Survey / Khasra No.</td>
                <td class="field-value" style="color: var(--primary); font-size: 15px; font-weight: 700;">${record.survey_no}</td>
                <td style="text-align: right;">${getConfidenceLabel(record.overall_confidence)}</td>
            </tr>
            <tr>
                <td class="field-label">Khata Account No.</td>
                <td class="field-value" style="color: var(--info); font-size: 15px; font-weight: 700;">${record.khata_no}</td>
                <td style="text-align: right;">${getConfidenceLabel(record.overall_confidence)}</td>
            </tr>
            <tr>
                <td class="field-label">Land Owners & Shares</td>
                <td>${ownersHtml}</td>
                <td style="text-align: right;">${getConfidenceLabel(record.validation_score)}</td>
            </tr>
            <tr>
                <td class="field-label">Total Land Area</td>
                <td class="field-value">${record.total_area_acres} Acres (${record.total_area_hectares} Hectares)</td>
                <td style="text-align: right;">${getConfidenceLabel(92)}</td>
            </tr>
            <tr>
                <td class="field-label">Land Classification</td>
                <td class="field-value">${ext.land_classification || 'Agricultural'}</td>
                <td style="text-align: right;">${getConfidenceLabel(98)}</td>
            </tr>
            <tr>
                <td class="field-label">Encumbrance Remarks</td>
                <td class="field-value">${(record.encumbrances && record.encumbrances.length > 0) ? `<span style="color: var(--warning-foreground); font-weight: 600;">${record.encumbrances.join('<br>')}</span>` : '<span style="color: var(--success); font-weight: 600;">Clear Title (No Active Liens)</span>'}</td>
                <td style="text-align: right;">${getConfidenceLabel(90)}</td>
            </tr>
            <tr>
                <td class="field-label">Mutation Reference</td>
                <td class="field-value">${record.mutation_ref || 'N/A'}</td>
                <td style="text-align: right;">${getConfidenceLabel(85)}</td>
            </tr>
            <tr>
                <td class="field-label">Digital Hash (SHA256)</td>
                <td class="field-value" style="font-family: monospace; font-size: 11px; color: var(--muted-foreground);" colspan="2">
                    ${record.digital_hash}
                    <button onclick="copyHash('${record.digital_hash}')" style="background: none; border: none; color: var(--muted-foreground); cursor: pointer; margin-left: 8px;" title="Copy Hash"><i class="fa-solid fa-copy"></i></button>
                </td>
            </tr>
        </table>
    `;
}

function copyHash(hashStr) {
    navigator.clipboard.writeText(hashStr);
    alert("Digital Signature Hash copied to clipboard!");
}

// Render Validation Audit Log
function renderValidationAudit(valData) {
    const list = document.getElementById("validationRulesList");
    if (!valData || !valData.rules_evaluated) return;
    
    list.innerHTML = valData.rules_evaluated.map(r => `
        <div class="rule-item">
            <div>
                <div style="font-size: 13px; font-weight: 700; color: var(--foreground);">${r.rule_id}: ${r.name}</div>
                <div style="font-size: 12px; color: var(--muted-foreground); margin-top: 2px;">${r.details}</div>
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
            <button class="btn-primary" onclick="downloadCertificate('${record.id}')" style="width: auto; padding: 10px 20px;">
                <i class="fa-solid fa-file-contract"></i> Download Audit Certificate
            </button>
        `;
    } else {
        banner.className = "decision-banner human-review";
        title.innerHTML = "HUMAN REVIEW REQUIRED (HITL)";
        subtitle.innerHTML = `Record confidence score (${record.overall_confidence}%) is below 85% threshold or failed rule validation. Routed to Inspector Desk.`;
        actionArea.innerHTML = `
            <button class="btn-primary" onclick="scrollToHitl()" style="width: auto; background: var(--warning); color: #ffffff; padding: 10px 20px;">
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
    const ownerName = document.getElementById("hitlOwnerName").value;
    const comments = document.getElementById("hitlComments").value;
    
    const updatedFields = {
        survey_no: surveyNo,
        survey_khasra_no: surveyNo,
        khata_no: khataNo
    };
    if (ownerName) {
        updatedFields.owner = ownerName;
    }
    
    fetch("/api/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            record_id: currentRecord.id,
            action: actionStatus,
            comments: comments,
            updated_fields: updatedFields
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            fetch(`/api/records/${currentRecord.id}`)
            .then(r => r.json())
            .then(recData => {
                if (recData.status === "success" && recData.record) {
                    renderPipelineOutput(recData.record);
                }
            });
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
    const polygonColor = isAccepted ? "#15803d" : "#d97706";
    
    gisPolygon = L.polygon(polyCoords, {
        color: polygonColor,
        fillColor: polygonColor,
        fillOpacity: 0.3,
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
            allDatabaseRecords = data.records || [];
            applyTableFilters();
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

function filterByStatus(statusKey, btnEl) {
    activeStatusFilter = statusKey;
    document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    if (btnEl) btnEl.classList.add("active");
    applyTableFilters();
}

function filterDatabaseTable() {
    applyTableFilters();
}

function applyTableFilters() {
    const searchVal = (document.getElementById("dbSearchInput")?.value || "").toLowerCase();
    
    let filtered = allDatabaseRecords.filter(r => {
        // 1. Status Filter
        if (activeStatusFilter !== "ALL") {
            if (activeStatusFilter === "PENDING_HUMAN_REVIEW" && r.status !== "PENDING_HUMAN_REVIEW") return false;
            if (activeStatusFilter === "AUTO_ACCEPTED" && r.status !== "AUTO_ACCEPTED") return false;
            if (activeStatusFilter === "MANUALLY_APPROVED" && r.status !== "MANUALLY_APPROVED") return false;
            if (activeStatusFilter === "REJECTED" && r.status !== "REJECTED") return false;
        }
        
        // 2. Search Query Filter
        if (searchVal) {
            const haystack = [
                r.id, r.doc_type, r.state, r.district, r.village, r.survey_no, r.khata_no, r.status
            ].join(" ").toLowerCase();
            return haystack.includes(searchVal);
        }
        
        return true;
    });
    
    renderDatabaseTable(filtered);
}

function loadRecordIntoWorkspace(recId) {
    fetch(`/api/records/${recId}`)
    .then(res => res.json())
    .then(data => {
        if (data.status === "success" && data.record) {
            renderPipelineOutput(data.record);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
}

// Format status pill HTML matching land-verifier-buddy reference
function formatStatusPill(statusStr) {
    if (statusStr === "AUTO_ACCEPTED") {
        return `<span class="status-pill status-verified"><i class="fa-solid fa-circle-check"></i> Auto Accepted</span>`;
    }
    if (statusStr === "MANUALLY_APPROVED") {
        return `<span class="status-pill status-verified"><i class="fa-solid fa-user-check"></i> Approved</span>`;
    }
    if (statusStr === "PENDING_HUMAN_REVIEW") {
        return `<span class="status-pill status-review"><i class="fa-solid fa-triangle-exclamation"></i> Needs Review</span>`;
    }
    if (statusStr === "REJECTED") {
        return `<span class="status-pill status-rejected"><i class="fa-solid fa-circle-xmark"></i> Rejected</span>`;
    }
    return `<span class="status-pill status-queued">${statusStr}</span>`;
}

function renderDatabaseTable(records) {
    const tbody = document.getElementById("dbTableBody");
    
    if (!records || records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--muted-foreground); padding: 24px;">No records match the active search or filter criteria.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = records.map(r => `
        <tr style="cursor: pointer;" onclick="loadRecordIntoWorkspace('${r.id}')">
            <td style="font-family: monospace; font-size: 12px; color: var(--primary); font-weight: 700;">${r.id}</td>
            <td style="font-weight: 600;">${r.doc_type || 'Land Record'}</td>
            <td>${r.state} / ${r.village}</td>
            <td style="color: var(--primary); font-weight: 700;">${r.survey_no}</td>
            <td style="font-weight: 600; color: var(--info);">${r.khata_no}</td>
            <td>${r.total_area_acres}</td>
            <td><span class="${r.overall_confidence >= 85 ? 'rule-status-pass' : 'rule-status-fail'}">${r.overall_confidence}%</span></td>
            <td>${formatStatusPill(r.status)}</td>
            <td style="font-family: monospace; font-size: 11px; color: var(--muted-foreground);">${(r.digital_hash || '').substring(0, 16)}...</td>
            <td onclick="event.stopPropagation();">
                <div style="display: flex; gap: 6px;">
                    <button onclick="downloadCertificate('${r.id}')" title="Download Audit Certificate" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--primary);">
                        <i class="fa-solid fa-file-pdf"></i> Cert
                    </button>
                    <button onclick="viewAuditHistory('${r.id}')" title="View Audit Trail History" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--info);">
                        <i class="fa-solid fa-clock-rotate-left"></i> History
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function viewAuditHistory(recordId) {
    const recId = recordId || (currentRecord ? currentRecord.id : null);
    if (!recId) return;
    
    const modal = document.getElementById("auditModal");
    const title = document.getElementById("auditModalRecId");
    const body = document.getElementById("auditModalBody");
    
    if (title) title.innerText = recId;
    if (body) body.innerHTML = '<p style="color: var(--muted-foreground); padding: 20px; text-align: center;"><i class="fa-solid fa-spinner fa-spin"></i> Loading audit history...</p>';
    if (modal) modal.style.display = "flex";
    
    fetch(`/api/records/${recId}/audit`)
    .then(res => res.json())
    .then(data => {
        if (data.status === "success" && data.audit_logs) {
            if (data.audit_logs.length === 0) {
                body.innerHTML = '<p style="color: var(--muted-foreground); padding: 20px; text-align: center;">No audit logs recorded for this document.</p>';
                return;
            }
            body.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    ${data.audit_logs.map(log => {
                        let detailsHtml = '';
                        if (typeof log.details === 'object' && log.details !== null) {
                            detailsHtml = `<pre style="background: #f8fafc; padding: 8px; border-radius: 6px; font-size: 11px; margin-top: 4px; color: var(--primary); white-space: pre-wrap; border: 1px solid var(--border);">${JSON.stringify(log.details, null, 2)}</pre>`;
                        } else {
                            detailsHtml = `<div style="font-size: 12px; color: var(--muted-foreground); margin-top: 2px;">${log.details || ''}</div>`;
                        }
                        return `
                            <div style="background: #ffffff; border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 700; font-size: 13px; color: var(--primary);"><i class="fa-solid fa-clock-rotate-left"></i> ${log.action}</span>
                                    <span style="font-size: 11px; color: var(--muted-foreground);">${log.timestamp || ''} (By: ${log.performed_by || 'System'})</span>
                                </div>
                                ${detailsHtml}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } else {
            body.innerHTML = '<p style="color: var(--destructive); padding: 20px; text-align: center;">Failed to load audit history.</p>';
        }
    })
    .catch(err => {
        console.error(err);
        body.innerHTML = '<p style="color: var(--destructive); padding: 20px; text-align: center;">Error fetching audit logs.</p>';
    });
}

function closeAuditModal() {
    const modal = document.getElementById("auditModal");
    if (modal) modal.style.display = "none";
}

function updateDashboardKPIs(stats) {
    if (document.getElementById("kpiTotalDocs")) document.getElementById("kpiTotalDocs").innerHTML = stats.total_docs;
    if (document.getElementById("kpiAutoAcceptRate")) document.getElementById("kpiAutoAcceptRate").innerHTML = `${stats.auto_accept_rate}%`;
    if (document.getElementById("kpiPendingQueue")) document.getElementById("kpiPendingQueue").innerHTML = stats.pending_review;
    if (document.getElementById("kpiVerifiedCount")) document.getElementById("kpiVerifiedCount").innerHTML = stats.manually_approved + stats.auto_accepted;
    if (document.getElementById("kpiAvgSpeed")) document.getElementById("kpiAvgSpeed").innerHTML = `${stats.avg_processing_time_ms} ms`;
    
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
                    backgroundColor: ['#16a34a', '#d97706', '#0284c7', '#dc2626']
                }]
            },
            options: {
                plugins: { legend: { labels: { color: '#475569', font: { family: 'DM Sans' } } } }
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
                    backgroundColor: '#15803d'
                }]
            },
            options: {
                scales: {
                    x: { ticks: { color: '#64748b' } },
                    y: { ticks: { color: '#64748b' } }
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

// Download Official Land Record Audit Certificate
function downloadCertificate(recId) {
    if (!recId) return;
    const certUrl = `/api/records/${recId}/certificate/download`;
    window.open(certUrl, '_blank');
}

// ==========================================================================
// Multilingual i18n Switcher (English / Marathi / Hindi)
// Derived from land-verifier-buddy i18n.tsx
// ==========================================================================

let currentLanguage = "en";

const i18nDict = {
    en: {
        brandSubtitle: "AI Land Record Digitization Engine",
        navUpload: '<i class="fa-solid fa-cloud-arrow-up"></i> Upload & Process',
        navDashboard: '<i class="fa-solid fa-chart-line"></i> Dashboard',
        navGis: '<i class="fa-solid fa-globe"></i> GIS Spatial Map',
        navDatabase: '<i class="fa-solid fa-folder-open"></i> Documents DB',
        navAsk: '<i class="fa-solid fa-comments"></i> Ask AI',
        navReview: '<i class="fa-solid fa-user-check"></i> HITL Review',
        aiActive: "AI Engine Active",
        heroTag: "GovTech Platform",
        heroTitle: "Validate & Digitize Land Records in Seconds with AI.",
        heroSubtitle: "Upload Form 7/12 extracts, RTC Pahani records, or Khasra mutation entries. Bhumi Netra pre-processes scans using OpenCV, extracts multilingual text, evaluates validation rules, and flags discrepancies for inspector review.",
        btnUpload: "Upload Scanned Record",
        btnBrowse: "Browse Verified Records",
        feat1Title: "Multilingual OCR",
        feat1Desc: "Devanagari (Marathi/Hindi) & Kannada",
        feat2Title: "Automated Rule Engine",
        feat2Desc: "Flags share & area math errors",
        feat3Title: "Immutable Audit Trail",
        feat3Desc: "SHA-256 digital signature hash",
        dropzoneTitle: "Drop Scanned Records Here",
        dropzoneSubtitle: "Supports PDF, PNG, or JPG formats. Low resolution, rotated, or aged revenue records supported.",
        dropzoneBtn: "Browse Computer",
        presetHeading: "Select Sample Land Record Document",
        kpiTotal: "Total Documents",
        kpiRestored: "Restored Rate",
        kpiPending: "Pending HITL",
        kpiVerified: "Verified Records"
    },
    mr: {
        brandSubtitle: "एआय जमीन नोंद डिझिटायझेशन इंजिन",
        navUpload: '<i class="fa-solid fa-cloud-arrow-up"></i> अपलोड आणि प्रक्रिया',
        navDashboard: '<i class="fa-solid fa-chart-line"></i> डॅशबोर्ड',
        navGis: '<i class="fa-solid fa-globe"></i> जीआयएस नकाशे',
        navDatabase: '<i class="fa-solid fa-folder-open"></i> दस्तऐवज डेटाबेस',
        navAsk: '<i class="fa-solid fa-comments"></i> प्रश्न विचारा',
        navReview: '<i class="fa-solid fa-user-check"></i> तपासणी डेस्क',
        aiActive: "एआय इंजिन सक्रिय",
        heroTag: "गव्हटेक प्लॅटफॉर्म",
        heroTitle: "एआय सह काही सेकंदात जमिनीच्या नोंदी तपासा व डिजिटल करा.",
        heroSubtitle: "७/१२ उतारा, आरटीसी पहाणी नोंद किंवा खसरा नोंदी अपलोड करा. भूमी नेत्रा मल्टिलिंग्वल ओसीआर आणि स्वयंचलित नियमांद्वारे फेरफार तपासून त्रुटी शोधते.",
        btnUpload: "स्कॅन कागदपत्र अपलोड करा",
        btnBrowse: "तपासलेल्या नोंदी पहा",
        feat1Title: "मल्टिलिंग्वल ओसीआर",
        feat1Desc: "देवनागरी (मराठी/हिंदी) आणि कन्नड",
        feat2Title: "स्वयंचलित नियम प्रणाली",
        feat2Desc: "क्षेत्रफळ व हिस्सा त्रुटी शोधते",
        feat3Title: "अखंड ऑडिट नोंद",
        feat3Desc: "SHA-256 डिजिटल स्वाक्षरी हॅश",
        dropzoneTitle: "स्कॅन केलेले कागदपत्र येथे टाका",
        dropzoneSubtitle: "PDF, PNG किंवा JPG फॉरमॅट स्वीकारले जातात. जुने किंवा फिरवलेले कागदपत्रेही चालतात.",
        dropzoneBtn: "संगणकावरून निवडा",
        presetHeading: "नमूना जमीन नोंद दस्तऐवज निवडा",
        kpiTotal: "एकूण दस्तऐवज",
        kpiRestored: "दुरुस्तीचे प्रमाण",
        kpiPending: "तपासणी प्रलंबित",
        kpiVerified: "तपासलेल्या नोंदी"
    },
    hi: {
        brandSubtitle: "एआई भूमि रिकॉर्ड डिजिटलीकरण इंजन",
        navUpload: '<i class="fa-solid fa-cloud-arrow-up"></i> अपलोड और प्रक्रिया',
        navDashboard: '<i class="fa-solid fa-chart-line"></i> डैशबोर्ड',
        navGis: '<i class="fa-solid fa-globe"></i> जीआईएस मानचित्र',
        navDatabase: '<i class="fa-solid fa-folder-open"></i> दस्तावेज़ डेटाबेस',
        navAsk: '<i class="fa-solid fa-comments"></i> सवाल पूछें',
        navReview: '<i class="fa-solid fa-user-check"></i> समीक्षा डेस्क',
        aiActive: "एआई इंजन सक्रिय",
        heroTag: "गवटेक प्लेटफॉर्म",
        heroTitle: "एआई से कुछ ही सेकंड में भूमि रिकॉर्ड की जांच और डिजिटलीकरण करें।",
        heroSubtitle: "फॉर्म 7/12, आरटीसी पहानी या खसरा प्रविष्टियाँ अपलोड करें। भूमि नेत्रा बहुभाषी ओसीआर और नियम इंजन से त्रुटियाँ पहचानता है।",
        btnUpload: "स्कैन दस्तावेज़ अपलोड करें",
        btnBrowse: "सत्यापित रिकॉर्ड देखें",
        feat1Title: "बहुभाषी ओसीआर",
        feat1Desc: "देवनागरी (मराठी/हिंदी) और कन्नड़",
        feat2Title: "स्वचालित नियम इंजन",
        feat2Desc: "क्षेत्रफल और हिस्सेदारी त्रुटियाँ",
        feat3Title: "अपरिवर्तनीय ऑडिट ट्रेल",
        feat3Desc: "SHA-256 डिजिटल हस्ताक्षर हैश",
        dropzoneTitle: "स्कैन किए गए दस्तावेज़ यहाँ खींचें",
        dropzoneSubtitle: "PDF, PNG या JPG प्रारूप समर्थित हैं। पुराने या घूमे हुए रिकॉर्ड भी स्वीकार्य हैं।",
        dropzoneBtn: "कंप्यूटर से चुनें",
        presetHeading: "नमूना भूमि रिकॉर्ड दस्तावेज़ चुनें",
        kpiTotal: "कुल दस्तावेज़",
        kpiRestored: "बहाली दर",
        kpiPending: "लंबित समीक्षा",
        kpiVerified: "सत्यापित रिकॉर्ड"
    }
};

function toggleLangDropdown() {
    const menu = document.getElementById("langDropdownMenu");
    if (menu) menu.style.display = menu.style.display === "flex" ? "none" : "flex";
}

function setLanguage(langCode) {
    if (!i18nDict[langCode]) return;
    currentLanguage = langCode;
    
    // Close dropdown
    const menu = document.getElementById("langDropdownMenu");
    if (menu) menu.style.display = "none";
    
    // Update active checkmarks
    ['en', 'mr', 'hi'].forEach(code => {
        const item = document.getElementById(`lang-item-${code}`);
        if (item) {
            const check = item.querySelector("i");
            if (code === langCode) {
                item.classList.add("active");
                if (check) check.style.display = "inline-block";
            } else {
                item.classList.remove("active");
                if (check) check.style.display = "none";
            }
        }
    });
    
    // Update badge label
    const badgeLabel = document.getElementById("currentLangLabel");
    if (badgeLabel) badgeLabel.innerText = langCode.toUpperCase();
    
    // Update translated text nodes
    const dict = i18nDict[langCode];
    if (document.getElementById("txt-brand-subtitle")) document.getElementById("txt-brand-subtitle").innerText = dict.brandSubtitle;
    if (document.getElementById("txt-nav-upload")) document.getElementById("txt-nav-upload").innerHTML = dict.navUpload;
    if (document.getElementById("txt-nav-dashboard")) document.getElementById("txt-nav-dashboard").innerHTML = dict.navDashboard;
    if (document.getElementById("txt-nav-gis")) document.getElementById("txt-nav-gis").innerHTML = dict.navGis;
    if (document.getElementById("txt-nav-database")) document.getElementById("txt-nav-database").innerHTML = dict.navDatabase;
    if (document.getElementById("txt-nav-ask")) document.getElementById("txt-nav-ask").innerHTML = dict.navAsk;
    if (document.getElementById("txt-nav-review")) document.getElementById("txt-nav-review").innerHTML = dict.navReview;
    if (document.getElementById("txt-ai-active")) document.getElementById("txt-ai-active").innerText = dict.aiActive;
    
    if (document.getElementById("txt-hero-tag")) document.getElementById("txt-hero-tag").innerText = dict.heroTag;
    if (document.getElementById("txt-hero-title")) document.getElementById("txt-hero-title").innerText = dict.heroTitle;
    if (document.getElementById("txt-hero-subtitle")) document.getElementById("txt-hero-subtitle").innerText = dict.heroSubtitle;
    if (document.getElementById("txt-btn-upload")) document.getElementById("txt-btn-upload").innerText = dict.btnUpload;
    if (document.getElementById("txt-btn-browse")) document.getElementById("txt-btn-browse").innerText = dict.btnBrowse;
    
    if (document.getElementById("txt-feat1-title")) document.getElementById("txt-feat1-title").innerText = dict.feat1Title;
    if (document.getElementById("txt-feat1-desc")) document.getElementById("txt-feat1-desc").innerText = dict.feat1Desc;
    if (document.getElementById("txt-feat2-title")) document.getElementById("txt-feat2-title").innerText = dict.feat2Title;
    if (document.getElementById("txt-feat2-desc")) document.getElementById("txt-feat2-desc").innerText = dict.feat2Desc;
    if (document.getElementById("txt-feat3-title")) document.getElementById("txt-feat3-title").innerText = dict.feat3Title;
    if (document.getElementById("txt-feat3-desc")) document.getElementById("txt-feat3-desc").innerText = dict.feat3Desc;
    
    if (document.getElementById("txt-dropzone-title")) document.getElementById("txt-dropzone-title").innerText = dict.dropzoneTitle;
    if (document.getElementById("txt-dropzone-subtitle")) document.getElementById("txt-dropzone-subtitle").innerText = dict.dropzoneSubtitle;
    if (document.getElementById("txt-dropzone-btn")) document.getElementById("txt-dropzone-btn").innerText = dict.dropzoneBtn;
    if (document.getElementById("txt-preset-heading")) document.getElementById("txt-preset-heading").innerText = dict.presetHeading;
    
    if (document.getElementById("txt-kpi-total")) document.getElementById("txt-kpi-total").innerText = dict.kpiTotal;
    if (document.getElementById("txt-kpi-restored")) document.getElementById("txt-kpi-restored").innerText = dict.kpiRestored;
    if (document.getElementById("txt-kpi-pending")) document.getElementById("txt-kpi-pending").innerText = dict.kpiPending;
    if (document.getElementById("txt-kpi-verified")) document.getElementById("txt-kpi-verified").innerText = dict.kpiVerified;
}

// ==========================================================================
// Ask Bhumi Netra AI Assistant Query Engine
// Inspired by land-verifier-buddy ask.tsx
// ==========================================================================

function handleAiChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("aiChatInput");
    if (!input || !input.value.trim()) return;
    const q = input.value.trim();
    input.value = "";
    sendAiChatQuery(q);
}

function sendAiChatQuery(questionText) {
    const chatBox = document.getElementById("aiChatBox");
    if (!chatBox) return;
    
    // 1. Append User Question Bubble
    const userDiv = document.createElement("div");
    userDiv.className = "chat-bubble-user";
    userDiv.innerText = questionText;
    chatBox.appendChild(userDiv);
    
    // 2. Compute Smart Answer based on allDatabaseRecords
    const ans = computeAiAnswer(questionText, allDatabaseRecords);
    
    // 3. Append App Answer Bubble
    setTimeout(() => {
        const appDiv = document.createElement("div");
        appDiv.className = "chat-bubble-app";
        appDiv.innerHTML = `🤖 ${ans}`;
        chatBox.appendChild(appDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }, 250);
    
    chatBox.scrollTop = chatBox.scrollHeight;
}

function computeAiAnswer(qText, docs) {
    const q = qText.toLowerCase();
    
    // District query
    const foundDoc = docs.find(d => d.district && q.includes(d.district.toLowerCase()));
    if (foundDoc) {
        const dist = foundDoc.district;
        const inDist = docs.filter(d => d.district === dist);
        const verified = inDist.filter(d => d.status === "AUTO_ACCEPTED" || d.status === "MANUALLY_APPROVED").length;
        return `<strong>${dist}</strong> district has <strong>${inDist.length}</strong> record(s): ${verified} verified, ${inDist.length - verified} in review queue. Records: ${inDist.map(d => `${d.id} (${d.survey_no})`).join(", ")}.`;
    }
    
    // Verified query
    if (q.includes("verified") || q.includes("accepted") || q.includes("done") || q.includes("approved")) {
        const verified = docs.filter(d => d.status === "AUTO_ACCEPTED" || d.status === "MANUALLY_APPROVED");
        return verified.length > 0 
            ? `Found <strong>${verified.length}</strong> verified land record(s): ${verified.map(d => `${d.id} (Survey ${d.survey_no}, ${d.village})`).join("; ")}.`
            : "No verified land records in database yet.";
    }
    
    // Pending / Review query
    if (q.includes("pending") || q.includes("check") || q.includes("review") || q.includes("hitl")) {
        const pending = docs.filter(d => d.status === "PENDING_HUMAN_REVIEW");
        return pending.length > 0
            ? `There are <strong>${pending.length}</strong> record(s) queued for human inspection: ${pending.map(d => `${d.id} (${d.doc_type}, ${d.district})`).join("; ")}.`
            : "All land records have been verified! Zero pending reviews.";
    }
    
    // Accuracy / Confidence query
    if (q.includes("accuracy") || q.includes("confidence") || q.includes("score")) {
        const avg = Math.round(docs.reduce((sum, d) => sum + (d.overall_confidence || 0), 0) / (docs.length || 1));
        return `The average OCR & AI Extraction confidence score across digitized records is <strong>${avg}%</strong>. Records scoring below 85% are automatically routed to the HITL inspector workbench.`;
    }
    
    // Specific Owner or Survey search
    const words = q.replace(/[?.,]/g, "").split(/\s+/).filter(w => w.length > 2);
    const hits = docs.filter(doc => {
        const ownerNames = (doc.owners || []).map(o => o.name).join(" ");
        const haystack = [doc.id, doc.doc_type, doc.district, doc.village, doc.survey_no, doc.khata_no, ownerNames].join(" ").toLowerCase();
        return words.some(w => haystack.includes(w));
    });
    
    if (hits.length > 0) {
        return `I found <strong>${hits.length}</strong> matching land record(s): ${hits.map(d => `${d.id} — Survey No. <b>${d.survey_no}</b> (Khata: ${d.khata_no}, ${d.village}) [Status: ${d.status}]`).join("; ")}.`;
    }
    
    return "I couldn't find a direct match. Try asking about a specific survey number (e.g. 142/3B), owner name, village, district, or asking 'How many records are verified?'.";
}

