"""
Terminal Section Prompt - Supporting Prompts
Identifies terminal sections (Next Steps, Related Content) in documents
"""
from typing import List


def get_terminal_section_prompt(sections: List[str]) -> str:
    """Get the prompt for identifying terminal sections"""
    
    return f"""Analyze the following section headings and identify which are terminal sections.

Terminal sections are the concluding sections of a document that:
- Guide readers to next steps or related content
- Provide additional resources or references
- Summarize or conclude the document
- Should always appear at the end of the document

Common terminal section patterns:
- "Next steps" / "What's next"
- "Related content" / "Related articles"
- "See also" / "Learn more"
- "Additional resources" / "Further reading"
- "References" / "Resources"
- "Summary" / "Conclusion"

SECTIONS TO ANALYZE:
{chr(10).join(f'- {section}' for section in sections)}

For each section, determine if it's a terminal section based on:
1. The section name pattern
2. Its typical purpose in documentation
3. Whether it should appear at the end

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking": [
    "YOUR analysis of the section name",
    "YOUR evaluation of its purpose",
    "YOUR determination of terminal status"
  ],
  "is_terminal": true,
  "pattern_matched": "Next steps"
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL analysis steps (2-10 items)
- is_terminal: Boolean indicating if this is a terminal section
- pattern_matched: String of the terminal pattern matched (e.g., "Next steps", "Related content") or null if not terminal

Note: Process EACH section individually and return separate JSON for each."""


TERMINAL_SECTION_SYSTEM = """You are an expert at analyzing documentation structure and identifying terminal sections.

CORE KNOWLEDGE:
Terminal sections are the final sections in technical documentation that help readers:
1. Navigate to related content
2. Find next steps in their learning journey
3. Access additional resources
4. Review what was covered

TERMINAL SECTION PATTERNS:
1. Navigation sections: "Next steps", "What's next", "Where to go from here"
2. Related content: "Related articles", "Related content", "See also"
3. Resources: "Additional resources", "Learn more", "Further reading"
4. References: "References", "External links", "Resources"
5. Conclusions: "Summary", "Conclusion", "Wrapping up"

ANALYSIS CRITERIA:
- Section name matches common terminal patterns
- Purpose is to guide readers after main content
- Typically contains links or navigation guidance
- Should logically appear at document end
- Helps readers continue their journey

NON-TERMINAL SECTIONS:
- Main content sections (procedures, concepts)
- Prerequisites or requirements
- Technical details or examples
- Troubleshooting (unless specifically "Troubleshooting resources")
- Configuration or setup sections

OUTPUT REQUIREMENTS:
- Accurately classify each section
- Provide clear reasoning for classification
- Flag any ambiguous cases
- Ensure terminal sections are identified for proper placement""" 