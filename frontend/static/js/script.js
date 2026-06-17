// MapmyIndia API Key Configuration
// Set your official MapmyIndia (Mappls) REST / SDK Key here to render official tiles.
const MAPMYINDIA_API_KEY = "qftitfzpungwqxtuhdmzdhcrjrxbcdbcphvy";

// Global Variables
let currentTab = 'dashboard';
let mainMap, predictorMap;
let mainMapClusterGroup, mainMapHeatLayer;
let zoneJunctionMap = {};
let allIncidents = [];
let charts = {};

// Live Date & Time Clock
function updateClock() {
    const clockEl = document.getElementById('live-clock');
    if (clockEl) {
        const now = new Date();
        clockEl.textContent = now.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }) + ' | ' + now.toLocaleTimeString('en-US', { hour12: false });
    }
}
setInterval(updateClock, 1000);
updateClock();

// Toast Warning for MapmyIndia Key (Inactive since key is provided)
function showMapmyindiaWarning() {
    const warningEl = document.createElement('div');
    warningEl.className = "fixed top-6 right-6 z-[10000] bg-amber-500/20 border-l-4 border-amber-500 p-4 rounded-lg shadow-xl max-w-sm fade-in";
    warningEl.innerHTML = `
        <div class="flex items-start gap-3">
            <span class="text-amber-400 text-lg"><i class="fa-solid fa-circle-exclamation"></i></span>
            <div>
                <h4 class="font-bold text-slate-200 text-sm">MapmyIndia Integration</h4>
                <p class="text-xs text-slate-300 mt-1">To render MapmyIndia tiles, configure your key in <b>static/js/script.js</b>. Falling back to open-source tiles.</p>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" class="text-slate-400 hover:text-slate-200 text-xs font-bold">&times;</button>
        </div>
    `;
    document.body.appendChild(warningEl);
    setTimeout(() => {
        if (warningEl.parentNode) warningEl.remove();
    }, 6000);
}

// Tab Switcher with Leaflet Map Invalidation Fix
function switchTab(tabId) {
    currentTab = tabId;
    
    // Hide all tab panes
    document.querySelectorAll('.tab-pane').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('fade-in');
    });
    
    // Show selected tab pane
    const activePane = document.getElementById(`tab-${tabId}`);
    if (activePane) {
        activePane.classList.remove('hidden');
        activePane.classList.add('fade-in');
    }
    
    // Reset Navigation styles
    const navButtons = [
        { id: 'dashboard', selector: 'nav-dashboard' },
        { id: 'predictor', selector: 'nav-predictor' },
        { id: 'map', selector: 'nav-map' },
        { id: 'analytics', selector: 'nav-analytics' },
        { id: 'recommendations', selector: 'nav-recommendations' },
        { id: 'resources', selector: 'nav-resources' },
        { id: 'alerts', selector: 'nav-alerts' },
        { id: 'export', selector: 'nav-export' }
    ];
    
    navButtons.forEach(btn => {
        const el = document.getElementById(btn.selector);
        if (el) {
            if (btn.id === tabId) {
                el.className = "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-left font-semibold transition-all duration-200 bg-[#1e293b] text-white border-l-4 border-[#2563EB] shadow-md";
            } else {
                el.className = "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-left font-medium transition-all duration-200 text-slate-400 hover:bg-[#1E293B] hover:text-white";
            }
        }
    });

    // Invalidate maps to render tiles correctly after being shown
    if (tabId === 'map' && mainMap) {
        setTimeout(() => {
            mainMap.invalidateSize();
        }, 150);
    }
    if (tabId === 'predictor' && predictorMap) {
        setTimeout(() => {
            predictorMap.invalidateSize();
        }, 150);
    }
}

