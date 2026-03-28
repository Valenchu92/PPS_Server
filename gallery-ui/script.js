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

    let animationInterval = null;
    let isAnimating = false;
    let imageSequence = [];
    let currentFrame = 0;
    let currentProduct = 'geocolor'; // Default GOES product
    const btnAnimate = document.getElementById('btn-animate');
    const productTabs = document.querySelectorAll('.prod-tab');

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

            // 2. Fetch latest weather data
            fetchWeatherData();

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
            updateGalleryUI(imageSequence[0]); // Return to latest
        }
    }

    if (btnAnimate) {
        btnAnimate.addEventListener('click', toggleAnimation);
    }


    function updateWeatherUI(data) {
        currentTemp.textContent = Math.round(data.temperature);
        currentHum.textContent = `${data.humidity}%`;
        currentPress.textContent = `${data.pressure} hPa`;
        currentWind.textContent = `${data.wind_speed} km/h`;
        
        // Update data source text AND observation time
        const dataSource = document.querySelector('.data-source');
        if (dataSource) {
            const obsDate = new Date(data.time);
            const timeStr = obsDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            dataSource.innerHTML = `Fuente: ${data.source === 'smn' ? 'SMN Argentina' : 'OpenWeatherMap'}<br><small>Obs: ${timeStr} UTC</small>`;
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


    // Chart logic
    let weatherChart = null;
    let currentChartType = 'temp';
    const tabBtns = document.querySelectorAll('.tab-btn');

    function initChart() {
        const ctx = document.getElementById('weather-chart').getContext('2d');
        weatherChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperatura (°C)',
                    data: [],
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#58a6ff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#8b949e', font: { size: 10 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8b949e', font: { size: 10 } }
                    }
                }
            }
        });
    }

    async function updateChart() {
        try {
            const response = await fetch('/goes/weather_history.json');
            if (!response.ok) return;
            const history = await response.json();

            const labels = history.map(entry => {
                const date = new Date(entry.time);
                return date.getHours() + ':00';
            });

            let dataValues = [];
            let label = '';
            let color = '#58a6ff';

            if (currentChartType === 'temp') {
                dataValues = history.map(entry => entry.temperature);
                label = 'Temperatura (°C)';
                color = '#ffab70'; // Gold/Orange for temp
            } else if (currentChartType === 'wind') {
                dataValues = history.map(entry => entry.wind_speed);
                label = 'Viento (km/h)';
                color = '#3fb950'; // Green for wind
            } else if (currentChartType === 'press') {
                dataValues = history.map(entry => entry.pressure);
                label = 'Presión (hPa)';
                color = '#bc8cff'; // Purple for pressure
            }

            weatherChart.data.labels = labels;
            weatherChart.data.datasets[0].data = dataValues;
            weatherChart.data.datasets[0].label = label;
            weatherChart.data.datasets[0].borderColor = color;
            weatherChart.data.datasets[0].backgroundColor = color + '1A'; // Alpha 0.1
            weatherChart.data.datasets[0].pointBackgroundColor = color;
            
            weatherChart.update();
        } catch (error) {
            console.warn('History data not available');
        }
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentChartType = btn.dataset.type;
            updateChart();
        });
    });

    // Product switching logic
    productTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            if (isAnimating) stopAnimation(); // Stop animation if switching tabs
            
            productTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            currentProduct = tab.dataset.product;
            fetchGalleryData(); // Fetch new list for this product
        });
    });

    // Initial load
    initChart();
    fetchGalleryData();
    updateChart();

    // Refresh every 2 minutes
    setInterval(() => {
        fetchGalleryData();
        updateChart();
    }, 120000);
});
