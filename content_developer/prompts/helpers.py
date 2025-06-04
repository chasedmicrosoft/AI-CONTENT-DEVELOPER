"""
Helper functions for prompt formatting
"""
from typing import Dict, List


def format_semantic_matches(matches: List[Dict]) -> str:
    """Format chunks for analysis in strategy prompt"""
    if not matches:
        return "No existing content found in the working directory."
    
    formatted = ["EXISTING CONTENT CHUNKS:"]
    formatted.append(f"Found {len(matches)} chunks across documentation files.\n")
    
    for i, chunk in enumerate(matches[:15], 1):  # Top 15 chunks
        formatted.append(f"Chunk {i}:")
        formatted.append(f"  File: {chunk.get('file', 'Unknown')}")
        formatted.append(f"  Content Type: {chunk.get('content_type', 'unknown')} (ms.topic: {chunk.get('ms_topic', 'unknown')})")
        formatted.append(f"  Chunk ID: {chunk.get('chunk_id', 'unknown')}")
        formatted.append(f"  Section: {chunk.get('section', 'Main')}")
        
        # Add content preview if available
        if preview := chunk.get('content_preview', ''):
            # Clean up preview for display
            preview_clean = preview.replace('\n', ' ').strip()
            if len(preview_clean) > 150:
                preview_clean = preview_clean[:147] + "..."
            formatted.append(f"  Preview: {preview_clean}")
        
        formatted.append("")  # Empty line between chunks
    
    if len(matches) > 15:
        formatted.append(f"... and {len(matches) - 15} more chunks")
    
    return '\n'.join(formatted)


def format_content_types(standards: Dict) -> str:
    """Format content types from standards"""
    types_info = []
    for ct in standards.get('contentTypes', []):
        types_info.append(
            f"- **{ct['name']}** (ms.topic: {ct['frontMatter']['ms.topic']})\n"
            f"  Purpose: {ct['purpose']}\n"
            f"  Use when: {ct['description']}"
        )
    return '\n'.join(types_info)


def format_top_chunks(top_chunks: List[Dict]) -> str:
    """Format top individual chunks for strategy analysis"""
    if not top_chunks:
        return ""
    
    sections = ["TOP RELEVANT CHUNKS (Individual chunks for reference):\n"]
    sections.append("These are the most relevant individual content chunks from your repository:")
    
    for i, chunk in enumerate(top_chunks[:20], 1):  # Show top 20 chunks
        sections.append(f"\nChunk #{i}:")
        sections.append(f"  Chunk ID: {chunk.get('chunk_id', 'unknown')}")
        sections.append(f"  File: {chunk.get('file', 'unknown')}")
        sections.append(f"  Section: {chunk.get('section', 'Main')}")
        sections.append(f"  Relevance Score: {chunk.get('relevance_score', 0):.3f}")
        
        # Add technology indicators
        if techs := chunk.get('technologies_mentioned', []):
            sections.append(f"  Technologies: {', '.join(techs[:5])}")
        
        # Add content preview
        if preview := chunk.get('content_preview', ''):
            preview_clean = preview.replace('\n', ' ').strip()[:150]
            sections.append(f"  Preview: {preview_clean}...")
            
        # Add metadata
        if chunk.get('has_code_examples'):
            sections.append(f"  Contains: Code examples")
    
    return '\n'.join(sections)


def format_chunk_clusters(chunk_clusters: Dict[str, List[Dict]]) -> str:
    """Format chunk clusters for gap analysis"""
    if not chunk_clusters:
        return ""
    
    sections = ["CONTENT CLUSTERS (Topic groupings for gap analysis):\n"]
    sections.append("Existing content is organized into these main topics:")
    
    # Format top clusters
    cluster_sections = _format_top_clusters(chunk_clusters, max_clusters=10)
    sections.extend(cluster_sections)
    
    # Add coverage summary
    summary = _generate_coverage_summary(chunk_clusters)
    sections.append(summary)
    
    return '\n'.join(sections)


def _format_top_clusters(chunk_clusters: Dict[str, List[Dict]], max_clusters: int = 10) -> List[str]:
    """Format the top N clusters with their chunks"""
    sections = []
    
    for topic, chunks in list(chunk_clusters.items())[:max_clusters]:
        sections.append(f"\n📁 {topic} ({len(chunks)} chunks)")
        
        # Format chunks in cluster
        chunk_sections = _format_cluster_chunks(chunks, max_chunks=3)
        sections.extend(chunk_sections)
        
        # Add overflow indicator
        if len(chunks) > 3:
            sections.append(f"  ... and {len(chunks) - 3} more chunks")
    
    return sections