// ---------------------------------------------------------
// Welcome Intro Animation: Bengaluru Outline -> Roads Illuminate -> AI Scan -> Logo Fade-in
// ---------------------------------------------------------
function runIntroAnimation() {
    const canvas = document.getElementById('intro-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    // Bengaluru Landmarks/Nodes relative to center
    const nodes = [
        { name: "Vidhana Soudha", x: 0, y: 0, scale: 1.0 },
        { name: "Majestic", x: -120, y: -20, scale: 0.8 },
        { name: "Indiranagar", x: 180, y: -30, scale: 0.8 },
        { name: "Hebbal", x: 40, y: -220, scale: 0.9 },
        { name: "Electronic City", x: 140, y: 260, scale: 0.9 },
        { name: "Whitefield", x: 280, y: 60, scale: 0.9 },
        { name: "Kengeri", x: -260, y: 150, scale: 0.8 },
        { name: "Yeshwanthpur", x: -160, y: -150, scale: 0.8 },
        { name: "Bannerghatta", x: -20, y: 280, scale: 0.7 }
    ];
    
    // Generate surrounding border coordinates for Bengaluru boundary shape
    const boundaryPoints = [];
    const numBoundaryPoints = 36;
    for (let i = 0; i < numBoundaryPoints; i++) {
        const angle = (i / numBoundaryPoints) * Math.PI * 2;
        // Wobbly circle representing Bengaluru urban limits
        const radius = 320 + Math.sin(angle * 5) * 40 + Math.cos(angle * 3) * 20;
        boundaryPoints.push({
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius
        });
    }

    const roads = [
        { from: 0, to: 1 }, { from: 0, to: 2 }, { from: 0, to: 3 },
        { from: 0, to: 8 }, { from: 1, to: 7 }, { from: 2, to: 5 },
        { from: 1, to: 6 }, { from: 4, to: 8 }, { from: 3, to: 7 },
        { from: 2, to: 4 }, { from: 6, to: 8 }
    ];
    
    let startTime = Date.now();
    let animationFrameId;
    
    function animate() {
        const elapsed = Date.now() - startTime;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        
        // 1. Bengaluru city outline appears (0 - 1500ms)
        if (elapsed > 100) {
            ctx.save();
            ctx.translate(cx, cy);
            ctx.beginPath();
            
            // Draw city boundary outline
            const limit = Math.min((elapsed - 100) / 1400, 1.0);
            const countToDraw = Math.floor(boundaryPoints.length * limit);
            
            if (countToDraw > 0) {
                ctx.moveTo(boundaryPoints[0].x, boundaryPoints[0].y);
                for (let i = 1; i < countToDraw; i++) {
                    ctx.lineTo(boundaryPoints[i].x, boundaryPoints[i].y);
                }
                if (limit >= 1.0) {
                    ctx.closePath();
                }
                ctx.strokeStyle = "rgba(59, 130, 246, 0.4)";
                ctx.lineWidth = 2;
                ctx.shadowBlur = 10;
                ctx.shadowColor = "#3b82f6";
                ctx.stroke();
            }
            ctx.restore();
        }
        
        // 2. Roads illuminate (1000ms - 2500ms)
        if (elapsed > 1000) {
            ctx.save();
            ctx.translate(cx, cy);
            
            const roadLimit = Math.min((elapsed - 1000) / 1500, 1.0);
            
            // Draw road networks radiating from Soudha
            roads.forEach(road => {
                const p1 = nodes[road.from];
                const p2 = nodes[road.to];
                
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                
                // Interpolate line drawing
                const dx = p1.x + (p2.x - p1.x) * roadLimit;
                const dy = p1.y + (p2.y - p1.y) * roadLimit;
                ctx.lineTo(dx, dy);
                
                // Neon Blue glow for roads matching specified system
                ctx.strokeStyle = "rgba(96, 165, 250, 0.75)";
                ctx.lineWidth = 1.5;
                ctx.shadowBlur = 8;
                ctx.shadowColor = "#60A5FA";
                ctx.stroke();
            });
            
            // Draw Node Points
            nodes.forEach(node => {
                ctx.beginPath();
                ctx.arc(node.x, node.y, 4 * node.scale, 0, Math.PI * 2);
                ctx.fillStyle = "#ffffff";
                ctx.shadowBlur = 12;
                ctx.shadowColor = "#ffffff";
                ctx.fill();
            });
            
            ctx.restore();
        }
        
        // 3. AI Scanning Effect (2000ms - 3200ms)
        if (elapsed > 1800 && elapsed < 3500) {
            const scanLimit = (elapsed - 1800) / 1700; // 0 to 1
            const scanY = canvas.height * scanLimit;
            
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(0, scanY);
            ctx.lineTo(canvas.width, scanY);
            ctx.strokeStyle = "rgba(16, 185, 129, 0.8)"; // Neon green scan bar
            ctx.lineWidth = 4;
            ctx.shadowBlur = 20;
            ctx.shadowColor = "#10b981";
            ctx.stroke();
            ctx.restore();
        }
        
        // 4. DROMETRA logo fades in (2600ms+)
        if (elapsed > 2400) {
            const content = document.getElementById('intro-content');
            if (content) {
                content.classList.remove('opacity-0', 'scale-95');
                content.classList.add('opacity-100', 'scale-100');
            }
        }
        
        // 5. Dashboard loads (4500ms)
        if (elapsed > 4500) {
            const overlay = document.getElementById('welcome-overlay');
            if (overlay) {
                overlay.style.opacity = '0';
                overlay.style.pointerEvents = 'none';
                setTimeout(() => {
                    overlay.classList.add('hidden');
                }, 1000);
            }
            cancelAnimationFrame(animationFrameId);
            return;
        }
        
        animationFrameId = requestAnimationFrame(animate);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

// ---------------------------------------------------------
// Initial Setup on DOM Load
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Run Intro Welcome Animation
    runIntroAnimation();
    
    fetchStats();
    fetchOptions();
    fetchTrafficNews();
    initGeospatialMap();
    initPredictorMap();
    
    // Default form inputs
    const today = new Date().toISOString().split('T')[0];
    const timeNow = new Date().toTimeString().slice(0, 5);
    document.getElementById('input-date').value = today;
    document.getElementById('input-time').value = timeNow;
});

// ---------------------------------------------------------
// API Fetching & Rendering KPI / Tables
// ---------------------------------------------------------
function fetchStats() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            // Populate KPIs
            document.getElementById('kpi-total-events').textContent = data.total_events.toLocaleString();
            document.getElementById('kpi-high-severity').textContent = data.high_priority_events.toLocaleString();
            document.getElementById('kpi-active-incidents').textContent = data.active_incidents.toLocaleString();
            document.getElementById('kpi-road-closures').textContent = data.road_closures.toLocaleString();
            document.getElementById('kpi-avg-impact').textContent = data.average_impact_score + ' / 100';
            document.getElementById('kpi-congestion-risk').textContent = data.congestion_risk_index + '%';
            
            // Populate Traffic Health Index circular gauge & status
            if (data.traffic_health_index !== undefined) {
                document.getElementById('health-gauge-text').textContent = data.traffic_health_index;
                const healthCircle = document.getElementById('health-gauge-circle');
                if (healthCircle) {
                    const offset = 364 - (364 * data.traffic_health_index) / 100;
                    healthCircle.style.strokeDashoffset = offset;
                    healthCircle.setAttribute('stroke', data.traffic_health_color);
                }
                const statusBadge = document.getElementById('health-status-badge');
                if (statusBadge) {
                    statusBadge.textContent = data.traffic_health_status;
                    statusBadge.style.color = data.traffic_health_color;
                    statusBadge.style.borderColor = data.traffic_health_color + '40';
                    statusBadge.style.backgroundColor = data.traffic_health_color + '15';
                }
            }
            
            // Populate Critical Alerts list
            const alertsList = document.getElementById('live-alerts-list');
            const alertsTabFeed = document.getElementById('alerts-tab-feed');
            
            if (alertsList && data.critical_alerts) {
                alertsList.innerHTML = '';
                if (alertsTabFeed) alertsTabFeed.innerHTML = '';
                
                data.critical_alerts.forEach(alert => {
                    const isHigh = alert.severity.includes('HIGH');
                    const bgClass = isHigh ? 'bg-red-950/20 border-red-900/40 text-red-200' : 'bg-amber-950/20 border-amber-900/40 text-amber-200';
                    const badgeClass = isHigh ? 'bg-red-900/50 border-red-700 text-red-300' : 'bg-amber-900/50 border-amber-700 text-amber-300';
                    
                    // Main sidebar panel alert item
                    const div = document.createElement('div');
                    div.className = `flex items-start justify-between border p-3 rounded-lg text-xs ${bgClass}`;
                    div.innerHTML = `
                        <div class="space-y-1">
                            <div class="font-bold uppercase tracking-wider">${alert.severity}</div>
                            <div class="font-semibold text-slate-200 text-sm">${alert.location}</div>
                            <div class="text-slate-400 text-[10px]">${alert.description}</div>
                        </div>
                        <div class="text-right">
                            <span class="border font-bold px-2 py-0.5 rounded text-[10px] ${badgeClass}">${alert.eta}</span>
                        </div>
                    `;
                    alertsList.appendChild(div);
                    
                    // Tab alerts view item
                    if (alertsTabFeed) {
                        const tabDiv = document.createElement('div');
                        const borderCol = isHigh ? 'border-red-500' : 'border-amber-500';
                        const tabBadge = isHigh ? 'bg-red-950 text-red-400' : 'bg-amber-950 text-amber-400';
                        tabDiv.className = `bg-[#0b0f19] border-l-4 ${borderCol} p-4 rounded-r-lg`;
                        tabDiv.innerHTML = `
                            <div class="flex justify-between items-start">
                                <span class="px-2 py-0.5 rounded ${tabBadge} text-[10px] font-bold uppercase tracking-wider">${alert.severity}</span>
                                <span class="text-xs text-slate-500 font-mono">${alert.eta}</span>
                            </div>
                            <h4 class="text-sm font-bold text-white mt-1">${alert.location}</h4>
                            <p class="text-xs text-slate-400 mt-1">${alert.description}</p>
                        `;
                        alertsTabFeed.appendChild(tabDiv);
                    }
                });
            }
            
            // Populate export page statistics
            const exportActive = document.getElementById('export-kpi-active');
            if (exportActive) {
                exportActive.textContent = data.active_incidents.toLocaleString();
            }
            const exportAvg = document.getElementById('export-kpi-avg');
            if (exportAvg) {
                exportAvg.textContent = data.average_impact_score + ' / 100';
            }

            // Cache recent events
            allIncidents = data.recent_incidents;
            renderTable(allIncidents);
            
            // Draw Pie Chart
            renderCausePieChart(data.cause_counts);
            
            // Draw Analytics Charts
            renderAnalyticsCharts(data);
        })
        .catch(err => console.error("Error loading stats:", err));
}

