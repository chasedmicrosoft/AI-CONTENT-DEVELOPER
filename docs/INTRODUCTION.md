# AI Content Developer

## What is it?

AI Content Developer is an intelligent documentation generation system that leverages OpenAI's GPT models to create, update, and enhance technical documentation for Microsoft Azure services. It's a sophisticated five-phase orchestration tool that analyzes existing documentation repositories, develops content strategies, generates new content, and ensures quality through automated remediation.

The tool operates as a command-line application that clones documentation repositories, analyzes their structure, and intelligently determines what content needs to be created or updated based on your specific goals and provided reference materials.

## What does it do?

### Core Capabilities

1. **Intelligent Content Analysis**
   - Automatically analyzes repository structure to find the most appropriate documentation directory
   - Processes existing documentation using embeddings for semantic understanding
   - Identifies content gaps and opportunities for improvement

2. **Strategic Content Planning**
   - Develops comprehensive content strategies based on your goals
   - Decides whether to CREATE new content, UPDATE existing content, or SKIP files
   - Aligns all decisions with your stated objectives and target audience

3. **Content Generation & Enhancement**
   - Creates new conceptual articles, how-to guides, tutorials, and reference documentation
   - Updates existing documentation with new information from your reference materials
   - Maintains Microsoft Learn documentation standards and formatting

4. **Quality Assurance & Remediation**
   - **SEO Optimization**: Improves titles, meta descriptions, headings, and keyword usage
   - **Security Review**: Identifies and removes sensitive information, adds security warnings
   - **Technical Accuracy**: Validates claims against source materials and corrects inaccuracies

5. **Preview-First Workflow**
   - All changes are first written to preview directories
   - Repository remains untouched unless you explicitly use `--apply-changes`
   - Allows review and verification before applying changes

### The Five-Phase Process

1. **Phase 1: Repository Analysis**
   - Clones the target repository
   - Analyzes provided materials (PDFs, Word docs, web pages)
   - Selects the most appropriate working directory

2. **Phase 2: Content Strategy**
   - Discovers existing relevant content using semantic search
   - Analyzes gaps between existing content and your goals
   - Creates a strategic plan for content creation/updates

3. **Phase 3: Content Generation**
   - Generates new content based on the strategy
   - Updates existing files with new information
   - Saves all content to preview directories

4. **Phase 4: Content Remediation**
   - Applies SEO best practices
   - Ensures security compliance
   - Validates technical accuracy

5. **Phase 5: TOC Management**
   - Updates Table of Contents (TOC.yml) files
   - Ensures proper navigation structure
   - Maintains documentation hierarchy

## Who is it for?

### Primary Users

1. **Technical Writers**
   - Need to create comprehensive documentation quickly
   - Want to maintain consistency across large documentation sets
   - Require automated quality checks and improvements

2. **Developer Relations Teams**
   - Creating documentation for new features or services
   - Updating existing docs with new capabilities
   - Ensuring technical accuracy and completeness

3. **Product Teams**
   - Need to document new Azure services or features
   - Want to align documentation with product requirements (PRDs)
   - Require scalable documentation solutions

4. **Documentation Managers**
   - Overseeing large-scale documentation projects
   - Ensuring quality and consistency standards
   - Managing documentation debt and gaps

### Ideal Use Cases

- **New Feature Documentation**: When launching new Azure services or features that need comprehensive documentation
- **Documentation Updates**: When existing documentation needs updates based on new PRDs or technical specifications
- **Content Migration**: When moving documentation between repositories or restructuring content
- **Quality Improvement**: When existing documentation needs SEO, security, or accuracy improvements
- **Bulk Documentation**: When multiple related articles need to be created or updated simultaneously

### Target Audience Levels

The tool can generate content for different expertise levels:
- **Beginner**: Foundational concepts and getting started guides
- **Intermediate**: In-depth explanations and standard procedures
- **Advanced**: Complex scenarios and expert-level content

### Supported Content Types

- Concept articles (explaining what and why)
- How-to guides (step-by-step procedures)
- Tutorials (learning-oriented walkthroughs)
- Quickstarts (fast-track getting started)
- Reference documentation (API/CLI references)
- Architecture guides (design and implementation)
- Best practices (recommendations and patterns)

## Key Benefits

1. **Efficiency**: Automates the time-consuming aspects of documentation creation
2. **Consistency**: Maintains Microsoft documentation standards automatically
3. **Quality**: Built-in remediation ensures high-quality output
4. **Safety**: Preview-first approach prevents accidental changes
5. **Intelligence**: Uses AI to understand context and make smart decisions
6. **Scalability**: Can handle large documentation repositories and bulk updates

## Getting Started

To use the AI Content Developer, you'll need:
- Python 3.8 or higher
- OpenAI API key
- Access to target GitHub repositories
- Reference materials (PDFs, Word docs, or web URLs)

The basic command structure is:
```bash
python main.py --repo <github-url> --goal "<your-goal>" --service "<azure-service>" --materials <material-paths> --audience "<target-audience>" --audience-level <level>
```

Add `--apply-changes` to apply changes to the repository, otherwise all changes remain in preview.

## Learn More

- See [README.md](README.md) for installation and usage instructions
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical implementation details
- Review the [examples](examples/) directory for sample use cases 