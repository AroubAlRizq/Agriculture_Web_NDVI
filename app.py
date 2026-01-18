from flask import Flask, render_template, request, jsonify
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import base64
from scipy.ndimage import gaussian_filter, zoom

app = Flask(__name__)

# --- 1. SATELLITE SIMULATION ENGINE (High-Res Pixelated) ---
def fetch_satellite_bands(lat, lon, z_level, date):
    """
    Simulates high-resolution, pixelated satellite bands.
    Returns two 1024x1024 numpy arrays.
    """
    # Seed for reproducibility based on location/date
    seed_val = int(abs(lat*lon*10000)) + sum([ord(c) for c in date])
    np.random.seed(seed_val)
    
    # 1. Create base large-scale features (like mountains/valleys)
    # Start small and zoom up to create large, smooth features
    coarse_grid = np.random.rand(64, 64)
    coarse_grid = gaussian_filter(coarse_grid, sigma=3)
    # Zoom up to 1024x1024 without smoothing for pixel effect
    large_features = zoom(coarse_grid, 16, order=0) 

    # 2. Create fine-scale pixel noise
    fine_noise = np.random.rand(1024, 1024) * 0.3

    # Combine features: Base terrain is a mix of large features and fine noise
    base_terrain = large_features * 0.7 + fine_noise

    # --- Simulate NIR & Red bands based on "terrain" ---
    
    # NIR: High reflection in healthy vegetation.
    # We'll say higher base_terrain values are more likely to be vegetated.
    # Add some seasonal logic:
    month = int(date.split('-')[1])
    is_growing_season = 1 <= month <= 4 # Jan-Apr in KSA
    
    veg_potential = base_terrain
    if is_growing_season:
        # Boost vegetation potential in growing season
        veg_potential = np.clip(veg_potential + 0.15, 0, 1)
    else:
        # Reduce it otherwise (more barren/soil)
        veg_potential = np.clip(veg_potential - 0.1, 0, 1)

    # NIR band simulation: High in veg, lower elsewhere
    nir_band = veg_potential * 0.8 + np.random.rand(1024, 1024) * 0.1
    
    # Red band simulation: Low in veg (absorbed), high in soil (reflected)
    # Invert the vegetation potential for Red
    red_band = (1.0 - veg_potential) * 0.6 + np.random.rand(1024, 1024) * 0.1
    
    # Normalize bands to 0.0-1.0 range
    nir_band = np.clip(nir_band, 0.001, 1.0)
    red_band = np.clip(red_band, 0.001, 1.0)

    return nir_band, red_band

# --- 2. IMAGE CALCULATOR (Same as before) ---
def compute_index_map(formula, nir_band, red_band):
    epsilon = 1e-10 
    
    if formula == "ndvi":
        numerator = nir_band - red_band
        denominator = nir_band + red_band + epsilon
        result = numerator / denominator
        # NDVI range is -1 to 1. We'll normalize for colormap later.
        return result, "RdYlGn"
        
    elif formula == "savi":
        L = 0.5
        numerator = (1 + L) * (nir_band - red_band)
        denominator = nir_band + red_band + L + epsilon
        result = numerator / denominator
        return result, "YlGn" # Soil Adjusted often uses Yellow-Green
        
    elif formula == "evi":
        # Simplified EVI
        numerator = 2.5 * (nir_band - red_band)
        denominator = nir_band + 6 * red_band - 7.5 * red_band + 1 + epsilon
        result = numerator / denominator
        # EVI has a wider dynamic range, often -1 to >1.
        # Greens is a good colormap for emphasizing vegetation quantity.
        return result, "Greens"

    else:
        return (nir_band - red_band) / (nir_band + red_band + epsilon), "RdYlGn"

# --- 3. MAP RENDERER (Updated for pixelated look) ---
def generate_heatmap_overlay(data_matrix, colormap_name):
    """
    Converts matrix to a sharp, pixelated PNG.
    """
    # Use a high DPI for detailed image
    plt.figure(figsize=(8, 8), dpi=128) 
    
    # Set norm based on colormap/index type for best visual contrast
    vmin, vmax = -0.1, 0.6 # Good general range for vegetation indices over land
    if colormap_name == 'Greens': # EVI often goes higher
         vmin, vmax = 0.0, 0.8

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax) 
    
    # IMPORTANT: interpolation='nearest' creates the sharp, pixelated look
    plt.imshow(data_matrix, cmap=colormap_name, norm=norm, interpolation='nearest')
    plt.axis('off')
    
    buffer = io.BytesIO()
    # Save with transparency
    plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()
    buffer.seek(0)
    
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
    zoom_level = data.get('zoom')
    dates = data.get('dates')
    formula = data.get('formula')
    
    layers = []
    
    for date in dates:
        # 1. Fetch High-Res Pixelated Data
        nir, red = fetch_satellite_bands(lat, lon, zoom_level, date)
        
        # 2. Compute Index
        result_matrix, cmap = compute_index_map(formula, nir, red)
        
        # 3. Generate Sharp Heatmap Image
        image_url = generate_heatmap_overlay(result_matrix, cmap)
        
        # 4. Compute stats (ignore water/background for better avg)
        valid_pixels = result_matrix[result_matrix > -0.1]
        avg_val = float(np.mean(valid_pixels)) if valid_pixels.size > 0 else 0.0
        
        layers.append({
            'date': date,
            'image': image_url,
            'stats': round(avg_val, 4)
        })

    return jsonify({'layers': layers})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
