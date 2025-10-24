import requests
from Application.interfaces.i_geoserver_service import IGeoServerService

class GeoServerService(IGeoServerService):
    def __init__(self, base_url: str, user: str, password: str):
        self.base = base_url.rstrip("/")
        self.auth = (user, password)

    # ::1 - cria o cadastro do style com filename <layer>.sld
    def create_style_registration(self, name: str, workspace: str, filename: str) -> None:
        url = f"{self.base}/workspaces/{workspace}/styles"
        data = f"<style><name>{name}</name><filename>{filename}</filename></style>"
        r = requests.post(url, data=data, headers={"Content-type": "text/xml"}, auth=self.auth)
        # 201 (created) é o ideal; 401/403/500 podem surgir em setups — trate 409 (já existe)
        if r.status_code not in (200, 201, 409):
            r.raise_for_status()

    # ::2 - faz upload (PUT) do conteúdo SLD no style criado
    def upload_style_sld(self, name: str, workspace: str, sld_xml: str) -> None:
        url = f"{self.base}/workspaces/{workspace}/styles/{name}"
        r = requests.put(
            url,
            data=sld_xml.encode("utf-8"),
            headers={"content-type": "application/vnd.ogc.se+xml"},
            auth=self.auth,
        )
        if r.status_code not in (200, 201):
            r.raise_for_status()

    # ::3 - publica a tabela como featureType
    def create_featuretype(self, workspace: str, datastore: str, layer: str) -> None:
        url = f"{self.base}/workspaces/{workspace}/datastores/{datastore}/featuretypes"
        payload = f"<featureType><name>{layer}</name></featureType>"
        r = requests.post(url, data=payload, headers={"Content-type": "text/xml"}, auth=self.auth)
        if r.status_code not in (200, 201, 409):
            r.raise_for_status()

    # ::4 - vincula o defaultStyle
    def set_default_style(self, layer: str, workspace: str, style: str) -> None:
        url = f"{self.base}/layers/{workspace}:{layer}"
        payload = f"""<layer>
                    <defaultStyle>
                        <name>{style}</name>
                        <workspace>{workspace}</workspace>
                    </defaultStyle>
                    </layer>"""
        r = requests.put(url, data=payload, headers={"Content-type": "text/xml"}, auth=self.auth)
        if r.status_code not in (200, 201):
            r.raise_for_status()

    # ::5 - baixa o SLD e retorna tamanho (para validar)
    def get_style_sld_length(self, workspace: str, name: str) -> int | None:
        url = f"{self.base}/workspaces/{workspace}/styles/{name}.sld"
        r = requests.get(url, auth=self.auth)
        if r.status_code != 200:
            return None
        content = r.text or ""
        return len(content)

    # ::6 - testa a layer
    def check_layer_status(self, layer: str, workspace: str) -> int:
        url = f"{self.base}/layers/{workspace}:{layer}"
        r = requests.get(url, auth=self.auth)
        return r.status_code
