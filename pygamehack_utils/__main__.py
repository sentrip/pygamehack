from .cli import get_args, gui, generate_aob_classes, update_offsets_in_file


args = get_args()

if args.command == 'gui':
    gui(command=None)
elif args.command == 'generate':
    generate_aob_classes(command=None)
elif args.command == 'update':
    update_offsets_in_file(command=None)
