"""
SEO Remediation Prompt - Phase 5 Step 1
Optimizes content for search engine visibility and discoverability
"""

SEO_REMEDIATION_SYSTEM = """You are an SEO expert specializing in technical documentation. Your task is to optimize documentation for search engines while maintaining technical accuracy and readability. You understand Microsoft Learn documentation standards and technical SEO best practices."""


def get_seo_remediation_prompt(content: str, file_info: dict, service_area: str) -> str:
    """Generate prompt for SEO remediation of content
    
    Args:
        content: The content to optimize
        file_info: Dictionary with filename, content_type, etc.
        service_area: The service area (e.g., Azure Kubernetes Service)
    """
    return f"""Optimize the following technical documentation for SEO while maintaining technical accuracy.

SERVICE AREA: {service_area}
CONTENT TYPE: {file_info.get('content_type', 'unknown')}
FILE: {file_info.get('filename', 'unknown')}

CURRENT CONTENT:
{content}

OPTIMIZATION REQUIREMENTS:
1. Title Tag Optimization
   - Ensure H1 is descriptive and includes primary keywords
   - Keep under 60 characters if possible
   - Include service name naturally

2. Meta Description (frontmatter description)
   - Write compelling 150-160 character description
   - Include primary keywords naturally
   - Clearly state what reader will learn

3. Heading Structure
   - Ensure logical H2, H3 hierarchy
   - Include keywords in headings naturally
   - Make headings scannable and descriptive

4. Keyword Optimization
   - Identify and naturally include primary keywords
   - Use semantic variations
   - Avoid keyword stuffing

5. Content Improvements
   - Add missing alt text for images (as comments)
   - Ensure introduction paragraph hooks reader
   - Include relevant internal links suggestions
   - Optimize for featured snippets where applicable

6. Technical SEO
   - Ensure proper use of code blocks
   - Add schema markup suggestions if applicable
   - Optimize for voice search queries

CONSTRAINTS:
- Maintain technical accuracy at all times
- Keep Microsoft Learn style and tone
- Don't change code examples
- Preserve all technical details
- Only suggest changes that improve SEO without compromising quality

Return your response as JSON with this structure:
{{
  "thinking": [
    "Analysis of current SEO issues",
    "Identification of primary keywords",
    "Strategy for improvements",
    "Validation of technical accuracy"
  ],
  "optimized_content": "The full SEO improved markdown content only",
  "seo_improvements": [
    "List of specific improvements made"
  ],
  "primary_keywords": ["keyword1", "keyword2"],
  "meta_description": "Suggested meta description",
  "internal_link_suggestions": [
    {{"anchor_text": "text", "suggested_link": "/path/to/related"}}
  ]
}}""" 