function fetchOptions() {
    fetch('/api/options')
        .then(res => res.json())
        .then(data => {
            zoneJunctionMap = data.zone_junction_map;
            
            // Populate Event Types
            const typeSelect = document.getElementById('input-event-type');
            typeSelect.innerHTML = '';
            data.types.forEach(type => {
                const opt = document.createElement('option');
                opt.value = type;
                opt.textContent = type;
                typeSelect.appendChild(opt);
            });
            
            // Populate Event Causes
            const causeSelect = document.getElementById('input-event-cause');
            causeSelect.innerHTML = '';
            data.causes.forEach(cause => {
                const opt = document.createElement('option');
                opt.value = cause;
                opt.textContent = cause.replace(/_/g, ' ');
                causeSelect.appendChild(opt);
            });
            
            // Populate Municipal Zones
            const zoneSelect = document.getElementById('input-zone');
            zoneSelect.innerHTML = '<option value="" disabled selected>Select Municipal Zone</option>';
            data.zones.forEach(zone => {
                const opt = document.createElement('option');
                opt.value = zone;
                opt.textContent = zone;
                zoneSelect.appendChild(opt);
            });
        })
        .catch(err => console.error("Error loading options:", err));
}

function fetchTrafficNews() {
    fetch('/api/traffic-news')
        .then(res => res.json())
        .then(data => {
            const newsContainer = document.getElementById('traffic-news-list');
            newsContainer.innerHTML = '';
            
            if (!data.success || !data.news || data.news.length === 0) {
                newsContainer.innerHTML = '<div class="text-center py-8 text-slate-500 text-xs">No traffic updates at this time.</div>';
                return;
            }
            
            data.news.forEach(item => {
                const itemEl = document.createElement('div');
                
                let severityBorder = 'border-[#334155]';
                let severityText = 'text-slate-400';
                let severityBg = 'bg-[#1e293b]';
                
                if (item.severity === 'High') {
                    severityBorder = 'border-red-900/50';
                    severityText = 'text-red-400';
                    severityBg = 'bg-red-950/20';
                } else if (item.severity === 'Moderate') {
                    severityBorder = 'border-amber-900/50';
                    severityText = 'text-amber-400';
                    severityBg = 'bg-amber-950/20';
                } else if (item.severity === 'Minor') {
                    severityBorder = 'border-emerald-900/50';
                    severityText = 'text-emerald-400';
                    severityBg = 'bg-emerald-950/20';
                } else if (item.severity === 'Info') {
                    severityBorder = 'border-blue-900/50';
                    severityText = 'text-blue-400';
                    severityBg = 'bg-blue-950/20';
                }
                
                itemEl.className = `flex flex-col p-2.5 rounded-lg border ${severityBorder} ${severityBg} transition-all duration-200 hover:scale-[1.01] hover:border-slate-500/30`;
                itemEl.innerHTML = `
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${severityBg} ${severityText} border ${severityBorder}">
                            ${item.category}
                        </span>
                        <span class="text-[9px] text-slate-400 font-mono">${item.time}</span>
                    </div>
                    <h4 class="text-xs font-semibold text-slate-200 mt-1.5 leading-snug">${item.title}</h4>
                    <p class="text-[10px] text-slate-400 mt-1 leading-normal">${item.details}</p>
                `;
                newsContainer.appendChild(itemEl);
            });
            
            // Format and update date
            const dateObj = new Date(data.date);
            const options = { month: 'short', day: 'numeric', year: 'numeric' };
            document.getElementById('news-date-badge').textContent = dateObj.toLocaleDateString('en-US', options);
        })
        .catch(err => {
            console.error("Error loading traffic news:", err);
            const newsContainer = document.getElementById('traffic-news-list');
            newsContainer.innerHTML = '<div class="text-center py-8 text-red-500 text-xs">Failed to load traffic news.</div>';
        });
}

