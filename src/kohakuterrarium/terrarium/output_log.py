"""Output log capture -- tee wrapper for creature observability."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kohakuterrarium.modules.output.base import OutputModule
from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LogEntry:
    """A single entry in the output log."""

    timestamp: datetime
    sequence: int
    content: str
    entry_type: str = "text"  # "text", "stream_flush", "activity"
    metadata: dict[str, Any] = field(default_factory=dict)

    def preview(self, max_len: int = 100) -> str:
        """Return a truncated preview of the content."""
        if len(self.content) <= max_len:
            return self.content
        return self.content[:max_len] + "..."


class OutputLogCapture:
    """
    Tee wrapper that captures output into a ring buffer.

    Wraps an existing OutputModule. All output goes to the wrapped
    module AND is logged into a deque for later retrieval.

    Usage::

        original_output = creature.agent.output_router.default_output
        capture = OutputLogCapture(original_output, max_entries=100)
        creature.agent.output_router.default_output = capture

        # Later:
        entries = capture.get_entries(last_n=10)
    """

    def __init__(self, wrapped: OutputModule, max_entries: int = 100):
        self._wrapped = wrapped
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._stream_buffer: str = ""
        self._max_entries = max_entries
        self._next_sequence = 1

    def _append_entry(
        self,
        *,
        content: str,
        entry_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._entries.append(
            LogEntry(
                timestamp=datetime.now(),
                sequence=self._next_sequence,
                content=content,
                entry_type=entry_type,
                metadata=dict(metadata or {}),
            )
        )
        self._next_sequence += 1

    # ------------------------------------------------------------------
    # OutputModule protocol
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the wrapped output module."""
        await self._wrapped.start()

    async def stop(self) -> None:
        """Flush remaining buffer, then stop the wrapped module."""
        await self.flush()
        await self._wrapped.stop()

    async def write(self, content: str) -> None:
        """Write content to wrapped module and log it."""
        await self._wrapped.write(content)
        if content:
            self._append_entry(content=content, entry_type="text")

    async def write_stream(self, chunk: str) -> None:
        """Stream a chunk to wrapped module and accumulate in buffer."""
        await self._wrapped.write_stream(chunk)
        self._stream_buffer += chunk

    async def flush(self) -> None:
        """Flush wrapped module and log any accumulated stream buffer."""
        await self._wrapped.flush()
        if self._stream_buffer:
            self._append_entry(content=self._stream_buffer, entry_type="stream_flush")
            self._stream_buffer = ""

    async def on_processing_start(self) -> None:
        """Forward processing start to wrapped module."""
        await self._wrapped.on_processing_start()

    async def on_processing_end(self) -> None:
        """Forward processing end to wrapped module."""
        await self._wrapped.on_processing_end()

    def on_activity(self, activity_type: str, detail: str) -> None:
        """Forward activity to wrapped module and log it."""
        self.on_activity_with_metadata(activity_type, detail, {})

    def on_activity_with_metadata(
        self,
        activity_type: str,
        detail: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        """Forward structured activity metadata when the wrapped output supports it."""
        if hasattr(self._wrapped, "on_activity_with_metadata"):
            self._wrapped.on_activity_with_metadata(
                activity_type, detail, metadata or {}
            )
        else:
            self._wrapped.on_activity(activity_type, detail)
        entry_metadata = dict(metadata or {})
        entry_metadata.setdefault("activity_type", activity_type)
        self._append_entry(
            content=detail,
            entry_type="activity",
            metadata=entry_metadata,
        )

    # ------------------------------------------------------------------
    # Log access
    # ------------------------------------------------------------------

    def get_entries(
        self,
        last_n: int = 20,
        entry_type: str | None = None,
    ) -> list[LogEntry]:
        """Get recent log entries, optionally filtered by type."""
        entries = list(self._entries)
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        return entries[-last_n:]

    def get_entries_since(
        self,
        sequence: int,
        *,
        entry_type: str | None = None,
    ) -> list[LogEntry]:
        """Return entries emitted strictly after ``sequence``."""
        entries = [entry for entry in self._entries if entry.sequence > sequence]
        if entry_type:
            entries = [entry for entry in entries if entry.entry_type == entry_type]
        return entries

    def get_text(self, last_n: int = 10) -> str:
        """Get recent text output concatenated (excludes activity)."""
        text_entries = self.get_entries(last_n=last_n, entry_type=None)
        return "\n".join(
            e.content for e in text_entries if e.entry_type in ("text", "stream_flush")
        )

    def clear(self) -> None:
        """Clear the log buffer."""
        self._entries.clear()
        self._stream_buffer = ""

    @property
    def entry_count(self) -> int:
        """Number of entries currently in the log."""
        return len(self._entries)

    @property
    def cursor(self) -> int:
        """Monotonic cursor for incremental reads."""
        return self._next_sequence - 1

    # ------------------------------------------------------------------
    # Pass-through helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Pass through reset to wrapped module if supported."""
        if hasattr(self._wrapped, "reset"):
            self._wrapped.reset()
