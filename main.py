#!/usr/bin/env python3
"""
AI Content Developer - Main Entry Point

A tool for analyzing repositories and generating documentation based on support materials.
"""
import argparse
import sys
from pathlib import Path
import logging
import os
import shutil
from urllib.parse import urlparse

from content_developer.models import Config
from content_developer.orchestrator import ContentDeveloperOrchestrator
from content_developer.display import display_results
from content_developer.display.console_display import ConsoleDisplay
from content_developer.utils.logging_config import setup_dual_logging, get_console
from content_developer.constants import MAX_PHASES


def perform_cleanup(console_display: ConsoleDisplay, work_dir: Path):
    """Clean up llm_outputs and work directory"""
    console_display.show_status("Cleaning up directories...", "info")
    
    # Directories to clean
    directories_to_clean = [
        "./llm_outputs",
        work_dir
    ]
    
    for directory in directories_to_clean:
        dir_path = Path(directory)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                console_display.show_status(f"Removed: {directory}", "success")
            except Exception as e:
                console_display.show_error(f"Failed to remove {directory}: {e}", "Warning")
        else:
            console_display.show_status(f"Directory not found: {directory}", "info")
    
    console_display.show_status("Cleanup complete", "success")
    console_display.print_separator()


def main():
    """Main entry point"""
    # Set up argument parser first
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set up dual logging before any other operations
    # Use INFO level for console if verbose, otherwise WARNING
    console_level = "INFO" if hasattr(args, 'verbose') and args.verbose else "WARNING"
    setup_dual_logging(console_level=console_level)
    
    # Create console display
    console = get_console()
    console_display = ConsoleDisplay(console)
    
    # Handle cleanup if requested
    if hasattr(args, 'clean') and args.clean:
        perform_cleanup(console_display, args.work_dir)
    
    # Validate arguments
    validate_arguments(parser, args)
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Execute workflow with console display
    execute_workflow(config, console_display)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="AI Content Developer - Generate documentation from support materials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_usage_examples()
    )
    
    # Add all argument groups
    add_required_arguments(parser)
    add_material_arguments(parser)
    add_audience_arguments(parser)
    add_workflow_arguments(parser)
    add_output_arguments(parser)
    add_debug_arguments(parser)
    
    return parser


def get_usage_examples() -> str:
    """Get formatted usage examples for help text"""
    return """
Examples:
  # Basic usage with materials
  python main.py --repo https://github.com/user/repo --goal "Create CNI docs" \\
    --service "Azure Kubernetes Service" -m material1.pdf material2.md
  
  # Clean previous runs and start fresh
  python main.py --repo https://github.com/user/repo --goal "Create tutorial" \\
    --service "AKS" --clean -m tutorial.md
  
  # Run with specific audience
  python main.py --repo https://github.com/user/repo --goal "Create networking guide" \\
    --service "AKS" --audience "DevOps engineers" --audience-level advanced \\
    -m material.pdf
  
  # Run for beginners
  python main.py --repo https://github.com/user/repo --goal "Create tutorial" \\
    --service "AKS" --audience "developers new to Kubernetes" \\
    --audience-level beginner -m tutorial.md
  
  # Run phases 1-3 only (analysis, strategy, generation)
  python main.py --repo https://github.com/user/repo --goal "Update networking guides" \\
    --service "AKS" --phases 3 -m material.docx
  
  # Auto-confirm selections and apply changes
  python main.py --repo https://github.com/user/repo --goal "Create tutorials" \\
    --service "AKS" --auto-confirm --apply-changes -m tutorial.md
  
  # Run all phases (1-5) and apply generated content
  python main.py --repo https://github.com/user/repo --goal "Update docs" \\
    --service "AKS" --apply-changes -m guide.pdf

Environment Variables:
  AZURE_OPENAI_ENDPOINT              - Azure OpenAI endpoint URL
  AZURE_OPENAI_COMPLETION_DEPLOYMENT - Deployment name for completion model
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT  - Deployment name for embedding model
  AZURE_OPENAI_TEMPERATURE          - Temperature for completions (default: 0.3)
        """


def add_required_arguments(parser: argparse.ArgumentParser):
    """Add required arguments to parser"""
    required = parser.add_argument_group('required arguments')
    
    required.add_argument(
        "--repo", 
        required=True,
        dest="repo_url",
        help="Repository URL to analyze (e.g., https://github.com/user/repo)"
    )
    
    required.add_argument(
        "--goal", 
        required=True,
        dest="content_goal",
        help="Goal for content creation/update (e.g., 'Create networking guide')"
    )
    
    required.add_argument(
        "--service", 
        required=True,
        dest="service_area",
        help="Target Azure service area (e.g., 'Azure Kubernetes Service', 'AKS')"
    )
    
    required.add_argument(
        "-m", "--materials", 
        nargs="+", 
        required=True,
        help="Support material files or URLs (PDFs, Word docs, Markdown, etc.)"
    )


