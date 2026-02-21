"""
Digital FTE - PDF Generator
Generates PDF CVs using Jinja2 templates and WeasyPrint.
"""

import structlog
from typing import Dict, Any
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS

from app.config import settings

logger = structlog.get_logger()

# Setup Jinja2 environment
TEMPLATE_DIR = Path("app/templates")
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def generate_cv_pdf(cv_data: Dict[str, Any], template_name: str = "cv/modern.html") -> bytes:
    """
    Generate a PDF from CV data using the specified HTML template.
    Returns the binary content of the PDF.
    """
    try:
        template = env.get_template(template_name)
        html_content = template.render(cv=cv_data)

        # Base CSS for fonts and basic print styles
        base_css = CSS(string="""
            @page {
                size: A4;
                margin: 0;
            }
            body {
                font-family: 'Helvetica', 'Arial', sans-serif;
                -webkit-print-color-adjust: exact;
            }
        """)

        # Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[base_css])
        
        logger.info("pdf_generated", size=len(pdf_bytes))
        return pdf_bytes

    except Exception as e:
        logger.error("pdf_generation_failed", error=str(e))
        raise