def _format_cluster_chunks(chunks: List[Dict], max_chunks: int = 3) -> List[str]:
    """Format individual chunks within a cluster"""
    sections = []
    
    for chunk in chunks[:max_chunks]:
        sections.append(f"  - {chunk['file']} > {chunk.get('section', 'Main')}")
        sections.append(f"    Chunk ID: {chunk['chunk_id']}")
    
    return sections


def _generate_coverage_summary(chunk_clusters: Dict[str, List[Dict]]) -> str:
    """Generate coverage summary statistics"""
    total_topics = len(chunk_clusters)
    total_chunks = sum(len(chunks) for chunks in chunk_clusters.values())
    return f"\nCOVERAGE SUMMARY: {total_topics} topics, {total_chunks} total chunks"


def format_materials_with_content(materials_content: Dict[str, str], summaries: List[Dict]) -> str:
    """Format materials with their full content"""
    sections = ["=== MATERIAL SOURCES (Full Content) ===\n"]
    
    for i, (source, content) in enumerate(materials_content.items(), 1):
        material_section = _format_single_material(i, source, content, summaries)
        sections.extend(material_section)
    
    return '\n'.join(sections)


def _format_single_material(index: int, source: str, content: str, summaries: List[Dict]) -> List[str]:
    """Format a single material with its metadata and content"""
    sections = []
    
    # Find matching summary
    summary = _find_material_summary(source, summaries)
    
    # Add material header
    sections.append(f"SOURCE {index}: {source}")
    
    # Add metadata
    metadata_sections = _format_material_metadata(summary)
    sections.extend(metadata_sections)
    
    # Add content
    content_sections = _format_material_content(content)
    sections.extend(content_sections)
    
    sections.append("")  # Empty line separator
    
    return sections


def _find_material_summary(source: str, summaries: List[Dict]) -> Dict:
    """Find the summary for a given material source"""
    return next((s for s in summaries if s.get('source') == source), {})


def _format_material_metadata(summary: Dict) -> List[str]:
    """Format material metadata from summary"""
    sections = []
    
    if technologies := summary.get('technologies', []):
        sections.append(f"Technologies: {', '.join(technologies)}")
    
    if key_concepts := summary.get('key_concepts', []):
        sections.append(f"Key Concepts: {', '.join(key_concepts)}")
    
    sections.append(f"Summary: {summary.get('summary', 'No summary available')}")
    
    return sections


def _format_material_content(content: str) -> List[str]:
    """Format the actual content of a material"""
    return [
        "\nFULL CONTENT:",
        "-" * 80,
        content,
        "-" * 80
    ]


def format_chunks_for_reference(chunks: List[Dict]) -> str:
    """Format reference chunks for style and context"""
    if not chunks:
        return "=== REFERENCE CHUNKS ===\n\nNo reference chunks available."
    
    sections = ["=== REFERENCE CHUNKS (For Style and Context) ===\n"]
    
    for i, chunk in enumerate(chunks[:5], 1):  # Top 5 chunks
        sections.append(f"REFERENCE {i}:")
        sections.append(f"File: {chunk.get('file', 'Unknown')}")
        sections.append(f"Section: {chunk.get('section', 'Unknown')}")
        sections.append(f"Relevance: {chunk.get('relevance_score', 0):.2f}")
        sections.append(f"Content Preview: {chunk.get('content', '')[:200]}...")
        sections.append("")
    
    return '\n'.join(sections)


def get_content_type_template(content_type: str, standards: Dict) -> str:
    """Get the template for a specific content type"""
    # Find the content type in standards
    ct_info = next((ct for ct in standards.get('contentTypes', []) 
                   if ct['name'] == content_type), None)
    
    if not ct_info:
        return f"=== CONTENT TYPE: {content_type} ===\n\nNo template available. Use standard documentation structure."
    
    template = f"=== CONTENT TYPE: {content_type} ===\n\n"
    template += f"Purpose: {ct_info.get('purpose', '')}\n"
    template += f"Description: {ct_info.get('description', '')}\n\n"
    
    if ct_info.get('structure'):
        template += "REQUIRED STRUCTURE:\n"
        for section in ct_info['structure']:
            template += f"- {section}\n"
    
    template += f"\nFRONTMATTER REQUIREMENTS:\n"
    for key, value in ct_info.get('frontMatter', {}).items():
        template += f"- {key}: {value}\n"
    
    return template


