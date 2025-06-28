import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright
import json


class WikisourceScaper:
    """
    Scraper for Wikisource content with screenshot capabilities
    """
    
    def __init__(self, output_dir: str = "scraped_content"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.screenshots_dir = self.output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        self.content_dir = self.output_dir / "content"
        self.content_dir.mkdir(exist_ok=True)
    
    async def scrape_chapter(self, url: str) -> Dict:
        """
        Scrape a single chapter from Wikisource
        
        Args:
            url: The Wikisource chapter URL
            
        Returns:
            Dictionary containing scraped content and metadata
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Navigate to the page
                await page.goto(url, wait_until='networkidle')
                
                # Extract metadata
                title = await self._extract_title(page)
                book_info = await self._extract_book_info(page)
                
                # Extract main content
                content = await self._extract_content(page)
                
                # Take screenshot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_filename = f"{self._sanitize_filename(title)}_{timestamp}.png"
                screenshot_path = self.screenshots_dir / screenshot_filename
                
                await page.screenshot(path=str(screenshot_path), full_page=True)
                
                # Prepare result
                result = {
                    'url': url,
                    'title': title,
                    'book_info': book_info,
                    'content': content,
                    'word_count': len(content.split()) if content else 0,
                    'scraped_at': datetime.now().isoformat(),
                    'screenshot_path': str(screenshot_path)
                }
                
                # Save content to file
                content_filename = f"{self._sanitize_filename(title)}_{timestamp}.json"
                content_path = self.content_dir / content_filename
                
                with open(content_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"Successfully scraped: {title}")
                print(f"Content saved to: {content_path}")
                print(f"Screenshot saved to: {screenshot_path}")
                
                return result
                
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                return {
                    'url': url,
                    'error': str(e),
                    'scraped_at': datetime.now().isoformat()
                }
            
            finally:
                await browser.close()
    
    async def _extract_title(self, page) -> str:
        """Extract the chapter title"""
        try:
            # Try different selectors for title
            title_selectors = [
                'h1.firstHeading',
                'h1',
                '.mw-page-title-main',
                '#firstHeading'
            ]
            
            for selector in title_selectors:
                title_element = await page.query_selector(selector)
                if title_element:
                    title = await title_element.text_content()
                    return title.strip()
            
            # Fallback to page title
            return await page.title()
            
        except Exception as e:
            print(f"Error extracting title: {e}")
            return "Unknown Title"
    
    async def _extract_book_info(self, page) -> Dict:
        """Extract book and chapter information"""
        book_info = {}
        
        try:
            # Extract breadcrumb or navigation info
            nav_elements = await page.query_selector_all('.mw-breadcrumbs a, .wikisource-nav a')
            if nav_elements:
                nav_texts = []
                for element in nav_elements:
                    text = await element.text_content()
                    if text and text.strip():
                        nav_texts.append(text.strip())
                book_info['navigation'] = nav_texts
            
            # Extract book title from URL or content
            url = page.url
            if 'wikisource.org/wiki/' in url:
                path_parts = url.split('/wiki/')[-1].split('/')
                if len(path_parts) >= 3:
                    book_info['book_title'] = path_parts[0].replace('_', ' ')
                    book_info['book_part'] = path_parts[1].replace('_', ' ')
                    book_info['chapter'] = path_parts[2].replace('_', ' ')
            
        except Exception as e:
            print(f"Error extracting book info: {e}")
        
        return book_info
    
    async def _extract_content(self, page) -> str:
        """Extract the main content text"""
        try:
            # Primary content selector for Wikisource
            content_selectors = [
                '.mw-parser-output',
                '#mw-content-text',
                '.mw-content-container',
                'main'
            ]
            
            for selector in content_selectors:
                content_element = await page.query_selector(selector)
                if content_element:
                    # Remove unwanted elements
                    await self._remove_unwanted_elements(page, content_element)
                    
                    # Get text content
                    content = await content_element.text_content()
                    
                    if content and len(content.strip()) > 100:  # Minimum content length
                        return self._clean_content(content)
            
            # Fallback to body text
            body_text = await page.locator('body').text_content()
            return self._clean_content(body_text) if body_text else ""
            
        except Exception as e:
            print(f"Error extracting content: {e}")
            return ""
    
    async def _remove_unwanted_elements(self, page, content_element):
        """Remove navigation, footer, and other unwanted elements"""
        unwanted_selectors = [
            '.mw-editsection',
            '.navbox',
            '.infobox',
            '.mw-references-wrap',
            '.wikisource-nav',
            '.mw-jump-link',
            '.printfooter',
            '.catlinks'
        ]
        
        for selector in unwanted_selectors:
            elements = await content_element.query_selector_all(selector)
            for element in elements:
                await element.evaluate('element => element.remove()')
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize the extracted content"""
        if not content:
            return ""
        
        # Remove excessive whitespace
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('[') and len(line) > 2:
                cleaned_lines.append(line)
        
        # Join lines and clean up spacing
        cleaned_content = '\n\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        import re
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content.strip()
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system storage"""
        import re
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:100]  # Limit length
    
    async def scrape_multiple_chapters(self, urls: list) -> list:
        """
        Scrape multiple chapters
        
        Args:
            urls: List of chapter URLs
            
        Returns:
            List of scraping results
        """
        results = []
        
        for i, url in enumerate(urls, 1):
            print(f"Scraping chapter {i}/{len(urls)}: {url}")
            result = await self.scrape_chapter(url)
            results.append(result)
            
            # Add delay between requests to be respectful
            if i < len(urls):
                await asyncio.sleep(2)
        
        return results


# Example usage and testing
async def main():
    """Example usage of the WikisourceScaper"""
    scraper = WikisourceScaper()
    
    # Test URL from the assignment
    test_url = "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1"
    
    print("Starting scraping process...")
    result = await scraper.scrape_chapter(test_url)
    
    if 'error' not in result:
        print(f"Successfully scraped chapter: {result['title']}")
        print(f"Word count: {result['word_count']}")
        print(f"Content preview: {result['content'][:200]}...")
    else:
        print(f"Scraping failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())