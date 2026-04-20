document.addEventListener('DOMContentLoaded', () => {
    const mainImage = document.getElementById('main-satellite-image');
    const imageTimestamp = document.getElementById('image-timestamp');
    const lastUpdateNav = document.getElementById('last-update');
    const thumbnailsList = document.getElementById('thumbnails-list');
    const loader = document.getElementById('image-loader');

    // Weather elements
    const currentTemp = document.getElementById('current-temp');
    const currentHum = document.getElementById('current-hum');
    const currentPress = document.getElementById('current-press');
    const currentWind = document.getElementById('current-wind');
    const currentDew = document.getElementById('current-dew'); // NEW
    const localClock = document.getElementById('local-clock'); // NEW

    // Humanized elements
    const pressTrendIcon = document.getElementById('press-trend-icon');
    const pressLabel = document.getElementById('press-label');
    const windLabel = document.getElementById('wind-label');

    // Alert elements
    const alertCard = document.getElementById('nowcast-alert-card');
    const alertSemaphore = document.getElementById('alert-semaphore');
    const alertStatus = document.getElementById('alert-status');
    const alertCondition = document.getElementById('alert-condition');
    const proj1h = document.getElementById('proj-1h');
    const proj2h = document.getElementById('proj-2h');

    let animationInterval = null;
    let isAnimating = false;
    let imageSequence = [];
    let currentFrame = 0;
    let currentProduct = 'geocolor'; // Default GOES product
    const btnAnimate = document.getElementById('btn-animate');
    const productTabs = document.querySelectorAll('.prod-tab');
    const docLink = document.getElementById('product-doc-link');

    // Advanced Predictive Charts
    Chart.register(window.ChartDataLabels); // Register plugin
    let smnPredChartObj = null;
    let owmPredChartObj = null;
    let smnPredDataCache = null;
    let owmPredDataCache = null;
    let currentSmnTab = 'temp';
    let currentOwmTab = 'temp';
    let currentSelectedSmnDay = null; // Format YYYY-MM-DD (local)
    let currentSelectedOwmDay = null; // Format YYYY-MM-DD (local)
    
    // Wire predictive tabs
    document.querySelectorAll('.predictive-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const source = e.target.dataset.source;
            const type = e.target.dataset.type;
            
            const peers = e.target.parentElement.querySelectorAll('.tab-btn');
            peers.forEach(p => p.classList.remove('active'));
            e.target.classList.add('active');

            if (source === 'smn') {
                currentSmnTab = type;
                if (smnPredDataCache) updatePredChart(smnPredChartObj, smnPredDataCache, type, currentSelectedSmnDay);
            } else if (source === 'owm') {
                currentOwmTab = type;
                if (owmPredDataCache) updatePredChart(owmPredChartObj, owmPredDataCache, type, currentSelectedOwmDay);
            }
        });
    });

    // Provider Switching Logic
    function switchProviderTab(provider) {
        const btn = document.querySelector(`.provider-tabs .tab-btn[data-provider="${provider}"]`);
        if (!btn) return;
        
        const peers = btn.parentElement.querySelectorAll('.tab-btn');
        peers.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');

        if (provider === 'smn') {
            document.getElementById('smn-forecast-content').classList.remove('hidden');
            document.getElementById('owm-forecast-content').classList.add('hidden');
            if (smnPredChartObj) smnPredChartObj.update();
        } else {
            document.getElementById('owm-forecast-content').classList.remove('hidden');
            document.getElementById('smn-forecast-content').classList.add('hidden');
            if (owmPredChartObj) owmPredChartObj.update();
        }
    }

    // Wire provider tabs
    document.querySelectorAll('.provider-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchProviderTab(e.target.dataset.provider);
        });
    });

    const productDocs = {
        'geocolor': 'https://www.star.nesdis.noaa.gov/GOES/documents/QuickGuide_CIRA_Geocolor_20171019.pdf',
        'airmass': 'https://www.star.nesdis.noaa.gov/GOES/documents/QuickGuide_GOESR_AirMassRGB_final.pdf',
        'sandwich': 'https://www.star.nesdis.noaa.gov/GOES/documents/SandwichProduct.pdf'
    };

    async function fetchGalleryData() {
        try {
            // 1. Fetch images from Nginx JSON autoindex (Using subfolders)
            const response = await fetch(`/goes/${currentProduct}/`);
            if (!response.ok) throw new Error(`No se pudo obtener la lista de imágenes para ${currentProduct}`);
            
            const files = await response.json();
            
            // Filter only PNG files and sort by name (timestamp) descending
            const images = files
                .filter(file => file.type === 'file' && file.name.endsWith('.png'))
                .sort((a, b) => b.name.localeCompare(a.name));

            if (images.length > 0) {
                // Store last 10 but in chronological order (oldest first)
                imageSequence = images.slice(0, 10).reverse(); 
                
                if (!isAnimating) {
                    updateGalleryUI(images[0]);
                }
            } else {
                imageTimestamp.textContent = "No hay imágenes disponibles";
            }

        } catch (error) {
            console.error('Error fetching gallery:', error);
            lastUpdateNav.textContent = "Error al actualizar";
        }
    }

    async function fetchWeatherData() {
        try {
            const response = await fetch('/goes/latest_weather.json');
            if (response.ok) {
                const data = await response.json();
                updateWeatherUI(data);
            }
        } catch (error) {
            console.warn('Weather data not available yet');
        }
        
        // 3. Fetch Prediction data (Nowcast)
        fetchPredictionData();
        
        // 4. Fetch Index data (Zambretti/DewPoint)
        fetchIndexData();
        
        // 5. Fetch Extended Forecasts
        fetchExtendedForecasts();
    }

    async function fetchPredictionData() {
        try {
            const response = await fetch('/goes/latest_predictions.json');
            if (response.ok) {
                const data = await response.json();
                updateAlertUI(data);
            }
        } catch (e) { console.warn("Predictions not ready"); }
    }

    async function fetchIndexData() {
        try {
            const response = await fetch('/goes/latest_indexes.json');
            if (response.ok) {
                const data = await response.json();
                updateIndexUI(data);
            }
        } catch (e) { console.warn("Indexes not ready"); }
    }

    function updateAlertUI(data) {
        if (!data || !alertStatus) return;
        
        alertCard.classList.remove('hidden');
        
        // Map severity to text and color
        const levels = {
            0: { txt: "NORMAL", color: "level-0" },
            1: { txt: "NORMAL", color: "level-1" },
            2: { txt: "ATENCIÓN", color: "level-2" },
            3: { txt: "ALERTA", color: "level-3" },
            4: { txt: "EXTREMO", color: "level-4" }
        };
        
        const mainLevel = data.severity_2h || 0;
        const config = levels[mainLevel] || levels[0];
        
        alertStatus.textContent = config.txt;
        alertCondition.textContent = data.condition_2h || "Sin cambios significativos";
        
        // Reset and set semaphore color
        alertSemaphore.className = 'semaphore ' + config.color;
        
        proj1h.textContent = data.condition_1h;
        proj2h.textContent = data.condition_2h;
    }

    async function fetchExtendedForecasts() {
        let hasData = false;
        
        if (!smnPredChartObj) smnPredChartObj = initPredChart('smn-pred-chart');
        if (!owmPredChartObj) owmPredChartObj = initPredChart('owm-pred-chart');

        // Fetch SMN
        try {
            const res = await fetch('/goes/smn_prediction.json');
            if (res.ok) {
                const data = await res.json();
                smnPredDataCache = data.predictions;
                if (smnPredDataCache && smnPredDataCache.length > 0) {
                    if (!currentSelectedSmnDay) {
                        currentSelectedSmnDay = getLocalDateKey(smnPredDataCache[0].time);
                    }
                    renderSmnDaySelector();
                    updatePredChart(smnPredChartObj, smnPredDataCache, currentSmnTab, currentSelectedSmnDay);
                    document.getElementById('third-party-forecast-card').style.display = 'block';
                    hasData = true;
                }
            }
        } catch(e) { console.warn("SMN forecast not ready"); }

        // Fetch OWM
        try {
            const res = await fetch('/goes/owm_prediction.json');
            if (res.ok) {
                const data = await res.json();
                owmPredDataCache = data.predictions;
                if (owmPredDataCache && owmPredDataCache.length > 0) {
                    if (!currentSelectedOwmDay) {
                        // Pick first local day with at least 4 time-slots (avoids nearly-empty today)
                        const owmGroups = {};
                        owmPredDataCache.forEach(p => {
                            const k = getLocalDateKey(p.time);
                            owmGroups[k] = (owmGroups[k] || 0) + 1;
                        });
                        currentSelectedOwmDay = (Object.entries(owmGroups).find(([, c]) => c >= 4) || Object.entries(owmGroups)[0])?.[0];
                    }
                    renderOwmDaySelector();
                    updatePredChart(owmPredChartObj, owmPredDataCache, currentOwmTab, currentSelectedOwmDay);
                    document.getElementById('third-party-forecast-card').style.display = 'block';
                    hasData = true;
                }
            }
        } catch(e) { console.warn("OWM forecast not ready"); }
    }

    function initPredChart(canvasId) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 30, bottom: 0, left: 15, right: 15 } },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }, // Google style
                    datalabels: {
                        display: true,
                        align: 'top',
                        anchor: 'end',
                        offset: 4,
                        color: '#c9d1d9',
                        font: { weight: 'bold', size: 11 },
                        formatter: function(value, context) {
                            const dataset = context.chart.data.datasets[context.datasetIndex];
                            const unit = dataset.unit || '';
                            return Math.round(value) + unit;
                        }
                    }
                },
                scales: {
                    y: { display: false },
                    x: { grid: { display: false }, ticks: { color: '#8b949e', font: { size: 10 } } }
                },
                elements: {
                    line: { tension: 0.4 },
                    point: { radius: 0, hoverRadius: 0 }
                }
            }
        });
    }

    function getPredChartConfig(type) {
        if (type === 'temp') return { color: '#ffab70', bgColor: 'rgba(255, 171, 112, 0.2)' };
        if (type === 'rain') return { color: '#58a6ff', bgColor: 'rgba(88, 166, 255, 0.2)' };
        if (type === 'wind') return { color: '#3fb950', bgColor: 'rgba(63, 185, 80, 0.2)' };
        return { color: '#fff', bgColor: 'rgba(255,255,255,0.1)' };
    }

    // Normaliza cualquier timestamp (UTC con Z o local sin Z) al día local del browser
    function getLocalDateKey(timeStr) {
        const d = new Date(timeStr);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function updatePredChart(chartObj, arrayData, type, selectedDay) {
        // Filter by selected day using local date (handles UTC "Z" from OWM and local from SMN)
        const filteredData = arrayData.filter(p => getLocalDateKey(p.time) === selectedDay);
        
        const labels = filteredData.map(p => {
            const d = new Date(p.time);
            let h = d.getHours();
            const ampm = h >= 12 ? 'pm' : 'am';
            h = h % 12 || 12;
            return `${h} ${ampm}`;
        });

        let dataPoints = [];
        if (type === 'temp') dataPoints = filteredData.map(p => p.temperature);
        if (type === 'rain') dataPoints = filteredData.map(p => p.precipitation || 0);
        if (type === 'wind') dataPoints = filteredData.map(p => p.wind_speed || 0);

        const config = getPredChartConfig(type);

        const maxVal = Math.max(...dataPoints, 1);
        const minVal = Math.min(...dataPoints);
        chartObj.options.scales.y.max = maxVal + (maxVal * 0.4); // headroom for tags
        chartObj.options.scales.y.min = type === 'temp' ? minVal - 2 : 0; 

        chartObj.data.labels = labels;
        chartObj.data.datasets = [{
            data: dataPoints,
            borderColor: config.color,
            backgroundColor: config.bgColor,
            borderWidth: 2,
            fill: true,
            unit: type === 'temp' ? '°' : 'mm'
        }];
        
        chartObj.update();
    }

    // --- Generic helper to build a day-selector for any data source ---
    function buildDaySelector(selectorId, dataCache, selectedDay, accentColor, onSelect) {
        const selector = document.getElementById(selectorId);
        if (!selector || !dataCache) return;

        const days = {};
        dataCache.forEach(p => {
            const dayKey = getLocalDateKey(p.time);
            if (!days[dayKey]) {
                const date = new Date(p.time);
                const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
                days[dayKey] = {
                    key: dayKey,
                    label: date.toLocaleDateString('es-ES', { weekday: 'short', timeZone: tz }).replace('.', '').toUpperCase(),
                    min: p.temperature,
                    max: p.temperature
                };
            } else {
                days[dayKey].min = Math.min(days[dayKey].min, p.temperature);
                days[dayKey].max = Math.max(days[dayKey].max, p.temperature);
            }
        });

        selector.innerHTML = Object.values(days).map(d => {
            const isActive = d.key === selectedDay;
            return `
            <div class="day-chip ${isActive ? 'active' : ''}" data-day="${d.key}"
                 style="cursor:pointer; padding: 8px 10px; border-radius: 12px;
                        background: ${isActive ? `rgba(${accentColor}, 0.2)` : 'rgba(255,255,255,0.05)'};
                        min-width: 58px; text-align: center;
                        border: 1px solid ${isActive ? `rgba(${accentColor}, 0.8)` : 'transparent'};
                        transition: all 0.2s;">
                <div style="font-size: 0.75rem; color: #8b949e; font-weight: 600;">${d.label}</div>
                <div style="font-weight: bold; font-size: 0.9rem; margin-top: 3px;">${Math.round(d.max)}°
                    <span style="color: #8b949e; font-weight: normal; font-size: 0.8rem;">${Math.round(d.min)}°</span>
                </div>
            </div>`;
        }).join('');

        selector.querySelectorAll('.day-chip').forEach(chip => {
            chip.addEventListener('click', () => onSelect(chip.dataset.day));
        });
    }

    function renderSmnDaySelector() {
        buildDaySelector('smn-day-selector', smnPredDataCache, currentSelectedSmnDay, '88, 166, 255', (day) => {
            currentSelectedSmnDay = day;
            renderSmnDaySelector();
            updatePredChart(smnPredChartObj, smnPredDataCache, currentSmnTab, currentSelectedSmnDay);
        });
    }

    function renderOwmDaySelector() {
        buildDaySelector('owm-day-selector', owmPredDataCache, currentSelectedOwmDay, '63, 185, 80', (day) => {
            currentSelectedOwmDay = day;
            renderOwmDaySelector();
            updatePredChart(owmPredChartObj, owmPredDataCache, currentOwmTab, currentSelectedOwmDay);
        });
    }

    function updateIndexUI(data) {
        if (!data) return;
        if (currentDew) currentDew.textContent = data.dew_point + " °C";
        
        // Update pressure trend icon
        if (pressTrendIcon) {
            const val = data.pressure_trend_value;
            if (val > 0.5) pressTrendIcon.textContent = "↑";
            else if (val < -0.5) pressTrendIcon.textContent = "↓";
            else pressTrendIcon.textContent = "→";
        }
        
        if (pressLabel) pressLabel.textContent = data.pressure_trend_text;
    }

    function preloadSequence() {
        imageSequence.forEach(img => {
            const tempImg = new Image();
            tempImg.src = `/goes/${currentProduct}/${img.name}`;
        });
    }

    function updateGalleryUI(imageFile) {
        const newSrc = `/goes/${currentProduct}/${imageFile.name}`;
        
        if (mainImage.src !== window.location.origin + newSrc) {
            if (!isAnimating) {
                loader.style.display = 'block';
                mainImage.style.opacity = '0.5';
            }
            
            mainImage.src = newSrc;
            
            mainImage.onload = () => {
                if (!isAnimating) {
                    loader.style.display = 'none';
                    mainImage.style.opacity = '1';
                }
            };
        }

        const nameParts = imageFile.name.replace('.png', '').split('_');
        if (nameParts.length >= 4) {
            const dateStr = nameParts[2];
            const timeStr = nameParts[3];
            const formatted = `${dateStr.slice(6,8)}/${dateStr.slice(4,6)}/${dateStr.slice(0,4)} ${timeStr.slice(0,2)}:${timeStr.slice(2,4)}:${timeStr.slice(4,6)}`;
            imageTimestamp.textContent = isAnimating ? `Secuencia: ${formatted} UTC` : `Captura: ${formatted} UTC`;
            if (!isAnimating) {
                lastUpdateNav.textContent = `Última actualización: ${new Date().toLocaleTimeString()}`;
            }
        }
    }

    function toggleAnimation() {
        if (isAnimating) {
            stopAnimation();
        } else {
            preloadSequence(); // Pre-cache everything
            startAnimation();
        }
    }

    function startAnimation() {
        if (imageSequence.length < 2) return;
        isAnimating = true;
        currentFrame = 0;
        btnAnimate.classList.add('active');
        btnAnimate.innerHTML = '<span class="btn-icon">⏹</span> Detener Secuencia';
        
        animationInterval = setInterval(() => {
            currentFrame = (currentFrame + 1) % imageSequence.length;
            updateGalleryUI(imageSequence[currentFrame]);
        }, 600); // 600ms per frame for smooth but visible change
    }

    function stopAnimation() {
        isAnimating = false;
        clearInterval(animationInterval);
        btnAnimate.classList.remove('active');
        btnAnimate.innerHTML = '<span class="btn-icon">▶</span> Reproducir Secuencia';
        if (imageSequence.length > 0) {
            updateGalleryUI(imageSequence[imageSequence.length - 1]); // Return to latest (last in chron array)
        }
    }

    if (btnAnimate) {
        btnAnimate.addEventListener('click', toggleAnimation);
    }


    function updateWeatherUI(data) {
        currentTemp.textContent = Math.round(data.temperature);
        currentHum.textContent = `${data.humidity}%`;
        currentPress.textContent = `${Math.round(data.pressure)} hPa`;
        currentWind.textContent = `${data.wind_speed} km/h`;
        
        // Beaufort Scale for non-experts
        if (windLabel) {
            const speed = data.wind_speed;
            let label = "Calma";
            if (speed > 5 && speed <= 11) label = "Brisa Leve";
            else if (speed > 11 && speed <= 19) label = "Brisa Ligera";
            else if (speed > 19 && speed <= 28) label = "Brisa Moderada";
            else if (speed > 28 && speed <= 38) label = "Brisa Fresca";
            else if (speed > 38 && speed <= 49) label = "Viento Fuerte";
            else if (speed > 49) label = "Temporal";
            windLabel.textContent = label;
        }
        
        // Update data source text AND observation time
        const dataSource = document.querySelector('.data-source');
        if (dataSource) {
            const obsDate = new Date(data.time);
            const timeStr = obsDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            dataSource.innerHTML = `Fuente: ${data.source === 'smn' ? 'SMN Argentina' : 'OpenWeatherMap'}<br><small>Obs: ${timeStr} UTC</small>`;
            
            // Match prediction tab to current data source
            switchProviderTab(data.source === 'smn' ? 'smn' : 'owm');
        }

        // Update icon based on OWM icon or description
        const iconEl = document.getElementById('weather-icon');
        const desc = (data.description || "").toLowerCase();
        
        // 1. Priority: OWM specific icon codes
        if (data.icon) {
            const iconMapping = {
                '01d': '☀️', '01n': '🌙',
                '02d': '🌤️', '02n': '☁️',
                '03d': '☁️', '03n': '☁️',
                '04d': '☁️', '04n': '☁️',
                '09d': '🌧️', '09n': '🌧️',
                '10d': '🌦️', '10n': '🌧️',
                '11d': '⛈️', '11n': '⛈️',
                '13d': '❄️', '13n': '❄️',
                '50d': '🌫️', '50n': '🌫️'
            };
            if (iconMapping[data.icon]) {
                iconEl.textContent = iconMapping[data.icon];
                return;
            }
        }

        // 2. Fallback: SMN / Description keywords
        if (desc.includes('lluvia') || desc.includes('llovizna')) iconEl.textContent = '🌧️';
        else if (desc.includes('tormenta')) iconEl.textContent = '⛈️';
        else if (desc.includes('nieve')) iconEl.textContent = '❄️';
        else if (desc.includes('niebla') || desc.includes('neblina')) iconEl.textContent = '🌫️';
        else if (desc.includes('nublado') || desc.includes('cubierto')) iconEl.textContent = '☁️';
        else if (desc.includes('parcialmente') || desc.includes('algo nublado')) iconEl.textContent = '⛅';
        else if (desc.includes('despejado')) {
            const hour = new Date().getHours();
            iconEl.textContent = (hour > 19 || hour < 7) ? '🌙' : '☀️';
        } else {
            // Heuristic fallback if everything else fails
            if (data.temperature > 30) iconEl.textContent = '☀️';
            else iconEl.textContent = '⛅';
        }
    }




    // Product switching logic
    productTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            if (isAnimating) stopAnimation(); // Stop animation if switching tabs
            
            productTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            currentProduct = tab.dataset.product;
            
            // Update documentation link
            if (docLink && productDocs[currentProduct]) {
                docLink.href = productDocs[currentProduct];
                console.log("Cambiando enlace de doc a:", currentProduct, productDocs[currentProduct]);
            }
            
            fetchGalleryData(); // Fetch new list for this product
        });
    });

    // Local Clock logic
    function updateLocalClock() {
        const now = new Date();
        const localTimeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        if (localClock) localClock.textContent = localTimeStr + " local";
    }
    
    setInterval(updateLocalClock, 1000);
    updateLocalClock();

    // Initial load
    fetchGalleryData();
    fetchWeatherData();

    // Refresh every 2 minutes
    setInterval(() => {
        fetchGalleryData();
        fetchWeatherData();
    }, 120000);
});
