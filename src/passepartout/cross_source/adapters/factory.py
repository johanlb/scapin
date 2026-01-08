"""
Adapter Factory for CrossSourceEngine.

Provides centralized adapter creation with:
- Lazy initialization (adapters created only when needed)
- Singleton pattern (adapters reused across requests)
- Configuration-based adapter selection
- Easy registration of new adapters
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from src.passepartout.cross_source.adapters.base import SourceAdapter

if TYPE_CHECKING:
    pass

logger = logging.getLogger("scapin.cross_source.factory")


# Type alias for adapter factory functions
AdapterCreator = Callable[..., SourceAdapter]


class AdapterFactory:
    """
    Factory for creating and managing source adapters.

    Provides lazy initialization and singleton behavior for adapters.
    Adapters are only created when first requested and reused thereafter.

    Example usage:
        factory = AdapterFactory()
        factory.register("email", EmailAdapter)
        factory.register("files", FilesAdapter, search_paths=[Path("~/")])

        email_adapter = factory.get("email")
        files_adapter = factory.get("files")
    """

    def __init__(self) -> None:
        """Initialize the factory with empty registrations."""
        self._creators: dict[str, tuple[AdapterCreator, dict[str, Any]]] = {}
        self._instances: dict[str, SourceAdapter] = {}

    def register(
        self,
        name: str,
        creator: AdapterCreator,
        **default_kwargs: Any,
    ) -> None:
        """
        Register an adapter creator with optional default arguments.

        Args:
            name: Unique name for this adapter (e.g., "email", "files")
            creator: Class or factory function that creates the adapter
            **default_kwargs: Default keyword arguments passed to creator
        """
        self._creators[name] = (creator, default_kwargs)
        logger.debug("Registered adapter: %s", name)

    def unregister(self, name: str) -> None:
        """
        Unregister an adapter and clear its cached instance.

        Args:
            name: Name of the adapter to unregister
        """
        if name in self._creators:
            del self._creators[name]
        if name in self._instances:
            del self._instances[name]
        logger.debug("Unregistered adapter: %s", name)

    def get(
        self,
        name: str,
        **override_kwargs: Any,
    ) -> SourceAdapter:
        """
        Get or create an adapter instance.

        Uses cached instance if available, otherwise creates new one.
        Override kwargs are merged with default kwargs.

        Args:
            name: Name of the adapter to get
            **override_kwargs: Keyword arguments to override defaults

        Returns:
            The adapter instance

        Raises:
            KeyError: If no adapter registered with given name
        """
        # Return cached instance if no overrides
        if not override_kwargs and name in self._instances:
            return self._instances[name]

        if name not in self._creators:
            raise KeyError(f"No adapter registered with name: {name}")

        creator, default_kwargs = self._creators[name]
        merged_kwargs = {**default_kwargs, **override_kwargs}

        try:
            instance = creator(**merged_kwargs)

            # Cache if no overrides (default configuration)
            if not override_kwargs:
                self._instances[name] = instance
                logger.debug("Created and cached adapter: %s", name)
            else:
                logger.debug("Created adapter: %s (with overrides)", name)

            return instance
        except Exception as e:
            logger.error("Failed to create adapter %s: %s", name, e)
            raise

    def get_all_available(self) -> list[SourceAdapter]:
        """
        Get all registered adapters that are currently available.

        Returns:
            List of available adapter instances
        """
        available = []
        for name in self._creators:
            try:
                adapter = self.get(name)
                if adapter.is_available:
                    available.append(adapter)
            except Exception as e:
                logger.warning("Failed to get adapter %s: %s", name, e)
        return available

    def get_by_source_name(self, source_name: str) -> SourceAdapter | None:
        """
        Get an adapter by its source_name property.

        This searches through cached instances and creates new ones
        as needed to find a match.

        Args:
            source_name: The source_name to look for (e.g., "email")

        Returns:
            Matching adapter or None if not found
        """
        for name in self._creators:
            try:
                adapter = self.get(name)
                if adapter.source_name == source_name:
                    return adapter
            except Exception:
                continue
        return None

    def clear_cache(self) -> None:
        """Clear all cached adapter instances."""
        self._instances.clear()
        logger.debug("Cleared adapter cache")

    @property
    def registered_names(self) -> list[str]:
        """Get list of registered adapter names."""
        return list(self._creators.keys())

    @property
    def cached_names(self) -> list[str]:
        """Get list of cached adapter instance names."""
        return list(self._instances.keys())


def create_default_factory() -> AdapterFactory:
    """
    Create a factory with all standard adapters registered.

    Returns:
        AdapterFactory with standard adapters
    """
    from src.passepartout.cross_source.adapters.calendar_adapter import CalendarAdapter
    from src.passepartout.cross_source.adapters.email_adapter import EmailAdapter
    from src.passepartout.cross_source.adapters.files_adapter import FilesAdapter
    from src.passepartout.cross_source.adapters.icloud_calendar_adapter import (
        ICloudCalendarAdapter,
    )
    from src.passepartout.cross_source.adapters.teams_adapter import TeamsAdapter
    from src.passepartout.cross_source.adapters.web_adapter import create_web_adapter
    from src.passepartout.cross_source.adapters.whatsapp_adapter import WhatsAppAdapter

    factory = AdapterFactory()

    # Register all standard adapters
    factory.register("email", EmailAdapter)
    factory.register("calendar", CalendarAdapter)
    factory.register("icloud_calendar", ICloudCalendarAdapter)
    factory.register("teams", TeamsAdapter)
    factory.register("files", FilesAdapter)
    factory.register("web", create_web_adapter)
    factory.register("whatsapp", WhatsAppAdapter)

    logger.info(
        "Created default adapter factory with %d adapters",
        len(factory.registered_names),
    )

    return factory


# Global factory instance for convenience
_default_factory: AdapterFactory | None = None


def get_default_factory() -> AdapterFactory:
    """
    Get the global default adapter factory.

    Creates it on first call (lazy initialization).

    Returns:
        The default AdapterFactory instance
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = create_default_factory()
    return _default_factory


def reset_default_factory() -> None:
    """Reset the global default factory (useful for testing)."""
    global _default_factory
    if _default_factory is not None:
        _default_factory.clear_cache()
    _default_factory = None
