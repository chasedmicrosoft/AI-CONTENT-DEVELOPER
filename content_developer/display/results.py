"""
Results display utilities
"""
from pathlib import Path
from typing import Dict, List

from ..models import Result


def display_results(result: Result):
    """Display final results"""
    _print_header()
    _display_basic_info(result)
    _display_materials(result)
    _display_phase_status(result)
    
    if result.content_strategy:
        _display_strategy_summary(result.content_strategy)
    
    if result.generation_results:
        _display_generation_results(result.generation_results)
    
    if result.remediation_results:
        _display_remediation_results(result.remediation_results)
    
    if result.toc_results:
        _display_toc_results(result.toc_results)
    
    _display_output_locations(result)
    _display_apply_reminder(result)
    _print_footer()


def _print_header():
    """Print results header"""
    print("\n" + "="*80)
    print("AI CONTENT DEVELOPER - RESULTS")
    print("="*80)


def _print_footer():
    """Print results footer"""
    print("\n" + "="*80)


def _display_basic_info(result: Result):
    """Display basic repository and goal information"""
    print(f"\n📁 Repository: {result.repo_url}")
    print(f"📂 Working Directory: {result.working_directory}")
    print(f"🎯 Goal: {result.content_goal}")
    print(f"🏢 Service Area: {result.service_area}")


def _display_materials(result: Result):
    """Display support materials summary"""
    if result.material_summaries:
        print(f"\n📚 Support Materials ({len(result.material_summaries)}):")
        for mat in result.material_summaries:
            print(f"  • {mat.get('source', 'Unknown')}: {mat.get('main_topic', 'No topic')}")


def _display_phase_status(result: Result):
    """Display phase completion status"""
    print(f"\n📊 Phase Status:")
    print(f"  ✅ Phase 1 - Repository Analysis: {'Complete' if result.directory_ready else 'Incomplete'}")
    print(f"  {'✅' if result.strategy_ready else '⏸️'} Phase 2 - Content Strategy: {'Complete' if result.strategy_ready else 'Incomplete'}")
    print(f"  {'✅' if result.generation_ready else '⏸️'} Phase 3 - Content Generation: {'Complete' if result.generation_ready else 'Incomplete'}")
    print(f"  {'✅' if result.remediation_ready else '⏸️'} Phase 4 - Content Remediation: {'Complete' if result.remediation_ready else 'Incomplete'}")
    print(f"  {'✅' if result.toc_ready else '⏸️'} Phase 5 - TOC Management: {'Complete' if result.toc_ready else 'Incomplete'}")


def _display_strategy_summary(strategy):
    """Display content strategy summary"""
    create_count = sum(1 for decision in strategy.decisions if decision.action == 'CREATE')
    update_count = sum(1 for decision in strategy.decisions if decision.action == 'UPDATE')
    skip_count = sum(1 for decision in strategy.decisions if decision.action == 'SKIP')
    
    print(f"\n📋 Content Strategy:")
    print(f"   Total Decisions: {len(strategy.decisions)}")
    print(f"   Files to Create: {create_count}")
    print(f"   Files to Update: {update_count}")
    print(f"   Files to Skip: {skip_count}")
    print(f"   Confidence: {strategy.confidence:.1%}")
    
    # Show each decision
    for i, decision in enumerate(strategy.decisions, 1):
        action_emoji = {
            'CREATE': '🆕',
            'UPDATE': '📝',
            'SKIP': '⏭️'
        }.get(decision.action, '📄')
        
        print(f"\n   {i}. {action_emoji} {decision.action}: {getattr(decision, 'file_title', getattr(decision, 'filename', 'Unknown'))}")
        if hasattr(decision, 'rationale') and decision.rationale:
            print(f"      Reason: {decision.rationale}")
        elif hasattr(decision, 'reason') and decision.reason:
            print(f"      Reason: {decision.reason}")
        if hasattr(decision, 'priority'):
            print(f"      Priority: {decision.priority}")