def format_microsoft_elements(content_standards: Dict) -> str:
    """Format Microsoft-specific formatting elements for prompt inclusion"""
    if not content_standards:
        return ""
    
    formatting_elements = content_standards.get('formattingElements', [])
    code_guidelines = content_standards.get('codeGuidelines', {})
    
    # Build formatting guide
    lines = ["=== MICROSOFT DOCUMENTATION FORMATTING ===\n"]
    
    # Add special elements
    lines.append("SPECIAL FORMATTING ELEMENTS:")
    for element in formatting_elements:
        lines.append(f"\n{element['name']}:")
        lines.append(f"Format: {element['format']}")
        if element['name'] in ['Note', 'Warning', 'Tip']:
            lines.append(f"Use for: {element['name'].lower()} callouts that need reader attention")
        elif element['name'] == 'Checklist':
            lines.append("Use for: Tutorial objectives or feature lists")
        elif element['name'] == 'Next step link':
            lines.append("Use for: Prominent navigation to the next article in a series")
    
    # Add code language guidelines
    lines.append("\n\nCODE BLOCK LANGUAGES:")
    languages = code_guidelines.get('languages', [])
    for lang in languages:
        lines.append(f"- {lang['syntax']} - {lang['useFor']}")
    
    # Add common tab groups
    tab_groups = content_standards.get('commonTabGroups', [])
    if tab_groups:
        lines.append("\n\nTAB GROUPS (for multiple approaches):")
        lines.append("Format: #### [Tab Name](#tab/tab-id)")
        lines.append("Common groups: Azure portal, Azure CLI, PowerShell, ARM template, Bicep")
        lines.append("End with: ---")
    
    # Add security reminders
    lines.append("\n\nSECURITY REQUIREMENTS:")
    lines.append("- Use <placeholder-name> for all sensitive values")
    lines.append("- NEVER include real credentials or secrets")
    lines.append("- Show managed identity approaches when applicable")
    
    return "\n".join(lines)


def schema_to_example(schema: dict, include_descriptions: bool = False) -> dict:
    """Convert JSON schema to example JSON for LLM prompts
    
    Args:
        schema: JSON schema dictionary
        include_descriptions: Whether to include field descriptions as comments
        
    Returns:
        Example JSON that matches the schema
    """
    if not isinstance(schema, dict) or 'properties' not in schema:
        return {}
    
    example = {}
    properties = schema.get('properties', {})
    
    for field_name, field_schema in properties.items():
        field_type = field_schema.get('type')
        
        if field_type == 'string':
            # Generate example based on field name and constraints
            if 'pattern' in field_schema:
                if field_schema['pattern'] == '^1\\.':
                    example[field_name] = "1. First analysis step...\n2. Second step...\n3. Final step..."
                elif field_schema['pattern'] == '^[^/]+\\.md$':
                    example[field_name] = "example-file.md"
                else:
                    example[field_name] = "example string"
            elif 'enum' in field_schema:
                example[field_name] = field_schema['enum'][0]
            elif field_name == 'source':
                example[field_name] = "./path/to/source"
            elif field_name == 'working_directory':
                example[field_name] = "articles/service-name"
            elif 'summary' in field_name:
                example[field_name] = "Comprehensive summary of the content covering key points and insights."
            else:
                max_length = field_schema.get('maxLength', 50)
                example[field_name] = f"Example {field_name.replace('_', ' ')}"[:max_length]
                
        elif field_type == 'array':
            # Generate array examples
            if field_name == 'thinking':
                example[field_name] = [
                    "First, I'll analyze the provided content and understand the requirements",
                    "Next, I'll identify key technical concepts and technologies mentioned",
                    "Then, I'll structure the information according to the expected format",
                    "Finally, I'll ensure all required fields are properly populated"
                ]
            elif field_name == 'decisions' and 'items' in field_schema and field_schema['items'].get('type') == 'object':
                # Handle decisions array with object schema
                item_schema = field_schema['items']
                decision_example = {
                    "action": "CREATE",
                    "filename": "example-guide.md",
                    "content_type": "How-To Guide",
                    "ms_topic": "how-to",
                    "reason": "No existing documentation covers this topic. Materials provide comprehensive information requiring new content creation.",
                    "priority": "high",
                    "relevant_chunks": ["chunk_id_1", "chunk_id_2"],
                    "content_brief": {
                        "objective": "Enable readers to accomplish specific task",
                        "key_points_to_cover": ["Point 1", "Point 2"],
                        "prerequisites_to_state": ["Prerequisite 1", "Prerequisite 2"],
                        "next_steps_to_suggest": ["Next step 1", "Next step 2"]
                    }
                }
                example[field_name] = [decision_example]
            elif field_name == 'technologies':
                example[field_name] = ["Technology1", "Technology2", "Framework1"]
            elif field_name == 'key_concepts':
                example[field_name] = ["concept1", "concept2", "methodology1"]
            elif field_name == 'microsoft_products':
                example[field_name] = ["Azure Service1", "Azure Service2"]
            elif 'chunks' in field_name:
                example[field_name] = ["chunk_id_1", "chunk_id_2"]
            else:
                # Handle other arrays with item schemas
                if 'items' in field_schema and field_schema['items'].get('type') == 'object':
                    # Recursively generate example for array of objects
                    item_example = schema_to_example({'properties': field_schema['items'].get('properties', {})})
                    example[field_name] = [item_example] if item_example else ["item1"]
                else:
                    example[field_name] = ["item1", "item2", "item3"]
                
        elif field_type == 'number':
            # Generate number examples based on constraints
            minimum = field_schema.get('minimum', 0)
            maximum = field_schema.get('maximum', 1)
            if maximum <= 1:
                example[field_name] = 0.85
            else:
                example[field_name] = (minimum + maximum) / 2
                
        elif field_type == 'integer':
            example[field_name] = field_schema.get('minimum', 1)
            
        elif field_type == 'boolean':
            example[field_name] = True
            
        elif field_type == 'object':
            # Recursively handle nested objects
            if 'properties' in field_schema:
                example[field_name] = schema_to_example(field_schema, include_descriptions)
            else:
                example[field_name] = {"key": "value"}
                
        elif isinstance(field_type, list):  # Union types like ["string", "null"]
            if "null" in field_type:
                example[field_name] = None
            else:
                # Use the first non-null type
                for t in field_type:
                    if t != "null":
                        field_schema_copy = field_schema.copy()
                        field_schema_copy['type'] = t
                        example[field_name] = schema_to_example(
                            {'properties': {field_name: field_schema_copy}}, 
                            include_descriptions
                        )[field_name]
                        break
    
    return example


