"""
Content Quality Prompt - Supporting Prompts
Evaluates content quality against Microsoft documentation standards
"""
from typing import Dict


def get_content_quality_prompt(content: str, content_type: str, requirements: Dict) -> str:
    """Get the prompt for evaluating content quality"""
    
    return f"""Evaluate the quality of this technical documentation against Microsoft standards.

CONTENT TYPE: {content_type}

CONTENT TO EVALUATE:
{content}

REQUIREMENTS:
{requirements}

Assess the content for:
1. Completeness - Are all required sections present?
2. Technical accuracy - Is the information correct and precise?
3. Clarity - Is the content easy to understand?
4. Structure - Does it follow the template for this content type?
5. Style - Does it match Microsoft's documentation style?
6. Formatting - Are Microsoft elements used correctly?

Identify:
- Missing required sections
- Style guide violations
- Formatting issues
- Unclear or ambiguous content
- Improvement opportunities

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking": [
    "YOUR assessment of content structure",
    "YOUR evaluation of technical accuracy",
    "YOUR analysis of clarity and style"
  ],
  "clarity_score": 8.5,
  "completeness_score": 9.0,
  "accuracy_indicators": [
    "Code examples are syntactically correct",
    "API references match current version",
    "Configuration values are valid"
  ],
  "improvement_areas": [
    "Add more detailed examples for complex scenarios",
    "Include troubleshooting section",
    "Clarify prerequisites section"
  ],
  "strengths": [
    "Clear step-by-step instructions",
    "Good use of NOTE and WARNING callouts",
    "Well-structured content flow"
  ]
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL analysis steps (2-10 items)
- clarity_score: Number between 0-10 rating content clarity
- completeness_score: Number between 0-10 rating content completeness
- accuracy_indicators: Array of specific accuracy observations
- improvement_areas: Array of specific areas needing improvement
- strengths: Array of content strengths and positive aspects"""


def get_content_quality_system() -> str:
    """Get the system prompt for content quality evaluation"""
    return """You are an expert documentation quality reviewer specializing in Microsoft technical documentation standards.

CORE COMPETENCIES:
1. Microsoft documentation style guide expertise
2. Technical accuracy assessment
3. Content structure analysis
4. Clarity and readability evaluation
5. Formatting and element usage review

EVALUATION CRITERIA:

COMPLETENESS:
- All required sections present
- No missing critical information
- Appropriate depth for audience
- Examples and scenarios included
- Proper frontmatter metadata

TECHNICAL ACCURACY:
- Correct technical information
- Accurate command syntax
- Valid configuration examples
- Proper API references
- Current version information

CLARITY:
- Clear, concise writing
- Well-defined terms
- Logical flow
- Appropriate technical level
- No ambiguous instructions

STRUCTURE:
- Follows content type template
- Proper section ordering
- Logical information hierarchy
- Terminal sections at end
- Consistent heading levels

STYLE:
- Active voice preferred
- Present tense for facts
- Imperative mood for instructions
- Consistent terminology
- Professional tone

FORMATTING:
- Proper use of NOTE, TIP, WARNING
- Correct code fence syntax
- Valid markdown formatting
- Proper link formatting
- Correct frontmatter YAML

OUTPUT REQUIREMENTS:
- Objective quality assessment
- Specific improvement recommendations
- Actionable feedback
- Priority ranking of issues
- Overall quality score with justification""" 