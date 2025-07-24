#!/usr/bin/env python3
"""
Internet Archive Diverse PDF Type Downloader
Downloads 15 PDFs of different document types with diverse layouts (max 20 pages each)
"""

import requests
import os
import time
import json
import random
from PyPDF2 import PdfReader

class PDFDownloader:
    def __init__(self):
        self.downloaded_pdfs = []
        self.target_count = 15
        self.max_pages = 20
        self.download_folder = "diverse_pdfs"
        
        # Define diverse PDF document types
        self.document_types = [
            {
                'name': 'Research Papers',
                'query': 'research paper academic journal scientific',
                'description': 'Academic research papers with formal layouts'
            },
            {
                'name': 'Government Documents',
                'query': 'government report official document public',
                'description': 'Official government reports and documents'
            },
            {
                'name': 'Pamphlets & Brochures',
                'query': 'pamphlet brochure leaflet marketing',
                'description': 'Marketing materials and informational pamphlets'
            },
            {
                'name': 'Historical Letters',
                'query': 'correspondence letters historical personal',
                'description': 'Personal and official correspondence'
            },
            {
                'name': 'Technical Manuals',
                'query': 'manual technical instructions handbook guide',
                'description': 'Technical documentation and user manuals'
            },
            {
                'name': 'Magazines & Periodicals',
                'query': 'magazine periodical newsletter publication',
                'description': 'Magazine layouts with columns and graphics'
            },
            {
                'name': 'Annual Reports',
                'query': 'annual report corporate business financial',
                'description': 'Corporate annual reports with charts and data'
            },
            {
                'name': 'Sheet Music',
                'query': 'sheet music score musical notation',
                'description': 'Musical scores and notation layouts'
            },
            {
                'name': 'Maps & Atlases',
                'query': 'map atlas geographical cartographic',
                'description': 'Cartographic materials and geographical layouts'
            },
            {
                'name': 'Catalogs',
                'query': 'catalog catalogue product listing directory',
                'description': 'Product catalogs and listing formats'
            },
            {
                'name': 'Posters & Flyers',
                'query': 'poster flyer advertisement promotional',
                'description': 'Promotional materials with graphic layouts'
            },
            {
                'name': 'Comics & Graphic Novels',
                'query': 'comic graphic novel sequential art',
                'description': 'Sequential art with panel layouts'
            },
            {
                'name': 'Educational Worksheets',
                'query': 'worksheet educational exercise workbook',
                'description': 'Educational materials with form layouts'
            },
            {
                'name': 'Legal Documents',
                'query': 'legal document contract agreement law',
                'description': 'Legal contracts and formal documents'
            },
            {
                'name': 'Architectural Plans',
                'query': 'architectural plan blueprint design drawing',
                'description': 'Technical drawings and architectural layouts'
            }
        ]

    def search_internet_archive(self, query, num_results=5):
        """Search Internet Archive for PDFs matching the query"""
        base_url = "https://archive.org/advancedsearch.php"
        
        search_query = f'{query} AND format:PDF AND mediatype:texts'
        
        params = {
            'q': search_query,
            'fl': 'identifier,title,creator,description,downloads,publicdate',
            'sort[]': 'downloads desc',
            'rows': num_results,
            'page': 1,
            'output': 'json'
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('response', {}).get('docs', [])
        except Exception as e:
            print(f"   ❌ Error searching for '{query}': {e}")
            return []

    def get_pdf_download_url(self, identifier):
        """Get the direct download URL for a PDF from Internet Archive"""
        metadata_url = f"https://archive.org/metadata/{identifier}"
        
        try:
            response = requests.get(metadata_url, timeout=15)
            response.raise_for_status()
            metadata = response.json()
            
            files = metadata.get('files', [])
            pdf_files = []
            
            # Find PDF files
            for file_info in files:
                name = file_info.get('name', '').lower()
                format_type = file_info.get('format', '').lower()
                
                if 'pdf' in format_type or name.endswith('.pdf'):
                    pdf_files.append(file_info)
            
            # Prefer original or main PDF files
            for pdf in pdf_files:
                name = pdf.get('name', '').lower()
                if any(keyword in name for keyword in ['orig', 'original', identifier]):
                    return f"https://archive.org/download/{identifier}/{pdf['name']}"
            
            # Otherwise, take the first PDF
            if pdf_files:
                return f"https://archive.org/download/{identifier}/{pdf_files[0]['name']}"
            
            return None
            
        except Exception as e:
            print(f"   ❌ Error getting metadata for {identifier}: {e}")
            return None

    def check_pdf_pages(self, filepath):
        """Check if PDF has acceptable page count"""
        try:
            with open(filepath, 'rb') as file:
                pdf_reader = PdfReader(file)
                num_pages = len(pdf_reader.pages)
                return num_pages <= self.max_pages, num_pages
        except Exception as e:
            print(f"   ⚠️  Could not check page count: {e}")
            return True, 0  # Allow if we can't check

    def download_pdf(self, url, filename, doc_type_name):
        """Download and validate a PDF file"""
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        
        filepath = os.path.join(self.download_folder, filename)
        
        try:
            print(f"   📥 Downloading: {filename}")
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Write file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Check file size
            file_size = os.path.getsize(filepath)
            if file_size < 5000:  # Less than 5KB, probably not a real PDF
                os.remove(filepath)
                print(f"   ❌ File too small ({file_size} bytes), removed")
                return False
            
            # Check page count
            is_valid_length, page_count = self.check_pdf_pages(filepath)
            if not is_valid_length:
                os.remove(filepath)
                print(f"   ❌ Too many pages ({page_count}), removed")
                return False
            
            print(f"   ✅ Success: {filename}")
            print(f"      📊 Size: {file_size:,} bytes | Pages: {page_count}")
            return True
            
        except Exception as e:
            print(f"   ❌ Download failed: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False

    def create_safe_filename(self, title, doc_type, index):
        """Create a safe filename from title and document type"""
        # Clean title
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:40]  # Limit length
        
        # Clean document type
        safe_doc_type = doc_type.replace(' & ', '_').replace(' ', '_').replace('&', 'and')
        
        return f"{index:02d}_{safe_doc_type}_{safe_title}.pdf"

    def download_from_category(self, doc_type):
        """Try to download one PDF from a specific document category"""
        print(f"\n🔍 Searching: {doc_type['name']}")
        print(f"   Query: {doc_type['query']}")
        
        results = self.search_internet_archive(doc_type['query'], num_results=8)
        
        if not results:
            print(f"   ❌ No results found")
            return False
        
        print(f"   📋 Found {len(results)} potential PDFs")
        
        for item in results:
            identifier = item.get('identifier')
            title = item.get('title', 'Unknown Title')
            creator = item.get('creator', 'Unknown Author')
            
            if not identifier:
                continue
            
            print(f"   🔍 Trying: {title[:60]}...")
            
            # Get PDF download URL
            pdf_url = self.get_pdf_download_url(identifier)
            if not pdf_url:
                print(f"   ❌ No PDF file found")
                continue
            
            # Create filename
            filename = self.create_safe_filename(
                title, doc_type['name'], len(self.downloaded_pdfs) + 1
            )
            
            # Download and validate PDF
            if self.download_pdf(pdf_url, filename, doc_type['name']):
                # Success! Add to our collection
                self.downloaded_pdfs.append({
                    'filename': filename,
                    'title': title,
                    'creator': creator,
                    'identifier': identifier,
                    'url': pdf_url,
                    'document_type': doc_type['name'],
                    'description': doc_type['description'],
                    'search_query': doc_type['query']
                })
                
                print(f"   🎉 Added to collection! ({len(self.downloaded_pdfs)}/{self.target_count})")
                time.sleep(2)  # Be respectful to the server
                return True
            
            # Try next result if this one failed
            time.sleep(1)
        
        print(f"   ❌ No valid PDFs found in this category")
        return False

    def fill_remaining_slots(self):
        """Fill any remaining slots with diverse content"""
        remaining = self.target_count - len(self.downloaded_pdfs)
        if remaining <= 0:
            return
        
        print(f"\n🔄 Filling remaining {remaining} slots with additional content...")
        
        backup_queries = [
            'vintage poster', 'scientific diagram', 'historical document',
            'art exhibition catalog', 'travel brochure', 'instruction booklet',
            'newsletter', 'program guide', 'advertisement', 'infographic'
        ]
        
        random.shuffle(backup_queries)
        
        for query in backup_queries:
            if len(self.downloaded_pdfs) >= self.target_count:
                break
            
            print(f"\n🔍 Backup search: {query}")
            results = self.search_internet_archive(query, num_results=5)
            
            for item in results:
                if len(self.downloaded_pdfs) >= self.target_count:
                    break
                
                identifier = item.get('identifier')
                title = item.get('title', 'Unknown Title')
                
                if not identifier:
                    continue
                
                pdf_url = self.get_pdf_download_url(identifier)
                if not pdf_url:
                    continue
                
                filename = self.create_safe_filename(
                    title, 'Mixed_Content', len(self.downloaded_pdfs) + 1
                )
                
                if self.download_pdf(pdf_url, filename, 'Mixed Content'):
                    self.downloaded_pdfs.append({
                        'filename': filename,
                        'title': title,
                        'creator': item.get('creator', 'Unknown'),
                        'identifier': identifier,
                        'url': pdf_url,
                        'document_type': 'Mixed Content',
                        'description': 'Additional diverse content',
                        'search_query': query
                    })
                    time.sleep(2)
                    break

    def save_download_log(self):
        """Save detailed log of downloads"""
        log_data = {
            'download_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'settings': {
                'target_count': self.target_count,
                'max_pages_per_pdf': self.max_pages,
                'download_folder': self.download_folder
            },
            'total_downloaded': len(self.downloaded_pdfs),
            'document_types_targeted': [dt['name'] for dt in self.document_types],
            'files': self.downloaded_pdfs
        }
        
        log_path = os.path.join(self.download_folder, 'download_log.json')
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return log_path

    def print_summary(self):
        """Print detailed download summary"""
        print("\n" + "=" * 70)
        print(f"🎉 DOWNLOAD COMPLETE!")
        print(f"📊 Successfully downloaded {len(self.downloaded_pdfs)} diverse PDF types")
        print(f"📏 All PDFs have ≤ {self.max_pages} pages")
        
        # Group by document type
        by_type = {}
        for pdf in self.downloaded_pdfs:
            doc_type = pdf['document_type']
            if doc_type not in by_type:
                by_type[doc_type] = []
            by_type[doc_type].append(pdf)
        
        print(f"\n📁 Downloaded files by document type:")
        for doc_type, pdfs in by_type.items():
            print(f"\n🔸 {doc_type} ({len(pdfs)} files):")
            for pdf in pdfs:
                print(f"   • {pdf['title'][:55]}...")
                print(f"     → {pdf['filename']}")
        
        print(f"\n📂 All files saved to: {self.download_folder}/")
        print(f"📋 Download log: {self.download_folder}/download_log.json")
        
        print(f"\n🎯 Layout diversity achieved through:")
        unique_types = set(pdf['document_type'] for pdf in self.downloaded_pdfs)
        for doc_type in sorted(unique_types):
            if doc_type != 'Mixed Content':
                type_info = next((dt for dt in self.document_types if dt['name'] == doc_type), None)
                if type_info:
                    print(f"   • {doc_type}: {type_info['description']}")

    def run(self):
        """Main execution method"""
        print("🚀 Internet Archive Diverse PDF Type Downloader")
        print(f"🎯 Target: {self.target_count} PDFs with ≤ {self.max_pages} pages each")
        print("=" * 70)
        
        print("📋 Targeting document types with diverse layouts:")
        for i, doc_type in enumerate(self.document_types, 1):
            print(f"{i:2d}. {doc_type['name']} - {doc_type['description']}")
        print("=" * 70)
        
        # Shuffle document types for variety
        shuffled_types = self.document_types.copy()
        random.shuffle(shuffled_types)
        
        # Try to get one PDF from each category
        for doc_type in shuffled_types:
            if len(self.downloaded_pdfs) >= self.target_count:
                break
            
            self.download_from_category(doc_type)
        
        # Fill remaining slots if needed
        self.fill_remaining_slots()
        
        # Save log and print summary
        log_path = self.save_download_log()
        self.print_summary()
        
        print(f"\n✨ Ready for PDF analysis with diverse layouts and structures!")

def main():
    """Entry point"""
    downloader = PDFDownloader()
    downloader.run()

if __name__ == "__main__":
    main()