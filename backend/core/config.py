from dataclasses import dataclass
from django.conf import settings as django_settings


@dataclass
class SimpleAPIConfig:
    api_key: str = ""
    base_url: str = "https://api.simpleapi.cl/api/v1"
    timeout: int = 30

    @classmethod
    def from_django_settings(cls) -> "SimpleAPIConfig":
        return cls(
            api_key=django_settings.SIMPLEAPI_KEY,
            base_url=django_settings.SIMPLEAPI_BASE_URL,
            timeout=django_settings.SIMPLEAPI_TIMEOUT,
        )


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout: int = 30

    @classmethod
    def from_django_settings(cls) -> "CircuitBreakerConfig":
        return cls(
            failure_threshold=django_settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=django_settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        )


@dataclass
class AppConfig:
    debug: bool = True
    allowed_hosts: list = None

    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = []

    @classmethod
    def from_django_settings(cls) -> "AppConfig":
        return cls(
            debug=django_settings.DEBUG,
            allowed_hosts=django_settings.ALLOWED_HOSTS,
        )


# Singleton instances
simpleapi_config = SimpleAPIConfig.from_django_settings()
circuit_breaker_config = CircuitBreakerConfig.from_django_settings()
app_config = AppConfig.from_django_settings()
