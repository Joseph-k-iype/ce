#!/usr/bin/env python3
"""
Rule Generator CLI
==================
Interactive command-line tool for developers to generate rules using AI.
Uses the new LangGraph rule ingestion workflow with multi-agent system.

Usage:
    python -m cli.rule_generator_cli
    python -m cli.rule_generator_cli --interactive
    python -m cli.rule_generator_cli --rule "Prohibit transfers from UK to China"
"""

import argparse
import json
import sys
import os
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.workflows.rule_ingestion_workflow import run_rule_ingestion, RuleIngestionResult
from services.database import get_db_service
from utils.graph_builder import RulesGraphBuilder
from config.settings import settings


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_banner():
    """Print CLI banner"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║              Compliance Engine - Rule Generator CLI              ║
║                    AI-Powered Rule Generation                     ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.END}
""")


def print_section(title: str):
    """Print a section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {message}{Colors.END}")


def get_user_input(prompt: str, default: Optional[str] = None) -> str:
    """Get user input with optional default"""
    if default:
        user_input = input(f"{Colors.BOLD}{prompt}{Colors.END} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{Colors.BOLD}{prompt}{Colors.END}: ").strip()


def confirm(prompt: str, default: bool = False) -> bool:
    """Get yes/no confirmation from user"""
    suffix = " [Y/n]" if default else " [y/N]"
    response = input(f"{Colors.BOLD}{prompt}{suffix}{Colors.END}: ").strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')


def display_generated_rule(result: RuleIngestionResult):
    """Display the generated rule in a formatted way"""
    print_section("Generated Rule Definition")

    if result.rule_definition:
        rule_def = result.rule_definition
        print(f"{Colors.CYAN}Rule ID:{Colors.END} {rule_def.get('rule_id', 'N/A')}")
        print(f"{Colors.CYAN}Rule Type:{Colors.END} {rule_def.get('rule_type', 'N/A')}")
        print(f"{Colors.CYAN}Iterations Used:{Colors.END} {result.iterations}")
        print()

        print(f"  {Colors.BOLD}Name:{Colors.END} {rule_def.get('name', 'N/A')}")
        print(f"  {Colors.BOLD}Description:{Colors.END} {rule_def.get('description', 'N/A')}")
        print(f"  {Colors.BOLD}Priority:{Colors.END} {rule_def.get('priority', 'N/A')}")
        print(f"  {Colors.BOLD}Outcome:{Colors.END} {rule_def.get('outcome', 'N/A')}")
        print(f"  {Colors.BOLD}ODRL Type:{Colors.END} {rule_def.get('odrl_type', 'N/A')}")
        print(f"  {Colors.BOLD}Requires PII:{Colors.END} {rule_def.get('requires_pii', False)}")

        if rule_def.get('origin_countries'):
            print(f"  {Colors.BOLD}Origin Countries:{Colors.END} {', '.join(rule_def['origin_countries'])}")
        if rule_def.get('origin_group'):
            print(f"  {Colors.BOLD}Origin Group:{Colors.END} {rule_def['origin_group']}")
        if rule_def.get('receiving_countries'):
            print(f"  {Colors.BOLD}Receiving Countries:{Colors.END} {', '.join(rule_def['receiving_countries'])}")
        if rule_def.get('receiving_group'):
            print(f"  {Colors.BOLD}Receiving Group:{Colors.END} {rule_def['receiving_group']}")
        if rule_def.get('attribute_name'):
            print(f"  {Colors.BOLD}Attribute Name:{Colors.END} {rule_def['attribute_name']}")
        if rule_def.get('attribute_keywords'):
            print(f"  {Colors.BOLD}Attribute Keywords:{Colors.END} {', '.join(rule_def['attribute_keywords'])}")

    if result.cypher_queries:
        print_section("Generated Cypher Queries")
        queries = result.cypher_queries.get('queries', {})

        if queries.get('rule_check'):
            print(f"{Colors.YELLOW}Rule Check Query:{Colors.END}")
            print(f"  {queries['rule_check'][:200]}..." if len(queries.get('rule_check', '')) > 200 else f"  {queries.get('rule_check', 'N/A')}")
            print()

        if queries.get('rule_insert'):
            print(f"{Colors.YELLOW}Rule Insert Query:{Colors.END}")
            print(f"  {queries['rule_insert'][:200]}..." if len(queries.get('rule_insert', '')) > 200 else f"  {queries.get('rule_insert', 'N/A')}")
            print()

    if result.analysis_result:
        print_section("AI Reasoning")
        for step, analysis in result.analysis_result.items():
            print(f"  {Colors.BOLD}{step}:{Colors.END} {str(analysis)[:100]}..." if len(str(analysis)) > 100 else f"  {Colors.BOLD}{step}:{Colors.END} {analysis}")


def display_python_code(result: RuleIngestionResult):
    """Display the Python code to add this rule manually"""
    if not result.rule_definition:
        return

    print_section("Python Code (for manual addition)")

    rule_def = result.rule_definition
    rule_type = rule_def.get('rule_type', 'transfer')

    origin_countries = rule_def.get('origin_countries')
    receiving_countries = rule_def.get('receiving_countries')

    origin_str = f"frozenset({origin_countries})" if origin_countries else "None"
    receiving_str = f"frozenset({receiving_countries})" if receiving_countries else "None"

    if rule_type == 'transfer':
        code = f'''
# Add to rules/dictionaries/rules_definitions.py in TRANSFER_RULES

"{rule_def.get('rule_id', 'RULE_NEW')}": TransferRule(
    rule_id="{rule_def.get('rule_id', 'RULE_NEW')}",
    name="{rule_def.get('name', '')}",
    description="""{rule_def.get('description', '')}""",
    priority={rule_def.get('priority', 10)},
    origin_countries={origin_str},
    origin_group={f'"{rule_def["origin_group"]}"' if rule_def.get('origin_group') else 'None'},
    receiving_countries={receiving_str},
    receiving_group={f'"{rule_def["receiving_group"]}"' if rule_def.get('receiving_group') else 'None'},
    outcome=RuleOutcome.{"PROHIBITION" if rule_def.get('outcome') == 'prohibition' else 'PERMISSION'},
    requires_pii={rule_def.get('requires_pii', False)},
    required_actions={rule_def.get('required_actions', [])},
    odrl_type="{rule_def.get('odrl_type', 'Prohibition')}",
    odrl_action="{rule_def.get('odrl_action', 'transfer')}",
    odrl_target="{rule_def.get('odrl_target', 'Data')}",
    enabled=True,
),
'''
    else:
        code = f'''
# Add to rules/dictionaries/rules_definitions.py in ATTRIBUTE_RULES

"{rule_def.get('rule_id', 'RULE_NEW')}": AttributeRule(
    rule_id="{rule_def.get('rule_id', 'RULE_NEW')}",
    name="{rule_def.get('name', '')}",
    description="""{rule_def.get('description', '')}""",
    priority={rule_def.get('priority', 10)},
    attribute_name="{rule_def.get('attribute_name', '')}",
    attribute_keywords={rule_def.get('attribute_keywords', [])},
    origin_countries={origin_str},
    origin_group={f'"{rule_def["origin_group"]}"' if rule_def.get('origin_group') else 'None'},
    receiving_countries={receiving_str},
    receiving_group={f'"{rule_def["receiving_group"]}"' if rule_def.get('receiving_group') else 'None'},
    outcome=RuleOutcome.{"PROHIBITION" if rule_def.get('outcome') == 'prohibition' else 'PERMISSION'},
    requires_pii={rule_def.get('requires_pii', False)},
    odrl_type="{rule_def.get('odrl_type', 'Prohibition')}",
    odrl_action="{rule_def.get('odrl_action', 'transfer')}",
    odrl_target="{rule_def.get('odrl_target', 'Data')}",
    enabled=True,
),
'''
    print(f"{Colors.YELLOW}{code}{Colors.END}")


def save_to_file(result: RuleIngestionResult, filename: str):
    """Save the generated rule to a JSON file"""
    output = {
        "generated_at": datetime.now().isoformat(),
        "success": result.success,
        "rule_definition": result.rule_definition,
        "cypher_queries": result.cypher_queries,
        "dictionary_result": result.dictionary_result,
        "validation_result": result.validation_result,
        "analysis_result": result.analysis_result,
        "iterations": result.iterations,
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print_success(f"Rule saved to {filename}")


def upload_to_graph(result: RuleIngestionResult) -> bool:
    """Upload the generated rule to the RulesGraph"""
    try:
        db = get_db_service()
        builder = RulesGraphBuilder(db.get_rules_graph())

        rule_def = result.rule_definition
        rule_type = rule_def.get('rule_type', 'transfer')

        if rule_type == 'transfer':
            success = builder.add_transfer_rule(rule_def)
        else:
            success = builder.add_attribute_rule(rule_def)

        if success:
            rule_id = rule_def.get('rule_id', 'unknown')
            print_success(f"Rule {rule_id} uploaded to RulesGraph")
            return True
        else:
            print_error("Failed to upload rule to graph")
            return False

    except Exception as e:
        print_error(f"Failed to upload rule: {e}")
        return False


def interactive_mode():
    """Run the interactive rule generation mode"""
    print_banner()
    print_info("Interactive Rule Generation Mode")
    print_info("Type 'quit' or 'exit' to end the session")
    print()

    while True:
        print(f"\n{Colors.BOLD}{'─'*60}{Colors.END}")
        print()

        # Get rule text
        rule_text = get_user_input("Enter your rule in natural language")
        if rule_text.lower() in ('quit', 'exit', 'q'):
            print_info("Goodbye!")
            break

        if not rule_text:
            print_warning("Please enter a rule description")
            continue

        # Get additional context
        origin_country = get_user_input("Origin country", "United States")
        scenario_type = get_user_input("Scenario type (transfer/attribute)", "transfer")
        receiving_input = get_user_input("Receiving countries (comma-separated)", "")
        receiving_countries = [c.strip() for c in receiving_input.split(",") if c.strip()] if receiving_input else []

        data_categories_input = get_user_input("Data categories (comma-separated, or empty)", "")
        data_categories = [c.strip() for c in data_categories_input.split(",") if c.strip()] if data_categories_input else None

        if scenario_type not in ('transfer', 'attribute'):
            scenario_type = "transfer"

        # Generate the rule
        print()
        print_info("Generating rule using AI agents...")
        print_info("This may take a moment as the LangGraph workflow runs...")
        print()

        result = run_rule_ingestion(
            origin_country=origin_country,
            scenario_type=scenario_type,
            receiving_countries=receiving_countries,
            rule_text=rule_text,
            data_categories=data_categories,
            max_iterations=10,
        )

        if not result.success:
            print_error(f"Rule generation failed: {result.error_message}")
            continue

        # Display the generated rule
        display_generated_rule(result)

        # Developer sign-off workflow
        print_section("Developer Sign-Off")

        print("Please review the generated rule above.")
        print()

        # Option 1: View Python code
        if confirm("View Python code for manual addition?"):
            display_python_code(result)

        # Option 2: Save to file
        if confirm("Save rule to JSON file?"):
            rule_id = result.rule_definition.get('rule_id', 'unknown') if result.rule_definition else 'unknown'
            filename = get_user_input("Filename", f"generated_rule_{rule_id}.json")
            save_to_file(result, filename)

        # Option 3: Upload to graph (requires explicit approval)
        print()
        print_warning("IMPORTANT: Uploading to the graph will make this rule active!")
        if confirm("Approve and upload to RulesGraph?"):
            if confirm("Are you sure? This action cannot be easily undone"):
                upload_to_graph(result)
            else:
                print_info("Upload cancelled")
        else:
            print_info("Rule not uploaded - you can add it manually using the Python code above")


def single_rule_mode(rule_text: str, origin_country: str = "United States",
                     scenario_type: str = "transfer", auto_approve: bool = False):
    """Generate a single rule from command line arguments"""
    print_banner()
    print_info(f"Generating rule from: {rule_text[:50]}...")
    print()

    result = run_rule_ingestion(
        origin_country=origin_country,
        scenario_type=scenario_type,
        receiving_countries=[],
        rule_text=rule_text,
        max_iterations=3,
    )

    if not result.success:
        print_error(f"Rule generation failed: {result.error_message}")
        sys.exit(1)

    display_generated_rule(result)
    display_python_code(result)

    if auto_approve:
        print_warning("Auto-approve mode: Uploading to graph...")
        if upload_to_graph(result):
            print_success("Rule uploaded successfully")
        else:
            sys.exit(1)
    else:
        print()
        print_info("To upload this rule, run with --auto-approve or use --interactive mode")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI-Powered Rule Generator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode (recommended):
    python -m cli.rule_generator_cli --interactive

  Single rule generation:
    python -m cli.rule_generator_cli --rule "Prohibit transfers from UK to China"

  With country context:
    python -m cli.rule_generator_cli --rule "Health data cannot leave the EU" --country "Germany"

  Auto-approve and upload:
    python -m cli.rule_generator_cli --rule "..." --auto-approve
        """
    )

    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode with full sign-off workflow'
    )

    parser.add_argument(
        '--rule', '-r',
        type=str,
        help='Natural language rule description'
    )

    parser.add_argument(
        '--country', '-c',
        type=str,
        default='United States',
        help='Primary country context (default: United States)'
    )

    parser.add_argument(
        '--type', '-t',
        type=str,
        choices=['transfer', 'attribute'],
        default='transfer',
        help='Scenario type (default: transfer)'
    )

    parser.add_argument(
        '--auto-approve',
        action='store_true',
        help='Automatically approve and upload the rule (use with caution)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Save generated rule to JSON file'
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.rule:
        single_rule_mode(
            rule_text=args.rule,
            origin_country=args.country,
            scenario_type=args.type,
            auto_approve=args.auto_approve,
        )
    else:
        # Default to interactive mode
        interactive_mode()


if __name__ == '__main__':
    main()
