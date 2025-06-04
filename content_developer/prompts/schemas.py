"""
JSON Schemas for all LLM response formats in AI Content Developer

This module defines strict JSON schemas for validating all LLM responses.
Each schema enforces exact field types and structure to prevent runtime errors.
"""

# Material Analysis Schema
MATERIAL_ANALYSIS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "thinking", "main_topic", "technologies", "key_concepts", 
        "microsoft_products", "document_type", "summary", "source"
    ],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of analysis steps",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 20
        },
        "main_topic": {
            "type": "string",
            "minLength": 5,
            "maxLength": 200
        },
        "technologies": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 20
        },
        "key_concepts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 15
        },
        "microsoft_products": {
            "type": "array",
            "items": {"type": "string"}
        },
        "document_type": {
            "type": "string",
            "minLength": 3,
            "maxLength": 50
        },
        "summary": {
            "type": "string",
            "minLength": 50,
            "maxLength": 500
        },
        "source": {
            "type": "string"
        }
    },
    "additionalProperties": False
}

# Directory Selection Schema
DIRECTORY_SELECTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "thinking", "working_directory", "justification", 
        "confidence", "structure_insights", "validation"
    ],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of analysis steps",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 20
        },
        "working_directory": {
            "type": "string",
            "pattern": "^[^/\\s].*[^/\\s]$",  # No leading/trailing slashes or spaces
            "minLength": 1
        },
        "justification": {
            "type": "string",
            "minLength": 50
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "structure_insights": {
            "type": "object",
            "required": ["pattern", "pattern_description", "depth", "has_docs", "doc_types"],
            "properties": {
                "pattern": {
                    "type": "string",
                    "enum": ["service-based", "topic-based", "technology-based", "hybrid", "flat", "unknown"]
                },
                "pattern_description": {"type": "string"},
                "depth": {"type": "integer", "minimum": 1, "maximum": 10},
                "has_docs": {"type": "boolean"},
                "doc_types": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "additionalProperties": False
        },
        "validation": {
            "type": "object",
            "required": ["is_valid", "is_documentation_directory", "pattern_match", "reason", "concerns"],
            "properties": {
                "is_valid": {"type": "boolean"},
                "is_documentation_directory": {"type": "boolean"},
                "pattern_match": {"type": "string"},
                "reason": {"type": "string"},
                "concerns": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "suggested_alternative": {
                    "type": ["string", "null"]
                }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}

# Content Strategy Schema
CONTENT_STRATEGY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking", "decisions", "confidence", "summary"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of analysis steps",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 20
        },
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action", "filename", "reason", "priority"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["CREATE", "UPDATE"]
                    },
                    "filename": {
                        "type": "string",
                        "pattern": "^[^/]+\\.md$"  # No paths, must end with .md
                    },
                    "content_type": {"type": "string"},
                    "ms_topic": {"type": "string"},
                    "reason": {
                        "type": "string",
                        "minLength": 50
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    },
                    "relevant_chunks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "content_brief": {
                        "type": "object"
                    },
                    "change_description": {
                        "type": "string",
                        "description": "Required for UPDATE actions"
                    },
                    "specific_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Required for UPDATE actions"
                    },
                    "current_content_type": {
                        "type": "string",
                        "description": "Required for UPDATE actions"
                    }
                },
                "additionalProperties": False
            }
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "summary": {
            "type": "string",
            "maxLength": 500
        }
    },
    "additionalProperties": False
}

# Content Generation CREATE Schema
CREATE_CONTENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking", "content", "metadata"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of content generation steps",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 20
        },
        "content": {
            "type": "string",
            "description": "Complete markdown document",
            "minLength": 100
        },
        "metadata": {
            "type": "object",
            "required": ["word_count", "sections_created", "materials_used", "key_topics_covered"],
            "properties": {
                "word_count": {
                    "type": "integer",
                    "minimum": 50
                },
                "sections_created": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "materials_used": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "key_topics_covered": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}

# Content Generation UPDATE Schema
UPDATE_CONTENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking", "updated_document", "changes_summary", "metadata"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of update steps",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 20
        },
        "updated_document": {
            "type": "string",
            "description": "Complete updated markdown document",
            "minLength": 100
        },
        "changes_summary": {
            "type": "string",
            "minLength": 20
        },
        "metadata": {
            "type": "object",
            "required": ["sections_modified", "sections_added", "word_count_before", "word_count_after"],
            "properties": {
                "sections_modified": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "sections_added": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "word_count_before": {
                    "type": "integer",
                    "minimum": 0
                },
                "word_count_after": {
                    "type": "integer",
                    "minimum": 0
                }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}

# TOC Update Schema
TOC_UPDATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking", "placement_analysis", "content", "entries_added", "placement_decisions"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of TOC analysis steps",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 20
        },
        "placement_analysis": {
            "type": "object",
            "required": ["structure_type", "main_sections", "placement_rationale"],
            "properties": {
                "structure_type": {"type": "string"},
                "main_sections": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "placement_rationale": {"type": "string"}
            },
            "additionalProperties": False
        },
        "content": {
            "type": "string",
            "description": "Complete updated TOC.yml content"
        },
        "entries_added": {
            "type": "array",
            "items": {"type": "string"}
        },
        "placement_decisions": {
            "type": "object",
            "description": "Map of filename to placement decision"
        }
    },
    "additionalProperties": False
}

