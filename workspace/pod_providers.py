"""
pod_providers.py -- Provider adapter interface and registry

Provides a unified interface for Printify and Printful uploads, allowing
backend orchestration to be provider-agnostic while maintaining provider-specific logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Literal
from dataclasses import dataclass


@dataclass
class UploadResult:
    """Unified result from provider upload operations."""
    product_id: str
    image_id: str
    external_listing_id: str | None = None
    external_listing_url: str | None = None
    provider_url: str | None = None
    status: str = "created"  # created, draft, published
    metadata: dict[str, Any] | None = None


class ProviderAdapter(ABC):
    """Abstract base for provider adapters (Printify, Printful, etc.)."""
    
    @abstractmethod
    def check_config(self) -> bool:
        """Verify provider credentials are configured."""
        pass
    
    @abstractmethod
    def upload_image(self, filepath: str) -> str:
        """Upload design image and return image ID."""
        pass
    
    @abstractmethod
    def create_product(
        self,
        image_id: str,
        title: str,
        description: str,
        cfg: dict,
        design_name: str | None = None,
    ) -> UploadResult:
        """Create a product with the uploaded image."""
        pass
    
    @abstractmethod
    def publish_product(self, product_id: str) -> None:
        """Publish product to connected sales channel."""
        pass
    
    @abstractmethod
    def get_product(self, product_id: str) -> dict[str, Any]:
        """Fetch product details (for external listing ID sync)."""
        pass


class PrintifyAdapter(ProviderAdapter):
    """Adapter wrapping existing Printify integration."""
    
    def __init__(self):
        try:
            from printify_upload import (
                check_config as printify_check_config,
                upload_image as printify_upload_image,
                create_product as printify_create_product,
                publish_product as printify_publish_product,
                get_product as printify_get_product,
            )
            self._check_config = printify_check_config
            self._upload_image = printify_upload_image
            self._create_product = printify_create_product
            self._publish_product = printify_publish_product
            self._get_product = printify_get_product
            self._available = True
        except ImportError:
            self._check_config = lambda: False
            self._available = False
    
    def check_config(self) -> bool:
        if not self._available:
            return False
        try:
            result = self._check_config()
            return True if result is None else bool(result)
        except BaseException:
            return False
    
    def upload_image(self, filepath: str) -> str:
        if not self._available:
            raise RuntimeError("Printify module not available")
        return self._upload_image(filepath)
    
    def create_product(
        self,
        image_id: str,
        title: str,
        description: str,
        cfg: dict,
        design_name: str | None = None,
    ) -> UploadResult:
        if not self._available:
            raise RuntimeError("Printify module not available")
        
        product_id = self._create_product(
            image_id, title, description, cfg, design_name=design_name
        )
        
        # Build Printify product URL
        provider_url = f"https://www.printify.com/app/products/{product_id}"
        
        return UploadResult(
            product_id=str(product_id),
            image_id=image_id,
            provider_url=provider_url,
            status="created",
        )
    
    def publish_product(self, product_id: str) -> None:
        if not self._available:
            raise RuntimeError("Printify module not available")
        self._publish_product(product_id)
    
    def get_product(self, product_id: str) -> dict[str, Any]:
        if not self._available:
            raise RuntimeError("Printify module not available")
        return self._get_product(product_id)


class PrintfulAdapter(ProviderAdapter):
    """Adapter for Printful integration (Phase 2)."""
    
    def __init__(self):
        try:
            from printful_upload import (
                check_config as printful_check_config,
                upload_image as printful_upload_image,
                create_product as printful_create_product,
                publish_product as printful_publish_product,
                get_product as printful_get_product,
            )
            self._check_config = printful_check_config
            self._upload_image = printful_upload_image
            self._create_product = printful_create_product
            self._publish_product = printful_publish_product
            self._get_product = printful_get_product
            self._available = True
        except ImportError:
            self._check_config = lambda: False
            self._available = False
    
    def check_config(self) -> bool:
        if not self._available:
            return False
        try:
            result = self._check_config()
            return True if result is None else bool(result)
        except BaseException:
            return False
    
    def upload_image(self, filepath: str) -> str:
        if not self._available:
            raise RuntimeError("Printful module not available")
        return self._upload_image(filepath)
    
    def create_product(
        self,
        image_id: str,
        title: str,
        description: str,
        cfg: dict,
        design_name: str | None = None,
    ) -> UploadResult:
        if not self._available:
            raise RuntimeError("Printful module not available")
        
        product_id = self._create_product(
            image_id, title, description, cfg, design_name=design_name
        )
        
        # Build Printful product URL
        provider_url = f"https://www.printful.com/dashboard/products/{product_id}"
        
        return UploadResult(
            product_id=str(product_id),
            image_id=image_id,
            provider_url=provider_url,
            status="created",
        )
    
    def publish_product(self, product_id: str) -> None:
        if not self._available:
            raise RuntimeError("Printful module not available")
        self._publish_product(product_id)
    
    def get_product(self, product_id: str) -> dict[str, Any]:
        if not self._available:
            raise RuntimeError("Printful module not available")
        return self._get_product(product_id)


class ProviderRegistry:
    """Registry of available provider adapters."""
    
    def __init__(self):
        self.adapters = {
            "printify": PrintifyAdapter(),
            "printful": PrintfulAdapter(),
        }
    
    def get_adapter(self, provider: Literal["printify", "printful"]) -> ProviderAdapter:
        """Get adapter for provider."""
        if provider not in self.adapters:
            raise ValueError(f"Unknown provider: {provider}")
        return self.adapters[provider]
    
    def is_configured(self, provider: Literal["printify", "printful"]) -> bool:
        """Check if provider is configured."""
        adapter = self.get_adapter(provider)
        return adapter.check_config()


# Global registry instance
PROVIDER_REGISTRY = ProviderRegistry()
