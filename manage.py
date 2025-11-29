# manage.py
""" Main orchestrator of admin layer """


import argparse
import sys

def handle_subscribers(args):
    """Dispatcher for subscriber commands."""
    from src.management.subscriber_manager import (
        list_subscribers,
        add_subscriber,
        import_subscribers_from_file,
        delete_subscribers_interactive  # <-- Import the new function
    )
    if args.action == 'list':
        list_subscribers()
    elif args.action == 'add':
        add_subscriber(args.email, args.name, args.override)
    elif args.action == 'import':
        import_subscribers_from_file(args.file)
    elif args.action == 'delete':  # <-- Add case for delete
        delete_subscribers_interactive()

def handle_anchors(args):
    """Dispatcher for anchor commands."""
    from src.management.anchor_manager import (
        list_anchors,
        generate_template_csv,
        create_anchors_from_file,
        create_anchor_interactive,
        delete_anchors_interactive  # <-- Import the new function
    )
    
    if args.action == 'list':
        list_anchors()
    elif args.action == 'create':
        create_anchor_interactive()
    elif args.action == 'template':
        generate_template_csv()
    elif args.action == 'delete':  # <-- Add case for delete
        delete_anchors_interactive()
    elif args.action == 'import':
        if args.file:
            create_anchors_from_file(args.file)
        else:
            print("❌ Error: --file argument is required for import action.")
    else:
        print(f"Unknown action for anchors: {args.action}")

# NEW: Dispatcher for system commands.
def handle_system(args):
    from src.management.system_manager import (
        reset_analysis_data,
        reset_anchor_data,
        reset_subscriber_data,
        reset_enrichment_data
    )
    # Adding a confirmation step for destructive actions
    confirm = input(f"Are you sure you want to perform the action '{args.action}'? This cannot be undone. (y/n): ")
    if confirm.lower() != 'y':
        print("Action cancelled.")
        return

    if args.action == 'reset-analysis':
        reset_analysis_data()
    elif args.action == 'reset-anchors':
        reset_anchor_data()
    elif args.action == 'reset-subscribers':
        reset_subscriber_data()
    elif args.action == 'reset-enrichment':
        # --- MODIFIED --- Pass the new arguments to the function
        reset_enrichment_data(args.limit, args.offset)
    else:
        print(f"Unknown action for system: {args.action}")

def handle_testing(args):
    from src.management.testing_manager import (
        generate_test_anchors_csv,
        generate_test_subscribers_csv
    )
    if args.action == 'generate-anchors':
        generate_test_anchors_csv(args.output)
    elif args.action == 'generate-subscribers':
        generate_test_subscribers_csv(args.output)
    else:
        print(f"Unknown action for testing: {args.action}")

def main():
    """Main entry point for the management script."""
    parser = argparse.ArgumentParser(
        description="A master command-line interface (CLI) for managing the AI Daily Digest system.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Top-level commands')

   # --- Subscribers Command Group ---
    parser_subs = subparsers.add_parser('subscribers', help='Manage subscribers and subscriptions')
    subs_subparsers = parser_subs.add_subparsers(dest='action', required=True, help='Action to perform')
    
    # `subscribers list` command
    subs_subparsers.add_parser('list', help='List all subscribers and their subscriptions').set_defaults(func=handle_subscribers)
    
    # `subscribers add` command
    parser_subs_add = subs_subparsers.add_parser('add', help='Add a single new subscriber')
    parser_subs_add.add_argument('--email', type=str, required=True, help='Email address of the subscriber')
    parser_subs_add.add_argument('--name', type=str, required=True, help='Name of the subscriber')
    parser_subs_add.add_argument('--override', action='store_true', help='If subscriber exists, update their name')
    parser_subs_add.set_defaults(func=handle_subscribers)

    # `subscribers import` command
    parser_subs_import = subs_subparsers.add_parser('import', help='Bulk import subscribers and their subscriptions from a CSV')
    parser_subs_import.add_argument('--file', type=str, required=True, help='Path to the CSV file')
    parser_subs_import.set_defaults(func=handle_subscribers)

    # `subscribers delete` command  # <-- Add this new parser
    subs_subparsers.add_parser('delete', help='Launch an interactive wizard to delete subscribers').set_defaults(func=handle_subscribers)


    # --- Anchors Command Group ---
    parser_anchors = subparsers.add_parser('anchors', help='Manage semantic anchors')
    anchors_subparsers = parser_anchors.add_subparsers(dest='action', required=True, help='Action to perform')

    # `anchors list` command
    anchors_subparsers.add_parser('list', help='List all existing semantic anchors').set_defaults(func=handle_anchors)

    # `anchors create` command
    anchors_subparsers.add_parser('create', help='Launch the interactive wizard to create a new anchor').set_defaults(func=handle_anchors)

    # `anchors template` command
    anchors_subparsers.add_parser('template', help='Generate a CSV template for bulk anchor creation').set_defaults(func=handle_anchors)
    
    # `anchors import` command
    parser_anchors_import = anchors_subparsers.add_parser('import', help='Bulk import anchors from a CSV file')
    parser_anchors_import.add_argument('--file', type=str, required=True, help='Path to the CSV file to import')
    parser_anchors_import.set_defaults(func=handle_anchors)

    # `anchors delete` command
    anchors_subparsers.add_parser('delete', help='Launch an interactive wizard to delete anchors').set_defaults(func=handle_anchors)

    # --- NEW: System Command Group ---
    parser_system = subparsers.add_parser('system', help='Perform system-level maintenance and reset tasks')
    system_subparsers = parser_system.add_subparsers(dest='action', required=True, help='Action to perform')
    system_subparsers.add_parser('reset-analysis', help='Reset all analysis data (links and timestamps)').set_defaults(func=handle_system)
    system_subparsers.add_parser('reset-anchors', help='Delete all anchors and their components').set_defaults(func=handle_system)
    system_subparsers.add_parser('reset-subscribers', help='Delete all subscribers and their subscriptions').set_defaults(func=handle_system)
    
     # --- MODIFIED --- Add arguments to the reset-enrichment parser
    parser_reset_enrichment = system_subparsers.add_parser('reset-enrichment', help='Reset enrichment timestamps in the articles table')
    parser_reset_enrichment.add_argument('--limit', type=int, help='The maximum number of articles to reset')
    parser_reset_enrichment.add_argument('--offset', type=int, default=0, help='The starting offset for resetting articles')
    parser_reset_enrichment.set_defaults(func=handle_system)

    # --- NEW: Testing Command Group ---
    parser_testing = subparsers.add_parser('testing', help='Generate test data files')
    testing_subparsers = parser_testing.add_subparsers(dest='action', required=True, help='Action to perform')
    
    # `testing generate-anchors` command
    parser_gen_anchors = testing_subparsers.add_parser('generate-anchors', help='Generate a CSV file of test anchors')
    parser_gen_anchors.add_argument('--output', type=str, help='Optional: Path to the output CSV file')
    parser_gen_anchors.set_defaults(func=handle_testing)
    
    # `testing generate-subscribers` command
    parser_gen_subs = testing_subparsers.add_parser('generate-subscribers', help='Generate a CSV file of test subscribers')
    parser_gen_subs.add_argument('--output', type=str, help='Optional: Path to the output CSV file')
    parser_gen_subs.set_defaults(func=handle_testing)

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)

if __name__ == '__main__':
    main()
