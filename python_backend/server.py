import asyncio
import json
import logging
import os
from aiohttp import web
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription
try:
    from camera_stream import CameraTrack, CameraManager
except ImportError:
    from python_backend.camera_stream import CameraTrack, CameraManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("safecam_webrtc_server")

# Global active peer connections storage: set of RTCPeerConnection
pcs = set()
camera_manager = CameraManager()

async def offer(request):
    """
    WebRTC Signaling SDP Offer Handler
    Accepts client SDP offer and returns SDP answer.
    Query params / Body: camera_id, stream_url
    """
    params = await request.json()
    sdp = params.get("sdp")
    type_ = params.get("type", "offer")

    # Camera ID & Stream URL from query params or body
    camera_id = request.query.get("camera_id") or params.get("camera_id") or "CAM-001"
    stream_url = request.query.get("stream_url") or params.get("stream_url") or ""

    logger.info(f"[WEBRTC OFFER] New connection request for camera: {camera_id}")

    offer_desc = RTCSessionDescription(sdp=sdp, type=type_)
    pc = RTCPeerConnection()
    pcs.add(pc)

    # Acquire shared SingleCameraPipeline for this camera ID from CameraManager
    pipeline = camera_manager.get_or_create_pipeline(camera_id=camera_id, stream_url=stream_url)
    pipeline.add_viewer()

    cleaned_up = False

    async def _cleanup_peer():
        nonlocal cleaned_up
        if cleaned_up:
            return
        cleaned_up = True
        if pc in pcs:
            pcs.discard(pc)
        pipeline.remove_viewer()
        if pipeline.active_viewers <= 0:
            camera_manager.release_pipeline(camera_id)

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        logger.info(f"[ICE STATE] Camera {camera_id}: {pc.iceConnectionState}")
        if pc.iceConnectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            await _cleanup_peer()

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"[CONNECTION STATE] Camera {camera_id}: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            await _cleanup_peer()

    track = CameraTrack(pipeline=pipeline)
    pc.addTrack(track)

    await pc.setRemoteDescription(offer_desc)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

try:
    from alarm_manager import alarm_manager
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_manager import alarm_manager
    from python_backend.alarm_config import alarm_config

async def get_alarms(request):
    """Returns single-source-of-truth alarm states and historical incident records."""
    camera_id = request.match_info.get("camera_id") if "camera_id" in request.match_info else request.query.get("camera_id")
    if camera_id:
        st = alarm_manager.get_camera_state(camera_id)
        return web.json_response(st)

    all_states = alarm_manager.get_all_states()
    all_incidents = alarm_manager.get_all_incidents()
    return web.json_response({
        "status": "success",
        "active_alarms": [st for st in all_states.values() if st.get("alarm_active")],
        "camera_states": all_states,
        "incidents": all_incidents
    })

async def acknowledge_alarm(request):
    """Silences audio alarm for a camera ID."""
    params = await request.json()
    camera_id = params.get("camera_id") or "CAM-001"
    success = alarm_manager.acknowledge_alarm(camera_id)
    return web.json_response({
        "status": "success" if success else "not_found",
        "camera_id": camera_id,
        "acknowledged": True
    })

async def delete_alarm(request):
    try:
        data = await request.json()
        incident_id = data.get("incident_id")
        if not incident_id:
            return web.json_response({"error": "Missing incident_id"}, status=400)
        
        success = alarm_manager.delete_incident(incident_id)
        print(f"[API REST] Deleted incident {incident_id}: success={success}")
        return web.json_response({"status": "success", "deleted_id": incident_id, "deleted": success})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_incidents(request):
    """Returns all saved incident records with metadata."""
    incidents = alarm_manager.get_all_incidents()
    return web.json_response({
        "status": "success",
        "incidents": incidents,
        "count": len(incidents)
    })

async def health(request):
    return web.json_response({
        "status": "online",
        "service": "SAFECAM AI Python WebRTC Server",
        "models": ["YOLO11n Pose", "safecam_lstm_24.keras"],
        "bytetrack": "ENABLED",
        "lstm_pipeline": "ENABLED",
        "active_streams": len(pcs),
        "incidents_count": len(alarm_manager.get_all_incidents())
    })

async def on_shutdown(app):
    logger.info("[SERVER SHUTDOWN] Closing active WebRTC peer connections...")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

def create_app():
    app = web.Application()
    app.on_shutdown.append(on_shutdown)

    # Routes
    app.router.add_post("/offer", offer)
    app.router.add_post("/api/webrtc/offer", offer)
    app.router.add_get("/health", health)
    app.router.add_get("/api/alarms", get_alarms)
    app.router.add_get("/api/alarms/{camera_id}", get_alarms)
    app.router.add_post("/api/alarms/acknowledge", acknowledge_alarm)
    app.router.add_post("/api/alarms/delete", delete_alarm)
    app.router.add_get("/api/incidents", get_incidents)

    # Static file route for incident clips & snapshots
    os.makedirs(alarm_config.INCIDENTS_DIR, exist_ok=True)
    app.router.add_static("/incidents", alarm_config.INCIDENTS_DIR, show_index=True)

    # Configure CORS for React Frontend
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        )
    })

    for route in list(app.router.routes()):
        cors.add(route)

    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n==================================================")
    print(f" SAFECAM AI WebRTC Server  →  http://localhost:{port}")
    print(f" Models:     yolo11n-pose.pt + safecam_lstm_24.keras")
    print(f" Pipeline:   YOLO Pose -> LSTM Sequence Buffer")
    print(f" Endpoints:  POST /offer | GET /health | GET /api/incidents")
    print(f"==================================================")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)