def _display_generation_results(gen_results: Dict):
    """Display content generation results"""
    summary = gen_results.get('summary', {})
    
    print(f"\n✨ Generation Results:")
    print(f"  • Created: {summary.get('create_success', 0)}/{summary.get('create_attempted', 0)}")
    print(f"  • Updated: {summary.get('update_success', 0)}/{summary.get('update_attempted', 0)}")
    
    # Show skipped results
    skip_results = gen_results.get('skip_results', [])
    if skip_results:
        insufficient_count = sum(1 for s in skip_results if s.get('status') == 'skipped_insufficient_materials')
        skip_count = len(skip_results) - insufficient_count
        if skip_count > 0:
            print(f"  • Skipped (by design): {skip_count}")
        if insufficient_count > 0:
            print(f"  • Skipped (insufficient materials): {insufficient_count}")
    
    # Show errors if any
    if summary.get('error'):
        print(f"\n❌ Generation Error: {summary['error']}")
    
    # Show file results
    _display_file_results(gen_results.get('create_results', []), "Created Files")
    _display_file_results(gen_results.get('update_results', []), "Updated Files")
    
    # Show skipped due to insufficient materials
    _display_skipped_results(skip_results)
    
    # Show debug info if available
    if debug_info := gen_results.get('debug_info'):
        _display_debug_info(debug_info)


def _display_file_results(results: List[Dict], title: str):
    """Display results for created or updated files"""
    if not results:
        return
    
    print(f"\n📝 {title} (Previews):")
    
    for res in results:
        # Get filename from the action object (ContentDecision)
        action = res.get('action')
        if action:
            # ContentDecision object - access attributes directly
            filename = getattr(action, 'filename', getattr(action, 'target_file', 'Unknown'))
        else:
            filename = 'Unknown'
        
        # Handle successful results
        if res.get('success'):
            _display_successful_result(res, filename)
            continue
        
        # Handle failed results
        _display_failed_result(res, filename)


def _display_successful_result(res: Dict, filename: str):
    """Display a successful file result"""
    if not res.get('preview_path'):
        return
    
    # Clean up filename to show relative path only
    # Remove any absolute path components
    display_filename = filename
    if '/' in display_filename:
        # If it contains the working directory path, extract relative part
        parts = display_filename.split('/')
        # Look for common directory names that indicate start of relative path
        for i, part in enumerate(parts):
            if part in ['articles', 'docs', 'content']:
                display_filename = '/'.join(parts[i:])
                break
    
    print(f"  • {display_filename}")
    print(f"    Preview: {res['preview_path']}")


def _display_failed_result(res: Dict, filename: str):
    """Display a failed file result"""
    print(f"  • {filename} - FAILED")
    
    gap_report = res.get('gap_report')
    if not gap_report:
        if error := res.get('error'):
            print(f"    Error: {error}")
        return
        
    # Show coverage percentage if available
    if 'coverage_percentage' in gap_report:
        print(f"    Coverage: {gap_report['coverage_percentage']:.0f}%")
    
    # Show missing information
    missing_info = gap_report.get('missing_info', [])
    if missing_info:
        print(f"    Missing: {', '.join(missing_info[:2])}")  # Show first 2
        if len(missing_info) > 2:
            print(f"    ... and {len(missing_info) - 2} more gaps")
    
    # Show suggestions if available
    suggestions = gap_report.get('suggestions', [])
    if suggestions:
        print(f"    💡 Add: {suggestions[0]}")  # Show first suggestion
        if len(suggestions) > 1:
            print(f"    ... and {len(suggestions) - 1} more suggestions")


def _display_debug_info(debug_info: Dict):
    """Display debug information"""
    print(f"\n🔍 Debug Information:")
    print(f"  • Materials Loaded: {len(debug_info.get('materials_loaded', []))}")
    print(f"  • Total Chunks: {debug_info.get('total_chunks_available', 0)}")
    print(f"  • Chunks with Content: {debug_info.get('chunks_with_content', 0)}")
    print(f"  • Generation Mode: {debug_info.get('generation_mode', 'Unknown')}")
    
    # Show gap reports summary
    if gap_reports := debug_info.get('gap_reports'):
        _display_gap_reports(gap_reports)


