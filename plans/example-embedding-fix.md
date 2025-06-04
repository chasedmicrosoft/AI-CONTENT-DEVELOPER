# Plan: Fix Embedding Type Conversion Issues

**Date**: 2024-05-31  
**Author**: AI Assistant  
**Type**: Bug Fix  
**Priority**: High  
**Estimated Time**: 3 hours  

## Objective
Fix type conversion issues where embeddings are sometimes stored as strings instead of float lists, causing runtime errors in similarity calculations.

## Current State Analysis
- Embeddings from OpenAI are lists of floats
- When stored/retrieved from cache, they may be strings
- This causes TypeError in cosine similarity calculations
- Affects Phase 2 strategy generation

## Proposed Solution

### Technical Approach
Add defensive type checking and conversion to ensure embeddings are always float lists

### Affected Components
- [ ] Component 1: [strategy.py](mdc:content_developer/processors/strategy.py)
- [ ] Component 2: [discovery.py](mdc:content_developer/processors/discovery.py)
- [ ] Component 3: [content_generator.py](mdc:content_developer/generation/content_generator.py)
- [ ] Component 4: [config.py](mdc:content_developer/models/config.py)

### Implementation Steps
1. **Step 1**: Add `_ensure_float_list()` method to strategy processor
   - Handle string representations
   - Convert all elements to floats
   - Add error logging
2. **Step 2**: Update embedding retrieval methods
   - Apply conversion when loading from cache
   - Apply conversion before calculations
3. **Step 3**: Add defensive checks in content generator
   - Validate decision structures
   - Handle malformed data gracefully
4. **Step 4**: Ensure directories exist before writing
   - Update Config post-init
   - Add mkdir calls in save methods

## Success Criteria
- [ ] No TypeError in embedding operations
- [ ] All phases complete successfully
- [ ] Cached embeddings work correctly
- [ ] Directory creation is automatic

## Risk Assessment
- **Risk 1**: Breaking existing embeddings → Test with existing cache
- **Risk 2**: Performance impact → Minimal, only type checking

## Testing Strategy
- Run full pipeline with test repository
- Test with corrupted cache data
- Verify all phases complete

## Documentation Updates
- [ ] Update ARCHITECTURE.md error handling section
- [ ] Document type safety in SmartProcessor
- [ ] Add to troubleshooting guide

## Rollback Plan
Remove type conversion methods and revert to previous version 