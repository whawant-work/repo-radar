"""
HTML Renderer Module

WBS 6.2 Day4: HTML 렌더러(Jinja2)

목표: Jinja2 기반 HTML 렌더러 구현, 빌드 경로에 날짜별 출력.

기능:
- Jinja2 템플릿 로드 및 컨텍스트 바인딩
- Digest 데이터를 HTML로 변환
- 날짜별 디렉토리 구조로 출력 (output/YYYY-MM-DD/index.html)
- JSON 출력 옵션 지원

사용법:
    from repo_radar.renderer import Renderer

    renderer = Renderer()
    digest = build_digest(buckets)

    # HTML 렌더링
    html = renderer.render_html(digest)

    # 파일로 저장
    output_path = renderer.save_digest(digest, output_dir="output", format="html")
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class Renderer:
    """HTML/JSON 렌더러 클래스."""

    def __init__(self, template_dir: Path | str | None = None):
        """
        Initialize the renderer.

        Args:
            template_dir: Path to template directory. If None, uses default location.
        """
        if template_dir is None:
            # Default to templates directory in the package
            template_dir = Path(__file__).parent / "templates"
        else:
            template_dir = Path(template_dir)

        if not template_dir.exists():
            raise ValueError(f"Template directory not found: {template_dir}")

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_html(self, digest: dict[str, Any]) -> str:
        """
        Render digest data as HTML.

        Args:
            digest: Digest dictionary from build_digest()

        Returns:
            HTML string
        """
        template = self.env.get_template("digest.html")
        return template.render(
            generated_at=digest.get("generated_at", ""),
            kpis=digest.get("kpis", {}),
            sections=digest.get("sections", {}),
        )

    def render_json(self, digest: dict[str, Any], *, indent: int = 2) -> str:
        """
        Render digest data as JSON.

        Args:
            digest: Digest dictionary from build_digest()
            indent: JSON indentation level (default: 2)

        Returns:
            JSON string
        """
        return json.dumps(digest, indent=indent, ensure_ascii=False)

    def save_digest(
        self,
        digest: dict[str, Any],
        *,
        output_dir: Path | str = "output",
        format: str = "html",  # noqa: A002
        date: str | None = None,
    ) -> Path:
        """
        Save digest to file with date-based directory structure.

        Args:
            digest: Digest dictionary from build_digest()
            output_dir: Base output directory (default: "output")
            format: Output format - "html" or "json" (default: "html")
            date: Date string in YYYY-MM-DD format. If None, uses current UTC date.

        Returns:
            Path to the saved file

        Raises:
            ValueError: If format is not supported
        """
        if format not in ("html", "json"):
            raise ValueError(f"Unsupported format: {format}. Use 'html' or 'json'.")

        # Determine date for directory structure
        if date is None:
            date = datetime.now(UTC).strftime("%Y-%m-%d")

        # Create date-based directory
        output_path = Path(output_dir) / date
        output_path.mkdir(parents=True, exist_ok=True)

        # Render content
        if format == "html":
            content = self.render_html(digest)
            filename = "index.html"
        else:  # json
            content = self.render_json(digest)
            filename = "digest.json"

        # Write to file
        file_path = output_path / filename
        file_path.write_text(content, encoding="utf-8")

        return file_path

    def save_both(
        self,
        digest: dict[str, Any],
        *,
        output_dir: Path | str = "output",
        date: str | None = None,
    ) -> tuple[Path, Path]:
        """
        Save digest in both HTML and JSON formats.

        Args:
            digest: Digest dictionary from build_digest()
            output_dir: Base output directory (default: "output")
            date: Date string in YYYY-MM-DD format. If None, uses current UTC date.

        Returns:
            Tuple of (html_path, json_path)
        """
        html_path = self.save_digest(digest, output_dir=output_dir, format="html", date=date)
        json_path = self.save_digest(digest, output_dir=output_dir, format="json", date=date)
        return html_path, json_path


__all__ = ["Renderer"]
