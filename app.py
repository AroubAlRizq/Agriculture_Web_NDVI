from flask import Flask, render_template, request, jsonify, send_file
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import base64
from scipy.ndimage import gaussian_filter

app = Flask(__name__)

# --- 1. SATELLITE SIMULATION ENGINE (The "API") ---
# In a real app, you would replace this function with a call to 
# Google Earth Engine or Sentinel Hub API.
def fetch_satellite_bands(lat, lon, zoom, date):
    """
    Simulates fetching Red and NIR bands for a specific location and date.
    Returns two 256x256 numpy arrays (matrices) simulating satellite tiles.
    """
    np.random.seed(sum([ord(c) for c in date]) + int(lat*100)) # Seed based on date/loc
    
    # Generate structured "noise" to look like terrain
    size = 256
    base_terrain = np.random.rand(size, size)
    smooth_terrain = gaussian_filter(base_terrain, sigma=5) # Make it look like clouds/land
    
    # simulate NIR (Vegetation reflects high NIR) - Higher in "green" areas
    nir_band = smooth_terrain * 0.8 + 0.1 
    
    # simulate Red (Vegetation absorbs Red) - Lower in "green" areas
    # We invert parts of the NIR to simulate healthy plants (Low Red, High NIR)
    red_band = (1 - smooth_terrain) * 0.5 + 0.1

    # Add seasonal variation based on date (simple simulation)
    if "01" in date or "12" in date: # Winter in KSA (More green potential)
        nir_band += 0.1
    elif "07" in date: # Summer (Drier)
        nir_band -= 0.1
        
    return nir_band, red_band

# --- 2. IMAGE CALCULATOR ---
def compute_index_map(formula, nir_band, red_band):
    """
    Applies the math formula to the entire image matrix at once.
    """
    # Avoid division by zero
    epsilon = 1e-10 
    
    if formula == "ndvi":
        # (NIR - Red) / (NIR + Red)
        numerator = nir_band - red_band
        denominator = nir_band + red_band + epsilon
        result = numerator / denominator
        return result, "RdYlGn" # Red-Yellow-Green colormap
        
    elif formula == "savi":
        # ((1 + L) * (NIR - Red)) / (NIR + Red + L)
        L = 0.5
        numerator = (1 + L) * (nir_band - red_band)
        denominator = nir_band + red_band + L + epsilon
        result = numerator / denominator
        return result, "YlGn"
        
    elif formula == "evi":
        # Simplified EVI for demo (requires Blue usually, using Red proxy)
        # 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Red + 1))
        numerator = 2.5 * (nir_band - red_band)
        denominator = nir_band + 6 * red_band - 7.5 * red_band + 1 + epsilon
        result = numerator / denominator
        return result, "Greens"

    else:
        # Default to NDVI if unknown
        return (nir_band - red_band) / (nir_band + red_band + epsilon), "RdYlGn"

# --- 3. MAP RENDERER ---
def generate_heatmap_overlay(data_matrix, colormap_name):
    """
    Converts the calculated index matrix into a PNG image for the map.
    """
    plt.figure(figsize=(4, 4))
    # Normalize data usually between -1 and 1 for NDVI
    norm = mcolors.Normalize(vmin=-0.2, vmax=0.8) 
    
    # Create image
    img = plt.imshow(data_matrix, cmap=colormap_name, norm=norm)
    plt.axis('off') # Hide axes
    
    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()
    buffer.seek(0)
    
    # Convert to Base64 to send to frontend
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{image_base64}"

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('map_view.html')

@app.route('/get_map_layer', methods=['POST'])
def get_map_layer():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    zoom = data.get('zoom')
    dates = data.get('dates') # List of dates
    formula = data.get('formula')
    
    layers = []
    
    for date in dates:
        # 1. Fetch Data (From Simulated Satellite API)
        nir, red = fetch_satellite_bands(lat, lon, zoom, date)
        
        # 2. Compute Indices (Using your formulas)
        result_matrix, cmap = compute_index_map(formula, nir, red)
        
        # 3. Generate Image
        image_url = generate_heatmap_overlay(result_matrix, cmap)
        
        # 4. Compute stats for the sidebar
        avg_val = float(np.mean(result_matrix))
        
        layers.append({
            'date': date,
            'image': image_url,
            'stats': round(avg_val, 4)
        })

    return jsonify({'layers': layers})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
