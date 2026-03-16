from .models import Pago


class PagoService:
    def procesar(self, pago: Pago) -> bool:
        return pago.procesar_pago()
