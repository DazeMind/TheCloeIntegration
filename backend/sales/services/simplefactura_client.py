import logging

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Mínimo de segundos entre llamadas al endpoint /token (rate limit 10 tokens/60 min).
_TOKEN_RATE_LIMIT_SEG = 1800


class SimpleFacturaClient:
    """
    Cliente HTTP de SimpleFactura (FASE 2).

    Solo cubre emisión de DTE: POST /invoiceV2/{sucursal} para boletas (39) y
    facturas (33). Autenticación JWT vía POST /token con caché en memoria.

    Modo SIMULATE: no toca la red. Emite un folio correlativo en memoria con
    forma de respuesta real, para probar el pipeline completo sin credenciales.
    """

    # Caché de token a nivel de clase: un process de worker comparte el estado
    # entre todas las ventas que procesa.
    _token = None
    _token_expira_en = None   # datetime aware (UTC)
    _ultimo_intento_token = None  # datetime aware (UTC)
    _folios = {}              # simulate: tipo_dte -> último folio entregado

    def __init__(self):
        self.base_url = settings.SIMPLEFACTURA_BASE_URL.rstrip('/')
        self.sucursal = settings.SIMPLEFACTURA_SUCURSAL
        self.simulate = settings.SIMPLEFACTURA_MODE == 'simulate'

    # ------------------------------------------------------------------ token
    def get_token(self):
        """Devuelve el token vigente, refrescándolo si es necesario.

        Máximo 1 llamada a /token cada 30 minutos RIGUROSO: si el último intento
        fue hace menos de 30 min se devuelve lo cacheado (aunque sea None).
        """
        if self.simulate:
            return 'simulado'

        ahora = timezone.now()

        # Barrera de rate limit: cachear siempre, incluso si el intento falló.
        if self._ultimo_intento_token is not None:
            if (ahora - self._ultimo_intento_token).total_seconds() < _TOKEN_RATE_LIMIT_SEG:
                return self._token

        # Token vigente -> reutilizar.
        if self._token and self._token_expira_en and ahora < self._token_expira_en:
            return self._token

        self._ultimo_intento_token = ahora
        url = f'{self.base_url}/token'
        payload = {
            'email': settings.SIMPLEFACTURA_EMAIL,
            'password': settings.SIMPLEFACTURA_PASSWORD,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=30.0)
        except httpx.HTTPError as exc:
            self._token = None
            self._token_expira_en = None
            logger.warning('SimpleFactura /token error de red: %s', exc)
            return self._token

        if resp.status_code == 200:
            data = resp.json()
            self._token = data.get('accessToken')
            expires_in = int(data.get('expiresIn', 86399))
            # Margen de 60s antes del vencimiento real.
            self._token_expira_en = ahora + timezone.timedelta(seconds=max(expires_in - 60, 60))
            logger.info('Token SimpleFactura obtenido (vigencia ~%ss)', expires_in)
        else:
            self._token = None
            self._token_expira_en = None
            logger.warning('SimpleFactura /token -> HTTP %s: %s', resp.status_code, resp.text[:300])
        return self._token

    # ---------------------------------------------------------------- emisión
    def emitir_dte(self, payload):
        """Emite un DTE en SimpleFactura.

        Devuelve siempre una tupla (respuesta_json|dict, http_status) y NUNCA
        lanza excepciones HTTP: el worker decide éxito/error con el status y la
        presencia de data.folio. En error de red http_status es None y el dict
        trae el detalle en 'errors'.
        """
        if self.simulate:
            respuesta = self._emision_simulada(payload)
            logger.info(
                'SimpleFactura SIMULADO -> DTE TipoDTE=%s folio=%s',
                payload['Documento']['Encabezado']['IdDoc']['TipoDTE'],
                respuesta['data']['folio'],
            )
            return respuesta, 200

        url = f'{self.base_url}/invoiceV2/{self.sucursal}'
        token = self.get_token()
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        except httpx.HTTPError as exc:
            return {
                'status': 'error',
                'message': f'Error de red hacia SimpleFactura: {exc}',
                'data': None,
                'errors': [str(exc)],
            }, None

        # 401 -> token caducado/revocado: invalidar caché y reintentar una vez.
        if resp.status_code == 401:
            self._token = None
            self._token_expira_en = None
            token = self.get_token()
            try:
                resp = httpx.post(
                    url, json=payload,
                    headers={**headers, 'Authorization': f'Bearer {token}'},
                    timeout=60.0,
                )
            except httpx.HTTPError as exc:
                return {
                    'status': 'error',
                    'message': f'Error de red hacia SimpleFactura: {exc}',
                    'data': None,
                    'errors': [str(exc)],
                }, None

        try:
            datos = resp.json()
        except ValueError:
            datos = {
                'status': 'error',
                'message': f'Respuesta no JSON (HTTP {resp.status_code})',
                'data': None,
                'errors': [resp.text[:500]],
            }
        return datos, resp.status_code

    # -------------------------------------------------------------- simulado
    def _emision_simulada(self, payload):
        encabezado = payload.get('Documento', {}).get('Encabezado', {})
        id_doc = encabezado.get('IdDoc', {})
        emisor = encabezado.get('Emisor', {})
        receptor = encabezado.get('Receptor', {})
        totales = encabezado.get('Totales', {})
        tipo = id_doc.get('TipoDTE', 39)
        folio = self._siguiente_folio(tipo)
        return {
            'status': 'ok',
            'message': f'se emitió el DTE tipo {tipo} con folio {folio} (simulado)',
            'data': {
                'tipoDTE': tipo,
                'rutEmisor': emisor.get('RUTEmisor', ''),
                'rutReceptor': receptor.get('RUTRecep', ''),
                'folio': folio,
                'fechaEmision': id_doc.get('FchEmis'),
                'total': totales.get('MntTotal'),
            },
            'errors': [],
        }

    def _siguiente_folio(self, tipo):
        """Folio correlativo en memoria (por tipo de DTE). Reinicia al reiniciar
        el proceso; suficiente para el modo simulado. Se siembra alto para
        minimizar colisiones con folios reales previos."""
        self._folios[tipo] = self._folios.get(tipo, 4000) + 1
        return self._folios[tipo]