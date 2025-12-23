"""Test script for calendar processor."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from processor import CalendarProcessor


async def test_calendar_processor():
    """Test the calendar processor with real ICS URLs."""
    # Load environment variables
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / '.env')

    # Get ICS URLs from environment
    work_url = os.getenv('CALENDAR_WORK_URL')
    private_url = os.getenv('CALENDAR_PRIVATE_URL')

    if not work_url or not private_url:
        print("Error: CALENDAR_WORK_URL and CALENDAR_PRIVATE_URL must be set in .env")
        return

    # Setup paths
    project_root = Path(__file__).parent.parent.parent.parent
    exports_path = project_root / "data" / "exports"
    cache_dir = project_root / "data" / "cache" / "calendar"

    # Create processor
    processor = CalendarProcessor(
        exports_path=exports_path,
        ics_urls={
            'work': work_url,
            'private': private_url
        },
        cache_dir=cache_dir,
        timezone='Europe/Amsterdam'
    )

    # Run processor
    print("Starting calendar processor...")
    result = await processor.run()

    # Print results
    print(f"\nProcessor Result:")
    print(f"  Success: {result.success}")
    print(f"  Duration: {(result.ended_at - result.started_at).total_seconds():.2f}s")

    if result.success:
        print(f"  Output: {result.output_path}")
        print(f"  Metrics:")
        for key, value in result.metrics.items():
            print(f"    {key}: {value}")
    else:
        print(f"  Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_calendar_processor())
