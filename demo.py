#!/usr/bin/env python
"""
Demo script for MP3JuiceMusicClient.

Usage:
    python demo.py "song name" [--max-results N]
    python demo.py                    # Interactive mode
"""
import sys
import argparse
import logging

# Add parent to path
sys.path.insert(0, r'C:\Users\shaheen\AppData\Local\Claude-3p\local-agent-mode-sessions\3235ebaa\00000000\aae63211\outputs\mp3juice_client')

from sources import MP3JuiceMusicClient


def get_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


def get_bool_input(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    user_input = input(f"{prompt} ({default_str}): ").strip().lower()
    if not user_input:
        return default
    return user_input in ('y', 'yes', 'true', '1')


def get_int_input(prompt: str, default: int) -> int:
    """Get integer input from user."""
    user_input = input(f"{prompt} [{default}]: ").strip()
    if not user_input:
        return default
    try:
        return int(user_input)
    except ValueError:
        print(f"Invalid number, using default: {default}")
        return default


def main():
    parser = argparse.ArgumentParser(description='Search and download music from MP3Juice')
    parser.add_argument('query', nargs='?', help='Song name to search for (optional, will prompt if omitted)')
    parser.add_argument('--max-results', type=int, default=5, help='Maximum results to fetch')
    parser.add_argument('--download', action='store_true', help='Download the first result')
    parser.add_argument('--output-dir', default='.', help='Output directory for downloads')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--interactive', action='store_true', help='Force interactive mode')
    args = parser.parse_args()

    # Interactive mode: prompt for missing values
    if not args.query or args.interactive:
        print("\n=== MP3Juice Music Search ===\n")
        args.query = get_input("Enter song/artist name to search for")
        while not args.query:
            print("Query cannot be empty!")
            args.query = get_input("Enter song/artist name to search for")

        args.max_results = get_int_input("Max results per source (YouTube + SoundCloud)", args.max_results)
        args.download = get_bool_input("Download the first result?", args.download)

        if args.download:
            args.output_dir = get_input("Output directory", args.output_dir)

        args.debug = get_bool_input("Enable debug logging?", args.debug)
        print()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print(f"Searching for: {args.query}")
    print(f"Max results: {args.max_results}")
    print("-" * 50)

    # Create client
    client = MP3JuiceMusicClient(
        search_size_per_source=args.max_results,
        disable_print=False
    )

    try:
        results = client.search(args.query)

        if not results:
            print("No results found.")
            return 1

        print(f"\nFound {len(results)} results:\n")
        for i, song in enumerate(results, 1):
            print(f"{i}. {song.song_name}")
            print(f"   Source: {song.root_source}")
            print(f"   Size: {song.file_size}")
            print(f"   Duration: {song.duration}")
            print(f"   URL: {song.download_url}")
            print()

        # Download first result if requested
        if args.download and results:
            import os
            os.makedirs(args.output_dir, exist_ok=True)

            first = results[0]
            filename = f"{first.song_name}{first.ext}"
            filepath = os.path.join(args.output_dir, filename)

            print(f"Downloading to: {filepath}")
            with open(filepath, 'wb') as f:
                f.write(first.downloaded_contents)
            print(f"Done! Saved {len(first.downloaded_contents)} bytes")

    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())