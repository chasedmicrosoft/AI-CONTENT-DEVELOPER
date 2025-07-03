"""
Content extraction from various sources
"""
from pathlib import Path
from typing import Optional
import logging

from ..utils import read, error_handler, get_import
from ..utils.imports import HAS_DOCX, HAS_PDF, HAS_WEB

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extract content from various file types and URLs"""
    
    def __init__(self, config):
        self.config = config
    
    @error_handler
    def extract(self, source: str, repo_path: Optional[Path] = None) -> Optional[str]:
        """Extract content from a source (file, URL, or raw text)"""
        logger.info(f"ContentExtractor.extract called with source: {source}")
        
        # Check if it's a URL
        if source.startswith(('http://', 'https://')):
            logger.info(f"Attempting URL extraction for: {source}")
            result = self._extract_url(source)
            logger.info(f"URL extraction result: {'Success' if result else 'Failed'}")
            return result
        
        # Check if it's an existing file
        path = Path(source)
        if path.exists():
            logger.info(f"Attempting file extraction for: {source}")
            result = self._extract_file(source)
            logger.info(f"File extraction result: {'Success' if result else 'Failed'}")
            return result
        
        # If it's neither a URL nor an existing file, treat it as raw text
        logger.info(f"Treating input as raw text: {source[:100]}...")
        # Apply content limit to raw text
        return source[:self.config.content_limit]
    
    def _extract_file(self, source: str) -> Optional[str]:
        """Extract content from a file"""
        path = Path(source)
        logger.info(f"_extract_file: path={path}, absolute={path.absolute()}, exists={path.exists()}")
        
        if not path.exists():
            logger.error(f"File does not exist: {path.absolute()}")
            return None
        
        file_extension = path.suffix.lower()
        logger.info(f"File extension: {file_extension}, HAS_DOCX={HAS_DOCX}, HAS_PDF={HAS_PDF}")
        
        # Get appropriate extractor for file type
        extractor = self._get_extractor_for_extension(file_extension)
        result = extractor(path)
        
        logger.info(f"Extraction result for {file_extension}: {'Success' if result else 'Failed'}")
        return result
    
    def _get_extractor_for_extension(self, extension: str):
        """Get the appropriate extraction function for a file extension"""
        if extension in ['.docx', '.doc']:
            return self._extract_docx_with_check
        elif extension == '.pdf':
            return self._extract_pdf_with_check
        else:
            return self._extract_text_file
    
    def _extract_docx_with_check(self, path: Path) -> Optional[str]:
        """Extract DOCX file with library availability check"""
        if not HAS_DOCX:
            logger.warning("DOCX extraction requested but python-docx not available")
            return None
        return self._extract_docx(path)
    
    def _extract_pdf_with_check(self, path: Path) -> Optional[str]:
        """Extract PDF file with library availability check"""
        if not HAS_PDF:
            logger.warning("PDF extraction requested but PyPDF2 not available")
            return None
        return self._extract_pdf(path)
    
    def _extract_text_file(self, path: Path) -> Optional[str]:
        """Extract content from a text-based file"""
        return read(path, self.config.content_limit)
    
    def _extract_docx(self, path: Path) -> Optional[str]:
        """Extract text from DOCX file"""
        Document = get_import('Document')
        if not Document:
            return None
        
        try:
            doc = Document(path)
        except Exception as e:
            error_msg = str(e).lower()
            if "file is not a zip file" in error_msg or "bad zip file" in error_msg:
                logger.error(
                    f"Cannot read {path.name}: This appears to be an encrypted or "
                    f"password-protected Word document. Please remove the password "
                    f"protection in Word and save the file before using it with this tool."
                )
                return None
            else:
                logger.error(f"Failed to open DOCX file {path.name}: {e}")
                return None
            
        parts = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
        
        # Extract table content
        for table in doc.tables:
            for row in table.rows:
                parts.extend(cell.text.strip() for cell in row.cells if cell.text.strip())
        
        return '\n'.join(parts)[:self.config.content_limit]
    
    def _extract_pdf(self, path: Path) -> Optional[str]:
        """Extract text from PDF file"""
        PdfReader = get_import('PdfReader')
        if not PdfReader:
            return None
            
        try:
            with open(path, 'rb') as f:
                return self._read_pdf_content(f, PdfReader)
        except Exception as e:
            logger.error(f"Failed to extract PDF content: {e}")
            return None
    
    def _read_pdf_content(self, file_handle, PdfReader) -> str:
        """Read content from PDF file handle"""
        reader = PdfReader(file_handle)
        content = ""
        
        # Extract from first 10 pages
        for page in reader.pages[:10]:
            text = page.extract_text()
            if not text:
                continue
                
            content += text + '\n'
            if len(content) > self.config.content_limit:
                break
        
        return content[:self.config.content_limit]
    
    def _extract_url(self, source: str) -> Optional[str]:
        """Extract content from URL"""
        if not HAS_WEB:
            return None
            
        try:
            # Fetch page content
            html_content = self._fetch_url_content(source)
            if not html_content:
                return None
            
            # Parse and extract text
            return self._parse_html_content(html_content)
            
        except Exception as e:
            logger.error(f"Failed to extract URL content: {e}")
            return None
    
    def _fetch_url_content(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        requests = get_import('requests')
        if not requests:
            return None
            
        resp = requests.get(
            url, 
            timeout=30, 
            headers={'User-Agent': 'Mozilla/5.0 (DocBot/1.0)'}
        )
        resp.raise_for_status()
        return resp.text
    
    def _parse_html_content(self, html_content: str) -> str:
        """Parse HTML content and extract text"""
        BeautifulSoup = get_import('BeautifulSoup')
        if not BeautifulSoup:
            return ""
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        
        # Extract text lines
        lines = []
        for line in soup.get_text().splitlines():
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
        
        text = '\n'.join(lines)
        return text[:self.config.content_limit]