def _display_gap_reports(gap_reports: List[Dict]):
    """Display gap reports summary"""
    print(f"\n⚠️  Gap Reports ({len(gap_reports)}):")
    for i, gap in enumerate(gap_reports, 1):
        print(f"  {i}. {gap.get('requested_file', 'Unknown file')}")
        
        # Show coverage percentage if available
        if 'coverage_percentage' in gap:
            print(f"     Coverage: {gap['coverage_percentage']:.0f}%")
        
        # Show missing information
        missing_info = gap.get('missing_info', [])
        if missing_info:
            print(f"     Missing Information:")
            for info in missing_info:
                print(f"       - {info}")
        
        # Show suggestions if available
        suggestions = gap.get('suggestions', [])
        if suggestions:
            print(f"     💡 Suggestions to make materials sufficient:")
            for suggestion in suggestions:
                print(f"       - {suggestion}")


def _display_output_locations(result: Result):
    """Display output file locations"""
    print(f"\n📂 Output Locations:")
    print(f"  • LLM Outputs: ./llm_outputs/")
    print(f"  • Embeddings Cache: ./llm_outputs/embeddings/{Path(result.repo_url).stem}/{result.working_directory}/")
    print(f"  • Content Previews: ./llm_outputs/preview/")


def _display_apply_reminder(result: Result):
    """Display reminder about applying changes"""
    # Check if content generation is in preview mode
    generation_preview = (result.generation_ready and 
                         not result.generation_results.get('applied', False))
    
    # Check if TOC changes are in preview mode
    toc_preview = (result.toc_ready and 
                   result.toc_results.get('changes_made', False) and
                   not result.toc_results.get('applied', False))
    
    if generation_preview or toc_preview:
        print(f"\n⚠️  All changes are in preview mode!")
        print(f"   • Generated content saved to: ./llm_outputs/preview/")
        if generation_preview:
            print(f"   • Repository files: NOT modified")
        if toc_preview:
            print(f"   • TOC.yml: NOT modified")
        print(f"\n   ✅ To apply ALL changes to the repository:")
        print(f"      Run with --apply-changes flag")


def _display_skipped_results(skip_results: List[Dict]):
    """Display files that were skipped"""
    if not skip_results:
        return
    
    # Separate by skip reason
    insufficient_skips = []
    design_skips = []
    
    for res in skip_results:
        if res.get('status') == 'skipped_insufficient_materials':
            insufficient_skips.append(res)
        else:
            design_skips.append(res)
    
    # Show insufficient materials skips
    if insufficient_skips:
        print(f"\n⚠️  Skipped Due to Insufficient Materials:")
        for res in insufficient_skips:
            decision = res.get('decision')
            if decision:
                filename = getattr(decision, 'file_title', getattr(decision, 'filename', 'Unknown'))
                print(f"  • {filename}")
                
                # Show material coverage if available
                if sufficiency := res.get('material_sufficiency'):
                    coverage = sufficiency.get('coverage_percentage', 0)
                    print(f"    Coverage: {coverage}% - {res.get('reason', 'Material coverage too low')}")
                    
                    # Show missing topics
                    if missing := sufficiency.get('missing_topics', []):
                        print(f"    Missing topics: {', '.join(missing[:3])}")
                        if len(missing) > 3:
                            print(f"    ... and {len(missing) - 3} more")
    
    # Show design skips (intentional skips from strategy)
    if design_skips:
        print(f"\n⏭️  Skipped by Design:")
        for res in design_skips:
            decision = res.get('decision')
            if decision:
                filename = getattr(decision, 'file_title', getattr(decision, 'filename', 'Unknown'))
                reason = res.get('reason', decision.rationale if hasattr(decision, 'rationale') else 'No reason provided')
                print(f"  • {filename}")
                print(f"    Reason: {reason[:100]}...")


