# Application/services/geoserver_service.py
import requests
from Application.interfaces.i_geoserver_service import IGeoServerService

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

    # ::1
    def create_style_registration(self, name: str, workspace: str, filename: str) -> None:
        if not self._workspace_exists(workspace):
            raise RuntimeError(f"Workspace '{workspace}' não existe no GeoServer.")
        if self._style_exists(workspace, name):
            return  # idempotente

        url = f"{self.base}/workspaces/{workspace}/styles"
        data = f"<style><name>{name}</name><filename>{filename}</filename></style>"
        r = requests.post(
            url, data=data,
            headers={"Content-type": "text/xml", "Accept": "application/xml"},
            auth=self.auth, timeout=self.timeout
        )
        # aceitar 'já existe' mesmo que a instância retorne 409 ou 500 com mensagem
        if r.status_code in (200, 201, 409):
            return
        if r.status_code == 500 and "already exists" in (r.text or "").lower():
            return
        r.raise_for_status()

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
        r.raise_for_status()

    # ::3 (idempotente)
    def create_featuretype(self, workspace: str, datastore: str, layer: str) -> None:
        # se já existe, não falha
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
        # algumas instâncias retornam 500 com 'already exists'
        if r.status_code == 500 and "already exists" in (r.text or "").lower():
            return
        r.raise_for_status()

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
        r.raise_for_status()

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
