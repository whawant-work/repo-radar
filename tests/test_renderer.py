"""
Tests for repo_radar.renderer module
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from repo_radar.renderer import Renderer


@pytest.fixture
def sample_digest():
    """Sample digest data for testing."""
    return {
        "generated_at": "2026-02-11T12:00:00Z",
        "kpis": {
            "waiting_pr_count": 5,
            "avg_waiting_days": 2.3,
        },
        "sections": {
            "review": [
                {
                    "id": "PR_123",
                    "type": "PR",
                    "repo": "owner/repo1",
                    "number": 42,
                    "title": "Add new feature",
                    "priority": 60,
                    "labels": ["feature", "urgent"],
                },
                {
                    "id": "PR_124",
                    "type": "PR",
                    "repo": "owner/repo2",
                    "number": 10,
                    "title": "Fix bug in parser",
                    "priority": 45,
                    "labels": ["bug"],
                },
            ],
            "reply": [
                {
                    "id": "Issue_200",
                    "type": "Issue",
                    "repo": "owner/repo1",
                    "number": 15,
                    "title": "How to configure X?",
                    "priority": 35,
                    "labels": ["question"],
                }
            ],
            "develop": [],
        },
    }


def test_renderer_init_default():
    """Test Renderer initialization with default template directory."""
    renderer = Renderer()
    assert renderer.template_dir.exists()
    assert (renderer.template_dir / "base.html").exists()
    assert (renderer.template_dir / "digest.html").exists()


def test_renderer_init_custom(tmp_path):
    """Test Renderer initialization with custom template directory."""
    # Create custom template directory
    custom_templates = tmp_path / "custom_templates"
    custom_templates.mkdir()
    (custom_templates / "digest.html").write_text("Custom template")

    # Should fail with non-existent directory
    with pytest.raises(ValueError, match="Template directory not found"):
        Renderer(template_dir=tmp_path / "nonexistent")

    # Should succeed with valid directory
    renderer = Renderer(template_dir=custom_templates)
    assert renderer.template_dir == custom_templates


def test_render_html(sample_digest):
    """Test HTML rendering."""
    renderer = Renderer()
    html = renderer.render_html(sample_digest)

    # Check essential content
    assert "<!DOCTYPE html>" in html
    assert "repo-radar Daily Digest" in html
    assert "2026-02-11T12:00:00Z" in html

    # Check KPIs
    assert "5" in html  # waiting_pr_count
    assert "2.3" in html  # avg_waiting_days

    # Check sections
    assert "Review Needed" in html
    assert "Reply Needed" in html
    assert "In Development" in html

    # Check items
    assert "Add new feature" in html
    assert "Fix bug in parser" in html
    assert "How to configure X?" in html
    assert "owner/repo1" in html

    # Check links
    assert "https://github.com/owner/repo1/pull/42" in html
    assert "https://github.com/owner/repo2/pull/10" in html
    assert "https://github.com/owner/repo1/issues/15" in html

    # Check labels
    assert "feature" in html
    assert "urgent" in html
    assert "bug" in html
    assert "question" in html


def test_render_html_empty_sections():
    """Test HTML rendering with empty sections."""
    digest = {
        "generated_at": "2026-02-11T12:00:00Z",
        "kpis": {"waiting_pr_count": 0, "avg_waiting_days": 0.0},
        "sections": {"review": [], "reply": [], "develop": []},
    }

    renderer = Renderer()
    html = renderer.render_html(digest)

    # Should have empty section messages
    assert "No items need review" in html or "No items" in html
    assert html  # Should not be empty


def test_render_json(sample_digest):
    """Test JSON rendering."""
    renderer = Renderer()
    json_str = renderer.render_json(sample_digest)

    # Parse to verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed == sample_digest

    # Check formatting
    assert "\n" in json_str  # Should be indented


def test_save_digest_html(sample_digest, tmp_path):
    """Test saving digest as HTML."""
    renderer = Renderer()
    output_path = renderer.save_digest(
        sample_digest, output_dir=tmp_path, format="html", date="2026-02-11"
    )

    # Check path structure
    assert output_path == tmp_path / "2026-02-11" / "index.html"
    assert output_path.exists()

    # Verify content
    content = output_path.read_text()
    assert "<!DOCTYPE html>" in content
    assert "Add new feature" in content


def test_save_digest_json(sample_digest, tmp_path):
    """Test saving digest as JSON."""
    renderer = Renderer()
    output_path = renderer.save_digest(
        sample_digest, output_dir=tmp_path, format="json", date="2026-02-11"
    )

    # Check path structure
    assert output_path == tmp_path / "2026-02-11" / "digest.json"
    assert output_path.exists()

    # Verify content
    content = json.loads(output_path.read_text())
    assert content == sample_digest


def test_save_digest_default_date(sample_digest, tmp_path):
    """Test saving digest with default date (current UTC date)."""
    renderer = Renderer()
    output_path = renderer.save_digest(sample_digest, output_dir=tmp_path, format="html")

    # Should use current UTC date
    expected_date = datetime.now(UTC).strftime("%Y-%m-%d")
    assert output_path == tmp_path / expected_date / "index.html"
    assert output_path.exists()


def test_save_digest_invalid_format(sample_digest, tmp_path):
    """Test saving digest with invalid format."""
    renderer = Renderer()

    with pytest.raises(ValueError, match="Unsupported format"):
        renderer.save_digest(sample_digest, output_dir=tmp_path, format="xml")


def test_save_both(sample_digest, tmp_path):
    """Test saving digest in both HTML and JSON formats."""
    renderer = Renderer()
    html_path, json_path = renderer.save_both(sample_digest, output_dir=tmp_path, date="2026-02-11")

    # Check both files exist
    assert html_path == tmp_path / "2026-02-11" / "index.html"
    assert json_path == tmp_path / "2026-02-11" / "digest.json"
    assert html_path.exists()
    assert json_path.exists()

    # Verify content
    assert "<!DOCTYPE html>" in html_path.read_text()
    assert json.loads(json_path.read_text()) == sample_digest


def test_save_digest_creates_directories(sample_digest, tmp_path):
    """Test that save_digest creates necessary directories."""
    renderer = Renderer()

    # Use nested path that doesn't exist
    output_dir = tmp_path / "nested" / "output"
    output_path = renderer.save_digest(sample_digest, output_dir=output_dir, date="2026-02-11")

    assert output_path.exists()
    assert output_path.parent.name == "2026-02-11"


def test_html_priority_badges(sample_digest):
    """Test that HTML includes priority badges."""
    renderer = Renderer()
    html = renderer.render_html(sample_digest)

    # High priority item (60)
    assert "priority-high" in html.lower() or "High Priority" in html

    # Medium priority item (45)
    assert "priority-medium" in html.lower() or "Medium" in html


def test_html_accessibility_features():
    """Test that HTML includes accessibility features."""
    digest = {
        "generated_at": "2026-02-11T12:00:00Z",
        "kpis": {"waiting_pr_count": 0, "avg_waiting_days": 0.0},
        "sections": {"review": [], "reply": [], "develop": []},
    }

    renderer = Renderer()
    html = renderer.render_html(digest)

    # Check for accessibility features
    assert 'lang="ko"' in html  # Language attribute
    assert 'charset="UTF-8"' in html
    assert 'rel="noopener noreferrer"' in html  # Security for external links


def test_html_responsive_design():
    """Test that HTML includes responsive design elements."""
    digest = {
        "generated_at": "2026-02-11T12:00:00Z",
        "kpis": {"waiting_pr_count": 0, "avg_waiting_days": 0.0},
        "sections": {"review": [], "reply": [], "develop": []},
    }

    renderer = Renderer()
    html = renderer.render_html(digest)

    # Check for viewport meta tag
    assert 'name="viewport"' in html
    assert "width=device-width" in html
