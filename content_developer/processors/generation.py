"""
Content generation processor that orchestrates creation and update operations
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import json

from ..models import Config, ContentDecision, DocumentChunk
from ..cache import UnifiedCache
from ..utils import get_hash
from ..prompts import get_create_content_prompt as get_create_prompt, get_update_content_prompt as get_update_prompt, CREATE_CONTENT_SYSTEM as CREATION_SYSTEM, UPDATE_CONTENT_SYSTEM as UPDATE_SYSTEM
from ..prompts.phase3.material_sufficiency import get_pregeneration_sufficiency_prompt, get_postgeneration_sufficiency_prompt
from .llm_native_processor import LLMNativeProcessor

logger = logging.getLogger(__name__)


class ContentGenerationProcessor(LLMNativeProcessor):
    """Generates content based on strategic decisions using LLM"""
    
    def _process(self, decision: ContentDecision, materials: List[Dict], 
                 chunks: List[DocumentChunk], config: Config, 
                 repo_name: str, working_directory: str) -> Tuple[str, Dict]:
        """Process content generation for a single decision"""
        
        # Handle SKIP actions
        if decision.action == "SKIP":
            logger.info(f"Skipping content generation - {decision.rationale}")
            return None, {
                'status': 'skipped',
                'reason': decision.rationale,
                'decision': decision
            }
        
        # Check material sufficiency BEFORE generating content
        if config.check_material_sufficiency:
            # For UPDATE actions, get existing content for context
            existing_content = None
            if decision.action == "UPDATE":
                target_chunks = self._get_target_chunks(decision.target_file, chunks)
                existing_content = self._reconstruct_content(target_chunks)
            
            # Check sufficiency
            pre_sufficiency = self._check_material_sufficiency_pregeneration(
                decision, materials, config, existing_content
            )
            
            # Display sufficiency results
            coverage = pre_sufficiency['coverage_percentage']
            reason = pre_sufficiency['confidence_reason']
            
            if pre_sufficiency['is_sufficient'] == 'no':
                if self.console_display:
                    self.console_display.show_error(
                        f"Material coverage too low: {coverage}%\n{reason}",
                        title="Insufficient Materials"
                    )
                    
                    # Show missing topics
                    if missing := pre_sufficiency.get('missing_topics', []):
                        self.console_display.show_warning("Critical missing topics:")
                        for topic in missing[:5]:
                            self.console_display.show_status(f"  • {topic}", "warning")
                    
                    # Show suggestions
                    if suggestions := pre_sufficiency.get('suggestions', []):
                        self.console_display.show_status("Required materials:", "info")
                        for suggestion in suggestions[:3]:
                            self.console_display.show_status(f"  • {suggestion}", "info")
                
                # Skip generation if coverage is too low (< 30%)
                if coverage < 30:
                    return None, {
                        'status': 'skipped_insufficient_materials',
                        'reason': f"Material coverage too low ({coverage}%)",
                        'material_sufficiency': pre_sufficiency,
                        'decision': decision
                    }
                
            elif pre_sufficiency['is_sufficient'] == 'partial':
                if self.console_display:
                    self.console_display.show_metric(
                        "Pre-generation Material Coverage", 
                        f"{coverage}% (Partial)"
                    )
                    self.console_display.show_warning(
                        f"⚠️  {reason[:150]}..."
                    )
                    
                    # Show missing topics if any
                    if missing := pre_sufficiency.get('missing_topics', []):
                        self.console_display.show_status("Topics with limited coverage:", "warning")
                        for topic in missing[:3]:
                            self.console_display.show_status(f"  • {topic}", "warning")
            else:  # sufficient
                if self.console_display:
                    self.console_display.show_status(
                        f"✓ Material coverage: {coverage}% - {reason[:100]}...",
                        "success"
                    )
        
        # Generate content based on action type
        if decision.action == "CREATE":
            content, metadata = self._create_content(decision, materials, config)
        else:  # UPDATE
            if 'target_chunks' not in locals():
                target_chunks = self._get_target_chunks(decision.target_file, chunks)
            content, metadata = self._update_content(decision, materials, target_chunks, config)
        
        # Add pre-generation sufficiency check results to metadata if available
        if config.check_material_sufficiency and 'pre_sufficiency' in locals():
            metadata['pre_generation_sufficiency'] = pre_sufficiency
        
        # Post-generation sufficiency check (optional, can be disabled)
        if config.check_material_sufficiency and hasattr(config, 'post_generation_check') and config.post_generation_check:
            sufficiency = self._check_material_sufficiency(content, decision, materials, config)
            metadata['material_sufficiency'] = sufficiency
            
            # Only show post-generation warnings for significant issues
            if sufficiency['is_sufficient'] == 'no':
                if self.console_display:
                    self.console_display.show_warning(
                        f"⚠️  Post-generation check: Low material coverage ({sufficiency['coverage_percentage']}%)"
                    )
        
        return content, metadata
    
    def _create_content(self, decision: ContentDecision, materials: List[Dict], 
                       config: Config) -> Tuple[str, Dict]:
        """Create new content based on decision and materials"""
        if self.console_display:
            self.console_display.show_operation(f"Creating new content: {decision.file_title}")
        
        # Load content standards
        try:
            with open('content_standards.json', 'r') as f:
                content_standards = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load content standards: {e}")
            content_standards = {
                'contentTypes': [],
                'formattingElements': [],
                'codeGuidelines': {}
            }
        
        # Get content type info
        content_type = getattr(decision, 'content_type', 'How-To Guide')
        content_type_info = next(
            (ct for ct in content_standards.get('contentTypes', []) 
             if ct.get('name') == content_type),
            {
                'name': content_type,
                'ms_topic': getattr(decision, 'ms_topic', 'how-to'),
                'purpose': f'Create a {content_type}',
                'structure': []
            }
        )
        
        # Create materials_content dictionary (source -> content)
        materials_content = {}
        for material in materials:
            material_dict = material if isinstance(material, dict) else material.__dict__
            source = material_dict.get('source', 'Unknown')
            content = material_dict.get('content', material_dict.get('summary', ''))
            materials_content[source] = content
        
        # Create materials summaries
        materials_summaries = []
        for material in materials:
            material_dict = material if isinstance(material, dict) else material.__dict__
            materials_summaries.append({
                'source': material_dict.get('source', 'Unknown'),
                'summary': material_dict.get('summary', ''),
                'technologies': material_dict.get('technologies', []),
                'key_concepts': material_dict.get('key_concepts', [])
            })
        
        # Empty related chunks and chunk context for now
        related_chunks = []
        chunk_context = "No additional chunk context available."
        
        # Get the creation prompt with all required arguments
        prompt = get_create_prompt(
            config,
            decision,  # action
            materials_content,
            materials_summaries,
            related_chunks,
            chunk_context,
            content_type_info,
            content_standards
        )
        
        messages = [
            {"role": "system", "content": CREATION_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM with JSON response
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Content Creation"
        )
        
        # Extract content and metadata
        content = result.get('content', '')
        metadata = {
            'thinking': result.get('thinking', ''),
            'sections_created': result.get('sections_created', []),
            'materials_used': result.get('materials_used', []),
            'confidence': result.get('confidence', 0.85),
            'status': 'created'
        }
        
        # Show thinking if available
        if self.console_display and metadata['thinking']:
            self.console_display.show_thinking(metadata['thinking'], "🤔 AI Thinking - Content Creation")
        
        return content, metadata
    
    def _update_content(self, decision: ContentDecision, materials: List[Dict],
                       target_chunks: List[DocumentChunk], config: Config) -> Tuple[str, Dict]:
        """Update existing content based on decision and materials"""
        if self.console_display:
            self.console_display.show_operation(f"Updating content: {decision.target_file}")
        
        # Get existing content
        existing_content = self._reconstruct_content(target_chunks)
        
        # Format materials for the prompt
        formatted_materials = self._format_materials_for_prompt(materials)
        
        # Build chunk context (empty for now since we're using full content)
        chunk_context = "No additional chunk context available."
        
        # Get content type info from existing content
        ms_topic = 'how-to'  # default
        if existing_content.startswith('---\n'):
            # Find the end of frontmatter
            end_fm_pos = existing_content.find('\n---\n', 4)
            if end_fm_pos > 0:
                frontmatter = existing_content[4:end_fm_pos]
                # Look for ms.topic in frontmatter
                for line in frontmatter.split('\n'):
                    if line.strip().startswith('ms.topic:'):
                        ms_topic = line.split(':', 1)[1].strip()
        
        # Map ms.topic to content type
        ms_topic_to_content_type = {
            'overview': 'Overview',
            'concept-article': 'Concept', 
            'quickstart': 'Quickstart',
            'how-to': 'How-To Guide',
            'tutorial': 'Tutorial'
        }
        content_type = ms_topic_to_content_type.get(ms_topic, 'How-To Guide')
        
        content_type_info = {
            'ms_topic': ms_topic,
            'content_type': content_type
        }
        
        # Load content standards from file
        try:
            with open('content_standards.json', 'r') as f:
                content_standards = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load content standards: {e}")
            content_standards = {
                'contentTypes': [],
                'formattingElements': [],
                'codeGuidelines': {}
            }
        
        # Get the update prompt with all required parameters
        prompt = get_update_prompt(
            config, 
            decision,  # Pass decision object directly, not as dict
            existing_content, 
            formatted_materials,  # material_context
            chunk_context,
            content_type_info,
            content_standards
        )
        
        messages = [
            {"role": "system", "content": UPDATE_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM with JSON response
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Content Update"
        )
        
        # Extract content and metadata
        content = result.get('updated_document', result.get('content', ''))  # Handle both response formats
        metadata = {
            'thinking': result.get('thinking', ''),
            'sections_updated': result.get('sections_modified', result.get('sections_updated', [])),
            'materials_used': result.get('materials_used', []),
            'changes_made': result.get('changes_made', []),
            'changes_summary': result.get('changes_summary', ''),
            'confidence': result.get('confidence', 0.85),
            'status': 'updated'
        }
        
        # Show thinking if available
        if self.console_display and metadata['thinking']:
            self.console_display.show_thinking(metadata['thinking'], "🤔 AI Thinking - Content Update")
        
        return content, metadata
    
    def _get_target_chunks(self, target_file: str, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Get chunks for the target file"""
        target_chunks = []
        for chunk in chunks:
            if chunk.file_path == target_file:
                target_chunks.append(chunk)
        
        # Sort by chunk index to maintain order
        target_chunks.sort(key=lambda c: c.chunk_index)
        return target_chunks
    
    def _reconstruct_content(self, chunks: List[DocumentChunk]) -> str:
        """Reconstruct full content from chunks"""
        if not chunks:
            return ""
        
        content_parts = []
        
        # Add frontmatter from first chunk
        if chunks[0].frontmatter:
            fm_lines = ["---"]
            for key, value in chunks[0].frontmatter.items():
                if isinstance(value, str) and '\n' in value:
                    fm_lines.append(f'{key}: |')
                    for line in value.split('\n'):
                        fm_lines.append(f'  {line}')
                else:
                    fm_lines.append(f"{key}: {value}")
            fm_lines.append("---\n")
            content_parts.append('\n'.join(fm_lines))
        
        # Add all chunk contents
        for chunk in chunks:
            content_parts.append(chunk.content)
        
        return '\n'.join(content_parts)
    
    def _format_materials_for_prompt(self, materials: List[Dict]) -> str:
        """Format materials for inclusion in prompt"""
        if not materials:
            return "No materials provided"
        
        formatted = []
        for i, material in enumerate(materials, 1):
            material_dict = material if isinstance(material, dict) else material.__dict__
            
            formatted.append(f"=== MATERIAL {i}: {material_dict.get('source', 'Unknown')} ===")
            formatted.append(f"Topic: {material_dict.get('main_topic', 'N/A')}")
            formatted.append(f"Type: {material_dict.get('document_type', 'N/A')}")
            
            # Add summary
            if summary := material_dict.get('summary'):
                formatted.append(f"\nSummary:\n{summary}")
            
            # Add key concepts
            if concepts := material_dict.get('key_concepts'):
                formatted.append(f"\nKey Concepts: {', '.join(concepts[:10])}")
            
            # Add technologies
            if techs := material_dict.get('technologies'):
                formatted.append(f"Technologies: {', '.join(techs[:10])}")
            
            # Add content if available
            if content := material_dict.get('content'):
                # Truncate very long content
                if len(content) > 5000:
                    content = content[:5000] + "\n\n[... content truncated ...]"
                formatted.append(f"\nContent:\n{content}")
            
            formatted.append("")  # Empty line between materials
        
        return '\n'.join(formatted)
    
    def _check_material_sufficiency(self, content: str, decision: ContentDecision, 
                                  materials: List[Dict], config: Config) -> Dict:
        """Check if materials are sufficient for the generated content"""
        if self.console_display:
            self.console_display.show_operation("Checking material sufficiency")
        
        # Create prompt for sufficiency check
        prompt = get_postgeneration_sufficiency_prompt(content, decision, materials)
        
        messages = [
            {"role": "system", "content": "You are an expert at evaluating documentation quality and material coverage."},
            {"role": "user", "content": prompt}
        ]
        
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Material Sufficiency Check"
        )
        
        # Extract thinking if available and display it
        thinking = result.get('thinking', '')
        if thinking and self.console_display:
            self.console_display.show_thinking(thinking, "🔍 AI Thinking - Material Sufficiency Analysis")
        
        return {
            'is_sufficient': result.get('is_sufficient', 'unknown'),
            'coverage_percentage': result.get('coverage_percentage', 0),
            'confidence': result.get('confidence', 0.5),
            'confidence_reason': result.get('confidence_reason', ''),
            'insufficient_areas': result.get('insufficient_areas', []),
            'suggestions': result.get('suggestions', []),
            'thinking': thinking  # Include thinking in the return value
        }
    
    def _check_material_sufficiency_pregeneration(self, decision: ContentDecision, 
                                                 materials: List[Dict], config: Config,
                                                 existing_content: Optional[str] = None) -> Dict:
        """Check if materials are sufficient BEFORE generating content"""
        if self.console_display:
            self.console_display.show_operation("Pre-checking material sufficiency")
        
        # Create prompt for pre-generation sufficiency check
        prompt = get_pregeneration_sufficiency_prompt(decision, materials, existing_content)
        
        messages = [
            {"role": "system", "content": "You are an expert at evaluating whether provided materials are sufficient for creating comprehensive documentation."},
            {"role": "user", "content": prompt}
        ]
        
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Pre-generation Material Sufficiency Check"
        )
        
        # Extract thinking if available and display it
        thinking = result.get('thinking', '')
        if thinking and self.console_display:
            self.console_display.show_thinking(thinking, "🔍 AI Thinking - Pre-generation Material Analysis")
        
        return {
            'is_sufficient': result.get('is_sufficient', 'unknown'),
            'coverage_percentage': result.get('coverage_percentage', 0),
            'confidence': result.get('confidence', 0.5),
            'confidence_reason': result.get('confidence_reason', ''),
            'missing_topics': result.get('missing_topics', []),
            'suggestions': result.get('suggestions', []),
            'thinking': thinking
        } 