"""
EfiBank (Gerencianet) Pix client — placeholder for Phase 9.

Requires:
- EfiBank API credentials (.p12 certificate)
- Client ID and Client Secret
"""


class EfiClient:
    """Generate Pix charges via EfiBank API."""

    def __init__(self, client_id: str, client_secret: str, cert_path: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cert_path = cert_path
        self._token = None

    def authenticate(self):
        """Obtain an OAuth2 token from EfiBank."""
        raise NotImplementedError("EfiBank integration pending (Phase 9)")

    def create_charge(self, amount: float, description: str, payer_cpf: str = ""):
        """Create an immediate Pix charge and return QR code data."""
        raise NotImplementedError("EfiBank integration pending (Phase 9)")

    def get_qr_code(self, loc_id: str) -> dict:
        """Fetch the QR Code image for a given location id."""
        raise NotImplementedError("EfiBank integration pending (Phase 9)")