function updateJunctionDropdown(zone) {
    const juncSelect = document.getElementById('input-junction');
    juncSelect.innerHTML = '<option value="" disabled selected>Select Junction</option>';
    
    const junctions = zoneJunctionMap[zone] || [];
    junctions.forEach(junc => {
        const opt = document.createElement('option');
        opt.value = junc;
        opt.textContent = junc;
        juncSelect.appendChild(opt);
    });
}

// Render Dark Table Rows
function renderTable(incidents) {
    const tbody = document.getElementById('incidents-table-body');
    tbody.innerHTML = '';
    
    if (incidents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">No matching records found</td></tr>`;
        return;
    }
    
    incidents.forEach(row => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-[#1e293b] hover:text-white transition-colors border-b border-[#334155]';
        
        const prioBadge = row.priority.toLowerCase() === 'high' 
            ? `<span class="bg-red-950 border border-red-800 text-red-400 text-xs px-2.5 py-0.5 rounded-full font-bold">High</span>` 
            : `<span class="bg-blue-950 border border-blue-800 text-blue-400 text-xs px-2.5 py-0.5 rounded-full font-medium">Low</span>`;
            
        tr.innerHTML = `
            <td class="px-6 py-4 font-mono text-xs text-slate-400">${row.start_datetime}</td>
            <td class="px-6 py-4 font-semibold text-slate-200 capitalize">${row.event_cause.replace(/_/g, ' ')}</td>
            <td class="px-6 py-4">${prioBadge}</td>
            <td class="px-6 py-4 text-slate-300">${row.corridor}</td>
            <td class="px-6 py-4 text-slate-200 font-semibold">${row.junction}</td>
            <td class="px-6 py-4 font-bold text-[#ffd700]">${row.event_impact_score_100} / 100</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterTable() {
    const q = document.getElementById('table-search').value.toLowerCase();
    const filtered = allIncidents.filter(row => {
        return row.corridor.toLowerCase().includes(q) || 
               row.junction.toLowerCase().includes(q) || 
               row.event_cause.toLowerCase().includes(q);
    });
    renderTable(filtered);
}

// ---------------------------------------------------------
// ApexCharts Visualizations (Gov App Light Theme)
// ---------------------------------------------------------
function renderCausePieChart(causeCounts) {
    const options = {
        series: Object.values(causeCounts),
        labels: Object.keys(causeCounts).map(c => c.replace(/_/g, ' ').toUpperCase()),
        chart: {
            type: 'donut',
            height: '100%',
            background: 'transparent'
        },
        theme: {
            mode: 'dark'
        },
        stroke: {
            colors: ['#1e293b']
        },
        legend: {
            position: 'bottom',
            horizontalAlign: 'center',
            fontFamily: 'Inter',
            fontSize: '11px',
            fontWeight: 500,
            offsetX: 0,
            offsetY: 6,
            markers: {
                width: 10,
                height: 10,
                radius: 12,
                offsetX: -4,
                offsetY: 1
            },
            itemMargin: {
                horizontal: 10,
                vertical: 6
            },
            labels: {
                colors: '#cbd5e1'
            }
        },
        dataLabels: {
            enabled: false
        },
        plotOptions: {
            pie: {
                donut: {
                    size: '60%'
                }
            }
        }
    };
    
    if (charts['cause']) {
        charts['cause'].destroy();
    }
    charts['cause'] = new ApexCharts(document.querySelector("#dashboard-cause-chart"), options);
    charts['cause'].render();
}

function renderAnalyticsCharts(data) {
    // 1. Municipal Zones
    const zoneOptions = {
        series: [{
            name: 'Incidents',
            data: Object.values(data.zone_counts)
        }],
        chart: {
            type: 'bar',
            height: 320,
            background: 'transparent',
            toolbar: { show: false }
        },
        plotOptions: {
            bar: {
                borderRadius: 4,
                horizontal: false,
                columnWidth: '55%',
            }
        },
        xaxis: {
            categories: Object.keys(data.zone_counts),
            labels: { style: { colors: '#94a3b8', fontWeight: 500 } }
        },
        yaxis: {
            labels: { style: { colors: '#94a3b8' } }
        },
        theme: { mode: 'dark' },
        colors: ['#3b82f6'] // Neon Blue
    };
    
    if (charts['zones']) charts['zones'].destroy();
    charts['zones'] = new ApexCharts(document.querySelector("#analytics-zones-chart"), zoneOptions);
    charts['zones'].render();

    // 2. Top Affected Junctions
    const juncOptions = {
        series: [{
            name: 'Incidents',
            data: Object.values(data.junction_counts)
        }],
        chart: {
            type: 'bar',
            height: 320,
            background: 'transparent',
            toolbar: { show: false }
        },
        plotOptions: {
            bar: {
                borderRadius: 4,
                horizontal: true,
            }
        },
        xaxis: {
            categories: Object.keys(data.junction_counts),
            labels: { style: { colors: '#94a3b8', fontWeight: 500 } }
        },
        yaxis: {
            labels: { style: { colors: '#94a3b8' } }
        },
        theme: { mode: 'dark' },
        colors: ['#f59e0b'] // Amber Gold
    };

    if (charts['junctions']) charts['junctions'].destroy();
    charts['junctions'] = new ApexCharts(document.querySelector("#analytics-junctions-chart"), juncOptions);
    charts['junctions'].render();

    // 3. Hourly Trends
    const hourOptions = {
        series: [{
            name: 'Incidents',
            data: Object.values(data.hourly_distribution)
        }],
        chart: {
            type: 'line',
            height: 320,
            background: 'transparent',
            toolbar: { show: false }
        },
        stroke: {
            curve: 'smooth',
            width: 3
        },
        xaxis: {
            categories: Object.keys(data.hourly_distribution).map(h => h + ':00'),
            labels: { style: { colors: '#94a3b8', fontWeight: 500 } }
        },
        yaxis: {
            labels: { style: { colors: '#94a3b8' } }
        },
        theme: { mode: 'dark' },
        colors: ['#a78bfa']
    };

    if (charts['hours']) charts['hours'].destroy();
    charts['hours'] = new ApexCharts(document.querySelector("#analytics-hourly-chart"), hourOptions);
    charts['hours'].render();

    // 4. Weekly Trends
    const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const weeklyOptions = {
        series: [{
            name: 'Incidents',
            data: Object.values(data.weekday_distribution)
        }],
        chart: {
            type: 'bar',
            height: 320,
            background: 'transparent',
            toolbar: { show: false }
        },
        xaxis: {
            categories: weekdayLabels,
            labels: { style: { colors: '#94a3b8', fontWeight: 500 } }
        },
        yaxis: {
            labels: { style: { colors: '#94a3b8' } }
        },
        theme: { mode: 'dark' },
        colors: ['#10b981']
    };

    if (charts['weekly']) charts['weekly'].destroy();
    charts['weekly'] = new ApexCharts(document.querySelector("#analytics-weekly-chart"), weeklyOptions);
    charts['weekly'].render();
}

// ---------------------------------------------------------
// Maps Rendering (CartoDB Dark Matter default & MapmyIndia option)
// ---------------------------------------------------------
function initGeospatialMap() {
    mainMap = L.map('main-leaflet-map').setView([12.9716, 77.5946], 11);
    
    // Default Base Layer: CartoDB Dark Matter (High-contrast command center style)
    const darkMatter = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 20
    }).addTo(mainMap);
    
    let mapplsLayer = null;
    
    // Check if MapmyIndia API Key is configured
    if (MAPMYINDIA_API_KEY && MAPMYINDIA_API_KEY !== "YOUR_MAPMYINDIA_API_KEY") {
        const tileUrl = `https://apis.mappls.com/advancedmaps/v1/${MAPMYINDIA_API_KEY}/vt/maptiles/v2/mapt/{z}/{x}/{y}.png`;
        mapplsLayer = L.tileLayer(tileUrl, {
            attribution: '&copy; MapmyIndia / Mappls',
            maxZoom: 20,
            crossOrigin: false // Prevents browser preflight CORS blocks
        });
        console.log("Registered MapmyIndia (Mappls) Tile Layer Option.");
    } else {
        console.warn("MapmyIndia API Key is not configured.");
    }
    
    // Layer switcher control
    if (mapplsLayer) {
        const baseMaps = {
            "NOVA Command Dark (Default)": darkMatter,
            "MapmyIndia (Mappls)": mapplsLayer
        };
        L.control.layers(baseMaps, null, { collapsed: false, position: 'topright' }).addTo(mainMap);
    }

    fetch('/api/historical-map')
        .then(res => res.json())
        .then(points => {
            // Remove loading overlay
            const overlay = document.getElementById('map-loading-overlay');
            if (overlay) overlay.classList.add('hidden');

            // 1. Create Cluster Group
            mainMapClusterGroup = L.markerClusterGroup();
            
            // 2. Create Heatmap Array
            const heatData = [];
            
            points.forEach(p => {
                heatData.push([p.latitude, p.longitude, 0.5]);
                
                const marker = L.marker([p.latitude, p.longitude])
                    .bindPopup(`
                        <div style="font-family: 'Inter';">
                            <h4 style="font-weight: 700; color: #3b82f6; margin-bottom: 4px;">${p.event_cause.replace(/_/g, ' ').toUpperCase()}</h4>
                            <p style="font-size: 11px; margin: 0; color: #cbd5e1;"><b>Junction:</b> ${p.junction}</p>
                            <p style="font-size: 11px; margin: 0; color: #cbd5e1;"><b>Corridor:</b> ${p.corridor}</p>
                        </div>
                    `);
                mainMapClusterGroup.addLayer(marker);
            });
            
            // Add Heat layer with official government heatmap gradient spec
            mainMapHeatLayer = L.heatLayer(heatData, {
                radius: 15,
                blur: 20,
                maxZoom: 15,
                gradient: {
                    0.2: '#22C55E',
                    0.4: '#FACC15',
                    0.8: '#F97316',
                    1.0: '#DC2626'
                }
            });
            
            // Default to Marker Cluster view
            mainMapClusterGroup.addTo(mainMap);
        })
        .catch(err => console.error("Error loading map telemetry:", err));
}

function toggleMapLayer(layerName) {
    if (!mainMap) return;
    
    if (layerName === 'heat') {
        mainMap.removeLayer(mainMapClusterGroup);
        mainMapHeatLayer.addTo(mainMap);
    } else {
        mainMap.removeLayer(mainMapHeatLayer);
        mainMapClusterGroup.addTo(mainMap);
    }
}

function initPredictorMap() {
    predictorMap = L.map('predictor-map').setView([12.9716, 77.5946], 13);
    
    const darkMatter = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 20
    }).addTo(predictorMap);
    
    if (MAPMYINDIA_API_KEY && MAPMYINDIA_API_KEY !== "YOUR_MAPMYINDIA_API_KEY") {
        const tileUrl = `https://apis.mappls.com/advancedmaps/v1/${MAPMYINDIA_API_KEY}/vt/maptiles/v2/mapt/{z}/{x}/{y}.png`;
        const mapplsLayer = L.tileLayer(tileUrl, {
            attribution: '&copy; MapmyIndia / Mappls',
            maxZoom: 20,
            crossOrigin: false
        });
        
        const baseMaps = {
            "NOVA Command Dark (Default)": darkMatter,
            "MapmyIndia (Mappls)": mapplsLayer
        };
        L.control.layers(baseMaps, null, { collapsed: true, position: 'topright' }).addTo(predictorMap);
    }
}

