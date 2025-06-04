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
    print(f"  {'✅' if result.toc_ready else '⏸️'} Phase 4 - TOC Management: {'Complete' if result.toc_ready else 'Incomplete'}")


def _display_strategy_summary(strategy):
    """Display content strategy summary"""
    create_count = sum(1 for decision in strategy.decisions if decision.get('action') == 'CREATE')
    update_count = sum(1 for decision in strategy.decisions if decision.get('action') == 'UPDATE')
    
    print(f"\n📋 Content Strategy:")
    print(f"  • Total Actions: {len(strategy.decisions)}")
    print(f"  • CREATE: {create_count} new files")
    print(f"  • UPDATE: {update_count} existing files")
    print(f"  • Confidence: {strategy.confidence:.0%}")


def _display_generation_results(gen_results: Dict):
    """Display content generation results"""
    summary = gen_results.get('summary', {})
    
    print(f"\n✨ Generation Results:")
    print(f"  • Created: {summary.get('create_success', 0)}/{summary.get('create_attempted', 0)}")
    print(f"  • Updated: {summary.get('update_success', 0)}/{summary.get('update_attempted', 0)}")
    
    # Show errors if any
    if summary.get('error'):
        print(f"\n❌ Generation Error: {summary['error']}")
    
    # Show file results
    _display_file_results(gen_results.get('create_results', []), "Created Files")
    _display_file_results(gen_results.get('update_results', []), "Updated Files")
    
    # Show debug info if available
    if debug_info := gen_results.get('debug_info'):
        _display_debug_info(debug_info)


def _display_file_results(results: List[Dict], title: str):
    """Display results for created or updated files"""
    if not results:
        return
    
    print(f"\n📝 {title} (Previews):")
    
    for res in results:
        filename = res['action'].get('filename', 'Unknown')
        
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
        
    print(f"  • {filename}")
    print(f"    Preview: {res['preview_path']}")


def _display_failed_result(res: Dict, filename: str):
    """Display a failed file result"""
    print(f"  • {filename} - FAILED")
    
    gap_report = res.get('gap_report')
    if not gap_report:
        return
        
    missing_info = gap_report.get('missing_info', [])
    if missing_info:
        print(f"    Missing: {', '.join(missing_info)}")


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
        for info in gap.get('missing_info', []):
            print(f"     - {info}")


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
        print(f"\n⚠️  Generated content is in preview mode!")
        if generation_preview:
            print(f"   • New/updated files are not applied")
        if toc_preview:
            print(f"   • TOC changes are not applied")
        print(f"   To apply changes to the repository, run with --apply-changes flag")


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
        
        # Show entries added
        if entries_added := toc_results.get('entries_added', []):
            print(f"  • Entries Added ({len(entries_added)}):")
            for entry in entries_added[:5]:  # Show first 5
                print(f"    - {entry}")
            if len(entries_added) > 5:
                print(f"    ... and {len(entries_added) - 5} more")
        
        # Show entries verified
        if entries_verified := toc_results.get('entries_verified', []):
            print(f"  • Entries Verified: {len(entries_verified)}")
        
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