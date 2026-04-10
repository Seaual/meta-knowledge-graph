"""
PDF parser unit tests.
"""
from mkg.pdf_parser import PaperContent, PDFParser


def test_pdf_parser_import():
    """Test that PDFParser can be imported."""
    assert PDFParser is not None


def test_pdf_parser_instantiation():
    """Test that PDFParser can be instantiated."""
    parser = PDFParser()
    assert parser is not None


def test_pdf_parser_has_parse_method():
    """Test that PDFParser has a parse method."""
    parser = PDFParser()
    assert hasattr(parser, "parse")
    assert callable(parser.parse)


def test_paper_content_dataclass():
    """Test PaperContent can be created."""
    content = PaperContent(
        title="Test Paper",
        authors=["Alice", "Bob"],
        abstract="This is a test abstract.",
        full_text="Full text here.",
        sections={"Introduction": "Intro text"},
        metadata={"source": "test"},
    )
    assert content.title == "Test Paper"
    assert len(content.authors) == 2
    assert content.abstract == "This is a test abstract."