// ---------------------------------------------------------
// ML Model Prediction Submit Handler & Spread Map Renderer
// ---------------------------------------------------------
let predictorMarker = null;
let spreadMarkers = [];
let spreadLines = [];

function runPrediction(event) {
    event.preventDefault();
    
    // Toggle Loading Panels
    document.getElementById('predictor-placeholder-panel').classList.add('hidden');
    
    const panel = document.getElementById('prediction-result-panel');
    panel.classList.add('opacity-50'); // Show loading state on panel
    panel.classList.remove('hidden');
    
    // Retrieve inputs
    const event_type = document.getElementById('input-event-type').value;
    const event_cause = document.getElementById('input-event-cause').value;
    const priority = document.getElementById('input-priority').value;
    const requires_road_closure = document.getElementById('input-road-closure').value;
    const zone = document.getElementById('input-zone').value;
    const junction = document.getElementById('input-junction').value;
    const date = document.getElementById('input-date').value;
    const time = document.getElementById('input-time').value;
    const duration = document.getElementById('input-duration').value;
    
    const payload = {
        event_type, event_cause, priority, requires_road_closure,
        zone, junction, date, time, duration
    };
    
    fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        panel.classList.remove('opacity-50');
        if (!data.success) {
            alert("Prediction Error: " + data.error);
            return;
        }
        
        const preds = data.predictions;
        
        // 1. Update Gauge Circular Indicator
        const score = preds.impact_score;
        document.getElementById('gauge-text').textContent = score;
        const circle = document.getElementById('gauge-circle');
        const offset = 377 * (1 - score / 100.0);
        circle.style.strokeDashoffset = offset;
        
        let color = "#10b981"; // green
        let label = "Low Impact";
        if (score > 70) {
            color = "#ef4444"; // red
            label = "High Impact";
        } else if (score > 30) {
            color = "#f59e0b"; // orange
            label = "Medium Impact";
        }
        
        circle.setAttribute('stroke', color);
        const catText = document.getElementById('impact-category');
        catText.textContent = label;
        catText.style.color = color;
        
        // 2. Risk Badge & Confidence
        const riskBadge = document.getElementById('risk-badge');
        riskBadge.textContent = preds.risk_level;
        
        // Remove old classes
        riskBadge.className = "font-black text-center tracking-widest text-2xl py-3 rounded-lg border bg-[#111827] border-[#334155]";
        if (preds.risk_level === 'LOW') {
            riskBadge.classList.add('border-emerald-500/50', 'text-emerald-400', 'bg-emerald-950/30');
        } else if (preds.risk_level === 'MEDIUM') {
            riskBadge.classList.add('border-amber-500/50', 'text-amber-400', 'bg-amber-950/30');
        } else if (preds.risk_level === 'HIGH') {
            riskBadge.classList.add('border-red-500/50', 'text-red-400', 'bg-red-950/30');
        } else {
            riskBadge.classList.add('border-red-600', 'text-red-300', 'bg-red-950/70', 'animate-pulse');
        }
        
        // Progress bar
        document.getElementById('risk-confidence-val').textContent = preds.confidence + '%';
        const prog = document.getElementById('risk-progress-bar');
        prog.style.width = preds.confidence + '%';
        prog.style.backgroundColor = preds.risk_color;
        
        // Reliability indicator
        const relInd = document.getElementById('reliability-indicator');
        if (relInd) {
            if (preds.confidence >= 90) {
                relInd.textContent = "Reliable Dispatch (High)";
                relInd.className = "font-semibold text-emerald-400 uppercase";
            } else if (preds.confidence >= 75) {
                relInd.textContent = "Optimized Advisor (Medium)";
                relInd.className = "font-semibold text-amber-400 uppercase";
            } else {
                relInd.textContent = "Standard Advisory (Low)";
                relInd.className = "font-semibold text-red-400 uppercase";
            }
        }
        
        // 3. Explainable drivers
        const expList = document.getElementById('explainable-list');
        expList.innerHTML = '';
        preds.explainable.forEach(driver => {
            const div = document.createElement('div');
            div.className = "flex justify-between items-center bg-[#111827] border border-[#334155] p-2.5 rounded-lg";
            div.innerHTML = `
                <span class="text-xs text-slate-400 font-semibold">${driver.factor}</span>
                <span class="text-xs font-bold text-white">${driver.value}</span>
            `;
            expList.appendChild(div);
        });
        
        // 4. Metadata details
        document.getElementById('meta-corridor').textContent = preds.geofenced_corridor;
        document.getElementById('meta-police-station').textContent = preds.police_station;
        document.getElementById('meta-coords').textContent = `${preds.coordinates.lat.toFixed(5)}, ${preds.coordinates.lon.toFixed(5)}`;
        
        // 5. Resource Allocation AI Display
        document.getElementById('res-officers').textContent = preds.resources.officers;
        document.getElementById('res-barricades').textContent = preds.resources.barricades;
        document.getElementById('res-diversions').textContent = preds.resources.diversions;
        
        // Also update Resource Allocation tab elements
        const tabOfficers = document.getElementById('tab-res-officers');
        if (tabOfficers) tabOfficers.textContent = preds.resources.officers;
        const tabBarricades = document.getElementById('tab-res-barricades');
        if (tabBarricades) tabBarricades.textContent = preds.resources.barricades;
        const tabDiversions = document.getElementById('tab-res-diversions');
        if (tabDiversions) tabDiversions.textContent = preds.resources.diversions;
        
        // 6. Congestion Spread Forecast Display
        document.getElementById('spread-current').textContent = junction;
        const spreadListEl = document.getElementById('spread-predictions-list');
        spreadListEl.innerHTML = '';
        
        preds.spread_predictions.forEach(spread => {
            const div = document.createElement('div');
            div.className = "flex justify-between bg-[#111827]/60 px-3 py-2 rounded border border-[#334155] text-xs";
            div.innerHTML = `
                <span class="text-slate-300"><i class="fa-solid fa-diamond-turn-right text-orange-500 mr-1.5"></i>${spread.road}</span>
                <span class="font-bold text-orange-400">${spread.delay_min} min</span>
            `;
            spreadListEl.appendChild(div);
        });
        
        // 7. Recommendations list
        const recContainer = document.getElementById('police-actions-container');
        recContainer.innerHTML = '';
        preds.recommendations.forEach(rec => {
            const div = document.createElement('div');
            div.className = "rec-item border-l-4";
            div.style.borderLeftColor = preds.risk_color;
            div.innerHTML = `
                <div class="font-bold text-sm text-[#ffd700]">${rec.title}</div>
                <div class="text-xs text-slate-400 mt-1">${rec.desc}</div>
            `;
            recContainer.appendChild(div);
        });
        
        // 8. Predictor & Spread Map Render
        const lat = preds.coordinates.lat;
        const lon = preds.coordinates.lon;
        
        setTimeout(() => {
            predictorMap.invalidateSize();
            predictorMap.setView([lat, lon], 14);
            
            // Clear previous layers
            if (predictorMarker) {
                predictorMap.removeLayer(predictorMarker);
            }
            spreadMarkers.forEach(m => predictorMap.removeLayer(m));
            spreadLines.forEach(l => predictorMap.removeLayer(l));
            spreadMarkers = [];
            spreadLines = [];
            
            // Add primary incident marker
            predictorMarker = L.marker([lat, lon]).addTo(predictorMap)
                .bindPopup(`<b>Primary Bottleneck</b><br>Junction: ${junction}<br>Zone: ${zone}`)
                .openPopup();
                
            // Draw spread nodes & connections
            preds.spread_predictions.forEach((spread, index) => {
                // Warning icon marker for spread junction
                const warningMarker = L.marker([spread.lat, spread.lon]).addTo(predictorMap)
                    .bindPopup(`<b>Spread Target</b><br>Junction: ${spread.road}<br>Est. Delay: ${spread.delay_min} mins`);
                spreadMarkers.push(warningMarker);
                
                // Draw dotted connecting road line with Predicted Spread color spec
                const line = L.polyline([[lat, lon], [spread.lat, spread.lon]], {
                    color: '#06B6D4',
                    dashArray: '8, 12',
                    weight: 4,
                    opacity: 0.85,
                    className: 'animated-polyline'
                }).addTo(predictorMap);
                spreadLines.push(line);
            });
            
        }, 150);
        
    })
    .catch(err => {
        panel.classList.remove('opacity-50');
        console.error("Prediction error:", err);
    });
}