def extract_type_requirements(schema: dict) -> str:
    """Extract human-readable type requirements from JSON schema
    
    Args:
        schema: JSON schema dictionary
        
    Returns:
        Formatted string describing type requirements
    """
    if not isinstance(schema, dict) or 'properties' not in schema:
        return ""
    
    requirements = []
    properties = schema.get('properties', {})
    required_fields = schema.get('required', [])
    
    for field_name, field_schema in properties.items():
        field_type = field_schema.get('type', 'any')
        is_required = field_name in required_fields
        
        # Build requirement description
        req_parts = [f"- {field_name}:"]
        
        # Add type information
        if field_type == 'string':
            req_parts.append("MUST be a STRING")
            if 'pattern' in field_schema:
                req_parts.append(f"(pattern: {field_schema['pattern']})")
            if 'minLength' in field_schema:
                req_parts.append(f"(min length: {field_schema['minLength']})")
            if 'maxLength' in field_schema:
                req_parts.append(f"(max length: {field_schema['maxLength']})")
                
        elif field_type == 'array':
            req_parts.append("MUST be an ARRAY/LIST")
            items_type = field_schema.get('items', {}).get('type', 'any')
            req_parts.append(f"of {items_type}s")
            if 'minItems' in field_schema:
                req_parts.append(f"(min items: {field_schema['minItems']})")
            if 'maxItems' in field_schema:
                req_parts.append(f"(max items: {field_schema['maxItems']})")
                
        elif field_type == 'number':
            req_parts.append("MUST be a NUMBER")
            if 'minimum' in field_schema and 'maximum' in field_schema:
                req_parts.append(f"(range: {field_schema['minimum']}-{field_schema['maximum']})")
                
        elif field_type == 'integer':
            req_parts.append("MUST be an INTEGER")
            if 'minimum' in field_schema:
                req_parts.append(f"(min: {field_schema['minimum']})")
                
        elif field_type == 'boolean':
            req_parts.append("MUST be a BOOLEAN (true/false)")
            
        elif field_type == 'object':
            req_parts.append("MUST be an OBJECT")
            if 'properties' in field_schema:
                req_parts.append(f"with fields: {', '.join(field_schema['properties'].keys())}")
                
        elif isinstance(field_type, list):
            types_str = " or ".join(t.upper() for t in field_type)
            req_parts.append(f"MUST be {types_str}")
        
        if is_required:
            req_parts.append("[REQUIRED]")
        else:
            req_parts.append("[OPTIONAL]")
            
        requirements.append(" ".join(req_parts))
    
    return "\n".join(requirements) 