# Content Placement Schema
CONTENT_PLACEMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "thinking", "recommended_placement", "alternative_placements", 
        "creates_new_section", "new_section_name"
    ],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of placement analysis steps",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10
        },
        "recommended_placement": {
            "type": "string"
        },
        "alternative_placements": {
            "type": "array",
            "items": {"type": "string"}
        },
        "creates_new_section": {
            "type": "boolean"
        },
        "new_section_name": {
            "type": ["string", "null"]
        }
    },
    "additionalProperties": False
}

# Terminal Section Detection Schema
TERMINAL_SECTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking", "is_terminal", "pattern_matched"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of analysis steps",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10
        },
        "is_terminal": {
            "type": "boolean"
        },
        "pattern_matched": {
            "type": ["string", "null"]
        }
    },
    "additionalProperties": False
}

# Content Quality Analysis Schema
CONTENT_QUALITY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "thinking", "clarity_score", "completeness_score", 
        "accuracy_indicators", "improvement_areas", "strengths"
    ],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of quality analysis steps",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10
        },
        "clarity_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 10
        },
        "completeness_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 10
        },
        "accuracy_indicators": {
            "type": "array",
            "items": {"type": "string"}
        },
        "improvement_areas": {
            "type": "array",
            "items": {"type": "string"}
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "additionalProperties": False
}

# Chunk Ranking Schema
CHUNK_RANKING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking", "rankings", "top_chunks", "key_themes"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of ranking analysis steps",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10
        },
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["chunk_id", "relevance_score", "relevance_reason"],
                "properties": {
                    "chunk_id": {"type": "string"},
                    "relevance_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "relevance_reason": {"type": "string"}
                },
                "additionalProperties": False
            }
        },
        "top_chunks": {
            "type": "array",
            "items": {"type": "string"}
        },
        "key_themes": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "additionalProperties": False
}

# Information Extraction Base Schema
INFORMATION_EXTRACTION_BASE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["thinking"],
    "properties": {
        "thinking": {
            "type": "array",
            "description": "Array of extraction steps",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 10
        }
    },
    "additionalProperties": True  # Allow purpose-specific fields
}

# Information Extraction Schema Factory
def get_information_extraction_schema(purpose: str) -> dict:
    """Generate schema based on extraction purpose"""
    base = INFORMATION_EXTRACTION_BASE_SCHEMA.copy()
    
    # Directory validation purpose
    if "directory" in purpose.lower() and "validate" in purpose.lower():
        base["required"].extend([
            "is_valid", "is_documentation_directory", 
            "pattern_match", "reason", "concerns", "suggested_alternative"
        ])
        base["properties"].update({
            "is_valid": {"type": "boolean"},
            "is_documentation_directory": {"type": "boolean"},
            "pattern_match": {"type": "string"},
            "reason": {"type": "string"},
            "concerns": {
                "type": "array",
                "items": {"type": "string"}
            },
            "suggested_alternative": {"type": ["string", "null"]}
        })
        base["additionalProperties"] = False
    
    # Material sufficiency check
    elif "sufficiency" in purpose.lower() or "sufficient" in purpose.lower():
        base["required"].extend([
            "has_sufficient_information", "insufficient_areas", "coverage_percentage"
        ])
        base["properties"].update({
            "has_sufficient_information": {"type": "boolean"},
            "insufficient_areas": {
                "type": "array",
                "items": {"type": "string"}
            },
            "coverage_percentage": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            }
        })
        base["additionalProperties"] = False
    
    # Gap analysis
    elif "gap" in purpose.lower() or "missing" in purpose.lower():
        base["required"].extend(["missing_items", "recommendations"])
        base["properties"].update({
            "missing_items": {
                "type": "array",
                "items": {"type": "string"}
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"}
            }
        })
        base["additionalProperties"] = False
    
    return base

# Export all schemas
__all__ = [
    'MATERIAL_ANALYSIS_SCHEMA',
    'DIRECTORY_SELECTION_SCHEMA',
    'CONTENT_STRATEGY_SCHEMA',
    'CREATE_CONTENT_SCHEMA',
    'UPDATE_CONTENT_SCHEMA',
    'TOC_UPDATE_SCHEMA',
    'CONTENT_PLACEMENT_SCHEMA',
    'TERMINAL_SECTION_SCHEMA',
    'CONTENT_QUALITY_SCHEMA',
    'CHUNK_RANKING_SCHEMA',
    'INFORMATION_EXTRACTION_BASE_SCHEMA',
    'get_information_extraction_schema'
] 