def _display_toc_results(toc_results: Dict):
    """Display TOC management results"""
    print(f"\n📑 TOC Management Results:")
    print(f"  • Status: {toc_results.get('message', 'Unknown')}")
    
    if toc_results.get('changes_made'):
        print(f"  • Changes Made: Yes")
        
        # Show if changes were applied
        if toc_results.get('applied'):
            print(f"  • Applied to Repository: ✅ Yes")
        else:
            print(f"  • Applied to Repository: ❌ No (preview mode)")
        
        # Show TOC modifications
        entries_added = toc_results.get('entries_added', [])
        created_files = toc_results.get('created_files', [])
        
        # Separate new entries from verified ones
        new_entries = [e for e in entries_added if e in created_files]
        verified_entries = [e for e in entries_added if e not in created_files]
        
        if new_entries:
            print(f"  • New TOC Entries ({len(new_entries)}):")
            for entry in new_entries[:3]:  # Show first 3
                print(f"    - {entry}")
            if len(new_entries) > 3:
                print(f"    ... and {len(new_entries) - 3} more")
        
        if verified_entries:
            print(f"  • Verified Entries ({len(verified_entries)}):")
            for entry in verified_entries[:2]:  # Show first 2
                print(f"    - {entry}")
            if len(verified_entries) > 2:
                print(f"    ... and {len(verified_entries) - 2} more")
        
        # Show preview path
        if preview_path := toc_results.get('preview_path'):
            print(f"  • TOC Preview: {preview_path}")
    else:
        print(f"  • Changes Made: No")
        
        # Show detailed error information if available
        if error_details := toc_results.get('error_details'):
            print(f"  • Error Details:\n{error_details}")
        
        # Show suggestion if available
        if suggestion := toc_results.get('suggestion'):
            print(f"  • ℹ️  Suggestion: {suggestion}")
    
    # Show any errors
    if error := toc_results.get('error'):
        print(f"  • ❌ Error: {error}")


def _display_remediation_results(rem_results: Dict):
    """Display content remediation results"""
    summary = rem_results.get('summary', {})
    
    print(f"\n🔧 Remediation Results:")
    print(f"  • Files Processed: {summary.get('total_files', 0)}")
    print(f"  • SEO Optimized: {summary.get('success_rate', {}).get('seo', 0) * 100:.0f}%")
    print(f"  • Security Checked: {summary.get('success_rate', {}).get('security', 0) * 100:.0f}%")
    print(f"  • Accuracy Validated: {summary.get('success_rate', {}).get('accuracy', 0) * 100:.0f}%")
    print(f"  • All Steps Complete: {summary.get('all_steps_completed', 0)}")
    
    # Show individual file results if available
    if rem_results.get('remediation_results'):
        print(f"\n  Details:")
        for res in rem_results['remediation_results'][:5]:  # Show first 5
            filename = res.get('filename', 'Unknown')
            # Clean up filename display
            if '/' in filename:
                parts = filename.split('/')
                for i, part in enumerate(parts):
                    if part in ['articles', 'docs', 'content']:
                        filename = '/'.join(parts[i:])
                        break
            
            print(f"    • {filename}:")
            
            # Show SEO improvements
            if res.get('seo_success'):
                seo_improvements = res.get('seo_metadata', {}).get('seo_improvements', [])
                if seo_improvements:
                    print(f"      - SEO: {len(seo_improvements)} improvements applied")
                else:
                    print(f"      - SEO: ✅ Already optimized")
            else:
                print(f"      - SEO: ❌ Failed")
            
            # Show security status
            if res.get('security_success'):
                security_issues = res.get('security_metadata', {}).get('security_issues_found', [])
                if security_issues:
                    print(f"      - Security: {len(security_issues)} issues remediated")
                else:
                    print(f"      - Security: ✅ No issues found")
            else:
                print(f"      - Security: ❌ Failed")
            
            # Show accuracy status
            if res.get('accuracy_success'):
                accuracy_score = res.get('accuracy_metadata', {}).get('accuracy_score', 0)
                accuracy_issues = res.get('accuracy_metadata', {}).get('accuracy_issues', [])
                if accuracy_issues:
                    print(f"      - Accuracy: ✅ Validated ({accuracy_score*100:.0f}%) - {len(accuracy_issues)} corrections made")
                else:
                    print(f"      - Accuracy: ✅ Validated ({accuracy_score*100:.0f}%)")
            else:
                print(f"      - Accuracy: ❌ Failed")
        
        if len(rem_results['remediation_results']) > 5:
            print(f"    ... and {len(rem_results['remediation_results']) - 5} more files") 