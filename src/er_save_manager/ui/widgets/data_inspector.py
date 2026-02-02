"""Data Inspector Widget - Shows selected bytes as different data types."""

import struct

import customtkinter as ctk


class DataInspectorWidget(ctk.CTkFrame):
    """Widget that shows hex editor selection as various data types."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Title label
        ctk.CTkLabel(
            self,
            text="Data Inspector",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.data_labels = {}
        self._setup_ui()

    def _setup_ui(self):
        """Create the data inspector UI."""
        # Create scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(
            self,
            height=400,
            fg_color=("gray95", "gray10"),
        )
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Data type labels
        data_types = [
            ("Int8", "int8"),
            ("UInt8", "uint8"),
            ("Int16 LE", "int16_le"),
            ("UInt16 LE", "uint16_le"),
            ("Int16 BE", "int16_be"),
            ("UInt16 BE", "uint16_be"),
            ("Int32 LE", "int32_le"),
            ("UInt32 LE", "uint32_le"),
            ("Int32 BE", "int32_be"),
            ("UInt32 BE", "uint32_be"),
            ("Int64 LE", "int64_le"),
            ("UInt64 LE", "uint64_le"),
            ("Float LE", "float_le"),
            ("Float BE", "float_be"),
            ("Double LE", "double_le"),
            ("Double BE", "double_be"),
            ("UTF-8 String", "utf8"),
            ("UTF-16 LE String", "utf16_le"),
            ("Binary", "binary"),
        ]

        for i, (label_text, data_key) in enumerate(data_types):
            # Label
            ctk.CTkLabel(
                scrollable_frame,
                text=f"{label_text}:",
                font=("Segoe UI", 10, "bold"),
                width=100,
                anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=5, pady=2)

            # Value
            value_label = ctk.CTkLabel(
                scrollable_frame,
                text="--",
                font=("Consolas", 10),
                width=200,
                anchor="w",
            )
            value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
            self.data_labels[data_key] = value_label

    def update_from_bytes(self, data: bytes, offset: int = 0):
        """Update inspector with data at offset."""
        if not data:
            self._clear_values()
            return

        # Get bytes for inspection (up to 16 bytes)
        inspect_bytes = data[offset : offset + 16]

        # Int8
        if len(inspect_bytes) >= 1:
            self.data_labels["int8"].configure(
                text=str(struct.unpack("b", inspect_bytes[0:1])[0])
            )
            self.data_labels["uint8"].configure(text=str(inspect_bytes[0]))
        else:
            self.data_labels["int8"].configure(text="--")
            self.data_labels["uint8"].configure(text="--")

        # Int16
        if len(inspect_bytes) >= 2:
            self.data_labels["int16_le"].configure(
                text=str(struct.unpack("<h", inspect_bytes[0:2])[0])
            )
            self.data_labels["uint16_le"].configure(
                text=str(struct.unpack("<H", inspect_bytes[0:2])[0])
            )
            self.data_labels["int16_be"].configure(
                text=str(struct.unpack(">h", inspect_bytes[0:2])[0])
            )
            self.data_labels["uint16_be"].configure(
                text=str(struct.unpack(">H", inspect_bytes[0:2])[0])
            )
        else:
            self.data_labels["int16_le"].configure(text="--")
            self.data_labels["uint16_le"].configure(text="--")
            self.data_labels["int16_be"].configure(text="--")
            self.data_labels["uint16_be"].configure(text="--")

        # Int32
        if len(inspect_bytes) >= 4:
            self.data_labels["int32_le"].configure(
                text=str(struct.unpack("<i", inspect_bytes[0:4])[0])
            )
            self.data_labels["uint32_le"].configure(
                text=str(struct.unpack("<I", inspect_bytes[0:4])[0])
            )
            self.data_labels["int32_be"].configure(
                text=str(struct.unpack(">i", inspect_bytes[0:4])[0])
            )
            self.data_labels["uint32_be"].configure(
                text=str(struct.unpack(">I", inspect_bytes[0:4])[0])
            )
            self.data_labels["float_le"].configure(
                text=f"{struct.unpack('<f', inspect_bytes[0:4])[0]:.6f}"
            )
            self.data_labels["float_be"].configure(
                text=f"{struct.unpack('>f', inspect_bytes[0:4])[0]:.6f}"
            )
        else:
            self.data_labels["int32_le"].configure(text="--")
            self.data_labels["uint32_le"].configure(text="--")
            self.data_labels["int32_be"].configure(text="--")
            self.data_labels["uint32_be"].configure(text="--")
            self.data_labels["float_le"].configure(text="--")
            self.data_labels["float_be"].configure(text="--")

        # Int64
        if len(inspect_bytes) >= 8:
            self.data_labels["int64_le"].configure(
                text=str(struct.unpack("<q", inspect_bytes[0:8])[0])
            )
            self.data_labels["uint64_le"].configure(
                text=str(struct.unpack("<Q", inspect_bytes[0:8])[0])
            )
            self.data_labels["double_le"].configure(
                text=f"{struct.unpack('<d', inspect_bytes[0:8])[0]:.10f}"
            )
            self.data_labels["double_be"].configure(
                text=f"{struct.unpack('>d', inspect_bytes[0:8])[0]:.10f}"
            )
        else:
            self.data_labels["int64_le"].configure(text="--")
            self.data_labels["uint64_le"].configure(text="--")
            self.data_labels["double_le"].configure(text="--")
            self.data_labels["double_be"].configure(text="--")

        # Strings
        try:
            # UTF-8 (null-terminated)
            null_pos = inspect_bytes.find(b"\x00")
            if null_pos != -1:
                utf8_str = inspect_bytes[:null_pos].decode("utf-8", errors="ignore")
            else:
                utf8_str = inspect_bytes.decode("utf-8", errors="ignore")
            self.data_labels["utf8"].configure(
                text=utf8_str[:25] + ("..." if len(utf8_str) > 25 else "")
            )
        except Exception:
            self.data_labels["utf8"].configure(text="<invalid>")

        try:
            # UTF-16 LE (null-terminated)
            utf16_str = inspect_bytes.decode("utf-16-le", errors="ignore")
            null_pos = utf16_str.find("\x00")
            if null_pos != -1:
                utf16_str = utf16_str[:null_pos]
            self.data_labels["utf16_le"].configure(
                text=utf16_str[:25] + ("..." if len(utf16_str) > 25 else "")
            )
        except Exception:
            self.data_labels["utf16_le"].configure(text="<invalid>")

        # Binary
        binary_str = "".join(f"{b:08b} " for b in inspect_bytes[:4])
        self.data_labels["binary"].configure(text=binary_str.strip())

    def _clear_values(self):
        """Clear all values."""
        for label in self.data_labels.values():
            label.configure(text="--")
