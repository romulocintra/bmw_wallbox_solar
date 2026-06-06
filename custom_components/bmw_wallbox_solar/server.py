"""WebSocket server that acts as an OCPP Central System for BMW Wallbox.

SSL modes
---------
1. Explicit cert + key paths  →  WSS using provided files
2. Auto-detect HA cert        →  WSS reusing /ssl/fullchain.pem + /ssl/privkey.pem
3. No SSL / plain mode        →  Plain ws:// (works for non-BMW chargers or when a
                                 reverse-proxy like Nginx/Caddy handles TLS in front)

BMW/Mini wallboxes enforce WSS in their firmware. For a plain-ws setup, place a
reverse proxy (e.g. Nginx, Caddy, or the HA Nginx Proxy Manager add-on) in front
that terminates TLS and forwards to ws://localhost:<port>.
"""
from __future__ import annotations

import logging
import ssl
from pathlib import Path
from typing import Callable

try:
    import websockets
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

from .charger import BMWWallboxChargePoint, ChargerState
from .const import OCPP_SUBPROTOCOL, SSL_MODE_AUTO, SSL_MODE_MANUAL, SSL_MODE_NONE

_LOGGER = logging.getLogger(__name__)

# Common locations where HA stores its own Let's Encrypt certificate
_HA_CERT_CANDIDATES = [
    ("/ssl/fullchain.pem", "/ssl/privkey.pem"),
    ("/ssl/certificate.pem", "/ssl/privkey.pem"),
    ("/config/ssl/fullchain.pem", "/config/ssl/privkey.pem"),
]


class OCPPServer:
    """Manages the WebSocket server and connected charge points."""

    def __init__(
        self,
        port: int,
        ssl_mode: str,                  # SSL_MODE_NONE | SSL_MODE_AUTO | SSL_MODE_MANUAL
        ssl_cert: str | None,
        ssl_key: str | None,
        expected_charge_point_id: str | None,
        rfid_token: str | None,
        on_connect: Callable | None = None,
        on_disconnect: Callable | None = None,
    ) -> None:
        self._port = port
        self._ssl_mode = ssl_mode
        self._ssl_cert = ssl_cert or ""
        self._ssl_key = ssl_key or ""
        self._expected_cp_id = expected_charge_point_id
        self._rfid_token = rfid_token
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

        self._server = None
        self.charge_point: BMWWallboxChargePoint | None = None
        self.state: ChargerState = ChargerState()
        self.ssl_active: bool = False  # set after start, readable by diagnostics sensor

    # ── SSL ──────────────────────────────────────────────────────────────────

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        """Return an SSLContext or None (plain WS) based on ssl_mode."""

        if self._ssl_mode == SSL_MODE_NONE:
            _LOGGER.info(
                "SSL mode: plain WebSocket (ws://). "
                "Use a reverse proxy (Nginx/Caddy) for TLS if your wallbox requires WSS."
            )
            return None

        if self._ssl_mode == SSL_MODE_AUTO:
            return self._auto_detect_ha_cert()

        # SSL_MODE_MANUAL
        return self._load_cert(self._ssl_cert, self._ssl_key)

    def _auto_detect_ha_cert(self) -> ssl.SSLContext | None:
        """Try to reuse the HA built-in Let's Encrypt certificate."""
        for cert_path, key_path in _HA_CERT_CANDIDATES:
            if Path(cert_path).exists() and Path(key_path).exists():
                _LOGGER.info("SSL auto-detect: found HA cert at %s", cert_path)
                ctx = self._load_cert(cert_path, key_path)
                if ctx:
                    return ctx
        _LOGGER.warning(
            "SSL auto-detect: no HA certificate found in standard locations %s. "
            "Falling back to plain WebSocket. "
            "Configure SSL manually or set up a reverse proxy.",
            [c for c, _ in _HA_CERT_CANDIDATES],
        )
        return None

    def _load_cert(self, cert: str, key: str) -> ssl.SSLContext | None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            ctx.load_cert_chain(cert, key)
            _LOGGER.info("SSL loaded: cert=%s", cert)
            return ctx
        except FileNotFoundError:
            _LOGGER.error("SSL cert/key not found: cert=%s key=%s", cert, key)
        except ssl.SSLError as exc:
            _LOGGER.error("SSL error loading cert: %s", exc)
        except Exception as exc:
            _LOGGER.error("Unexpected SSL error: %s", exc)
        return None

    # ── Connection handler ───────────────────────────────────────────────────

    async def _on_new_connection(self, websocket) -> None:
        """Called for each new WebSocket connection."""
        # Extract charge point ID from the URL path
        path = websocket.request.path if hasattr(websocket, "request") else getattr(websocket, "path", "/unknown")
        cp_id = path.strip("/").split("/")[-1]

        if self._expected_cp_id and cp_id != self._expected_cp_id:
            _LOGGER.warning("Rejected connection from unexpected CP ID: %s (expected %s)", cp_id, self._expected_cp_id)
            await websocket.close(code=1008, reason="Unexpected Charge Point ID")
            return

        _LOGGER.info("BMW Wallbox connecting: %s", cp_id)

        # Disconnect any existing session
        if self.charge_point is not None:
            _LOGGER.info("Replacing existing connection for %s", cp_id)
            self.charge_point.disconnect()

        self.charge_point = BMWWallboxChargePoint(
            id=cp_id,
            connection=websocket,
            state=self.state,
            rfid_token=self._rfid_token,
        )

        if self._on_connect:
            self._on_connect(self.charge_point)

        try:
            await self.charge_point.start()
        except Exception as exc:
            _LOGGER.error("Charge point session error: %s", exc)
        finally:
            _LOGGER.info("BMW Wallbox disconnected: %s", cp_id)
            self.charge_point.disconnect()
            self.charge_point = None
            if self._on_disconnect:
                self._on_disconnect()

    # ── Server lifecycle ─────────────────────────────────────────────────────

    async def async_start(self) -> None:
        """Start the WebSocket server."""
        if not DEPS_AVAILABLE:
            _LOGGER.error("Required libraries (ocpp, websockets) not installed")
            return

        ssl_ctx = self._build_ssl_context()
        self.ssl_active = ssl_ctx is not None
        scheme = "wss" if self.ssl_active else "ws"
        _LOGGER.info("Starting OCPP server on %s://0.0.0.0:%d", scheme, self._port)

        self._server = await websockets.serve(
            self._on_new_connection,
            "0.0.0.0",
            self._port,
            subprotocols=[OCPP_SUBPROTOCOL],
            ssl=ssl_ctx,
        )
        _LOGGER.info("OCPP server started on port %d (SSL=%s)", self._port, self.ssl_active)

    async def async_stop(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            _LOGGER.info("OCPP server stopped")
