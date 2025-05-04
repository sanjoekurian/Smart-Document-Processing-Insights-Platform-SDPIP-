from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from pathlib import Path
import logging
from typing import Dict, List
import json
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        # Main Title Style
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            textColor=HexColor('#1a365d'),
            alignment=1,  # Center alignment
            fontName='Helvetica-Bold'
        ))
        
        # Section Title Style
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=20,
            spaceBefore=25,
            spaceAfter=15,
            textColor=HexColor('#2c5282'),
            fontName='Helvetica-Bold'
        ))

        # Subsection Title Style
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Heading3'],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=10,
            textColor=HexColor('#2d3748'),
            fontName='Helvetica-Bold',
            leading=20
        ))
        
        # Normal Text Style
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=HexColor('#2d3748'),
            spaceAfter=8,
            leading=16
        ))

        # List Item Style
        self.styles.add(ParagraphStyle(
            name='ListItem',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=HexColor('#2d3748'),
            leftIndent=20,
            spaceAfter=3,
            leading=16,
            bulletIndent=10,
            firstLineIndent=0
        ))
        
        # Table Header Style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#ffffff'),
            fontName='Helvetica-Bold'
        ))
        
        # Table Cell Style
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=HexColor('#2d3748')
        ))

    def _format_summary(self, text: str) -> List[Paragraph]:
        """Format the summary text with proper styling for sections and paragraphs."""
        paragraphs = []
        current_text = []
        
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                if current_text:
                    paragraphs.append(Paragraph(' '.join(current_text), self.styles['NormalText']))
                    current_text = []
                i += 1
                continue
            
            # Check if line is a major heading (followed by blank line)
            if (i < len(lines) - 1 and not lines[i + 1].strip() and 
                not line.startswith('•') and not re.match(r'^\d+\.', line)):
                if current_text:
                    paragraphs.append(Paragraph(' '.join(current_text), self.styles['NormalText']))
                    current_text = []
                paragraphs.append(Paragraph(line, self.styles['SubsectionTitle']))
                paragraphs.append(Spacer(1, 10))
                i += 2
                continue
            
            # Check if line is a bullet point
            if line.startswith('•'):
                if current_text:
                    paragraphs.append(Paragraph(' '.join(current_text), self.styles['NormalText']))
                    current_text = []
                
                # Collect all consecutive bullet points
                bullet_points = []
                while i < len(lines) and lines[i].strip().startswith('•'):
                    bullet_points.append(lines[i].strip()[2:].strip())  # Remove bullet and trim
                    i += 1
                
                # Add bullet points with proper styling
                for point in bullet_points:
                    paragraphs.append(Paragraph(
                        f'• {point}',
                        self.styles['ListItem']
                    ))
                paragraphs.append(Spacer(1, 6))
                continue
            
            # Check if line is a numbered list item
            if re.match(r'^\d+\.', line):
                if current_text:
                    paragraphs.append(Paragraph(' '.join(current_text), self.styles['NormalText']))
                    current_text = []
                
                # Collect all consecutive numbered items
                numbered_items = []
                while i < len(lines) and re.match(r'^\d+\.', lines[i].strip()):
                    numbered_items.append(lines[i].strip())
                    i += 1
                
                # Add numbered items with proper styling
                for item in numbered_items:
                    paragraphs.append(Paragraph(
                        item,
                        self.styles['ListItem']
                    ))
                paragraphs.append(Spacer(1, 6))
                continue
            
            current_text.append(line)
            i += 1
        
        # Add any remaining text
        if current_text:
            paragraphs.append(Paragraph(' '.join(current_text), self.styles['NormalText']))
        
        return paragraphs

    async def generate_report(self, 
                            output_path: Path,
                            document_data: Dict,
                            summary: str,
                            sentiment_analysis: Dict) -> Path:
        """Generate a PDF report with modern styling."""
        try:
            # Create the document with custom margins
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )

            # Initialize story for the document
            story = []
            
            # Add Title
            story.append(Paragraph("Document Analysis Report", self.styles['MainTitle']))
            story.append(Paragraph(
                f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                self.styles['NormalText']
            ))
            story.append(Spacer(1, 30))

            # Document Metadata Section
            story.append(Paragraph("Document Information", self.styles['SectionTitle']))
            
            # Create metadata table with modern styling
            metadata_items = []
            for key, value in document_data['metadata'].items():
                if value:  # Only add non-empty metadata
                    metadata_items.append([
                        Paragraph(key.replace('_', ' ').title(), self.styles['TableCell']),
                        Paragraph(str(value), self.styles['TableCell'])
                    ])
            
            if metadata_items:
                metadata_table = Table(metadata_items, colWidths=[2.5*inch, 4*inch])
                metadata_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), HexColor('#f7fafc')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2d3748')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('LEFTPADDING', (0, 0), (-1, -1), 16),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 16),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
                ]))
                story.append(metadata_table)
            
            story.append(Spacer(1, 20))

            # Summary Section with improved formatting
            story.append(Paragraph("Document Summary", self.styles['SectionTitle']))
            story.extend(self._format_summary(summary))
            story.append(Spacer(1, 20))

            # Sentiment Analysis Section
            story.append(Paragraph("Content Analysis", self.styles['SectionTitle']))
            
            # Overall Sentiment
            sentiment = sentiment_analysis.get('sentiment', 'N/A').title()
            story.append(Paragraph(f"Overall Sentiment: {sentiment}", self.styles['NormalText']))
            
            # Key Themes
            if 'themes' in sentiment_analysis and sentiment_analysis['themes']:
                story.append(Paragraph("Key Themes Identified:", self.styles['NormalText']))
                themes_table_data = [[Paragraph("Theme", self.styles['TableHeader'])]]
                for theme in sentiment_analysis['themes']:
                    themes_table_data.append([Paragraph(theme, self.styles['TableCell'])])
                
                themes_table = Table(themes_table_data, colWidths=[6*inch])
                themes_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4299e1')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('LEFTPADDING', (0, 0), (-1, -1), 16),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 16),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ]))
                story.append(themes_table)

            story.append(Spacer(1, 20))

            # PII Findings Section
            story.append(Paragraph("Privacy Analysis", self.styles['SectionTitle']))
            
            pii_items = []
            has_pii = False
            
            for pii_type, findings in document_data['pii_findings'].items():
                if findings:
                    has_pii = True
                    pii_items.append([
                        Paragraph(pii_type.replace('_', ' ').title(), self.styles['TableCell']),
                        Paragraph(f"{len(findings)} instance(s) found", self.styles['TableCell'])
                    ])
            
            if pii_items:
                story.append(Paragraph(
                    "The following types of sensitive information were detected:",
                    self.styles['NormalText']
                ))
                pii_table = Table(pii_items, colWidths=[3*inch, 3.5*inch])
                pii_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), HexColor('#fff5f5')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#2d3748')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('LEFTPADDING', (0, 0), (-1, -1), 16),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 16),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor('#fed7d7')),
                ]))
                story.append(pii_table)
            else:
                story.append(Paragraph(
                    "No sensitive information was detected in this document.",
                    self.styles['NormalText']
                ))

            # Build the PDF
            doc.build(story)
            logger.info(f"Report generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise Exception(f"Failed to generate report: {str(e)}")

# Initialize the report generator
report_generator = ReportGenerator() 