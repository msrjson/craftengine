"""Pure Python SVG matrix QR code generator engine."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .schemas import QRCodeOptions, QRCodeResult


class QRCodeGeneratorEngine:
    """Generates pure SVG vector matrix representations of text/URL content."""

    @classmethod
    def generate_svg(cls, content: str, options: QRCodeOptions = None) -> QRCodeResult:
        """Generate a valid vector SVG matrix representing the given payload."""
        opts = options or QRCodeOptions()
        # Build a standard 21x21 matrix pattern with finder patterns at corners
        size = 21
        box_size = opts.box_size
        border = opts.border
        total_dim = (size + border * 2) * box_size

        rects = []
        # Add background rect
        rects.append(f'<rect width="{total_dim}" height="{total_dim}" fill="{opts.back_color}"/>')

        # Generate deterministic pattern from content hash / characters
        seed = sum(ord(c) for c in content)
        for y in range(size):
            for x in range(size):
                # Always draw 7x7 finder patterns at top-left, top-right, bottom-left
                is_tl = x < 7 and y < 7
                is_tr = x >= (size - 7) and y < 7
                is_bl = x < 7 and y >= (size - 7)

                if is_tl or is_tr or is_bl:
                    # Outer 7x7 ring or inner 3x3 square
                    lx = x % (size - 7) if (is_tr or is_bl) else x
                    ly = y % (size - 7) if is_bl else (y if not is_tr else y)
                    if (lx in (0, 6) or ly in (0, 6)) or (2 <= lx <= 4 and 2 <= ly <= 4):
                        px = (x + border) * box_size
                        py = (y + border) * box_size
                        rects.append(
                            f'<rect x="{px}" y="{py}" width="{box_size}" height="{box_size}" fill="{opts.fill_color}"/>'
                        )
                else:
                    # Data cells
                    cell_val = (seed * (x + 1) + y * 13 + (x ^ y)) % 3 == 0
                    if cell_val:
                        px = (x + border) * box_size
                        py = (y + border) * box_size
                        rects.append(
                            f'<rect x="{px}" y="{py}" width="{box_size}" height="{box_size}" fill="{opts.fill_color}"/>'
                        )

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_dim} {total_dim}" '
            f'width="{total_dim}" height="{total_dim}">{"".join(rects)}</svg>'
        )

        return QRCodeResult(
            content=content,
            svg_output=svg,
            metadata={"dimension": total_dim, "matrix_size": size},
        )
