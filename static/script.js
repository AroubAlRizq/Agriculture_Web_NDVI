document.addEventListener('DOMContentLoaded', function() {
    const calcBtn = document.getElementById('calc-btn');
    const resultArea = document.getElementById('result-area');
    const citySelect = document.getElementById('city');
    const resultDisplay = document.getElementById('result-display');

    // Dashboard Elements
    const wTemp = document.getElementById('w-temp');
    const wHum = document.getElementById('w-hum');
    const wDew = document.getElementById('w-dew');
    const wWind = document.getElementById('w-wind');
    const wVis = document.getElementById('w-vis');
    const wPres = document.getElementById('w-pres');

    calcBtn.addEventListener('click', async function() {
        // 1. Force Reset UI
        calcBtn.innerText = "Connecting to Satellite...";
        calcBtn.disabled = true;
        resultArea.classList.add('hidden'); // Hide previous results immediately
        resultDisplay.innerHTML = "";       // Clear previous text

        const payload = { city: citySelect.value };

        try {
            const response = await fetch('/assess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();

            if (data.error) {
                alert("Alert: " + data.error);
            } else {
                // 2. Safe Injection (Check if elements exist first)
                if(wTemp) wTemp.innerText = data.weather_summary.temp + "°C";
                if(wHum) wHum.innerText = data.weather_summary.rh + "%";
                if(wDew) wDew.innerText = data.weather_summary.dew + "°C";
                if(wWind) wWind.innerText = data.weather_summary.wind + " km/h";
                if(wVis) wVis.innerText = data.weather_summary.vis + " km";
                if(wPres) wPres.innerText = data.weather_summary.pressure + " hPa";

                // 3. Show Results
                resultDisplay.innerHTML = data.result;
                resultArea.classList.remove('hidden');
                
                // Scroll
                resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } catch (error) {
            console.error("Fetch error:", error);
            alert("Connection Failed. Please check internet connection.");
        } finally {
            // 4. ALWAYS Re-enable button
            calcBtn.innerText = "Analyze Satellite Data";
            calcBtn.disabled = false;
        }
    });
});
