import time
from typing import Optional


class CircuitBreaker:
    """
    Patrón Circuit Breaker para proteger llamadas externas a SimpleAPI.

    Estados:
        CLOSED   — Funcionamiento normal, las peticiones pasan.
        OPEN     — Servicio caído, las peticiones se rechazan inmediatamente.
        HALF_OPEN — Periodo de prueba para verificar recuperación.
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state: str = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time and (time.time() - self.last_failure_time > self.recovery_timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False

    @property
    def remaining_wait(self) -> int:
        """Segundos restantes antes de que el circuito pase a HALF_OPEN."""
        if self.state == "OPEN" and self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            return max(0, int(self.recovery_timeout - elapsed))
        return 0
