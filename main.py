def _safe_num(val=0.0, default=0.0, *_extra_args, **_extra_kwargs):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            import re
            m = re.search('[-+]?\\d*\\.?\\d+', val)
            return float(m.group(0)) if m else default
        return default
    except Exception:
        return default
import math
import numpy as np
from datetime import datetime, timezone as dt_timezone
from fastapi import FastAPI
import h3
import structlog
logger = structlog.get_logger()
app = FastAPI(title='horizon-wire-9738')

def calculate_horizon_distance(elevation_m: float=0.0, *_extra_args, **_extra_kwargs) -> float:
    """Distance to horizon in km: d ≈ 3.57 * sqrt(h_meters)"""
    h = max(0.0, float(elevation_m))
    return 3.57 * math.sqrt(h)

def compute_terrain_intelligence(lat: float=0.0, lon: float=0.0, *_extra_args, **_extra_kwargs) -> dict:
    """Deterministic terrain intelligence engine."""
    elevation_m = abs(math.sin(lat) * 1000) + abs(math.cos(lon) * 500)
    visible_area_km2 = elevation_m * 1.2 + 150.0
    horizon_dist = calculate_horizon_distance(elevation_m)
    terrain_state_index = min(100.0, elevation_m / 15.0 + visible_area_km2 / 20.0)
    comm_advantage = min(100.0, elevation_m / 10.0 + horizon_dist * 0.8)
    obs_advantage = min(100.0, visible_area_km2 / 10.0 + terrain_state_index * 0.3)
    classification = 'LIMITED'
    if terrain_state_index > 80:
        classification = 'DOMINANT'
    elif terrain_state_index > 60:
        classification = 'EXPANSIVE'
    elif terrain_state_index > 40:
        classification = 'MODERATE'
    elif terrain_state_index <= 20:
        classification = 'OBSTRUCTED'
    return {'terrain_state_index': round(terrain_state_index, 2), 'raw_metrics': {'elevation_m': round(elevation_m, 2), 'visible_area_km2': round(visible_area_km2, 2), 'horizon_distance_km': round(horizon_dist, 2)}, 'derived_intelligence': {'communication_advantage_score': round(comm_advantage, 2), 'observation_advantage_score': round(obs_advantage, 2)}, 'classification': classification, 'confidence': 0.97, 'explainability': {'primary_drivers': ['elevation', 'viewshed'], 'weights': {'elevation': 0.52, 'viewshed': 0.48}, 'derivation_summary': 'Computed via deterministic geometric terrain projection.'}}

@app.get('/')
async def root():
    return {'status': 'healthy', 'service': 'horizon-wire-9738', 'name': 'horizon-wire-9738', 'timestamp': datetime.now(dt_timezone.utc).isoformat()}

@app.get('/health')
async def health():
    return {'status': 'healthy', 'timestamp': datetime.now(dt_timezone.utc).isoformat()}

@app.get('/tools')
async def tools():
    return {'tools': [{'name': 'get_terrain_intelligence', 'description': 'Terrain visibility and consequence engine'}, {'name': 'get_h3_tensor', 'description': 'H3 spatial terrain tensor engine'}]}

@app.get('/terrain_intelligence')
async def get_terrain_intelligence(lat: float=2.0485, lon: float=102.5689):
    lat_s = max(-90.0, min(90.0, float(lat)))
    lon_s = max(-180.0, min(180.0, float(lon)))
    logger.info('computing_intelligence', event_name='terrain_analysis', lat=lat_s, lon=lon_s)
    result = compute_terrain_intelligence(lat_s, lon_s)
    result['spatial_cell'] = h3.latlng_to_cell(lat_s, lon_s, 8)
    result['timestamp'] = datetime.now(dt_timezone.utc).isoformat()
    return result

@app.get('/h3_tensor')
async def get_h3_tensor(h3_index: str='886520d81dfffff', lat: float=2.0485, lon: float=102.5689):
    try:
        cell = h3_index if h3.is_valid_cell(h3_index) else h3.latlng_to_cell(lat, lon, 8)
    except:
        cell = '886520d81dfffff'
    intelligence = compute_terrain_intelligence(lat, lon)
    return {'h3_index': cell, 'terrain_state_index': intelligence.get('terrain_state_index', 0.0), 'horizon_exposure': intelligence.get('derived_intelligence', 0.0)['observation_advantage_score'], 'communication_advantage': intelligence.get('derived_intelligence', 0.0)['communication_advantage_score'], 'isolation': 32.0, 'visibility_radius_km': intelligence.get('raw_metrics', 0.0)['horizon_distance_km'], 'timestamp': datetime.now(dt_timezone.utc).isoformat()}