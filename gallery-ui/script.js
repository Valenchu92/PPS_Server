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

    async function fetchGalleryData() {
        try {
            // 1. Fetch images from Nginx JSON autoindex
            const response = await fetch('/goes/');
            if (!response.ok) throw new Error('No se pudo obtener la lista de imágenes');
            
            const files = await response.json();
            
            // Filter only PNG files and sort by name (timestamp) descending
            const images = files
                .filter(file => file.type === 'file' && file.name.endsWith('.png'))
                .sort((a, b) => b.name.localeCompare(a.name));

            if (images.length > 0) {
                updateGalleryUI(images);
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

    function updateGalleryUI(images) {
        const latest = images[0];
        
        // Update main image
        const newSrc = `/goes/${latest.name}`;
        if (mainImage.src !== window.location.origin + newSrc) {
            loader.style.display = 'block';
            mainImage.style.opacity = '0.5';
            mainImage.src = newSrc;
            mainImage.onload = () => {
                loader.style.display = 'none';
                mainImage.style.opacity = '1';
            };
        }

        // Format name goes_cordoba_20260315_220020.png -> 15/03/2026 22:00:20
        const nameParts = latest.name.replace('.png', '').split('_');
        if (nameParts.length >= 4) {
            const dateStr = nameParts[2];
            const timeStr = nameParts[3];
            const formatted = `${dateStr.slice(6,8)}/${dateStr.slice(4,6)}/${dateStr.slice(0,4)} ${timeStr.slice(0,2)}:${timeStr.slice(2,4)}:${timeStr.slice(4,6)}`;
            imageTimestamp.textContent = `Captura: ${formatted} UTC`;
            lastUpdateNav.textContent = `Última actualización: ${new Date().toLocaleTimeString()}`;
        }
    }


    function updateWeatherUI(data) {
        currentTemp.textContent = Math.round(data.temperature);
        currentHum.textContent = `${data.humidity}%`;
        currentPress.textContent = `${data.pressure} hPa`;
        currentWind.textContent = `${data.wind_speed} km/h`;
        
        // Update data source text
        const dataSource = document.querySelector('.data-source');
        if (dataSource) {
            dataSource.textContent = `Fuente: ${data.source === 'smn' ? 'SMN Argentina' : 'OpenWeatherMap'}`;
        }

        // Update icon based on humidity/temp if needed
        const icon = document.getElementById('weather-icon');
        if (data.humidity > 80) icon.textContent = '🌧️';
        else if (data.temperature > 30) icon.textContent = '☀️';
        else icon.textContent = '⛅';
    }


    // Initial load
    fetchGalleryData();

    // Refresh every 2 minutes
    setInterval(fetchGalleryData, 120000);
});
