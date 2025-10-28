# Application/services/geoserver_service.py
import requests
from Application.interfaces.i_geoserver_service import IGeoServerService
from Application.helpers.exceptions import GeoServerError

class GeoServerService(IGeoServerService):
    def __init__(self, base_url: str, user: str, password: str):
        self.base = base_url.rstrip("/")
        self.auth = (user, password)
        self.timeout = 30

    # --- helpers ---
    def _workspace_exists(self, workspace: str) -> bool:
        url = f"{self.base}/workspaces/{workspace}"
        r = requests.get(url, auth=self.auth, timeout=self.timeout)
        return r.status_code == 200

    def _style_exists(self, workspace: str, name: str) -> bool:
        url = f"{self.base}/workspaces/{workspace}/styles/{name}.xml"
        r = requests.get(url, auth=self.auth, timeout=self.timeout)
        return r.status_code == 200

    def _featuretype_exists(self, workspace: str, datastore: str, layer: str) -> bool:
        url = f"{self.base}/workspaces/{workspace}/datastores/{datastore}/featuretypes/{layer}.xml"
        r = requests.get(url, auth=self.auth, timeout=self.timeout)
        return r.status_code == 200

    @staticmethod
    def dump_response(r, max_bytes=200000):
        try:
            body_json = r.json()
        except Exception:
            # tenta decodificar com o melhor charset possível
            enc = r.encoding or getattr(r, 'apparent_encoding', None) or 'utf-8'
            try:
                body_text = r.content[:max_bytes].decode(enc, errors='replace')
            except Exception:
                body_text = r.text[:max_bytes] if hasattr(r, 'text') else None
            body_json = None

        return {
            "status_code": getattr(r, "status_code", None),
            "reason": getattr(r, "reason", None),
            "url": str(getattr(r, "url", None)),
            "headers": dict(getattr(r, "headers", {}) or {}),
            "request": {
                "method": getattr(getattr(r, "request", None), "method", None),
                "url": str(getattr(getattr(r, "request", None), "url", None)),
                "headers": dict(getattr(getattr(r, "request", None), "headers", {}) or {}),
                # cuidado: pode ser grande/binário
                "body_sample": (getattr(getattr(r, "request", None), "body", None) or b"")[:2000] if getattr(getattr(r, "request", None), "body", None) else None,
            },
            "elapsed_ms": int(getattr(r, "elapsed", 0).total_seconds() * 1000) if getattr(r,"elapsed",None) else None,
            "body_json": body_json,
            "body_text": None if body_json is not None else body_text,
            "body_bytes_len": len(getattr(r, "content", b"") or b""),
            "content_type": (getattr(r, "headers", {}) or {}).get("Content-Type"),
        }

    def create_style_registration_old(self, name: str, workspace: str, filename: str) -> None:
        url = f"{self.base}/workspaces/{workspace}/styles"
        data = f"<style><name>{name}</name><filename>{filename}</filename></style>"

        r = requests.post(
            url,
            data=data,
            headers={"Content-type": "text/xml"},
            auth=self.auth
        )

        # 201 (created) é o ideal; 401/403/500 podem surgir em setups — trate 409 (já existe)
        if r.status_code not in (200, 201, 409):
            r.raise_for_status()
        
    # ::1   
    def create_style_registration(self, name: str, workspace: str, filename: str) -> None:
        if not self._workspace_exists(workspace):
            raise GeoServerError(
                status_code=404, method="GET",
                url=f"{self.base}/workspaces/{workspace}",
                response_text="Workspace não encontrado.",
                message=f"Workspace '{workspace}' não existe no GeoServer."
            )
        if self._style_exists(workspace, name):
            return  # idempotente

        url = f"{self.base}/workspaces/{workspace}/styles"
        data = f"<style><name>{name}</name><filename>{filename}</filename></style>"
        r = requests.post(
            url, data=data,
            headers={"Content-type": "text/xml"},
            auth=self.auth, timeout=self.timeout
        )
        
        if r.status_code in (200, 201, 409):
            return
        if r.status_code == 500 and "already exists" in (r.text or "").lower():
            return

        body_preview = info["body_text"] or (str(info["body_json"]) if info["body_json"] else None)
        raise GeoServerError(
            status_code=r.status_code,
            method="POST",
            url=url,
            response_text=(body_preview or "")[:5000],
            message="Falha ao registrar style no GeoServer."
        )

    # ::2
    def upload_style_sld(self, name: str, workspace: str, sld_xml: str) -> None:
        url = f"{self.base}/workspaces/{workspace}/styles/{name}"
        r = requests.put(
            url,
            data=sld_xml.encode("utf-8"),
            headers={"Content-type": "application/vnd.ogc.se+xml", "Accept": "application/xml"},
            auth=self.auth, timeout=self.timeout
        )
        if r.status_code in (200, 201):
            return
        # antes: r.raise_for_status()
        raise GeoServerError(
            status_code=r.status_code, method="PUT", url=url,
            response_text=r.text,
            message="Falha ao enviar SLD para o GeoServer."
        )

    # ::3
    def create_featuretype(self, workspace: str, datastore: str, layer: str) -> None:
        if self._featuretype_exists(workspace, datastore, layer):
            return

        url = f"{self.base}/workspaces/{workspace}/datastores/{datastore}/featuretypes"
        payload = f"<featureType><name>{layer}</name></featureType>"
        r = requests.post(
            url, data=payload,
            headers={"Content-type": "text/xml", "Accept": "application/xml"},
            auth=self.auth, timeout=self.timeout
        )
        if r.status_code in (200, 201, 409):
            return
        if r.status_code == 500 and "already exists" in (r.text or "").lower():
            return
        raise GeoServerError(
            status_code=r.status_code, method="POST", url=url,
            response_text=r.text,
            message="Falha ao criar featureType no GeoServer."
        )

    # ::4
    def set_default_style(self, layer: str, workspace: str, style: str) -> None:
        url = f"{self.base}/layers/{workspace}:{layer}"
        payload = f"""<layer>
    <defaultStyle>
        <name>{style}</name>
        <workspace>{workspace}</workspace>
    </defaultStyle>
    </layer>"""
        r = requests.put(
            url, data=payload,
            headers={"Content-type": "text/xml", "Accept": "application/xml"},
            auth=self.auth, timeout=self.timeout
        )
        if r.status_code in (200, 201):
            return
        raise GeoServerError(
            status_code=r.status_code, method="PUT", url=url,
            response_text=r.text,
            message="Falha ao vincular defaultStyle no GeoServer."
        )

    # ::5
    def get_style_sld_length(self, workspace: str, name: str) -> int | None:
        url = f"{self.base}/workspaces/{workspace}/styles/{name}.sld"
        r = requests.get(url, auth=self.auth, timeout=self.timeout)
        if r.status_code != 200:
            return None
        return len(r.text or "")

    # ::6
    def check_layer_status(self, layer: str, workspace: str) -> int:
        url = f"{self.base}/layers/{workspace}:{layer}"
        r = requests.get(url, auth=self.auth, timeout=self.timeout)
        return r.status_code