// PDF Generation using jsPDF
function downloadPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Header block
    doc.setFillColor(11, 15, 25);
    doc.rect(0, 0, 210, 40, 'F');
    
    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.setTextColor(255, 255, 255);
    doc.text("DROMETRA COMMAND CENTER", 14, 18);
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(156, 163, 175);
    doc.text("AI-Powered Traffic Event Decision Support Report", 14, 25);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 32);
    
    // 1. Incident Context
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(59, 130, 246);
    doc.text("1. Incident Context Details", 14, 52);
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(50, 50, 50);
    
    const eventType = document.getElementById('input-event-type').value;
    const eventCause = document.getElementById('input-event-cause').value;
    const zone = document.getElementById('input-zone').value;
    const junction = document.getElementById('input-junction').value;
    const dateVal = document.getElementById('input-date').value;
    const timeVal = document.getElementById('input-time').value;
    const duration = document.getElementById('input-duration').value;
    
    doc.text(`• Event Type: ${eventType}`, 16, 60);
    doc.text(`• Trigger Cause: ${eventCause.replace(/_/g, ' ').toUpperCase()}`, 16, 66);
    doc.text(`• Target Zone: ${zone}`, 16, 72);
    doc.text(`• Target Junction: ${junction}`, 16, 78);
    doc.text(`• Scheduled Incident Start: ${dateVal} ${timeVal}`, 16, 84);
    doc.text(`• Simulated Block Duration: ${duration} minutes`, 16, 90);
    
    // 2. AI Model Predictions
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(59, 130, 246);
    doc.text("2. AI Congestion Impact Predictions", 14, 104);
    
    const impactScore = document.getElementById('gauge-text').textContent;
    const riskLevel = document.getElementById('risk-badge').textContent;
    const confidence = document.getElementById('risk-confidence-val').textContent;
    const corridor = document.getElementById('meta-corridor').textContent;
    const police = document.getElementById('meta-police-station').textContent;
    const coords = document.getElementById('meta-coords').textContent;
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`• Calculated Event Impact Score: ${impactScore} / 100`, 16, 112);
    doc.text(`• Congestion Risk Profile: ${riskLevel}`, 16, 118);
    doc.text(`• Model Prediction Confidence: ${confidence}`, 16, 124);
    doc.text(`• Corridor Geofenced Status: ${corridor}`, 16, 130);
    doc.text(`• Patrol Jurisdiction Area: ${police}`, 16, 136);
    doc.text(`• Coordinate Centroid: ${coords}`, 16, 142);
    
    // 3. Resource Allocation
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(59, 130, 246);
    doc.text("3. Recommended Resource Allocation AI", 14, 156);
    
    const officers = document.getElementById('res-officers').textContent;
    const barricades = document.getElementById('res-barricades').textContent;
    const diversions = document.getElementById('res-diversions').textContent;
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`• Required Traffic Police Officers: ${officers}`, 16, 164);
    doc.text(`• Heavy Barricades Needed: ${barricades}`, 16, 170);
    doc.text(`• Active Diversion Signages: ${diversions}`, 16, 176);
    
    // 4. Police Action SOP Recommendations
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(59, 130, 246);
    doc.text("4. AI Recommendation & SOP Directives", 14, 190);
    
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    
    const recsList = document.querySelectorAll('#police-actions-container .rec-item');
    let y = 198;
    recsList.forEach((item, idx) => {
        if (y > 270) {
            doc.addPage();
            y = 20;
        }
        const title = item.querySelector('.font-bold').textContent;
        const desc = item.querySelector('.text-xs').textContent;
        
        doc.setFont("helvetica", "bold");
        doc.text(`${idx + 1}. ${title}`, 16, y);
        doc.setFont("helvetica", "normal");
        doc.text(`   ${desc}`, 16, y + 4);
        y += 10;
    });
    
    doc.save(`drometra_incident_report_${dateVal}_${timeVal.replace(':', '-')}.pdf`);
}