def add_material_arguments(parser: argparse.ArgumentParser):
    """Add material-related arguments"""
    materials = parser.add_argument_group('material configuration')
    
    materials.add_argument(
        "--content-limit", 
        type=int, 
        default=15000, 
        help="Maximum characters to extract from each material (default: 15000)"
    )


def add_audience_arguments(parser: argparse.ArgumentParser):
    """Add audience-related arguments"""
    audience = parser.add_argument_group('audience configuration')
    
    audience.add_argument(
        "--audience", 
        default="technical professionals", 
        help="Target audience description (default: 'technical professionals')"
    )
    
    audience.add_argument(
        "--audience-level", 
        default="intermediate", 
        choices=["beginner", "intermediate", "advanced"],
        help="Technical expertise level of the target audience (default: intermediate)"
    )


def add_workflow_arguments(parser: argparse.ArgumentParser):
    """Add workflow control arguments"""
    workflow = parser.add_argument_group('workflow control')
    
    workflow.add_argument(
        "--phases", 
        default="all", 
        help=f"Run phases from 1 up to specified phase (1-{MAX_PHASES}) or 'all' (default: all)"
    )
    
    workflow.add_argument(
        "--auto-confirm", "-y", 
        action="store_true", 
        help="Auto-confirm all prompts (useful for automation)"
    )
    
    workflow.add_argument(
        "--apply-changes", 
        action="store_true", 
        help="Apply generated content to repository (otherwise preview only)"
    )
    
    workflow.add_argument(
        "--skip-toc", 
        action="store_true", 
        help="Skip TOC.yml management in Phase 4 (useful if TOC is invalid)"
    )
    
    workflow.add_argument(
        "--clean", 
        action="store_true", 
        help="Clear llm_outputs and work directory before starting (fresh run)"
    )


def add_output_arguments(parser: argparse.ArgumentParser):
    """Add output configuration arguments"""
    output = parser.add_argument_group('output configuration')
    
    output.add_argument(
        "--work-dir", 
        type=Path, 
        default=Path.cwd() / "work" / "tmp", 
        help="Working directory for cloned repository (default: ./work/tmp)"
    )
    
    output.add_argument(
        "--max-depth", 
        type=int, 
        default=3, 
        help="Maximum repository depth to analyze (default: 3)"
    )


def add_debug_arguments(parser: argparse.ArgumentParser):
    """Add debugging arguments"""
    debug = parser.add_argument_group('debugging options')
    
    debug.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Show detailed console output (INFO level logging)"
    )
    
    debug.add_argument(
        "--debug-similarity", 
        action="store_true", 
        help="Show detailed similarity scoring for content matching"
    )


def validate_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace):
    """Validate parsed arguments"""
    # Validate phases
    if args.phases != "all" and not (args.phases.isdigit() and 1 <= int(args.phases) <= MAX_PHASES):
        parser.error(f"--phases must be a number between 1 and {MAX_PHASES}, or 'all'")
    
    # Validate repository URL
    if not is_valid_url(args.repo_url):
        parser.error(f"Invalid repository URL: {args.repo_url}")
    
    # Validate materials exist
    for material in args.materials:
        if not is_valid_url(material) and not Path(material).exists():
            parser.error(f"Material not found: {material}")
    
    # Validate work directory
    try:
        args.work_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        parser.error(f"Cannot create work directory {args.work_dir}: {e}")
    
    # Check Azure OpenAI configuration
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        parser.error("AZURE_OPENAI_ENDPOINT environment variable not set. See --help for details.")


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def create_config_from_args(args: argparse.Namespace) -> Config:
    """Create Config object from parsed arguments"""
    return Config(
        repo_url=args.repo_url,
        content_goal=args.content_goal,
        service_area=args.service_area,
        audience=args.audience,
        audience_level=args.audience_level,
        support_materials=args.materials,
        auto_confirm=args.auto_confirm,
        work_dir=args.work_dir,
        max_repo_depth=args.max_depth,
        content_limit=args.content_limit,
        phases=args.phases,
        debug_similarity=args.debug_similarity,
        apply_changes=args.apply_changes,
        skip_toc=args.skip_toc
    )


def execute_workflow(config: Config, console_display: ConsoleDisplay):
    """Execute the content development workflow"""
    try:
        # Show header
        repo_name = config.repo_url.split('/')[-1].replace('.git', '')
        console_display.show_header(repo_name, config.content_goal, config.service_area)
        
        # Create orchestrator with console display
        orchestrator = ContentDeveloperOrchestrator(config, console_display)
        result = orchestrator.execute()
        
        # Display final results
        console_display.print_separator()
        display_results(result)
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(console_display)
    except Exception as e:
        handle_error(e, console_display)


def handle_keyboard_interrupt(console_display: ConsoleDisplay):
    """Handle user cancellation"""
    console_display.show_error("Operation cancelled by user", "Cancelled")
    sys.exit(1)


def handle_error(error: Exception, console_display: ConsoleDisplay):
    """Handle general errors"""
    console_display.show_error(str(error), "Error")
    logging.exception("Fatal error occurred")
    sys.exit(1)


if __name__ == "__main__":
    main() 